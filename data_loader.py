"""Market data loader.

Wraps `yfinance` with Streamlit caching so the same query is not refetched
on every UI interaction. Downloads each ticker individually so newer yfinance
versions cannot silently drop tickers due to MultiIndex restructuring.
"""
from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import date

import pandas as pd
import streamlit as st
import yfinance as yf

from ticker_utils import normalize_ticker

logger = logging.getLogger(__name__)


@st.cache_data(show_spinner=False, ttl=60 * 60)
def load_price_data(
    tickers: Iterable[str],
    start: date,
    end: date,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Download adjusted close prices for every requested ticker.

    Returns ``(prices, failed)`` where ``prices`` is a wide DataFrame indexed
    by date (one column per ticker) and ``failed`` is a ``{ticker: reason}``
    dict explaining *why* each failing ticker was excluded.
    """
    failed: dict[str, str] = {}
    normalized_tickers: list[str] = []
    for raw_ticker in tickers:
        ticker = normalize_ticker(raw_ticker)
        if ticker:
            normalized_tickers.append(ticker)
        else:
            failed[str(raw_ticker)] = "Invalid ticker symbol format."

    tickers = list(dict.fromkeys(normalized_tickers))
    if not tickers:
        return pd.DataFrame(), failed

    series_list: list[pd.Series] = []

    for ticker in tickers:
        try:
            raw = yf.download(
                tickers=ticker,
                start=start,
                end=end,
                auto_adjust=True,
                progress=False,
                multi_level_index=False,
            )
            if raw is None or raw.empty:
                failed[ticker] = (
                    "Symbol not found on Yahoo Finance "
                    "(possibly delisted or wrong symbol)."
                )
                continue

            # With auto_adjust=True the "Close" column is already adjusted.
            if "Close" in raw.columns:
                s = raw["Close"].rename(ticker)
            elif "Adj Close" in raw.columns:
                s = raw["Adj Close"].rename(ticker)
            else:
                failed[ticker] = "No price column returned by Yahoo Finance."
                continue

            if s.dropna().empty:
                failed[ticker] = (
                    "No price data in the selected date range "
                    "(asset may not have existed yet)."
                )
                continue

            series_list.append(s)

        except Exception as exc:
            logger.warning(
                "Failed to download ticker %s from Yahoo Finance", ticker,
                exc_info=True,
            )
            failed[ticker] = f"Network/API error: {type(exc).__name__}."

    if not series_list:
        # Mark every ticker that didn't already have a reason as "no data"
        for t in tickers:
            failed.setdefault(t, "No usable data returned.")
        return pd.DataFrame(), failed

    prices = pd.concat(series_list, axis=1)
    prices = prices.dropna(axis=1, how="all")
    prices = prices.dropna(axis=0, how="any")

    # Re-check which tickers survived the NaN drop
    found = set(prices.columns)
    for t in tickers:
        if t not in found and t not in failed:
            failed[t] = (
                "Insufficient overlapping trading days with other selected "
                "tickers (excluded after aligning dates)."
            )

    return prices, failed


@st.cache_data(show_spinner=False, ttl=60 * 60 * 6)
def load_sector_info(tickers: Iterable[str]) -> dict[str, str]:
    """Fetch sector (industry classification) for each ticker.

    Falls back to 'Cryptocurrency', 'ETF / Fund', 'Market Index', or 'Others'
    depending on instrument type.
    Cached for 6 hours since sector data changes very rarely.
    """
    sectors: dict[str, str] = {}
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info or {}
            sector = info.get("sector")
            if sector:
                sectors[ticker] = sector
                continue
            quote_type = (info.get("quoteType") or "").upper()
            if quote_type == "CRYPTOCURRENCY":
                sectors[ticker] = "Cryptocurrency"
            elif quote_type == "ETF":
                sectors[ticker] = "ETF / Fund"
            elif quote_type == "INDEX":
                sectors[ticker] = "Market Index"
            else:
                sectors[ticker] = "Others"
        except Exception:
            logger.warning("Failed to load sector info for %s", ticker, exc_info=True)
            sectors[ticker] = "Others"
    return sectors
