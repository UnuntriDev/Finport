from __future__ import annotations

import pandas as pd
import streamlit as st

from ui_components import metric_card
from visualization import plot_efficient_frontier


def render_optimization_tab(*, 
    prices,
    weights,
    returns,
    norm,
    asset_stats,
    port_metrics,
    sharpe,
    corr,
    port_value,
    portfolio_cagr,
    equal_weights,
    eq_metrics,
    eq_sharpe,
    eq_value,
    dd_info,
    sortino,
    max_sharpe_weights,
    min_var_weights,
    max_sharpe_metrics,
    min_var_metrics,
    max_sharpe_value,
    min_var_sharpe,
    frontier_df,
    market_value,
    capm,
    market_loaded,
    sims,
    mc_p5,
    mc_p50,
    mc_p95,
    var_95,
    mc_method,
    start_date,
    end_date,
    initial_investment,
    risk_free_rate,
    mc_horizon_days,
    mc_method_label,
    demo_mode,
) -> None:
    st.subheader("Markowitz Portfolio Optimization")
    st.markdown(
        '<p style="color:#64748b; font-size:14px; margin-bottom:20px;">'
        "Two classical optimal portfolios computed by minimizing variance under "
        "constraints (long-only, sum of weights = 1). The <b>Efficient Frontier</b> "
        "below shows the best achievable risk/return trade-offs."
        "</p>",
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

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

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
