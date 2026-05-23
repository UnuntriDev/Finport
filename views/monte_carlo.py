"""Monte Carlo tab."""
from __future__ import annotations

import streamlit as st

from models import PortfolioAnalysisResult, ViewContext
from ui_components import arrow_for_sign, color_for_sign, metric_card, vertical_spacer
from visualization import plot_monte_carlo

_METHOD_CAPTIONS = {
    "bootstrap": (
        "Method: **Historical bootstrap**. Each simulated day samples one "
        "historical return row with replacement, preserving empirical joint "
        "asset moves. It avoids a normality assumption but still assumes "
        "historical return patterns are relevant."
    ),
    "parametric": (
        "Method: **Parametric normal**. Each path is drawn from a multivariate "
        "normal distribution using historical mean and covariance. Cross-asset "
        "correlations are preserved via **Cholesky decomposition**."
    ),
}


def render_monte_carlo_tab(
    result: PortfolioAnalysisResult,
    context: ViewContext,
) -> None:
    initial = context.initial_investment
    st.subheader("Monte Carlo simulation of portfolio value")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(_median_card(result.mc_p50, initial), unsafe_allow_html=True)
    with m2:
        st.markdown(_percentile_card(
            "5th Percentile",
            result.mc_p5,
            initial,
            "Pessimistic outcome: only 5% of simulations end lower than this. "
            "Represents a bad-case scenario.",
        ), unsafe_allow_html=True)
    with m3:
        st.markdown(_percentile_card(
            "95th Percentile",
            result.mc_p95,
            initial,
            "Optimistic outcome: only 5% of simulations end higher than this. "
            "Represents a best-case scenario.",
        ), unsafe_allow_html=True)
    with m4:
        st.markdown(_var_card(result.var_95), unsafe_allow_html=True)

    st.markdown(vertical_spacer(20), unsafe_allow_html=True)
    st.plotly_chart(plot_monte_carlo(result.simulations), use_container_width=True)
    st.caption(_METHOD_CAPTIONS.get(context.mc_method, _METHOD_CAPTIONS["parametric"]))


def _median_card(median: float, initial: float) -> str:
    pct = _pct_vs_initial(median, initial)
    return metric_card(
        "Median Outcome",
        f"${median:,.0f}",
        "The 50th percentile of simulated final values. Half of all simulated "
        "paths end above this value.",
        f"{arrow_for_sign(pct)} {abs(pct):.1f}% vs. initial",
        "#60a5fa",
        "#475569",
    )


def _percentile_card(label: str, value: float, initial: float, tooltip: str) -> str:
    pct = _pct_vs_initial(value, initial)
    color = color_for_sign(pct)
    arrow = arrow_for_sign(pct)
    sub = f"{arrow} {abs(pct):.1f}% vs. initial"
    return metric_card(label, f"${value:,.0f}", tooltip, sub, color, color)


def _var_card(var_95: float) -> str:
    return metric_card(
        "VaR 95%",
        f"${var_95:,.0f}",
        "Value at Risk at 95% confidence: the maximum loss not exceeded in "
        "95% of simulated scenarios, relative to the initial investment.",
        "Max loss in 95% of cases",
        "#f59e0b",
        "#475569",
    )


def _pct_vs_initial(value: float, initial: float) -> float:
    if initial <= 0:
        return 0.0
    return (value / initial - 1.0) * 100.0
