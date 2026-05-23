"""Sidebar section renderers — one function per logical block."""
from __future__ import annotations

from datetime import date

import streamlit as st

from constants import MIN_PERIOD_DAYS, WEIGHT_TOLERANCE_PCT
from models import MonteCarloMethod
from sidebar.callbacks import (
    build_config_json,
    cb_add_ticker,
    cb_equal_weight,
    cb_load_config,
    cb_quick_add,
    cb_remove_ticker,
    cb_toggle_lock,
    cb_weight_changed,
)
from sidebar.donut import allocation_donut
from ui_components import sidebar_section_header

_CRYPTO_PICKS = [
    ("BTC", "BTC-USD"),
    ("ETH", "ETH-USD"),
    ("SOL", "SOL-USD"),
    ("XRP", "XRP-USD"),
    ("BNB", "BNB-USD"),
    ("DOGE", "DOGE-USD"),
]

_INDEX_PICKS = [
    ("AAPL", "AAPL"),
    ("MSFT", "MSFT"),
    ("TSLA", "TSLA"),
    ("NVDA", "NVDA"),
    ("META", "META"),
    ("SPX", "^GSPC"),
    ("NDX", "^NDX"),
    ("GOLD", "GC=F"),
]

_QUICK_ADD_CSS = """
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
"""


def render_assets_section() -> list[str]:
    st.markdown(sidebar_section_header("◆", "Assets"), unsafe_allow_html=True)

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
        st.button("➕ Add", use_container_width=True, key="fp_add_btn", on_click=cb_add_ticker)

    if st.session_state.get("fp_ticker_error"):
        st.caption(f":red[⚠ {st.session_state['fp_ticker_error']}]")

    _render_ticker_chips()
    st.markdown(_QUICK_ADD_CSS, unsafe_allow_html=True)
    _render_quick_add_expander("⚡ Crypto", _CRYPTO_PICKS, "fp_qa", "fp_crypto_open")
    _render_quick_add_expander("⚡ Stocks & indexes", _INDEX_PICKS, "fp_qi", "fp_stocks_open")

    return list(st.session_state.fp_tickers)


def render_dates_section() -> tuple[date | None, date | None]:
    st.divider()
    st.markdown(sidebar_section_header("📅", "Period"), unsafe_allow_html=True)

    today = date.today()
    start_date = st.date_input(
        "Start date", value=None, max_value=today, key="fp_start_input",
    )
    end_date = st.date_input(
        "End date", value=None, max_value=today, key="fp_end_input",
    )

    _render_date_validation_caption(start_date, end_date)
    return start_date, end_date


def render_weights_section(tickers: list[str]) -> tuple[dict[str, float], bool]:
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
            on_click=cb_equal_weight,
        )

    weights_pct: dict[str, float] = {}
    if not tickers:
        return weights_pct, False

    for ticker in tickers:
        weights_pct[ticker] = _render_weight_row(ticker)

    total = sum(weights_pct.values())
    weights_valid = abs(total - 100.0) < WEIGHT_TOLERANCE_PCT

    st.plotly_chart(
        allocation_donut(tickers, weights_pct),
        use_container_width=True,
        config={"displayModeBar": False},
    )
    return weights_pct, weights_valid


def render_assumptions_section() -> tuple[float, float]:
    st.divider()
    st.markdown(sidebar_section_header("⚙", "Assumptions"), unsafe_allow_html=True)

    risk_free_rate = st.slider(
        "Risk-free rate (annual, %)",
        min_value=0.0,
        max_value=10.0,
        value=2.0,
        step=0.1,
        key="fp_rfr_input",
        help=(
            "Typically approximated by a short-term government bond yield "
            "(e.g. 3-month T-bill)."
        ),
    ) / 100.0

    investment_raw = st.text_input(
        "Initial investment ($)",
        value="",
        placeholder="e.g. 10 000",
        key="fp_inv_input",
        help="Hypothetical capital invested at the start date.",
    )
    initial_investment = _parse_money(investment_raw)
    return risk_free_rate, initial_investment


def render_monte_carlo_section() -> tuple[int, int, str]:
    st.divider()
    st.markdown(sidebar_section_header("🎲", "Monte Carlo"), unsafe_allow_html=True)

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
        [method.value for method in MonteCarloMethod],
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
    return mc_horizon_days, mc_simulations, mc_method_label


def render_demo_section(query_demo: bool) -> bool:
    st.divider()
    demo_mode = st.toggle(
        "Demo / offline mode",
        value=query_demo,
        key="fp_demo_mode",
        help=(
            "Use deterministic local demo prices instead of Yahoo Finance. "
            "Useful for presentations, screenshots and offline testing."
        ),
    )
    if demo_mode:
        st.caption(
            ":green[✓ Demo mode uses a local sample portfolio if inputs are empty.]"
        )
    return demo_mode


def render_save_load_section(tickers: list[str]) -> None:
    st.divider()
    with st.expander("💾 Save / Load Configuration", expanded=False):
        st.download_button(
            "📥 Save current config (.json)",
            data=build_config_json(),
            file_name=f"finport_config_{date.today()}.json",
            mime="application/json",
            use_container_width=True,
            disabled=not tickers,
        )
        st.file_uploader(
            "📤 Load config (.json)",
            type=["json"],
            key="fp_config_uploader",
            on_change=cb_load_config,
            label_visibility="visible",
        )
        if st.session_state.get("fp_config_loaded_msg"):
            st.caption(f":green[✓ {st.session_state.pop('fp_config_loaded_msg')}]")
        if st.session_state.get("fp_config_error"):
            st.caption(f":red[⚠ {st.session_state.pop('fp_config_error')}]")


def render_run_button(
    *,
    tickers: list[str],
    start_date: date | None,
    end_date: date | None,
    initial_investment: float,
    demo_mode: bool,
    query_autorun: bool,
) -> bool:
    st.divider()
    missing = _missing_requirements(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        initial_investment=initial_investment,
        demo_mode=demo_mode,
    )
    run_clicked = st.button(
        "▶  Run analysis",
        type="primary",
        use_container_width=True,
        disabled=bool(missing),
        help=(
            "Required: " + ", ".join(missing) + "."
            if missing else "Start analysis"
        ),
    )
    return run_clicked or (query_autorun and demo_mode)


def _render_ticker_chips() -> None:
    tickers = st.session_state.fp_tickers
    if not tickers:
        st.caption(":orange[No assets added yet — add at least 2 tickers.]")
        return

    chips_per_row = 3
    for row_start in range(0, len(tickers), chips_per_row):
        row = tickers[row_start: row_start + chips_per_row]
        cols = st.columns(chips_per_row)
        for col, ticker in zip(cols, row, strict=False):
            with col:
                st.button(
                    f"{ticker}  ✕",
                    key=f"fp_chip_{ticker}",
                    help=f"Remove {ticker}",
                    use_container_width=True,
                    on_click=cb_remove_ticker,
                    args=(ticker,),
                )


def _render_quick_add_expander(
    label: str,
    picks: list[tuple[str, str]],
    key_prefix: str,
    open_key: str,
) -> None:
    with st.expander(label, expanded=st.session_state.get(open_key, False)):
        _render_quick_add_grid(picks, key_prefix=key_prefix, open_key=open_key)


def _render_quick_add_grid(
    picks: list[tuple[str, str]],
    key_prefix: str,
    open_key: str | None = None,
    cols_per_row: int = 2,
) -> None:
    st.markdown('<div class="fp-qa-row">', unsafe_allow_html=True)
    for row_start in range(0, len(picks), cols_per_row):
        row = picks[row_start: row_start + cols_per_row]
        cells = list(row) + [None] * (cols_per_row - len(row))
        cols = st.columns(cols_per_row)
        for col, item in zip(cols, cells, strict=False):
            with col:
                if item is None:
                    st.markdown("&nbsp;", unsafe_allow_html=True)
                    continue
                label, symbol = item
                st.button(
                    label,
                    key=f"{key_prefix}_{symbol}",
                    use_container_width=True,
                    on_click=cb_quick_add,
                    args=(symbol, open_key),
                    disabled=symbol in st.session_state.fp_tickers,
                    help=f"Add {symbol}",
                )
    st.markdown('</div>', unsafe_allow_html=True)


def _render_date_validation_caption(start: date | None, end: date | None) -> None:
    if start is None or end is None:
        return
    if start >= end:
        st.caption(":red[⚠ Start date must be earlier than end date.]")
        return
    period_days = (end - start).days
    if period_days < MIN_PERIOD_DAYS:
        st.caption(
            f":orange[⚠ Period is only {period_days} days — "
            f"need at least {MIN_PERIOD_DAYS} for meaningful analysis.]"
        )
    else:
        st.caption(f":green[✓ Period: {period_days} days]")


def _render_weight_row(ticker: str) -> float:
    wcol, lockcol = st.columns([4, 1])
    locked = st.session_state.fp_locks.get(ticker, False)
    with wcol:
        st.number_input(
            f"{ticker}",
            min_value=0.0,
            max_value=100.0,
            step=1.0,
            key=f"w_{ticker}",
            disabled=locked,
            on_change=cb_weight_changed,
            args=(ticker,),
        )
        weight_pct = float(st.session_state.get(f"w_{ticker}", 0.0))
    with lockcol:
        st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
        lock_icon = "🔒" if locked else "🔓"
        st.button(
            lock_icon,
            key=f"fp_lock_{ticker}",
            help=("Unlock" if locked else "Lock") + f" {ticker} weight",
            use_container_width=True,
            on_click=cb_toggle_lock,
            args=(ticker,),
        )
    return weight_pct


def _parse_money(raw: str) -> float:
    cleaned = raw.replace(" ", "").replace(",", "").strip()
    if not cleaned:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _missing_requirements(
    *,
    tickers: list[str],
    start_date: date | None,
    end_date: date | None,
    initial_investment: float,
    demo_mode: bool,
) -> list[str]:
    missing: list[str] = []
    if len(tickers) < 2 and not demo_mode:
        missing.append("at least 2 tickers")
    if start_date is None and not demo_mode:
        missing.append("start date")
    if end_date is None and not demo_mode:
        missing.append("end date")
    elif start_date is not None and end_date is not None:
        if start_date >= end_date:
            missing.append("valid date range (start < end)")
        elif (end_date - start_date).days < MIN_PERIOD_DAYS:
            missing.append(f"period ≥ {MIN_PERIOD_DAYS} days")
    if initial_investment <= 0 and not demo_mode:
        missing.append("initial investment")
    return missing
