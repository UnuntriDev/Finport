"""Property-based tests for the pure portfolio_state helpers.

These tests use hypothesis to verify algebraic invariants that must hold for
ANY ticker list, weight dict and lock combination — not just the few cases
hard-coded in test_portfolio_state.py.

Invariants checked:
    1. ``redistribute_equal_locked`` and ``rebalance_after_weight_change`` both
       always sum to (approximately) 100% — within a tiny rounding tolerance.
    2. Locked weights are never modified by either function.
    3. No weight ever becomes negative.
    4. All input tickers appear in the output.
"""
from __future__ import annotations

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from portfolio_state import rebalance_after_weight_change, redistribute_equal_locked

# Acceptable rounding tolerance — each weight is rounded to 2 decimal places,
# so cumulative drift is bounded by 0.5% even for ~12 tickers.
_TOLERANCE_PCT = 0.5

# A realistic ticker name (uppercase + digits). Length 1–6 is enough for tests
# while still triggering rare 12-ticker portfolios.
_TICKER_STRATEGY = st.text(
    alphabet=st.characters(min_codepoint=ord("A"), max_codepoint=ord("Z")),
    min_size=1,
    max_size=6,
)

# Weight values up to 100. Allow zeros (boundary case).
_WEIGHT_STRATEGY = st.floats(
    min_value=0.0,
    max_value=100.0,
    allow_nan=False,
    allow_infinity=False,
)


@st.composite
def portfolios(draw, min_tickers: int = 2, max_tickers: int = 12):
    """Generate (tickers, weights, locks) triplets."""
    tickers = draw(
        st.lists(
            _TICKER_STRATEGY,
            min_size=min_tickers,
            max_size=max_tickers,
            unique=True,
        )
    )
    weights = {t: draw(_WEIGHT_STRATEGY) for t in tickers}
    locks = {t: draw(st.booleans()) for t in tickers}
    return tickers, weights, locks


# ---------------------------------------------------------------------------
# redistribute_equal_locked
# ---------------------------------------------------------------------------

@given(portfolio=portfolios())
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_redistribute_equal_locked_sums_to_100_when_locked_within_budget(portfolio):
    """With a feasible locked allocation, the total reaches 100% exactly."""
    tickers, weights, locks = portfolio
    assume(any(not locks[t] for t in tickers))
    locked_sum = sum(
        max(0.0, weights[t]) for t in tickers if locks[t]
    )
    assume(locked_sum <= 100.0)  # feasible budget

    result = redistribute_equal_locked(tickers, weights, locks)
    total = sum(result.values())
    assert abs(total - 100.0) <= _TOLERANCE_PCT


@given(portfolio=portfolios())
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_redistribute_equal_locked_preserves_locked_weights(portfolio):
    tickers, weights, locks = portfolio

    result = redistribute_equal_locked(tickers, weights, locks)
    for ticker in tickers:
        if locks[ticker]:
            expected = max(0.0, float(weights[ticker]))
            assert result[ticker] == expected


@given(portfolio=portfolios())
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_redistribute_equal_locked_no_negative_weights(portfolio):
    tickers, weights, locks = portfolio

    result = redistribute_equal_locked(tickers, weights, locks)
    assert all(value >= 0.0 for value in result.values())


@given(portfolio=portfolios())
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_redistribute_equal_locked_keeps_all_tickers(portfolio):
    tickers, weights, locks = portfolio

    result = redistribute_equal_locked(tickers, weights, locks)
    assert set(result) == set(tickers)


# ---------------------------------------------------------------------------
# rebalance_after_weight_change
# ---------------------------------------------------------------------------

@given(portfolio=portfolios(min_tickers=2))
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_rebalance_after_change_sums_to_100_when_feasible(portfolio):
    """Total reaches 100% when there is at least one other unlocked ticker
    to absorb the residual budget.
    """
    tickers, weights, locks = portfolio
    changed = tickers[0]
    assume(not locks[changed])  # the edited ticker must be unlocked
    other_unlocked = [t for t in tickers if t != changed and not locks[t]]
    assume(other_unlocked)       # at least one other unlocked ticker
    locked_sum = sum(
        max(0.0, weights[t]) for t in tickers if locks[t]
    )
    assume(locked_sum <= 100.0)  # feasible budget

    result = rebalance_after_weight_change(tickers, weights, locks, changed)
    total = sum(result.values())
    assert abs(total - 100.0) <= _TOLERANCE_PCT


@given(portfolio=portfolios(min_tickers=2))
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_rebalance_after_change_preserves_locked_weights(portfolio):
    tickers, weights, locks = portfolio
    changed = tickers[0]

    result = rebalance_after_weight_change(tickers, weights, locks, changed)
    for ticker in tickers:
        if locks[ticker] and ticker != changed:
            expected = max(0.0, float(weights[ticker]))
            assert result[ticker] == expected


@given(portfolio=portfolios(min_tickers=2))
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_rebalance_after_change_no_negative_weights(portfolio):
    tickers, weights, locks = portfolio
    changed = tickers[0]

    result = rebalance_after_weight_change(tickers, weights, locks, changed)
    assert all(value >= 0.0 for value in result.values())


@given(portfolio=portfolios(min_tickers=2))
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_rebalance_after_change_keeps_all_tickers(portfolio):
    tickers, weights, locks = portfolio
    changed = tickers[0]

    result = rebalance_after_weight_change(tickers, weights, locks, changed)
    assert set(result) == set(tickers)
