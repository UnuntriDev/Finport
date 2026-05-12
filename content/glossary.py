"""Financial glossary content shown in the app."""

GLOSSARY_TERMS = [
    (
        "📈 Annualized Return",
        "Average daily return × 252 trading days. Represents the expected "
        "yearly gain of an asset or portfolio assuming continuation of "
        "historical patterns. Formula: μ_daily × 252.",
    ),
    (
        "⚡ Annualized Volatility",
        "Standard deviation of daily returns × √252. Measures the dispersion "
        "of returns around the mean — the higher the value, the more "
        "uncertain (risky) the future outcome. Formula: σ_daily × √252.",
    ),
    (
        "🎯 Sharpe Ratio (Sharpe, 1966)",
        "Risk-adjusted return: (Return − Risk-free rate) / Volatility. "
        "Tells you how much excess return you earn per unit of risk taken. "
        "> 1.0 is considered good, > 2.0 excellent. Below 0.5 means low "
        "compensation for risk.",
    ),
    (
        "🎯 Sortino Ratio (Sortino & Price, 1994)",
        "Like Sharpe ratio, but only penalizes **downside** volatility "
        "(returns below 0). More realistic for investors — upward swings "
        "are not 'risk'. Formula: (Return − Rf) / Downside deviation.",
    ),
    (
        "📉 Maximum Drawdown",
        "The largest peak-to-trough decline in portfolio value over a "
        "given period. Critical risk metric — shows the worst loss an "
        "investor would have actually experienced. Often paired with "
        "drawdown **duration** (time underwater) and **recovery time**.",
    ),
    (
        "📐 Beta (β)",
        "Sensitivity to market moves (CAPM). β = 1 means the asset moves "
        "1-to-1 with the market. β > 1 amplifies market moves (aggressive). "
        "β < 1 dampens them (defensive). β < 0 means inverse correlation. "
        "Calculated as: Cov(asset, market) / Var(market).",
    ),
    (
        "✨ Alpha (α)",
        "CAPM alpha — annualized excess return that cannot be explained "
        "by beta exposure to the market. Positive α means the portfolio "
        "beats the risk-adjusted market expectation. Considered the "
        "holy grail of active management; persistently positive α is rare.",
    ),
    (
        "🔗 Correlation",
        "Pearson correlation coefficient (−1 to +1) measuring co-movement "
        "between two return series. +1 = perfect lockstep (no diversification), "
        "0 = independent, −1 = perfect hedge. Low/negative correlations "
        "between portfolio components reduce overall risk.",
    ),
    (
        "📊 R² (R-squared)",
        "Proportion of portfolio variance explained by market moves. High "
        "R² (> 0.7) means the portfolio behaves mostly like the market — "
        "diversification benefit vs market is limited.",
    ),
    (
        "🛡 Value at Risk (VaR)",
        "Maximum expected loss over a given time horizon at a given "
        "confidence level. VaR 95% = the loss that won't be exceeded in "
        "95% of scenarios. Widely used in banking but criticized for "
        "ignoring 'tail' losses beyond the threshold.",
    ),
    (
        "🛡 Conditional VaR (CVaR / Expected Shortfall)",
        "Average loss in the **worst** (1 − α)% of cases — e.g., the "
        "average of the worst 5% Monte Carlo outcomes. CVaR is preferred "
        "over VaR under Basel III banking regulations because it accounts "
        "for tail risk.",
    ),
    (
        "🎲 Monte Carlo Simulation",
        "Generates thousands of possible future paths by repeatedly sampling "
        "from a statistical distribution (here: multivariate normal with "
        "historical mean and covariance). Cross-asset correlations are "
        "preserved via Cholesky decomposition. The distribution of final "
        "outcomes shows the range of plausible scenarios.",
    ),
    (
        "📐 Efficient Frontier (Markowitz, 1952)",
        "The set of optimal portfolios offering the highest expected return "
        "for each level of risk (volatility). Foundation of Modern Portfolio "
        "Theory. Any portfolio below the frontier is sub-optimal: there "
        "exists another portfolio with either more return for the same risk "
        "or less risk for the same return.",
    ),
    (
        "🎯 Max Sharpe Portfolio (Tangency Portfolio)",
        "The portfolio on the efficient frontier with the highest "
        "Sharpe ratio. In CAPM theory, this is the **tangency portfolio** — "
        "where the Capital Market Line touches the efficient frontier. "
        "Theoretically the optimal risky portfolio for any investor.",
    ),
    (
        "🛡 Minimum Variance Portfolio",
        "The leftmost point of the efficient frontier — the portfolio with "
        "the lowest possible volatility regardless of expected return. "
        "Useful for risk-averse investors prioritizing capital preservation.",
    ),
    (
        "📐 CAPM (Sharpe, 1964)",
        "Capital Asset Pricing Model: an asset's expected return equals "
        "Rf + β · (Rm − Rf), where Rf is risk-free rate, Rm is market "
        "return. Foundation of modern asset pricing — Sharpe won the "
        "Nobel Prize in 1990 for this work.",
    ),
    (
        "🏛 Risk-free Rate",
        "Theoretical return of a zero-risk investment, used as a baseline "
        "in Sharpe ratio, CAPM, and other models. Typically approximated "
        "by short-term government bond yields (e.g. 3-month T-bills in "
        "the U.S.).",
    ),
    (
        "⚖ Portfolio Weights",
        "Proportion of total capital allocated to each asset. Must sum to "
        "1 (or 100%). In a buy-and-hold portfolio, weights drift over "
        "time as assets perform differently — periodic **rebalancing** "
        "restores the target allocation.",
    ),
    (
        "🔄 Buy-and-Hold",
        "Investment strategy where assets are bought once at the start "
        "and held without modifications. Implicit in FinPort's portfolio "
        "value calculation. Alternative: periodic rebalancing back to "
        "target weights.",
    ),
    (
        "📊 252 Trading Days",
        "The conventional number of trading days per year (≈ 365 minus "
        "weekends and major holidays). Used to annualize daily statistics: "
        "annual_return = daily_return × 252, "
        "annual_volatility = daily_volatility × √252.",
    ),
]

GLOSSARY_SOURCES = (
    "**Sources:** Markowitz (1952) 'Portfolio Selection', Sharpe (1964) "
    "'Capital Asset Prices', Sortino & Price (1994) 'Performance Measurement "
    "in a Downside Risk Framework', Basel Committee on Banking Supervision "
    "(2019) 'Minimum Capital Requirements for Market Risk'."
)
