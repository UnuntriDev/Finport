from portfolio_state import (
    rebalance_after_weight_change,
    redistribute_equal_locked,
)


def test_equal_weight_without_locks_sums_to_100() -> None:
    result = redistribute_equal_locked(
        ["AAPL", "MSFT", "NVDA"],
        {"AAPL": 0.0, "MSFT": 0.0, "NVDA": 0.0},
        {},
    )

    assert result == {"AAPL": 33.33, "MSFT": 33.33, "NVDA": 33.34}
    assert round(sum(result.values()), 2) == 100.0


def test_equal_weight_respects_locked_weights() -> None:
    result = redistribute_equal_locked(
        ["AAPL", "MSFT", "NVDA"],
        {"AAPL": 40.0, "MSFT": 10.0, "NVDA": 50.0},
        {"AAPL": True},
    )

    assert result["AAPL"] == 40.0
    assert result["MSFT"] == 30.0
    assert result["NVDA"] == 30.0
    assert round(sum(result.values()), 2) == 100.0


def test_rebalance_after_change_scales_other_unlocked_weights() -> None:
    result = rebalance_after_weight_change(
        ["AAPL", "MSFT", "NVDA"],
        {"AAPL": 60.0, "MSFT": 25.0, "NVDA": 25.0},
        {},
        "AAPL",
    )

    assert result["AAPL"] == 60.0
    assert result["MSFT"] == 20.0
    assert result["NVDA"] == 20.0
    assert round(sum(result.values()), 2) == 100.0


def test_rebalance_caps_changed_weight_when_locked_allocation_is_high() -> None:
    result = rebalance_after_weight_change(
        ["AAPL", "MSFT", "NVDA"],
        {"AAPL": 80.0, "MSFT": 30.0, "NVDA": 20.0},
        {"MSFT": True},
        "AAPL",
    )

    assert result["MSFT"] == 30.0
    assert result["AAPL"] == 70.0
    assert result["NVDA"] == 0.0
    assert round(sum(result.values()), 2) == 100.0


def test_all_locked_weights_are_returned_unchanged() -> None:
    result = redistribute_equal_locked(
        ["AAPL", "MSFT"],
        {"AAPL": 55.0, "MSFT": 45.0},
        {"AAPL": True, "MSFT": True},
    )

    assert result == {"AAPL": 55.0, "MSFT": 45.0}
