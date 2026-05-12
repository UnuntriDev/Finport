"""End-to-end portfolio analysis orchestration."""
from __future__ import annotations

import numpy as np
import pandas as pd

from analysis import (
    annualized_portfolio_metrics,
    cagr,
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
from constants import MIN_TRADING_ROWS
from data_loader import load_price_data
from demo_data import load_demo_price_data
from models import PortfolioAnalysisRequest, PortfolioAnalysisResult


class PortfolioAnalysisError(RuntimeError):
    """Raised when the portfolio analysis cannot produce a valid result."""

    def __init__(self, message: str, failed: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.failed = failed or {}


def run_portfolio_analysis(
    request: PortfolioAnalysisRequest,
) -> PortfolioAnalysisResult:
    """Run the complete FinPort analytics pipeline."""
    prices, failed = _load_prices(
        request,
        request.tickers,
    )
    if prices.empty or prices.shape[1] < 2:
        raise PortfolioAnalysisError(
            "Not enough valid price data. Try different tickers or a wider date range.",
            failed=failed,
        )

    if len(prices) < MIN_TRADING_ROWS:
        raise PortfolioAnalysisError(
            f"Only {len(prices)} trading days of overlapping data available "
            f"across all selected tickers (need at least {MIN_TRADING_ROWS}). "
            "Widen the date range or pick assets with more shared history.",
            failed=failed,
        )

    weights = _surviving_weights(request.weights_pct, prices.columns)
    returns = daily_returns(prices)
    normalized = normalize_prices(prices)
    asset_stats = summary_per_asset(returns)

    portfolio_metrics = annualized_portfolio_metrics(returns, weights)
    portfolio_sharpe = sharpe_ratio(
        portfolio_metrics["return"],
        portfolio_metrics["volatility"],
        request.risk_free_rate,
    )
    correlation = correlation_matrix(returns)
    portfolio_value = portfolio_value_series(
        prices,
        weights,
        request.initial_investment,
    )
    portfolio_cagr = cagr(portfolio_value)

    equal_weights = pd.Series(1.0 / len(prices.columns), index=prices.columns)
    equal_weight_metrics = annualized_portfolio_metrics(returns, equal_weights)
    equal_weight_sharpe = sharpe_ratio(
        equal_weight_metrics["return"],
        equal_weight_metrics["volatility"],
        request.risk_free_rate,
    )
    equal_weight_value = portfolio_value_series(
        prices,
        equal_weights,
        request.initial_investment,
    )

    port_daily_returns = portfolio_daily_returns(returns, weights)
    drawdown_info = max_drawdown(portfolio_value)
    sortino = sortino_ratio(port_daily_returns, request.risk_free_rate)

    max_sharpe_weights = optimize_max_sharpe(returns, request.risk_free_rate)
    min_variance_weights = optimize_min_variance(returns)
    max_sharpe_metrics = annualized_portfolio_metrics(returns, max_sharpe_weights)
    min_variance_metrics = annualized_portfolio_metrics(returns, min_variance_weights)
    max_sharpe_ratio = sharpe_ratio(
        max_sharpe_metrics["return"],
        max_sharpe_metrics["volatility"],
        request.risk_free_rate,
    )
    min_variance_sharpe = sharpe_ratio(
        min_variance_metrics["return"],
        min_variance_metrics["volatility"],
        request.risk_free_rate,
    )
    frontier = efficient_frontier(returns, n_points=40)

    market_returns, market_value, capm, market_loaded = _market_benchmark(
        request,
        port_daily_returns,
    )

    simulations = monte_carlo_simulation(
        returns=returns,
        weights=weights,
        initial_value=request.initial_investment,
        horizon_days=request.mc_horizon_days,
        n_simulations=request.mc_simulations,
        method=request.mc_method.key,
    )
    final_mc = simulations.iloc[-1]
    mc_p5, mc_p50, mc_p95 = np.percentile(final_mc, [5, 50, 95])
    var_95 = request.initial_investment - mc_p5

    return PortfolioAnalysisResult(
        prices=prices,
        failed=failed,
        weights=weights,
        returns=returns,
        normalized_prices=normalized,
        asset_stats=asset_stats,
        portfolio_metrics=portfolio_metrics,
        portfolio_sharpe=portfolio_sharpe,
        correlation=correlation,
        portfolio_value=portfolio_value,
        portfolio_cagr=portfolio_cagr,
        equal_weights=equal_weights,
        equal_weight_metrics=equal_weight_metrics,
        equal_weight_sharpe=equal_weight_sharpe,
        equal_weight_value=equal_weight_value,
        portfolio_daily_returns=port_daily_returns,
        drawdown_info=drawdown_info,
        sortino=sortino,
        max_sharpe_weights=max_sharpe_weights,
        min_variance_weights=min_variance_weights,
        max_sharpe_metrics=max_sharpe_metrics,
        min_variance_metrics=min_variance_metrics,
        max_sharpe_ratio=max_sharpe_ratio,
        min_variance_sharpe=min_variance_sharpe,
        efficient_frontier=frontier,
        market_returns=market_returns,
        market_value=market_value,
        capm=capm,
        market_loaded=market_loaded,
        simulations=simulations,
        mc_p5=float(mc_p5),
        mc_p50=float(mc_p50),
        mc_p95=float(mc_p95),
        var_95=float(var_95),
        data_source="Demo data" if request.use_demo_data else "Yahoo Finance",
    )


def _surviving_weights(
    weights_pct: dict[str, float],
    price_columns: pd.Index,
) -> pd.Series:
    weights = pd.Series(weights_pct, dtype=float) / 100.0
    weights = weights.reindex(price_columns).dropna()
    if weights.sum() == 0:
        raise PortfolioAnalysisError("All weights for valid tickers are zero.")
    return weights / weights.sum()


def _market_benchmark(
    request: PortfolioAnalysisRequest,
    port_daily_returns: pd.Series,
) -> tuple[pd.Series, pd.Series, dict[str, float], bool]:
    market_prices, _ = _load_prices(
        request,
        [request.benchmark_ticker],
    )
    if market_prices.empty:
        return (
            pd.Series(dtype=float),
            pd.Series(dtype=float),
            {"beta": 0.0, "alpha": 0.0, "r_squared": 0.0, "correlation": 0.0},
            False,
        )

    market_returns = daily_returns(market_prices).iloc[:, 0]
    market_value = portfolio_value_series(
        market_prices,
        pd.Series([1.0], index=market_prices.columns),
        request.initial_investment,
    )
    capm = compute_beta_alpha(
        port_daily_returns,
        market_returns,
        request.risk_free_rate,
    )
    return market_returns, market_value, capm, True


def _load_prices(
    request: PortfolioAnalysisRequest,
    tickers: list[str],
) -> tuple[pd.DataFrame, dict[str, str]]:
    if request.use_demo_data:
        return load_demo_price_data(tickers, request.start_date, request.end_date)
    return load_price_data(tickers, request.start_date, request.end_date)
