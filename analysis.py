"""Pure quantitative finance routines. Annualization uses 252 trading days."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

TRADING_DAYS = 252


def daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.pct_change().dropna(how="all")


def normalize_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """Rebase each price series to start at 100."""
    return prices.divide(prices.iloc[0]).multiply(100.0)


def summary_per_asset(returns: pd.DataFrame) -> pd.DataFrame:
    mean_daily = returns.mean()
    return pd.DataFrame(
        {
            "mean_daily": mean_daily,
            "annual_return": mean_daily * TRADING_DAYS,
            "annual_vol": returns.std() * np.sqrt(TRADING_DAYS),
        }
    )


def annualized_portfolio_metrics(
    returns: pd.DataFrame,
    weights: pd.Series,
) -> dict[str, float]:
    """Annualized expected return and volatility:
        ret = w · μ_annual
        vol = sqrt(w · Σ_annual · w)
    """
    weights = weights.reindex(returns.columns).fillna(0.0)
    w = weights.values
    mean_daily = returns.mean().values
    cov_daily = returns.cov().values

    port_return = float(np.dot(w, mean_daily) * TRADING_DAYS)
    port_var = float(np.dot(w, np.dot(cov_daily * TRADING_DAYS, w)))
    return {"return": port_return, "volatility": float(np.sqrt(max(port_var, 0.0)))}


def sharpe_ratio(
    annual_return: float,
    annual_volatility: float,
    risk_free_rate: float,
) -> float:
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
    """Buy-and-hold portfolio value over time."""
    weights = weights.reindex(prices.columns).fillna(0.0)
    normalized = prices.divide(prices.iloc[0])
    value = normalized.multiply(weights.values, axis=1).sum(axis=1) * initial_value
    value.name = "portfolio_value"
    return value


def cagr(value_series: pd.Series, trading_days: int = TRADING_DAYS) -> float:
    clean = value_series.dropna()
    if len(clean) < 2:
        return 0.0
    start = float(clean.iloc[0])
    end = float(clean.iloc[-1])
    if start <= 0 or end <= 0:
        return 0.0
    years = (len(clean) - 1) / trading_days
    if years <= 0:
        return 0.0
    return float((end / start) ** (1.0 / years) - 1.0)


def monte_carlo_simulation(
    returns: pd.DataFrame,
    weights: pd.Series,
    initial_value: float,
    horizon_days: int,
    n_simulations: int,
    method: str = "parametric",
    seed: int | None = 42,
) -> pd.DataFrame:
    """Simulate portfolio value paths.

    ``parametric`` draws from multivariate normal (historical μ, Σ).
    ``bootstrap`` resamples historical return rows with replacement.
    Returns shape (horizon_days + 1, n_simulations).
    """
    weights_array = weights.reindex(returns.columns).fillna(0.0).values
    rng = np.random.default_rng(seed)

    if method not in {"parametric", "bootstrap"}:
        raise ValueError("method must be either 'parametric' or 'bootstrap'")

    if method == "bootstrap":
        sampled_idx = rng.integers(0, len(returns), size=(horizon_days, n_simulations))
        portfolio_daily = returns.to_numpy()[sampled_idx] @ weights_array
        return _compound_simulated_returns(portfolio_daily, initial_value, n_simulations)

    mean_daily = returns.mean().values
    cov_daily = returns.cov().values

    # Ridge regularization for non-PD covariance (numerical noise / collinearity)
    try:
        chol = np.linalg.cholesky(cov_daily)
    except np.linalg.LinAlgError:
        eigvals, eigvecs = np.linalg.eigh(cov_daily)
        eigvals = np.clip(eigvals, 1e-10, None)
        cov_daily = (eigvecs * eigvals) @ eigvecs.T
        chol = np.linalg.cholesky(cov_daily)

    z = rng.standard_normal(size=(horizon_days, n_simulations, len(mean_daily)))
    correlated = z @ chol.T + mean_daily
    portfolio_daily = correlated @ weights_array

    return _compound_simulated_returns(portfolio_daily, initial_value, n_simulations)


def _compound_simulated_returns(
    portfolio_daily: np.ndarray,
    initial_value: float,
    n_simulations: int,
) -> pd.DataFrame:
    growth = np.cumprod(1.0 + portfolio_daily, axis=0)
    paths = np.vstack([np.ones((1, n_simulations)), growth]) * initial_value
    return pd.DataFrame(paths, columns=[f"sim_{i}" for i in range(n_simulations)])


def max_drawdown(value_series: pd.Series) -> dict:
    """Largest peak-to-trough decline plus peak/trough/recovery dates."""
    cummax = value_series.cummax()
    drawdown = (value_series - cummax) / cummax
    max_dd = float(drawdown.min())
    trough_date = drawdown.idxmin()
    peak_date = value_series.loc[:trough_date].idxmax()

    peak_level = float(cummax.loc[trough_date])
    after_trough = value_series.loc[trough_date:]
    recovered = after_trough[after_trough >= peak_level]
    recovery_date = recovered.index[0] if len(recovered) > 0 else None

    return {
        "max_drawdown": max_dd,
        "drawdown_series": drawdown,
        "peak_date": peak_date,
        "trough_date": trough_date,
        "recovery_date": recovery_date,
        "drawdown_days": (trough_date - peak_date).days,
        "recovery_days": (recovery_date - trough_date).days if recovery_date else None,
    }


def sortino_ratio(
    daily_returns_series: pd.Series,
    risk_free_rate: float = 0.0,
) -> float:
    """Like Sharpe but only penalizes downside deviation."""
    rf_daily = risk_free_rate / TRADING_DAYS
    excess = daily_returns_series - rf_daily
    downside = excess[excess < 0]
    if len(downside) == 0:
        return 0.0
    downside_std_annual = downside.std() * np.sqrt(TRADING_DAYS)
    if downside_std_annual <= 0:
        return 0.0
    return float(excess.mean() * TRADING_DAYS / downside_std_annual)


def _portfolio_perf(
    weights: np.ndarray,
    mean_annual: np.ndarray,
    cov_annual: np.ndarray,
) -> tuple[float, float]:
    ret = float(np.dot(weights, mean_annual))
    vol = float(np.sqrt(max(np.dot(weights, np.dot(cov_annual, weights)), 0.0)))
    return ret, vol


def _clean_optimizer_weights(result, columns: pd.Index) -> pd.Series:
    """Normalize SLSQP output, fall back to equal weights on failure."""
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
    """Tangency portfolio (max Sharpe), long-only, fully invested."""
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
    result = minimize(
        neg_sharpe, np.ones(n) / n,
        method="SLSQP", bounds=bounds, constraints=constraints,
    )
    return _clean_optimizer_weights(result, returns.columns)


def optimize_min_variance(returns: pd.DataFrame) -> pd.Series:
    """Long-only minimum-variance portfolio."""
    n = returns.shape[1]
    cov_annual = returns.cov().values * TRADING_DAYS

    constraints = ({"type": "eq", "fun": lambda w: np.sum(w) - 1.0},)
    bounds = tuple((0.0, 1.0) for _ in range(n))
    result = minimize(
        lambda w: float(np.dot(w, np.dot(cov_annual, w))),
        np.ones(n) / n,
        method="SLSQP", bounds=bounds, constraints=constraints,
    )
    return _clean_optimizer_weights(result, returns.columns)


def efficient_frontier(
    returns: pd.DataFrame,
    n_points: int = 40,
) -> pd.DataFrame:
    """Min-variance portfolio for each target return on a linear grid."""
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
            points.append({
                "return": float(target),
                "volatility": float(np.sqrt(max(result.fun, 0.0))),
            })

    return pd.DataFrame(points)


def compute_beta_alpha(
    portfolio_returns: pd.Series,
    market_returns: pd.Series,
    risk_free_rate: float = 0.02,
) -> dict[str, float]:
    """CAPM regression: excess_p = alpha + beta · excess_m. Returns zeros if
    fewer than 30 aligned observations or market variance is degenerate.
    """
    aligned = pd.concat(
        [portfolio_returns.rename("p"), market_returns.rename("m")],
        axis=1,
    ).dropna()
    zeros = {"beta": 0.0, "alpha": 0.0, "r_squared": 0.0, "correlation": 0.0}
    if len(aligned) < 30:
        return zeros

    rf_daily = risk_free_rate / TRADING_DAYS
    excess_p = aligned["p"] - rf_daily
    excess_m = aligned["m"] - rf_daily

    market_var = float(np.var(excess_m, ddof=1))
    if market_var <= 0:
        return zeros

    cov_pm = float(np.cov(excess_p, excess_m, ddof=1)[0, 1])
    beta = cov_pm / market_var
    alpha_annual = (float(excess_p.mean()) - beta * float(excess_m.mean())) * TRADING_DAYS
    corr = float(np.corrcoef(aligned["p"], aligned["m"])[0, 1])

    return {
        "beta": float(beta),
        "alpha": float(alpha_annual),
        "r_squared": float(corr ** 2),
        "correlation": float(corr),
    }


def portfolio_daily_returns(
    returns: pd.DataFrame,
    weights: pd.Series,
) -> pd.Series:
    weights = weights.reindex(returns.columns).fillna(0.0)
    return returns.dot(weights.values)
