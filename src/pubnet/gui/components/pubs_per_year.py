"""Publications per year bar chart component (Plotly) - warm academic palette."""

from __future__ import annotations

from dash import dcc, html
import plotly.graph_objects as go

from pubnet.models import CitationTrends


def build_pubs_per_year_figure(trends: CitationTrends | None = None) -> go.Figure:
    """Build a Plotly bar chart for publications per year."""
    fig = go.Figure()

    if trends and trends.yearly:
        years = [y.year for y in trends.yearly]
        pub_counts = [y.publication_count for y in trends.yearly]

        max_p = max(pub_counts) if pub_counts else 1
        colors = [
            f"rgba(26, 77, 124, {0.35 + 0.65 * (c / max_p)})"
            for c in pub_counts
        ]

        fig.add_trace(go.Bar(
            x=years,
            y=pub_counts,
            name="Publications",
            marker=dict(color=colors, cornerradius=4),
            hovertemplate="%{x}<br>Publications: %{y}<extra></extra>",
        ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="'Inter', -apple-system, sans-serif", size=11, color="#5C4F46"),
        margin=dict(t=10, r=20, b=35, l=45),
        xaxis=dict(gridcolor="#EDE8E3", linecolor="#E2DCD6", dtick=1),
        yaxis=dict(gridcolor="#EDE8E3", linecolor="#E2DCD6", title=dict(text="Publications", font=dict(size=11))),
        showlegend=False,
        height=280,
    )

    return fig


def pubs_per_year_component(trends: CitationTrends | None = None) -> html.Div:
    """Build the publications per year panel."""
    fig = build_pubs_per_year_figure(trends)
    return html.Div(
        [
            html.P("Publications Per Year", className="panel-title"),
            dcc.Graph(
                id="pubs-per-year-chart",
                figure=fig,
                config={"displayModeBar": False, "responsive": True},
                style={"height": "280px"},
            ),
        ],
        className="panel",
    )
