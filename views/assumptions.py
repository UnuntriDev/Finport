from __future__ import annotations

import streamlit as st

from models import PortfolioAnalysisResult, ViewContext
from ui_components import metric_card, muted_paragraph


def render_assumptions_tab(result: PortfolioAnalysisResult, context: ViewContext) -> None:
    del result
    st.subheader("Model assumptions")
    st.markdown(
        muted_paragraph(
            "FinPort is an educational analytics tool. These assumptions explain "
            "how to interpret the results responsibly.",
            margin_bottom=20,
        ),
        unsafe_allow_html=True,
    )

    a1, a2 = st.columns(2)
    with a1:
        st.markdown(_market_data_card(context.demo_mode), unsafe_allow_html=True)
        st.markdown(_portfolio_method_card(), unsafe_allow_html=True)
    with a2:
        st.markdown(_annualization_card(), unsafe_allow_html=True)
        st.markdown(_monte_carlo_card(context.mc_method_label), unsafe_allow_html=True)

    st.info(
        "Educational disclaimer: FinPort does not provide investment advice. "
        "Past performance, optimization output and Monte Carlo scenarios do not "
        "guarantee future results."
    )


def _market_data_card(demo_mode: bool) -> str:
    data_source = "Demo data" if demo_mode else "Yahoo Finance"
    tooltip = (
        "Adjusted close prices are generated locally for offline demos. "
        "They are deterministic sample data, not real market prices."
        if demo_mode
        else "Adjusted close prices are downloaded from Yahoo Finance via "
        "yfinance. Missing, delisted or incorrect symbols are excluded."
    )
    sub = "Offline sample" if demo_mode else "External data source"
    return metric_card("Market Data", data_source, tooltip, sub, "#60a5fa", "#94a3b8")


def _portfolio_method_card() -> str:
    return metric_card(
        "Portfolio Method",
        "Buy-and-hold",
        "Portfolio value assumes the initial weights are set on the first day "
        "and then held. Transaction costs, taxes and slippage are not included.",
        "No periodic rebalancing",
        "#f59e0b",
        "#94a3b8",
    )


def _annualization_card() -> str:
    return metric_card(
        "Annualization",
        "252 days",
        "Daily return and volatility metrics are annualized using the standard "
        "convention of 252 trading days per year.",
        "Finance convention",
        "#10b981",
        "#94a3b8",
    )


def _monte_carlo_card(method_label: str) -> str:
    return metric_card(
        "Monte Carlo",
        method_label,
        "Parametric simulation uses historical mean and covariance; bootstrap "
        "simulation resamples historical daily return rows. Both assume the "
        "selected period is representative.",
        "Scenario model, not prediction",
        "#a78bfa",
        "#94a3b8",
    )
