"""Pure portfolio state helpers used by Streamlit callbacks.

All functions return a fresh dict — they never mutate the input.

Invariants guaranteed by these helpers:
    * Returned weights are always >= 0 (no negative weights leak through).
    * Locked weights are never modified.
    * When ``locked_sum <= 100`` the result sums to (approximately) 100.
    * When ``locked_sum > 100`` (degenerate input) all unlocked weights are
      set to 0 — the total stays above 100 but no negative values appear.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

_ROUND_DECIMALS = 2
_TOTAL_TARGET = 100.0


def _clean_weights(
    tickers: Sequence[str],
    weights: Mapping[str, float],
) -> dict[str, float]:
    return {ticker: max(0.0, float(weights.get(ticker, 0.0))) for ticker in tickers}


def redistribute_equal_locked(
    tickers: Sequence[str],
    weights: Mapping[str, float],
    locks: Mapping[str, bool],
) -> dict[str, float]:
    """Split remaining allocation equally across unlocked tickers."""
    result = _clean_weights(tickers, weights)
    unlocked = [t for t in tickers if not locks.get(t, False)]
    if not unlocked:
        return result

    locked_sum = sum(
        result[t] for t in tickers if locks.get(t, False)
    )
    remaining = max(0.0, _TOTAL_TARGET - locked_sum)
    share = round(remaining / len(unlocked), _ROUND_DECIMALS)

    for ticker in unlocked:
        result[ticker] = share

    drift = round(_TOTAL_TARGET - (locked_sum + share * len(unlocked)), _ROUND_DECIMALS)
    if abs(drift) > 0.001:
        last = unlocked[-1]
        result[last] = max(0.0, round(result[last] + drift, _ROUND_DECIMALS))

    return result


def rebalance_after_weight_change(
    tickers: Sequence[str],
    weights: Mapping[str, float],
    locks: Mapping[str, bool],
    changed_ticker: str,
) -> dict[str, float]:
    """Rebalance unlocked weights after one ticker weight has changed."""
    result = _clean_weights(tickers, weights)
    if not tickers or changed_ticker not in tickers:
        return result

    locked_sum = sum(
        result[t] for t in tickers if locks.get(t, False)
    )
    other_unlocked = [
        t for t in tickers
        if t != changed_ticker and not locks.get(t, False)
    ]

    max_for_changed = max(0.0, _TOTAL_TARGET - locked_sum)
    if result[changed_ticker] > max_for_changed:
        result[changed_ticker] = round(max_for_changed, _ROUND_DECIMALS)

    target = max(0.0, round(_TOTAL_TARGET - locked_sum - result[changed_ticker], _ROUND_DECIMALS))
    if not other_unlocked:
        return result

    current_sum = sum(result[t] for t in other_unlocked)
    if current_sum > 0.001:
        scale = target / current_sum
        for ticker in other_unlocked:
            result[ticker] = round(result[ticker] * scale, _ROUND_DECIMALS)
    else:
        share = round(target / len(other_unlocked), _ROUND_DECIMALS)
        for ticker in other_unlocked:
            result[ticker] = share

    drift = round(
        _TOTAL_TARGET - (
            locked_sum + result[changed_ticker]
            + sum(result[t] for t in other_unlocked)
        ),
        _ROUND_DECIMALS,
    )
    if abs(drift) > 0.001:
        last = other_unlocked[-1]
        result[last] = max(0.0, round(result[last] + drift, _ROUND_DECIMALS))

    return result
