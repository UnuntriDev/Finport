"""Reusable HTML snippets for the Streamlit UI."""

from __future__ import annotations

from html import escape

from theme import COLORS


def metric_card(
    label: str,
    value: str,
    tooltip: str,
    sub_text: str = "",
    value_color: str | None = None,
    sub_color: str | None = None,
) -> str:
    safe_label = escape(label)
    safe_value = escape(value)
    safe_tooltip = escape(tooltip, quote=True)
    value_color = value_color or COLORS["text_strong"]
    sub_color = sub_color or COLORS["muted"]
    sub_html = (
        f'<div style="font-size:12px; color:{sub_color}; margin-top:6px; '
        f'font-weight:500;">{escape(sub_text)}</div>'
        if sub_text else ""
    )
    return (
        f'<div style="background:linear-gradient(145deg,{COLORS["surface"]},'
        f'{COLORS["surface_alt"]}); border:1px solid {COLORS["primary_soft"]}; '
        'border-radius:10px; padding:18px 20px; min-height:108px;">'
        f'<div style="font-size:10px; color:{COLORS["muted"]}; font-weight:700; '
        'text-transform:uppercase; letter-spacing:0.07em; display:flex; '
        'align-items:center; gap:6px; margin-bottom:10px;">'
        f'{safe_label}'
        f'<span title="{safe_tooltip}" style="display:inline-flex; '
        'align-items:center; justify-content:center; width:14px; height:14px; '
        f'border-radius:50%; background:{COLORS["primary_soft"]}; '
        f'color:#60a5fa; font-size:8px; font-weight:800; cursor:help; '
        f'border:1px solid {COLORS["primary"]}; flex-shrink:0;">?</span>'
        '</div>'
        f'<div style="font-size:26px; font-weight:800; color:{value_color}; '
        f'line-height:1.1; letter-spacing:-0.02em;">{safe_value}</div>'
        f'{sub_html}'
        '</div>'
    )


def sidebar_section_header(icon: str, label: str, margin_bottom: int = 10) -> str:
    return (
        '<div style="display:flex; align-items:center; gap:8px; '
        f'margin:4px 0 {margin_bottom}px 0; padding:7px 10px; '
        f'background:linear-gradient(90deg,#0f2040 0%,{COLORS["surface_deep"]} 100%); '
        f'border-left:3px solid {COLORS["primary"]}; border-radius:0 6px 6px 0;">'
        f'<span style="font-size:13px;">{escape(icon)}</span>'
        f'<span style="color:{COLORS["text"]}; font-size:13px; font-weight:800; '
        'text-transform:uppercase; letter-spacing:0.06em;">'
        f'{escape(label)}</span>'
        '</div>'
    )


def export_section_header(icon: str, label: str) -> str:
    return (
        '<div style="display:flex; align-items:center; gap:10px; '
        'margin:8px 0 16px 0;">'
        f'<span style="font-size:16px;">{escape(icon)}</span>'
        f'<span style="color:{COLORS["text"]}; font-size:14px; font-weight:700; '
        f'letter-spacing:0.01em;">{escape(label)}</span>'
        f'<div style="flex:1; height:1px; background:{COLORS["surface_alt"]}; '
        'margin-left:4px;"></div>'
        '</div>'
    )


def export_item_label(label: str) -> str:
    return (
        f'<div style="color:#93c5fd; font-size:12px; font-weight:700; '
        'text-transform:uppercase; letter-spacing:0.06em; margin-bottom:4px;">'
        f'{escape(label)}</div>'
    )


def muted_paragraph(text: str, margin_bottom: int = 24) -> str:
    return (
        f'<p style="color:{COLORS["muted"]}; font-size:14px; '
        f'margin-bottom:{margin_bottom}px;">'
        f'{escape(text)}</p>'
    )


def vertical_spacer(height: int = 20) -> str:
    return f"<div style='margin-bottom:{height}px;'></div>"


# ---------------------------------------------------------------------------
# Semantic color helpers (sign-based / threshold-based) — keep UI consistent
# ---------------------------------------------------------------------------

def color_for_sign(value: float, positive_color: str | None = None,
                   negative_color: str | None = None) -> str:
    """Return success color for positive values, danger color for negative."""
    pos = positive_color or COLORS["success"]
    neg = negative_color or COLORS["danger"]
    return pos if value >= 0 else neg


def arrow_for_sign(value: float) -> str:
    """Return ▲ for positive values, ▼ for negative."""
    return "▲" if value >= 0 else "▼"


def color_for_threshold(
    value: float,
    good_threshold: float,
    warn_threshold: float,
) -> str:
    """Three-tier semantic color: >= good ⇒ success, >= warn ⇒ warning, else danger."""
    if value >= good_threshold:
        return COLORS["success"]
    if value >= warn_threshold:
        return COLORS["warning"]
    return COLORS["danger"]
