"""Optimization tab — Max Sharpe, Min Variance, Efficient Frontier."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from models import PortfolioAnalysisResult, ViewContext
from ui_components import metric_card, muted_paragraph, vertical_spacer
from visualization import plot_efficient_frontier


def render_optimization_tab(
    result: PortfolioAnalysisResult,
    context: ViewContext,
) -> None:
    del context
    st.subheader("Markowitz Portfolio Optimization")
    st.markdown(
        muted_paragraph(
            "Two classical optimal portfolios computed by minimizing variance "
            "under constraints (long-only, sum of weights = 1). The Efficient "
            "Frontier below shows the best achievable risk/return trade-offs.",
            margin_bottom=20,
        ),
        unsafe_allow_html=True,
    )

    _render_portfolio_cards(result)
    st.markdown(vertical_spacer(24), unsafe_allow_html=True)
    _render_weights_table(result)
    _render_efficient_frontier(result)


def _render_portfolio_cards(result: PortfolioAnalysisResult) -> None:
    o1, o2, o3 = st.columns(3)
    with o1:
        st.markdown(
            _portfolio_card(
                "Custom Portfolio",
                result.portfolio_sharpe,
                result.portfolio_metrics,
                tooltip="Your weights.",
                value_color="#fbbf24",
            ),
            unsafe_allow_html=True,
        )
    with o2:
        st.markdown(
            _portfolio_card(
                "Max Sharpe (Tangency)",
                result.max_sharpe_ratio,
                result.max_sharpe_metrics,
                tooltip="Portfolio with the highest risk-adjusted return. This "
                "is the tangency portfolio from the Capital Market Line.",
                value_color="#10b981",
            ),
            unsafe_allow_html=True,
        )
    with o3:
        st.markdown(
            _portfolio_card(
                "Min Variance",
                result.min_variance_sharpe,
                result.min_variance_metrics,
                tooltip="Portfolio with the lowest possible volatility "
                "regardless of expected return. The safest reachable allocation.",
                value_color="#a855f7",
            ),
            unsafe_allow_html=True,
        )


def _portfolio_card(
    label: str,
    sharpe: float,
    metrics: dict[str, float],
    tooltip: str,
    value_color: str,
) -> str:
    return metric_card(
        label,
        f"{sharpe:.2f}",
        f"{tooltip} Return {metrics['return']*100:.2f}%, "
        f"Vol {metrics['volatility']*100:.2f}%.",
        f"Return {metrics['return']*100:.1f}% | Vol {metrics['volatility']*100:.1f}%",
        value_color,
        "#94a3b8",
    )


def _render_weights_table(result: PortfolioAnalysisResult) -> None:
    st.subheader("Optimal weights")
    weights = result.weights.reindex(result.prices.columns).fillna(0.0)
    weights_table = pd.DataFrame(
        {
            "Custom": (weights * 100).map(lambda x: f"{x:.2f}%"),
            "Max Sharpe": (result.max_sharpe_weights * 100).map(lambda x: f"{x:.2f}%"),
            "Min Variance": (result.min_variance_weights * 100).map(lambda x: f"{x:.2f}%"),
        }
    )
    st.dataframe(weights_table, use_container_width=True)


def _render_efficient_frontier(result: PortfolioAnalysisResult) -> None:
    st.subheader("Efficient Frontier")
    asset_points = {
        ticker: (
            float(result.asset_stats.loc[ticker, "annual_return"]),
            float(result.asset_stats.loc[ticker, "annual_vol"]),
        )
        for ticker in result.asset_stats.index
    }
    st.plotly_chart(
        plot_efficient_frontier(
            result.efficient_frontier,
            asset_points=asset_points,
            custom_point=result.portfolio_metrics,
            max_sharpe_point=result.max_sharpe_metrics,
            min_var_point=result.min_variance_metrics,
        ),
        use_container_width=True,
    )
    st.caption(
        "The **Efficient Frontier** (Markowitz, 1952) is the set of portfolios "
        "offering the highest expected return for a given level of risk. Any "
        "portfolio below the frontier is suboptimal — you could earn more for "
        "the same risk, or take less risk for the same return."
    )
