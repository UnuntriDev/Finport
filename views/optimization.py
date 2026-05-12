from __future__ import annotations

import pandas as pd
import streamlit as st

from models import PortfolioAnalysisResult, ViewContext
from ui_components import metric_card, muted_paragraph, vertical_spacer
from visualization import plot_efficient_frontier


def render_optimization_tab(result: PortfolioAnalysisResult, context: ViewContext) -> None:
    prices = result.prices
    weights = result.weights
    asset_stats = result.asset_stats
    port_metrics = result.portfolio_metrics
    sharpe = result.portfolio_sharpe
    max_sharpe_weights = result.max_sharpe_weights
    min_var_weights = result.min_variance_weights
    max_sharpe_metrics = result.max_sharpe_metrics
    min_var_metrics = result.min_variance_metrics
    max_sharpe_value = result.max_sharpe_ratio
    min_var_sharpe = result.min_variance_sharpe
    frontier_df = result.efficient_frontier
    st.subheader("Markowitz Portfolio Optimization")
    st.markdown(
        muted_paragraph(
            "Two classical optimal portfolios computed by minimizing variance under "
            "constraints (long-only, sum of weights = 1). The Efficient Frontier "
            "below shows the best achievable risk/return trade-offs.",
            margin_bottom=20,
        ),
        unsafe_allow_html=True,
    )

    # Portfolio comparison cards
    o1, o2, o3 = st.columns(3)
    with o1:
        st.markdown(
            metric_card(
                "Custom Portfolio",
                f"{sharpe:.2f}",
                f"Your weights. Return {port_metrics['return']*100:.2f}%, "
                f"Vol {port_metrics['volatility']*100:.2f}%.",
                f"Return {port_metrics['return']*100:.1f}% | Vol "
                f"{port_metrics['volatility']*100:.1f}%",
                "#fbbf24", "#94a3b8",
            ),
            unsafe_allow_html=True,
        )
    with o2:
        st.markdown(
            metric_card(
                "Max Sharpe (Tangency)",
                f"{max_sharpe_value:.2f}",
                "Portfolio with the highest risk-adjusted return. This is the "
                "tangency portfolio from the Capital Market Line.",
                f"Return {max_sharpe_metrics['return']*100:.1f}% | Vol "
                f"{max_sharpe_metrics['volatility']*100:.1f}%",
                "#10b981", "#94a3b8",
            ),
            unsafe_allow_html=True,
        )
    with o3:
        st.markdown(
            metric_card(
                "Min Variance",
                f"{min_var_sharpe:.2f}",
                "Portfolio with the lowest possible volatility regardless of "
                "expected return. The safest reachable allocation.",
                f"Return {min_var_metrics['return']*100:.1f}% | Vol "
                f"{min_var_metrics['volatility']*100:.1f}%",
                "#a855f7", "#94a3b8",
            ),
            unsafe_allow_html=True,
        )

    st.markdown(vertical_spacer(24), unsafe_allow_html=True)

    # Optimal weights table
    st.subheader("Optimal weights")
    weights_table = pd.DataFrame(
        {
            "Custom": (weights.reindex(prices.columns).fillna(0.0) * 100).map(
                lambda x: f"{x:.2f}%"
            ),
            "Max Sharpe": (max_sharpe_weights * 100).map(lambda x: f"{x:.2f}%"),
            "Min Variance": (min_var_weights * 100).map(lambda x: f"{x:.2f}%"),
        }
    )
    st.dataframe(weights_table, use_container_width=True)

    # Efficient Frontier plot
    st.subheader("Efficient Frontier")
    asset_points = {
        ticker: (
            float(asset_stats.loc[ticker, "annual_return"]),
            float(asset_stats.loc[ticker, "annual_vol"]),
        )
        for ticker in asset_stats.index
    }
    st.plotly_chart(
        plot_efficient_frontier(
            frontier_df,
            asset_points=asset_points,
            custom_point=port_metrics,
            max_sharpe_point=max_sharpe_metrics,
            min_var_point=min_var_metrics,
        ),
        use_container_width=True,
    )
    st.caption(
        "The **Efficient Frontier** (Markowitz, 1952) is the set of portfolios "
        "offering the highest expected return for a given level of risk. Any "
        "portfolio below the frontier is suboptimal — you could earn more for "
        "the same risk, or take less risk for the same return."
    )


    # ============================================================
    # Tab 6: Benchmark
