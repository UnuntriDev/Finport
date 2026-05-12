from __future__ import annotations

import logging
from datetime import date

import streamlit as st

from models import PortfolioAnalysisResult, ViewContext
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
    muted_paragraph,
    vertical_spacer,
)

logger = logging.getLogger(__name__)


def render_export_tab(result: PortfolioAnalysisResult, context: ViewContext) -> None:
    prices = result.prices
    weights = result.weights
    returns = result.returns
    asset_stats = result.asset_stats
    port_metrics = result.portfolio_metrics
    sharpe = result.portfolio_sharpe
    port_value = result.portfolio_value
    portfolio_cagr = result.portfolio_cagr
    dd_info = result.drawdown_info
    sortino = result.sortino
    max_sharpe_weights = result.max_sharpe_weights
    min_var_weights = result.min_variance_weights
    max_sharpe_metrics = result.max_sharpe_metrics
    min_var_metrics = result.min_variance_metrics
    capm = result.capm
    market_loaded = result.market_loaded
    mc_p5 = result.mc_p5
    mc_p50 = result.mc_p50
    mc_p95 = result.mc_p95
    start_date = context.start_date
    end_date = context.end_date
    initial_investment = context.initial_investment
    risk_free_rate = context.risk_free_rate
    mc_horizon_days = context.mc_horizon_days
    mc_method_label = context.mc_method_label
    st.subheader("Download report & data")
    st.markdown(
        muted_paragraph(
            "Export the full analysis as a PDF report or download raw data as CSV files."
        ),
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

    st.markdown(vertical_spacer(24), unsafe_allow_html=True)

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
