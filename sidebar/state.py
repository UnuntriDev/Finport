"""Sidebar state and session-state initialisation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import streamlit as st


@dataclass(frozen=True)
class SidebarState:
    tickers: list[str]
    weights_pct: dict[str, float]
    weights_valid: bool
    start_date: date | None
    end_date: date | None
    risk_free_rate: float
    initial_investment: float
    mc_horizon_days: int
    mc_simulations: int
    mc_method_label: str
    demo_mode: bool
    run: bool


def init_portfolio_state() -> None:
    """Seed widget-keyed session state. Streamlit forbids mutating widget state
    after the widget renders, so all defaults must land here first.
    """
    ss = st.session_state
    if "fp_tickers" not in ss:
        ss.fp_tickers = []
    if "fp_locks" not in ss:
        ss.fp_locks = {t: False for t in ss.fp_tickers}
    if "fp_start_input" not in ss:
        ss.fp_start_input = None
    if "fp_end_input" not in ss:
        ss.fp_end_input = None

    n_tickers = len(ss.fp_tickers)
    if n_tickers > 0:
        share = round(100.0 / n_tickers, 2)
        diff = round(100.0 - share * n_tickers, 2)
        for i, ticker in enumerate(ss.fp_tickers):
            key = f"w_{ticker}"
            if key not in ss:
                ss[key] = round(share + (diff if i == n_tickers - 1 else 0), 2)
