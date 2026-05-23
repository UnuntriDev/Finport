"""Deterministic synthetic price data for offline demos."""
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

_BENCHMARK_TICKER = "^GSPC"
_BENCHMARK_BASE_PRICE = 4000.0
_BENCHMARK_DRIFT = 0.00045
_BENCHMARK_VOL = 0.009
_BENCHMARK_SEED = 7


def demo_weights_pct(tickers: list[str]) -> dict[str, float]:
    """Equal weights summing exactly to 100% (residual absorbed by last)."""
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
    """Stable synthetic adjusted-close prices.

    Each asset is ``beta * market + idiosyncratic_noise`` so the synthetic
    ^GSPC benchmark genuinely correlates with the portfolio and CAPM stays
    meaningful in demo mode.
    """
    index = pd.bdate_range(start_date, end_date)
    if len(index) == 0:
        return pd.DataFrame(), {}

    market_returns = _generate_market_returns(len(index))
    data: dict[str, np.ndarray] = {}

    for ticker in tickers:
        if ticker == _BENCHMARK_TICKER:
            data[ticker] = _BENCHMARK_BASE_PRICE * np.cumprod(1.0 + market_returns)
            continue
        data[ticker] = _generate_asset_path(ticker, market_returns)

    prices = pd.DataFrame(data, index=index)
    prices.index.name = "Date"
    return prices.round(2), {}


def _generate_market_returns(n_days: int) -> np.ndarray:
    rng = np.random.default_rng(_BENCHMARK_SEED)
    return rng.normal(_BENCHMARK_DRIFT, _BENCHMARK_VOL, n_days)


def _generate_asset_path(ticker: str, market_returns: np.ndarray) -> np.ndarray:
    seed = zlib.crc32(ticker.encode("utf-8"))
    rng = np.random.default_rng(seed)
    beta = 0.75 + (seed % 70) / 100
    drift = 0.00015 + (seed % 17) / 100000
    idiosyncratic = rng.normal(0.0, 0.006 + (seed % 11) / 2000, len(market_returns))
    returns = drift + beta * market_returns + idiosyncratic
    base_price = 80.0 + (seed % 220)
    return base_price * np.cumprod(1.0 + returns)
