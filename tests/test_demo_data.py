"""Tests for the offline demo data generator."""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from analysis import compute_beta_alpha, daily_returns, portfolio_daily_returns
from demo_data import load_demo_price_data


def test_demo_data_generates_business_day_index():
    prices, failed = load_demo_price_data(
        ["AAPL", "MSFT"], date(2024, 1, 1), date(2024, 3, 31),
    )
    assert failed == {}
    assert not prices.empty
    assert prices.index.inferred_freq in {"B", "C"}
    assert list(prices.columns) == ["AAPL", "MSFT"]


def test_demo_data_is_deterministic():
    first, _ = load_demo_price_data(["AAPL"], date(2024, 1, 1), date(2024, 2, 1))
    second, _ = load_demo_price_data(["AAPL"], date(2024, 1, 1), date(2024, 2, 1))
    assert (first == second).all().all()


def test_demo_benchmark_correlates_with_portfolio_assets():
    """^GSPC must be the shared market factor, not independent noise.

    Without this property, CAPM (beta/alpha/R²) in demo mode is meaningless.
    """
    prices, _ = load_demo_price_data(
        ["AAPL", "MSFT", "NVDA", "META", "^GSPC"],
        date(2023, 1, 3),
        date(2024, 6, 30),
    )
    returns = daily_returns(prices)
    asset_returns = returns[["AAPL", "MSFT", "NVDA", "META"]]
    weights = pd.Series(0.25, index=asset_returns.columns)
    portfolio_returns = portfolio_daily_returns(asset_returns, weights)
    market_returns = returns["^GSPC"]

    capm = compute_beta_alpha(portfolio_returns, market_returns, 0.02)
    assert capm["correlation"] > 0.5, (
        f"Demo CAPM correlation should be meaningfully positive, "
        f"got {capm['correlation']:.3f}"
    )
    assert capm["r_squared"] > 0.25
    assert 0.5 < capm["beta"] < 1.5


def test_demo_data_handles_empty_date_range():
    prices, failed = load_demo_price_data(["AAPL"], date(2024, 1, 6), date(2024, 1, 6))
    # Saturday-only range — yields no business days
    assert prices.empty
    assert failed == {}


def test_demo_prices_are_positive():
    prices, _ = load_demo_price_data(
        ["AAPL", "MSFT", "^GSPC"], date(2024, 1, 1), date(2024, 6, 30),
    )
    assert (prices > 0).all().all()
    assert np.isfinite(prices.values).all()
