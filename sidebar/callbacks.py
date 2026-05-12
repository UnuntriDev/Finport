"""Streamlit widget callbacks for the sidebar (run before next render)."""
from __future__ import annotations

import json
from datetime import date

import streamlit as st

from constants import MAX_TICKERS
from portfolio_config import normalize_weights_to_100, parse_portfolio_config
from portfolio_state import rebalance_after_weight_change, redistribute_equal_locked
from ticker_utils import normalize_ticker


def redistribute_equal_locked_session() -> None:
    """Split 100% over unlocked tickers, keeping locked weights fixed."""
    ss = st.session_state
    tickers = ss.fp_tickers
    if not tickers:
        return
    weights = {ticker: float(ss.get(f"w_{ticker}", 0.0)) for ticker in tickers}
    updated = redistribute_equal_locked(tickers, weights, ss.fp_locks)
    for ticker, weight in updated.items():
        ss[f"w_{ticker}"] = weight


def add_ticker_to_state(ticker: str, open_key: str | None = None) -> bool:
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
    redistribute_equal_locked_session()
    ss["fp_ticker_error"] = ""
    return True


def cb_add_ticker() -> None:
    """Handle ➕ Add button — read text input and add to portfolio."""
    ss = st.session_state
    raw = ss.get("fp_new_ticker_input", "")
    ticker = normalize_ticker(raw)
    if not ticker:
        ss["fp_ticker_error"] = (
            "Enter a ticker symbol."
            if not str(raw).strip()
            else f"Invalid ticker '{str(raw).strip().upper()}'."
        )
        return
    if add_ticker_to_state(ticker):
        ss["fp_new_ticker_input"] = ""


def cb_remove_ticker(ticker: str) -> None:
    """Handle chip ✕ click — remove ticker and rebalance."""
    ss = st.session_state
    if ticker not in ss.fp_tickers:
        return
    ss.fp_tickers.remove(ticker)
    ss.fp_locks.pop(ticker, None)
    ss.pop(f"w_{ticker}", None)
    redistribute_equal_locked_session()


def cb_toggle_lock(ticker: str) -> None:
    """Handle 🔒/🔓 button — flip the lock for a single ticker."""
    ss = st.session_state
    ss.fp_locks[ticker] = not ss.fp_locks.get(ticker, False)


def cb_equal_weight() -> None:
    """Handle "Equal" button — redistribute 100% across unlocked tickers."""
    redistribute_equal_locked_session()


def cb_quick_add(ticker: str, open_key: str | None = None) -> None:
    """Add a popular ticker (e.g. crypto) without typing.

    ``open_key`` is a session-state flag set to True so the triggering
    expander stays open across the Streamlit rerun.
    """
    add_ticker_to_state(ticker, open_key=open_key)


def cb_weight_changed(ticker: str) -> None:
    """Auto-rebalance other unlocked weights to keep total at 100%."""
    ss = st.session_state
    if not ss.fp_tickers:
        return
    weights = {
        symbol: float(ss.get(f"w_{symbol}", 0.0))
        for symbol in ss.fp_tickers
    }
    updated = rebalance_after_weight_change(
        ss.fp_tickers,
        weights,
        ss.fp_locks,
        ticker,
    )
    for symbol, weight in updated.items():
        ss[f"w_{symbol}"] = weight


def cb_load_config() -> None:
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

    for old_ticker in list(ss.fp_tickers):
        ss.pop(f"w_{old_ticker}", None)

    ss.fp_tickers = config.tickers
    ss.fp_locks = dict(config.locks)

    normalized_weights = normalize_weights_to_100(config.weights)
    for ticker in ss.fp_tickers:
        ss[f"w_{ticker}"] = normalized_weights.get(ticker, 0.0)

    if config.start is not None:
        ss.fp_start_input = config.start
    if config.end is not None:
        ss.fp_end_input = config.end

    ss["fp_config_loaded_msg"] = (
        f"Loaded {len(ss.fp_tickers)} tickers from config."
    )
    ss["fp_config_error"] = ""


def build_config_json() -> str:
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
