"""Tests for the Scholar fetcher and cache."""

import json
import pytest
from pathlib import Path

from pubnet.fetch import parse_scholar_id, load_demo, _scholarly_to_publication


class TestParseScholarId:
    def test_bare_id(self):
        assert parse_scholar_id("ML7X29AAAAAJ") == "ML7X29AAAAAJ"

    def test_full_url(self):
        url = "https://scholar.google.com/citations?user=ML7X29AAAAAJ"
        assert parse_scholar_id(url) == "ML7X29AAAAAJ"

    def test_url_with_hl(self):
        url = "https://scholar.google.com/citations?user=ML7X29AAAAAJ&hl=en"
        assert parse_scholar_id(url) == "ML7X29AAAAAJ"

    def test_url_with_extra_params(self):
        url = "https://scholar.google.com/citations?hl=en&user=ML7X29AAAAAJ&oi=ao"
        assert parse_scholar_id(url) == "ML7X29AAAAAJ"

    def test_whitespace_stripped(self):
        assert parse_scholar_id("  ML7X29AAAAAJ  ") == "ML7X29AAAAAJ"

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_scholar_id("not a valid id or url at all !!!")


class TestLoadDemo:
    def test_load_demo_returns_author(self):
        author = load_demo()
        assert author.name == "Sanjiv Kumar"
        assert author.scholar_id == "ML7X29AAAAAJ"
        assert len(author.publications) == 27

    def test_demo_publications_have_titles(self):
        author = load_demo()
        for pub in author.publications:
            assert pub.title
            assert len(pub.title) > 5

    def test_demo_has_citations(self):
        author = load_demo()
        assert author.total_citations > 0
        assert any(p.citations > 100 for p in author.publications)


class TestScholarlyConversion:
    def test_basic_conversion(self):
        raw = {
            "bib": {
                "title": "Test Paper",
                "author": "Alice Smith and Bob Jones",
                "pub_year": "2023",
                "venue": "Nature",
                "abstract": "An abstract.",
            },
            "num_citations": 42,
            "pub_url": "https://example.com/paper",
        }
        pub = _scholarly_to_publication(raw)
        assert pub.title == "Test Paper"
        assert pub.authors == ["Alice Smith", "Bob Jones"]
        assert pub.year == 2023
        assert pub.venue == "Nature"
        assert pub.citations == 42
        assert pub.abstract == "An abstract."

    def test_missing_fields(self):
        raw = {"bib": {"title": "Minimal"}, "num_citations": 0}
        pub = _scholarly_to_publication(raw)
        assert pub.title == "Minimal"
        assert pub.authors == []
        assert pub.year is None
        assert pub.venue is None

    def test_invalid_year(self):
        raw = {"bib": {"title": "Bad year", "pub_year": "forthcoming"}}
        pub = _scholarly_to_publication(raw)
        assert pub.year is None
