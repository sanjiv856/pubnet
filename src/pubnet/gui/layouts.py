"""Dash page layout - topbar, sidebar, main panel.

Academic/professional design with warm tones, serif headings, card-based layout.
"""

from __future__ import annotations

from dash import dcc, html
from dash.development.base_component import Component

from pubnet.gui.components.stat_cards import stat_cards_row
from pubnet.gui.components.network import network_component
from pubnet.gui.components.trends import trends_component
from pubnet.gui.components.clusters import clusters_component
from pubnet.gui.components.pub_table import pub_table_component


def _inject_css(css: str) -> Component:
    """Inject raw CSS using an html.Div with a <style> tag via Markdown.

    Works across Dash versions (html.Style may not exist in older versions).
    """
    try:
        return html.Style(css)
    except AttributeError:
        # Fallback for older Dash: use dcc.Markdown with dangerously_allow_html
        return dcc.Markdown(
            f"<style>{css}</style>",
            dangerously_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Custom CSS - academic/professional warm palette
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Inter:wght@400;500;600&display=swap');

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  margin: 0;
  background: #F5F0EB;
  color: #2C2420;
  -webkit-font-smoothing: antialiased;
}

/* Top bar */
.topbar {
    border-bottom: 1px solid #E2DCD6;
    padding: 12px 20px;
    display: flex;
    align-items: center;
    gap: 14px;
    background: #FFFFFF;
    box-shadow: 0 1px 3px rgba(44,36,32,0.06);
}
.topbar .brand {
    font-family: 'Libre Baskerville', Georgia, serif;
    font-size: 17px;
    font-weight: 700;
    color: #6B4C3B;
    letter-spacing: -0.01em;
}

.app-body { display: flex; min-height: calc(100vh - 52px); }

/* Sidebar */
.sidebar {
    background: #FAF7F4;
    border-right: 1px solid #E2DCD6;
    padding: 20px 16px;
    width: 220px;
    flex-shrink: 0;
}
.sidebar-heading {
    font-family: 'Libre Baskerville', Georgia, serif;
    font-size: 11px;
    color: #8A7E75;
    font-weight: 700;
    letter-spacing: 0.06em;
    margin: 0 0 10px;
    text-transform: uppercase;
}
.nav-item {
    font-size: 13px;
    padding: 8px 12px;
    border-radius: 8px;
    margin-bottom: 3px;
    cursor: pointer;
    color: #5C4F46;
    border: 1px solid transparent;
    transition: all 0.12s;
}
.nav-item:hover { background: #FFFFFF; }
.nav-item.active {
    background: #FFFFFF;
    color: #2C2420;
    font-weight: 500;
    border: 1px solid #E2DCD6;
    box-shadow: 0 1px 3px rgba(44,36,32,0.06);
}
.filter-label {
    font-size: 12px;
    color: #5C4F46;
    margin: 0 0 5px;
    font-weight: 500;
}

/* Main area */
.main-panel {
    flex: 1;
    padding: 20px;
    min-width: 0;
    overflow-y: auto;
    background: #F5F0EB;
}

/* Stat cards */
.stats-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 10px;
    margin-bottom: 16px;
}
.stat-card {
    background: #FFFFFF;
    border-radius: 10px;
    padding: 14px 16px;
    border: 1px solid #E2DCD6;
    box-shadow: 0 1px 3px rgba(44,36,32,0.06);
    transition: box-shadow 0.2s, transform 0.15s;
}
.stat-card:hover {
    box-shadow: 0 2px 8px rgba(44,36,32,0.08);
    transform: translateY(-1px);
}
.stat-label {
    font-size: 11px;
    color: #8A7E75;
    margin: 0 0 4px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
}
.stat-val {
    font-family: 'Libre Baskerville', Georgia, serif;
    font-size: 22px;
    font-weight: 700;
    margin: 0;
    color: #6B4C3B;
}

/* Panels */
.panel {
    background: #FFFFFF;
    border: 1px solid #E2DCD6;
    border-radius: 14px;
    padding: 18px 22px;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(44,36,32,0.06);
}
.panel-title {
    font-family: 'Libre Baskerville', Georgia, serif;
    font-size: 15px;
    font-weight: 700;
    color: #2C2420;
    margin: 0 0 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #EDE8E3;
    letter-spacing: 0.01em;
}

/* Two-column grid */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
@media (max-width: 900px) { .two-col { grid-template-columns: 1fr; } }

/* Publication table */
.pub-controls {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    flex-wrap: wrap;
    gap: 10px;
}
.sort-buttons { display: flex; gap: 6px; }
.sort-btn {
    font-size: 11px;
    padding: 5px 12px;
    border-radius: 99px;
    border: 1px solid #E2DCD6;
    background: #FFFFFF;
    color: #5C4F46;
    cursor: pointer;
    font-family: inherit;
    font-weight: 500;
    transition: all 0.15s;
}
.sort-btn:hover { background: #F0EBE3; }
.sort-btn.active {
    background: #6B4C3B;
    color: #FFFFFF;
    border-color: #6B4C3B;
}
.search-box {
    font-size: 12px;
    padding: 7px 14px;
    border-radius: 99px;
    border: 1px solid #E2DCD6;
    background: #FAF7F4;
    color: #2C2420;
    width: 220px;
}
.search-box:focus {
    outline: none;
    border-color: #6B4C3B;
}

.pub-row {
    padding: 12px 10px;
    border-bottom: 1px solid #EDE8E3;
    display: flex;
    gap: 14px;
    align-items: flex-start;
    cursor: pointer;
    border-radius: 6px;
    transition: background 0.12s;
}
.pub-row:last-child { border-bottom: none; }
.pub-row:hover { background: #FAF7F4; }
.pub-year {
    font-family: 'Libre Baskerville', Georgia, serif;
    font-size: 13px;
    color: #8A7E75;
    min-width: 40px;
    padding-top: 2px;
    flex-shrink: 0;
}
.pub-info { flex: 1; min-width: 0; }
.pub-title {
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 4px;
    line-height: 1.45;
    color: #2C2420;
}
.pub-authors {
    font-size: 12px;
    color: #8A7E75;
    margin-bottom: 6px;
    font-style: italic;
}
.pub-meta { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }

/* Badges */
.badge {
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 99px;
    display: inline-block;
    font-weight: 500;
}
.badge-cites { background: #F0EBE3; color: #5A3D2E; }
.badge-venue { background: #E8F4EF; color: #1B5E47; }
.badge-if { background: #FDF4E7; color: #7A5216; }
.badge-if-high { background: #E8F4EF; color: #1B5E47; }

/* Reference expand */
.pub-ref {
    display: none;
    margin-top: 8px;
    padding: 10px 14px;
    background: #FAF7F4;
    border-radius: 8px;
    border: 1px solid #EDE8E3;
    font-size: 12px;
    color: #5C4F46;
}
.pub-ref.show { display: block; }
.ref-text {
    font-family: 'Libre Baskerville', Georgia, serif;
    font-size: 13px;
    word-break: break-word;
    line-height: 1.65;
}
.copy-btn {
    font-size: 11px;
    padding: 4px 12px;
    margin-top: 6px;
    border-radius: 99px;
    border: 1px solid #E2DCD6;
    background: #FFFFFF;
    color: #5C4F46;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.15s;
}
.copy-btn:hover { background: #6B4C3B; color: #fff; border-color: #6B4C3B; }

/* Export buttons */
.export-btn {
    font-size: 12px;
    padding: 7px 16px;
    border-radius: 99px;
    border: 1px solid #E2DCD6;
    background: #FFFFFF;
    color: #2C2420;
    cursor: pointer;
    font-weight: 500;
    box-shadow: 0 1px 3px rgba(44,36,32,0.06);
    transition: all 0.15s;
}
.export-btn:hover { background: #6B4C3B; color: #fff; border-color: #6B4C3B; }

/* Loading spinner */
.loading-overlay {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 60px;
    color: #8A7E75;
    font-size: 14px;
    font-family: 'Libre Baskerville', Georgia, serif;
    font-style: italic;
}

/* Publication count badge */
.pub-count {
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    font-weight: 600;
    background: #F0EBE3;
    color: #5A3D2E;
    padding: 2px 8px;
    border-radius: 99px;
    margin-left: 8px;
    vertical-align: middle;
}

/* Active filter info */
.filter-info {
    font-size: 11px;
    color: #8A7E75;
    margin-top: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.clear-filter-btn {
    font-size: 11px;
    padding: 2px 10px;
    border-radius: 99px;
    border: 1px solid #E2DCD6;
    background: #FFFFFF;
    cursor: pointer;
    color: #5C4F46;
    font-weight: 500;
    transition: all 0.15s;
}
.clear-filter-btn:hover { background: #6B4C3B; color: #fff; }

/* Dash-specific overrides */
.dash-graph .modebar { display: none !important; }
._dash-loading { background: transparent !important; }
"""


# ---------------------------------------------------------------------------
# Layout builder
# ---------------------------------------------------------------------------

def build_layout(scholar_url: str | None = None) -> html.Div:
    """Build the full Dash app layout.

    Args:
        scholar_url: Optional pre-loaded Scholar URL to show in the input.
    """
    return html.Div(
        [
            # CSS is served from gui/assets/style.css automatically by Dash

            # Hidden stores for data caching
            dcc.Store(id="profile-store", storage_type="session"),
            dcc.Store(id="analysis-store", storage_type="session"),
            dcc.Store(id="current-sort", data="citations"),
            dcc.Store(id="current-filter-coauthor", data=None),
            dcc.Store(id="current-filter-cluster", data=None),

            # Top bar
            html.Div(
                [
                    html.Span("PubNet", className="brand"),
                    dcc.Input(
                        id="scholar-url-input",
                        type="text",
                        placeholder="https://scholar.google.com/citations?user=...",
                        value=scholar_url or "",
                        style={
                            "flex": "1",
                            "maxWidth": "400px",
                            "fontSize": "12px",
                            "padding": "7px 14px",
                            "borderRadius": "99px",
                            "border": "1px solid #E2DCD6",
                            "background": "#FAF7F4",
                            "color": "#2C2420",
                        },
                        debounce=True,
                    ),
                    html.Button("Analyze", id="analyze-btn", n_clicks=0, style={
                        "fontSize": "12px", "padding": "7px 20px",
                        "borderRadius": "99px", "border": "1px solid #6B4C3B",
                        "background": "#6B4C3B", "cursor": "pointer",
                        "fontWeight": "600", "color": "#FFFFFF",
                        "transition": "all 0.15s",
                    }),
                    html.Button("Export JSON", id="export-json-btn", n_clicks=0, className="export-btn"),
                    html.Button("Export CSV", id="export-csv-btn", n_clicks=0, className="export-btn"),
                    dcc.Download(id="export-download"),
                    html.A(
                        "GitHub",
                        href="https://github.com/sanjiv856/pubnet",
                        target="_blank",
                        style={
                            "fontSize": "12px", "color": "#6B4C3B", "fontWeight": "500",
                            "textDecoration": "none", "borderBottom": "1px solid #D4CEC7",
                            "marginLeft": "auto", "padding": "4px 0",
                        },
                    ),
                ],
                className="topbar",
            ),

            # Body: sidebar + main
            html.Div(
                [
                    # Sidebar
                    html.Div(
                        [
                            html.P("VIEWS", className="sidebar-heading"),
                            html.Div("All views", id="nav-all", className="nav-item active", n_clicks=0),
                            html.Div("Network graph", id="nav-network", className="nav-item", n_clicks=0),
                            html.Div("Citation trends", id="nav-trends", className="nav-item", n_clicks=0),
                            html.Div("Topic clusters", id="nav-clusters", className="nav-item", n_clicks=0),
                            html.Div("Publications", id="nav-pubs", className="nav-item", n_clicks=0),

                            html.P("FILTERS", className="sidebar-heading", style={"marginTop": "24px"}),

                            html.P("Year range", className="filter-label"),
                            dcc.RangeSlider(
                                id="year-range",
                                min=2000,
                                max=2026,
                                value=[2000, 2026],
                                marks={y: str(y) for y in range(2000, 2027, 5)},
                                step=1,
                                tooltip={"placement": "bottom"},
                            ),

                            html.P("Min. citations", className="filter-label", style={"marginTop": "14px"}),
                            dcc.Slider(
                                id="min-citations",
                                min=0,
                                max=500,
                                value=0,
                                step=10,
                                marks={0: "0", 100: "100", 250: "250", 500: "500"},
                                tooltip={"placement": "bottom"},
                            ),

                            html.P("Reference format", className="filter-label", style={"marginTop": "14px"}),
                            dcc.Dropdown(
                                id="ref-format",
                                options=[
                                    {"label": "APA", "value": "apa"},
                                    {"label": "MLA", "value": "mla"},
                                    {"label": "BibTeX", "value": "bibtex"},
                                    {"label": "Vancouver", "value": "vancouver"},
                                    {"label": "Chicago", "value": "chicago"},
                                ],
                                value="apa",
                                clearable=False,
                                style={"fontSize": "12px"},
                            ),

                            # Active filter info
                            html.Div(id="active-filter-info", style={"marginTop": "16px", "fontSize": "11px", "color": "#8A7E75"}),
                        ],
                        className="sidebar",
                    ),

                    # Main panel
                    html.Div(
                        [
                            dcc.Loading(
                                id="main-loading",
                                type="default",
                                children=html.Div(id="main-content", children=_empty_state()),
                            ),
                        ],
                        className="main-panel",
                    ),
                ],
                className="app-body",
            ),
        ],
    )


def _empty_state() -> html.Div:
    """Placeholder shown before a profile is loaded."""
    return html.Div(
        [
            stat_cards_row(),
            html.Div(
                "Enter a Google Scholar URL and click Analyze, or the demo will load automatically.",
                className="loading-overlay",
            ),
        ],
    )
