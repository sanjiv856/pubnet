"""Stat cards row — Publications, Citations, h-index, Co-authors, Avg IF."""

from __future__ import annotations

from dash import html


def make_stat_card(label: str, value: str | int | float) -> html.Div:
    """Create a single stat card."""
    return html.Div(
        [
            html.P(label, className="stat-label"),
            html.P(str(value), className="stat-val"),
        ],
        className="stat-card",
    )


def stat_cards_row(stats: dict | None = None) -> html.Div:
    """Build the stat cards row.

    Args:
        stats: dict with keys like total_publications, total_citations, etc.
              If None, shows placeholder dashes.
    """
    if stats is None:
        cards = [
            make_stat_card("Publications", "—"),
            make_stat_card("Total citations", "—"),
            make_stat_card("h-index", "—"),
            make_stat_card("Co-authors", "—"),
            make_stat_card("Avg. IF", "—"),
        ]
    else:
        cites = f"{stats.get('total_citations', 0):,}"
        avg_if = stats.get("avg_impact_factor")
        avg_if_str = f"{avg_if}" if avg_if else "—"
        cards = [
            make_stat_card("Publications", stats.get("total_publications", 0)),
            make_stat_card("Total citations", cites),
            make_stat_card("h-index", stats.get("h_index", 0)),
            make_stat_card("Co-authors", stats.get("unique_coauthors", 0)),
            make_stat_card("Avg. IF", avg_if_str),
        ]

    return html.Div(cards, className="stats-row", id="stat-cards")
