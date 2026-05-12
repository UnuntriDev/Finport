"""Landing page markup shown before the first analysis run."""
from __future__ import annotations

import streamlit as st

from ui.logo import logo_img

_FEATURE_CARD_STYLE = (
    "background:#0a1628; border:1px solid #1e3a5f; border-radius:8px; "
    "padding:12px 20px; color:#60a5fa; font-size:12px; font-weight:600;"
)

_FEATURES = (
    "📈 Price History",
    "⚡ Risk &amp; Return",
    "🎲 Monte Carlo",
    "📄 PDF Export",
)


def render_landing_page() -> None:
    """Render the centred 'configure your portfolio' welcome card."""
    big_logo = logo_img(height=72, with_text=False)
    feature_cards = "".join(
        f'<div style="{_FEATURE_CARD_STYLE}">{feature}</div>'
        for feature in _FEATURES
    )
    st.markdown(
        '<div style="background:linear-gradient(145deg,#0f172a,#1e293b); '
        'border:1px solid #1e3a5f; border-radius:12px; padding:48px; '
        'text-align:center; margin-top:20px;">'
        '<div style="display:flex; justify-content:center; margin-bottom:20px;">'
        f'{big_logo}</div>'
        '<h2 style="color:#e2e8f0; font-size:22px; font-weight:700; '
        'margin:0 0 8px 0;">Configure your portfolio</h2>'
        '<p style="color:#64748b; font-size:14px; max-width:440px; '
        'margin:0 auto 24px;">Enter tickers, set a date range and assign '
        'weights in the sidebar, then click '
        '<strong style="color:#60a5fa;">Run analysis</strong>.</p>'
        '<div style="display:flex; justify-content:center; gap:14px; '
        f'flex-wrap:wrap;">{feature_cards}</div>'
        '</div>',
        unsafe_allow_html=True,
    )
