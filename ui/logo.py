"""Inline SVG logo."""


def _logo_icon_svg(size: int) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 48 48" fill="none" '
        'xmlns="http://www.w3.org/2000/svg" style="flex-shrink:0; display:block;">'
        '<defs>'
        '<linearGradient id="fpBg" x1="0" y1="0" x2="48" y2="48" '
        'gradientUnits="userSpaceOnUse">'
        '<stop offset="0%" stop-color="#60a5fa"/>'
        '<stop offset="55%" stop-color="#2563eb"/>'
        '<stop offset="100%" stop-color="#1e3a8a"/>'
        '</linearGradient>'
        '<linearGradient id="fpGloss" x1="0" y1="0" x2="0" y2="48" '
        'gradientUnits="userSpaceOnUse">'
        '<stop offset="0%" stop-color="#ffffff" stop-opacity="0.18"/>'
        '<stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>'
        '</linearGradient>'
        '</defs>'
        '<rect width="48" height="48" rx="12" fill="url(#fpBg)"/>'
        '<rect width="48" height="48" rx="12" fill="url(#fpGloss)"/>'
        '<rect x="10" y="30" width="3.5" height="8" rx="1" '
        'fill="#ffffff" opacity="0.22"/>'
        '<rect x="16.5" y="25" width="3.5" height="13" rx="1" '
        'fill="#ffffff" opacity="0.22"/>'
        '<rect x="23" y="20" width="3.5" height="18" rx="1" '
        'fill="#ffffff" opacity="0.22"/>'
        '<polyline points="9,34 17,26 24,29 36,14" stroke="#ffffff" '
        'stroke-width="2.8" fill="none" stroke-linecap="round" '
        'stroke-linejoin="round"/>'
        '<polyline points="30,14 36,14 36,20" stroke="#ffffff" '
        'stroke-width="2.8" fill="none" stroke-linecap="round" '
        'stroke-linejoin="round"/>'
        '<circle cx="36" cy="14" r="3.2" fill="#fbbf24" '
        'stroke="#ffffff" stroke-width="1.2"/>'
        '</svg>'
    )


def logo_img(height: int = 44, with_text: bool = True) -> str:
    icon = _logo_icon_svg(height)
    if not with_text:
        return icon
    text_size = max(int(height * 0.72), 16)
    return (
        '<div style="display:flex; align-items:center; gap:12px;">'
        + icon
        + f'<div style="font-size:{text_size}px; font-weight:900; '
        'color:#f8fafc; letter-spacing:-1.5px; line-height:1; '
        'font-family:-apple-system,Segoe UI,sans-serif;">'
        'Fin<span style="color:#3b82f6;">Port</span>'
        '</div>'
        '</div>'
    )
