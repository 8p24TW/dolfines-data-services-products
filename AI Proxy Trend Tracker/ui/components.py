from __future__ import annotations

import base64
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
import streamlit.components.v1 as components


STATUS_COLORS = {
    "rising":  "#10b981",   # emerald
    "stable":  "#64748b",   # slate
    "falling": "#ef4444",   # red
    "new":     "#3b82f6",   # blue
}

STATUS_LABELS = {
    "rising":  "↑ Rising",
    "stable":  "→ Stable",
    "falling": "↓ Falling",
    "new":     "✦ New",
}


def _dark_html_table(df: pd.DataFrame, max_height: str = "360px") -> str:
    """Render a DataFrame as a fully dark HTML table (not subject to Streamlit iframe isolation)."""
    TH = (
        "background:#091828;color:#c8ddf0;"
        "border-bottom:2px solid rgba(77,212,172,0.32);"
        "border-right:1px solid rgba(107,138,172,0.14);"
        "padding:8px 13px;font-size:0.73rem;"
        "text-transform:uppercase;letter-spacing:0.065em;font-weight:700;white-space:nowrap;"
    )
    TD_EVEN = (
        "background:#0d1e31;color:#d4e5f4;"
        "border-bottom:1px solid rgba(107,138,172,0.11);"
        "border-right:1px solid rgba(107,138,172,0.08);"
        "padding:7px 13px;font-size:0.82rem;vertical-align:top;"
    )
    TD_ODD = TD_EVEN.replace("#0d1e31", "#091929")

    header = "".join(f'<th style="{TH}">{col}</th>' for col in df.columns)
    rows_html = ""
    for i, (_, row) in enumerate(df.iterrows()):
        td = TD_EVEN if i % 2 == 0 else TD_ODD
        cells = "".join(f'<td style="{td}">{v}</td>' for v in row)
        rows_html += f"<tr>{cells}</tr>"

    return (
        f'<div style="overflow:auto;max-height:{max_height};border-radius:13px;'
        f'border:1px solid rgba(107,138,172,0.20);margin-bottom:0.5rem;">'
        f'<table style="width:100%;border-collapse:collapse;'
        f'font-family:IBM Plex Sans,Inter,sans-serif;">'
        f"<thead><tr>{header}</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        f"</table></div>"
    )


def style_dark_table(frame: pd.DataFrame):
    """Legacy pandas Styler — only used where st.table() is called."""
    return frame.style.set_table_styles(
        [
            {"selector": "thead tr th", "props": [
                ("background-color", "#0b1929"), ("color", "#e2eaf3"),
                ("border-bottom", "2px solid rgba(77,212,172,0.35)"),
                ("padding", "8px 12px"), ("font-size", "0.78rem"),
                ("text-transform", "uppercase"), ("font-weight", "700"),
            ]},
            {"selector": "tbody tr td", "props": [
                ("background-color", "#0f1e30"), ("color", "#d8e6f2"),
                ("border-bottom", "1px solid rgba(121,145,171,0.12)"),
                ("padding", "7px 12px"), ("font-size", "0.82rem"),
            ]},
            {"selector": "table", "props": [
                ("background-color", "#0f1e30"), ("color", "#d8e6f2"),
                ("border-collapse", "collapse"), ("width", "100%"),
            ]},
        ]
    )


def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

        :root {
            --bg:       #08111c;
            --bg-2:     #0d1c2e;
            --panel:    rgba(14, 27, 43, 0.96);
            --panel-2:  rgba(9, 19, 33, 0.94);
            --text:     #e8f1fa;
            --muted:    #8ba8c4;
            --accent:   #4dd4ac;
            --accent-2: #3b9eff;
            --danger:   #ef4444;
            --warn:     #f59e0b;
            --line:     rgba(107, 138, 172, 0.22);
            --shadow:   0 20px 48px rgba(1, 6, 14, 0.55);
            --glow:     0 0 0 1px rgba(77,212,172,0.18), 0 0 18px rgba(77,212,172,0.06);
        }

        /* ── Base ─────────────────────────────────────────────── */
        html, body, .stApp {
            font-family: "IBM Plex Sans", "Inter", system-ui, sans-serif;
            background:
                radial-gradient(ellipse at top left, rgba(77,212,172,0.10) 0%, transparent 32%),
                radial-gradient(ellipse at top right, rgba(59,158,255,0.10) 0%, transparent 30%),
                linear-gradient(175deg, #08111c 0%, #060e18 55%, #050c16 100%);
            color: var(--text);
        }
        .block-container {
            max-width: 1480px;
            padding-top: 1rem;
            padding-bottom: 2.5rem;
        }

        /* ── Typography ──────────────────────────────────────── */
        h1, h2, h3, h4, h5, h6,
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            color: var(--text) !important;
        }
        .stMarkdown, .stCaption, label, p {
            color: var(--text) !important;
        }

        /* ── Controls ────────────────────────────────────────── */
        [data-baseweb="select"] > div,
        [data-baseweb="base-input"] > div,
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input {
            background: rgba(10, 22, 38, 0.92) !important;
            color: var(--text) !important;
            border-color: rgba(107,138,172,0.28) !important;
            border-radius: 10px !important;
        }
        [data-baseweb="tag"] {
            background: rgba(77,212,172,0.15) !important;
            color: var(--accent) !important;
            border: 1px solid rgba(77,212,172,0.28) !important;
            border-radius: 6px !important;
        }
        [data-baseweb="menu"], [data-baseweb="popover"] {
            background: #0d1e31 !important;
            border: 1px solid var(--line) !important;
            border-radius: 12px !important;
            color: var(--text) !important;
        }
        [data-baseweb="menu"] li:hover {
            background: rgba(77,212,172,0.10) !important;
        }
        [data-baseweb="option"] {
            color: var(--text) !important;
        }
        .stSelectbox label, .stMultiSelect label,
        .stTextInput label, .stSlider label,
        .stCheckbox label, .stRadio label {
            color: var(--muted) !important;
            font-size: 0.8rem !important;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-weight: 600;
        }
        .stSlider [data-testid="stTickBarMin"],
        .stSlider [data-testid="stTickBarMax"] {
            color: var(--muted) !important;
        }
        .stSlider [data-testid="stSlider"] div[role="slider"] {
            background: var(--accent) !important;
        }
        .stButton button {
            background: rgba(77,212,172,0.12) !important;
            color: var(--accent) !important;
            border: 1px solid rgba(77,212,172,0.28) !important;
            border-radius: 10px !important;
            font-weight: 600;
            transition: all 0.18s ease;
        }
        .stButton button:hover {
            background: rgba(77,212,172,0.22) !important;
            border-color: rgba(77,212,172,0.5) !important;
        }

        /* ── Sidebar ─────────────────────────────────────────── */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #080f1c 0%, #0a1525 100%) !important;
            border-right: 1px solid var(--line) !important;
        }
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p {
            color: var(--text) !important;
        }
        [data-testid="stSidebarContent"] {
            padding-top: 1.5rem;
        }

        /* ── Expanders ───────────────────────────────────────── */
        [data-testid="stExpander"] {
            background: var(--panel-2) !important;
            border: 1px solid var(--line) !important;
            border-radius: 14px !important;
        }
        [data-testid="stExpander"] summary {
            color: var(--text) !important;
        }

        /* ── DataFrames ──────────────────────────────────────── */
        [data-testid="stDataFrame"], [data-testid="stTable"] {
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid var(--line);
            background: rgba(9, 19, 33, 0.97) !important;
        }
        div[data-testid="stDataFrame"] div[role="grid"],
        div[data-testid="stDataFrame"] div[role="row"],
        div[data-testid="stDataFrame"] div[role="gridcell"],
        div[data-testid="stDataFrame"] div[role="columnheader"] {
            background: #0d1e31 !important;
            color: var(--text) !important;
            border-color: rgba(107,138,172,0.14) !important;
        }
        div[data-testid="stDataFrame"] div[role="columnheader"] {
            background: #091828 !important;
            font-weight: 700 !important;
            font-size: 0.76rem !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        div[data-testid="stDataFrame"] canvas {
            background: #0d1e31 !important;
        }
        div[data-testid="stDataFrame"] [data-testid="glideDataEditor"] {
            background: #0d1e31 !important;
        }

        /* ── Metrics ─────────────────────────────────────────── */
        [data-testid="stMetric"] {
            background: var(--panel) !important;
            border: 1px solid var(--line) !important;
            border-radius: 14px !important;
            padding: 0.9rem 1rem !important;
        }
        [data-testid="stMetricLabel"] { color: var(--muted) !important; font-size: 0.78rem !important; }
        [data-testid="stMetricValue"] { color: var(--text) !important; }
        [data-testid="stMetricDelta"] { font-size: 0.82rem !important; }

        /* ── Scrollbar ───────────────────────────────────────── */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: rgba(8,17,28,0.5); }
        ::-webkit-scrollbar-thumb { background: rgba(77,212,172,0.25); border-radius: 99px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(77,212,172,0.45); }

        /* ── App shell ───────────────────────────────────────── */
        .app-shell {
            background: linear-gradient(145deg, rgba(16,32,52,0.95), rgba(9,18,30,0.97));
            border: 1px solid rgba(107,138,172,0.22);
            border-top: 1px solid rgba(77,212,172,0.18);
            border-radius: 20px;
            padding: 1.2rem 1.4rem 1.3rem;
            box-shadow: var(--shadow);
            backdrop-filter: blur(14px);
            margin-bottom: 1.2rem;
        }
        .notice {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(77,212,172,0.10);
            color: #a7f3d0;
            border: 1px solid rgba(77,212,172,0.22);
            border-radius: 999px;
            padding: 0.4rem 0.85rem;
            font-size: 0.82rem;
            font-weight: 600;
            letter-spacing: 0.02em;
        }
        .minor-note {
            color: var(--muted);
            font-size: 0.88rem;
            line-height: 1.5;
        }

        /* ── Summary cards ───────────────────────────────────── */
        .summary-card {
            background: linear-gradient(150deg, rgba(16,30,48,0.97), rgba(11,22,38,0.98));
            border: 1px solid rgba(107,138,172,0.20);
            border-radius: 18px;
            padding: 1.05rem 1.15rem;
            min-height: 122px;
            box-shadow: var(--shadow);
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
            position: relative;
            overflow: hidden;
        }
        .summary-card::before {
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, var(--accent), var(--accent-2));
            opacity: 0.55;
            border-radius: 18px 18px 0 0;
        }
        .summary-label {
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.09em;
            font-size: 0.7rem;
            font-weight: 700;
        }
        .summary-value {
            color: var(--text);
            font-size: 1.55rem;
            font-weight: 700;
            margin-top: 0.3rem;
            line-height: 1.15;
            letter-spacing: -0.01em;
        }
        .summary-meta {
            color: var(--muted);
            font-size: 0.82rem;
            margin-top: 0.4rem;
            line-height: 1.4;
        }

        /* ── Detail panel ────────────────────────────────────── */
        .detail-panel {
            background: linear-gradient(160deg, rgba(14,27,44,0.97), rgba(9,19,33,0.98));
            border: 1px solid rgba(107,138,172,0.20);
            border-left: 3px solid var(--accent);
            border-radius: 18px;
            padding: 1.2rem 1.25rem;
            box-shadow: var(--shadow);
        }
        .tool-table-shell {
            background: var(--panel-2);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 1rem 1.05rem;
            box-shadow: var(--shadow);
        }

        /* ── Mini stat ───────────────────────────────────────── */
        .mini-label {
            color: var(--muted);
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            font-weight: 700;
        }
        .mini-value {
            font-size: 1.12rem;
            font-weight: 700;
            color: var(--text);
            margin-top: 0.14rem;
            margin-bottom: 0.65rem;
        }

        /* ── Status badge ────────────────────────────────────── */
        .status-badge {
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.04em;
        }
        .status-rising  { background: rgba(16,185,129,0.16); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.28); }
        .status-stable  { background: rgba(100,116,139,0.16); color: #94a3b8; border: 1px solid rgba(100,116,139,0.28); }
        .status-falling { background: rgba(239,68,68,0.14); color: #fca5a5; border: 1px solid rgba(239,68,68,0.24); }
        .status-new     { background: rgba(59,130,246,0.16); color: #93c5fd; border: 1px solid rgba(59,130,246,0.28); }

        /* ── Dividers ────────────────────────────────────────── */
        hr { border-color: var(--line) !important; }

        /* ── Bubble chart legend ─────────────────────────────── */
        .bubble-legend {
            display: flex;
            gap: 1.2rem;
            flex-wrap: wrap;
            padding: 0.5rem 0.2rem 0.1rem;
            justify-content: center;
        }
        .bubble-legend-item {
            display: flex;
            align-items: center;
            gap: 0.45rem;
            font-size: 0.78rem;
            color: var(--muted);
            font-weight: 600;
        }
        .bubble-dot {
            width: 11px;
            height: 11px;
            border-radius: 50%;
            display: inline-block;
            flex-shrink: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _image_to_data_uri(path: str | Path | None) -> str:
    if not path:
        return ""
    path_obj = Path(path)
    if not path_obj.exists():
        return ""
    encoded = base64.b64encode(path_obj.read_bytes()).decode("ascii")
    suffix = path_obj.suffix.lower().lstrip(".") or "png"
    return f"data:image/{suffix};base64,{encoded}"


def render_header(title: str, notice: str, last_refresh: str, logo_path: str | Path | None = None) -> None:
    logo_markup = ""
    logo_uri = _image_to_data_uri(logo_path)
    if logo_uri:
        logo_markup = f'<img src="{logo_uri}" alt="8.2 Advisory" style="height:52px;width:auto;display:block;margin-bottom:0.85rem;" />'
    st.markdown(
        f"""
        <div class="app-shell">
          <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;flex-wrap:wrap;">
            <div>
              {logo_markup}
              <div style="font-size:1.95rem;font-weight:750;color:#e8f1fa;line-height:1.05;letter-spacing:-0.015em;">{title}</div>
              <div class="minor-note" style="margin-top:0.3rem;max-width:820px;">
                Monitor growing AI topics and product opportunities from public proxy signals — Reddit, Hacker News, GitHub, and Google Trends.
              </div>
              <div style="margin-top:0.8rem;" class="notice">⚡ {notice}</div>
            </div>
            <div style="text-align:right;color:#7a9ab8;font-size:0.85rem;padding-top:0.2rem;">
              <div style="text-transform:uppercase;letter-spacing:0.09em;font-size:0.68rem;font-weight:700;color:#5a7a96;">Last refresh</div>
              <div style="font-size:0.96rem;color:#c8ddf0;font-weight:700;margin-top:0.22rem;">{last_refresh}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_summary_cards(summary_cards: list[dict]) -> None:
    cols = st.columns(len(summary_cards))
    for col, card in zip(cols, summary_cards):
        col.markdown(
            f"""
            <div class="summary-card">
              <div class="summary-label">{card['label']}</div>
              <div class="summary-value">{card['value']}</div>
              <div class="summary-meta">{card['meta']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_bubble_chart(topics: pd.DataFrame, selected_topic: str | None = None, height: int = 660) -> None:
    if topics.empty:
        st.info("No topics are available for the bubble chart.")
        return

    chart_df = topics.copy()
    marker_line_width = [3.2 if t == selected_topic else 1.2 for t in chart_df["topic"]]
    marker_line_color = ["#f3f7fb" if t == selected_topic else "#1a3050" for t in chart_df["topic"]]
    marker_size = [max(18.0, min(82.0, (v ** 0.5) * 7.8)) for v in chart_df["total_hits"]]

    fig = go.Figure(
        data=[
            go.Scatter(
                x=chart_df["growth_7d_pct"],
                y=chart_df["relevance_score"],
                mode="markers",
                customdata=chart_df[["topic", "total_hits", "status_flag", "growth_7d_pct", "tool_opportunity_score"]].to_numpy(),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Hit volume: %{customdata[1]:.0f}<br>"
                    "7d growth: %{customdata[3]:.1f}%<br>"
                    "Opportunity: %{customdata[4]:.0f}/100"
                    "<extra></extra>"
                ),
                marker=dict(
                    size=marker_size,
                    color=[STATUS_COLORS.get(v, "#64748b") for v in chart_df["status_flag"]],
                    opacity=0.84,
                    line=dict(width=marker_line_width, color=marker_line_color),
                ),
            )
        ]
    )
    fig.update_layout(
        title=dict(
            text="Topic Momentum Map",
            font=dict(size=15, color="#c8ddf0", family="IBM Plex Sans, sans-serif"),
            x=0.02,
        ),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(13,27,46,0.90)",
        font=dict(color="#b8ccdf", family="IBM Plex Sans, Inter, sans-serif", size=11),
        margin=dict(l=30, r=24, t=54, b=30),
        dragmode=False,
        showlegend=False,
        hoverlabel=dict(
            bgcolor="#0e1e31",
            bordercolor="#2d4a68",
            font=dict(color="#e2eaf3", size=12, family="IBM Plex Sans, sans-serif"),
        ),
    )
    fig.update_xaxes(
        title=dict(text="7-day growth rate (%)", font=dict(size=10.5, color="#7a9ab8")),
        zeroline=True, zerolinecolor="rgba(77,212,172,0.22)", zerolinewidth=1.5,
        gridcolor="rgba(30,55,82,0.7)", tickfont=dict(size=9.5, color="#6a8aab"),
    )
    fig.update_yaxes(
        title=dict(text="AI tool opportunity score", font=dict(size=10.5, color="#7a9ab8")),
        range=[0, 102],
        gridcolor="rgba(30,55,82,0.7)", tickfont=dict(size=9.5, color="#6a8aab"),
    )

    import json as _json
    sizes_json = _json.dumps([s / 2 for s in marker_size])  # radii in Plotly marker units

    plot_html = pio.to_html(
        fig,
        include_plotlyjs=True,
        full_html=False,
        div_id="ai-proxy-bubble",
        config={"responsive": True, "displayModeBar": False, "scrollZoom": False},
    )

    legend_items = "".join(
        f'<div class="blg-item">'
        f'<span class="blg-dot" style="background:{color};box-shadow:0 0 7px {color}66;"></span>'
        f'{STATUS_LABELS[status]}</div>'
        for status, color in STATUS_COLORS.items()
    )

    html_block = f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
    html, body {{ margin:0; padding:0; background:transparent; overflow:hidden;
                  font-family:"IBM Plex Sans",Inter,sans-serif; }}
    #chart-wrap {{ position:relative; width:100%; height:{height}px; cursor:default; }}
    .blg {{ display:flex;gap:0.75rem;flex-wrap:wrap;padding:0.1rem 0.5rem 0;
            justify-content:center; }}
    .blg-item {{ display:flex;align-items:center;gap:0.42rem;font-size:0.74rem;
                 color:#7a9ab8;font-weight:600;
                 font-family:"IBM Plex Sans",sans-serif; }}
    .blg-dot {{ width:10px;height:10px;border-radius:50%;display:inline-block;flex-shrink:0; }}
    </style>

    <div id="chart-wrap">
      {plot_html}
    </div>
    <div class="blg">{legend_items}</div>

    <script>
    (function() {{
      // ── Collapse the Streamlit iframe gap ────────────────────────────────
      try {{
        window.parent.document.querySelectorAll('iframe').forEach(function(f) {{
          if (f.contentWindow === window) {{
            f.style.marginBottom = '-2.5rem';
            f.style.display = 'block';
            var p = f.parentElement;
            if (p) {{ p.style.marginBottom = '0'; p.style.paddingBottom = '0'; }}
          }}
        }});
      }} catch(e) {{}}

      var wrap = document.getElementById("chart-wrap");

      // Bubble radii in SVG px (Plotly marker.size is diameter in pt ≈ px at 96dpi)
      var radii = {sizes_json};

      // ── Per-bubble state ─────────────────────────────────────────────────
      // Use SVG setAttribute — CSS style.transform overrides Plotly's SVG
      // transform attribute, sending bubbles to (0,0).
      var state = new WeakMap();

      function getState(el, idx) {{
        if (!state.has(el)) {{
          var orig = el.getAttribute('transform') || '';
          var m = orig.match(/translate\(\s*([-\d.]+)[,\s]+([-\d.]+)\s*\)/);
          state.set(el, {{
            ox: m ? parseFloat(m[1]) : 0,
            oy: m ? parseFloat(m[2]) : 0,
            x: 0, y: 0, vx: 0, vy: 0,
            r: (radii[idx] !== undefined ? radii[idx] : 18),
            ax: (Math.random() * 2 - 1) * 70,   // drift amplitude ±70 px
            ay: (Math.random() * 2 - 1) * 55,
            fx: 0.40 + Math.random() * 0.45,
            fy: 0.35 + Math.random() * 0.40,
            px: Math.random() * Math.PI * 2,
            py: Math.random() * Math.PI * 2,
          }});
        }}
        return state.get(el);
      }}

      // ── Physics constants ────────────────────────────────────────────────
      var DAMPING      = 0.96;   // less friction → faster, longer motion
      var SPRING_DRIFT = 0.060;
      var SPRING_HOME  = 0.14;
      var RESTITUTION  = 0.80;   // energy kept after collision (0=inelastic, 1=elastic)

      var hovering   = false;
      var allBubbles = [];
      var scanStamp  = 0;

      function scanBubbles() {{
        allBubbles = Array.from(document.querySelectorAll('g.points > path'));
      }}

      function physicsStep(now) {{
        if (now - scanStamp > 1500) {{ scanBubbles(); scanStamp = now; }}
        var t = now / 1000;
        var n = allBubbles.length;

        // ── 1. Apply spring force toward drift target (or home) ─────────────
        for (var i = 0; i < n; i++) {{
          var el = allBubbles[i];
          var s  = getState(el, i);
          var tx, ty, k;
          if (hovering) {{
            tx = 0; ty = 0; k = SPRING_HOME;
          }} else {{
            tx = s.ax * Math.sin(s.fx * t + s.px);
            ty = s.ay * Math.sin(s.fy * t + s.py);
            k  = SPRING_DRIFT;
          }}
          s.vx = (s.vx + (tx - s.x) * k) * DAMPING;
          s.vy = (s.vy + (ty - s.y) * k) * DAMPING;
          s.x += s.vx;
          s.y += s.vy;
        }}

        // ── 2. Collision detection & response (O(n²), fine for n ≤ 30) ──────
        for (var i = 0; i < n - 1; i++) {{
          var si = getState(allBubbles[i], i);
          for (var j = i + 1; j < n; j++) {{
            var sj = getState(allBubbles[j], j);
            var dx   = (sj.ox + sj.x) - (si.ox + si.x);
            var dy   = (sj.oy + sj.y) - (si.oy + si.y);
            var dist = Math.sqrt(dx * dx + dy * dy);
            var minD = si.r + sj.r;
            if (dist < minD && dist > 0.01) {{
              // Unit collision normal
              var nx = dx / dist, ny = dy / dist;
              // Relative velocity along normal
              var dvn = (sj.vx - si.vx) * nx + (sj.vy - si.vy) * ny;
              if (dvn < 0) {{   // only resolve if approaching
                var imp = dvn * (1 + RESTITUTION) * 0.5;
                si.vx += imp * nx;  si.vy += imp * ny;
                sj.vx -= imp * nx;  sj.vy -= imp * ny;
              }}
              // Positional correction — push apart so they don't overlap
              var corr = (minD - dist) * 0.5;
              si.x -= corr * nx;  si.y -= corr * ny;
              sj.x += corr * nx;  sj.y += corr * ny;
            }}
          }}
        }}

        // ── 3. Write transforms ──────────────────────────────────────────────
        for (var i = 0; i < n; i++) {{
          var s = getState(allBubbles[i], i);
          allBubbles[i].setAttribute('transform',
            'translate(' + (s.ox + s.x).toFixed(1) + ',' + (s.oy + s.y).toFixed(1) + ')');
        }}

        requestAnimationFrame(physicsStep);
      }}

      // ── Start loop after a short delay so Plotly has rendered ────────────
      setTimeout(function() {{
        scanBubbles();
        scanStamp = performance.now();
        requestAnimationFrame(physicsStep);
      }}, 300);

      // ── Hover: snap home; leave: drift again ─────────────────────────────
      wrap.addEventListener('mouseenter', function() {{ hovering = true;  }});
      wrap.addEventListener('mouseleave', function() {{ hovering = false; }});

    }})();
    </script>
    """
    components.html(html_block, height=height + 20, scrolling=False)


def render_topic_table(topics: pd.DataFrame, selected_topic: str | None):
    if topics.empty:
        st.info("No topics match the current filters.")
        return selected_topic

    display = topics.copy()
    display.insert(0, "Focus", display["topic"].map(lambda value: "●" if value == selected_topic else ""))
    display["Total hits"] = display["total_hits"].map(lambda value: f"{value:,.0f}")
    display["Score"] = display["tool_opportunity_score"].map(lambda value: f"{value:,.0f}/100")
    display["Last updated"] = pd.to_datetime(display["last_updated"], utc=True).dt.strftime("%Y-%m-%d")
    display = display[
        [
            "Focus",
            "topic",
            "Total hits",
            "Score",
            "trend_series_30d",
            "category",
            "Last updated",
            "status_flag",
        ]
    ].rename(
        columns={
            "topic": "Topic",
            "trend_series_30d": "1m trend",
            "category": "Category",
            "status_flag": "Status",
        }
    )
    selected = selected_topic
    try:
        event = st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="topic_table",
            height=530,
            column_config={
                "1m trend": st.column_config.LineChartColumn("1m trend", y_min=0.0, y_max=None, width="medium"),
            },
        )
        rows = event.selection.get("rows", []) if event else []
        if rows:
            selected = topics.iloc[rows[0]]["topic"]
    except TypeError:
        fallback = display.copy()
        fallback["1m trend"] = topics["sparkline_30d"]
        st.dataframe(fallback, use_container_width=True, hide_index=True, height=530)
    return selected


def _status_badge(status: str) -> str:
    label = STATUS_LABELS.get(status, status.title())
    cls   = f"status-{status}"
    return f'<span class="status-badge {cls}">{label}</span>'


def render_detail_panel(topic_row: pd.Series, detail_mentions: pd.DataFrame) -> None:
    st.markdown('<div class="detail-panel">', unsafe_allow_html=True)

    status = topic_row.get("status_flag", "stable")
    badge  = _status_badge(status)
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:0.7rem;margin-bottom:0.2rem;">'
        f'<span style="font-size:1.25rem;font-weight:700;color:#e8f1fa;">{topic_row["topic"]}</span>'
        f'{badge}</div>',
        unsafe_allow_html=True,
    )
    st.caption(f"{topic_row['category']} · Last updated {pd.to_datetime(topic_row['last_updated'], utc=True).strftime('%Y-%m-%d')}")

    stat_cols = st.columns(4)
    stat_cols[0].markdown(f'<div class="mini-label">Total hits</div><div class="mini-value">{topic_row["total_hits"]:.0f}</div>', unsafe_allow_html=True)
    stat_cols[1].markdown(f'<div class="mini-label">7d growth</div><div class="mini-value">{topic_row["growth_7d_pct"]:+.1f}%</div>', unsafe_allow_html=True)
    stat_cols[2].markdown(f'<div class="mini-label">Source diversity</div><div class="mini-value">{topic_row["source_diversity_count"]} sources</div>', unsafe_allow_html=True)
    stat_cols[3].markdown(f'<div class="mini-label">Opportunity score</div><div class="mini-value">{topic_row["tool_opportunity_score"]:.0f}/100</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"**Topic summary**  \n{topic_row['summary']}")
    if "service_fit" in topic_row and topic_row["service_fit"]:
        st.markdown(f"**8p2 service fit**  \n{topic_row['service_fit']}")
    st.markdown(
        f"**Proxy trend**  \n"
        f"7-day growth `{topic_row['growth_7d_pct']:+.1f}%` · 30-day trend `{topic_row['trend_30d_pct']:+.1f}%` · "
        f"sources: `{topic_row['source_breakdown']}`."
    )
    if "pulse_signal" in topic_row and topic_row["pulse_signal"]:
        st.markdown(f"**Daily Pulse cross-check**  \n{topic_row['pulse_signal']}")
    st.markdown(f"**Suggested 8p2 product / tool idea**  \n{topic_row['tool_idea']}")
    st.markdown(f"**Risk / data notes**  \n{topic_row['risk_notes']}")

    sample_mentions = detail_mentions.sort_values(["weighted_hits", "published_at"], ascending=[False, False]).head(8)
    if not sample_mentions.empty:
        st.markdown("**Sample source mentions**")
        for item in sample_mentions.itertuples(index=False):
            date_str = pd.to_datetime(item.published_at, utc=True).strftime("%Y-%m-%d")
            st.markdown(f"- [{item.title}]({item.url}) · `{item.source}` · {date_str}")
            if item.snippet:
                st.caption(item.snippet[:220])
    st.markdown("</div>", unsafe_allow_html=True)


def render_score_explainer(topic_row: pd.Series) -> None:
    st.markdown('<div class="detail-panel">', unsafe_allow_html=True)
    st.markdown("#### Score model")
    st.caption("Heuristic, proxy-based scoring — does not use private ChatGPT or Claude query data.")
    breakdown = pd.DataFrame(
        [
            {"Component": "Growth contribution",       "Calculation": "35 % of normalised 7-day growth score",         "This topic": f"{topic_row['score_growth_component']:.1f}"},
            {"Component": "Volume contribution",       "Calculation": "20 % of percentile rank on total weighted hits", "This topic": f"{topic_row['score_volume_component']:.1f}"},
            {"Component": "Source diversity",          "Calculation": "20 % of distinct source-family coverage score",  "This topic": f"{topic_row['score_diversity_component']:.1f}"},
            {"Component": "Commercial intent",         "Calculation": "25 % of keyword-based commercial intent score",  "This topic": f"{topic_row['score_commercial_component']:.1f}"},
            {"Component": "New topic bonus",           "Calculation": "+10 if first seen within 14 days",               "This topic": f"{topic_row['new_topic_bonus']:.1f}"},
        ]
    )
    st.markdown(_dark_html_table(breakdown, max_height="220px"), unsafe_allow_html=True)
    st.markdown(
        "**Weighted hits:** `hits × source_weight × (1 + log1p(engagement) / 8)`  \n"
        "**7-day growth:** `((recent_7d + 1) / (prior_7d + 1) − 1) × 100`  \n"
        "**30-day trend:** `((recent_30d + 1) / (prior_30d + 1) − 1) × 100`"
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_tool_ideas_table(topics: pd.DataFrame) -> None:
    st.markdown('<div class="tool-table-shell">', unsafe_allow_html=True)
    st.markdown("#### Suggested 8p2 product / tool ideas")
    tool_rows = topics[
        ["topic", "category", "service_fit", "pulse_signal", "tool_opportunity_score", "commercial_intent_score", "status_flag", "tool_idea"]
    ].copy()
    tool_rows["Tool score"] = tool_rows["tool_opportunity_score"].map(lambda v: f"{v:.0f}/100")
    tool_rows["Commercial"] = tool_rows["commercial_intent_score"].map(lambda v: f"{v:.0f}/100")
    tool_rows["Status"]     = tool_rows["status_flag"].map(lambda v: STATUS_LABELS.get(v, v.title()))
    tool_rows = tool_rows.rename(columns={
        "topic":       "Topic",
        "category":    "Category",
        "service_fit": "8p2 service fit",
        "pulse_signal":"Daily Pulse signal",
        "tool_idea":   "Suggested tool idea",
    })
    tool_rows = tool_rows[["Topic", "Category", "8p2 service fit", "Daily Pulse signal", "Tool score", "Commercial", "Status", "Suggested tool idea"]]
    st.markdown(_dark_html_table(tool_rows, max_height="380px"), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
