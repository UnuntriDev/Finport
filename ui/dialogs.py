"""Modal dialogs."""
from __future__ import annotations

from html import escape

import streamlit as st


@st.dialog("⚠️ Some tickers could not be loaded")
def show_failed_tickers_dialog(failed: dict[str, str], failed_key: str) -> None:
    st.markdown("The following tickers were **excluded from the analysis**:")
    for ticker, reason in failed.items():
        safe_ticker = escape(str(ticker))
        safe_reason = escape(str(reason))
        st.markdown(
            f'<div style="background:#1a1a2e; border-left:3px solid '
            f'#f59e0b; border-radius:0 6px 6px 0; padding:10px 14px; '
            f'margin:8px 0;">'
            f'<div style="color:#fbbf24; font-weight:800; '
            f'font-size:14px; margin-bottom:4px;">{safe_ticker}</div>'
            f'<div style="color:#cbd5e1; font-size:12px;">{safe_reason}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
    st.caption(
        "Tip: verify the symbol on Yahoo Finance, or widen the date range "
        "if the asset is recent."
    )
    if st.button("Got it", type="primary", use_container_width=True):
        st.session_state["fp_failed_dismissed_key"] = failed_key
        st.rerun()
