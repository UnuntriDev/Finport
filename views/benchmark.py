from __future__ import annotations

import pandas as pd
import streamlit as st

from models import PortfolioAnalysisResult, ViewContext
from ui_components import metric_card, vertical_spacer
from visualization import plot_portfolio_vs_market, plot_weights_comparison


def render_benchmark_tab(result: PortfolioAnalysisResult, context: ViewContext) -> None:
    weights = result.weights
    port_metrics = result.portfolio_metrics
    sharpe = result.portfolio_sharpe
    port_value = result.portfolio_value
    equal_weights = result.equal_weights
    eq_metrics = result.equal_weight_metrics
    eq_sharpe = result.equal_weight_sharpe
    eq_value = result.equal_weight_value
    market_value = result.market_value
    capm = result.capm
    market_loaded = result.market_loaded
    st.subheader("Custom portfolio vs. equal-weight benchmark")

    comparison_fmt = pd.DataFrame(
        {
            "Custom portfolio": [
                f"{port_metrics['return'] * 100:.2f}%",
                f"{port_metrics['volatility'] * 100:.2f}%",
                f"{sharpe:.2f}",
            ],
            "Equal-weight": [
                f"{eq_metrics['return'] * 100:.2f}%",
                f"{eq_metrics['volatility'] * 100:.2f}%",
                f"{eq_sharpe:.2f}",
            ],
        },
        index=["Annualized return", "Annualized volatility", "Sharpe ratio"],
    )
    st.dataframe(comparison_fmt, use_container_width=True)

    st.plotly_chart(
        plot_weights_comparison(weights, equal_weights),
        use_container_width=True,
    )

    combined = pd.concat(
        [port_value.rename("Custom portfolio"), eq_value.rename("Equal-weight")],
        axis=1,
    )
    st.subheader("Cumulative value: custom vs. equal-weight")
    st.line_chart(combined, use_container_width=True)

    st.divider()
    st.subheader("Market benchmark — S&P 500")

    if not market_loaded:
        st.warning("Could not load S&P 500 data (`^GSPC`). Market comparison skipped.")
    else:
        cm1, cm2, cm3, cm4 = st.columns(4)
        with cm1:
            st.markdown(
                metric_card(
                    "Beta",
                    f"{capm['beta']:.2f}",
                    "Sensitivity to market moves (slope of CAPM regression). "
                    "β = 1: moves 1-to-1 with market. β > 1: amplifies moves. "
                    "β < 1: dampens them.",
                    "Defensive" if capm["beta"] < 0.8 else "Aggressive" if capm["beta"] > 1.2 else "Market-like",
                    "#60a5fa", "#94a3b8",
                ),
                unsafe_allow_html=True,
            )
        with cm2:
            a_color = "#10b981" if capm["alpha"] >= 0 else "#ef4444"
            a_arrow = "▲" if capm["alpha"] >= 0 else "▼"
            st.markdown(
                metric_card(
                    "Alpha (annual)",
                    f"{capm['alpha'] * 100:+.2f}%",
                    "CAPM alpha: excess annualized return beyond what beta "
                    "exposure to the market would predict. Positive = portfolio "
                    "beats the risk-adjusted market expectation.",
                    f"{a_arrow} {'Beats' if capm['alpha'] >= 0 else 'Trails'} CAPM expectation",
                    a_color, a_color,
                ),
                unsafe_allow_html=True,
            )
        with cm3:
            r2_color = "#60a5fa" if capm["r_squared"] > 0.7 else "#f59e0b" if capm["r_squared"] > 0.3 else "#94a3b8"
            r2_sub = (
                "High market dependence" if capm["r_squared"] > 0.7
                else "Moderate market dependence" if capm["r_squared"] > 0.3
                else "Independent of market"
            )
            st.markdown(
                metric_card(
                    "R²",
                    f"{capm['r_squared']:.2f}",
                    "Fraction of portfolio variance explained by market moves. "
                    "High R² means the portfolio behaves mostly like the market.",
                    r2_sub, r2_color, "#94a3b8",
                ),
                unsafe_allow_html=True,
            )
        with cm4:
            st.markdown(
                metric_card(
                    "Correlation",
                    f"{capm['correlation']:.2f}",
                    "Pearson correlation between daily portfolio returns and "
                    "S&P 500 daily returns.",
                    "Strength of co-movement",
                    "#60a5fa", "#94a3b8",
                ),
                unsafe_allow_html=True,
            )

        st.markdown(vertical_spacer(20), unsafe_allow_html=True)

        st.plotly_chart(
            plot_portfolio_vs_market(port_value, market_value, market_label="S&P 500"),
            use_container_width=True,
        )

        st.caption(
            "**CAPM** (Capital Asset Pricing Model, Sharpe 1964) states that an "
            "asset's expected return should equal: rf + β · (market_return − rf). "
            "**Alpha** is the deviation from this prediction — a measure of "
            "manager skill or anomaly. Positive alpha is rare and considered the "
            "holy grail of active management."
        )


    # ============================================================
    # Tab 6: Export
