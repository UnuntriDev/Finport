import pandas as pd

from report_exporter import (
    build_excel_workbook,
    build_pdf,
    prices_to_csv,
    returns_to_csv,
    summary_to_csv,
)


def _report_data():
    index = pd.date_range("2024-01-01", periods=5, freq="B")
    prices = pd.DataFrame(
        {"AAPL": [100, 101, 102, 103, 104], "MSFT": [50, 51, 52, 51, 53]},
        index=index,
    )
    returns = prices.pct_change().dropna()
    stats = pd.DataFrame(
        {
            "mean_daily": returns.mean(),
            "annual_return": returns.mean() * 252,
            "annual_vol": returns.std() * 252**0.5,
        }
    )
    weights = pd.Series({"AAPL": 0.6, "MSFT": 0.4})
    port_value = pd.Series([10_000, 10_100, 10_250, 10_300, 10_500], index=index)
    metrics = {"return": 0.12, "volatility": 0.18}
    return prices, returns, stats, weights, port_value, metrics


def test_csv_exports_contain_expected_headers():
    prices, returns, stats, weights, *_ = _report_data()

    assert "AAPL" in prices_to_csv(prices)
    assert "MSFT" in returns_to_csv(returns)
    assert "weight" in summary_to_csv(stats, weights)


def test_build_pdf_returns_bytes_like_output():
    prices, _, stats, weights, port_value, metrics = _report_data()

    output = build_pdf(
        tickers=list(prices.columns),
        weights=weights,
        start_date=prices.index[0].date(),
        end_date=prices.index[-1].date(),
        port_metrics=metrics,
        sharpe=0.55,
        risk_free_rate=0.02,
        initial_investment=10_000,
        asset_stats=stats,
        port_value=port_value,
        cagr_value=0.10,
        mc_p5=9_500,
        mc_p50=10_500,
        mc_p95=12_000,
        mc_horizon_days=252,
        mc_method="Parametric normal",
    )

    assert bytes(output).startswith(b"%PDF")


def test_build_excel_workbook_returns_xlsx_bytes():
    prices, returns, stats, weights, port_value, metrics = _report_data()

    output = build_excel_workbook(
        prices=prices,
        returns=returns,
        asset_stats=stats,
        weights=weights,
        port_value=port_value,
        port_metrics=metrics,
        sharpe=0.55,
        cagr_value=0.10,
    )

    assert output.startswith(b"PK")
