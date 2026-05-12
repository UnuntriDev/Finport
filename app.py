"""FinPort — Streamlit entry point.

Wires together user inputs (sidebar), data loading, analysis, and
visualization into a tabbed fintech-style dashboard.
"""
from __future__ import annotations

import logging
import time

import streamlit as st

from constants import LOADER_MIN_SECONDS, LOADER_PAINT_DELAY
from demo_data import (
    DEMO_END_DATE,
    DEMO_INITIAL_INVESTMENT,
    DEMO_START_DATE,
    DEMO_TICKERS,
    demo_weights_pct,
)
from models import PortfolioAnalysisRequest, ValidationError, validate_request
from services.portfolio_analysis import (
    PortfolioAnalysisError,
    run_portfolio_analysis,
)
from sidebar import SidebarState, render_sidebar
from ui.dialogs import show_failed_tickers_dialog
from ui.header import render_header
from ui.landing import render_landing_page
from ui.loader import MONEY_LOADER_HTML
from ui.styles import GLOBAL_CSS
from views.dashboard_tabs import render_dashboard_tabs

logging.basicConfig(level=logging.INFO)

_DIALOG_SUPPRESSED_KEY = "fp_dialog_suppressed"
_FAILED_DISMISSED_KEY = "fp_failed_dismissed_key"
_HAS_RUN_KEY = "fp_has_run"
_RESET_PREFIXES = ("fp_", "w_")


# ---------------------------------------------------------------------------
# Helpers (defined first because Streamlit reruns this script top-down)
# ---------------------------------------------------------------------------

def _build_analysis_request(state: SidebarState) -> PortfolioAnalysisRequest:
    """Resolve effective inputs (demo mode fills any empty fields)."""
    tickers = state.tickers
    weights_pct = state.weights_pct
    start_date = state.start_date
    end_date = state.end_date
    investment = state.initial_investment

    if state.demo_mode:
        tickers = tickers if len(tickers) >= 2 else DEMO_TICKERS
        weights_pct = (
            weights_pct
            if state.tickers and state.weights_valid
            else demo_weights_pct(tickers)
        )
        start_date = start_date or DEMO_START_DATE
        end_date = end_date or DEMO_END_DATE
        investment = investment if investment > 0 else DEMO_INITIAL_INVESTMENT

    return PortfolioAnalysisRequest(
        tickers=tickers,
        weights_pct=weights_pct,
        start_date=start_date,  # type: ignore[arg-type]
        end_date=end_date,      # type: ignore[arg-type]
        initial_investment=investment,
        risk_free_rate=state.risk_free_rate,
        mc_horizon_days=state.mc_horizon_days,
        mc_simulations=state.mc_simulations,
        mc_method_label=state.mc_method_label,
        use_demo_data=state.demo_mode,
    )


def _validate_analysis_inputs(request: PortfolioAnalysisRequest) -> None:
    """Defensive validation: sidebar disables Run but query params can bypass it."""
    try:
        validate_request(request)
    except ValidationError as exc:
        st.error(str(exc))
        st.stop()


def _maybe_show_failed_dialog(failed: dict[str, str]) -> None:
    """Show the failed-ticker modal unless it was already dismissed."""
    if not failed or st.session_state.get(_DIALOG_SUPPRESSED_KEY, False):
        return
    failed_key = "|".join(sorted(failed.keys()))
    if st.session_state.get(_FAILED_DISMISSED_KEY) != failed_key:
        show_failed_tickers_dialog(failed, failed_key)


def _render_reset_button() -> None:
    """Render the 'New analysis' button that wipes all FinPort session state."""
    _, right = st.columns([5, 1])
    with right:
        clicked = st.button(
            "🔄 New analysis",
            key="fp_reset_btn",
            help="Clear results and return to the configuration screen.",
            use_container_width=True,
        )
    if not clicked:
        return
    for key in list(st.session_state.keys()):
        if key.startswith(_RESET_PREFIXES):
            del st.session_state[key]
    st.session_state[_DIALOG_SUPPRESSED_KEY] = True
    st.rerun()


# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="FinPort — Portfolio Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar — user inputs
# ---------------------------------------------------------------------------
sidebar_state = render_sidebar(
    query_demo=st.query_params.get("demo") == "1",
    query_autorun=st.query_params.get("autorun") == "1",
)

if sidebar_state.run:
    st.session_state[_HAS_RUN_KEY] = True
    st.session_state[_DIALOG_SUPPRESSED_KEY] = False

if not (sidebar_state.run or st.session_state.get(_HAS_RUN_KEY, False)):
    render_header()
    render_landing_page()
    st.stop()


# ---------------------------------------------------------------------------
# Build the analysis request + validation
# ---------------------------------------------------------------------------
analysis_request = _build_analysis_request(sidebar_state)
_validate_analysis_inputs(analysis_request)


# ---------------------------------------------------------------------------
# Loading animation + analysis pipeline
# ---------------------------------------------------------------------------
loading_overlay = st.empty()
loader_start = time.time()
if sidebar_state.run:
    loading_overlay.markdown(MONEY_LOADER_HTML, unsafe_allow_html=True)
    time.sleep(LOADER_PAINT_DELAY)

try:
    with st.spinner(
        "Running portfolio analysis: market data, risk metrics, "
        "optimization and Monte Carlo..."
    ):
        result = run_portfolio_analysis(analysis_request)
except PortfolioAnalysisError as exc:
    loading_overlay.empty()
    _maybe_show_failed_dialog(exc.failed)
    st.error(str(exc))
    st.stop()

if sidebar_state.run:
    elapsed = time.time() - loader_start
    if elapsed < LOADER_MIN_SECONDS:
        time.sleep(LOADER_MIN_SECONDS - elapsed)
loading_overlay.empty()

_maybe_show_failed_dialog(result.failed)

period_str = (
    f"{analysis_request.start_date.strftime('%b %Y')} – "
    f"{analysis_request.end_date.strftime('%b %Y')}"
)
render_header(tickers=list(result.prices.columns), period=period_str)


# ---------------------------------------------------------------------------
# Reset button + dashboard tabs
# ---------------------------------------------------------------------------
_render_reset_button()
render_dashboard_tabs(
    result=result,
    start_date=analysis_request.start_date,
    end_date=analysis_request.end_date,
    initial_investment=analysis_request.initial_investment,
    risk_free_rate=analysis_request.risk_free_rate,
    mc_horizon_days=analysis_request.mc_horizon_days,
    mc_method_label=analysis_request.mc_method_label,
    demo_mode=analysis_request.use_demo_data,
)
