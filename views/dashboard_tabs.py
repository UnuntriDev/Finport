"""Dashboard tab router."""
from __future__ import annotations

from datetime import date

import streamlit as st

from models import PortfolioAnalysisResult, ViewContext
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
    context = ViewContext(
        start_date=start_date,
        end_date=end_date,
        initial_investment=initial_investment,
        risk_free_rate=risk_free_rate,
        mc_horizon_days=mc_horizon_days,
        mc_method_label=mc_method_label,
        demo_mode=demo_mode,
    )

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
            renderer(result, context)
