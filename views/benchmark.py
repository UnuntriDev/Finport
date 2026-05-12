"""Benchmark tab — vs equal-weight portfolio and vs S&P 500 market index."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from models import PortfolioAnalysisResult, ViewContext
from ui_components import arrow_for_sign, color_for_sign, metric_card, vertical_spacer
from visualization import plot_portfolio_vs_market, plot_weights_comparison


def render_benchmark_tab(
    result: PortfolioAnalysisResult,
    context: ViewContext,
) -> None:
    """Render benchmark comparisons (equal-weight + S&P 500)."""
    del context
    _render_equal_weight_section(result)
    st.divider()
    _render_market_benchmark_section(result)


def _render_equal_weight_section(result: PortfolioAnalysisResult) -> None:
    st.subheader("Custom portfolio vs. equal-weight benchmark")

    comparison = pd.DataFrame(
        {
            "Custom portfolio": [
                f"{result.portfolio_metrics['return'] * 100:.2f}%",
                f"{result.portfolio_metrics['volatility'] * 100:.2f}%",
                f"{result.portfolio_sharpe:.2f}",
            ],
            "Equal-weight": [
                f"{result.equal_weight_metrics['return'] * 100:.2f}%",
                f"{result.equal_weight_metrics['volatility'] * 100:.2f}%",
                f"{result.equal_weight_sharpe:.2f}",
            ],
        },
        index=["Annualized return", "Annualized volatility", "Sharpe ratio"],
    )
    st.dataframe(comparison, use_container_width=True)
    st.plotly_chart(
        plot_weights_comparison(result.weights, result.equal_weights),
        use_container_width=True,
    )

    combined = pd.concat(
        [
            result.portfolio_value.rename("Custom portfolio"),
            result.equal_weight_value.rename("Equal-weight"),
        ],
        axis=1,
    )
    st.subheader("Cumulative value: custom vs. equal-weight")
    st.line_chart(combined, use_container_width=True)


def _render_market_benchmark_section(result: PortfolioAnalysisResult) -> None:
    st.subheader("Market benchmark — S&P 500")
    if not result.market_loaded:
        st.warning("Could not load S&P 500 data (`^GSPC`). Market comparison skipped.")
        return

    capm = result.capm
    cm1, cm2, cm3, cm4 = st.columns(4)
    with cm1:
        st.markdown(_beta_card(capm["beta"]), unsafe_allow_html=True)
    with cm2:
        st.markdown(_alpha_card(capm["alpha"]), unsafe_allow_html=True)
    with cm3:
        st.markdown(_r_squared_card(capm["r_squared"]), unsafe_allow_html=True)
    with cm4:
        st.markdown(_correlation_card(capm["correlation"]), unsafe_allow_html=True)

    st.markdown(vertical_spacer(20), unsafe_allow_html=True)
    st.plotly_chart(
        plot_portfolio_vs_market(
            result.portfolio_value,
            result.market_value,
            market_label="S&P 500",
        ),
        use_container_width=True,
    )
    st.caption(
        "**CAPM** (Capital Asset Pricing Model, Sharpe 1964) states that an "
        "asset's expected return should equal: rf + β · (market_return − rf). "
        "**Alpha** is the deviation from this prediction — a measure of "
        "manager skill or anomaly. Positive alpha is rare and considered the "
        "holy grail of active management."
    )


def _beta_card(beta: float) -> str:
    if beta < 0.8:
        sub = "Defensive"
    elif beta > 1.2:
        sub = "Aggressive"
    else:
        sub = "Market-like"
    return metric_card(
        "Beta",
        f"{beta:.2f}",
        "Sensitivity to market moves (slope of CAPM regression). β = 1: moves "
        "1-to-1 with market. β > 1: amplifies moves. β < 1: dampens them.",
        sub,
        "#60a5fa",
        "#94a3b8",
    )


def _alpha_card(alpha: float) -> str:
    color = color_for_sign(alpha)
    sub = (
        f"{arrow_for_sign(alpha)} "
        f"{'Beats' if alpha >= 0 else 'Trails'} CAPM expectation"
    )
    return metric_card(
        "Alpha (annual)",
        f"{alpha * 100:+.2f}%",
        "CAPM alpha: excess annualized return beyond what beta exposure to "
        "the market would predict. Positive = portfolio beats the "
        "risk-adjusted market expectation.",
        sub,
        color,
        color,
    )


def _r_squared_card(r_squared: float) -> str:
    if r_squared > 0.7:
        color, sub = "#60a5fa", "High market dependence"
    elif r_squared > 0.3:
        color, sub = "#f59e0b", "Moderate market dependence"
    else:
        color, sub = "#94a3b8", "Independent of market"
    return metric_card(
        "R²",
        f"{r_squared:.2f}",
        "Fraction of portfolio variance explained by market moves. High R² "
        "means the portfolio behaves mostly like the market.",
        sub,
        color,
        "#94a3b8",
    )


def _correlation_card(correlation: float) -> str:
    return metric_card(
        "Correlation",
        f"{correlation:.2f}",
        "Pearson correlation between daily portfolio returns and "
        "S&P 500 daily returns.",
        "Strength of co-movement",
        "#60a5fa",
        "#94a3b8",
    )
