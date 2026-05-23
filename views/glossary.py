from __future__ import annotations

import streamlit as st

from content.glossary import GLOSSARY_SOURCES, GLOSSARY_TERMS
from models import PortfolioAnalysisResult, ViewContext
from ui_components import muted_paragraph


def render_glossary_tab(result: PortfolioAnalysisResult, context: ViewContext) -> None:
    st.subheader("Financial terms glossary")
    st.markdown(
        muted_paragraph("Reference for the concepts and metrics used throughout FinPort."),
        unsafe_allow_html=True,
    )

    g_col1, g_col2 = st.columns(2)
    for i, (term, definition) in enumerate(GLOSSARY_TERMS):
        target_col = g_col1 if i % 2 == 0 else g_col2
        with target_col:
            with st.expander(term):
                st.markdown(definition)

    st.divider()
    st.caption(GLOSSARY_SOURCES)
