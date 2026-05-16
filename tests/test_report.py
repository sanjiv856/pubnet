"""Tests for the HTML report renderer."""

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
from pubnet.report import render_report, _build_network_html, _short_name
from pubnet.models import CoauthorGraph


class TestRenderReport:
    @pytest.fixture
    def full_report(self):
        """Generate a complete report from demo data."""
        author = load_demo()
        pubs = clean_publications(author.publications)
        if_lookup = JournalIFLookup()
        impact_factors = if_lookup.enrich_publications(pubs)
        graph = build_coauthor_graph(author, pubs)
        trends = compute_citation_trends(pubs)
        topics = cluster_topics(pubs, num_clusters=5)
        stats = compute_stats(author, pubs, impact_factors=impact_factors)

        return render_report(
            author=author,
            publications=pubs,
            stats=stats,
            coauthor_graph=graph,
            citation_trends=trends,
            topic_analysis=topics,
            impact_factors=impact_factors,
        )

    def test_is_valid_html(self, full_report):
        assert full_report.startswith("<!DOCTYPE html>")
        assert "</html>" in full_report

    def test_contains_author_name(self, full_report):
        assert "Sanjiv Kumar" in full_report

    def test_contains_stat_cards(self, full_report):
        assert "Publications" in full_report
        assert "Total Citations" in full_report
        assert "h-index" in full_report

    def test_contains_plotly_data(self, full_report):
        assert "CITATION_CHART_DATA" in full_report
        assert "CLUSTER_CHART_DATA" in full_report

    def test_contains_publications_json(self, full_report):
        assert "PUBLICATIONS" in full_report
        assert "REFERENCES" in full_report

    def test_contains_network_graph(self, full_report):
        assert "<svg" in full_report or "network" in full_report.lower()

    def test_contains_export_buttons(self, full_report):
        assert "exportJSON" in full_report
        assert "exportCSV" in full_report

    def test_report_size_reasonable(self, full_report):
        # Should be under 500KB without full Plotly embedded
        assert len(full_report) < 500_000


class TestNetworkHtml:
    def test_empty_graph(self):
        graph = CoauthorGraph()
        html = _build_network_html(graph, "Test")
        assert "No co-author data" in html

    def test_produces_svg(self, sample_author, sample_publications):
        from pubnet.analyze import build_coauthor_graph
        graph = build_coauthor_graph(sample_author, sample_publications)
        html = _build_network_html(graph, sample_author.name)
        assert "<svg" in html
        assert "circle" in html


class TestShortName:
    def test_two_names(self):
        assert _short_name("Alice Smith") == "A.S."

    def test_three_names(self):
        assert _short_name("Alice B Smith") == "A.B.S."

    def test_single_name(self):
        result = _short_name("Madonna")
        assert len(result) <= 8
