"""Analysis modules for PubNet.

Each public function is a pure function:
    (list[Publication], **config) → AnalysisResult

Modules:
    - clean_publications: dedup, null-fill, normalise
    - build_coauthor_graph: network analysis
    - compute_citation_trends: yearly aggregation + rolling h-index
    - cluster_topics: TF-IDF + k-means
    - compute_stats: summary statistics
"""

from __future__ import annotations

import logging
import re
from collections import Counter

from pubnet.models import (
    Author,
    CitationTrends,
    CitationYear,
    CoauthorEdge,
    CoauthorGraph,
    CoauthorNode,
    Publication,
    StatsSummary,
    TopicAnalysis,
    TopicCluster,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data cleaning
# ---------------------------------------------------------------------------

def clean_publications(publications: list[Publication]) -> list[Publication]:
    """Clean and deduplicate a list of publications.

    Steps:
        1. Fuzzy title dedup (rapidfuzz, threshold 90)
        2. Null-fill missing years/venues
        3. Normalise author names
        4. Sort by year descending (most recent first)
    """
    pubs = [p.model_copy() for p in publications]  # don't mutate originals
    pubs = _dedup_titles(pubs)
    pubs = _fill_missing(pubs)
    pubs = _normalise_authors(pubs)
    pubs.sort(key=lambda p: (p.year or 0, p.citations), reverse=True)
    return pubs


def _dedup_titles(pubs: list[Publication]) -> list[Publication]:
    """Remove near-duplicate publications by fuzzy title matching.

    When two titles are >90% similar, keep the one with more citations.
    """
    try:
        from rapidfuzz import fuzz
    except ImportError:
        logger.warning("rapidfuzz not installed - skipping dedup")
        return pubs

    if len(pubs) <= 1:
        return pubs

    keep = []
    removed_indices: set[int] = set()

    for i, pub_a in enumerate(pubs):
        if i in removed_indices:
            continue
        best = pub_a
        for j in range(i + 1, len(pubs)):
            if j in removed_indices:
                continue
            pub_b = pubs[j]
            ratio = fuzz.ratio(
                _normalise_title(pub_a.title),
                _normalise_title(pub_b.title),
            )
            if ratio > 90:
                # Keep the one with more citations
                if pub_b.citations > best.citations:
                    best = pub_b
                removed_indices.add(j)
                logger.debug("Dedup: %r ≈ %r (%.0f%%)", pub_a.title, pub_b.title, ratio)
        keep.append(best)

    if removed_indices:
        logger.info("Dedup removed %d duplicate(s) from %d publications", len(removed_indices), len(pubs))
    return keep


def _normalise_title(title: str) -> str:
    """Lowercase, strip punctuation for fuzzy comparison."""
    return re.sub(r"[^a-z0-9\s]", "", title.lower()).strip()


def _fill_missing(pubs: list[Publication]) -> list[Publication]:
    """Fill None values with sensible defaults."""
    result = []
    for pub in pubs:
        updates = {}
        if pub.venue is None:
            updates["venue"] = "Unknown"
        # Strip whitespace from venue
        if pub.venue and pub.venue.strip() == "":
            updates["venue"] = "Unknown"
        # Year stays None - analysis modules handle it
        if updates:
            pub = pub.model_copy(update=updates)
        result.append(pub)
    return result


def _normalise_authors(pubs: list[Publication]) -> list[Publication]:
    """Normalise author name formats for consistency.

    Strips extra whitespace. More aggressive normalisation (e.g., merging
    "J. Smith" and "John Smith") would need a name-matching heuristic that
    risks false positives, so we keep it simple for now.
    """
    result = []
    for pub in pubs:
        cleaned = [_clean_author_name(a) for a in pub.authors if a.strip()]
        if cleaned != pub.authors:
            pub = pub.model_copy(update={"authors": cleaned})
        result.append(pub)
    return result


def _clean_author_name(name: str) -> str:
    """Clean up a single author name."""
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    # Remove trailing/leading punctuation
    name = name.strip(".,;:")
    return name


# ---------------------------------------------------------------------------
# Co-author graph
# ---------------------------------------------------------------------------

def build_coauthor_graph(
    author: Author,
    publications: list[Publication],
) -> CoauthorGraph:
    """Build a co-author network graph.

    Nodes are people. Edges connect anyone who co-authored at least one paper.
    Edge weight = number of shared papers.
    """
    ego_name = author.name
    edge_map: dict[tuple[str, str], list[str]] = {}
    author_papers: Counter[str] = Counter()
    author_citations: Counter[str] = Counter()

    for pub in publications:
        authors = pub.authors
        if not authors:
            continue

        for a in authors:
            author_papers[a] += 1
            author_citations[a] += pub.citations

        # Build edges between ego and each co-author
        for a in authors:
            if a == ego_name:
                continue
            key = tuple(sorted([ego_name, a]))
            if key not in edge_map:
                edge_map[key] = []
            edge_map[key].append(pub.title)

        # Build edges between co-authors (not just ego-centric)
        non_ego = [a for a in authors if a != ego_name]
        for i, a in enumerate(non_ego):
            for b in non_ego[i + 1:]:
                key = tuple(sorted([a, b]))
                if key not in edge_map:
                    edge_map[key] = []
                edge_map[key].append(pub.title)

    # Build node list
    all_authors = set()
    for a, b in edge_map:
        all_authors.add(a)
        all_authors.add(b)
    all_authors.add(ego_name)

    nodes = [
        CoauthorNode(
            name=name,
            paper_count=author_papers.get(name, 0),
            total_citations=author_citations.get(name, 0),
            is_ego=(name == ego_name),
        )
        for name in sorted(all_authors)
    ]

    edges = [
        CoauthorEdge(source=a, target=b, weight=len(papers), papers=papers)
        for (a, b), papers in edge_map.items()
    ]

    # Compute average co-authors per paper
    coauthor_counts = [len(p.authors) - 1 for p in publications if len(p.authors) > 1]
    avg = sum(coauthor_counts) / len(coauthor_counts) if coauthor_counts else 0.0

    return CoauthorGraph(
        nodes=nodes,
        edges=edges,
        total_coauthors=len(all_authors) - 1,  # exclude ego
        avg_coauthors_per_paper=round(avg, 1),
    )


# ---------------------------------------------------------------------------
# Citation trends
# ---------------------------------------------------------------------------

def compute_citation_trends(publications: list[Publication]) -> CitationTrends:
    """Aggregate citations and publications by year, with rolling h-index."""
    pubs_with_year = [p for p in publications if p.year is not None]
    if not pubs_with_year:
        return CitationTrends()

    years = sorted({p.year for p in pubs_with_year})
    first_year, last_year = years[0], years[-1]

    yearly = []
    for year in range(first_year, last_year + 1):
        year_pubs = [p for p in pubs_with_year if p.year == year]
        cumulative_pubs = [p for p in pubs_with_year if p.year <= year]

        yearly.append(CitationYear(
            year=year,
            citation_count=sum(p.citations for p in year_pubs),
            publication_count=len(year_pubs),
            cumulative_h_index=_compute_h_index(cumulative_pubs),
        ))

    return CitationTrends(
        yearly=yearly,
        first_year=first_year,
        last_year=last_year,
    )


def _compute_h_index(publications: list[Publication]) -> int:
    """Compute h-index: largest h such that h papers have ≥ h citations."""
    cites = sorted([p.citations for p in publications], reverse=True)
    h = 0
    for i, c in enumerate(cites):
        if c >= i + 1:
            h = i + 1
        else:
            break
    return h


# ---------------------------------------------------------------------------
# Topic clustering
# ---------------------------------------------------------------------------

def cluster_topics(
    publications: list[Publication],
    num_clusters: int = 5,
) -> TopicAnalysis:
    """Cluster publications by topic using TF-IDF + k-means.

    Falls back gracefully to title-only if abstracts are missing.
    """
    try:
        from sklearn.cluster import KMeans
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        logger.warning("scikit-learn not installed - skipping topic clustering")
        return TopicAnalysis()

    if len(publications) < num_clusters:
        num_clusters = max(1, len(publications))

    # Build text corpus: title + abstract (or title only)
    corpus = []
    valid_indices = []
    for i, pub in enumerate(publications):
        text = pub.title
        if pub.abstract:
            text = f"{pub.title}. {pub.abstract}"
        if text.strip():
            corpus.append(text)
            valid_indices.append(i)

    if len(corpus) < 2:
        return TopicAnalysis()

    # Adjust num_clusters if we have fewer documents
    num_clusters = min(num_clusters, len(corpus))

    vectorizer = TfidfVectorizer(
        max_features=500,
        stop_words="english",
        max_df=0.85,
        min_df=1,
    )
    tfidf_matrix = vectorizer.fit_transform(corpus)
    feature_names = vectorizer.get_feature_names_out()

    kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(tfidf_matrix)

    # Extract top keywords per cluster from centroids
    clusters = []
    for cid in range(num_clusters):
        centroid = kmeans.cluster_centers_[cid]
        top_indices = centroid.argsort()[-5:][::-1]
        keywords = [feature_names[idx] for idx in top_indices]

        pub_indices = [valid_indices[i] for i, label in enumerate(labels) if label == cid]
        total_cites = sum(publications[idx].citations for idx in pub_indices)

        clusters.append(TopicCluster(
            cluster_id=cid,
            keywords=keywords,
            publication_indices=pub_indices,
            total_citations=total_cites,
            publication_count=len(pub_indices),
        ))

    return TopicAnalysis(clusters=clusters, num_clusters=num_clusters)


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

def compute_stats(
    author: Author,
    publications: list[Publication],
    impact_factors: dict[str, float | None] | None = None,
) -> StatsSummary:
    """Compute summary statistics for the profile."""
    years = [p.year for p in publications if p.year is not None]
    first_year = min(years) if years else None
    last_year = max(years) if years else None

    # Top venue by publication count
    venue_counts = Counter(p.venue for p in publications if p.venue and p.venue != "Unknown")
    top_venue, top_venue_count = venue_counts.most_common(1)[0] if venue_counts else (None, 0)

    # Unique co-authors
    all_coauthors = set()
    for pub in publications:
        for a in pub.authors:
            if a != author.name:
                all_coauthors.add(a)

    # Average impact factor (from enriched data)
    avg_if = None
    if impact_factors:
        known_ifs = [v for v in impact_factors.values() if v is not None]
        if known_ifs:
            avg_if = round(sum(known_ifs) / len(known_ifs), 1)

    total_cites = sum(p.citations for p in publications)
    years_str = ""
    if first_year and last_year:
        years_str = f"{first_year}-{last_year}" if first_year != last_year else str(first_year)

    return StatsSummary(
        total_publications=len(publications),
        total_citations=total_cites,
        h_index=author.h_index or _compute_h_index(publications),
        i10_index=author.i10_index or sum(1 for p in publications if p.citations >= 10),
        years_active=years_str,
        first_pub_year=first_year,
        last_pub_year=last_year,
        top_venue=top_venue,
        top_venue_count=top_venue_count,
        unique_coauthors=len(all_coauthors),
        avg_impact_factor=avg_if,
        avg_citations_per_paper=round(total_cites / len(publications), 1) if publications else 0.0,
    )
