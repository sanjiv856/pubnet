"""Scholar profile fetcher with local JSON cache.

Usage:
    author = fetch_profile("https://scholar.google.com/citations?user=ML7X29AAAAAJ")
    author = fetch_profile("ML7X29AAAAAJ")  # author ID directly
    author = load_demo()                     # bundled demo data
"""

from __future__ import annotations

import json
import logging
import random
import re
import time
from pathlib import Path

from pydantic import ValidationError

from pubnet.models import Author, Publication

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CACHE_DIR = Path.home() / ".pubnet" / "cache"
DEMO_DATA_PATH = Path(__file__).parent / "data" / "demo.json"

# Regex to extract author ID from a Scholar URL
_SCHOLAR_URL_RE = re.compile(r"[?&]user=([A-Za-z0-9_-]+)")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class FetchError(Exception):
    """Base exception for fetch errors."""


class ScholarBlockedError(FetchError):
    """Raised when Google Scholar blocks our request."""


class ProfileNotFoundError(FetchError):
    """Raised when the author profile cannot be found."""


# ---------------------------------------------------------------------------
# URL / ID parsing
# ---------------------------------------------------------------------------

def parse_scholar_id(url_or_id: str) -> str:
    """Extract a Scholar author ID from a URL or return the ID directly.

    Accepts:
        "ML7X29AAAAAJ"
        "https://scholar.google.com/citations?user=ML7X29AAAAAJ"
        "https://scholar.google.com/citations?user=ML7X29AAAAAJ&hl=en"
    """
    url_or_id = url_or_id.strip()
    match = _SCHOLAR_URL_RE.search(url_or_id)
    if match:
        return match.group(1)
    # Assume it's a bare author ID if it looks like one (alphanumeric, 12 chars)
    if re.match(r"^[A-Za-z0-9_-]{8,16}$", url_or_id):
        return url_or_id
    raise ValueError(
        f"Cannot parse Scholar author ID from: {url_or_id!r}. "
        "Provide a Google Scholar profile URL or a bare author ID."
    )


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------

def _cache_path(scholar_id: str) -> Path:
    return CACHE_DIR / f"{scholar_id}.json"


def _read_cache(scholar_id: str) -> Author | None:
    path = _cache_path(scholar_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Author.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning("Cache file corrupt for %s, ignoring: %s", scholar_id, exc)
        return None


def _write_cache(author: Author) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(author.scholar_id)
    path.write_text(author.model_dump_json(indent=2), encoding="utf-8")
    logger.info("Cached profile to %s", path)


def list_cached_profiles() -> list[dict[str, str]]:
    """Return a list of cached profile summaries."""
    profiles = []
    if not CACHE_DIR.exists():
        return profiles
    for path in CACHE_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            profiles.append({
                "scholar_id": data.get("scholar_id", path.stem),
                "name": data.get("name", "Unknown"),
                "publications": str(len(data.get("publications", []))),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return profiles


def clear_cache() -> int:
    """Delete all cached profiles. Returns number of files removed."""
    if not CACHE_DIR.exists():
        return 0
    count = 0
    for path in CACHE_DIR.glob("*.json"):
        path.unlink()
        count += 1
    return count


# ---------------------------------------------------------------------------
# Scholar fetching via SerpAPI (works on cloud servers)
# ---------------------------------------------------------------------------

def _fetch_from_serpapi(scholar_id: str) -> Author:
    """Fetch a profile from Google Scholar using SerpAPI.

    Requires SERPAPI_KEY environment variable or google-search-results package.
    Works on cloud servers where direct Scholar scraping is blocked.
    """
    import os
    api_key = os.environ.get("SERPAPI_KEY") or os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        raise FetchError("No SERPAPI_KEY environment variable set")

    try:
        from serpapi import GoogleSearch
    except ImportError:
        raise FetchError(
            "The 'google-search-results' package is required for SerpAPI. "
            "Install with: pip install google-search-results"
        )

    logger.info("Fetching Scholar profile via SerpAPI: %s", scholar_id)

    # Step 1: Get author info
    params = {
        "engine": "google_scholar_author",
        "author_id": scholar_id,
        "api_key": api_key,
        "num": 100,
    }
    search = GoogleSearch(params)
    results = search.get_dict()

    if "error" in results:
        raise FetchError(f"SerpAPI error: {results['error']}")

    author_info = results.get("author", {})
    cited_by = results.get("cited_by", {})
    table = cited_by.get("table", [])

    # Parse h-index and i10-index from the table
    h_index = None
    i10_index = None
    for row in table:
        if "h_index" in row:
            h_index = _safe_int(row["h_index"].get("all"))
        if "i10_index" in row:
            i10_index = _safe_int(row["i10_index"].get("all"))

    # Step 2: Get publications (SerpAPI returns them with the author query)
    articles = results.get("articles", [])
    publications = []
    for art in articles:
        authors_str = art.get("authors", "")
        authors = [a.strip() for a in authors_str.split(",") if a.strip()]
        publications.append(Publication(
            title=art.get("title", "Untitled"),
            authors=authors,
            year=_safe_int(art.get("year")),
            venue=art.get("publication") or None,
            citations=art.get("cited_by", {}).get("value", 0),
            url=art.get("link") or None,
        ))

    # Check for additional pages of articles
    while "next" in results.get("serpapi_pagination", {}):
        next_url = results["serpapi_pagination"]["next"]
        # Extract start parameter
        import urllib.parse
        parsed = urllib.parse.urlparse(next_url)
        qs = urllib.parse.parse_qs(parsed.query)
        params["start"] = qs.get("start", [str(len(publications))])[0]
        search = GoogleSearch(params)
        results = search.get_dict()
        for art in results.get("articles", []):
            authors_str = art.get("authors", "")
            authors = [a.strip() for a in authors_str.split(",") if a.strip()]
            publications.append(Publication(
                title=art.get("title", "Untitled"),
                authors=authors,
                year=_safe_int(art.get("year")),
                venue=art.get("publication") or None,
                citations=art.get("cited_by", {}).get("value", 0),
                url=art.get("link") or None,
            ))

    return Author(
        name=author_info.get("name", "Unknown"),
        scholar_id=scholar_id,
        affiliation=author_info.get("affiliations"),
        interests=[i.get("title", "") for i in author_info.get("interests", [])],
        h_index=h_index,
        i10_index=i10_index,
        total_citations=cited_by.get("table", [{}])[0].get("citations", {}).get("all", 0) if table else 0,
        url_picture=author_info.get("thumbnail"),
        publications=publications,
    )


# ---------------------------------------------------------------------------
# Scholar fetching via `scholarly` (direct scraping, works locally)
# ---------------------------------------------------------------------------

def _scholarly_to_publication(pub_dict: dict) -> Publication:
    """Convert a scholarly publication dict to our Publication model."""
    bib = pub_dict.get("bib", {})
    return Publication(
        title=bib.get("title", "Untitled"),
        authors=[a.strip() for a in bib.get("author", "").split(" and ") if a.strip()],
        year=_safe_int(bib.get("pub_year")),
        venue=bib.get("venue") or bib.get("journal") or bib.get("conference") or None,
        citations=pub_dict.get("num_citations", 0),
        abstract=bib.get("abstract") or None,
        url=pub_dict.get("pub_url") or pub_dict.get("eprint_url") or None,
        publisher=bib.get("publisher") or None,
    )


def _safe_int(val) -> int | None:
    """Safely convert a value to int, returning None on failure."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _fetch_from_scholarly(scholar_id: str) -> Author:
    """Fetch a profile from Google Scholar using the scholarly library."""
    try:
        from scholarly import scholarly
    except ImportError as exc:
        raise FetchError(
            "The 'scholarly' library is required for live Scholar fetching. "
            "Install it with: pip install scholarly"
        ) from exc

    logger.info("Fetching Scholar profile: %s", scholar_id)

    try:
        author_gen = scholarly.search_author_id(scholar_id)
    except Exception as exc:
        if "blocked" in str(exc).lower() or "captcha" in str(exc).lower():
            raise ScholarBlockedError(
                f"Google Scholar blocked the request for {scholar_id}. "
                "Try again later or use --builtin for demo data."
            ) from exc
        raise ProfileNotFoundError(f"Could not find profile: {scholar_id}") from exc

    if author_gen is None:
        raise ProfileNotFoundError(f"No profile found for ID: {scholar_id}")

    # Fill in all publication details
    try:
        author_data = scholarly.fill(author_gen, sections=["basics", "indices", "publications"])
    except Exception as exc:
        if "blocked" in str(exc).lower():
            raise ScholarBlockedError(str(exc)) from exc
        raise FetchError(f"Error filling profile data: {exc}") from exc

    # Rate-limit: random delay before fetching individual publications
    publications = []
    raw_pubs = author_data.get("publications", [])
    for i, pub in enumerate(raw_pubs):
        try:
            filled_pub = scholarly.fill(pub)
            publications.append(_scholarly_to_publication(filled_pub))
        except Exception as exc:
            logger.warning("Skipping publication %d: %s", i, exc)
            # Still include with basic info
            publications.append(_scholarly_to_publication(pub))

        # Random delay between 1-3 seconds to avoid rate limiting
        if i < len(raw_pubs) - 1:
            delay = random.uniform(1.0, 3.0)
            logger.debug("Rate limit delay: %.1fs", delay)
            time.sleep(delay)

    return Author(
        name=author_data.get("name", "Unknown"),
        scholar_id=scholar_id,
        affiliation=author_data.get("affiliation"),
        email_domain=author_data.get("email_domain"),
        interests=author_data.get("interests", []),
        h_index=author_data.get("hindex"),
        i10_index=author_data.get("i10index"),
        total_citations=author_data.get("citedby", 0),
        url_picture=author_data.get("url_picture"),
        publications=publications,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_profile(
    url_or_id: str,
    *,
    use_cache: bool = True,
) -> Author:
    """Fetch a Scholar profile by URL or author ID.

    Args:
        url_or_id: Google Scholar profile URL or bare author ID.
        use_cache: If True (default), return cached data when available.

    Returns:
        Author model with publications.

    Raises:
        FetchError: On network or parsing errors.
        ProfileNotFoundError: If the profile doesn't exist.
        ScholarBlockedError: If Scholar blocks the request.
    """
    scholar_id = parse_scholar_id(url_or_id)

    if use_cache:
        cached = _read_cache(scholar_id)
        if cached is not None:
            logger.info("Loaded cached profile: %s (%d pubs)", cached.name, len(cached.publications))
            return cached

    # Try SerpAPI first (works on cloud servers), fall back to scholarly
    import os
    if os.environ.get("SERPAPI_KEY") or os.environ.get("SERPAPI_API_KEY"):
        try:
            author = _fetch_from_serpapi(scholar_id)
            _write_cache(author)
            return author
        except Exception as exc:
            logger.warning("SerpAPI fetch failed, trying scholarly: %s", exc)

    author = _fetch_from_scholarly(scholar_id)
    _write_cache(author)
    return author


def load_demo() -> Author:
    """Load the bundled demo profile (no network required).

    Returns:
        Author model from data/demo.json.

    Raises:
        FileNotFoundError: If demo.json is missing (shouldn't happen in installed package).
    """
    if not DEMO_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Demo data not found at {DEMO_DATA_PATH}. "
            "The package may be improperly installed."
        )
    data = json.loads(DEMO_DATA_PATH.read_text(encoding="utf-8"))
    return Author.model_validate(data)
