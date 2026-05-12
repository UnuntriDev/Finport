"""Deterministic offline market data for demos and screenshots."""
from __future__ import annotations

import zlib
from datetime import date

import numpy as np
import pandas as pd

DEMO_TICKERS = ["AAPL", "MSFT", "NVDA", "META"]
DEMO_START_DATE = date(2023, 1, 3)
DEMO_END_DATE = date(2026, 5, 11)
DEMO_INITIAL_INVESTMENT = 10_000.0
DEMO_SECTORS = {
    "AAPL": "Technology",
    "MSFT": "Technology",
    "NVDA": "Semiconductors",
    "META": "Communication Services",
    "^GSPC": "Market Index",
}


def demo_weights_pct(tickers: list[str]) -> dict[str, float]:
    """Return equal demo weights that sum exactly to 100%."""
    if not tickers:
        return {}
    share = round(100.0 / len(tickers), 2)
    weights = {ticker: share for ticker in tickers}
    diff = round(100.0 - sum(weights.values()), 2)
    weights[tickers[-1]] = round(weights[tickers[-1]] + diff, 2)
    return weights


def load_demo_price_data(
    tickers: list[str],
    start_date: date,
    end_date: date,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Generate stable synthetic adjusted-close data for offline demos."""
    index = pd.bdate_range(start_date, end_date)
    if len(index) == 0:
        return pd.DataFrame(), {}

    market_rng = np.random.default_rng(7)
    market_returns = market_rng.normal(0.00045, 0.009, len(index))
    data = {}
    for ticker in tickers:
        seed = zlib.crc32(ticker.encode("utf-8"))
        rng = np.random.default_rng(seed)
        beta = 0.75 + (seed % 70) / 100
        drift = 0.00015 + (seed % 17) / 100000
        noise = rng.normal(0.0, 0.006 + (seed % 11) / 2000, len(index))
        returns = drift + beta * market_returns + noise
        base_price = 80.0 + (seed % 220)
        data[ticker] = base_price * np.cumprod(1.0 + returns)

    prices = pd.DataFrame(data, index=index)
    prices.index.name = "Date"
    return prices.round(2), {}
