"""Shared data models for FinPort."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

import pandas as pd

from constants import MIN_PERIOD_DAYS


class MonteCarloMethod(StrEnum):
    """Identifiers for supported Monte Carlo simulation methods."""

    PARAMETRIC = "Parametric normal"
    BOOTSTRAP = "Historical bootstrap"

    @property
    def key(self) -> str:
        """Internal key used by `analysis.monte_carlo_simulation`."""
        return "bootstrap" if self is MonteCarloMethod.BOOTSTRAP else "parametric"

    @classmethod
    def from_label(cls, label: str) -> MonteCarloMethod:
        for member in cls:
            if member.value == label:
                return member
        return cls.PARAMETRIC


class ValidationError(ValueError):
    """Raised when an analysis request cannot be served."""


BENCHMARK_TICKER = "^GSPC"


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
    benchmark_ticker: str = BENCHMARK_TICKER
    use_demo_data: bool = False

    @property
    def mc_method(self) -> MonteCarloMethod:
        return MonteCarloMethod.from_label(self.mc_method_label)


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


@dataclass(frozen=True)
class ViewContext:
    start_date: date
    end_date: date
    initial_investment: float
    risk_free_rate: float
    mc_horizon_days: int
    mc_method_label: str
    demo_mode: bool = False

    @property
    def mc_method(self) -> str:
        return MonteCarloMethod.from_label(self.mc_method_label).key


def validate_request(request: PortfolioAnalysisRequest) -> None:
    """Validate an analysis request; raise ValidationError with a user message."""
    if request.start_date is None or request.end_date is None:
        raise ValidationError("Select a start and end date in the sidebar.")
    if request.initial_investment <= 0:
        raise ValidationError("Enter an initial investment amount greater than $0.")
    if request.start_date >= request.end_date:
        raise ValidationError("Start date must be earlier than end date.")

    period_days = (request.end_date - request.start_date).days
    if period_days < MIN_PERIOD_DAYS:
        raise ValidationError(
            f"Analysis period is only {period_days} days. Choose at least "
            f"{MIN_PERIOD_DAYS} days so that the covariance matrix, Markowitz "
            "optimization and Monte Carlo simulation have enough data to "
            "produce meaningful results."
        )
    if len(request.tickers) < 2:
        raise ValidationError(
            "Select at least two tickers for a meaningful portfolio analysis."
        )
