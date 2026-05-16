"""Core data models for PubNet.

All data flows through these Pydantic models:
  Scholar API → Author (with Publications) → Analysis modules → Renderers
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Primary data models
# ---------------------------------------------------------------------------

class Publication(BaseModel):
    """A single scholarly publication."""

    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    citations: int = 0
    abstract: str | None = None
    url: str | None = None
    publisher: str | None = None
    # Enriched later by analysis modules
    impact_factor: float | None = None
    cluster_id: int | None = None


class Author(BaseModel):
    """A Scholar author profile with their publications."""

    name: str
    scholar_id: str
    affiliation: str | None = None
    email_domain: str | None = None
    interests: list[str] = Field(default_factory=list)
    h_index: int | None = None
    i10_index: int | None = None
    total_citations: int = 0
    url_picture: str | None = None
    publications: list[Publication] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Analysis result models
# ---------------------------------------------------------------------------

class CoauthorEdge(BaseModel):
    """An edge in the co-author network graph."""

    source: str
    target: str
    weight: int = 1  # number of shared papers
    papers: list[str] = Field(default_factory=list)  # shared paper titles


class CoauthorNode(BaseModel):
    """A node in the co-author network graph."""

    name: str
    paper_count: int = 0
    total_citations: int = 0
    is_ego: bool = False  # True for the profile author


class CoauthorGraph(BaseModel):
    """Complete co-author network analysis result."""

    nodes: list[CoauthorNode] = Field(default_factory=list)
    edges: list[CoauthorEdge] = Field(default_factory=list)
    total_coauthors: int = 0
    avg_coauthors_per_paper: float = 0.0


class CitationYear(BaseModel):
    """Citation data for a single year."""

    year: int
    citation_count: int = 0
    publication_count: int = 0
    cumulative_h_index: int = 0


class CitationTrends(BaseModel):
    """Citation trend analysis result."""

    yearly: list[CitationYear] = Field(default_factory=list)
    first_year: int | None = None
    last_year: int | None = None


class TopicCluster(BaseModel):
    """A topic cluster from TF-IDF + k-means."""

    cluster_id: int
    keywords: list[str] = Field(default_factory=list)  # top N terms
    publication_indices: list[int] = Field(default_factory=list)
    total_citations: int = 0
    publication_count: int = 0


class TopicAnalysis(BaseModel):
    """Complete topic clustering result."""

    clusters: list[TopicCluster] = Field(default_factory=list)
    num_clusters: int = 0


class StatsSummary(BaseModel):
    """Summary statistics for the author profile."""

    total_publications: int = 0
    total_citations: int = 0
    h_index: int = 0
    i10_index: int = 0
    years_active: str = ""  # e.g. "2015–2025"
    first_pub_year: int | None = None
    last_pub_year: int | None = None
    top_venue: str | None = None
    top_venue_count: int = 0
    unique_coauthors: int = 0
    avg_impact_factor: float | None = None
    avg_citations_per_paper: float = 0.0


class AnalysisResult(BaseModel):
    """Container for all analysis outputs. Passed to renderers."""

    author: Author
    stats: StatsSummary = Field(default_factory=StatsSummary)
    coauthor_graph: CoauthorGraph = Field(default_factory=CoauthorGraph)
    citation_trends: CitationTrends = Field(default_factory=CitationTrends)
    topic_analysis: TopicAnalysis = Field(default_factory=TopicAnalysis)
    impact_factors: dict[str, float | None] = Field(default_factory=dict)
