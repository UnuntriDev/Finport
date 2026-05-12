"""Small donut chart used inside the sidebar (allocation preview)."""
from __future__ import annotations

import plotly.graph_objects as go

from theme import CHART_PALETTE, COLORS


def allocation_donut(tickers: list[str], weights: dict[str, float]) -> go.Figure:
    """Small donut chart visualising portfolio allocation."""
    values = [weights.get(t, 0.0) for t in tickers]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=tickers,
                values=values,
                hole=0.65,
                marker=dict(
                    colors=CHART_PALETTE[: len(tickers)],
                    line=dict(color=COLORS["surface_deep"], width=2),
                ),
                textinfo="label+percent",
                textfont=dict(size=10, color="#f1f5f9"),
                hoverinfo="label+percent",
                showlegend=False,
            )
        ]
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        height=210,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        annotations=[
            dict(
                text=(
                    f"{len(tickers)}<br>"
                    f"<span style='font-size:10px;color:{COLORS['muted']};'>"
                    "ASSETS</span>"
                ),
                x=0.5,
                y=0.5,
                font=dict(size=22, color="#f1f5f9", family="Arial Black"),
                showarrow=False,
            )
        ],
    )
    return fig
