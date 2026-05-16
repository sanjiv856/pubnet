"""HTML report renderer for PubNet.

Generates a self-contained HTML file with embedded charts, network graph,
and interactive publication table.

Usage:
    html = render_report(author, publications, analyses)
    Path("report.html").write_text(html)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from jinja2 import Template

from pubnet.models import (
    Author,
    CitationTrends,
    CoauthorGraph,
    Publication,
    StatsSummary,
    TopicAnalysis,
)
from pubnet.formatters import format_all

logger = logging.getLogger(__name__)

TEMPLATE_PATH = Path(__file__).parent / "templates" / "report.html"


def render_report(
    author: Author,
    publications: list[Publication],
    stats: StatsSummary,
    coauthor_graph: CoauthorGraph,
    citation_trends: CitationTrends,
    topic_analysis: TopicAnalysis,
    impact_factors: dict[str, float | None],
) -> str:
    """Render a self-contained HTML report.

    Returns:
        Complete HTML string ready to write to a file.
    """
    # Load template
    template_str = TEMPLATE_PATH.read_text(encoding="utf-8")
    template = Template(template_str)

    # Build Plotly.js inline (use CDN reference for size, or embed minimal)
    plotly_js = _get_plotly_js()

    # Build chart data
    citation_chart = _build_citation_chart(citation_trends)
    cluster_chart = _build_cluster_chart(topic_analysis, publications)
    pubs_per_year_chart = _build_pubs_per_year_chart(citation_trends)

    # Build network HTML
    network_html = _build_network_html(coauthor_graph, author.name)

    # Build publication data and references for JS
    # Each pub carries its original index (_idx) so references stay correct
    # even after sorting/filtering in the browser
    pub_dicts = [
        {
            "_idx": i,
            "title": p.title,
            "authors": p.authors,
            "year": p.year,
            "venue": p.venue,
            "citations": p.citations,
            "abstract": p.abstract,
        }
        for i, p in enumerate(publications)
    ]

    references = [format_all(p) for p in publications]

    # Clean impact factors (remove None values for JSON)
    clean_ifs = {k: v for k, v in impact_factors.items() if v is not None}

    # Render
    html = template.render(
        author=author,
        stats=stats,
        plotly_js=plotly_js,
        network_html=network_html,
        publications_json=json.dumps(pub_dicts),
        impact_factors_json=json.dumps(clean_ifs),
        references_json=json.dumps(references),
        citation_chart_json=json.dumps(citation_chart),
        cluster_chart_json=json.dumps(cluster_chart),
        pubs_per_year_json=json.dumps(pubs_per_year_chart),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        github_url="https://github.com/YOUR_USERNAME/pubnet",
        gui_url="",  # Set to deployed GUI URL once available
    )

    return html


def _get_plotly_js() -> str:
    """Get Plotly.js loader as a complete <script> block.

    Loads Plotly from CDN, then calls initCharts() once loaded.
    Placed at end of <body> so initCharts is already defined.
    """
    return """
    <script>
    (function(){
      if(typeof Plotly !== 'undefined') { initCharts(); return; }
      var s = document.createElement('script');
      s.src = 'https://cdn.plot.ly/plotly-2.35.0.min.js';
      s.onload = function(){ if(typeof initCharts === 'function') initCharts(); };
      s.onerror = function(){
        document.getElementById('citation-chart').innerHTML = '<p style="text-align:center;color:#8A7E75;padding:40px;">Charts require internet connection to load Plotly.js</p>';
        document.getElementById('cluster-chart').innerHTML = '<p style="text-align:center;color:#8A7E75;padding:40px;">Charts require internet connection to load Plotly.js</p>';
      };
      document.head.appendChild(s);
    })();
    </script>
    """


def _build_citation_chart(trends: CitationTrends) -> dict:
    """Build Plotly data for the citation trends bar chart."""
    if not trends.yearly:
        return {"data": [], "layout": {}}

    years = [y.year for y in trends.yearly]
    citations = [y.citation_count for y in trends.yearly]
    pub_counts = [y.publication_count for y in trends.yearly]
    h_indices = [y.cumulative_h_index for y in trends.yearly]

    # Color bars: warm brown tones, higher citation years get darker
    max_cites = max(citations) if citations else 1
    colors = [
        f"rgba(107, 76, 59, {0.35 + 0.65 * (c / max_cites)})"
        for c in citations
    ]

    data = [
        {
            "type": "bar",
            "x": years,
            "y": citations,
            "name": "Citations",
            "marker": {"color": colors, "cornerradius": 4},
            "hovertemplate": "%{x}<br>Citations: %{y}<br>Papers: %{customdata}<extra></extra>",
            "customdata": pub_counts,
        },
        {
            "type": "scatter",
            "x": years,
            "y": h_indices,
            "name": "h-index",
            "mode": "lines+markers",
            "line": {"color": "#1B5E47", "width": 2.5},
            "marker": {"size": 6, "color": "#1B5E47"},
            "yaxis": "y2",
            "hovertemplate": "%{x}<br>h-index: %{y}<extra></extra>",
        },
    ]

    layout = {
        "barmode": "group",
        "showlegend": True,
        "legend": {"x": 0.01, "y": 0.99, "bgcolor": "rgba(255,255,255,0.8)", "font": {"size": 10}},
        "yaxis": {"title": {"text": "Citations", "font": {"size": 11}}},
        "yaxis2": {
            "title": {"text": "h-index", "font": {"size": 11}},
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
        },
        "xaxis": {"dtick": 1},
    }

    return {"data": data, "layout": layout}


def _build_pubs_per_year_chart(trends: CitationTrends) -> dict:
    """Build Plotly data for publications per year bar chart."""
    if not trends.yearly:
        return {"data": [], "layout": {}}

    years = [y.year for y in trends.yearly]
    pub_counts = [y.publication_count for y in trends.yearly]

    max_pubs = max(pub_counts) if pub_counts else 1
    colors = [
        "rgba(26, 77, 124, %.2f)" % (0.35 + 0.65 * (c / max_pubs))
        for c in pub_counts
    ]

    data = [
        {
            "type": "bar",
            "x": years,
            "y": pub_counts,
            "name": "Publications",
            "marker": {"color": colors, "cornerradius": 4},
            "hovertemplate": "%{x}<br>Publications: %{y}<extra></extra>",
        },
    ]

    layout = {
        "showlegend": False,
        "yaxis": {"title": {"text": "Publications", "font": {"size": 11}}},
        "xaxis": {"dtick": 1},
    }

    return {"data": data, "layout": layout}


def _build_cluster_chart(topic_analysis: TopicAnalysis, publications: list[Publication]) -> dict:
    """Build Plotly data for the topic clusters bubble chart."""
    if not topic_analysis.clusters:
        return {"data": [], "layout": {}}

    colors = [
        "#6B4C3B", "#1B5E47", "#1A4D7C", "#7A5216", "#8B2E2E",
        "#5A3D6B", "#2E6B5A", "#3B5C8B", "#8B6B2E", "#6B2E4C",
    ]

    labels = []
    sizes = []
    cite_counts = []
    pub_counts = []
    marker_colors = []
    hover_texts = []

    for c in topic_analysis.clusters:
        kw = ", ".join(c.keywords[:3])
        labels.append(kw)
        sizes.append(max(c.publication_count * 15, 20))
        cite_counts.append(c.total_citations)
        pub_counts.append(c.publication_count)
        marker_colors.append(colors[c.cluster_id % len(colors)])
        hover_texts.append(
            f"<b>{kw}</b><br>"
            f"Papers: {c.publication_count}<br>"
            f"Citations: {c.total_citations}<br>"
            f"Keywords: {', '.join(c.keywords)}"
        )

    data = [
        {
            "type": "scatter",
            "x": list(range(len(labels))),
            "y": cite_counts,
            "mode": "markers+text",
            "text": labels,
            "textposition": "top center",
            "textfont": {"size": 10, "color": "#5C4F46"},
            "marker": {
                "size": sizes,
                "color": marker_colors,
                "opacity": 0.8,
                "line": {"width": 1.5, "color": "white"},
            },
            "hovertext": hover_texts,
            "hoverinfo": "text",
        }
    ]

    layout = {
        "showlegend": False,
        "xaxis": {"visible": False},
        "yaxis": {"title": {"text": "Total Citations", "font": {"size": 11}}},
    }

    return {"data": data, "layout": layout}


def _build_network_html(graph: CoauthorGraph, ego_name: str) -> str:
    """Build an inline SVG network graph using basic force-layout positioning."""
    if not graph.nodes:
        return '<div style="text-align:center;padding:40px;color:#8A7E75;">No co-author data available</div>'

    try:
        import networkx as nx
    except ImportError:
        return '<div style="text-align:center;padding:40px;color:#8A7E75;">networkx required for network graph</div>'

    # Build networkx graph
    G = nx.Graph()
    for node in graph.nodes:
        G.add_node(node.name, paper_count=node.paper_count, is_ego=node.is_ego)
    for edge in graph.edges:
        G.add_edge(edge.source, edge.target, weight=edge.weight)

    # Compute layout
    if len(G.nodes) < 2:
        pos = {list(G.nodes)[0]: (0.5, 0.5)} if G.nodes else {}
    else:
        pos = nx.spring_layout(G, k=2.0, iterations=50, seed=42)

    # Scale to SVG coordinates
    width, height = 700, 400
    pad = 60
    if pos:
        xs = [p[0] for p in pos.values()]
        ys = [p[1] for p in pos.values()]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        x_range = x_max - x_min or 1
        y_range = y_max - y_min or 1

        scaled = {}
        for name, (x, y) in pos.items():
            sx = pad + (x - x_min) / x_range * (width - 2 * pad)
            sy = pad + (y - y_min) / y_range * (height - 2 * pad)
            scaled[name] = (sx, sy)
    else:
        scaled = {}

    # Warm academic node palette
    node_colors = [
        ("#F0EBE3", "#6B4C3B"),
        ("#E8F4EF", "#1B5E47"),
        ("#E8F0F8", "#1A4D7C"),
        ("#FDF4E7", "#7A5216"),
        ("#FBF0EF", "#8B2E2E"),
    ]

    svg_parts = [
        '<svg width="100%" height="' + str(height) + '" viewBox="0 0 ' + str(width) + ' ' + str(height) + '" '
        'xmlns="http://www.w3.org/2000/svg" style="font-family:Inter,-apple-system,sans-serif;">'
    ]

    # Edges
    for edge in graph.edges:
        if edge.source in scaled and edge.target in scaled:
            x1, y1 = scaled[edge.source]
            x2, y2 = scaled[edge.target]
            stroke_w = min(1 + edge.weight * 0.8, 5)
            opacity = min(0.3 + edge.weight * 0.15, 0.8)
            svg_parts.append(
                '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" '
                'stroke="#D4CEC7" stroke-width="%.1f" opacity="%.2f"/>'
                % (x1, y1, x2, y2, stroke_w, opacity)
            )

    # Nodes
    for i, node in enumerate(graph.nodes):
        if node.name not in scaled:
            continue
        x, y = scaled[node.name]
        if node.is_ego:
            fill, stroke = node_colors[0]
            r = 18
        else:
            cidx = (i % (len(node_colors) - 1)) + 1
            fill, stroke = node_colors[cidx]
            r = max(8, min(5 + node.paper_count * 2, 16))

        svg_parts.append(
            '<circle cx="%.1f" cy="%.1f" r="%d" fill="%s" '
            'stroke="%s" stroke-width="1.2">'
            '<title>%s (%d papers, %d citations)</title>'
            '</circle>'
            % (x, y, r, fill, stroke, node.name, node.paper_count, node.total_citations)
        )

        # Label
        short_name = _short_name(node.name) if not node.is_ego else "You"
        font_size = 9 if node.is_ego else 7
        font_weight = "600" if node.is_ego else "400"
        svg_parts.append(
            '<text x="%.1f" y="%.1f" text-anchor="middle" '
            'font-size="%d" font-weight="%s" fill="%s">%s</text>'
            % (x, y + 3, font_size, font_weight, stroke, short_name)
        )

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)


def _short_name(name: str) -> str:
    """Shorten 'First Last' to 'F.L.' for graph labels."""
    parts = name.split()
    if len(parts) <= 1:
        return name[:8]
    return ".".join(p[0] for p in parts) + "."
