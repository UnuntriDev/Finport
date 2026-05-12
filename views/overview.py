from __future__ import annotations

import pandas as pd
import streamlit as st

from data_loader import load_sector_info
from demo_data import DEMO_SECTORS
from ui_components import metric_card
from visualization import (
    plot_drawdown,
    plot_normalized_prices,
    plot_portfolio_value,
    plot_price_history,
    plot_sector_breakdown,
)


def render_overview_tab(*, 
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
    # --- Colored metric cards ---
    ann_ret = port_metrics["return"]
    ann_vol = port_metrics["volatility"]
    final_val = float(port_value.iloc[-1])
    pnl_pct = (final_val / initial_investment - 1) * 100

    ret_color = "#10b981" if ann_ret > 0 else "#ef4444"
    ret_vs_rf = ann_ret - risk_free_rate
    ret_arrow = "▲" if ret_vs_rf >= 0 else "▼"
    ret_sub = (
        f"{ret_arrow} {abs(ret_vs_rf * 100):.2f}% "
        f"{'above' if ret_vs_rf >= 0 else 'below'} risk-free rate"
    )
    ret_sub_color = "#10b981" if ret_vs_rf >= 0 else "#ef4444"

    if sharpe >= 1.0:
        sharpe_color, sharpe_sub = "#10b981", "▲ Excellent  (≥ 1.0)"
    elif sharpe >= 0.5:
        sharpe_color, sharpe_sub = "#f59e0b", "◆ Acceptable  (0.5 – 1.0)"
    else:
        sharpe_color, sharpe_sub = "#ef4444", "▼ Low  (< 0.5)"

    pnl_color = "#10b981" if pnl_pct >= 0 else "#ef4444"
    pnl_arrow = "▲" if pnl_pct >= 0 else "▼"

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(
            metric_card(
                "Annualized Return",
                f"{ann_ret * 100:.2f}%",
                "Historical average daily return × 252 trading days. "
                "Represents the expected yearly gain of the portfolio.",
                ret_sub, ret_color, ret_sub_color,
            ),
            unsafe_allow_html=True,
        )
    with c2:
        cagr_color = "#10b981" if portfolio_cagr >= 0 else "#ef4444"
        st.markdown(
            metric_card(
                "CAGR",
                f"{portfolio_cagr * 100:.2f}%",
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
                "Standard deviation of daily returns × √252. "
                "Measures total portfolio risk — higher = more uncertain outcomes.",
                "Risk measure (std. deviation)",
                "#60a5fa", "#475569",
            ),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            metric_card(
                "Sharpe Ratio",
                f"{sharpe:.2f}",
                "Risk-adjusted return = (Portfolio return − Risk-free rate) / Volatility. "
                "Measures return earned per unit of risk. > 1.0 is considered good.",
                sharpe_sub, sharpe_color, sharpe_color,
            ),
            unsafe_allow_html=True,
        )
    with c5:
        st.markdown(
            metric_card(
                "Portfolio Value",
                f"${final_val:,.0f}",
                f"Final value of a ${initial_investment:,.0f} initial investment "
                "held as a buy-and-hold portfolio over the selected period.",
                f"{pnl_arrow} {abs(pnl_pct):.2f}% total return",
                pnl_color, pnl_color,
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)

    # Second row of metrics: drawdown + sortino
    max_dd_pct = dd_info["max_drawdown"] * 100
    dd_color = "#ef4444" if max_dd_pct < -20 else "#f59e0b" if max_dd_pct < -10 else "#10b981"
    sortino_color = "#10b981" if sortino >= 1.0 else "#f59e0b" if sortino >= 0.5 else "#ef4444"

    if sortino >= 1.0:
        sortino_sub = "▲ Excellent  (≥ 1.0)"
    elif sortino >= 0.5:
        sortino_sub = "◆ Acceptable  (0.5 – 1.0)"
    else:
        sortino_sub = "▼ Low  (< 0.5)"

    dd_days_text = (
        f"{dd_info['drawdown_days']} days peak → trough"
        if dd_info["drawdown_days"] else "—"
    )
    recovery_text = (
        f"Recovered after {dd_info['recovery_days']} days"
        if dd_info["recovery_days"] is not None
        else "Not yet recovered"
    )

    if market_loaded:
        beta_color = "#60a5fa"
        beta_sub = "Defensive" if capm["beta"] < 0.8 else "Aggressive" if capm["beta"] > 1.2 else "Neutral"
        alpha_color = "#10b981" if capm["alpha"] > 0 else "#ef4444"
        alpha_arrow = "▲" if capm["alpha"] >= 0 else "▼"
        alpha_sub = f"{alpha_arrow} {'Beats' if capm['alpha'] >= 0 else 'Trails'} S&P 500 (CAPM)"
    else:
        beta_color = "#475569"
        beta_sub = "S&P 500 data unavailable"
        alpha_color = "#475569"
        alpha_sub = "—"

    d1, d2, d3, d4 = st.columns(4)
    with d1:
        st.markdown(
            metric_card(
                "Max Drawdown",
                f"{max_dd_pct:.2f}%",
                "The largest peak-to-trough decline. Crucial risk metric — "
                "shows the worst loss an investor would have experienced.",
                dd_days_text, dd_color, dd_color,
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
                sortino_sub, sortino_color, sortino_color,
            ),
            unsafe_allow_html=True,
        )
    with d3:
        st.markdown(
            metric_card(
                "Beta vs S&P 500",
                f"{capm['beta']:.2f}" if market_loaded else "—",
                "Sensitivity to market moves. β = 1 means moves with market; "
                "β > 1 more volatile; β < 1 defensive; β < 0 inverse.",
                beta_sub, beta_color, "#475569" if not market_loaded else beta_color,
            ),
            unsafe_allow_html=True,
        )
    with d4:
        st.markdown(
            metric_card(
                "Alpha (CAPM)",
                f"{capm['alpha'] * 100:+.2f}%" if market_loaded else "—",
                "Annualized excess return not explained by market exposure "
                "(beta). Positive alpha = portfolio beats CAPM expectation.",
                alpha_sub, alpha_color, alpha_color,
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)
    st.divider()

    st.subheader("Adjusted closing prices")
    st.plotly_chart(plot_price_history(prices), use_container_width=True)

    st.subheader("Normalized performance  (start = 100)")
    st.plotly_chart(plot_normalized_prices(norm), use_container_width=True)

    st.subheader("Portfolio value over time")
    st.plotly_chart(plot_portfolio_value(port_value, initial_investment), use_container_width=True)

    st.subheader("Drawdown analysis")
    st.plotly_chart(
        plot_drawdown(
            dd_info["drawdown_series"],
            dd_info["max_drawdown"],
            dd_info["trough_date"],
        ),
        use_container_width=True,
    )
    dd_cols = st.columns(3)
    dd_cols[0].markdown(
        f"**Peak date:** {dd_info['peak_date'].date()}"
    )
    dd_cols[1].markdown(
        f"**Trough date:** {dd_info['trough_date'].date()}"
    )
    dd_cols[2].markdown(f"**Status:** {recovery_text}")

    # ---- Sector Breakdown ------------------------------------------------
    st.divider()
    st.subheader("Sector allocation")
    if demo_mode:
        sector_info = {
            ticker: DEMO_SECTORS.get(ticker, "Others")
            for ticker in prices.columns
        }
    else:
        with st.spinner("Looking up sector classifications..."):
            sector_info = load_sector_info(list(prices.columns))

    # Aggregate weights by sector
    sector_weights: dict[str, float] = {}
    for ticker, weight_share in weights.items():
        sec = sector_info.get(ticker, "Others")
        sector_weights[sec] = sector_weights.get(sec, 0.0) + float(weight_share) * 100.0

    sec_col1, sec_col2 = st.columns([1, 1])
    with sec_col1:
        st.plotly_chart(
            plot_sector_breakdown(sector_weights),
            use_container_width=True,
        )
    with sec_col2:
        st.markdown(
            '<div style="margin-top:24px;"></div>', unsafe_allow_html=True,
        )
        sector_table = pd.DataFrame(
            [
                {"Sector": sec, "Weight": f"{w:.2f}%"}
                for sec, w in sorted(
                    sector_weights.items(), key=lambda x: -x[1]
                )
            ]
        )
        st.dataframe(sector_table, use_container_width=True, hide_index=True)
        st.caption(
            "Sector data fetched from Yahoo Finance. "
            "Higher concentration in one sector = higher idiosyncratic risk."
        )


    # ============================================================
    # Tab 2: Returns & Risk
