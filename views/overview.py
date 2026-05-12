"""Overview tab — top-level portfolio metrics, charts and sector breakdown."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from data_loader import load_sector_info
from demo_data import DEMO_SECTORS
from models import PortfolioAnalysisResult, ViewContext
from theme import COLORS
from ui_components import (
    arrow_for_sign,
    color_for_sign,
    color_for_threshold,
    metric_card,
    vertical_spacer,
)
from visualization import (
    plot_drawdown,
    plot_normalized_prices,
    plot_portfolio_value,
    plot_price_history,
    plot_sector_breakdown,
)


def render_overview_tab(result: PortfolioAnalysisResult, context: ViewContext) -> None:
    """Render the overview tab: KPI cards, prices, drawdown and sector breakdown."""
    _render_primary_metrics(result, context)
    st.markdown(vertical_spacer(20), unsafe_allow_html=True)
    _render_risk_metrics(result, context)

    st.markdown(vertical_spacer(20), unsafe_allow_html=True)
    st.divider()
    _render_charts(result, context)
    _render_drawdown_details(result)
    st.divider()
    _render_sector_breakdown(result, context)


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def _render_primary_metrics(result: PortfolioAnalysisResult, context: ViewContext) -> None:
    ann_ret = result.portfolio_metrics["return"]
    ann_vol = result.portfolio_metrics["volatility"]
    final_val = float(result.portfolio_value.iloc[-1])
    initial = context.initial_investment
    pnl_pct = _safe_pct_change(final_val, initial)

    ret_vs_rf = ann_ret - context.risk_free_rate
    ret_sub = (
        f"{arrow_for_sign(ret_vs_rf)} {abs(ret_vs_rf * 100):.2f}% "
        f"{'above' if ret_vs_rf >= 0 else 'below'} risk-free rate"
    )

    sharpe = result.portfolio_sharpe
    sharpe_color = color_for_threshold(sharpe, 1.0, 0.5)
    sharpe_sub = _sharpe_sub_label(sharpe)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(
            metric_card(
                "Annualized Return",
                f"{ann_ret * 100:.2f}%",
                "Historical average daily return × 252 trading days. "
                "Represents the expected yearly gain of the portfolio.",
                ret_sub,
                color_for_sign(ann_ret),
                color_for_sign(ret_vs_rf),
            ),
            unsafe_allow_html=True,
        )
    with c2:
        cagr_color = color_for_sign(result.portfolio_cagr)
        st.markdown(
            metric_card(
                "CAGR",
                f"{result.portfolio_cagr * 100:.2f}%",
                "Compound Annual Growth Rate based on actual portfolio value "
                "growth over the selected period.",
                "Compounded realized growth",
                cagr_color,
                cagr_color,
            ),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            metric_card(
                "Annualized Volatility",
                f"{ann_vol * 100:.2f}%",
                "Standard deviation of daily returns × √252. Measures total "
                "portfolio risk — higher = more uncertain outcomes.",
                "Risk measure (std. deviation)",
                "#60a5fa",
                "#475569",
            ),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            metric_card(
                "Sharpe Ratio",
                f"{sharpe:.2f}",
                "Risk-adjusted return = (Portfolio return − Risk-free rate) / "
                "Volatility. > 1.0 is considered good.",
                sharpe_sub,
                sharpe_color,
                sharpe_color,
            ),
            unsafe_allow_html=True,
        )
    with c5:
        pnl_color = color_for_sign(pnl_pct)
        st.markdown(
            metric_card(
                "Portfolio Value",
                f"${final_val:,.0f}",
                f"Final value of a ${initial:,.0f} initial investment held as "
                "a buy-and-hold portfolio over the selected period.",
                f"{arrow_for_sign(pnl_pct)} {abs(pnl_pct):.2f}% total return",
                pnl_color,
                pnl_color,
            ),
            unsafe_allow_html=True,
        )


def _render_risk_metrics(result: PortfolioAnalysisResult, context: ViewContext) -> None:
    dd_info = result.drawdown_info
    max_dd_pct = dd_info["max_drawdown"] * 100
    dd_color = color_for_threshold(max_dd_pct, -10.0, -20.0)

    sortino = result.sortino
    sortino_color = color_for_threshold(sortino, 1.0, 0.5)
    sortino_sub = _sortino_sub_label(sortino)

    dd_days_text = (
        f"{dd_info['drawdown_days']} days peak → trough"
        if dd_info["drawdown_days"] else "—"
    )

    capm = result.capm
    market_loaded = result.market_loaded
    beta_value = f"{capm['beta']:.2f}" if market_loaded else "—"
    beta_sub = (
        "S&P 500 data unavailable"
        if not market_loaded
        else "Defensive" if capm["beta"] < 0.8
        else "Aggressive" if capm["beta"] > 1.2
        else "Neutral"
    )
    beta_color = "#60a5fa" if market_loaded else COLORS["muted"]

    alpha_value = f"{capm['alpha'] * 100:+.2f}%" if market_loaded else "—"
    alpha_color = (
        color_for_sign(capm["alpha"]) if market_loaded else COLORS["muted"]
    )
    alpha_sub = (
        "—"
        if not market_loaded
        else f"{arrow_for_sign(capm['alpha'])} "
        f"{'Beats' if capm['alpha'] >= 0 else 'Trails'} S&P 500 (CAPM)"
    )

    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.markdown(
            metric_card(
                "Max Drawdown",
                f"{max_dd_pct:.2f}%",
                "The largest peak-to-trough decline. Crucial risk metric — "
                "shows the worst loss an investor would have experienced.",
                dd_days_text,
                dd_color,
                dd_color,
            ),
            unsafe_allow_html=True,
        )
    with d2:
        st.markdown(
            metric_card(
                "Sortino Ratio",
                f"{sortino:.2f}",
                "Like Sharpe ratio, but only penalizes downside volatility. "
                "More realistic for investors — upward volatility is not risk.",
                sortino_sub,
                sortino_color,
                sortino_color,
            ),
            unsafe_allow_html=True,
        )
    with d3:
        st.markdown(
            metric_card(
                "Beta vs S&P 500",
                beta_value,
                "Sensitivity to market moves. β = 1 means moves with market; "
                "β > 1 more volatile; β < 1 defensive; β < 0 inverse.",
                beta_sub,
                beta_color,
                beta_color if market_loaded else COLORS["muted"],
            ),
            unsafe_allow_html=True,
        )
    with d4:
        st.markdown(
            metric_card(
                "Alpha (CAPM)",
                alpha_value,
                "Annualized excess return not explained by market exposure "
                "(beta). Positive alpha = portfolio beats CAPM expectation.",
                alpha_sub,
                alpha_color,
                alpha_color,
            ),
            unsafe_allow_html=True,
        )


def _render_charts(result: PortfolioAnalysisResult, context: ViewContext) -> None:
    st.subheader("Adjusted closing prices")
    st.plotly_chart(plot_price_history(result.prices), use_container_width=True)

    st.subheader("Normalized performance  (start = 100)")
    st.plotly_chart(
        plot_normalized_prices(result.normalized_prices),
        use_container_width=True,
    )

    st.subheader("Portfolio value over time")
    st.plotly_chart(
        plot_portfolio_value(result.portfolio_value, context.initial_investment),
        use_container_width=True,
    )

    st.subheader("Drawdown analysis")
    dd_info = result.drawdown_info
    st.plotly_chart(
        plot_drawdown(
            dd_info["drawdown_series"],
            dd_info["max_drawdown"],
            dd_info["trough_date"],
        ),
        use_container_width=True,
    )


def _render_drawdown_details(result: PortfolioAnalysisResult) -> None:
    dd_info = result.drawdown_info
    recovery_text = (
        f"Recovered after {dd_info['recovery_days']} days"
        if dd_info["recovery_days"] is not None
        else "Not yet recovered"
    )
    cols = st.columns(3)
    cols[0].markdown(f"**Peak date:** {dd_info['peak_date'].date()}")
    cols[1].markdown(f"**Trough date:** {dd_info['trough_date'].date()}")
    cols[2].markdown(f"**Status:** {recovery_text}")


def _render_sector_breakdown(
    result: PortfolioAnalysisResult,
    context: ViewContext,
) -> None:
    st.subheader("Sector allocation")
    sector_info = _resolve_sector_info(result.prices.columns, context.demo_mode)

    sector_weights: dict[str, float] = {}
    for ticker, share in result.weights.items():
        sec = sector_info.get(ticker, "Others")
        sector_weights[sec] = sector_weights.get(sec, 0.0) + float(share) * 100.0

    sec_col1, sec_col2 = st.columns([1, 1])
    with sec_col1:
        st.plotly_chart(
            plot_sector_breakdown(sector_weights),
            use_container_width=True,
        )
    with sec_col2:
        st.markdown(vertical_spacer(24), unsafe_allow_html=True)
        sector_table = pd.DataFrame(
            [
                {"Sector": sec, "Weight": f"{weight:.2f}%"}
                for sec, weight in sorted(
                    sector_weights.items(), key=lambda item: -item[1]
                )
            ]
        )
        st.dataframe(sector_table, use_container_width=True, hide_index=True)
        st.caption(
            "Sector data fetched from Yahoo Finance. Higher concentration in "
            "one sector = higher idiosyncratic risk."
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_pct_change(final_value: float, initial_value: float) -> float:
    """Return percentage change (0.0 when initial is non-positive)."""
    if initial_value <= 0:
        return 0.0
    return (final_value / initial_value - 1.0) * 100.0


def _sharpe_sub_label(sharpe: float) -> str:
    if sharpe >= 1.0:
        return "▲ Excellent  (≥ 1.0)"
    if sharpe >= 0.5:
        return "◆ Acceptable  (0.5 – 1.0)"
    return "▼ Low  (< 0.5)"


def _sortino_sub_label(sortino: float) -> str:
    if sortino >= 1.0:
        return "▲ Excellent  (≥ 1.0)"
    if sortino >= 0.5:
        return "◆ Acceptable  (0.5 – 1.0)"
    return "▼ Low  (< 0.5)"


def _resolve_sector_info(tickers: pd.Index, demo_mode: bool) -> dict[str, str]:
    if demo_mode:
        return {ticker: DEMO_SECTORS.get(ticker, "Others") for ticker in tickers}
    with st.spinner("Looking up sector classifications..."):
        return load_sector_info(list(tickers))
