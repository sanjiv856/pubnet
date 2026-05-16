"""Citation trends bar chart component (Plotly) — warm academic palette."""

from __future__ import annotations

from dash import dcc, html
import plotly.graph_objects as go

from pubnet.models import CitationTrends


def build_citation_figure(trends: CitationTrends | None = None) -> go.Figure:
    """Build a Plotly bar chart for citations per year with h-index overlay."""
    fig = go.Figure()

    if trends and trends.yearly:
        years = [y.year for y in trends.yearly]
        citations = [y.citation_count for y in trends.yearly]
        h_indices = [y.cumulative_h_index for y in trends.yearly]
        pub_counts = [y.publication_count for y in trends.yearly]

        max_c = max(citations) if citations else 1
        colors = [
            f"rgba(107, 76, 59, {0.35 + 0.65 * (c / max_c)})"
            for c in citations
        ]

        fig.add_trace(go.Bar(
            x=years,
            y=citations,
            name="Citations",
            marker=dict(color=colors, cornerradius=4),
            customdata=pub_counts,
            hovertemplate="%{x}<br>Citations: %{y}<br>Papers: %{customdata}<extra></extra>",
        ))

        fig.add_trace(go.Scatter(
            x=years,
            y=h_indices,
            name="h-index",
            mode="lines+markers",
            line=dict(color="#1B5E47", width=2.5),
            marker=dict(size=6, color="#1B5E47"),
            yaxis="y2",
            hovertemplate="%{x}<br>h-index: %{y}<extra></extra>",
        ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="'Inter', -apple-system, sans-serif", size=11, color="#5C4F46"),
        margin=dict(t=10, r=40, b=35, l=45),
        xaxis=dict(gridcolor="#EDE8E3", linecolor="#E2DCD6", dtick=1),
        yaxis=dict(gridcolor="#EDE8E3", linecolor="#E2DCD6", title=dict(text="Citations", font=dict(size=11))),
        yaxis2=dict(
            title=dict(text="h-index", font=dict(size=11)),
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        showlegend=True,
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.8)", font=dict(size=10)),
        height=280,
    )

    return fig


def trends_component(trends: CitationTrends | None = None) -> html.Div:
    """Build the citation trends panel."""
    fig = build_citation_figure(trends)
    return html.Div(
        [
            html.P("Citations Per Year", className="panel-title"),
            dcc.Graph(
                id="citation-chart",
                figure=fig,
                config={"displayModeBar": False, "responsive": True},
                style={"height": "280px"},
            ),
        ],
        className="panel",
    )
