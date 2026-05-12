"""Dashboard tab rendering for FinPort."""
from __future__ import annotations

import logging
from datetime import date

import pandas as pd
import streamlit as st

from content.glossary import GLOSSARY_SOURCES, GLOSSARY_TERMS
from data_loader import load_sector_info
from models import PortfolioAnalysisResult
from report_exporter import (
    build_excel_workbook,
    build_pdf,
    prices_to_csv,
    returns_to_csv,
    summary_to_csv,
)
from ui_components import (
    export_item_label,
    export_section_header,
    metric_card,
)
from visualization import (
    plot_correlation_heatmap,
    plot_drawdown,
    plot_efficient_frontier,
    plot_monte_carlo,
    plot_normalized_prices,
    plot_portfolio_value,
    plot_portfolio_vs_market,
    plot_price_history,
    plot_sector_breakdown,
    plot_weights_comparison,
)

logger = logging.getLogger(__name__)


def render_dashboard_tabs(
    result: PortfolioAnalysisResult,
    start_date: date,
    end_date: date,
    initial_investment: float,
    risk_free_rate: float,
    mc_horizon_days: int,
    mc_method_label: str,
) -> None:
    """Render all analysis dashboard tabs."""
    prices = result.prices
    weights = result.weights
    returns = result.returns
    norm = result.normalized_prices
    asset_stats = result.asset_stats
    port_metrics = result.portfolio_metrics
    sharpe = result.portfolio_sharpe
    corr = result.correlation
    port_value = result.portfolio_value
    portfolio_cagr = result.portfolio_cagr
    equal_weights = result.equal_weights
    eq_metrics = result.equal_weight_metrics
    eq_sharpe = result.equal_weight_sharpe
    eq_value = result.equal_weight_value
    dd_info = result.drawdown_info
    sortino = result.sortino
    max_sharpe_weights = result.max_sharpe_weights
    min_var_weights = result.min_variance_weights
    max_sharpe_metrics = result.max_sharpe_metrics
    min_var_metrics = result.min_variance_metrics
    max_sharpe_value = result.max_sharpe_ratio
    min_var_sharpe = result.min_variance_sharpe
    frontier_df = result.efficient_frontier
    market_value = result.market_value
    capm = result.capm
    market_loaded = result.market_loaded
    sims = result.simulations
    mc_p5 = result.mc_p5
    mc_p50 = result.mc_p50
    mc_p95 = result.mc_p95
    var_95 = result.var_95
    mc_method = "bootstrap" if mc_method_label == "Historical bootstrap" else "parametric"

    # ---------------------------------------------------------------------------
    # Tabs
    # ---------------------------------------------------------------------------
    (
        tab_overview, tab_returns, tab_corr, tab_mc, tab_opt, tab_bench,
        tab_export, tab_assumptions, tab_glossary,
    ) = st.tabs([
        "Overview", "Returns & Risk", "Correlation", "Monte Carlo",
        "Optimization", "Benchmark", "Export", "Assumptions", "Glossary",
    ])


    # ============================================================
    # Tab 1: Overview
    # ============================================================
    with tab_overview:
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
    # ============================================================
    with tab_returns:
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
    # ============================================================
    with tab_corr:
        st.subheader("Return correlation matrix")
        st.plotly_chart(plot_correlation_heatmap(corr), use_container_width=True)
        st.caption(
            "**+1.0** — assets move in perfect lockstep (no diversification). "
            "**0.0** — uncorrelated (good diversification). "
            "**−1.0** — assets move in opposite directions (maximum hedge)."
        )


    # ============================================================
    # Tab 4: Monte Carlo
    # ============================================================
    with tab_mc:
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
    # ============================================================
    with tab_opt:
        st.subheader("Markowitz Portfolio Optimization")
        st.markdown(
            '<p style="color:#64748b; font-size:14px; margin-bottom:20px;">'
            "Two classical optimal portfolios computed by minimizing variance under "
            "constraints (long-only, sum of weights = 1). The <b>Efficient Frontier</b> "
            "below shows the best achievable risk/return trade-offs."
            "</p>",
            unsafe_allow_html=True,
        )

        # Portfolio comparison cards
        o1, o2, o3 = st.columns(3)
        with o1:
            st.markdown(
                metric_card(
                    "Custom Portfolio",
                    f"{sharpe:.2f}",
                    f"Your weights. Return {port_metrics['return']*100:.2f}%, "
                    f"Vol {port_metrics['volatility']*100:.2f}%.",
                    f"Return {port_metrics['return']*100:.1f}% | Vol "
                    f"{port_metrics['volatility']*100:.1f}%",
                    "#fbbf24", "#94a3b8",
                ),
                unsafe_allow_html=True,
            )
        with o2:
            st.markdown(
                metric_card(
                    "Max Sharpe (Tangency)",
                    f"{max_sharpe_value:.2f}",
                    "Portfolio with the highest risk-adjusted return. This is the "
                    "tangency portfolio from the Capital Market Line.",
                    f"Return {max_sharpe_metrics['return']*100:.1f}% | Vol "
                    f"{max_sharpe_metrics['volatility']*100:.1f}%",
                    "#10b981", "#94a3b8",
                ),
                unsafe_allow_html=True,
            )
        with o3:
            st.markdown(
                metric_card(
                    "Min Variance",
                    f"{min_var_sharpe:.2f}",
                    "Portfolio with the lowest possible volatility regardless of "
                    "expected return. The safest reachable allocation.",
                    f"Return {min_var_metrics['return']*100:.1f}% | Vol "
                    f"{min_var_metrics['volatility']*100:.1f}%",
                    "#a855f7", "#94a3b8",
                ),
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

        # Optimal weights table
        st.subheader("Optimal weights")
        weights_table = pd.DataFrame(
            {
                "Custom": (weights.reindex(prices.columns).fillna(0.0) * 100).map(
                    lambda x: f"{x:.2f}%"
                ),
                "Max Sharpe": (max_sharpe_weights * 100).map(lambda x: f"{x:.2f}%"),
                "Min Variance": (min_var_weights * 100).map(lambda x: f"{x:.2f}%"),
            }
        )
        st.dataframe(weights_table, use_container_width=True)

        # Efficient Frontier plot
        st.subheader("Efficient Frontier")
        asset_points = {
            ticker: (
                float(asset_stats.loc[ticker, "annual_return"]),
                float(asset_stats.loc[ticker, "annual_vol"]),
            )
            for ticker in asset_stats.index
        }
        st.plotly_chart(
            plot_efficient_frontier(
                frontier_df,
                asset_points=asset_points,
                custom_point=port_metrics,
                max_sharpe_point=max_sharpe_metrics,
                min_var_point=min_var_metrics,
            ),
            use_container_width=True,
        )
        st.caption(
            "The **Efficient Frontier** (Markowitz, 1952) is the set of portfolios "
            "offering the highest expected return for a given level of risk. Any "
            "portfolio below the frontier is suboptimal — you could earn more for "
            "the same risk, or take less risk for the same return."
        )


    # ============================================================
    # Tab 6: Benchmark
    # ============================================================
    with tab_bench:
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

            st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)

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
    # ============================================================
    with tab_export:
        st.subheader("Download report & data")
        st.markdown(
            '<p style="color:#64748b; font-size:14px; margin-bottom:24px;">'
            "Export the full analysis as a PDF report or download raw data as CSV files."
            "</p>",
            unsafe_allow_html=True,
        )

        export_key = (
            tuple(prices.columns),
            str(start_date),
            str(end_date),
            round(float(initial_investment), 2),
            tuple(round(float(weights.get(t, 0.0)), 8) for t in prices.columns),
        )
        if st.session_state.get("fp_export_key") != export_key:
            for key in (
                "fp_pdf_bytes",
                "fp_pdf_error",
                "fp_excel_bytes",
                "fp_excel_error",
            ):
                st.session_state.pop(key, None)
            st.session_state["fp_export_key"] = export_key

        # ---- Formatted reports (PDF + Excel) --------------------------------
        st.markdown(
            export_section_header("📄", "Formatted reports"),
            unsafe_allow_html=True,
        )
        rep_a, rep_b = st.columns(2)
        with rep_a:
            st.markdown(
                export_item_label("PDF Report"),
                unsafe_allow_html=True,
            )
            st.caption("Full analysis with metrics, tables and Monte Carlo summary.")
            if st.button("Generate PDF", use_container_width=True, key="fp_generate_pdf"):
                try:
                    with st.spinner("Preparing PDF report..."):
                        st.session_state["fp_pdf_bytes"] = bytes(
                            build_pdf(
                                tickers=list(prices.columns),
                                weights=weights,
                                start_date=start_date,
                                end_date=end_date,
                                port_metrics=port_metrics,
                                sharpe=sharpe,
                                risk_free_rate=risk_free_rate,
                                initial_investment=initial_investment,
                                asset_stats=asset_stats,
                                port_value=port_value,
                                cagr_value=portfolio_cagr,
                                mc_p5=float(mc_p5),
                                mc_p50=float(mc_p50),
                                mc_p95=float(mc_p95),
                                mc_horizon_days=mc_horizon_days,
                                mc_method=mc_method_label,
                                max_dd=dd_info["max_drawdown"],
                                sortino=sortino,
                                beta=capm["beta"] if market_loaded else None,
                                alpha=capm["alpha"] if market_loaded else None,
                                r_squared=capm["r_squared"] if market_loaded else None,
                                max_sharpe_weights=max_sharpe_weights,
                                max_sharpe_metrics=max_sharpe_metrics,
                                min_var_weights=min_var_weights,
                                min_var_metrics=min_var_metrics,
                            )
                        )
                    st.session_state.pop("fp_pdf_error", None)
                except (ValueError, RuntimeError, OSError) as exc:
                    logger.exception("PDF export failed")
                    st.session_state["fp_pdf_error"] = str(exc)

            if st.session_state.get("fp_pdf_bytes"):
                st.download_button(
                    label="📥 Download PDF",
                    data=st.session_state["fp_pdf_bytes"],
                    file_name=f"finport_report_{date.today()}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            if st.session_state.get("fp_pdf_error"):
                st.error(f"PDF export failed: {st.session_state['fp_pdf_error']}")
        with rep_b:
            st.markdown(
                export_item_label("Excel Workbook"),
                unsafe_allow_html=True,
            )
            st.caption("One .xlsx with 5 sheets: Summary, Stats, Prices, Returns, Portfolio Value.")
            if st.button("Generate Excel", use_container_width=True, key="fp_generate_excel"):
                try:
                    with st.spinner("Preparing Excel workbook..."):
                        st.session_state["fp_excel_bytes"] = build_excel_workbook(
                            prices=prices,
                            returns=returns,
                            asset_stats=asset_stats,
                            weights=weights,
                            port_value=port_value,
                            port_metrics=port_metrics,
                            sharpe=sharpe,
                            cagr_value=portfolio_cagr,
                            sortino=sortino,
                            max_dd=dd_info["max_drawdown"],
                        )
                    st.session_state.pop("fp_excel_error", None)
                except (ValueError, RuntimeError, OSError) as exc:
                    logger.exception("Excel export failed")
                    st.session_state["fp_excel_error"] = str(exc)

            if st.session_state.get("fp_excel_bytes"):
                st.download_button(
                    label="📥 Download Excel",
                    data=st.session_state["fp_excel_bytes"],
                    file_name=f"finport_workbook_{date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            if st.session_state.get("fp_excel_error"):
                st.error(f"Excel export failed: {st.session_state['fp_excel_error']}")

        st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

        # ---- Raw data (CSV) -------------------------------------------------
        st.markdown(
            export_section_header("📊", "Raw data"),
            unsafe_allow_html=True,
        )
        col_b, col_c, col_d = st.columns(3)
        with col_b:
            st.markdown(
                export_item_label("Price History"),
                unsafe_allow_html=True,
            )
            st.caption("Adjusted closing prices.")
            st.download_button(
                label="📥 Download CSV",
                data=prices_to_csv(prices),
                file_name=f"finport_prices_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with col_c:
            st.markdown(
                export_item_label("Daily Returns"),
                unsafe_allow_html=True,
            )
            st.caption("Daily percentage returns per asset.")
            st.download_button(
                label="📥 Download CSV",
                data=returns_to_csv(returns),
                file_name=f"finport_returns_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with col_d:
            st.markdown(
                export_item_label("Asset Summary"),
                unsafe_allow_html=True,
            )
            st.caption("Annualized return, volatility, weights.")
            st.download_button(
                label="📥 Download CSV",
                data=summary_to_csv(asset_stats, weights),
                file_name=f"finport_summary_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        st.divider()
        st.caption(
            "**Disclaimer:** This report is generated for educational purposes only and does not "
            "constitute financial advice. Past performance is not indicative of future results."
        )


    # ============================================================
    # Tab 8: Assumptions
    # ============================================================
    with tab_assumptions:
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
            st.markdown(
                metric_card(
                    "Market Data",
                    "Yahoo Finance",
                    "Adjusted close prices are downloaded from Yahoo Finance via "
                    "yfinance. Missing, delisted or incorrect symbols are excluded.",
                    "External data source",
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
    # ============================================================
    with tab_glossary:
        st.subheader("Financial terms glossary")
        st.markdown(
            '<p style="color:#64748b; font-size:14px; margin-bottom:24px;">'
            "Reference for the concepts and metrics used throughout FinPort."
            "</p>",
            unsafe_allow_html=True,
        )

        # Render glossary with 2 columns of expanders
        g_col1, g_col2 = st.columns(2)
        for i, (term, definition) in enumerate(GLOSSARY_TERMS):
            target_col = g_col1 if i % 2 == 0 else g_col2
            with target_col:
                with st.expander(term):
                    st.markdown(definition)

        st.divider()
        st.caption(GLOSSARY_SOURCES)
