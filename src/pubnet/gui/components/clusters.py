"""Topic clusters bubble chart component (Plotly) - warm academic palette."""

from __future__ import annotations

from dash import dcc, html
import plotly.graph_objects as go

from pubnet.models import TopicAnalysis


_CLUSTER_COLORS = [
    "#6B4C3B", "#1B5E47", "#1A4D7C", "#7A5216", "#8B2E2E",
    "#5A3D6B", "#2E6B5A", "#3B5C8B", "#8B6B2E", "#6B2E4C",
]


def build_cluster_figure(topic_analysis: TopicAnalysis | None = None) -> go.Figure:
    """Build a Plotly bubble chart for topic clusters."""
    fig = go.Figure()

    if topic_analysis and topic_analysis.clusters:
        labels = []
        cite_counts = []
        sizes = []
        colors = []
        hover_texts = []

        for c in topic_analysis.clusters:
            kw = ", ".join(c.keywords[:3])
            labels.append(kw)
            cite_counts.append(c.total_citations)
            sizes.append(max(c.publication_count * 15, 20))
            colors.append(_CLUSTER_COLORS[c.cluster_id % len(_CLUSTER_COLORS)])
            hover_texts.append(
                f"<b>{kw}</b><br>"
                f"Papers: {c.publication_count}<br>"
                f"Citations: {c.total_citations}<br>"
                f"Keywords: {', '.join(c.keywords)}"
            )

        fig.add_trace(go.Scatter(
            x=list(range(len(labels))),
            y=cite_counts,
            mode="markers+text",
            text=labels,
            textposition="top center",
            textfont=dict(size=9, color="#5C4F46"),
            marker=dict(
                size=sizes,
                color=colors,
                opacity=0.8,
                line=dict(width=1.5, color="white"),
            ),
            hovertext=hover_texts,
            hoverinfo="text",
            customdata=[c.cluster_id for c in topic_analysis.clusters],
        ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="'Inter', -apple-system, sans-serif", size=11, color="#5C4F46"),
        margin=dict(t=10, r=20, b=35, l=45),
        xaxis=dict(visible=False),
        yaxis=dict(gridcolor="#EDE8E3", linecolor="#E2DCD6", title=dict(text="Total Citations", font=dict(size=11))),
        showlegend=False,
        height=280,
    )

    return fig


def clusters_component(topic_analysis: TopicAnalysis | None = None) -> html.Div:
    """Build the topic clusters panel."""
    fig = build_cluster_figure(topic_analysis)
    return html.Div(
        [
            html.P("Topic Clusters", className="panel-title"),
            dcc.Graph(
                id="cluster-chart",
                figure=fig,
                config={"displayModeBar": False, "responsive": True},
                style={"height": "280px"},
            ),
        ],
        className="panel",
    )
