from __future__ import annotations

import pandas as pd
import streamlit as st

from models import PortfolioAnalysisResult, ViewContext


def render_returns_tab(result: PortfolioAnalysisResult, context: ViewContext) -> None:
    weights = result.weights
    returns = result.returns
    asset_stats = result.asset_stats
    st.subheader("Per-asset statistics")
    display_stats = pd.DataFrame(
        {
            "Weight": weights.reindex(asset_stats.index).map(lambda x: f"{x * 100:.2f}%"),
            "Avg daily return": asset_stats["mean_daily"].map(lambda x: f"{x * 100:.3f}%"),
            "Annualized return": asset_stats["annual_return"].map(lambda x: f"{x * 100:.2f}%"),
            "Annualized volatility": asset_stats["annual_vol"].map(lambda x: f"{x * 100:.2f}%"),
        }
    )
    st.dataframe(display_stats, use_container_width=True)

    st.subheader("Daily returns — descriptive statistics")
    st.dataframe(
        returns.describe().T.style.format("{:.4f}"),
        use_container_width=True,
    )
    st.caption(
        "Annualization assumes **252 trading days** per year. "
        "Volatility = σ_daily × √252. Return = μ_daily × 252."
    )


    # ============================================================
    # Tab 3: Correlation
