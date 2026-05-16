"""Reference formatters for PubNet.

Supported styles: APA, MLA, BibTeX, Vancouver, Chicago.

Usage:
    ref = format_reference(publication, style="apa")
"""

from __future__ import annotations

import re
import unicodedata

from pubnet.models import Publication


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

STYLES = ("apa", "mla", "bibtex", "vancouver", "chicago")


def format_reference(pub: Publication, style: str = "apa") -> str:
    """Format a publication as a reference string.

    Args:
        pub: Publication to format.
        style: One of "apa", "mla", "bibtex", "vancouver", "chicago".

    Returns:
        Formatted reference string.
    """
    style = style.lower().strip()
    formatter = _FORMATTERS.get(style)
    if formatter is None:
        raise ValueError(f"Unknown style {style!r}. Choose from: {', '.join(STYLES)}")
    return formatter(pub)


def format_all(pub: Publication) -> dict[str, str]:
    """Return the publication formatted in every supported style."""
    return {style: format_reference(pub, style) for style in STYLES}


# ---------------------------------------------------------------------------
# Individual formatters
# ---------------------------------------------------------------------------

def _format_apa(pub: Publication) -> str:
    """APA 7th edition format.

    Author, A. A., & Author, B. B. (Year). Title. *Venue*, etc.
    """
    authors = _apa_authors(pub.authors)
    year = f"({pub.year})" if pub.year else "(n.d.)"
    title = pub.title
    venue = f"*{pub.venue}*" if pub.venue and pub.venue != "Unknown" else ""

    parts = [f"{authors} {year}. {title}."]
    if venue:
        parts.append(venue + ".")

    return " ".join(parts)


def _format_mla(pub: Publication) -> str:
    """MLA 9th edition format.

    Author(s). "Title." *Venue*, year.
    """
    authors = _mla_authors(pub.authors)
    title = f'"{pub.title}."'
    venue = f"*{pub.venue}*," if pub.venue and pub.venue != "Unknown" else ""
    year = str(pub.year) if pub.year else "n.d."

    parts = [authors + "."]
    parts.append(title)
    if venue:
        parts.append(venue)
    parts.append(year + ".")

    return " ".join(parts)


def _format_bibtex(pub: Publication) -> str:
    """BibTeX format.

    @article{key, title={...}, author={...}, year={...}, journal={...}}
    """
    key = _bibtex_key(pub)
    authors_str = " and ".join(pub.authors) if pub.authors else "Unknown"

    lines = [f"@article{{{key},"]
    lines.append(f"  title={{{pub.title}}},")
    lines.append(f"  author={{{authors_str}}},")
    if pub.year:
        lines.append(f"  year={{{pub.year}}},")
    if pub.venue and pub.venue != "Unknown":
        lines.append(f"  journal={{{pub.venue}}},")
    lines.append("}")
    return "\n".join(lines)


def _format_vancouver(pub: Publication) -> str:
    """Vancouver (ICMJE) format.

    Author AA, Author BB. Title. Venue. Year.
    """
    authors = _vancouver_authors(pub.authors)
    year = str(pub.year) if pub.year else "n.d.";
    venue = pub.venue if pub.venue and pub.venue != "Unknown" else ""

    parts = [f"{authors}. {pub.title}."]
    if venue:
        parts.append(f"{venue}.")
    parts.append(f"{year}.")

    return " ".join(parts)


def _format_chicago(pub: Publication) -> str:
    """Chicago Manual of Style (author-date) format.

    Author, First. Year. "Title." *Venue*.
    """
    authors = _chicago_authors(pub.authors)
    year = str(pub.year) if pub.year else "n.d."
    title = f'"{pub.title}."'
    venue = f"*{pub.venue}*." if pub.venue and pub.venue != "Unknown" else ""

    parts = [f"{authors}. {year}. {title}"]
    if venue:
        parts.append(venue)

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Author name formatting helpers
# ---------------------------------------------------------------------------

def _apa_authors(authors: list[str]) -> str:
    """APA: Last, F. M., & Last, F. M. (truncate after 20 with ...)"""
    if not authors:
        return "Unknown"
    formatted = [_last_initials(a) for a in authors]
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]}, & {formatted[1]}"
    if len(formatted) > 20:
        return ", ".join(formatted[:19]) + ", ... " + formatted[-1]
    return ", ".join(formatted[:-1]) + ", & " + formatted[-1]


def _mla_authors(authors: list[str]) -> str:
    """MLA: Last, First, and First Last."""
    if not authors:
        return "Unknown"
    if len(authors) == 1:
        return _last_first(authors[0])
    if len(authors) == 2:
        return f"{_last_first(authors[0])}, and {authors[1]}"
    return f"{_last_first(authors[0])}, et al"


def _vancouver_authors(authors: list[str]) -> str:
    """Vancouver: Last AA, Last BB. Truncate after 6 with et al."""
    if not authors:
        return "Unknown"
    formatted = [_last_initials_no_dots(a) for a in authors]
    if len(formatted) > 6:
        return ", ".join(formatted[:6]) + ", et al"
    return ", ".join(formatted)


def _chicago_authors(authors: list[str]) -> str:
    """Chicago: Last, First. Truncate after 10 with et al."""
    if not authors:
        return "Unknown"
    if len(authors) == 1:
        return _last_first(authors[0])
    formatted = [_last_first(authors[0])]
    for a in authors[1:10]:
        formatted.append(a)
    if len(authors) > 10:
        formatted.append("et al")
    if len(formatted) == 2:
        return " and ".join(formatted)
    return ", ".join(formatted[:-1]) + ", and " + formatted[-1]


def _last_initials(name: str) -> str:
    """Convert 'First Middle Last' → 'Last, F. M.'"""
    parts = name.strip().split()
    if len(parts) == 1:
        return parts[0]
    last = parts[-1]
    initials = " ".join(f"{p[0]}." for p in parts[:-1])
    return f"{last}, {initials}"


def _last_initials_no_dots(name: str) -> str:
    """Convert 'First Middle Last' → 'Last FM' (Vancouver style)."""
    parts = name.strip().split()
    if len(parts) == 1:
        return parts[0]
    last = parts[-1]
    initials = "".join(p[0] for p in parts[:-1])
    return f"{last} {initials}"


def _last_first(name: str) -> str:
    """Convert 'First Last' → 'Last, First'."""
    parts = name.strip().split()
    if len(parts) == 1:
        return parts[0]
    return f"{parts[-1]}, {' '.join(parts[:-1])}"


def _bibtex_key(pub: Publication) -> str:
    """Generate a BibTeX citation key: lastauthor_year_firstword."""
    last = "unknown"
    if pub.authors:
        parts = pub.authors[0].strip().split()
        last = _ascii_lower(parts[-1]) if parts else "unknown"
    year = str(pub.year) if pub.year else "nd"
    # First significant word of title (skip articles)
    words = pub.title.lower().split()
    skip = {"a", "an", "the", "of", "in", "on", "for", "and", "to"}
    first_word = next((w for w in words if w not in skip), "untitled")
    first_word = re.sub(r"[^a-z0-9]", "", first_word)
    return f"{last}_{year}_{first_word}"


def _ascii_lower(s: str) -> str:
    """Convert to lowercase ASCII (strip accents)."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


# ---------------------------------------------------------------------------
# Formatter dispatch table
# ---------------------------------------------------------------------------

_FORMATTERS = {
    "apa": _format_apa,
    "mla": _format_mla,
    "bibtex": _format_bibtex,
    "vancouver": _format_vancouver,
    "chicago": _format_chicago,
}
