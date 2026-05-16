"""Sortable publication table component — warm academic palette."""

from __future__ import annotations

from dash import html, dcc

from pubnet.models import Publication
from pubnet.formatters import format_reference


def _if_badge_class(if_val: float | None) -> str:
    """Return badge CSS class based on impact factor value."""
    if if_val is None:
        return ""
    if if_val >= 10:
        return "badge badge-if-high"
    return "badge badge-if"


def _truncate_authors(authors: list[str], max_shown: int = 4) -> str:
    """Truncate author list for display."""
    if not authors:
        return ""
    if len(authors) <= max_shown:
        return ", ".join(authors)
    return ", ".join(authors[:max_shown]) + " et al."


def build_pub_row(
    pub: Publication,
    impact_factors: dict[str, float | None],
    ref_format: str = "apa",
    index: int = 0,
) -> html.Div:
    """Build a single publication row."""
    if_val = impact_factors.get(pub.venue or "") if impact_factors else None

    badges = [
        html.Span(f"{pub.citations:,} citations", className="badge badge-cites"),
    ]
    if pub.venue and pub.venue != "Unknown":
        badges.append(html.Span(pub.venue, className="badge badge-venue"))
    if if_val is not None:
        badges.append(html.Span(f"IF {if_val}", className=_if_badge_class(if_val)))

    # Reference text
    try:
        ref_text = format_reference(pub, style=ref_format)
    except Exception:
        ref_text = pub.title

    # Author line
    author_line = _truncate_authors(pub.authors)

    children = [
        html.Span(str(pub.year or "n.d."), className="pub-year"),
        html.Div(
            [
                html.Div(pub.title, className="pub-title"),
                html.Div(author_line, className="pub-authors") if author_line else None,
                html.Div(badges, className="pub-meta"),
                html.Div(
                    [
                        html.Div(ref_text, className="ref-text"),
                        html.Button(
                            "Copy Reference",
                            className="copy-btn",
                            id={"type": "copy-btn", "index": index},
                            **{"data-ref": ref_text},
                        ),
                    ],
                    className="pub-ref",
                    id={"type": "pub-ref", "index": index},
                ),
            ],
            className="pub-info",
        ),
    ]
    # Filter out None children
    children = [c for c in children if c is not None]

    return html.Div(
        children,
        className="pub-row",
        id={"type": "pub-row", "index": index},
    )


def pub_table_component(
    publications: list[Publication] | None = None,
    impact_factors: dict[str, float | None] | None = None,
    ref_format: str = "apa",
    sort_by: str = "citations",
) -> html.Div:
    """Build the full publications panel with sort buttons and rows."""
    pubs = publications or []
    ifs = impact_factors or {}

    # Sort
    pubs = _sort_pubs(pubs, sort_by, ifs)

    rows = [
        build_pub_row(pub, ifs, ref_format, i)
        for i, pub in enumerate(pubs)
    ]

    sort_buttons = html.Div(
        [
            html.Button("Citations", className=f"sort-btn {'active' if sort_by == 'citations' else ''}", id="sort-citations"),
            html.Button("Year", className=f"sort-btn {'active' if sort_by == 'year' else ''}", id="sort-year"),
            html.Button("IF", className=f"sort-btn {'active' if sort_by == 'if' else ''}", id="sort-if"),
            html.Button("Journal", className=f"sort-btn {'active' if sort_by == 'venue' else ''}", id="sort-venue"),
        ],
        className="sort-buttons",
    )

    search_box = dcc.Input(
        id="pub-search",
        type="text",
        placeholder="Search title, author, or journal...",
        className="search-box",
        debounce=True,
    )

    pub_count = html.Span(str(len(pubs)), className="pub-count")

    return html.Div(
        [
            html.Div(
                [
                    html.P(
                        ["Publications ", pub_count],
                        className="panel-title",
                        style={"margin": "0", "border": "none", "padding": "0"},
                    ),
                    html.Div(
                        [search_box, sort_buttons],
                        style={"display": "flex", "gap": "10px", "alignItems": "center"},
                    ),
                ],
                className="pub-controls",
            ),
            html.Div(rows, id="pub-rows"),
        ],
        className="panel",
        id="pub-table-panel",
    )


def _sort_pubs(
    pubs: list[Publication],
    sort_by: str,
    impact_factors: dict[str, float | None],
) -> list[Publication]:
    """Sort publications by the given key."""
    if sort_by == "citations":
        return sorted(pubs, key=lambda p: p.citations, reverse=True)
    elif sort_by == "year":
        return sorted(pubs, key=lambda p: p.year or 0, reverse=True)
    elif sort_by == "if":
        return sorted(pubs, key=lambda p: impact_factors.get(p.venue or "", 0) or 0, reverse=True)
    elif sort_by == "venue":
        return sorted(pubs, key=lambda p: (p.venue or "").lower())
    return pubs
