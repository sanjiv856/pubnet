"""Tests for Pydantic data models."""

import json
import pytest

from pubnet.models import (
    Author, Publication, AnalysisResult, StatsSummary,
    CoauthorEdge, CoauthorNode, CoauthorGraph,
    CitationYear, CitationTrends,
    TopicCluster, TopicAnalysis,
)


class TestPublication:
    def test_defaults(self):
        pub = Publication(title="Test paper")
        assert pub.title == "Test paper"
        assert pub.authors == []
        assert pub.year is None
        assert pub.citations == 0
        assert pub.abstract is None
        assert pub.impact_factor is None
        assert pub.cluster_id is None

    def test_full(self):
        pub = Publication(
            title="Test paper", authors=["A", "B"], year=2023,
            venue="Nature", citations=100, abstract="An abstract",
            url="https://example.com", publisher="Springer",
            impact_factor=42.8, cluster_id=2,
        )
        assert pub.year == 2023
        assert len(pub.authors) == 2
        assert pub.impact_factor == 42.8

    def test_serialization_roundtrip(self):
        pub = Publication(title="RT Test", authors=["X"], year=2024, citations=50)
        restored = Publication(**pub.model_dump())
        assert restored.title == pub.title
        assert restored.citations == pub.citations

    def test_json_roundtrip(self):
        pub = Publication(title="JSON Test", year=2023, venue="Cell")
        restored = Publication.model_validate_json(pub.model_dump_json())
        assert restored.venue == "Cell"


class TestAuthor:
    def test_with_publications(self):
        pubs = [Publication(title=f"Paper {i}") for i in range(3)]
        author = Author(name="Test", scholar_id="ABC123", publications=pubs)
        assert len(author.publications) == 3
        assert author.total_citations == 0

    def test_defaults(self):
        author = Author(name="Min", scholar_id="X")
        assert author.affiliation is None
        assert author.interests == []
        assert author.h_index is None
        assert author.publications == []

    def test_serialisation_roundtrip(self):
        author = Author(
            name="Test Author", scholar_id="XYZ789", h_index=10,
            affiliation="MIT", interests=["ML", "NLP"],
            publications=[Publication(title="Paper 1", year=2023, citations=50)],
        )
        restored = Author.model_validate_json(author.model_dump_json())
        assert restored.name == author.name
        assert len(restored.publications) == 1
        assert restored.publications[0].citations == 50
        assert restored.affiliation == "MIT"

    def test_full_profile(self):
        author = Author(
            name="Full", scholar_id="FULL", affiliation="Stanford",
            email_domain="stanford.edu", interests=["AI", "Robotics"],
            h_index=25, i10_index=40, total_citations=5000,
            url_picture="https://example.com/pic.jpg",
        )
        assert author.email_domain == "stanford.edu"
        assert author.total_citations == 5000


class TestCoauthorModels:
    def test_coauthor_edge(self):
        edge = CoauthorEdge(source="A", target="B", weight=3, papers=["p1", "p2", "p3"])
        assert edge.weight == 3
        assert len(edge.papers) == 3

    def test_coauthor_edge_defaults(self):
        edge = CoauthorEdge(source="A", target="B")
        assert edge.weight == 1
        assert edge.papers == []

    def test_coauthor_node(self):
        node = CoauthorNode(name="Alice", paper_count=5, total_citations=200, is_ego=True)
        assert node.is_ego is True

    def test_coauthor_node_defaults(self):
        node = CoauthorNode(name="Bob")
        assert node.paper_count == 0
        assert node.is_ego is False

    def test_coauthor_graph(self):
        graph = CoauthorGraph(
            nodes=[CoauthorNode(name="A"), CoauthorNode(name="B")],
            edges=[CoauthorEdge(source="A", target="B")],
            total_coauthors=1, avg_coauthors_per_paper=1.0,
        )
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1

    def test_coauthor_graph_empty(self):
        graph = CoauthorGraph()
        assert graph.total_coauthors == 0
        assert graph.nodes == []

    def test_coauthor_graph_roundtrip(self):
        graph = CoauthorGraph(
            nodes=[CoauthorNode(name="X", paper_count=3)],
            edges=[CoauthorEdge(source="X", target="Y", weight=2)],
            total_coauthors=1,
        )
        restored = CoauthorGraph(**json.loads(graph.model_dump_json()))
        assert restored.nodes[0].name == "X"
        assert restored.edges[0].weight == 2


class TestCitationModels:
    def test_citation_year(self):
        cy = CitationYear(year=2023, citation_count=50, publication_count=3, cumulative_h_index=5)
        assert cy.year == 2023

    def test_citation_year_defaults(self):
        cy = CitationYear(year=2020)
        assert cy.citation_count == 0
        assert cy.cumulative_h_index == 0

    def test_citation_trends(self):
        trends = CitationTrends(
            yearly=[CitationYear(year=2022), CitationYear(year=2023)],
            first_year=2022, last_year=2023,
        )
        assert len(trends.yearly) == 2
        assert trends.first_year == 2022

    def test_citation_trends_empty(self):
        trends = CitationTrends()
        assert trends.yearly == []
        assert trends.first_year is None


class TestTopicModels:
    def test_topic_cluster(self):
        cluster = TopicCluster(
            cluster_id=0, keywords=["ml", "deep", "learning"],
            publication_indices=[0, 3, 7], total_citations=500, publication_count=3,
        )
        assert cluster.cluster_id == 0
        assert len(cluster.keywords) == 3

    def test_topic_cluster_defaults(self):
        cluster = TopicCluster(cluster_id=1)
        assert cluster.keywords == []
        assert cluster.total_citations == 0

    def test_topic_analysis(self):
        topics = TopicAnalysis(
            clusters=[TopicCluster(cluster_id=0), TopicCluster(cluster_id=1)],
            num_clusters=2,
        )
        assert topics.num_clusters == 2

    def test_topic_analysis_empty(self):
        topics = TopicAnalysis()
        assert topics.clusters == []
        assert topics.num_clusters == 0


class TestStatsSummary:
    def test_defaults(self):
        stats = StatsSummary()
        assert stats.total_publications == 0
        assert stats.h_index == 0
        assert stats.avg_impact_factor is None

    def test_full(self):
        stats = StatsSummary(
            total_publications=27, total_citations=4547, h_index=18,
            i10_index=20, years_active="2020-2024", first_pub_year=2020,
            last_pub_year=2024, top_venue="Nature Medicine", top_venue_count=5,
            unique_coauthors=42, avg_impact_factor=15.3, avg_citations_per_paper=168.4,
        )
        assert stats.top_venue == "Nature Medicine"
        assert stats.avg_citations_per_paper == 168.4

    def test_roundtrip(self):
        stats = StatsSummary(total_publications=10, h_index=5)
        restored = StatsSummary(**stats.model_dump())
        assert restored.total_publications == 10


class TestAnalysisResult:
    def test_defaults(self):
        author = Author(name="Test", scholar_id="ABC")
        result = AnalysisResult(author=author)
        assert result.stats.total_publications == 0
        assert result.coauthor_graph.total_coauthors == 0
        assert result.citation_trends.yearly == []
        assert result.topic_analysis.clusters == []
        assert result.impact_factors == {}

    def test_full_construction(self):
        author = Author(name="Full", scholar_id="FULL")
        result = AnalysisResult(
            author=author,
            stats=StatsSummary(total_publications=10),
            coauthor_graph=CoauthorGraph(total_coauthors=5),
            citation_trends=CitationTrends(first_year=2020, last_year=2024),
            topic_analysis=TopicAnalysis(num_clusters=3),
            impact_factors={"Nature": 42.8},
        )
        assert result.stats.total_publications == 10
        assert result.impact_factors["Nature"] == 42.8

    def test_requires_author(self):
        with pytest.raises(Exception):
            AnalysisResult()

    def test_json_roundtrip(self):
        author = Author(name="RT", scholar_id="RT1")
        result = AnalysisResult(
            author=author,
            stats=StatsSummary(h_index=7),
            impact_factors={"Cell": 54.8},
        )
        restored = AnalysisResult.model_validate_json(result.model_dump_json())
        assert restored.author.name == "RT"
        assert restored.stats.h_index == 7
        assert restored.impact_factors["Cell"] == 54.8
