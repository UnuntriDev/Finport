from __future__ import annotations

import streamlit as st

from content.glossary import GLOSSARY_SOURCES, GLOSSARY_TERMS


def render_glossary_tab(*, 
    prices,
    weights,
    returns,
    norm,
    asset_stats,
    port_metrics,
    sharpe,
    corr,
    port_value,
    portfolio_cagr,
    equal_weights,
    eq_metrics,
    eq_sharpe,
    eq_value,
    dd_info,
    sortino,
    max_sharpe_weights,
    min_var_weights,
    max_sharpe_metrics,
    min_var_metrics,
    max_sharpe_value,
    min_var_sharpe,
    frontier_df,
    market_value,
    capm,
    market_loaded,
    sims,
    mc_p5,
    mc_p50,
    mc_p95,
    var_95,
    mc_method,
    start_date,
    end_date,
    initial_investment,
    risk_free_rate,
    mc_horizon_days,
    mc_method_label,
    demo_mode,
) -> None:
    st.subheader("Financial terms glossary")
    st.markdown(
        '<p style="color:#64748b; font-size:14px; margin-bottom:24px;">'
        "Reference for the concepts and metrics used throughout FinPort."
        "</p>",
        unsafe_allow_html=True,
    )

    # Render glossary with 2 columns of expanders
    g_col1, g_col2 = st.columns(2)
    for i, (term, definition) in enumerate(GLOSSARY_TERMS):
        target_col = g_col1 if i % 2 == 0 else g_col2
        with target_col:
            with st.expander(term):
                st.markdown(definition)

    st.divider()
    st.caption(GLOSSARY_SOURCES)
