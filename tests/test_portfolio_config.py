from datetime import date

import pytest

from portfolio_config import normalize_weights_to_100, parse_portfolio_config


def test_parse_portfolio_config_normalizes_tickers_and_dates():
    raw = """
    {
      "tickers": ["aapl", "MSFT", "AAPL"],
      "weights": {"AAPL": 60, "MSFT": 40},
      "locks": {"AAPL": true},
      "start": "2024-01-01",
      "end": "2024-12-31"
    }
    """

    config = parse_portfolio_config(raw)

    assert config.tickers == ["AAPL", "MSFT"]
    assert config.weights == {"AAPL": 60.0, "MSFT": 40.0}
    assert config.locks == {"AAPL": True, "MSFT": False}
    assert config.start == date(2024, 1, 1)
    assert config.end == date(2024, 12, 31)


def test_parse_portfolio_config_rejects_invalid_ticker():
    with pytest.raises(ValueError, match="invalid ticker"):
        parse_portfolio_config('{"tickers": ["<script>"], "weights": {}, "locks": {}}')


def test_parse_portfolio_config_rejects_invalid_date_order():
    raw = """
    {
      "tickers": ["AAPL"],
      "weights": {},
      "locks": {},
      "start": "2024-12-31",
      "end": "2024-01-01"
    }
    """

    with pytest.raises(ValueError, match="start date"):
        parse_portfolio_config(raw)


def test_normalize_weights_to_100_scales_and_fixes_rounding():
    normalized = normalize_weights_to_100({"AAPL": 10, "MSFT": 20, "NVDA": 30})

    assert round(sum(normalized.values()), 2) == 100.0
    assert normalized["NVDA"] > normalized["MSFT"] > normalized["AAPL"]


def test_normalize_weights_to_100_uses_equal_weight_for_zero_total():
    normalized = normalize_weights_to_100({"AAPL": 0, "MSFT": 0, "NVDA": 0})

    assert round(sum(normalized.values()), 2) == 100.0
    assert set(normalized) == {"AAPL", "MSFT", "NVDA"}
