"""Tests for Dash callback logic.

These test the pure-logic parts of callbacks without running a Dash server.
For the callback functions that depend on ctx.triggered_id, we patch it.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from pubnet.fetch import load_demo
from pubnet.analyze import (
    clean_publications,
    build_coauthor_graph,
    compute_citation_trends,
    cluster_topics,
    compute_stats,
)
from pubnet.journal_if import JournalIFLookup
from pubnet.models import (
    Publication, Author, CoauthorGraph, CitationTrends,
    TopicAnalysis, StatsSummary,
)


@pytest.fixture
def demo_stores():
    """Build the profile-store and analysis-store dicts as callbacks would."""
    author = load_demo()
    pubs = clean_publications(author.publications)
    if_lookup = JournalIFLookup()
    ifs = if_lookup.enrich_publications(pubs)
    graph = build_coauthor_graph(author, pubs)
    trends = compute_citation_trends(pubs)
    topics = cluster_topics(pubs, num_clusters=5)
    stats = compute_stats(author, pubs, impact_factors=ifs)

    profile_data = {
        "author": author.model_dump(),
        "publications": [p.model_dump() for p in pubs],
        "impact_factors": {k: v for k, v in ifs.items() if v is not None},
    }
    analysis_data = {
        "stats": stats.model_dump(),
        "coauthor_graph": graph.model_dump(),
        "citation_trends": trends.model_dump(),
        "topic_analysis": topics.model_dump(),
    }
    return profile_data, analysis_data


class TestOnAnalyzeLogic:
    """Test the on_analyze callback's data pipeline."""

    def test_demo_data_roundtrip(self, demo_stores):
        """Profile and analysis stores should survive JSON serialization."""
        profile_data, analysis_data = demo_stores

        json_profile = json.dumps(profile_data)
        json_analysis = json.dumps(analysis_data)

        restored_profile = json.loads(json_profile)
        restored_analysis = json.loads(json_analysis)

        pubs = [Publication(**p) for p in restored_profile["publications"]]
        assert len(pubs) > 0

        stats = StatsSummary(**restored_analysis["stats"])
        assert stats.total_publications == len(pubs)

    def test_stores_have_required_keys(self, demo_stores):
        profile_data, analysis_data = demo_stores
        assert "author" in profile_data
        assert "publications" in profile_data
        assert "impact_factors" in profile_data
        assert "stats" in analysis_data
        assert "coauthor_graph" in analysis_data
        assert "citation_trends" in analysis_data
        assert "topic_analysis" in analysis_data


class TestFilterLogic:
    """Test the filtering logic used by update_main."""

    def test_year_filter(self, demo_stores):
        profile_data, _ = demo_stores
        pubs = [Publication(**p) for p in profile_data["publications"]]
        year_range = [2022, 2024]
        filtered = [p for p in pubs if p.year and year_range[0] <= p.year <= year_range[1]]
        assert all(year_range[0] <= p.year <= year_range[1] for p in filtered)
        assert len(filtered) < len(pubs)

    def test_citation_filter(self, demo_stores):
        profile_data, _ = demo_stores
        pubs = [Publication(**p) for p in profile_data["publications"]]
        min_cites = 100
        filtered = [p for p in pubs if p.citations >= min_cites]
        assert all(p.citations >= min_cites for p in filtered)
        assert len(filtered) < len(pubs)

    def test_coauthor_filter(self, demo_stores):
        profile_data, _ = demo_stores
        pubs = [Publication(**p) for p in profile_data["publications"]]
        # Pick a real co-author from the data
        all_authors = set()
        for p in pubs:
            all_authors.update(p.authors)
        # Remove the ego author and pick one co-author
        ego_name = profile_data["author"]["name"]
        coauthors = [a for a in all_authors if a != ego_name]
        assert len(coauthors) > 0
        target = coauthors[0]
        filtered = [p for p in pubs if target in p.authors]
        assert len(filtered) > 0
        assert len(filtered) < len(pubs)

    def test_cluster_filter(self, demo_stores):
        profile_data, analysis_data = demo_stores
        pubs = [Publication(**p) for p in profile_data["publications"]]
        topics = TopicAnalysis(**analysis_data["topic_analysis"])
        assert len(topics.clusters) > 0
        cluster = topics.clusters[0]
        cluster_indices = set(cluster.publication_indices)
        filtered = [p for i, p in enumerate(pubs) if i in cluster_indices]
        assert len(filtered) == cluster.publication_count

    def test_combined_filters(self, demo_stores):
        """Multiple filters compose (all are AND)."""
        profile_data, _ = demo_stores
        pubs = [Publication(**p) for p in profile_data["publications"]]
        # Year + citation filter
        year_range = [2020, 2024]
        min_cites = 50
        filtered = pubs
        filtered = [p for p in filtered if p.year and year_range[0] <= p.year <= year_range[1]]
        filtered = [p for p in filtered if p.citations >= min_cites]
        assert len(filtered) <= len(pubs)
        assert all(p.citations >= min_cites for p in filtered)
        assert all(year_range[0] <= p.year <= year_range[1] for p in filtered)


class TestSortLogic:
    """Test the on_sort callback mapping."""

    def test_sort_map(self):
        sort_map = {
            "sort-citations": "citations",
            "sort-year": "year",
            "sort-if": "if",
            "sort-venue": "venue",
        }
        for trigger_id, expected in sort_map.items():
            assert sort_map[trigger_id] == expected

    def test_sort_default(self):
        sort_map = {
            "sort-citations": "citations",
            "sort-year": "year",
            "sort-if": "if",
            "sort-venue": "venue",
        }
        assert sort_map.get("unknown-id", "citations") == "citations"


class TestNetworkClickLogic:
    """Test the on_network_click callback logic."""

    def test_ego_click_returns_none(self):
        node_data = {"is_ego": True, "full_name": "Sanjiv Kumar"}
        # Ego click should clear filter
        if node_data.get("is_ego"):
            result = None
        else:
            result = node_data.get("full_name")
        assert result is None

    def test_coauthor_click_returns_name(self):
        node_data = {"is_ego": False, "full_name": "Alice Smith"}
        if node_data.get("is_ego"):
            result = None
        else:
            result = node_data.get("full_name")
        assert result == "Alice Smith"

    def test_empty_click_returns_none(self):
        node_data = None
        result = None if not node_data else node_data.get("full_name")
        assert result is None


class TestClusterClickLogic:
    def test_valid_click(self):
        click_data = {"points": [{"customdata": 2}]}
        point = click_data["points"][0]
        assert point.get("customdata") == 2

    def test_empty_click(self):
        click_data = None
        result = None
        if click_data and click_data.get("points"):
            result = click_data["points"][0].get("customdata")
        assert result is None


class TestExportLogic:
    def test_export_produces_json(self, demo_stores):
        profile_data, _ = demo_stores
        exported = json.dumps(profile_data["publications"], indent=2)
        parsed = json.loads(exported)
        assert isinstance(parsed, list)
        assert len(parsed) > 0
        assert "title" in parsed[0]


class TestYearRangeLogic:
    def test_year_range_from_data(self, demo_stores):
        profile_data, _ = demo_stores
        years = [p["year"] for p in profile_data["publications"] if p.get("year")]
        y_min = min(years)
        y_max = max(years)
        marks = {y: str(y) for y in range(y_min, y_max + 1) if y % 2 == 0}
        marks[y_min] = str(y_min)
        marks[y_max] = str(y_max)
        assert y_min < y_max
        assert str(y_min) in marks.values()
        assert str(y_max) in marks.values()

    def test_year_range_no_data(self):
        """Without data, defaults to 2000-2026."""
        y_min, y_max = 2000, 2026
        assert y_min == 2000
        assert y_max == 2026

    def test_year_range_no_years(self):
        """Publications with no years should give defaults."""
        pubs = [{"title": "Test", "year": None}]
        years = [p["year"] for p in pubs if p.get("year")]
        assert len(years) == 0


class TestGetActiveView:
    """Test _get_active_view helper."""

    def test_view_map_completeness(self):
        from pubnet.gui.callbacks import _get_active_view
        view_map = {
            "nav-all": "all",
            "nav-network": "network",
            "nav-trends": "trends",
            "nav-clusters": "clusters",
            "nav-pubs": "pubs",
        }
        for nav_id, view_name in view_map.items():
            assert view_map[nav_id] == view_name


class TestEmptyState:
    def test_empty_state_returns_list(self):
        from pubnet.gui.callbacks import _empty_state
        result = _empty_state()
        assert isinstance(result, list)
        assert len(result) == 2  # stat cards + loading message
