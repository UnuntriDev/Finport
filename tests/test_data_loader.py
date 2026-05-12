from datetime import date

import pandas as pd

import data_loader


def _clear_loader_cache():
    if hasattr(data_loader.load_price_data, "clear"):
        data_loader.load_price_data.clear()


def test_load_price_data_rejects_invalid_symbol_without_calling_yfinance(monkeypatch):
    _clear_loader_cache()
    called = False

    def fake_download(*args, **kwargs):
        nonlocal called
        called = True
        return pd.DataFrame()

    monkeypatch.setattr(data_loader.yf, "download", fake_download)

    prices, failed = data_loader.load_price_data(["<script>"], date(2024, 1, 1), date(2024, 2, 1))

    assert prices.empty
    assert failed == {"<script>": "Invalid ticker symbol format."}
    assert called is False


def test_load_price_data_handles_empty_yfinance_response(monkeypatch):
    _clear_loader_cache()

    def fake_download(*args, **kwargs):
        return pd.DataFrame()

    monkeypatch.setattr(data_loader.yf, "download", fake_download)

    prices, failed = data_loader.load_price_data(["AAPL"], date(2024, 1, 1), date(2024, 2, 1))

    assert prices.empty
    assert "AAPL" in failed


def test_load_price_data_extracts_close_column(monkeypatch):
    _clear_loader_cache()
    dates = pd.date_range("2024-01-01", periods=3, freq="B")

    def fake_download(*args, **kwargs):
        return pd.DataFrame({"Close": [100.0, 101.0, 102.0]}, index=dates)

    monkeypatch.setattr(data_loader.yf, "download", fake_download)

    prices, failed = data_loader.load_price_data(["aapl"], date(2024, 1, 1), date(2024, 2, 1))

    assert failed == {}
    assert list(prices.columns) == ["AAPL"]
    assert prices.iloc[-1, 0] == 102.0
