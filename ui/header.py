"""Top header banner for the analysis dashboard."""
from __future__ import annotations

from datetime import date
from html import escape

import streamlit as st

from ui.logo import logo_img


def render_header(tickers: list[str] | None = None, period: str = "") -> None:
    """Render the FinPort header with logo, ticker badges, period and today date."""
    col_logo, col_meta = st.columns([3, 1])

    with col_logo:
        st.markdown(_logo_block(), unsafe_allow_html=True)
    with col_meta:
        st.markdown(_meta_block(tickers, period), unsafe_allow_html=True)

    st.markdown(
        '<div style="border-top:1px solid #1e3a5f; margin:4px 0 20px 0;"></div>',
        unsafe_allow_html=True,
    )


def _logo_block() -> str:
    return (
        '<div style="padding:8px 0 6px 0;">'
        + logo_img(height=48)
        + '<div style="color:#64748b; font-size:12px; font-weight:500; '
        'margin:10px 0 0 60px; letter-spacing:0.01em;">'
        'Portfolio Analysis &amp; Risk Assessment Platform'
        '</div></div>'
    )


def _meta_block(tickers: list[str] | None, period: str) -> str:
    badges_html = _badges_html(tickers)
    period_html = (
        f'<div style="color:#64748b; font-size:11px; margin-bottom:2px;">'
        f'{escape(period)}</div>'
        if period else ""
    )
    date_str = date.today().strftime("%b %d, %Y")
    return (
        '<div style="padding:18px 0 6px 0; text-align:right;">'
        + badges_html
        + period_html
        + f'<div style="color:#334155; font-size:11px;">{date_str}</div>'
        + '</div>'
    )


def _badges_html(tickers: list[str] | None) -> str:
    if not tickers:
        return ""
    badges = "".join(
        '<span style="background:#1e3a5f; color:#93c5fd; font-size:10px; '
        'font-weight:600; padding:2px 8px; border-radius:10px; '
        'border:1px solid #1d4ed8; margin:2px 2px 0 0; '
        f'display:inline-block;">{escape(str(t))}</span>'
        for t in tickers
    )
    return f'<div style="margin-bottom:6px; line-height:2;">{badges}</div>'
