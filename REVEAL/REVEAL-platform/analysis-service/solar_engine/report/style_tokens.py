from __future__ import annotations


BRAND_TOKENS = {
    "primary_navy": "#0B2A3D",
    "accent_orange": "#F39200",
    "secondary_slate_blue": "#3E516C",
    "deep_indigo": "#27275A",
    "body_text": "#1F2933",
    "muted_text": "#6B7785",
    "light_background": "#F4F6F8",
    "border_grey": "#D9E0E6",
    "success_green": "#70AD47",
    "warning_amber": "#C98A00",
    "danger_red": "#C62828",
    "white": "#FFFFFF",
}


def get_style_tokens(debug_layout: bool = False) -> dict:
    return {
        "colors": BRAND_TOKENS.copy(),
        "fonts": {
            "sans": "Aptos, Calibri, Arial, Helvetica, sans-serif",
            "body_size_pt": 10.5,
            "caption_size_pt": 8.5,
        },
        "page": {
            "size": "A4 portrait",
            "margin_top": "12mm",
            "margin_right": "12mm",
            "margin_bottom": "14mm",
            "margin_left": "12mm",
        },
        "debug_layout": debug_layout,
        "chart": {
            "full": (7.1, 4.6),
            "half": (3.35, 3.0),
            "appendix_wide": (7.2, 6.9),
        },
    }
