"""Tests for journal impact factor lookup."""

import pytest
from pathlib import Path

from pubnet.journal_if import JournalIFLookup, _normalise_venue
from pubnet.models import Publication


class TestNormaliseVenue:
    def test_lowercase(self):
        assert _normalise_venue("Nature Medicine") == "nature medicine"

    def test_strips_the(self):
        assert _normalise_venue("The Lancet") == "lancet"

    def test_strips_journal_of(self):
        assert _normalise_venue("Journal of Clinical Oncology") == "clinical oncology"

    def test_removes_punctuation(self):
        assert _normalise_venue("Cell Host & Microbe") == "cell host microbe"


class TestScimagoLookup:
    def test_exact_match(self):
        lookup = JournalIFLookup()
        val = lookup._lookup_scimago("Nature Medicine")
        assert val is not None
        assert val > 0

    def test_case_insensitive(self):
        lookup = JournalIFLookup()
        val = lookup._lookup_scimago("nature medicine")
        assert val is not None

    def test_unknown_journal(self):
        lookup = JournalIFLookup()
        val = lookup._lookup_scimago("Journal of Obscure Studies ZZZZZ")
        assert val is None

    def test_the_lancet(self):
        lookup = JournalIFLookup()
        val = lookup._lookup_scimago("The Lancet")
        assert val is not None
        assert val > 10


class TestGetWithCache:
    def test_caches_results(self):
        lookup = JournalIFLookup()
        val1 = lookup.get("Nature Medicine")
        val2 = lookup.get("Nature Medicine")
        assert val1 == val2

    def test_unknown_venue(self):
        lookup = JournalIFLookup()
        assert lookup.get("Unknown") is None

    def test_empty_venue(self):
        lookup = JournalIFLookup()
        assert lookup.get("") is None


class TestEnrichPublications:
    def test_returns_dict(self):
        lookup = JournalIFLookup()
        pubs = [
            Publication(title="P1", venue="Nature Medicine"),
            Publication(title="P2", venue="Cell"),
            Publication(title="P3", venue="Unknown"),
        ]
        result = lookup.enrich_publications(pubs)
        assert isinstance(result, dict)
        assert "Nature Medicine" in result
        assert "Cell" in result
        assert "Unknown" not in result  # filtered out

    def test_known_journals_have_values(self):
        lookup = JournalIFLookup()
        pubs = [Publication(title="P1", venue="Science")]
        result = lookup.enrich_publications(pubs)
        assert result["Science"] is not None
        assert result["Science"] > 0
