"""FinPort — Streamlit entry point.

Wires together user inputs (sidebar), data loading, analysis, and
visualization into a tabbed fintech-style dashboard.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date, timedelta
from html import escape

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analysis import (
    annualized_portfolio_metrics,
    compute_beta_alpha,
    correlation_matrix,
    daily_returns,
    efficient_frontier,
    max_drawdown,
    monte_carlo_simulation,
    normalize_prices,
    optimize_max_sharpe,
    optimize_min_variance,
    portfolio_daily_returns,
    portfolio_value_series,
    sharpe_ratio,
    sortino_ratio,
    summary_per_asset,
)
from constants import (
    LOADER_MIN_SECONDS,
    LOADER_PAINT_DELAY,
    MAX_TICKERS,
    MIN_PERIOD_DAYS,
    MIN_TRADING_ROWS,
    WEIGHT_TOLERANCE_PCT,
)
from data_loader import load_price_data, load_sector_info
from portfolio_config import normalize_weights_to_100, parse_portfolio_config
from report_exporter import (
    build_excel_workbook,
    build_pdf,
    prices_to_csv,
    returns_to_csv,
    summary_to_csv,
)
from theme import CHART_PALETTE
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
from ticker_utils import normalize_ticker
from ui_components import (
    export_item_label,
    export_section_header,
    metric_card,
    sidebar_section_header,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="FinPort — Portfolio Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        /* Global dark base */
        .stApp { background-color: #020617; }
        .main > div { padding-top: 0.5rem; }

        /* Remove default Streamlit padding on metric */
        div[data-testid="metric-container"] { display: none; }

        /* Tabs — pill-style buttons with gradient active state */
        [data-baseweb="tab-list"] {
            background: transparent !important;
            gap: 8px !important;
            border-bottom: none !important;
            padding: 4px 0 12px 0 !important;
            margin-bottom: 18px !important;
            flex-wrap: wrap !important;
        }
        [data-baseweb="tab-list"] button[data-baseweb="tab"],
        [data-baseweb="tab-list"] [role="tab"] {
            background: #0f172a !important;
            border: 1px solid #1e293b !important;
            border-radius: 10px !important;
            color: #94a3b8 !important;
            font-weight: 600 !important;
            font-size: 13px !important;
            padding: 8px 18px !important;
            min-height: 38px !important;
            height: auto !important;
            transition: all 0.18s ease !important;
            white-space: nowrap !important;
        }
        [data-baseweb="tab-list"] button[data-baseweb="tab"]:hover,
        [data-baseweb="tab-list"] [role="tab"]:hover {
            background: #1e293b !important;
            color: #93c5fd !important;
            border-color: #334155 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
        }
        [data-baseweb="tab-list"] button[data-baseweb="tab"][aria-selected="true"],
        [data-baseweb="tab-list"] [role="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%) !important;
            color: #ffffff !important;
            border-color: #3b82f6 !important;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
            transform: translateY(-1px) !important;
        }
        /* Hide Streamlit's default underline highlight and divider */
        [data-baseweb="tab-highlight"],
        [data-baseweb="tab-border"] {
            display: none !important;
            background: transparent !important;
        }
        /* Tab panel padding */
        [data-baseweb="tab-panel"] {
            padding-top: 8px !important;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: #0a0f1e;
            border-right: 1px solid #1e293b;
        }

        /* Buttons */
        div[data-testid="stButton"] > button[kind="primary"] {
            background: linear-gradient(135deg, #1d4ed8, #2563eb);
            border: none;
            font-weight: 600;
            letter-spacing: 0.02em;
        }

        /* Download buttons */
        div[data-testid="stDownloadButton"] > button {
            background: #0f172a;
            border: 1px solid #1e3a5f;
            color: #60a5fa;
            font-weight: 600;
        }
        div[data-testid="stDownloadButton"] > button:hover {
            background: #1e3a5f;
            border-color: #3b82f6;
        }

        /* Dataframes */
        div[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }

        /* Dividers */
        hr { border-color: #1e293b; }

        h2, h3 { color: #e2e8f0 !important; letter-spacing: -0.02em; }

        /* Sidebar: compact small buttons for chips & date presets */
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
            padding: 4px 10px !important;
            font-size: 11px !important;
            font-weight: 600 !important;
            min-height: 28px !important;
            line-height: 1.2 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="secondary"] {
            background: #0f172a !important;
            border: 1px solid #1e3a5f !important;
            color: #93c5fd !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="secondary"]:hover {
            background: #1e3a5f !important;
            border-color: #3b82f6 !important;
            color: #ffffff !important;
        }
        /* Compact number inputs in sidebar */
        section[data-testid="stSidebar"] div[data-testid="stNumberInput"] input {
            padding: 4px 8px !important;
            font-size: 13px !important;
        }
        /* Run analysis button — prominent glow */
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] {
            background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
            border: none !important;
            font-size: 14px !important;
            font-weight: 800 !important;
            letter-spacing: 0.04em !important;
            min-height: 46px !important;
            border-radius: 10px !important;
            box-shadow: 0 0 18px rgba(37,99,235,0.55), 0 4px 16px rgba(0,0,0,0.4) !important;
            transition: all 0.18s ease !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"]:hover {
            box-shadow: 0 0 30px rgba(59,130,246,0.75), 0 6px 20px rgba(0,0,0,0.5) !important;
            transform: translateY(-1px) !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Logo (inline SVG — transparent background, no external file needed)
# ---------------------------------------------------------------------------
# IMPORTANT: every HTML string passed to st.markdown must have NO leading
# whitespace on any line, otherwise Streamlit's markdown parser treats lines
# indented by 4+ spaces as code blocks and shows them as text.

def _logo_icon_svg(size: int) -> str:
    """Square icon: blue gradient tile with white rising chart and gold accent."""
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" '
        'xmlns="http://www.w3.org/2000/svg" style="flex-shrink:0; display:block;">'
        '<defs>'
        '<linearGradient id="fpBg" x1="0" y1="0" x2="48" y2="48" '
        'gradientUnits="userSpaceOnUse">'
        '<stop offset="0%" stop-color="#60a5fa"/>'
        '<stop offset="55%" stop-color="#2563eb"/>'
        '<stop offset="100%" stop-color="#1e3a8a"/>'
        '</linearGradient>'
        '<linearGradient id="fpGloss" x1="0" y1="0" x2="0" y2="48" '
        'gradientUnits="userSpaceOnUse">'
        '<stop offset="0%" stop-color="#ffffff" stop-opacity="0.18"/>'
        '<stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>'
        '</linearGradient>'
        '</defs>'
        # background tile
        '<rect width="48" height="48" rx="12" fill="url(#fpBg)"/>'
        '<rect width="48" height="48" rx="12" fill="url(#fpGloss)"/>'
        # subtle bar chart in the background
        '<rect x="10" y="30" width="3.5" height="8" rx="1" '
        'fill="#ffffff" opacity="0.22"/>'
        '<rect x="16.5" y="25" width="3.5" height="13" rx="1" '
        'fill="#ffffff" opacity="0.22"/>'
        '<rect x="23" y="20" width="3.5" height="18" rx="1" '
        'fill="#ffffff" opacity="0.22"/>'
        # rising chart line
        '<polyline points="9,34 17,26 24,29 36,14" stroke="#ffffff" '
        'stroke-width="2.8" fill="none" stroke-linecap="round" '
        'stroke-linejoin="round"/>'
        # arrow head at the end
        '<polyline points="30,14 36,14 36,20" stroke="#ffffff" '
        'stroke-width="2.8" fill="none" stroke-linecap="round" '
        'stroke-linejoin="round"/>'
        # gold accent dot (financial highlight)
        '<circle cx="36" cy="14" r="3.2" fill="#fbbf24" '
        'stroke="#ffffff" stroke-width="1.2"/>'
        '</svg>'
    )


def logo_img(height: int = 44, with_text: bool = True) -> str:
    """Return HTML for the FinPort logo (icon + wordmark)."""
    icon = _logo_icon_svg(height)
    if not with_text:
        return icon
    text_size = max(int(height * 0.72), 16)
    return (
        '<div style="display:flex; align-items:center; gap:12px;">'
        + icon
        + f'<div style="font-size:{text_size}px; font-weight:900; '
        'color:#f8fafc; letter-spacing:-1.5px; line-height:1; '
        'font-family:-apple-system,Segoe UI,sans-serif;">'
        'Fin<span style="color:#3b82f6;">Port</span>'
        '</div>'
        '</div>'
    )


# ---------------------------------------------------------------------------
# Money-themed loading overlay (shown during analysis)
# ---------------------------------------------------------------------------
MONEY_LOADER_HTML = (
    '<style>'
    '@keyframes fp-bounce{'
    '0%,100%{transform:translateY(0) rotate(-6deg) scale(1);}'
    '50%{transform:translateY(-30px) rotate(8deg) scale(1.08);}'
    '}'
    '@keyframes fp-fall{'
    '0%{transform:translateY(-15vh) rotate(0deg);opacity:0;}'
    '8%{opacity:0.55;}'
    '92%{opacity:0.55;}'
    '100%{transform:translateY(115vh) rotate(720deg);opacity:0;}'
    '}'
    '@keyframes fp-pulse-dot{'
    '0%,100%{opacity:0.35;transform:scale(0.7);}'
    '50%{opacity:1;transform:scale(1.3);}'
    '}'
    '@keyframes fp-glow{'
    '0%,100%{filter:drop-shadow(0 0 24px rgba(59,130,246,0.6));}'
    '50%{filter:drop-shadow(0 0 50px rgba(251,191,36,0.85));}'
    '}'
    '@keyframes fp-ring-spin{'
    'from{transform:rotate(0deg);}'
    'to{transform:rotate(360deg);}'
    '}'
    '.fp-overlay{'
    'position:fixed;top:0;left:0;width:100vw;height:100vh;'
    'background:radial-gradient(circle at center,rgba(15,23,42,0.94) 0%,'
    'rgba(2,6,23,0.99) 80%);'
    '-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);'
    'z-index:99999;display:flex;flex-direction:column;'
    'align-items:center;justify-content:center;'
    'overflow:hidden;pointer-events:none;'
    '}'
    '.fp-drop{position:absolute;top:0;font-size:30px;'
    'animation:fp-fall 5s linear infinite;will-change:transform;}'
    '.fp-ring{'
    'position:absolute;width:220px;height:220px;border-radius:50%;'
    'border:2px dashed rgba(59,130,246,0.35);'
    'animation:fp-ring-spin 18s linear infinite;'
    '}'
    '.fp-ring-2{width:300px;height:300px;'
    'border:1px dashed rgba(251,191,36,0.25);'
    'animation:fp-ring-spin 26s linear infinite reverse;}'
    '.fp-center{font-size:96px;'
    'animation:fp-bounce 1.6s ease-in-out infinite,'
    'fp-glow 2.6s ease-in-out infinite;'
    'z-index:2;line-height:1;}'
    '.fp-brand{font-size:34px;font-weight:900;color:#f8fafc;'
    'letter-spacing:-1.5px;margin-top:22px;z-index:2;}'
    '.fp-brand span{color:#3b82f6;}'
    '.fp-text{color:#94a3b8;font-size:14px;font-weight:500;'
    'margin-top:10px;z-index:2;letter-spacing:0.02em;}'
    '.fp-dots{display:flex;gap:8px;margin-top:18px;z-index:2;}'
    '.fp-dots span{width:9px;height:9px;border-radius:50%;'
    'background:#3b82f6;animation:fp-pulse-dot 1.4s ease-in-out infinite;}'
    '.fp-dots span:nth-child(2){animation-delay:0.2s;background:#fbbf24;}'
    '.fp-dots span:nth-child(3){animation-delay:0.4s;background:#10b981;}'
    '</style>'
    '<div class="fp-overlay">'
    # Falling money rain (varied positions, delays, emoji types)
    '<span class="fp-drop" style="left:3%;animation-delay:0s;">💵</span>'
    '<span class="fp-drop" style="left:10%;animation-delay:1.3s;font-size:24px;">💰</span>'
    '<span class="fp-drop" style="left:17%;animation-delay:2.6s;">💸</span>'
    '<span class="fp-drop" style="left:24%;animation-delay:0.7s;font-size:36px;">💴</span>'
    '<span class="fp-drop" style="left:31%;animation-delay:3.1s;">💵</span>'
    '<span class="fp-drop" style="left:38%;animation-delay:1.9s;font-size:28px;">💶</span>'
    '<span class="fp-drop" style="left:62%;animation-delay:0.4s;">💷</span>'
    '<span class="fp-drop" style="left:69%;animation-delay:2.2s;font-size:34px;">💰</span>'
    '<span class="fp-drop" style="left:76%;animation-delay:3.7s;">💵</span>'
    '<span class="fp-drop" style="left:83%;animation-delay:0.95s;font-size:26px;">💸</span>'
    '<span class="fp-drop" style="left:90%;animation-delay:2.8s;">💴</span>'
    '<span class="fp-drop" style="left:97%;animation-delay:1.5s;font-size:30px;">💵</span>'
    # Decorative rotating rings
    '<div class="fp-ring"></div>'
    '<div class="fp-ring fp-ring-2"></div>'
    # Center animated icon
    '<div class="fp-center">💰</div>'
    '<div class="fp-brand">Fin<span>Port</span></div>'
    '<div class="fp-text">Analyzing your portfolio...</div>'
    '<div class="fp-dots"><span></span><span></span><span></span></div>'
    '</div>'
)


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
# Configuration constants (single source of truth)
# ---------------------------------------------------------------------------

@st.dialog("⚠️ Some tickers could not be loaded")
def _show_failed_tickers_dialog(failed: dict[str, str], failed_key: str) -> None:
    """Render a dismissible dialog for non-loadable tickers."""
    st.markdown("The following tickers were **excluded from the analysis**:")
    for ticker, reason in failed.items():
        safe_ticker = escape(str(ticker))
        safe_reason = escape(str(reason))
        st.markdown(
            f'<div style="background:#1a1a2e; border-left:3px solid '
            f'#f59e0b; border-radius:0 6px 6px 0; padding:10px 14px; '
            f'margin:8px 0;">'
            f'<div style="color:#fbbf24; font-weight:800; '
            f'font-size:14px; margin-bottom:4px;">{safe_ticker}</div>'
            f'<div style="color:#cbd5e1; font-size:12px;">{safe_reason}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
    st.caption(
        "Tip: verify the symbol on Yahoo Finance, or widen the date range "
        "if the asset is recent."
    )
    if st.button("Got it", type="primary", use_container_width=True):
        st.session_state["fp_failed_dismissed_key"] = failed_key
        st.rerun()


def _init_portfolio_state() -> None:
    """Initialise session state for the portfolio configuration widgets.

    All widget-keyed values (date inputs, weight number_inputs) are written
    here so subsequent reads/writes go through callbacks rather than mutating
    widget state after instantiation (which Streamlit forbids).
    """
    ss = st.session_state
    if "fp_tickers" not in ss:
        ss.fp_tickers = []
    if "fp_locks" not in ss:
        ss.fp_locks = {t: False for t in ss.fp_tickers}
    # Date widget keys are the source of truth
    if "fp_start_input" not in ss:
        ss.fp_start_input = None
    if "fp_end_input" not in ss:
        ss.fp_end_input = None
    # Weight widget keys (w_{ticker}) are the source of truth for each weight
    n = len(ss.fp_tickers)
    if n > 0:
        share = round(100.0 / n, 2)
        diff = round(100.0 - share * n, 2)
        for i, t in enumerate(ss.fp_tickers):
            wkey = f"w_{t}"
            if wkey not in ss:
                ss[wkey] = round(share + (diff if i == n - 1 else 0), 2)


def _redistribute_equal_locked() -> None:
    """Split 100% over unlocked tickers, keeping locked weights fixed.

    Writes to widget-state keys (w_{ticker}); must run in a callback context.
    """
    ss = st.session_state
    tickers = ss.fp_tickers
    if not tickers:
        return
    locked = [t for t in tickers if ss.fp_locks.get(t, False)]
    unlocked = [t for t in tickers if not ss.fp_locks.get(t, False)]
    locked_sum = sum(float(ss.get(f"w_{t}", 0.0)) for t in locked)
    remaining = max(0.0, 100.0 - locked_sum)
    if not unlocked:
        return
    share = round(remaining / len(unlocked), 2)
    for t in unlocked:
        ss[f"w_{t}"] = share
    # Compensate rounding on the last unlocked ticker so total = 100
    total = locked_sum + share * len(unlocked)
    diff = round(100.0 - total, 2)
    if abs(diff) > 0.001:
        ss[f"w_{unlocked[-1]}"] = round(share + diff, 2)


def _add_ticker_to_state(ticker: str, open_key: str | None = None) -> bool:
    """Add one ticker to session state with shared validation and rebalancing."""
    ss = st.session_state
    if open_key:
        ss[open_key] = True

    ticker = normalize_ticker(ticker)
    if not ticker:
        ss["fp_ticker_error"] = (
            "Invalid ticker. Use letters, digits, '.', '-', '^', '='."
        )
        return False
    if ticker in ss.fp_tickers:
        ss["fp_ticker_error"] = f"'{ticker}' is already in the portfolio."
        return False
    if len(ss.fp_tickers) >= MAX_TICKERS:
        ss["fp_ticker_error"] = f"Maximum {MAX_TICKERS} tickers allowed."
        return False

    ss.fp_tickers.append(ticker)
    ss.fp_locks[ticker] = False
    ss[f"w_{ticker}"] = 0.0
    _redistribute_equal_locked()
    ss["fp_ticker_error"] = ""
    return True


# ---------- Streamlit widget callbacks (run BEFORE next render) -------------

def _cb_add_ticker() -> None:
    ss = st.session_state
    raw = ss.get("fp_new_ticker_input", "")
    t = normalize_ticker(raw)
    if not t:
        ss["fp_ticker_error"] = (
            "Enter a ticker symbol."
            if not str(raw).strip()
            else f"Invalid ticker '{str(raw).strip().upper()}'."
        )
        return
    if _add_ticker_to_state(t):
        ss["fp_new_ticker_input"] = ""


def _cb_remove_ticker(ticker: str) -> None:
    ss = st.session_state
    if ticker not in ss.fp_tickers:
        return
    ss.fp_tickers.remove(ticker)
    ss.fp_locks.pop(ticker, None)
    ss.pop(f"w_{ticker}", None)
    _redistribute_equal_locked()


def _cb_toggle_lock(ticker: str) -> None:
    ss = st.session_state
    ss.fp_locks[ticker] = not ss.fp_locks.get(ticker, False)


def _cb_equal_weight() -> None:
    _redistribute_equal_locked()


def _cb_quick_add(ticker: str, open_key: str | None = None) -> None:
    """Add a popular ticker (e.g. crypto) without typing.

    ``open_key`` (optional) is a session-state flag set to True so that the
    triggering expander stays open across the Streamlit rerun.
    """
    _add_ticker_to_state(ticker, open_key=open_key)


def _cb_load_config() -> None:
    """Apply a previously-saved portfolio configuration from an uploaded JSON."""
    ss = st.session_state
    file = ss.get("fp_config_uploader")
    if file is None:
        return
    try:
        config = parse_portfolio_config(file.read())
    except ValueError as exc:
        ss["fp_config_error"] = str(exc)
        return

    # Clear any previous per-ticker weight keys
    for old_t in list(ss.fp_tickers):
        ss.pop(f"w_{old_t}", None)

    ss.fp_tickers = config.tickers
    ss.fp_locks = dict(config.locks)

    normalized_weights = normalize_weights_to_100(config.weights)
    for t in ss.fp_tickers:
        ss[f"w_{t}"] = normalized_weights.get(t, 0.0)

    if config.start is not None:
        ss.fp_start_input = config.start
    if config.end is not None:
        ss.fp_end_input = config.end

    ss["fp_config_loaded_msg"] = (
        f"Loaded {len(ss.fp_tickers)} tickers from config."
    )
    ss["fp_config_error"] = ""


def _build_config_json() -> str:
    """Serialize the current portfolio configuration as JSON."""
    ss = st.session_state
    config = {
        "version": 1,
        "saved_at": date.today().isoformat(),
        "tickers": list(ss.fp_tickers),
        "weights": {
            t: round(float(ss.get(f"w_{t}", 0.0)), 4) for t in ss.fp_tickers
        },
        "locks": {t: bool(ss.fp_locks.get(t, False)) for t in ss.fp_tickers},
        "start": str(ss.get("fp_start_input", "")),
        "end": str(ss.get("fp_end_input", "")),
    }
    return json.dumps(config, indent=2)


def _cb_weight_changed(ticker: str) -> None:
    """Auto-rebalance the other unlocked weights so the total stays at 100%.

    When the user edits one slider/input, the difference is absorbed
    proportionally by the other unlocked tickers. Locked weights and the
    one the user just edited are never touched.
    """
    ss = st.session_state
    if not ss.fp_tickers:
        return

    locked = [t for t in ss.fp_tickers if ss.fp_locks.get(t, False)]
    locked_sum = sum(float(ss.get(f"w_{t}", 0.0)) for t in locked)

    new_val = float(ss.get(f"w_{ticker}", 0.0))
    other_unlocked = [
        t for t in ss.fp_tickers
        if t != ticker and not ss.fp_locks.get(t, False)
    ]

    # Cap the just-edited weight if it would push the total over 100
    max_for_this = max(0.0, 100.0 - locked_sum)
    if new_val > max_for_this:
        new_val = round(max_for_this, 2)
        ss[f"w_{ticker}"] = new_val

    target = round(100.0 - locked_sum - new_val, 2)

    if not other_unlocked:
        return

    current_sum = sum(float(ss.get(f"w_{t}", 0.0)) for t in other_unlocked)

    if current_sum > 0.001:
        # Proportional rescaling
        scale = target / current_sum
        for t in other_unlocked:
            ss[f"w_{t}"] = round(float(ss[f"w_{t}"]) * scale, 2)
    else:
        # All zero — distribute equally
        share = round(target / len(other_unlocked), 2)
        for t in other_unlocked:
            ss[f"w_{t}"] = share

    # Fix rounding error by absorbing it on the last "other unlocked" ticker
    total = (
        locked_sum
        + float(ss.get(f"w_{ticker}", 0.0))
        + sum(float(ss.get(f"w_{t}", 0.0)) for t in other_unlocked)
    )
    diff = round(100.0 - total, 2)
    if abs(diff) > 0.001 and other_unlocked:
        last = other_unlocked[-1]
        ss[f"w_{last}"] = round(float(ss[f"w_{last}"]) + diff, 2)


def _allocation_donut(tickers: list[str], weights: dict[str, float]) -> go.Figure:
    """Small donut chart visualising portfolio allocation."""
    values = [weights.get(t, 0.0) for t in tickers]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=tickers,
                values=values,
                hole=0.65,
                marker=dict(
                    colors=CHART_PALETTE[: len(tickers)],
                    line=dict(color="#0a0f1e", width=2),
                ),
                textinfo="label+percent",
                textfont=dict(size=10, color="#f1f5f9"),
                hoverinfo="label+percent",
                showlegend=False,
            )
        ]
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        height=210,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        annotations=[
            dict(
                text=f"{len(tickers)}<br><span style='font-size:10px;color:#64748b;'>"
                     "ASSETS</span>",
                x=0.5, y=0.5,
                font=dict(size=22, color="#f1f5f9", family="Arial Black"),
                showarrow=False,
            )
        ],
    )
    return fig


# ---------------------------------------------------------------------------
# Sidebar — user inputs
# ---------------------------------------------------------------------------
_init_portfolio_state()

with st.sidebar:
    sidebar_logo = logo_img(height=32)
    st.markdown(
        '<div style="padding:6px 0 8px 0;">' + sidebar_logo + '</div>'
        '<div style="color:#475569; font-size:10px; font-weight:600; '
        'text-transform:uppercase; letter-spacing:0.08em; '
        'margin:0 0 14px 0;">Portfolio configuration</div>',
        unsafe_allow_html=True,
    )

    # ---- TICKERS (chips) -------------------------------------------------
    st.markdown(
        sidebar_section_header("◆", "Assets"),
        unsafe_allow_html=True,
    )

    add_col, btn_col = st.columns([3, 1])
    with add_col:
        st.text_input(
            "Add ticker",
            key="fp_new_ticker_input",
            placeholder="e.g. AAPL",
            label_visibility="collapsed",
            help="Yahoo Finance symbol — letters, digits, '.', '-', '^'",
        )
    with btn_col:
        st.button(
            "➕ Add",
            use_container_width=True,
            key="fp_add_btn",
            on_click=_cb_add_ticker,
        )

    if st.session_state.get("fp_ticker_error"):
        st.caption(f":red[⚠ {st.session_state['fp_ticker_error']}]")

    # Chips display - up to 3 per row
    if st.session_state.fp_tickers:
        n_per_row = 3
        for row_start in range(0, len(st.session_state.fp_tickers), n_per_row):
            row_tickers = st.session_state.fp_tickers[row_start: row_start + n_per_row]
            cols = st.columns(n_per_row)
            for i, t in enumerate(row_tickers):
                with cols[i]:
                    st.button(
                        f"{t}  ✕",
                        key=f"fp_chip_{t}",
                        help=f"Remove {t}",
                        use_container_width=True,
                        on_click=_cb_remove_ticker,
                        args=(t,),
                    )
    else:
        st.caption(":orange[No assets added yet — add at least 2 tickers.]")

    # Scoped style for quick-add grids — 2-column layout gives each button
    # enough room (~110 px) so no text ever wraps.
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] .fp-qa-row div[data-testid="stButton"] > button {
            padding: 0 6px !important;
            min-height: 28px !important;
            height: 28px !important;
            border-radius: 6px !important;
        }
        section[data-testid="stSidebar"] .fp-qa-row div[data-testid="stButton"] > button p {
            font-size: 11px !important;
            font-weight: 700 !important;
            white-space: nowrap !important;
            word-break: keep-all !important;
            overflow-wrap: normal !important;
            line-height: 1 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        section[data-testid="stSidebar"] .fp-qa-row [data-testid="stHorizontalBlock"] {
            gap: 0 !important;
            margin-bottom: 5px !important;
        }
        section[data-testid="stSidebar"] .fp-qa-row [data-testid="column"] {
            padding-left: 3px !important;
            padding-right: 3px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    def _quick_add_grid(picks: list[tuple[str, str]], key_prefix: str,
                        open_key: str | None = None,
                        cols_per_row: int = 2) -> None:
        """Render a tidy grid of small uniform quick-add buttons.

        ``picks`` is a list of (display_label, ticker_symbol) tuples.
        ``open_key`` is forwarded to the callback so the expander stays open
        after a click triggers a Streamlit rerun.
        """
        st.markdown('<div class="fp-qa-row">', unsafe_allow_html=True)
        for row_start in range(0, len(picks), cols_per_row):
            row = picks[row_start: row_start + cols_per_row]
            # Pad the final row with empty placeholders so all buttons stay
            # the same width (no stretching when the row is short).
            cells = list(row) + [None] * (cols_per_row - len(row))
            cols = st.columns(cols_per_row)
            for i, item in enumerate(cells):
                with cols[i]:
                    if item is None:
                        st.markdown("&nbsp;", unsafe_allow_html=True)
                        continue
                    label, sym = item
                    st.button(
                        label,
                        key=f"{key_prefix}_{sym}",
                        use_container_width=True,
                        on_click=_cb_quick_add,
                        args=(sym, open_key),
                        disabled=sym in st.session_state.fp_tickers,
                        help=f"Add {sym}",
                    )
        st.markdown('</div>', unsafe_allow_html=True)

    # Quick-add crypto — keep open after a click (sticky expander)
    with st.expander(
        "⚡ Crypto",
        expanded=st.session_state.get("fp_crypto_open", False),
    ):
        crypto_picks = [
            ("BTC", "BTC-USD"),
            ("ETH", "ETH-USD"),
            ("SOL", "SOL-USD"),
            ("XRP", "XRP-USD"),
            ("BNB", "BNB-USD"),
            ("DOGE", "DOGE-USD"),
        ]
        _quick_add_grid(
            crypto_picks, key_prefix="fp_qa", open_key="fp_crypto_open",
        )

    # Quick-add stocks & indexes — same sticky-expander behaviour
    with st.expander(
        "⚡ Stocks & indexes",
        expanded=st.session_state.get("fp_stocks_open", False),
    ):
        index_picks = [
            ("AAPL",  "AAPL"),
            ("MSFT",  "MSFT"),
            ("TSLA",  "TSLA"),
            ("NVDA",  "NVDA"),
            ("META",  "META"),
            ("SPX",   "^GSPC"),   # S&P 500  — tooltip shows ^GSPC
            ("NDX",   "^NDX"),    # Nasdaq 100
            ("GOLD",  "GC=F"),    # Gold futures
        ]
        _quick_add_grid(
            index_picks, key_prefix="fp_qi", open_key="fp_stocks_open",
        )

    tickers = list(st.session_state.fp_tickers)

    # ---- DATES with presets ---------------------------------------------
    st.divider()
    st.markdown(
        sidebar_section_header("📅", "Period"),
        unsafe_allow_html=True,
    )

    today = date.today()
    start_date = st.date_input(
        "Start date", value=None, max_value=today, key="fp_start_input",
    )
    end_date = st.date_input(
        "End date", value=None, max_value=today, key="fp_end_input",
    )

    # Inline date validation — show the issue immediately, not after Run
    if start_date is not None and end_date is not None:
        if start_date >= end_date:
            st.caption(":red[⚠ Start date must be earlier than end date.]")
        else:
            period_days = (end_date - start_date).days
            if period_days < MIN_PERIOD_DAYS:
                st.caption(
                    f":orange[⚠ Period is only {period_days} days — "
                    f"need at least {MIN_PERIOD_DAYS} for meaningful analysis.]"
                )
            else:
                st.caption(f":green[✓ Period: {period_days} days]")

    # ---- WEIGHTS with locks ----------------------------------------------
    st.divider()
    header_l, header_r = st.columns([3, 2])
    with header_l:
        st.markdown(
            sidebar_section_header("⚖", "Weights (%)", margin_bottom=6),
            unsafe_allow_html=True,
        )
    with header_r:
        st.button(
            "Equal",
            key="fp_equal_btn",
            help="Distribute 100% equally over unlocked tickers",
            use_container_width=True,
            disabled=not tickers,
            on_click=_cb_equal_weight,
        )

    weights_pct: dict[str, float] = {}
    if tickers:
        for t in tickers:
            wcol, lockcol = st.columns([4, 1])
            locked = st.session_state.fp_locks.get(t, False)
            with wcol:
                st.number_input(
                    f"{t}",
                    min_value=0.0,
                    max_value=100.0,
                    step=1.0,
                    key=f"w_{t}",
                    disabled=locked,
                    on_change=_cb_weight_changed,
                    args=(t,),
                )
                weights_pct[t] = float(st.session_state.get(f"w_{t}", 0.0))
            with lockcol:
                st.markdown(
                    '<div style="height:28px;"></div>', unsafe_allow_html=True,
                )
                lock_icon = "🔒" if locked else "🔓"
                st.button(
                    lock_icon,
                    key=f"fp_lock_{t}",
                    help=("Unlock" if locked else "Lock") + f" {t} weight",
                    use_container_width=True,
                    on_click=_cb_toggle_lock,
                    args=(t,),
                )

        # Weights are auto-balanced to 100% via _cb_weight_changed.
        # Tolerance accounts for tiny floating-point rounding errors.
        total_pct = sum(weights_pct.values())
        weights_valid = abs(total_pct - 100.0) < WEIGHT_TOLERANCE_PCT

        # Donut chart
        st.plotly_chart(
            _allocation_donut(tickers, weights_pct),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    else:
        weights_valid = False

    # ---- ASSUMPTIONS -----------------------------------------------------
    st.divider()
    st.markdown(
        sidebar_section_header("⚙", "Assumptions"),
        unsafe_allow_html=True,
    )
    risk_free_rate = st.slider(
        "Risk-free rate (annual, %)",
        min_value=0.0,
        max_value=10.0,
        value=2.0,
        step=0.1,
        key="fp_rfr_input",
        help="Typically approximated by a short-term government bond yield (e.g. 3-month T-bill).",
    ) / 100.0
    _inv_raw = st.text_input(
        "Initial investment ($)",
        value="",
        placeholder="e.g. 10 000",
        key="fp_inv_input",
        help="Hypothetical capital invested at the start date.",
    )
    try:
        initial_investment = float(_inv_raw.replace(" ", "").replace(",", "")) if _inv_raw.strip() else 0.0
    except ValueError:
        initial_investment = 0.0

    # ---- MONTE CARLO -----------------------------------------------------
    st.divider()
    st.markdown(
        sidebar_section_header("🎲", "Monte Carlo"),
        unsafe_allow_html=True,
    )
    mc_horizon_days = st.slider(
        "Horizon (trading days)",
        30, 504, 252, step=21,
        key="fp_mc_horizon_input",
        help="252 ≈ 1 trading year. 504 ≈ 2 years.",
    )
    mc_simulations = st.slider(
        "Simulations",
        100, 5000, 1000, step=100,
        key="fp_mc_sims_input",
        help="More simulations = more accurate distribution, but slower.",
    )
    st.warning(
        "Monte Carlo is a probabilistic simulation based on historical return "
        "statistics. It is not a price forecast.",
        icon="⚠️",
    )

    # ---- SAVE / LOAD CONFIG ---------------------------------------------
    st.divider()
    with st.expander("💾 Save / Load Configuration", expanded=False):
        st.download_button(
            "📥 Save current config (.json)",
            data=_build_config_json(),
            file_name=f"finport_config_{date.today()}.json",
            mime="application/json",
            use_container_width=True,
            disabled=not tickers,
        )
        st.file_uploader(
            "📤 Load config (.json)",
            type=["json"],
            key="fp_config_uploader",
            on_change=_cb_load_config,
            label_visibility="visible",
        )
        if st.session_state.get("fp_config_loaded_msg"):
            st.caption(f":green[✓ {st.session_state.pop('fp_config_loaded_msg')}]")
        if st.session_state.get("fp_config_error"):
            st.caption(f":red[⚠ {st.session_state.pop('fp_config_error')}]")

    st.divider()
    # Weights are now auto-balanced — Run is only disabled when there are
    # not enough tickers to make a portfolio.
    _missing = []
    if len(tickers) < 2:
        _missing.append("at least 2 tickers")
    if start_date is None:
        _missing.append("start date")
    if end_date is None:
        _missing.append("end date")
    elif start_date is not None and start_date >= end_date:
        _missing.append("valid date range (start < end)")
    elif start_date is not None and (end_date - start_date).days < MIN_PERIOD_DAYS:
        _missing.append(f"period ≥ {MIN_PERIOD_DAYS} days")
    if initial_investment <= 0:
        _missing.append("initial investment")

    run_disabled = bool(_missing)
    run = st.button(
        "▶  Run analysis",
        type="primary",
        use_container_width=True,
        disabled=run_disabled,
        help=(
            "Required: " + ", ".join(_missing) + "."
            if run_disabled else "Start analysis"
        ),
    )


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
# Input validation
# ---------------------------------------------------------------------------
if start_date is None or end_date is None:
    st.error("Select a start and end date in the sidebar.")
    st.stop()

if initial_investment <= 0:
    st.error("Enter an initial investment amount greater than $0.")
    st.stop()

if start_date >= end_date:
    st.error("Start date must be earlier than end date.")
    st.stop()

period_days = (end_date - start_date).days
if period_days < MIN_PERIOD_DAYS:
    st.error(
        f"Analysis period is only **{period_days} days**. "
        f"Choose at least **{MIN_PERIOD_DAYS} days** so that the covariance "
        "matrix, Markowitz optimization and Monte Carlo simulation have "
        "enough data to produce meaningful results."
    )
    st.stop()

if len(tickers) < 2:
    st.error("Select at least two tickers for a meaningful portfolio analysis.")
    st.stop()

if not weights_valid:
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
# Step 1 — Data loading
# ---------------------------------------------------------------------------
with st.spinner("Step 1 / 3  —  Downloading market data from Yahoo Finance..."):
    prices, failed = load_price_data(tickers, start_date, end_date)

if prices.empty or prices.shape[1] < 2:
    # Critical failure — clear loader so the user can actually see the
    # error and (if present) the failed-tickers dialog.
    loading_overlay.empty()
    if failed and not st.session_state.get("fp_dialog_suppressed", False):
        _failed_key = "|".join(sorted(failed.keys()))
        if st.session_state.get("fp_failed_dismissed_key") != _failed_key:
            _show_failed_tickers_dialog(failed, _failed_key)
    st.error(
        "Not enough valid price data. Try different tickers or a wider date range."
    )
    st.stop()

# Second-line check: even with a long calendar window, some tickers might
# share too few trading days (e.g. recent IPO).
if len(prices) < MIN_TRADING_ROWS:
    st.error(
        f"Only **{len(prices)} trading days** of overlapping data available "
        f"across all selected tickers (need at least {MIN_TRADING_ROWS}). "
        "Widen the date range or pick assets with more shared history."
    )
    st.stop()

# Renormalize weights over the surviving tickers
weights = pd.Series(weights_pct, dtype=float) / 100.0
weights = weights.reindex(prices.columns).dropna()
if weights.sum() == 0:
    st.error("All weights for valid tickers are zero.")
    st.stop()
weights = weights / weights.sum()


# ---------------------------------------------------------------------------
# Step 2 — Portfolio analytics
# ---------------------------------------------------------------------------
with st.spinner("Step 2 / 4  —  Computing portfolio analytics..."):
    returns = daily_returns(prices)
    norm = normalize_prices(prices)
    asset_stats = summary_per_asset(returns)
    port_metrics = annualized_portfolio_metrics(returns, weights)
    sharpe = sharpe_ratio(port_metrics["return"], port_metrics["volatility"], risk_free_rate)
    corr = correlation_matrix(returns)
    port_value = portfolio_value_series(prices, weights, initial_investment)
    equal_weights = pd.Series(1.0 / len(prices.columns), index=prices.columns)
    eq_metrics = annualized_portfolio_metrics(returns, equal_weights)
    eq_sharpe = sharpe_ratio(eq_metrics["return"], eq_metrics["volatility"], risk_free_rate)
    eq_value = portfolio_value_series(prices, equal_weights, initial_investment)

    # Advanced risk metrics
    port_daily_ret = portfolio_daily_returns(returns, weights)
    dd_info = max_drawdown(port_value)
    sortino = sortino_ratio(port_daily_ret, risk_free_rate)

# ---------------------------------------------------------------------------
# Step 3 — Optimization & market benchmark
# ---------------------------------------------------------------------------
with st.spinner("Step 3 / 4  —  Optimizing portfolio (efficient frontier)..."):
    max_sharpe_weights = optimize_max_sharpe(returns, risk_free_rate)
    min_var_weights = optimize_min_variance(returns)
    max_sharpe_metrics = annualized_portfolio_metrics(returns, max_sharpe_weights)
    min_var_metrics = annualized_portfolio_metrics(returns, min_var_weights)
    max_sharpe_value = sharpe_ratio(
        max_sharpe_metrics["return"], max_sharpe_metrics["volatility"], risk_free_rate
    )
    min_var_sharpe = sharpe_ratio(
        min_var_metrics["return"], min_var_metrics["volatility"], risk_free_rate
    )
    frontier_df = efficient_frontier(returns, n_points=40)

    # Load S&P 500 benchmark
    market_prices, market_failed = load_price_data(["^GSPC"], start_date, end_date)
    if not market_prices.empty:
        market_returns = daily_returns(market_prices).iloc[:, 0]
        market_value = portfolio_value_series(
            market_prices, pd.Series([1.0], index=market_prices.columns),
            initial_investment,
        )
        capm = compute_beta_alpha(port_daily_ret, market_returns, risk_free_rate)
        market_loaded = True
    else:
        market_returns = pd.Series(dtype=float)
        market_value = pd.Series(dtype=float)
        capm = {"beta": 0.0, "alpha": 0.0, "r_squared": 0.0, "correlation": 0.0}
        market_loaded = False


# ---------------------------------------------------------------------------
# Step 4 — Monte Carlo simulation
# ---------------------------------------------------------------------------
with st.spinner(
    f"Step 4 / 4  —  Running {mc_simulations:,} Monte Carlo paths "
    f"over {mc_horizon_days} trading days..."
):
    sims = monte_carlo_simulation(
        returns=returns,
        weights=weights,
        initial_value=initial_investment,
        horizon_days=mc_horizon_days,
        n_simulations=mc_simulations,
    )

final_mc = sims.iloc[-1]
mc_p5, mc_p50, mc_p95 = np.percentile(final_mc, [5, 50, 95])
var_95 = initial_investment - mc_p5

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
        _show_failed_tickers_dialog(failed, _failed_key)

period_str = f"{start_date.strftime('%b %Y')} – {end_date.strftime('%b %Y')}"
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
# Tabs
# ---------------------------------------------------------------------------
(
    tab_overview, tab_returns, tab_corr, tab_mc, tab_opt, tab_bench,
    tab_export, tab_glossary,
) = st.tabs([
    "Overview", "Returns & Risk", "Correlation", "Monte Carlo",
    "Optimization", "Benchmark", "Export", "Glossary",
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

    c1, c2, c3, c4 = st.columns(4)
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
    with c3:
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
    with c4:
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
    st.caption(
        "Each path is drawn from a **multivariate normal distribution** with the historical "
        "mean vector and covariance matrix. Cross-asset correlations are preserved via "
        "**Cholesky decomposition**. This assumes future returns follow the same statistical "
        "properties as historical ones — which is a simplification."
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
                            mc_p5=float(mc_p5),
                            mc_p50=float(mc_p50),
                            mc_p95=float(mc_p95),
                            mc_horizon_days=mc_horizon_days,
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
# Tab 8: Glossary
# ============================================================
with tab_glossary:
    st.subheader("Financial terms glossary")
    st.markdown(
        '<p style="color:#64748b; font-size:14px; margin-bottom:24px;">'
        "Reference for the concepts and metrics used throughout FinPort."
        "</p>",
        unsafe_allow_html=True,
    )

    glossary_data = [
        (
            "📈 Annualized Return",
            "Average daily return × 252 trading days. Represents the expected "
            "yearly gain of an asset or portfolio assuming continuation of "
            "historical patterns. Formula: μ_daily × 252.",
        ),
        (
            "⚡ Annualized Volatility",
            "Standard deviation of daily returns × √252. Measures the dispersion "
            "of returns around the mean — the higher the value, the more "
            "uncertain (risky) the future outcome. Formula: σ_daily × √252.",
        ),
        (
            "🎯 Sharpe Ratio (Sharpe, 1966)",
            "Risk-adjusted return: (Return − Risk-free rate) / Volatility. "
            "Tells you how much excess return you earn per unit of risk taken. "
            "> 1.0 is considered good, > 2.0 excellent. Below 0.5 means low "
            "compensation for risk.",
        ),
        (
            "🎯 Sortino Ratio (Sortino & Price, 1994)",
            "Like Sharpe ratio, but only penalizes **downside** volatility "
            "(returns below 0). More realistic for investors — upward swings "
            "are not 'risk'. Formula: (Return − Rf) / Downside deviation.",
        ),
        (
            "📉 Maximum Drawdown",
            "The largest peak-to-trough decline in portfolio value over a "
            "given period. Critical risk metric — shows the worst loss an "
            "investor would have actually experienced. Often paired with "
            "drawdown **duration** (time underwater) and **recovery time**.",
        ),
        (
            "📐 Beta (β)",
            "Sensitivity to market moves (CAPM). β = 1 means the asset moves "
            "1-to-1 with the market. β > 1 amplifies market moves (aggressive). "
            "β < 1 dampens them (defensive). β < 0 means inverse correlation. "
            "Calculated as: Cov(asset, market) / Var(market).",
        ),
        (
            "✨ Alpha (α)",
            "CAPM alpha — annualized excess return that cannot be explained "
            "by beta exposure to the market. Positive α means the portfolio "
            "beats the risk-adjusted market expectation. Considered the "
            "holy grail of active management; persistently positive α is rare.",
        ),
        (
            "🔗 Correlation",
            "Pearson correlation coefficient (−1 to +1) measuring co-movement "
            "between two return series. +1 = perfect lockstep (no diversification), "
            "0 = independent, −1 = perfect hedge. Low/negative correlations "
            "between portfolio components reduce overall risk.",
        ),
        (
            "📊 R² (R-squared)",
            "Proportion of portfolio variance explained by market moves. High "
            "R² (> 0.7) means the portfolio behaves mostly like the market — "
            "diversification benefit vs market is limited.",
        ),
        (
            "🛡 Value at Risk (VaR)",
            "Maximum expected loss over a given time horizon at a given "
            "confidence level. VaR 95% = the loss that won't be exceeded in "
            "95% of scenarios. Widely used in banking but criticized for "
            "ignoring 'tail' losses beyond the threshold.",
        ),
        (
            "🛡 Conditional VaR (CVaR / Expected Shortfall)",
            "Average loss in the **worst** (1 − α)% of cases — e.g., the "
            "average of the worst 5% Monte Carlo outcomes. CVaR is preferred "
            "over VaR under Basel III banking regulations because it accounts "
            "for tail risk.",
        ),
        (
            "🎲 Monte Carlo Simulation",
            "Generates thousands of possible future paths by repeatedly sampling "
            "from a statistical distribution (here: multivariate normal with "
            "historical mean and covariance). Cross-asset correlations are "
            "preserved via Cholesky decomposition. The distribution of final "
            "outcomes shows the range of plausible scenarios.",
        ),
        (
            "📐 Efficient Frontier (Markowitz, 1952)",
            "The set of optimal portfolios offering the highest expected return "
            "for each level of risk (volatility). Foundation of Modern Portfolio "
            "Theory. Any portfolio below the frontier is sub-optimal: there "
            "exists another portfolio with either more return for the same risk "
            "or less risk for the same return.",
        ),
        (
            "🎯 Max Sharpe Portfolio (Tangency Portfolio)",
            "The portfolio on the efficient frontier with the highest "
            "Sharpe ratio. In CAPM theory, this is the **tangency portfolio** — "
            "where the Capital Market Line touches the efficient frontier. "
            "Theoretically the optimal risky portfolio for any investor.",
        ),
        (
            "🛡 Minimum Variance Portfolio",
            "The leftmost point of the efficient frontier — the portfolio with "
            "the lowest possible volatility regardless of expected return. "
            "Useful for risk-averse investors prioritizing capital preservation.",
        ),
        (
            "📐 CAPM (Sharpe, 1964)",
            "Capital Asset Pricing Model: an asset's expected return equals "
            "Rf + β · (Rm − Rf), where Rf is risk-free rate, Rm is market "
            "return. Foundation of modern asset pricing — Sharpe won the "
            "Nobel Prize in 1990 for this work.",
        ),
        (
            "🏛 Risk-free Rate",
            "Theoretical return of a zero-risk investment, used as a baseline "
            "in Sharpe ratio, CAPM, and other models. Typically approximated "
            "by short-term government bond yields (e.g. 3-month T-bills in "
            "the U.S.).",
        ),
        (
            "⚖ Portfolio Weights",
            "Proportion of total capital allocated to each asset. Must sum to "
            "1 (or 100%). In a buy-and-hold portfolio, weights drift over "
            "time as assets perform differently — periodic **rebalancing** "
            "restores the target allocation.",
        ),
        (
            "🔄 Buy-and-Hold",
            "Investment strategy where assets are bought once at the start "
            "and held without modifications. Implicit in FinPort's portfolio "
            "value calculation. Alternative: periodic rebalancing back to "
            "target weights.",
        ),
        (
            "📊 252 Trading Days",
            "The conventional number of trading days per year (≈ 365 minus "
            "weekends and major holidays). Used to annualize daily statistics: "
            "annual_return = daily_return × 252, "
            "annual_volatility = daily_volatility × √252.",
        ),
    ]

    # Render glossary with 2 columns of expanders
    g_col1, g_col2 = st.columns(2)
    for i, (term, definition) in enumerate(glossary_data):
        target_col = g_col1 if i % 2 == 0 else g_col2
        with target_col:
            with st.expander(term):
                st.markdown(definition)

    st.divider()
    st.caption(
        "**Sources:** Markowitz (1952) 'Portfolio Selection', Sharpe (1964) 'Capital "
        "Asset Prices', Sortino & Price (1994) 'Performance Measurement in a "
        "Downside Risk Framework', Basel Committee on Banking Supervision "
        "(2019) 'Minimum Capital Requirements for Market Risk'."
    )
