from __future__ import annotations

import pandas as pd
import streamlit as st


def render_returns_tab(*, 
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
    st.subheader("Per-asset statistics")
    display_stats = pd.DataFrame(
        {
            "Weight": weights.reindex(asset_stats.index).map(lambda x: f"{x * 100:.2f}%"),
            "Avg daily return": asset_stats["mean_daily"].map(lambda x: f"{x * 100:.3f}%"),
            "Annualized return": asset_stats["annual_return"].map(lambda x: f"{x * 100:.2f}%"),
            "Annualized volatility": asset_stats["annual_vol"].map(lambda x: f"{x * 100:.2f}%"),
        }
    )
    st.dataframe(display_stats, use_container_width=True)

    st.subheader("Daily returns — descriptive statistics")
    st.dataframe(
        returns.describe().T.style.format("{:.4f}"),
        use_container_width=True,
    )
    st.caption(
        "Annualization assumes **252 trading days** per year. "
        "Volatility = σ_daily × √252. Return = μ_daily × 252."
    )


    # ============================================================
    # Tab 3: Correlation
