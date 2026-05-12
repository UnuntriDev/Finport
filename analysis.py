"""Quantitative finance routines for FinPort.

All functions are pure (no Streamlit, no I/O) so they can be unit-tested in
isolation. Annualization assumes 252 trading days.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

TRADING_DAYS = 252


def daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Simple daily returns. First row (NaN) is dropped."""
    return prices.pct_change().dropna(how="all")


def normalize_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """Rebase each price series so they all start at 100, for fair comparison."""
    return prices.divide(prices.iloc[0]).multiply(100.0)


def summary_per_asset(returns: pd.DataFrame) -> pd.DataFrame:
    """Mean daily return + annualized return and volatility, per asset."""
    mean_daily = returns.mean()
    annual_return = mean_daily * TRADING_DAYS
    annual_vol = returns.std() * np.sqrt(TRADING_DAYS)
    return pd.DataFrame(
        {
            "mean_daily": mean_daily,
            "annual_return": annual_return,
            "annual_vol": annual_vol,
        }
    )


def annualized_portfolio_metrics(
    returns: pd.DataFrame,
    weights: pd.Series,
) -> dict[str, float]:
    """Portfolio expected return and volatility (annualized).

    Return  = w^T * mu_annual
    Vol     = sqrt(w^T * Sigma_annual * w)

    where Sigma_annual = Sigma_daily * 252.
    """
    weights = weights.reindex(returns.columns).fillna(0.0)
    w = weights.values
    mean_daily = returns.mean().values
    cov_daily = returns.cov().values

    port_return = float(np.dot(w, mean_daily) * TRADING_DAYS)
    port_var = float(np.dot(w, np.dot(cov_daily * TRADING_DAYS, w)))
    port_vol = float(np.sqrt(max(port_var, 0.0)))
    return {"return": port_return, "volatility": port_vol}


def sharpe_ratio(
    annual_return: float,
    annual_volatility: float,
    risk_free_rate: float,
) -> float:
    """Standard Sharpe ratio. Returns 0 if volatility is zero (degenerate)."""
    if annual_volatility <= 0:
        return 0.0
    return (annual_return - risk_free_rate) / annual_volatility


def correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    return returns.corr()


def portfolio_value_series(
    prices: pd.DataFrame,
    weights: pd.Series,
    initial_value: float,
) -> pd.Series:
    """Track the value of a buy-and-hold portfolio over time.

    Capital is allocated according to ``weights`` at the first date and then
    held; daily portfolio value is the weighted sum of normalized prices.
    """
    weights = weights.reindex(prices.columns).fillna(0.0)
    normalized = prices.divide(prices.iloc[0])  # each series starts at 1.0
    value = normalized.multiply(weights.values, axis=1).sum(axis=1) * initial_value
    value.name = "portfolio_value"
    return value


def monte_carlo_simulation(
    returns: pd.DataFrame,
    weights: pd.Series,
    initial_value: float,
    horizon_days: int,
    n_simulations: int,
    seed: int | None = 42,
) -> pd.DataFrame:
    """Monte Carlo simulation of portfolio value over ``horizon_days``.

    Daily returns are drawn from a multivariate normal distribution with the
    historical mean vector and covariance matrix. Cross-asset correlations are
    preserved via Cholesky decomposition.

    Returns a DataFrame of shape (horizon_days + 1, n_simulations) where each
    column is one simulated portfolio value path starting at ``initial_value``.
    """
    weights = weights.reindex(returns.columns).fillna(0.0).values
    mean_daily = returns.mean().values
    cov_daily = returns.cov().values

    # Cholesky factor; fall back to a small ridge if matrix is not PD due to
    # numerical noise / collinear assets.
    try:
        chol = np.linalg.cholesky(cov_daily)
    except np.linalg.LinAlgError:
        eigvals, eigvecs = np.linalg.eigh(cov_daily)
        eigvals = np.clip(eigvals, 1e-10, None)
        cov_daily = (eigvecs * eigvals) @ eigvecs.T
        chol = np.linalg.cholesky(cov_daily)

    rng = np.random.default_rng(seed)
    n_assets = len(mean_daily)

    # Shape: (horizon_days, n_simulations, n_assets)
    z = rng.standard_normal(size=(horizon_days, n_simulations, n_assets))
    correlated = z @ chol.T + mean_daily  # broadcast mean across axes
    portfolio_daily = correlated @ weights  # (horizon_days, n_simulations)

    # Compound to a value path that starts at initial_value
    growth = np.cumprod(1.0 + portfolio_daily, axis=0)
    paths = np.vstack([np.ones((1, n_simulations)), growth]) * initial_value

    return pd.DataFrame(paths, columns=[f"sim_{i}" for i in range(n_simulations)])


# ============================================================================
# Advanced risk metrics
# ============================================================================

def max_drawdown(value_series: pd.Series) -> dict:
    """Maximum drawdown analysis.

    Drawdown is the percentage decline from a running peak. The "underwater"
    series tracks how far below the all-time-high the portfolio is at each
    moment. We also report peak/trough/recovery dates.
    """
    cummax = value_series.cummax()
    drawdown = (value_series - cummax) / cummax  # negative or 0
    max_dd = float(drawdown.min())
    trough_date = drawdown.idxmin()
    peak_date = value_series.loc[:trough_date].idxmax()

    # First date after the trough where the portfolio returns to the prior peak
    peak_level = float(cummax.loc[trough_date])
    after_trough = value_series.loc[trough_date:]
    recovered = after_trough[after_trough >= peak_level]
    recovery_date = recovered.index[0] if len(recovered) > 0 else None

    duration_days = (trough_date - peak_date).days
    recovery_days = (recovery_date - trough_date).days if recovery_date else None

    return {
        "max_drawdown": max_dd,
        "drawdown_series": drawdown,
        "peak_date": peak_date,
        "trough_date": trough_date,
        "recovery_date": recovery_date,
        "drawdown_days": duration_days,
        "recovery_days": recovery_days,
    }


def sortino_ratio(
    daily_returns_series: pd.Series,
    risk_free_rate: float = 0.0,
) -> float:
    """Sortino ratio — like Sharpe but uses only downside deviation.

    Downside deviation considers only returns below a threshold (here 0).
    This makes more economic sense: upward volatility is not "risk".
    """
    rf_daily = risk_free_rate / TRADING_DAYS
    excess = daily_returns_series - rf_daily
    downside = excess[excess < 0]
    if len(downside) == 0:
        return 0.0
    downside_std_annual = downside.std() * np.sqrt(TRADING_DAYS)
    if downside_std_annual <= 0:
        return 0.0
    annual_excess = excess.mean() * TRADING_DAYS
    return float(annual_excess / downside_std_annual)


# ============================================================================
# Portfolio optimization (Markowitz)
# ============================================================================

def _portfolio_perf(weights: np.ndarray, mean_annual: np.ndarray, cov_annual: np.ndarray):
    ret = float(np.dot(weights, mean_annual))
    vol = float(np.sqrt(max(np.dot(weights, np.dot(cov_annual, weights)), 0.0)))
    return ret, vol


def _clean_optimizer_weights(result, columns: pd.Index) -> pd.Series:
    """Normalize SLSQP output and fall back to equal weights on failure."""
    n = len(columns)
    if not getattr(result, "success", False):
        return pd.Series(np.ones(n) / n, index=columns)

    weights = np.asarray(result.x, dtype=float)
    if weights.shape != (n,) or not np.all(np.isfinite(weights)):
        return pd.Series(np.ones(n) / n, index=columns)

    weights = np.clip(weights, 0.0, 1.0)
    total = weights.sum()
    if total <= 0:
        weights = np.ones(n) / n
    else:
        weights = weights / total
    return pd.Series(weights, index=columns)


def optimize_max_sharpe(
    returns: pd.DataFrame,
    risk_free_rate: float = 0.02,
) -> pd.Series:
    """Find weights that maximize the Sharpe ratio (tangency portfolio).

    Long-only constraint: 0 <= w_i <= 1, sum(w) = 1.
    """
    n = returns.shape[1]
    mean_annual = returns.mean().values * TRADING_DAYS
    cov_annual = returns.cov().values * TRADING_DAYS

    def neg_sharpe(w):
        ret, vol = _portfolio_perf(w, mean_annual, cov_annual)
        if vol <= 0:
            return 1e10
        return -(ret - risk_free_rate) / vol

    constraints = ({"type": "eq", "fun": lambda w: np.sum(w) - 1.0},)
    bounds = tuple((0.0, 1.0) for _ in range(n))
    w0 = np.ones(n) / n

    result = minimize(
        neg_sharpe,
        w0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
    )
    return _clean_optimizer_weights(result, returns.columns)


def optimize_min_variance(returns: pd.DataFrame) -> pd.Series:
    """Find weights that minimize portfolio variance (long-only)."""
    n = returns.shape[1]
    cov_annual = returns.cov().values * TRADING_DAYS

    def variance(w):
        return float(np.dot(w, np.dot(cov_annual, w)))

    constraints = ({"type": "eq", "fun": lambda w: np.sum(w) - 1.0},)
    bounds = tuple((0.0, 1.0) for _ in range(n))
    w0 = np.ones(n) / n

    result = minimize(
        variance,
        w0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
    )
    return _clean_optimizer_weights(result, returns.columns)


def efficient_frontier(
    returns: pd.DataFrame,
    n_points: int = 40,
) -> pd.DataFrame:
    """Compute the Markowitz efficient frontier.

    For each target return level, finds the portfolio with minimum variance
    that achieves that return. Returns a DataFrame with columns
    'return' and 'volatility' (annualized).
    """
    n = returns.shape[1]
    mean_annual = returns.mean().values * TRADING_DAYS
    cov_annual = returns.cov().values * TRADING_DAYS

    target_returns = np.linspace(mean_annual.min(), mean_annual.max(), n_points)

    bounds = tuple((0.0, 1.0) for _ in range(n))
    w0 = np.ones(n) / n

    points = []
    for target in target_returns:
        constraints = (
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "eq", "fun": lambda w, t=target: float(np.dot(w, mean_annual)) - t},
        )
        result = minimize(
            lambda w: float(np.dot(w, np.dot(cov_annual, w))),
            w0, method="SLSQP", bounds=bounds, constraints=constraints,
        )
        if result.success:
            vol = float(np.sqrt(max(result.fun, 0.0)))
            points.append({"return": float(target), "volatility": vol})

    return pd.DataFrame(points)


# ============================================================================
# CAPM: Beta, Alpha vs market
# ============================================================================

def compute_beta_alpha(
    portfolio_returns: pd.Series,
    market_returns: pd.Series,
    risk_free_rate: float = 0.02,
) -> dict[str, float]:
    """CAPM regression: portfolio_excess_return = alpha + beta * market_excess_return.

    - Beta measures sensitivity to market moves. Beta > 1: more volatile
      than market; Beta < 1: less volatile; Beta < 0: moves opposite.
    - Alpha (annualized) is the portion of return not explained by market
      exposure. Positive alpha = portfolio beats market on a risk-adjusted basis.
    - R-squared shows what fraction of portfolio variance is explained by
      market moves.
    """
    aligned = pd.concat(
        [portfolio_returns.rename("p"), market_returns.rename("m")],
        axis=1,
    ).dropna()
    if len(aligned) < 30:
        return {"beta": 0.0, "alpha": 0.0, "r_squared": 0.0, "correlation": 0.0}

    rf_daily = risk_free_rate / TRADING_DAYS
    excess_p = aligned["p"] - rf_daily
    excess_m = aligned["m"] - rf_daily

    market_var = float(np.var(excess_m, ddof=1))
    if market_var <= 0:
        return {"beta": 0.0, "alpha": 0.0, "r_squared": 0.0, "correlation": 0.0}

    cov_pm = float(np.cov(excess_p, excess_m, ddof=1)[0, 1])
    beta = cov_pm / market_var

    alpha_daily = float(excess_p.mean()) - beta * float(excess_m.mean())
    alpha_annual = alpha_daily * TRADING_DAYS

    corr = float(np.corrcoef(aligned["p"], aligned["m"])[0, 1])
    r_squared = corr ** 2

    return {
        "beta": float(beta),
        "alpha": float(alpha_annual),
        "r_squared": float(r_squared),
        "correlation": float(corr),
    }


def portfolio_daily_returns(
    returns: pd.DataFrame,
    weights: pd.Series,
) -> pd.Series:
    """Compute the daily return series of a buy-and-hold portfolio."""
    weights = weights.reindex(returns.columns).fillna(0.0)
    return returns.dot(weights.values)
