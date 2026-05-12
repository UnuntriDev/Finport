from __future__ import annotations

import streamlit as st

from visualization import plot_correlation_heatmap


def render_correlation_tab(*, 
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
    st.subheader("Return correlation matrix")
    st.plotly_chart(plot_correlation_heatmap(corr), use_container_width=True)
    st.caption(
        "**+1.0** — assets move in perfect lockstep (no diversification). "
        "**0.0** — uncorrelated (good diversification). "
        "**−1.0** — assets move in opposite directions (maximum hedge)."
    )


    # ============================================================
    # Tab 4: Monte Carlo
