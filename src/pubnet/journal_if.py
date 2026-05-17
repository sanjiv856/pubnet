"""Journal impact factor lookup.

Lookup order:
    1. Bundled Scimago CSV (offline, fast, 255 journals)
    2. OpenAlex API fallback (online, always current)
    3. None if both miss

Usage:
    lookup = JournalIFLookup()
    if_value = lookup.get("Nature Medicine")          # → 82.9
    all_ifs = lookup.enrich_publications(publications) # → dict[venue, IF]
"""

from __future__ import annotations

import csv
import logging
import re
from pathlib import Path

from pubnet.models import Publication

logger = logging.getLogger(__name__)

SCIMAGO_PATH = Path(__file__).parent / "data" / "scimago.csv"


class JournalIFLookup:
    """Journal impact factor lookup with Scimago CSV + OpenAlex fallback."""

    def __init__(self, scimago_path: Path | str | None = None):
        self._scimago_path = Path(scimago_path) if scimago_path else SCIMAGO_PATH
        self._scimago: dict[str, float] | None = None  # lazy loaded
        self._scimago_raw: dict[str, str] | None = None  # normalised → original name
        self._cache: dict[str, float | None] = {}      # query cache

    # ------------------------------------------------------------------
    # Scimago CSV
    # ------------------------------------------------------------------

    def _load_scimago(self) -> dict[str, float]:
        """Load and index the Scimago CSV. Lazy, called once."""
        if self._scimago is not None:
            return self._scimago

        self._scimago = {}
        self._scimago_raw = {}
        if not self._scimago_path.exists():
            logger.warning("Scimago CSV not found at %s", self._scimago_path)
            return self._scimago

        try:
            with open(self._scimago_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("title", "").strip()
                    try:
                        sjr = float(row.get("sjr", 0) or 0)
                    except (ValueError, TypeError):
                        sjr = 0.0
                    if name and sjr > 0:
                        key = _normalise_venue(name)
                        self._scimago[key] = sjr
                        self._scimago_raw[key] = name
            logger.info("Loaded %d journals from Scimago CSV", len(self._scimago))
        except Exception as exc:
            logger.warning("Error loading Scimago CSV: %s", exc)

        return self._scimago

    def _lookup_scimago(self, venue: str) -> float | None:
        """Exact + fuzzy match against Scimago data."""
        scimago = self._load_scimago()
        if not scimago:
            return None

        key = _normalise_venue(venue)

        # Exact match
        if key in scimago:
            return scimago[key]

        # Substring/contains match: "biological crystallography" is contained
        # within "acta crystallographica section d biological crystallography"
        # Pick the best (shortest) containing key to avoid overly broad matches
        containing = []
        for csv_key in scimago:
            if key in csv_key or csv_key in key:
                containing.append(csv_key)
        if containing:
            # Prefer the key whose length is closest to the query
            best = min(containing, key=lambda k: abs(len(k) - len(key)))
            logger.debug(
                "Substring matched %r → %r",
                venue, self._scimago_raw.get(best, best),
            )
            return scimago[best]

        # Fuzzy matching with strict safeguards
        try:
            from rapidfuzz import fuzz, process

            # Use token_sort_ratio for better handling of word order differences
            result = process.extractOne(
                key,
                scimago.keys(),
                scorer=fuzz.token_sort_ratio,
                score_cutoff=90,  # Higher threshold to prevent false matches
            )
            if result:
                matched_key, score, _ = result

                # Length ratio check: reject if lengths are too different
                # This prevents "crystallography" from matching "nature"
                len_ratio = min(len(key), len(matched_key)) / max(len(key), len(matched_key))
                if len_ratio < 0.5:
                    logger.debug(
                        "Rejected fuzzy match %r → %r (score=%.0f%%, len_ratio=%.2f)",
                        venue, self._scimago_raw.get(matched_key, matched_key),
                        score, len_ratio,
                    )
                    return None

                # Word overlap check: at least one significant word must match
                query_words = set(key.split()) - {"of", "the", "and", "in", "for", "a", "an"}
                match_words = set(matched_key.split()) - {"of", "the", "and", "in", "for", "a", "an"}
                overlap = query_words & match_words
                if not overlap and len(query_words) > 1:
                    logger.debug(
                        "Rejected fuzzy match %r → %r (no word overlap)",
                        venue, self._scimago_raw.get(matched_key, matched_key),
                    )
                    return None

                logger.debug(
                    "Fuzzy matched %r → %r (%.0f%%)",
                    venue, self._scimago_raw.get(matched_key, matched_key), score,
                )
                return scimago[matched_key]
        except ImportError:
            pass

        return None

    # ------------------------------------------------------------------
    # OpenAlex API
    # ------------------------------------------------------------------

    def _lookup_openalex(self, venue: str) -> float | None:
        """Look up a journal via the OpenAlex API."""
        try:
            import requests
        except ImportError:
            logger.warning("requests not installed - cannot query OpenAlex")
            return None

        try:
            resp = requests.get(
                "https://api.openalex.org/sources",
                params={"search": venue, "per_page": 1},
                timeout=10,
                headers={"User-Agent": "PubNet/0.1 (mailto:drsanjivk@gmail.com)"},
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if not results:
                return None

            source = results[0]
            # OpenAlex provides 'summary_stats' with '2yr_mean_citedness'
            summary = source.get("summary_stats", {})
            citedness = summary.get("2yr_mean_citedness")
            if citedness and citedness > 0:
                return round(citedness, 1)

            # No reliable fallback - cited_by_count / works_count is a
            # lifetime ratio, not a 2-year IF, and produces wildly
            # inflated numbers for discontinued or long-running journals.
            # Return None rather than a misleading value.
            logger.debug(
                "OpenAlex: no 2yr_mean_citedness for %r (works=%d, cited=%d), skipping",
                venue, source.get("works_count", 0), source.get("cited_by_count", 0),
            )

        except Exception as exc:
            logger.debug("OpenAlex lookup failed for %r: %s", venue, exc)

        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, venue: str) -> float | None:
        """Look up impact factor for a journal/venue name.

        Returns:
            Impact factor (float) or None if not found.
        """
        if not venue or venue == "Unknown":
            return None

        # Check cache first
        if venue in self._cache:
            return self._cache[venue]

        # Try Scimago
        result = self._lookup_scimago(venue)

        # Try OpenAlex fallback
        if result is None:
            result = self._lookup_openalex(venue)

        self._cache[venue] = result
        return result

    def enrich_publications(
        self,
        publications: list[Publication],
    ) -> dict[str, float | None]:
        """Look up IFs for all unique venues in a publication list.

        Returns:
            dict mapping venue name → IF (or None).
        """
        venues = {p.venue for p in publications if p.venue and p.venue != "Unknown"}
        result = {}
        for venue in sorted(venues):
            result[venue] = self.get(venue)

        found = sum(1 for v in result.values() if v is not None)
        logger.info("IF lookup: %d/%d venues resolved", found, len(venues))
        return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_venue(name: str) -> str:
    """Normalise a venue name for matching."""
    name = name.lower().strip()
    # Remove common prefixes/suffixes
    for prefix in ("the ", "journal of ", "proceedings of "):
        if name.startswith(prefix):
            name = name[len(prefix):]
    # Remove punctuation
    name = "".join(c for c in name if c.isalnum() or c == " ")
    return " ".join(name.split())
