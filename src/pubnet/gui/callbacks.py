"""Dash callbacks — wire UI interactions to analysis modules.

Callback map:
    Analyze button  -> fetch profile -> store data -> update all views
    Sidebar nav     -> show/hide view panels
    Year range      -> filter pubs -> update charts + table
    Min citations   -> filter pubs -> update charts + table
    Ref format      -> re-render reference strings
    Sort buttons    -> re-sort publication table
    Network click   -> filter table by co-author
    Cluster click   -> filter table by cluster
    Export button   -> download JSON
"""

from __future__ import annotations

import json
import logging

from dash import Input, Output, State, callback, html, dcc, no_update, ctx
from dash.exceptions import PreventUpdate

logger = logging.getLogger(__name__)


def register_callbacks(app):
    """Register all callbacks on the Dash app."""

    # ------------------------------------------------------------------
    # 1. Analyze button -> fetch + analyse -> store results
    # ------------------------------------------------------------------
    @app.callback(
        Output("profile-store", "data"),
        Output("analysis-store", "data"),
        Input("analyze-btn", "n_clicks"),
        State("scholar-url-input", "value"),
        prevent_initial_call=False,
    )
    def on_analyze(n_clicks, scholar_url):
        from pubnet.fetch import fetch_profile, load_demo, FetchError
        from pubnet.analyze import (
            clean_publications,
            build_coauthor_graph,
            compute_citation_trends,
            cluster_topics,
            compute_stats,
        )
        from pubnet.journal_if import JournalIFLookup

        # On initial load (n_clicks=0 or None), always load demo.
        # Only fetch from Scholar when user explicitly clicks Analyze.
        if not n_clicks:
            try:
                author = load_demo()
            except FileNotFoundError:
                return no_update, no_update
        elif not scholar_url or not scholar_url.strip():
            try:
                author = load_demo()
            except FileNotFoundError:
                return no_update, no_update
        else:
            try:
                author = fetch_profile(scholar_url.strip())
            except Exception as exc:
                # Scholar fetching often fails on cloud servers (IP blocked).
                # Fall back to demo with a warning.
                logger.warning("Scholar fetch failed (%s), falling back to demo", exc)
                try:
                    author = load_demo()
                except FileNotFoundError:
                    return no_update, no_update

        # Clean
        pubs = clean_publications(author.publications)

        # Crossref enrichment (corrects venue names)
        try:
            from pubnet.crossref import enrich_publications as crossref_enrich
            cr_results = crossref_enrich(pubs, max_lookups=None)
            for idx, cr in cr_results.items():
                if cr.venue_corrected and pubs[idx].venue:
                    if cr.venue_corrected != pubs[idx].venue and len(cr.venue_corrected) > 3:
                        pubs[idx].venue = cr.venue_corrected
        except Exception as exc:
            logger.warning("Crossref enrichment failed: %s", exc)

        # Journal IF
        if_lookup = JournalIFLookup()
        impact_factors = if_lookup.enrich_publications(pubs)

        # Analyse
        graph = build_coauthor_graph(author, pubs)
        trends = compute_citation_trends(pubs)
        topics = cluster_topics(pubs, num_clusters=5)
        stats = compute_stats(author, pubs, impact_factors=impact_factors)

        # Serialize to JSON-safe dicts for dcc.Store
        profile_data = {
            "author": author.model_dump(),
            "publications": [p.model_dump() for p in pubs],
            "impact_factors": {k: v for k, v in impact_factors.items() if v is not None},
        }

        analysis_data = {
            "stats": stats.model_dump(),
            "coauthor_graph": graph.model_dump(),
            "citation_trends": trends.model_dump(),
            "topic_analysis": topics.model_dump(),
        }

        return profile_data, analysis_data

    # ------------------------------------------------------------------
    # 2. Store data -> update main content
    # ------------------------------------------------------------------
    @app.callback(
        Output("main-content", "children"),
        Input("profile-store", "data"),
        Input("analysis-store", "data"),
        Input("year-range", "value"),
        Input("min-citations", "value"),
        Input("ref-format", "value"),
        Input("current-sort", "data"),
        Input("current-filter-coauthor", "data"),
        Input("current-filter-cluster", "data"),
        Input("nav-all", "n_clicks"),
        Input("nav-network", "n_clicks"),
        Input("nav-trends", "n_clicks"),
        Input("nav-clusters", "n_clicks"),
        Input("nav-pubs", "n_clicks"),
    )
    def update_main(
        profile_data, analysis_data,
        year_range, min_citations, ref_format,
        sort_by, filter_coauthor, filter_cluster,
        nav_all, nav_network, nav_trends, nav_clusters, nav_pubs,
    ):
        from pubnet.models import (
            Publication, CoauthorGraph, CitationTrends,
            TopicAnalysis, StatsSummary,
        )
        from pubnet.gui.components.stat_cards import stat_cards_row
        from pubnet.gui.components.network import network_component
        from pubnet.gui.components.trends import trends_component
        from pubnet.gui.components.clusters import clusters_component
        from pubnet.gui.components.pub_table import pub_table_component
        from pubnet.gui.components.pubs_per_year import pubs_per_year_component

        if not profile_data or not analysis_data:
            return _empty_state()

        # Reconstruct models from store
        pubs = [Publication(**p) for p in profile_data["publications"]]
        impact_factors = profile_data.get("impact_factors", {})
        stats = StatsSummary(**analysis_data["stats"])
        graph = CoauthorGraph(**analysis_data["coauthor_graph"])
        trends = CitationTrends(**analysis_data["citation_trends"])
        topics = TopicAnalysis(**analysis_data["topic_analysis"])

        # Apply filters
        filtered = pubs
        if year_range:
            y_min, y_max = year_range
            filtered = [p for p in filtered if p.year and y_min <= p.year <= y_max]
        if min_citations and min_citations > 0:
            filtered = [p for p in filtered if p.citations >= min_citations]
        if filter_coauthor:
            filtered = [p for p in filtered if filter_coauthor in p.authors]
        if filter_cluster is not None:
            cluster_indices = set()
            for c in topics.clusters:
                if c.cluster_id == filter_cluster:
                    cluster_indices = set(c.publication_indices)
                    break
            if cluster_indices:
                filtered = [p for i, p in enumerate(pubs) if i in cluster_indices]

        # Determine which view is active
        active_view = _get_active_view()

        # Build author header card
        author_data = profile_data["author"]
        author_header = html.Div(
            [
                html.H1(author_data.get("name", "")),
                html.Div(
                    author_data.get("affiliation", "") or "",
                    className="affiliation",
                ),
                html.Div(
                    [html.Span(interest) for interest in (author_data.get("interests") or [])],
                    className="interests",
                ),
            ],
            className="author-header",
        )

        # Build stat cards (always visible)
        stat_row = stat_cards_row(stats.model_dump())

        # Build view components
        show_network = active_view in ("all", "network")
        show_trends = active_view in ("all", "trends")
        show_clusters = active_view in ("all", "clusters")
        show_pubs = active_view in ("all", "pubs")

        children = [author_header, stat_row]

        # Row 1: Network + Publications Per Year
        if show_network:
            children.append(
                html.Div(
                    [
                        network_component(graph),
                        pubs_per_year_component(trends),
                    ],
                    className="two-col",
                )
            )

        # Row 2: Citations Per Year + Topic Clusters
        if show_trends and show_clusters:
            children.append(
                html.Div(
                    [
                        trends_component(trends),
                        clusters_component(topics),
                    ],
                    className="two-col",
                )
            )
        else:
            if show_trends:
                children.append(trends_component(trends))
            if show_clusters:
                children.append(clusters_component(topics))

        if show_pubs:
            children.append(
                pub_table_component(filtered, impact_factors, ref_format or "apa", sort_by or "citations")
            )

        # Active filter info
        filter_info_parts = []
        if filter_coauthor:
            filter_info_parts.append("Co-author: %s" % filter_coauthor)
        if filter_cluster is not None:
            filter_info_parts.append("Cluster: %s" % filter_cluster)
        if len(filtered) < len(pubs):
            filter_info_parts.append("Showing %d/%d" % (len(filtered), len(pubs)))

        if filter_info_parts:
            children.append(
                html.Div(
                    [
                        html.Span(" / ".join(filter_info_parts), style={"fontSize": "11px", "color": "#8A7E75"}),
                        html.Button("Clear filters", id="clear-filters-btn", n_clicks=0, style={
                            "fontSize": "11px", "marginLeft": "8px", "padding": "2px 10px",
                            "borderRadius": "99px", "border": "1px solid #E2DCD6",
                            "background": "#fff", "cursor": "pointer", "color": "#5C4F46",
                        }),
                    ],
                    style={"marginTop": "8px", "display": "flex", "alignItems": "center"},
                )
            )

        return children

    # ------------------------------------------------------------------
    # 3. Sort buttons
    # ------------------------------------------------------------------
    @app.callback(
        Output("current-sort", "data"),
        Input("sort-citations", "n_clicks"),
        Input("sort-year", "n_clicks"),
        Input("sort-if", "n_clicks"),
        Input("sort-venue", "n_clicks"),
        prevent_initial_call=True,
    )
    def on_sort(n_cites, n_year, n_if, n_venue):
        triggered = ctx.triggered_id
        sort_map = {
            "sort-citations": "citations",
            "sort-year": "year",
            "sort-if": "if",
            "sort-venue": "venue",
        }
        return sort_map.get(triggered, "citations")

    # ------------------------------------------------------------------
    # 4. Network node click -> filter by co-author
    # ------------------------------------------------------------------
    @app.callback(
        Output("current-filter-coauthor", "data"),
        Input("network-graph", "tapNodeData"),
        prevent_initial_call=True,
    )
    def on_network_click(node_data):
        if not node_data:
            return None
        if node_data.get("is_ego"):
            return None
        return node_data.get("full_name")

    # ------------------------------------------------------------------
    # 4b. Network reset button -> fit view
    # ------------------------------------------------------------------
    @app.callback(
        Output("network-graph", "layout"),
        Input("network-reset-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def on_network_reset(n_clicks):
        return {"name": "cose", "animate": True, "randomize": False, "nodeRepulsion": 8000, "idealEdgeLength": 120, "fit": True}

    # ------------------------------------------------------------------
    # 5. Cluster chart click -> filter by cluster
    # ------------------------------------------------------------------
    @app.callback(
        Output("current-filter-cluster", "data"),
        Input("cluster-chart", "clickData"),
        prevent_initial_call=True,
    )
    def on_cluster_click(click_data):
        if not click_data or not click_data.get("points"):
            return None
        point = click_data["points"][0]
        return point.get("customdata")

    # ------------------------------------------------------------------
    # 6. Clear filters
    # ------------------------------------------------------------------
    @app.callback(
        Output("current-filter-coauthor", "data", allow_duplicate=True),
        Output("current-filter-cluster", "data", allow_duplicate=True),
        Input("clear-filters-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def on_clear_filters(n):
        return None, None

    # ------------------------------------------------------------------
    # 7. Sidebar nav -> update active class (client-side)
    # ------------------------------------------------------------------
    for nav_id in ["nav-all", "nav-network", "nav-trends", "nav-clusters", "nav-pubs"]:
        app.clientside_callback(
            """
            function(n) {
                var navs = document.querySelectorAll('.nav-item');
                navs.forEach(function(el) { el.classList.remove('active'); });
                var el = document.getElementById('%s');
                if (el) el.classList.add('active');
                return window.dash_clientside.no_update;
            }
            """ % nav_id,
            Output(nav_id, "className"),
            Input(nav_id, "n_clicks"),
            prevent_initial_call=True,
        )

    # ------------------------------------------------------------------
    # 8. Export -> download JSON
    # ------------------------------------------------------------------
    @app.callback(
        Output("export-download", "data"),
        Input("export-json-btn", "n_clicks"),
        Input("export-csv-btn", "n_clicks"),
        State("profile-store", "data"),
        prevent_initial_call=True,
    )
    def on_export(n_json, n_csv, profile_data):
        if not profile_data:
            raise PreventUpdate

        triggered = ctx.triggered_id
        pubs = profile_data["publications"]
        impact_factors = profile_data.get("impact_factors", {})

        if triggered == "export-csv-btn":
            # Build CSV string
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Title", "Authors", "Year", "Venue", "Citations", "Impact Factor"])
            for p in pubs:
                writers_str = "; ".join(p.get("authors", []))
                venue = p.get("venue", "")
                if_val = impact_factors.get(venue, "")
                writer.writerow([
                    p.get("title", ""),
                    writers_str,
                    p.get("year", ""),
                    venue,
                    p.get("citations", 0),
                    if_val if if_val else "",
                ])
            return dcc.send_string(output.getvalue(), filename="pubnet_publications.csv")

        # Default: JSON export
        return dcc.send_string(
            json.dumps(pubs, indent=2),
            filename="pubnet_publications.json",
        )

    # ------------------------------------------------------------------
    # 9. Year range auto-update based on data
    # ------------------------------------------------------------------
    @app.callback(
        Output("year-range", "min"),
        Output("year-range", "max"),
        Output("year-range", "value"),
        Output("year-range", "marks"),
        Input("profile-store", "data"),
    )
    def update_year_range(profile_data):
        if not profile_data:
            return 2000, 2026, [2000, 2026], {2000: "2000", 2026: "2026"}

        years = [p["year"] for p in profile_data["publications"] if p.get("year")]
        if not years:
            return 2000, 2026, [2000, 2026], {2000: "2000", 2026: "2026"}

        y_min = min(years)
        y_max = max(years)
        span = y_max - y_min
        # Adaptive step: avoid cramped marks in narrow sidebar
        if span > 20:
            step = 10
        elif span > 10:
            step = 5
        else:
            step = 2
        marks = {y: str(y) for y in range(y_min, y_max + 1) if y % step == 0}
        marks[y_min] = str(y_min)
        marks[y_max] = str(y_max)
        return y_min, y_max, [y_min, y_max], marks


# Placeholder URL - update after creating the GitHub repo
GITHUB_URL = "https://github.com/sanjiv856/pubnet"


def _get_active_view():
    """Determine which view to show based on which nav was last clicked."""
    triggered = ctx.triggered_id
    view_map = {
        "nav-all": "all",
        "nav-network": "network",
        "nav-trends": "trends",
        "nav-clusters": "clusters",
        "nav-pubs": "pubs",
    }
    return view_map.get(triggered, "all")


def _empty_state():
    """Welcome panel shown before a profile is loaded."""
    from pubnet.gui.components.stat_cards import stat_cards_row
    return [
        html.Div(
            [
                html.H1("Welcome to PubNet",
                         style={"fontFamily": "'Libre Baskerville', Georgia, serif",
                                "fontSize": "22px", "fontWeight": "700",
                                "color": "#2C2420", "marginBottom": "8px"}),
                html.P(
                    "PubNet analyses Google Scholar profiles to generate interactive "
                    "co-author networks, citation trends, topic clusters, journal impact "
                    "factors, and formatted references.",
                    style={"fontSize": "13px", "color": "#5C4F46", "marginBottom": "12px",
                           "lineHeight": "1.6"}),
                html.Div([
                    html.Span("How to use: ", style={"fontWeight": "600", "color": "#6B4C3B"}),
                    html.Span(
                        "Paste a Google Scholar profile URL in the bar above and click Analyze. "
                        "Or just click Analyze to see a demo.",
                        style={"color": "#5C4F46"}),
                ], style={"fontSize": "12px", "marginBottom": "12px"}),
                html.A(
                    "View on GitHub",
                    href=GITHUB_URL,
                    target="_blank",
                    style={"fontSize": "12px", "color": "#6B4C3B", "fontWeight": "500",
                           "textDecoration": "none", "borderBottom": "1px solid #D4CEC7"},
                ),
            ],
            className="author-header",
        ),
        stat_cards_row(),
    ]
