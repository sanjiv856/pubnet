"""Tests for reference formatters."""

import pytest
from pubnet.models import Publication
from pubnet.formatters import format_reference, format_all, STYLES


@pytest.fixture
def sample_pub() -> Publication:
    return Publication(
        title="Machine learning for clinical prediction",
        authors=["Alice Smith", "Bob Jones", "Carol White"],
        year=2023,
        venue="Nature Medicine",
        citations=150,
    )


class TestFormatReference:
    def test_all_styles_produce_output(self, sample_pub):
        for style in STYLES:
            ref = format_reference(sample_pub, style)
            assert len(ref) > 20
            assert "Machine learning" in ref or "machine" in ref.lower()

    def test_invalid_style_raises(self, sample_pub):
        with pytest.raises(ValueError, match="Unknown style"):
            format_reference(sample_pub, "invalid_style")

    def test_apa_format(self, sample_pub):
        ref = format_reference(sample_pub, "apa")
        assert "(2023)" in ref
        assert "Smith" in ref
        assert "*Nature Medicine*" in ref

    def test_mla_format(self, sample_pub):
        ref = format_reference(sample_pub, "mla")
        assert "Smith, Alice" in ref
        assert "2023" in ref

    def test_bibtex_format(self, sample_pub):
        ref = format_reference(sample_pub, "bibtex")
        assert ref.startswith("@article{")
        assert "title={" in ref
        assert "author={" in ref
        assert "Alice Smith and Bob Jones and Carol White" in ref

    def test_vancouver_format(self, sample_pub):
        ref = format_reference(sample_pub, "vancouver")
        assert "Smith A" in ref or "Smith AS" in ref
        assert "2023" in ref

    def test_chicago_format(self, sample_pub):
        ref = format_reference(sample_pub, "chicago")
        assert "Smith, Alice" in ref
        assert "2023" in ref


class TestFormatAll:
    def test_returns_all_styles(self, sample_pub):
        result = format_all(sample_pub)
        assert set(result.keys()) == set(STYLES)
        for style, ref in result.items():
            assert len(ref) > 10


class TestEdgeCases:
    def test_single_author(self):
        pub = Publication(title="Solo paper", authors=["Alice Smith"], year=2023)
        ref = format_reference(pub, "apa")
        assert "Smith" in ref

    def test_no_year(self):
        pub = Publication(title="Timeless paper", authors=["Alice Smith"])
        ref = format_reference(pub, "apa")
        assert "n.d." in ref

    def test_no_venue(self):
        pub = Publication(title="Homeless paper", authors=["Alice Smith"], year=2023)
        ref = format_reference(pub, "apa")
        assert "Nature" not in ref  # no venue should be included

    def test_no_authors(self):
        pub = Publication(title="Anonymous paper", year=2023)
        ref = format_reference(pub, "apa")
        assert "Unknown" in ref

    def test_many_authors_apa(self):
        authors = [f"Author {chr(65 + i)}" for i in range(25)]
        pub = Publication(title="Crowd paper", authors=authors, year=2023)
        ref = format_reference(pub, "apa")
        assert "..." in ref  # APA truncates after 20
