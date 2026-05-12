import numpy as np
import pandas as pd
import pytest

from analysis import (
    annualized_portfolio_metrics,
    cagr,
    daily_returns,
    max_drawdown,
    monte_carlo_simulation,
    optimize_max_sharpe,
    optimize_min_variance,
    portfolio_value_series,
    sharpe_ratio,
    sortino_ratio,
)


def _sample_prices() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=80, freq="B")
    rng = np.random.default_rng(7)
    return pd.DataFrame(
        {
            "AAPL": 100 * np.cumprod(1 + rng.normal(0.0010, 0.010, len(index))),
            "MSFT": 120 * np.cumprod(1 + rng.normal(0.0008, 0.009, len(index))),
            "META": 90 * np.cumprod(1 + rng.normal(0.0012, 0.012, len(index))),
        },
        index=index,
    )


def test_daily_returns_shape_and_no_first_nan_row():
    returns = daily_returns(_sample_prices())

    assert returns.shape == (79, 3)
    assert not returns.isna().any().any()


def test_portfolio_metrics_are_finite_and_volatility_non_negative():
    returns = daily_returns(_sample_prices())
    weights = pd.Series({"AAPL": 0.4, "MSFT": 0.3, "META": 0.3})

    metrics = annualized_portfolio_metrics(returns, weights)

    assert np.isfinite(metrics["return"])
    assert np.isfinite(metrics["volatility"])
    assert metrics["volatility"] >= 0


def test_portfolio_value_starts_at_initial_value():
    prices = _sample_prices()
    weights = pd.Series({"AAPL": 0.4, "MSFT": 0.3, "META": 0.3})

    values = portfolio_value_series(prices, weights, 10_000)

    assert values.iloc[0] == 10_000
    assert values.name == "portfolio_value"


def test_max_drawdown_for_monotonic_growth_is_zero():
    values = pd.Series(
        [100, 105, 110, 120],
        index=pd.date_range("2024-01-01", periods=4),
    )

    result = max_drawdown(values)

    assert result["max_drawdown"] == 0.0
    assert (result["drawdown_series"] == 0.0).all()


def test_optimizer_weights_are_valid_probabilities():
    returns = daily_returns(_sample_prices())

    for optimizer in (optimize_max_sharpe, optimize_min_variance):
        weights = optimizer(returns)

        assert list(weights.index) == list(returns.columns)
        assert np.isclose(weights.sum(), 1.0)
        assert (weights >= 0).all()
        assert (weights <= 1).all()


def test_monte_carlo_output_shape_and_initial_row():
    returns = daily_returns(_sample_prices())
    weights = pd.Series({"AAPL": 0.4, "MSFT": 0.3, "META": 0.3})

    paths = monte_carlo_simulation(
        returns=returns,
        weights=weights,
        initial_value=10_000,
        horizon_days=20,
        n_simulations=50,
    )

    assert paths.shape == (21, 50)
    assert (paths.iloc[0] == 10_000).all()


def test_bootstrap_monte_carlo_output_shape_and_initial_row():
    returns = daily_returns(_sample_prices())
    weights = pd.Series({"AAPL": 0.4, "MSFT": 0.3, "META": 0.3})

    paths = monte_carlo_simulation(
        returns=returns,
        weights=weights,
        initial_value=10_000,
        horizon_days=20,
        n_simulations=50,
        method="bootstrap",
    )

    assert paths.shape == (21, 50)
    assert (paths.iloc[0] == 10_000).all()


def test_monte_carlo_rejects_unknown_method():
    returns = daily_returns(_sample_prices())
    weights = pd.Series({"AAPL": 0.4, "MSFT": 0.3, "META": 0.3})

    with pytest.raises(ValueError, match="method"):
        monte_carlo_simulation(
            returns=returns,
            weights=weights,
            initial_value=10_000,
            horizon_days=20,
            n_simulations=50,
            method="bad-method",
        )


def test_cagr_for_doubled_portfolio_over_one_trading_year():
    values = pd.Series(
        np.linspace(100.0, 200.0, 253),
        index=pd.date_range("2024-01-01", periods=253, freq="B"),
    )

    assert np.isclose(cagr(values), 1.0)


def test_risk_ratios_handle_zero_volatility_inputs():
    assert sharpe_ratio(0.1, 0.0, 0.02) == 0.0

    returns = pd.Series([0.01, 0.02, 0.03])
    assert sortino_ratio(returns, 0.0) == 0.0
