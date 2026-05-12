from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from models import PortfolioAnalysisRequest
from services import portfolio_analysis


def test_run_portfolio_analysis_pipeline_with_offline_prices(monkeypatch) -> None:
    index = pd.bdate_range("2025-01-01", periods=80)
    stock_prices = pd.DataFrame(
        {
            "AAPL": np.linspace(100.0, 125.0, len(index)),
            "MSFT": np.linspace(80.0, 92.0, len(index)),
            "NVDA": np.linspace(140.0, 180.0, len(index)),
        },
        index=index,
    )
    benchmark_prices = pd.DataFrame(
        {"^GSPC": np.linspace(5000.0, 5300.0, len(index))},
        index=index,
    )

    def fake_load_price_data(tickers, start_date, end_date):
        if tickers == ["^GSPC"]:
            return benchmark_prices, {}
        return stock_prices.loc[:, tickers], {}

    monkeypatch.setattr(
        portfolio_analysis,
        "load_price_data",
        fake_load_price_data,
    )

    request = PortfolioAnalysisRequest(
        tickers=["AAPL", "MSFT", "NVDA"],
        weights_pct={"AAPL": 50.0, "MSFT": 30.0, "NVDA": 20.0},
        start_date=date(2025, 1, 1),
        end_date=date(2025, 4, 30),
        initial_investment=10_000.0,
        risk_free_rate=0.03,
        mc_horizon_days=20,
        mc_simulations=100,
        mc_method_label="Historical bootstrap",
    )

    result = portfolio_analysis.run_portfolio_analysis(request)

    assert list(result.prices.columns) == ["AAPL", "MSFT", "NVDA"]
    assert round(float(result.weights.sum()), 8) == 1.0
    assert result.returns.shape[0] == len(stock_prices) - 1
    assert result.portfolio_value.iloc[0] == 10_000.0
    assert result.simulations.shape == (21, 100)
    assert result.market_loaded is True
    assert {"beta", "alpha", "r_squared", "correlation"} <= set(result.capm)
