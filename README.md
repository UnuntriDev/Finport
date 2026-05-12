# FinPort

FinPort is a Streamlit web application for portfolio analysis and risk assessment in stock investments. It was built as an academic Finance and Banking project, but it follows a modular project structure and uses realistic quantitative finance formulas.

## Features

- Multi-asset portfolio configuration with ticker chips and auto-balanced weights
- Yahoo Finance market data via `yfinance`
- Adjusted close prices and daily returns
- Annualized portfolio return and volatility
- Sharpe ratio, Sortino ratio, max drawdown
- Correlation matrix and sector allocation
- Monte Carlo simulation of future portfolio value
- Markowitz optimization:
  - Maximum Sharpe portfolio
  - Minimum variance portfolio
  - Efficient frontier
- CAPM benchmark analysis against S&P 500:
  - Beta
  - Alpha
  - R-squared
  - Correlation
- Equal-weight benchmark comparison
- PDF, Excel and CSV export
- Save/load portfolio configuration as JSON
- Glossary of finance terms

## Project Structure

```text
.
├── app.py                 # Streamlit UI and dashboard orchestration
├── analysis.py            # Pure quantitative finance calculations
├── data_loader.py         # yfinance data loading and sector lookup
├── visualization.py       # Plotly chart builders
├── report_exporter.py     # PDF, CSV and Excel export helpers
├── constants.py           # Shared app constants
├── ticker_utils.py        # Ticker validation helpers
├── tests/
│   └── test_analysis.py   # Unit tests for financial logic
├── requirements.txt
├── runtime.txt
└── .streamlit/
    └── config.toml
```

## Installation

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run tests:

```powershell
pytest
```

Run the app:

```powershell
streamlit run app.py
```

The app opens at:

```text
http://localhost:8501
```

## Example Portfolio

You can load an example portfolio from:

```text
examples/sample_portfolio.json
```

Use the **Save / Load Configuration** section in the sidebar.

## Data Source

Market prices and instrument metadata are downloaded from Yahoo Finance using `yfinance`.

Known limitations:

- Yahoo Finance can temporarily throttle requests.
- Some tickers may not return sector metadata.
- Recently listed assets may have insufficient historical data.
- Results depend on the selected historical period.

## Financial Methodology

FinPort uses standard portfolio analysis techniques:

- Daily simple returns: `price_t / price_t-1 - 1`
- Annualized return: mean daily return multiplied by 252 trading days
- Annualized volatility: daily standard deviation multiplied by `sqrt(252)`
- Portfolio volatility: full covariance matrix calculation
- Sharpe ratio: excess return per unit of volatility
- Sortino ratio: excess return per unit of downside volatility
- Max drawdown: largest peak-to-trough decline
- CAPM beta/alpha: regression against S&P 500 returns
- Monte Carlo: multivariate normal simulation preserving historical covariance
- Markowitz optimization: long-only portfolio optimization using SLSQP

## Deployment

The recommended deployment target is Streamlit Community Cloud.

Steps:

1. Push this project to GitHub.
2. Go to [Streamlit Community Cloud](https://streamlit.io/cloud).
3. Create a new app from the GitHub repository.
4. Set the main file path to:

```text
app.py
```

The app uses `runtime.txt` to request Python 3.11.

## Disclaimer

This application is for educational and academic purposes only. It does not constitute investment advice, financial recommendation, or an offer to buy or sell securities. Past performance is not indicative of future results. Market data is provided by Yahoo Finance and may contain inaccuracies or delays.
