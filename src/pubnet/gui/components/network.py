"""Co-author network graph component using dash-cytoscape — warm academic palette."""

from __future__ import annotations

from dash import html

try:
    import dash_cytoscape as cyto
except ImportError:
    cyto = None

from pubnet.models import CoauthorGraph


# Node colour palette — warm academic tones
_COLORS = [
    {"bg": "#F0EBE3", "border": "#6B4C3B", "text": "#5A3D2E"},  # ego: warm brown
    {"bg": "#E8F4EF", "border": "#1B5E47", "text": "#1B5E47"},  # teal
    {"bg": "#E8F0F8", "border": "#1A4D7C", "text": "#1A4D7C"},  # blue
    {"bg": "#FDF4E7", "border": "#7A5216", "text": "#7A5216"},  # amber
    {"bg": "#FBF0EF", "border": "#8B2E2E", "text": "#8B2E2E"},  # red
]


def build_cytoscape_elements(graph: CoauthorGraph) -> list[dict]:
    """Convert CoauthorGraph into Cytoscape elements."""
    elements = []

    for i, node in enumerate(graph.nodes):
        color = _COLORS[0] if node.is_ego else _COLORS[(i % (len(_COLORS) - 1)) + 1]
        size = 50 if node.is_ego else max(20, min(15 + node.paper_count * 5, 45))
        label = "You" if node.is_ego else _short_name(node.name)

        elements.append({
            "data": {
                "id": node.name,
                "label": label,
                "full_name": node.name,
                "paper_count": node.paper_count,
                "citations": node.total_citations,
                "is_ego": node.is_ego,
                "size": size,
                "bg_color": color["bg"],
                "border_color": color["border"],
                "text_color": color["text"],
            },
        })

    for edge in graph.edges:
        elements.append({
            "data": {
                "source": edge.source,
                "target": edge.target,
                "weight": edge.weight,
                "papers": ", ".join(edge.papers[:3]),
            },
        })

    return elements


def network_component(graph: CoauthorGraph | None = None) -> html.Div:
    """Build the co-author network panel."""
    if cyto is None:
        return html.Div(
            "dash-cytoscape is not installed. Install with: pip install dash-cytoscape",
            className="panel",
            style={"padding": "40px", "textAlign": "center", "color": "#8A7E75"},
        )

    elements = build_cytoscape_elements(graph) if graph else []

    stylesheet = [
        {
            "selector": "node",
            "style": {
                "label": "data(label)",
                "width": "data(size)",
                "height": "data(size)",
                "background-color": "data(bg_color)",
                "border-color": "data(border_color)",
                "border-width": 1.5,
                "font-size": "9px",
                "font-weight": "500",
                "font-family": "'Inter', -apple-system, sans-serif",
                "text-valign": "center",
                "text-halign": "center",
                "color": "data(text_color)",
                "text-wrap": "wrap",
                "text-max-width": "60px",
            },
        },
        {
            "selector": "edge",
            "style": {
                "width": "mapData(weight, 1, 5, 1, 4)",
                "line-color": "#D4CEC7",
                "opacity": "mapData(weight, 1, 5, 0.35, 0.75)",
                "curve-style": "bezier",
            },
        },
        {
            "selector": "node:selected",
            "style": {
                "border-width": 3,
                "border-color": "#6B4C3B",
                "background-color": "#F0EBE3",
            },
        },
    ]

    return html.Div(
        [
            html.Div(
                [
                    html.P("Co-Author Network", className="panel-title",
                           style={"display": "inline", "borderBottom": "none", "marginBottom": "0", "paddingBottom": "0"}),
                    html.Button(
                        "Reset View", id="network-reset-btn", n_clicks=0,
                        className="sort-btn",
                        style={"float": "right", "marginTop": "-2px"},
                    ),
                ],
                style={"marginBottom": "10px", "overflow": "hidden",
                        "borderBottom": "1px solid #EDE8E3", "paddingBottom": "8px"},
            ),
            cyto.Cytoscape(
                id="network-graph",
                elements=elements,
                layout={"name": "cose", "animate": True, "randomize": False, "nodeRepulsion": 8000, "idealEdgeLength": 120},
                stylesheet=stylesheet,
                style={"height": "380px", "width": "100%", "backgroundColor": "#FAF7F4", "borderRadius": "8px"},
                responsive=True,
            ),
        ],
        className="panel",
    )


def _short_name(name: str) -> str:
    """Shorten 'First Last' -> 'F.L.' for graph labels."""
    parts = name.split()
    if len(parts) <= 1:
        return name[:8]
    return ".".join(p[0] for p in parts) + "."
