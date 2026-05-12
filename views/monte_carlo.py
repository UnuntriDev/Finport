from __future__ import annotations

import streamlit as st

from ui_components import metric_card
from visualization import plot_monte_carlo


def render_monte_carlo_tab(*, 
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
    st.subheader("Monte Carlo simulation of portfolio value")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            metric_card(
                "Median Outcome",
                f"${mc_p50:,.0f}",
                "The 50th percentile of simulated final values. "
                "Half of all simulated paths end above this value.",
                f"{'▲' if mc_p50 >= initial_investment else '▼'} "
                f"{abs((mc_p50 / initial_investment - 1) * 100):.1f}% vs. initial",
                "#60a5fa", "#475569",
            ),
            unsafe_allow_html=True,
        )
    with m2:
        p5_pct = (mc_p5 / initial_investment - 1) * 100
        st.markdown(
            metric_card(
                "5th Percentile",
                f"${mc_p5:,.0f}",
                "Pessimistic outcome: only 5% of simulations end lower than this. "
                "Represents a bad-case scenario.",
                f"▼ {abs(p5_pct):.1f}% vs. initial" if p5_pct < 0
                else f"▲ {p5_pct:.1f}% vs. initial",
                "#ef4444" if p5_pct < 0 else "#10b981",
                "#ef4444" if p5_pct < 0 else "#10b981",
            ),
            unsafe_allow_html=True,
        )
    with m3:
        p95_pct = (mc_p95 / initial_investment - 1) * 100
        st.markdown(
            metric_card(
                "95th Percentile",
                f"${mc_p95:,.0f}",
                "Optimistic outcome: only 5% of simulations end higher than this. "
                "Represents a best-case scenario.",
                f"▲ {p95_pct:.1f}% vs. initial",
                "#10b981", "#10b981",
            ),
            unsafe_allow_html=True,
        )
    with m4:
        st.markdown(
            metric_card(
                "VaR 95%",
                f"${var_95:,.0f}",
                "Value at Risk at 95% confidence: the maximum loss not exceeded "
                "in 95% of simulated scenarios, relative to the initial investment.",
                "Max loss in 95% of cases",
                "#f59e0b", "#475569",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)
    st.plotly_chart(plot_monte_carlo(sims), use_container_width=True)
    if mc_method == "bootstrap":
        st.caption(
            "Method: **Historical bootstrap**. Each simulated day samples one "
            "historical return row with replacement, preserving empirical joint "
            "asset moves. It avoids a normality assumption but still assumes "
            "historical return patterns are relevant."
        )
    else:
        st.caption(
            "Method: **Parametric normal**. Each path is drawn from a multivariate "
            "normal distribution using historical mean and covariance. Cross-asset "
            "correlations are preserved via **Cholesky decomposition**."
        )


    # ============================================================
    # Tab 5: Optimization (Efficient Frontier + Max Sharpe + Min Variance)
