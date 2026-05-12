"""Dashboard tab router for FinPort."""
from __future__ import annotations

from datetime import date

import streamlit as st

from models import PortfolioAnalysisResult
from views.assumptions import render_assumptions_tab
from views.benchmark import render_benchmark_tab
from views.correlation import render_correlation_tab
from views.export import render_export_tab
from views.glossary import render_glossary_tab
from views.monte_carlo import render_monte_carlo_tab
from views.optimization import render_optimization_tab
from views.overview import render_overview_tab
from views.returns import render_returns_tab


def render_dashboard_tabs(
    result: PortfolioAnalysisResult,
    start_date: date,
    end_date: date,
    initial_investment: float,
    risk_free_rate: float,
    mc_horizon_days: int,
    mc_method_label: str,
    demo_mode: bool = False,
) -> None:
    """Render all analysis dashboard tabs."""
    prices = result.prices
    weights = result.weights
    returns = result.returns
    norm = result.normalized_prices
    asset_stats = result.asset_stats
    port_metrics = result.portfolio_metrics
    sharpe = result.portfolio_sharpe
    corr = result.correlation
    port_value = result.portfolio_value
    portfolio_cagr = result.portfolio_cagr
    equal_weights = result.equal_weights
    eq_metrics = result.equal_weight_metrics
    eq_sharpe = result.equal_weight_sharpe
    eq_value = result.equal_weight_value
    dd_info = result.drawdown_info
    sortino = result.sortino
    max_sharpe_weights = result.max_sharpe_weights
    min_var_weights = result.min_variance_weights
    max_sharpe_metrics = result.max_sharpe_metrics
    min_var_metrics = result.min_variance_metrics
    max_sharpe_value = result.max_sharpe_ratio
    min_var_sharpe = result.min_variance_sharpe
    frontier_df = result.efficient_frontier
    market_value = result.market_value
    capm = result.capm
    market_loaded = result.market_loaded
    sims = result.simulations
    mc_p5 = result.mc_p5
    mc_p50 = result.mc_p50
    mc_p95 = result.mc_p95
    var_95 = result.var_95
    mc_method = "bootstrap" if mc_method_label == "Historical bootstrap" else "parametric"

    tabs = st.tabs([
        "Overview", "Returns & Risk", "Correlation", "Monte Carlo",
        "Optimization", "Benchmark", "Export", "Assumptions", "Glossary",
    ])
    renderers = [
        render_overview_tab,
        render_returns_tab,
        render_correlation_tab,
        render_monte_carlo_tab,
        render_optimization_tab,
        render_benchmark_tab,
        render_export_tab,
        render_assumptions_tab,
        render_glossary_tab,
    ]
    for tab, renderer in zip(tabs, renderers, strict=True):
        with tab:
            renderer(

            prices=prices,
            weights=weights,
            returns=returns,
            norm=norm,
            asset_stats=asset_stats,
            port_metrics=port_metrics,
            sharpe=sharpe,
            corr=corr,
            port_value=port_value,
            portfolio_cagr=portfolio_cagr,
            equal_weights=equal_weights,
            eq_metrics=eq_metrics,
            eq_sharpe=eq_sharpe,
            eq_value=eq_value,
            dd_info=dd_info,
            sortino=sortino,
            max_sharpe_weights=max_sharpe_weights,
            min_var_weights=min_var_weights,
            max_sharpe_metrics=max_sharpe_metrics,
            min_var_metrics=min_var_metrics,
            max_sharpe_value=max_sharpe_value,
            min_var_sharpe=min_var_sharpe,
            frontier_df=frontier_df,
            market_value=market_value,
            capm=capm,
            market_loaded=market_loaded,
            sims=sims,
            mc_p5=mc_p5,
            mc_p50=mc_p50,
            mc_p95=mc_p95,
            var_95=var_95,
            mc_method=mc_method,
            start_date=start_date,
            end_date=end_date,
            initial_investment=initial_investment,
            risk_free_rate=risk_free_rate,
            mc_horizon_days=mc_horizon_days,
            mc_method_label=mc_method_label,
            demo_mode=demo_mode,
            )
