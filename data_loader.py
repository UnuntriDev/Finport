"""Yahoo Finance loader with Streamlit caching.

Downloads each ticker separately so newer yfinance versions can't silently
drop tickers via MultiIndex restructuring.
"""
from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import date

import pandas as pd
import streamlit as st
import yfinance as yf

from ticker_utils import normalize_ticker

logger = logging.getLogger(__name__)

# Expected yfinance failure modes — translated into friendly failed[ticker] reasons.
_YF_RECOVERABLE_ERRORS: tuple[type[BaseException], ...] = (
    OSError, ValueError, RuntimeError, KeyError,
)

_NO_DATA_REASON = "No usable data returned."


@st.cache_data(show_spinner=False, ttl=60 * 60)
def load_price_data(
    tickers: Sequence[str],
    start: date,
    end: date,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Return (prices, failed). `failed` maps ticker → reason for exclusion."""
    failed: dict[str, str] = {}
    valid_tickers = _normalize_input_tickers(tickers, failed)
    if not valid_tickers:
        return pd.DataFrame(), failed

    series_list: list[pd.Series] = []
    for ticker in valid_tickers:
        series = _download_ticker_series(ticker, start, end, failed)
        if series is not None:
            series_list.append(series)

    if not series_list:
        for ticker in valid_tickers:
            failed.setdefault(ticker, _NO_DATA_REASON)
        return pd.DataFrame(), failed

    prices = pd.concat(series_list, axis=1).dropna(axis=1, how="all").dropna(axis=0, how="any")
    _record_dropped_tickers(valid_tickers, prices.columns, failed)
    return prices, failed


@st.cache_data(show_spinner=False, ttl=60 * 60 * 6)
def load_sector_info(tickers: Sequence[str]) -> dict[str, str]:
    """Sector per ticker. Falls back to quote-type label or 'Others'."""
    return {ticker: _resolve_sector(ticker) for ticker in tickers}


def _normalize_input_tickers(
    tickers: Sequence[str],
    failed: dict[str, str],
) -> list[str]:
    seen: list[str] = []
    for raw_ticker in tickers:
        normalized = normalize_ticker(raw_ticker)
        if not normalized:
            failed[str(raw_ticker)] = "Invalid ticker symbol format."
            continue
        if normalized not in seen:
            seen.append(normalized)
    return seen


def _download_ticker_series(
    ticker: str,
    start: date,
    end: date,
    failed: dict[str, str],
) -> pd.Series | None:
    try:
        raw = yf.download(
            tickers=ticker,
            start=start,
            end=end,
            auto_adjust=True,
            progress=False,
            multi_level_index=False,
        )
    except _YF_RECOVERABLE_ERRORS as exc:
        logger.warning("Failed to download %s from Yahoo Finance", ticker, exc_info=True)
        failed[ticker] = f"Network/API error: {type(exc).__name__}."
        return None

    if raw is None or raw.empty:
        failed[ticker] = (
            "Symbol not found on Yahoo Finance (possibly delisted or wrong symbol)."
        )
        return None

    if "Close" in raw.columns:
        series = raw["Close"].rename(ticker)
    elif "Adj Close" in raw.columns:
        series = raw["Adj Close"].rename(ticker)
    else:
        failed[ticker] = "No price column returned by Yahoo Finance."
        return None

    if series.dropna().empty:
        failed[ticker] = (
            "No price data in the selected date range (asset may not have existed yet)."
        )
        return None

    return series


def _record_dropped_tickers(
    requested: list[str],
    surviving: pd.Index,
    failed: dict[str, str],
) -> None:
    surviving_set = set(surviving)
    for ticker in requested:
        if ticker not in surviving_set and ticker not in failed:
            failed[ticker] = (
                "Insufficient overlapping trading days with other selected tickers."
            )


def _resolve_sector(ticker: str) -> str:
    try:
        info = yf.Ticker(ticker).info or {}
    except _YF_RECOVERABLE_ERRORS:
        logger.warning("Failed to load sector info for %s", ticker, exc_info=True)
        return "Others"

    sector = info.get("sector")
    if sector:
        return sector

    quote_type = (info.get("quoteType") or "").upper()
    if quote_type == "CRYPTOCURRENCY":
        return "Cryptocurrency"
    if quote_type == "ETF":
        return "ETF / Fund"
    if quote_type == "INDEX":
        return "Market Index"
    return "Others"
