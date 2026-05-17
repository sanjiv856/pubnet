"""Shared test fixtures for PubNet."""

import pytest
from pubnet.models import Author, Publication


@pytest.fixture
def sample_publications() -> list[Publication]:
    """A small set of publications for testing."""
    return [
        Publication(
            title="Machine learning for clinical prediction",
            authors=["Alice Smith", "Bob Jones", "Carol White"],
            year=2023,
            venue="Nature Medicine",
            citations=150,
            abstract="We develop ML models for clinical outcome prediction.",
        ),
        Publication(
            title="Deep learning in medical imaging",
            authors=["Alice Smith", "David Brown"],
            year=2022,
            venue="Radiology",
            citations=80,
            abstract="Deep neural networks for automated radiology.",
        ),
        Publication(
            title="Genomic biomarkers of treatment response",
            authors=["Alice Smith", "Bob Jones", "Eve Green"],
            year=2023,
            venue="Cell",
            citations=200,
            abstract="Whole-genome sequencing reveals biomarkers.",
        ),
        Publication(
            title="Single-cell analysis of tumor immunity",
            authors=["Alice Smith", "Carol White", "Frank Lee"],
            year=2021,
            venue="Science",
            citations=300,
            abstract="scRNA-seq of tumor-infiltrating lymphocytes.",
        ),
        Publication(
            title="Natural language processing for EHR data",
            authors=["Alice Smith", "Eve Green"],
            year=2024,
            venue="Nature Medicine",
            citations=30,
            abstract="NLP methods for extracting clinical information.",
        ),
    ]


@pytest.fixture
def sample_author(sample_publications) -> Author:
    """A sample author with publications."""
    return Author(
        name="Alice Smith",
        scholar_id="TEST123",
        affiliation="Test University",
        h_index=4,
        i10_index=3,
        total_citations=760,
        publications=sample_publications,
    )


@pytest.fixture
def duplicate_publications() -> list[Publication]:
    """Publications with near-duplicate titles for dedup testing."""
    return [
        Publication(
            title="Machine learning for clinical prediction models",
            authors=["Alice Smith"],
            year=2023,
            venue="Nature Medicine",
            citations=150,
        ),
        Publication(
            title="Machine Learning for Clinical Prediction Models",
            authors=["Alice Smith"],
            year=2023,
            venue="Nature Medicine",
            citations=100,  # lower citations - should be removed
        ),
        Publication(
            title="Deep learning in medical imaging analysis",
            authors=["Alice Smith"],
            year=2022,
            venue="Radiology",
            citations=80,
        ),
    ]
