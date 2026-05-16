"""Crossref API integration for publication enrichment.

Uses the free Crossref REST API (no key required) to:
- Look up DOIs for publications
- Get correct/canonical venue (journal) names
- Retrieve additional metadata (ISSN, publisher, type, etc.)

API docs: https://api.crossref.org/swagger-ui/index.html
Etiquette: https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/

Rate limits: be polite — include mailto in User-Agent, 50 req/s max.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import requests

from pubnet.models import Publication

logger = logging.getLogger(__name__)

# Crossref REST API base
_BASE = "https://api.crossref.org"

# Polite pool: include contact email for priority access
_HEADERS = {
    "User-Agent": "PubNet/0.1.0 (mailto:pubnet@example.com; https://github.com/pubnet)",
}

# Delay between requests to be polite (seconds)
_REQUEST_DELAY = 0.15


@dataclass
class CrossrefResult:
    """Enrichment data from Crossref for a single publication."""
    doi: str | None = None
    venue_corrected: str | None = None
    publisher: str | None = None
    issn: str | None = None
    pub_type: str | None = None
    url: str | None = None
    subject: list[str] | None = None


def lookup_publication(pub: Publication) -> CrossrefResult | None:
    """Look up a publication on Crossref by title + author.

    Returns CrossrefResult with enrichment data, or None if not found.
    """
    if not pub.title:
        return None

    # Build query: title + first author last name for better matching
    query = pub.title
    if pub.authors:
        # Use first author's last name
        first_author = pub.authors[0]
        last_name = first_author.split()[-1] if first_author else ""
        if last_name:
            query = f"{pub.title} {last_name}"

    params = {
        "query": query,
        "rows": 3,
        "select": "DOI,title,container-title,publisher,ISSN,type,URL,subject",
    }

    try:
        resp = requests.get(
            f"{_BASE}/works",
            params=params,
            headers=_HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Crossref lookup failed for '%s': %s", pub.title[:50], exc)
        return None

    items = data.get("message", {}).get("items", [])
    if not items:
        return None

    # Find best match by title similarity
    best = _find_best_match(pub.title, items)
    if not best:
        return None

    # Extract fields
    container = best.get("container-title", [])
    venue = container[0] if container else None
    issns = best.get("ISSN", [])

    return CrossrefResult(
        doi=best.get("DOI"),
        venue_corrected=venue,
        publisher=best.get("publisher"),
        issn=issns[0] if issns else None,
        pub_type=best.get("type"),
        url=best.get("URL"),
        subject=best.get("subject"),
    )


def enrich_publications(
    publications: list[Publication],
    delay: float = _REQUEST_DELAY,
    max_lookups: int | None = None,
) -> dict[int, CrossrefResult]:
    """Enrich a list of publications with Crossref data.

    Args:
        publications: List of publications to enrich.
        delay: Delay between API calls (seconds).
        max_lookups: Maximum number of lookups (None = all).

    Returns:
        Dict mapping publication index to CrossrefResult.
    """
    results = {}
    count = 0

    for i, pub in enumerate(publications):
        if max_lookups is not None and count >= max_lookups:
            break

        result = lookup_publication(pub)
        if result:
            results[i] = result
            count += 1

            # Update venue if Crossref has a better name
            if result.venue_corrected and pub.venue:
                old_venue = pub.venue
                # Only update if the Crossref venue looks like a real journal name
                if len(result.venue_corrected) > 3:
                    logger.info(
                        "Crossref venue correction: '%s' -> '%s'",
                        old_venue, result.venue_corrected,
                    )

        if delay > 0 and i < len(publications) - 1:
            time.sleep(delay)

    logger.info("Crossref enrichment: %d/%d publications matched", len(results), len(publications))
    return results


def _find_best_match(title: str, items: list[dict]) -> dict | None:
    """Find the best matching item from Crossref results."""
    title_lower = title.lower().strip()

    for item in items:
        item_titles = item.get("title", [])
        for it in item_titles:
            if not it:
                continue
            it_lower = it.lower().strip()
            # Check for high overlap
            if _title_similarity(title_lower, it_lower) > 0.85:
                return item

    return None


def _title_similarity(a: str, b: str) -> float:
    """Simple word-overlap similarity between two titles."""
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)
