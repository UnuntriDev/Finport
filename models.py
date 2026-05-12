"""Shared data models for FinPort."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass(frozen=True)
class PortfolioAnalysisRequest:
    tickers: list[str]
    weights_pct: dict[str, float]
    start_date: date
    end_date: date
    initial_investment: float
    risk_free_rate: float
    mc_horizon_days: int
    mc_simulations: int
    mc_method_label: str
    benchmark_ticker: str = "^GSPC"
    use_demo_data: bool = False


@dataclass(frozen=True)
class PortfolioAnalysisResult:
    prices: pd.DataFrame
    failed: dict[str, str]
    weights: pd.Series
    returns: pd.DataFrame
    normalized_prices: pd.DataFrame
    asset_stats: pd.DataFrame
    portfolio_metrics: dict[str, float]
    portfolio_sharpe: float
    correlation: pd.DataFrame
    portfolio_value: pd.Series
    portfolio_cagr: float
    equal_weights: pd.Series
    equal_weight_metrics: dict[str, float]
    equal_weight_sharpe: float
    equal_weight_value: pd.Series
    portfolio_daily_returns: pd.Series
    drawdown_info: dict
    sortino: float
    max_sharpe_weights: pd.Series
    min_variance_weights: pd.Series
    max_sharpe_metrics: dict[str, float]
    min_variance_metrics: dict[str, float]
    max_sharpe_ratio: float
    min_variance_sharpe: float
    efficient_frontier: pd.DataFrame
    market_returns: pd.Series
    market_value: pd.Series
    capm: dict[str, float]
    market_loaded: bool
    simulations: pd.DataFrame
    mc_p5: float
    mc_p50: float
    mc_p95: float
    var_95: float
    data_source: str
