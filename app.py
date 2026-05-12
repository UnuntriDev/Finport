"""FinPort — Streamlit entry point.

Wires together user inputs (sidebar), data loading, analysis, and
visualization into a tabbed fintech-style dashboard.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date
from html import escape

import plotly.graph_objects as go
import streamlit as st

from constants import (
    LOADER_MIN_SECONDS,
    LOADER_PAINT_DELAY,
    MAX_TICKERS,
    MIN_PERIOD_DAYS,
    WEIGHT_TOLERANCE_PCT,
)
from models import PortfolioAnalysisRequest
from portfolio_config import normalize_weights_to_100, parse_portfolio_config
from portfolio_state import rebalance_after_weight_change, redistribute_equal_locked
from services.portfolio_analysis import (
    PortfolioAnalysisError,
    run_portfolio_analysis,
)
from theme import CHART_PALETTE
from ticker_utils import normalize_ticker
from ui.dialogs import show_failed_tickers_dialog
from ui.loader import MONEY_LOADER_HTML
from ui.logo import logo_img
from ui_components import sidebar_section_header
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
    weights = {ticker: float(ss.get(f"w_{ticker}", 0.0)) for ticker in tickers}
    updated = redistribute_equal_locked(tickers, weights, ss.fp_locks)
    for ticker, weight in updated.items():
        ss[f"w_{ticker}"] = weight


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

    weights = {
        ticker_symbol: float(ss.get(f"w_{ticker_symbol}", 0.0))
        for ticker_symbol in ss.fp_tickers
    }
    updated = rebalance_after_weight_change(
        ss.fp_tickers,
        weights,
        ss.fp_locks,
        ticker,
    )
    for ticker_symbol, weight in updated.items():
        ss[f"w_{ticker_symbol}"] = weight


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
    mc_method_label = st.selectbox(
        "Simulation method",
        ["Parametric normal", "Historical bootstrap"],
        key="fp_mc_method_input",
        help=(
            "Parametric normal uses historical mean/covariance. Historical "
            "bootstrap samples actual past return days with replacement."
        ),
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
# Portfolio analysis pipeline
# ---------------------------------------------------------------------------
analysis_request = PortfolioAnalysisRequest(
    tickers=tickers,
    weights_pct=weights_pct,
    start_date=start_date,
    end_date=end_date,
    initial_investment=initial_investment,
    risk_free_rate=risk_free_rate,
    mc_horizon_days=mc_horizon_days,
    mc_simulations=mc_simulations,
    mc_method_label=mc_method_label,
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
# Dashboard tabs
# ---------------------------------------------------------------------------
render_dashboard_tabs(
    result=analysis_result,
    start_date=start_date,
    end_date=end_date,
    initial_investment=initial_investment,
    risk_free_rate=risk_free_rate,
    mc_horizon_days=mc_horizon_days,
    mc_method_label=mc_method_label,
)
