from __future__ import annotations

import streamlit as st

from ui_components import metric_card


def render_assumptions_tab(*, 
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
    st.subheader("Model assumptions")
    st.markdown(
        '<p style="color:#64748b; font-size:14px; margin-bottom:20px;">'
        "FinPort is an educational analytics tool. These assumptions explain "
        "how to interpret the results responsibly."
        "</p>",
        unsafe_allow_html=True,
    )

    a1, a2 = st.columns(2)
    with a1:
        market_value = "Demo data" if demo_mode else "Yahoo Finance"
        market_note = (
            "Adjusted close prices are generated locally for offline demos. "
            "They are deterministic sample data, not real market prices."
            if demo_mode
            else "Adjusted close prices are downloaded from Yahoo Finance via "
            "yfinance. Missing, delisted or incorrect symbols are excluded."
        )
        st.markdown(
            metric_card(
                "Market Data",
                market_value,
                market_note,
                "Offline sample" if demo_mode else "External data source",
                "#60a5fa",
                "#94a3b8",
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            metric_card(
                "Portfolio Method",
                "Buy-and-hold",
                "Portfolio value assumes the initial weights are set on the "
                "first day and then held. Transaction costs, taxes and slippage "
                "are not included.",
                "No periodic rebalancing",
                "#f59e0b",
                "#94a3b8",
            ),
            unsafe_allow_html=True,
        )
    with a2:
        st.markdown(
            metric_card(
                "Annualization",
                "252 days",
                "Daily return and volatility metrics are annualized using the "
                "standard convention of 252 trading days per year.",
                "Finance convention",
                "#10b981",
                "#94a3b8",
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            metric_card(
                "Monte Carlo",
                mc_method_label,
                "Parametric simulation uses historical mean and covariance; "
                "bootstrap simulation resamples historical daily return rows. "
                "Both assume the selected period is representative.",
                "Scenario model, not prediction",
                "#a78bfa",
                "#94a3b8",
            ),
            unsafe_allow_html=True,
        )

    st.info(
        "Educational disclaimer: FinPort does not provide investment advice. "
        "Past performance, optimization output and Monte Carlo scenarios do not "
        "guarantee future results."
    )


    # ============================================================
    # Tab 9: Glossary
