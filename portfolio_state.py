"""Pure portfolio state helpers used by Streamlit callbacks."""
from __future__ import annotations

from collections.abc import Mapping, Sequence


def _current_weights(
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
    result = _current_weights(tickers, weights)
    locked = [ticker for ticker in tickers if locks.get(ticker, False)]
    unlocked = [ticker for ticker in tickers if not locks.get(ticker, False)]

    if not unlocked:
        return result

    locked_sum = sum(result[ticker] for ticker in locked)
    remaining = max(0.0, 100.0 - locked_sum)
    share = round(remaining / len(unlocked), 2)

    for ticker in unlocked:
        result[ticker] = share

    diff = round(100.0 - (locked_sum + share * len(unlocked)), 2)
    if abs(diff) > 0.001:
        result[unlocked[-1]] = round(result[unlocked[-1]] + diff, 2)

    return result


def rebalance_after_weight_change(
    tickers: Sequence[str],
    weights: Mapping[str, float],
    locks: Mapping[str, bool],
    changed_ticker: str,
) -> dict[str, float]:
    """Rebalance unlocked weights after one ticker weight has changed."""
    result = _current_weights(tickers, weights)
    if not tickers or changed_ticker not in tickers:
        return result

    locked = [ticker for ticker in tickers if locks.get(ticker, False)]
    locked_sum = sum(result[ticker] for ticker in locked)

    new_value = result[changed_ticker]
    other_unlocked = [
        ticker
        for ticker in tickers
        if ticker != changed_ticker and not locks.get(ticker, False)
    ]

    max_for_changed = max(0.0, 100.0 - locked_sum)
    if new_value > max_for_changed:
        new_value = round(max_for_changed, 2)
        result[changed_ticker] = new_value

    target = round(100.0 - locked_sum - new_value, 2)
    if not other_unlocked:
        return result

    current_sum = sum(result[ticker] for ticker in other_unlocked)
    if current_sum > 0.001:
        scale = target / current_sum
        for ticker in other_unlocked:
            result[ticker] = round(result[ticker] * scale, 2)
    else:
        share = round(target / len(other_unlocked), 2)
        for ticker in other_unlocked:
            result[ticker] = share

    total = locked_sum + result[changed_ticker] + sum(
        result[ticker] for ticker in other_unlocked
    )
    diff = round(100.0 - total, 2)
    if abs(diff) > 0.001:
        last = other_unlocked[-1]
        result[last] = round(result[last] + diff, 2)

    return result
