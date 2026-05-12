"""FinPort — Streamlit entry point.

Wires together user inputs (sidebar), data loading, analysis, and
visualization into a tabbed fintech-style dashboard.
"""
from __future__ import annotations

import logging
import time
from datetime import date
from html import escape

import streamlit as st

from constants import (
    LOADER_MIN_SECONDS,
    LOADER_PAINT_DELAY,
    MIN_PERIOD_DAYS,
)
from demo_data import (
    DEMO_END_DATE,
    DEMO_INITIAL_INVESTMENT,
    DEMO_START_DATE,
    DEMO_TICKERS,
    demo_weights_pct,
)
from models import PortfolioAnalysisRequest
from services.portfolio_analysis import (
    PortfolioAnalysisError,
    run_portfolio_analysis,
)
from sidebar import render_sidebar
from ui.dialogs import show_failed_tickers_dialog
from ui.loader import MONEY_LOADER_HTML
from ui.logo import logo_img
from ui.styles import GLOBAL_CSS
from views.dashboard_tabs import render_dashboard_tabs

logging.basicConfig(level=logging.INFO)

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
# Header banner
# ---------------------------------------------------------------------------
def render_header(tickers: list[str] | None = None, period: str = "") -> None:
    col_logo, col_meta = st.columns([3, 1])

    logo_html = (
        '<div style="padding:8px 0 6px 0;">'
        + logo_img(height=48)
        + '<div style="color:#64748b; font-size:12px; font-weight:500; '
        'margin:10px 0 0 60px; letter-spacing:0.01em;">'
        'Portfolio Analysis &amp; Risk Assessment Platform'
        '</div>'
        '</div>'
    )

    with col_logo:
        st.markdown(logo_html, unsafe_allow_html=True)

    badges_html = ""
    if tickers:
        badges = "".join(
            '<span style="background:#1e3a5f; color:#93c5fd; font-size:10px; '
            'font-weight:600; padding:2px 8px; border-radius:10px; '
            'border:1px solid #1d4ed8; margin:2px 2px 0 0; '
            f'display:inline-block;">{escape(str(t))}</span>'
            for t in tickers
        )
        badges_html = f'<div style="margin-bottom:6px; line-height:2;">{badges}</div>'

    period_html = (
        f'<div style="color:#64748b; font-size:11px; margin-bottom:2px;">'
        f'{escape(period)}</div>'
        if period else ""
    )
    date_str = date.today().strftime("%b %d, %Y")

    meta_html = (
        '<div style="padding:18px 0 6px 0; text-align:right;">'
        + badges_html
        + period_html
        + f'<div style="color:#334155; font-size:11px;">{date_str}</div>'
        + '</div>'
    )

    with col_meta:
        st.markdown(meta_html, unsafe_allow_html=True)

    st.markdown(
        '<div style="border-top:1px solid #1e3a5f; margin:4px 0 20px 0;"></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Sidebar — user inputs
# ---------------------------------------------------------------------------
sidebar_state = render_sidebar(
    query_demo=st.query_params.get("demo") == "1",
    query_autorun=st.query_params.get("autorun") == "1",
)
tickers = sidebar_state.tickers
weights_pct = sidebar_state.weights_pct
weights_valid = sidebar_state.weights_valid
start_date = sidebar_state.start_date
end_date = sidebar_state.end_date
risk_free_rate = sidebar_state.risk_free_rate
initial_investment = sidebar_state.initial_investment
mc_horizon_days = sidebar_state.mc_horizon_days
mc_simulations = sidebar_state.mc_simulations
mc_method_label = sidebar_state.mc_method_label
demo_mode = sidebar_state.demo_mode
run = sidebar_state.run


# ---------------------------------------------------------------------------
# Landing page (before first run)
# ---------------------------------------------------------------------------
# Persist "analysis was run" across reruns caused by download buttons etc.
if run:
    st.session_state["fp_has_run"] = True
    # Re-enable popups for the new run (in case they were suppressed by reset)
    st.session_state["fp_dialog_suppressed"] = False

if not (run or st.session_state.get("fp_has_run", False)):
    render_header()

    feature_card = (
        'background:#0a1628; border:1px solid #1e3a5f; border-radius:8px; '
        'padding:12px 20px; color:#60a5fa; font-size:12px; font-weight:600;'
    )
    big_logo = logo_img(height=72, with_text=False)
    landing_html = (
        '<div style="background:linear-gradient(145deg,#0f172a,#1e293b); '
        'border:1px solid #1e3a5f; border-radius:12px; padding:48px; '
        'text-align:center; margin-top:20px;">'
        '<div style="display:flex; justify-content:center; margin-bottom:20px;">'
        + big_logo + '</div>'
        '<h2 style="color:#e2e8f0; font-size:22px; font-weight:700; '
        'margin:0 0 8px 0;">Configure your portfolio</h2>'
        '<p style="color:#64748b; font-size:14px; max-width:440px; '
        'margin:0 auto 24px;">Enter tickers, set a date range and assign '
        'weights in the sidebar, then click '
        '<strong style="color:#60a5fa;">Run analysis</strong>.</p>'
        '<div style="display:flex; justify-content:center; gap:14px; '
        'flex-wrap:wrap;">'
        f'<div style="{feature_card}">📈 Price History</div>'
        f'<div style="{feature_card}">⚡ Risk &amp; Return</div>'
        f'<div style="{feature_card}">🎲 Monte Carlo</div>'
        f'<div style="{feature_card}">📄 PDF Export</div>'
        '</div>'
        '</div>'
    )
    st.markdown(landing_html, unsafe_allow_html=True)
    st.stop()


# ---------------------------------------------------------------------------
# Effective inputs (demo mode can fill empty configuration fields)
# ---------------------------------------------------------------------------
analysis_tickers = tickers
analysis_weights_pct = weights_pct
analysis_start_date = start_date
analysis_end_date = end_date
analysis_initial_investment = initial_investment

if demo_mode:
    analysis_tickers = tickers if len(tickers) >= 2 else DEMO_TICKERS
    analysis_weights_pct = (
        weights_pct
        if tickers and weights_valid
        else demo_weights_pct(analysis_tickers)
    )
    analysis_start_date = start_date or DEMO_START_DATE
    analysis_end_date = end_date or DEMO_END_DATE
    analysis_initial_investment = (
        initial_investment
        if initial_investment > 0
        else DEMO_INITIAL_INVESTMENT
    )


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
if analysis_start_date is None or analysis_end_date is None:
    st.error("Select a start and end date in the sidebar.")
    st.stop()

if analysis_initial_investment <= 0:
    st.error("Enter an initial investment amount greater than $0.")
    st.stop()

if analysis_start_date >= analysis_end_date:
    st.error("Start date must be earlier than end date.")
    st.stop()

period_days = (analysis_end_date - analysis_start_date).days
if period_days < MIN_PERIOD_DAYS:
    st.error(
        f"Analysis period is only **{period_days} days**. "
        f"Choose at least **{MIN_PERIOD_DAYS} days** so that the covariance "
        "matrix, Markowitz optimization and Monte Carlo simulation have "
        "enough data to produce meaningful results."
    )
    st.stop()

if len(analysis_tickers) < 2:
    st.error("Select at least two tickers for a meaningful portfolio analysis.")
    st.stop()

if not weights_valid and not demo_mode:
    st.error("Weights do not sum to 100%. Adjust them in the sidebar.")
    st.stop()


# ---------------------------------------------------------------------------
# Money-themed fullscreen loading animation (overlay, cleared when done)
# ---------------------------------------------------------------------------
# Only show the loader on the *fresh* Run click — on subsequent reruns
# (downloads, dialog dismissals, sidebar widget changes) data is already
# cached and the loader would just slow the UX down (and could remain
# visible when returning to the landing page).
loading_overlay = st.empty()
_loader_start = time.time()
if run:
    loading_overlay.markdown(MONEY_LOADER_HTML, unsafe_allow_html=True)
    # Give the browser a moment to actually render the overlay before Python
    # starts the heavy work.
    time.sleep(LOADER_PAINT_DELAY)


# ---------------------------------------------------------------------------
# Portfolio analysis pipeline
# ---------------------------------------------------------------------------
analysis_request = PortfolioAnalysisRequest(
    tickers=analysis_tickers,
    weights_pct=analysis_weights_pct,
    start_date=analysis_start_date,
    end_date=analysis_end_date,
    initial_investment=analysis_initial_investment,
    risk_free_rate=risk_free_rate,
    mc_horizon_days=mc_horizon_days,
    mc_simulations=mc_simulations,
    mc_method_label=mc_method_label,
    use_demo_data=demo_mode,
)

try:
    with st.spinner(
        "Running portfolio analysis: market data, risk metrics, "
        "optimization and Monte Carlo..."
    ):
        analysis_result = run_portfolio_analysis(analysis_request)
except PortfolioAnalysisError as exc:
    loading_overlay.empty()
    if exc.failed and not st.session_state.get("fp_dialog_suppressed", False):
        _failed_key = "|".join(sorted(exc.failed.keys()))
        if st.session_state.get("fp_failed_dismissed_key") != _failed_key:
            show_failed_tickers_dialog(exc.failed, _failed_key)
    st.error(str(exc))
    st.stop()

prices = analysis_result.prices
failed = analysis_result.failed
weights = analysis_result.weights
returns = analysis_result.returns
norm = analysis_result.normalized_prices
asset_stats = analysis_result.asset_stats
port_metrics = analysis_result.portfolio_metrics
sharpe = analysis_result.portfolio_sharpe
corr = analysis_result.correlation
port_value = analysis_result.portfolio_value
portfolio_cagr = analysis_result.portfolio_cagr
equal_weights = analysis_result.equal_weights
eq_metrics = analysis_result.equal_weight_metrics
eq_sharpe = analysis_result.equal_weight_sharpe
eq_value = analysis_result.equal_weight_value
port_daily_ret = analysis_result.portfolio_daily_returns
dd_info = analysis_result.drawdown_info
sortino = analysis_result.sortino
max_sharpe_weights = analysis_result.max_sharpe_weights
min_var_weights = analysis_result.min_variance_weights
max_sharpe_metrics = analysis_result.max_sharpe_metrics
min_var_metrics = analysis_result.min_variance_metrics
max_sharpe_value = analysis_result.max_sharpe_ratio
min_var_sharpe = analysis_result.min_variance_sharpe
frontier_df = analysis_result.efficient_frontier
market_returns = analysis_result.market_returns
market_value = analysis_result.market_value
capm = analysis_result.capm
market_loaded = analysis_result.market_loaded
sims = analysis_result.simulations
mc_p5 = analysis_result.mc_p5
mc_p50 = analysis_result.mc_p50
mc_p95 = analysis_result.mc_p95
var_95 = analysis_result.var_95
mc_method = (
    "bootstrap"
    if mc_method_label == "Historical bootstrap"
    else "parametric"
)

# ---------------------------------------------------------------------------
# Header (with context)
# ---------------------------------------------------------------------------
# Ensure the money animation respects LOADER_MIN_SECONDS only on a
# fresh Run click. Subsequent reruns (downloads, dialog clicks) don't need it.
if run:
    _min_loader_seconds = LOADER_MIN_SECONDS
    _elapsed = time.time() - _loader_start
    if _elapsed < _min_loader_seconds:
        time.sleep(_min_loader_seconds - _elapsed)
loading_overlay.empty()

# ---- Failed tickers dialog (non-fatal: ≥2 valid tickers survived) ---------
# Shown AFTER the loader is cleared, otherwise the modal hides behind it.
if failed and not st.session_state.get("fp_dialog_suppressed", False):
    _failed_key = "|".join(sorted(failed.keys()))
    if st.session_state.get("fp_failed_dismissed_key") != _failed_key:
        show_failed_tickers_dialog(failed, _failed_key)

period_str = (
    f"{analysis_start_date.strftime('%b %Y')} – "
    f"{analysis_end_date.strftime('%b %Y')}"
)
render_header(tickers=list(prices.columns), period=period_str)

# ---- New analysis / reset button (clears dashboard, returns to landing) ----
_reset_col_l, _reset_col_r = st.columns([5, 1])
with _reset_col_r:
    if st.button(
        "🔄 New analysis",
        key="fp_reset_btn",
        help="Clear results and return to the configuration screen.",
        use_container_width=True,
    ):
        # Full reset — wipe every piece of portfolio configuration so the
        # landing page comes back exactly as on a fresh launch.
        for _k in list(st.session_state.keys()):
            if _k.startswith("fp_") or _k.startswith("w_"):
                del st.session_state[_k]
        # Suppress any leftover modal dialog (st.dialog persists across reruns
        # via Streamlit-internal state; an explicit suppress flag prevents it
        # from rendering on the landing page after reset).
        st.session_state["fp_dialog_suppressed"] = True
        st.rerun()


# ---------------------------------------------------------------------------
# Dashboard tabs
# ---------------------------------------------------------------------------
render_dashboard_tabs(
    result=analysis_result,
    start_date=analysis_start_date,
    end_date=analysis_end_date,
    initial_investment=analysis_initial_investment,
    risk_free_rate=risk_free_rate,
    mc_horizon_days=mc_horizon_days,
    mc_method_label=mc_method_label,
    demo_mode=demo_mode,
)
