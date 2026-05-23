"""Correlation tab."""
from __future__ import annotations

import streamlit as st

from models import PortfolioAnalysisResult, ViewContext
from visualization import plot_correlation_heatmap


def render_correlation_tab(
    result: PortfolioAnalysisResult,
    context: ViewContext,
) -> None:
    del context
    st.subheader("Return correlation matrix")
    st.plotly_chart(plot_correlation_heatmap(result.correlation), use_container_width=True)
    st.caption(
        "**+1.0** — assets move in perfect lockstep (no diversification). "
        "**0.0** — uncorrelated (good diversification). "
        "**−1.0** — assets move in opposite directions (maximum hedge)."
    )
