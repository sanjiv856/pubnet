"""Tests for the Dash GUI components and app factory."""

import json
import pytest

from pubnet.fetch import load_demo
from pubnet.analyze import (
    clean_publications,
    build_coauthor_graph,
    compute_citation_trends,
    cluster_topics,
    compute_stats,
)
from pubnet.journal_if import JournalIFLookup


@pytest.fixture
def demo_data():
    """Load and analyse demo data for GUI testing."""
    author = load_demo()
    pubs = clean_publications(author.publications)
    if_lookup = JournalIFLookup()
    ifs = if_lookup.enrich_publications(pubs)
    graph = build_coauthor_graph(author, pubs)
    trends = compute_citation_trends(pubs)
    topics = cluster_topics(pubs, num_clusters=5)
    stats = compute_stats(author, pubs, impact_factors=ifs)
    return {
        "author": author,
        "pubs": pubs,
        "ifs": ifs,
        "graph": graph,
        "trends": trends,
        "topics": topics,
        "stats": stats,
    }


class TestAppFactory:
    def test_create_app(self):
        from pubnet.gui.app import create_app
        app = create_app()
        assert app.title == "PubNet"

    def test_create_app_with_url(self):
        from pubnet.gui.app import create_app
        app = create_app(scholar_url="https://scholar.google.com/citations?user=TEST")
        layout_str = str(app.layout)
        assert "TEST" in layout_str

    def test_layout_has_required_ids(self):
        from pubnet.gui.app import create_app
        app = create_app()
        layout_str = str(app.layout)
        required_ids = [
            "scholar-url-input", "analyze-btn", "export-json-btn", "export-csv-btn",
            "profile-store", "analysis-store",
            "year-range", "min-citations", "ref-format",
            "nav-all", "nav-network", "nav-trends", "nav-clusters", "nav-pubs",
        ]
        for id_name in required_ids:
            assert id_name in layout_str, f"Missing ID: {id_name}"


class TestStatCards:
    def test_empty_stat_cards(self):
        from pubnet.gui.components.stat_cards import stat_cards_row
        row = stat_cards_row()
        assert len(row.children) == 5

    def test_stat_cards_with_data(self, demo_data):
        from pubnet.gui.components.stat_cards import stat_cards_row
        row = stat_cards_row(demo_data["stats"].model_dump())
        assert len(row.children) >= 5


class TestNetworkComponent:
    def test_build_elements(self, demo_data):
        from pubnet.gui.components.network import build_cytoscape_elements
        elements = build_cytoscape_elements(demo_data["graph"])
        nodes = [e for e in elements if "source" not in e["data"]]
        edges = [e for e in elements if "source" in e["data"]]
        assert len(nodes) > 0
        assert len(edges) > 0

    def test_ego_node_marked(self, demo_data):
        from pubnet.gui.components.network import build_cytoscape_elements
        elements = build_cytoscape_elements(demo_data["graph"])
        ego_nodes = [e for e in elements if e["data"].get("is_ego")]
        assert len(ego_nodes) == 1
        assert ego_nodes[0]["data"]["label"] == "You"


class TestTrendsComponent:
    def test_build_figure(self, demo_data):
        from pubnet.gui.components.trends import build_citation_figure
        fig = build_citation_figure(demo_data["trends"])
        assert len(fig.data) == 2  # bars + h-index line

    def test_empty_figure(self):
        from pubnet.gui.components.trends import build_citation_figure
        fig = build_citation_figure(None)
        assert len(fig.data) == 0


class TestClustersComponent:
    def test_build_figure(self, demo_data):
        from pubnet.gui.components.clusters import build_cluster_figure
        fig = build_cluster_figure(demo_data["topics"])
        assert len(fig.data) == 1  # scatter trace

    def test_empty_figure(self):
        from pubnet.gui.components.clusters import build_cluster_figure
        fig = build_cluster_figure(None)
        assert len(fig.data) == 0


class TestPubTable:
    def test_sort_by_citations(self, demo_data):
        from pubnet.gui.components.pub_table import _sort_pubs
        sorted_pubs = _sort_pubs(demo_data["pubs"], "citations", demo_data["ifs"])
        cites = [p.citations for p in sorted_pubs]
        assert cites == sorted(cites, reverse=True)

    def test_sort_by_year(self, demo_data):
        from pubnet.gui.components.pub_table import _sort_pubs
        sorted_pubs = _sort_pubs(demo_data["pubs"], "year", demo_data["ifs"])
        years = [p.year or 0 for p in sorted_pubs]
        assert years == sorted(years, reverse=True)

    def test_table_component(self, demo_data):
        from pubnet.gui.components.pub_table import pub_table_component
        table = pub_table_component(demo_data["pubs"], demo_data["ifs"], "apa", "citations")
        assert table.id == "pub-table-panel"


class TestDataSerialization:
    """Test that analysis data survives JSON round-trip for dcc.Store."""

    def test_profile_store_roundtrip(self, demo_data):
        from pubnet.models import Author, Publication
        profile_data = {
            "author": demo_data["author"].model_dump(),
            "publications": [p.model_dump() for p in demo_data["pubs"]],
            "impact_factors": {k: v for k, v in demo_data["ifs"].items() if v is not None},
        }
        json_str = json.dumps(profile_data)
        restored = json.loads(json_str)
        assert len(restored["publications"]) == len(demo_data["pubs"])
        assert restored["author"]["name"] == "Sanjiv Kumar"

    def test_analysis_store_roundtrip(self, demo_data):
        from pubnet.models import StatsSummary, CoauthorGraph, CitationTrends, TopicAnalysis
        analysis_data = {
            "stats": demo_data["stats"].model_dump(),
            "coauthor_graph": demo_data["graph"].model_dump(),
            "citation_trends": demo_data["trends"].model_dump(),
            "topic_analysis": demo_data["topics"].model_dump(),
        }
        json_str = json.dumps(analysis_data)
        restored = json.loads(json_str)
        stats = StatsSummary(**restored["stats"])
        assert stats.total_publications == 27
        graph = CoauthorGraph(**restored["coauthor_graph"])
        assert gra