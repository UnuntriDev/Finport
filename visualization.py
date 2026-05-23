"""Plotly chart builders. Each function returns a ``go.Figure``."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from theme import CHART_PALETTE, COLORS

_LAYOUT = dict(
    template="plotly_dark",
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(orientation="h", y=-0.15),
    hovermode="x unified",
)

_CHART_PORTFOLIO_LINE = "#4f9eff"
_CHART_PORTFOLIO_FILL = "rgba(79,158,255,0.15)"
_CHART_EQUAL_WEIGHT_BAR = "#a371f7"
_CHART_MC_PATH = "rgba(120,160,220,0.25)"
_CHART_MC_HIGH = "#7ee787"
_CHART_MC_MEDIAN = "#f0f6fc"
_CHART_MC_LOW = "#ff7b72"
_CHART_DRAWDOWN_FILL = "rgba(239,68,68,0.18)"
_CHART_DRAWDOWN_TEXT = "#fca5a5"
_CHART_DRAWDOWN_BG = "rgba(15,23,42,0.85)"


def plot_price_history(prices: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for col in prices.columns:
        fig.add_trace(
            go.Scatter(x=prices.index, y=prices[col], mode="lines", name=col)
        )
    fig.update_layout(title="Adjusted close prices", yaxis_title="Price ($)", **_LAYOUT)
    return fig


def plot_normalized_prices(normalized: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for col in normalized.columns:
        fig.add_trace(
            go.Scatter(x=normalized.index, y=normalized[col], mode="lines", name=col)
        )
    fig.add_hline(y=100, line_dash="dot", line_color="gray", opacity=0.5)
    fig.update_layout(
        title="Normalized performance (start = 100)",
        yaxis_title="Index level",
        **_LAYOUT,
    )
    return fig


def plot_portfolio_value(value: pd.Series, initial: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=value.index,
            y=value.values,
            mode="lines",
            name="Portfolio value",
            line=dict(width=2.5, color=_CHART_PORTFOLIO_LINE),
            fill="tozeroy",
            fillcolor=_CHART_PORTFOLIO_FILL,
        )
    )
    fig.add_hline(
        y=initial,
        line_dash="dash",
        line_color="gray",
        opacity=0.6,
        annotation_text="Initial investment",
        annotation_position="top left",
    )
    fig.update_layout(title="Portfolio value over time", yaxis_title="Value ($)", **_LAYOUT)
    return fig


def plot_correlation_heatmap(corr: pd.DataFrame) -> go.Figure:
    fig = px.imshow(
        corr,
        text_auto=".2f",
        zmin=-1,
        zmax=1,
        color_continuous_scale="RdBu_r",
        aspect="auto",
    )
    fig.update_layout(title="Return correlation matrix", **_LAYOUT)
    return fig


def plot_monte_carlo(sims: pd.DataFrame) -> go.Figure:
    """Thinned sample of paths plus median and 5/95 percentile bands."""
    fig = go.Figure()

    sample_cols = sims.columns[:: max(1, sims.shape[1] // 200)]
    for col in sample_cols:
        fig.add_trace(
            go.Scatter(
                x=sims.index,
                y=sims[col],
                mode="lines",
                line=dict(width=0.5, color=_CHART_MC_PATH),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    median = sims.median(axis=1)
    p5 = sims.quantile(0.05, axis=1)
    p95 = sims.quantile(0.95, axis=1)

    fig.add_trace(go.Scatter(
        x=sims.index, y=p95, mode="lines",
        line=dict(color=_CHART_MC_HIGH, width=1.5), name="95th percentile",
    ))
    fig.add_trace(go.Scatter(
        x=sims.index, y=median, mode="lines",
        line=dict(color=_CHART_MC_MEDIAN, width=2.5), name="Median",
    ))
    fig.add_trace(go.Scatter(
        x=sims.index, y=p5, mode="lines",
        line=dict(color=_CHART_MC_LOW, width=1.5), name="5th percentile",
    ))

    fig.update_layout(
        title="Monte Carlo: simulated portfolio value paths",
        xaxis_title="Trading day",
        yaxis_title="Portfolio value ($)",
        **_LAYOUT,
    )
    return fig


def plot_weights_comparison(custom: pd.Series, equal: pd.Series) -> go.Figure:
    df = pd.DataFrame({"Custom": custom * 100, "Equal-weight": equal * 100})
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df.index, y=df["Custom"], name="Custom",
        marker_color=_CHART_PORTFOLIO_LINE,
    ))
    fig.add_trace(go.Bar(
        x=df.index, y=df["Equal-weight"], name="Equal-weight",
        marker_color=_CHART_EQUAL_WEIGHT_BAR,
    ))
    fig.update_layout(
        title="Weight allocation: custom vs. equal-weight",
        yaxis_title="Weight (%)",
        barmode="group",
        **_LAYOUT,
    )
    return fig


def plot_drawdown(drawdown: pd.Series, max_dd: float, trough_date) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=drawdown.index,
            y=drawdown.values * 100,
            mode="lines",
            line=dict(width=1.5, color=COLORS["danger"]),
            fill="tozeroy",
            fillcolor=_CHART_DRAWDOWN_FILL,
            name="Drawdown",
            hovertemplate="%{x|%Y-%m-%d}<br>DD: %{y:.2f}%<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_color="#475569", opacity=0.5)
    fig.add_annotation(
        x=trough_date,
        y=max_dd * 100,
        text=f"Max DD: {max_dd * 100:.2f}%",
        showarrow=True,
        arrowhead=2,
        arrowcolor=COLORS["danger"],
        font=dict(color=_CHART_DRAWDOWN_TEXT, size=12),
        bgcolor=_CHART_DRAWDOWN_BG,
        bordercolor=COLORS["danger"],
        borderwidth=1,
    )
    fig.update_layout(
        title="Underwater chart — drawdown over time",
        yaxis_title="Drawdown (%)",
        **_LAYOUT,
    )
    return fig


def plot_efficient_frontier(
    frontier: pd.DataFrame,
    asset_points: dict[str, tuple[float, float]],
    custom_point: dict,
    max_sharpe_point: dict,
    min_var_point: dict,
) -> go.Figure:
    """Frontier curve plus individual assets and the three optimal portfolios."""
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=frontier["volatility"] * 100,
            y=frontier["return"] * 100,
            mode="lines",
            line=dict(color=COLORS["primary"], width=3),
            name="Efficient frontier",
            hovertemplate="Vol: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>",
        )
    )

    asset_x = [v[1] * 100 for v in asset_points.values()]
    asset_y = [v[0] * 100 for v in asset_points.values()]
    asset_names = list(asset_points.keys())
    fig.add_trace(
        go.Scatter(
            x=asset_x, y=asset_y,
            mode="markers+text",
            marker=dict(
                size=11, color="#94a3b8",
                line=dict(width=1, color="#475569"),
            ),
            text=asset_names,
            textposition="top center",
            textfont=dict(color="#cbd5e1", size=11),
            name="Individual assets",
            hovertemplate="%{text}<br>Vol: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>",
        )
    )

    _add_portfolio_marker(
        fig, custom_point, "Custom", COLORS["gold"], "star", size=22,
    )
    _add_portfolio_marker(
        fig, max_sharpe_point, "Max Sharpe", COLORS["success"], "diamond", size=18,
    )
    _add_portfolio_marker(
        fig, min_var_point, "Min Var", COLORS["purple"], "diamond", size=18,
    )

    fig.update_layout(
        title="Efficient Frontier — Markowitz (1952)",
        xaxis_title="Annualized volatility (%)",
        yaxis_title="Annualized return (%)",
        **_LAYOUT,
    )
    return fig


def _add_portfolio_marker(
    fig: go.Figure,
    point: dict,
    label: str,
    color: str,
    symbol: str,
    size: int,
) -> None:
    fig.add_trace(
        go.Scatter(
            x=[point["volatility"] * 100],
            y=[point["return"] * 100],
            mode="markers+text",
            marker=dict(
                size=size, color=color, symbol=symbol,
                line=dict(width=1.5, color="#ffffff"),
            ),
            text=[label],
            textposition="bottom center",
            textfont=dict(color=color, size=12, family="Arial Black"),
            name=label,
        )
    )


def plot_sector_breakdown(sector_weights: dict[str, float]) -> go.Figure:
    labels = list(sector_weights.keys())
    values = list(sector_weights.values())
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.5,
                marker=dict(
                    colors=CHART_PALETTE[: len(labels)],
                    line=dict(color=COLORS["surface_deep"], width=2),
                ),
                textinfo="label+percent",
                textfont=dict(size=12, color="#f1f5f9"),
                hovertemplate="<b>%{label}</b><br>Weight: %{value:.2f}%<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title="Sector allocation",
        template="plotly_dark",
        margin=dict(l=10, r=10, t=50, b=10),
        showlegend=False,
        height=400,
    )
    return fig


def plot_portfolio_vs_market(
    port_value: pd.Series,
    market_value: pd.Series,
    market_label: str = "S&P 500",
) -> go.Figure:
    """Portfolio vs benchmark, both rebased to 100."""
    p_norm = (port_value / port_value.iloc[0]) * 100
    m_norm = (market_value / market_value.iloc[0]) * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=p_norm.index, y=p_norm.values,
        mode="lines", name="Your portfolio",
        line=dict(color=COLORS["primary"], width=2.6),
    ))
    fig.add_trace(go.Scatter(
        x=m_norm.index, y=m_norm.values,
        mode="lines", name=market_label,
        line=dict(color="#94a3b8", width=2, dash="dash"),
    ))
    fig.add_hline(y=100, line_dash="dot", line_color="gray", opacity=0.4)
    fig.update_layout(
        title=f"Portfolio vs. {market_label} (start = 100)",
        yaxis_title="Index level",
        **_LAYOUT,
    )
    return fig
