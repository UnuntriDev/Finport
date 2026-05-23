"""Sidebar package — public API: render_sidebar(), SidebarState."""
from __future__ import annotations

import streamlit as st

from sidebar.sections import (
    render_assets_section,
    render_assumptions_section,
    render_dates_section,
    render_demo_section,
    render_monte_carlo_section,
    render_run_button,
    render_save_load_section,
    render_weights_section,
)
from sidebar.state import SidebarState, init_portfolio_state
from ui.logo import logo_img

__all__ = ["SidebarState", "render_sidebar"]


def render_sidebar(
    query_demo: bool = False,
    query_autorun: bool = False,
) -> SidebarState:
    init_portfolio_state()

    with st.sidebar:
        _render_header()
        tickers = render_assets_section()
        start_date, end_date = render_dates_section()
        weights_pct, weights_valid = render_weights_section(tickers)
        risk_free_rate, initial_investment = render_assumptions_section()
        mc_horizon_days, mc_simulations, mc_method_label = render_monte_carlo_section()
        demo_mode = render_demo_section(query_demo)
        render_save_load_section(tickers)
        run = render_run_button(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            initial_investment=initial_investment,
            demo_mode=demo_mode,
            query_autorun=query_autorun,
        )

    return SidebarState(
        tickers=tickers,
        weights_pct=weights_pct,
        weights_valid=weights_valid,
        start_date=start_date,
        end_date=end_date,
        risk_free_rate=risk_free_rate,
        initial_investment=initial_investment,
        mc_horizon_days=mc_horizon_days,
        mc_simulations=mc_simulations,
        mc_method_label=mc_method_label,
        demo_mode=demo_mode,
        run=run,
    )


def _render_header() -> None:
    st.markdown(
        '<div style="padding:6px 0 8px 0;">'
        + logo_img(height=32)
        + '</div>'
        '<div style="color:#475569; font-size:10px; font-weight:600; '
        'text-transform:uppercase; letter-spacing:0.08em; '
        'margin:0 0 14px 0;">Portfolio configuration</div>',
        unsafe_allow_html=True,
    )
