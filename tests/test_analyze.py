"""Tests for analysis modules."""

import pytest
from pubnet.models import Publication
from pubnet.analyze import (
    clean_publications,
    build_coauthor_graph,
    compute_citation_trends,
    cluster_topics,
    compute_stats,
    _compute_h_index,
)


class TestCleanPublications:
    def test_dedup_removes_near_duplicates(self, duplicate_publications):
        cleaned = clean_publications(duplicate_publications)
        # "Machine learning..." appears twice — should be deduped to 1
        assert len(cleaned) == 2

    def test_dedup_keeps_higher_citations(self, duplicate_publications):
        cleaned = clean_publications(duplicate_publications)
        ml_pubs = [p for p in cleaned if "machine learning" in p.title.lower()]
        assert len(ml_pubs) == 1
        assert ml_pubs[0].citations == 150  # the higher one

    def test_fills_missing_venue(self):
        pubs = [Publication(title="No venue", year=2023)]
        cleaned = clean_publications(pubs)
        assert cleaned[0].venue == "Unknown"

    def test_sorts_by_year_descending(self, sample_publications):
        cleaned = clean_publications(sample_publications)
        years = [p.year for p in cleaned if p.year]
        assert years == sorted(years, reverse=True)

    def test_strips_author_whitespace(self):
        pubs = [Publication(title="Test", authors=["  Alice   Smith  ", "Bob"])]
        cleaned = clean_publications(pubs)
        assert cleaned[0].authors[0] == "Alice Smith"


class TestCoauthorGraph:
    def test_graph_has_nodes(self, sample_author, sample_publications):
        graph = build_coauthor_graph(sample_author, sample_publications)
        assert graph.total_coauthors > 0
        assert len(graph.nodes) > 1

    def test_ego_node_exists(self, sample_author, sample_publications):
        graph = build_coauthor_graph(sample_author, sample_publications)
        ego_nodes = [n for n in graph.nodes if n.is_ego]
        assert len(ego_nodes) == 1
        assert ego_nodes[0].name == "Alice Smith"

    def test_edge_weights(self, sample_author, sample_publications):
        graph = build_coauthor_graph(sample_author, sample_publications)
        # Bob Jones appears in 2 papers with Alice → weight 2
        bob_edges = [e for e in graph.edges if "Bob Jones" in (e.source, e.target) and "Alice Smith" in (e.source, e.target)]
        assert len(bob_edges) == 1
        assert bob_edges[0].weight == 2

    def test_empty_publications(self, sample_author):
        graph = build_coauthor_graph(sample_author, [])
        assert graph.total_coauthors == 0


class TestCitationTrends:
    def test_yearly_counts(self, sample_publications):
        trends = compute_citation_trends(sample_publications)
        assert len(trends.yearly) > 0
        assert trends.first_year == 2021
        assert trends.last_year == 2024

    def test_citation_sums(self, sample_publications):
        trends = compute_citation_trends(sample_publications)
        # 2023 has two pubs: 150 + 200 = 350
        year_2023 = next(y for y in trends.yearly if y.year == 2023)
        assert year_2023.citation_count == 350
        assert year_2023.publication_count == 2

    def test_cumulative_h_index_grows(self, sample_publications):
        trends = compute_citation_trends(sample_publications)
        h_indices = [y.cumulative_h_index for y in trends.yearly]
        # h-index should be non-decreasing
        for i in range(1, len(h_indices)):
            assert h_indices[i] >= h_indices[i - 1]

    def test_empty_publications(self):
        trends = compute_citation_trends([])
        assert trends.yearly == []


class TestTopicClusters:
    def test_clusters_created(self, sample_publications):
        result = cluster_topics(sample_publications, num_clusters=2)
        assert result.num_clusters == 2
        assert len(result.clusters) == 2

    def test_all_pubs_assigned(self, sample_publications):
        result = cluster_topics(sample_publications, num_clusters=2)
        all_indices = set()
        for c in result.clusters:
            all_indices.update(c.publication_indices)
        assert len(all_indices) == len(sample_publications)

    def test_clusters_have_keywords(self, sample_publications):
        result = cluster_topics(sample_publications, num_clusters=2)
        for c in result.clusters:
            assert len(c.keywords) > 0

    def test_fewer_pubs_than_clusters(self):
        pubs = [Publication(title="Only one paper", abstract="Test")]
        result = cluster_topics(pubs, num_clusters=5)
        assert result.num_clusters <= 1


class TestComputeStats:
    def test_basic_stats(self, sample_author, sample_publications):
        stats = compute_stats(sample_author, sample_publications)
        assert stats.total_publications == 5
        assert stats.total_citations == 760
        assert stats.h_index == 4

    def test_years_active(self, sample_author, sample_publications):
        stats = compute_stats(sample_author, sample_publications)
        assert stats.years_active == "2021–2024"

    def test_top_venue(self, sample_author, sample_publications):
        stats = compute_stats(sample_author, sample_publications)
        assert stats.top_venue == "Nature Medicine"
        assert stats.top_venue_count == 2

    def test_coauthor_count(self, sample_author, sample_publications):
        stats = compute_stats(sample_author, sample_publications)
        # Bob Jones, Carol White, David Brown, Eve Green, Frank Lee = 5
        assert stats.unique_coauthors == 5


class TestHIndex:
    def test_h_index_calculation(self):
        pubs = [
            Publication(title=f"P{i}", citations=c)
            for i, c in enumerate([10, 8, 5, 4, 3, 1, 0])
        ]
        assert _compute_h_index(pubs) == 4  # 4 papers with ≥4 citations

    def test_h_index_zero(self):
        pubs = [Publication(title="P", citations=0)]
        assert _compute_h_index(pubs) == 0

    def test_h_index_all_high(self):
        pubs = [Publication(title=f"P{i}", citations=100) for i in range(5)]
        assert _compute_h_index(pubs) == 5
