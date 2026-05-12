"""Export tab — PDF / Excel / CSV downloads."""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

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

_PDF_BYTES_KEY = "fp_pdf_bytes"
_PDF_ERROR_KEY = "fp_pdf_error"
_EXCEL_BYTES_KEY = "fp_excel_bytes"
_EXCEL_ERROR_KEY = "fp_excel_error"
_EXPORT_KEY = "fp_export_key"

_CACHE_KEYS = (_PDF_BYTES_KEY, _PDF_ERROR_KEY, _EXCEL_BYTES_KEY, _EXCEL_ERROR_KEY)


def render_export_tab(result: PortfolioAnalysisResult, context: ViewContext) -> None:
    """Render the export tab: PDF/Excel buttons and raw CSV download links."""
    st.subheader("Download report & data")
    st.markdown(
        muted_paragraph(
            "Export the full analysis as a PDF report or download raw data as CSV files."
        ),
        unsafe_allow_html=True,
    )

    _invalidate_caches_if_inputs_changed(result, context)

    st.markdown(export_section_header("📄", "Formatted reports"), unsafe_allow_html=True)
    rep_a, rep_b = st.columns(2)
    with rep_a:
        _render_pdf_section(result, context)
    with rep_b:
        _render_excel_section(result)

    st.markdown(vertical_spacer(24), unsafe_allow_html=True)
    st.markdown(export_section_header("📊", "Raw data"), unsafe_allow_html=True)
    _render_csv_section(result)

    st.divider()
    st.caption(
        "**Disclaimer:** This report is generated for educational purposes only "
        "and does not constitute financial advice. Past performance is not "
        "indicative of future results."
    )


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def _render_pdf_section(result: PortfolioAnalysisResult, context: ViewContext) -> None:
    st.markdown(export_item_label("PDF Report"), unsafe_allow_html=True)
    st.caption("Full analysis with metrics, tables and Monte Carlo summary.")

    if st.button("Generate PDF", use_container_width=True, key="fp_generate_pdf"):
        _generate_artifact(
            session_key=_PDF_BYTES_KEY,
            error_key=_PDF_ERROR_KEY,
            spinner_text="Preparing PDF report...",
            log_message="PDF export failed",
            build=lambda: bytes(_build_pdf_bytes(result, context)),
        )

    pdf_bytes = st.session_state.get(_PDF_BYTES_KEY)
    if pdf_bytes:
        st.download_button(
            label="📥 Download PDF",
            data=pdf_bytes,
            file_name=f"finport_report_{date.today()}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    if st.session_state.get(_PDF_ERROR_KEY):
        st.error(f"PDF export failed: {st.session_state[_PDF_ERROR_KEY]}")


def _render_excel_section(result: PortfolioAnalysisResult) -> None:
    st.markdown(export_item_label("Excel Workbook"), unsafe_allow_html=True)
    st.caption("One .xlsx with 5 sheets: Summary, Stats, Prices, Returns, Portfolio Value.")

    if st.button("Generate Excel", use_container_width=True, key="fp_generate_excel"):
        _generate_artifact(
            session_key=_EXCEL_BYTES_KEY,
            error_key=_EXCEL_ERROR_KEY,
            spinner_text="Preparing Excel workbook...",
            log_message="Excel export failed",
            build=lambda: _build_excel_bytes(result),
        )

    excel_bytes = st.session_state.get(_EXCEL_BYTES_KEY)
    if excel_bytes:
        st.download_button(
            label="📥 Download Excel",
            data=excel_bytes,
            file_name=f"finport_workbook_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    if st.session_state.get(_EXCEL_ERROR_KEY):
        st.error(f"Excel export failed: {st.session_state[_EXCEL_ERROR_KEY]}")


def _render_csv_section(result: PortfolioAnalysisResult) -> None:
    csv_items = [
        ("Price History", "Adjusted closing prices.",
         "finport_prices", lambda: prices_to_csv(result.prices)),
        ("Daily Returns", "Daily percentage returns per asset.",
         "finport_returns", lambda: returns_to_csv(result.returns)),
        ("Asset Summary", "Annualized return, volatility, weights.",
         "finport_summary",
         lambda: summary_to_csv(result.asset_stats, result.weights)),
    ]
    cols = st.columns(len(csv_items))
    for col, (label, caption, prefix, builder) in zip(cols, csv_items, strict=True):
        with col:
            st.markdown(export_item_label(label), unsafe_allow_html=True)
            st.caption(caption)
            st.download_button(
                label="📥 Download CSV",
                data=builder(),
                file_name=f"{prefix}_{date.today()}.csv",
                mime="text/csv",
                use_container_width=True,
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _invalidate_caches_if_inputs_changed(
    result: PortfolioAnalysisResult,
    context: ViewContext,
) -> None:
    export_key = (
        tuple(result.prices.columns),
        str(context.start_date),
        str(context.end_date),
        round(float(context.initial_investment), 2),
        tuple(
            round(float(result.weights.get(t, 0.0)), 8)
            for t in result.prices.columns
        ),
    )
    if st.session_state.get(_EXPORT_KEY) != export_key:
        for key in _CACHE_KEYS:
            st.session_state.pop(key, None)
        st.session_state[_EXPORT_KEY] = export_key


def _generate_artifact(
    *,
    session_key: str,
    error_key: str,
    spinner_text: str,
    log_message: str,
    build: Any,
) -> None:
    try:
        with st.spinner(spinner_text):
            st.session_state[session_key] = build()
        st.session_state.pop(error_key, None)
    except (ValueError, RuntimeError, OSError) as exc:
        logger.exception(log_message)
        st.session_state[error_key] = str(exc)


def _build_pdf_bytes(
    result: PortfolioAnalysisResult,
    context: ViewContext,
) -> bytes | bytearray:
    capm = result.capm
    return build_pdf(
        tickers=list(result.prices.columns),
        weights=result.weights,
        start_date=context.start_date,
        end_date=context.end_date,
        port_metrics=result.portfolio_metrics,
        sharpe=result.portfolio_sharpe,
        risk_free_rate=context.risk_free_rate,
        initial_investment=context.initial_investment,
        asset_stats=result.asset_stats,
        port_value=result.portfolio_value,
        cagr_value=result.portfolio_cagr,
        mc_p5=float(result.mc_p5),
        mc_p50=float(result.mc_p50),
        mc_p95=float(result.mc_p95),
        mc_horizon_days=context.mc_horizon_days,
        mc_method=context.mc_method_label,
        max_dd=result.drawdown_info["max_drawdown"],
        sortino=result.sortino,
        beta=capm["beta"] if result.market_loaded else None,
        alpha=capm["alpha"] if result.market_loaded else None,
        r_squared=capm["r_squared"] if result.market_loaded else None,
        max_sharpe_weights=result.max_sharpe_weights,
        max_sharpe_metrics=result.max_sharpe_metrics,
        min_var_weights=result.min_variance_weights,
        min_var_metrics=result.min_variance_metrics,
    )


def _build_excel_bytes(result: PortfolioAnalysisResult) -> bytes:
    return build_excel_workbook(
        prices=result.prices,
        returns=result.returns,
        asset_stats=result.asset_stats,
        weights=result.weights,
        port_value=result.portfolio_value,
        port_metrics=result.portfolio_metrics,
        sharpe=result.portfolio_sharpe,
        cagr_value=result.portfolio_cagr,
        sortino=result.sortino,
        max_dd=result.drawdown_info["max_drawdown"],
    )
