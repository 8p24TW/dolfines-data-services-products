"""
daily_chart_factory.py — Charts for the PVPAT Daily Report
===========================================================
Produces 5 chart types, each saved to a temporary PNG byte buffer.
All charts use the same Dolfines colour palette as the main report.
"""

from __future__ import annotations

import io
import warnings
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── Colours ───────────────────────────────────────────────────────────────
_BLUE    = "#003D6B"
_ORANGE  = "#F07820"
_GREEN   = "#2E8B57"
_RED     = "#C0392B"
_AMBER   = "#E67E22"
_GREY    = "#B0B8C1"
_LGREY   = "#EAF0F6"
_WHITE   = "#FFFFFF"

matplotlib.rcParams.update({
    "font.family":     "sans-serif",
    "font.sans-serif": ["Open Sans", "Arial", "DejaVu Sans"],
    "axes.titlesize":  9,
    "axes.labelsize":  8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "figure.facecolor": _WHITE,
    "axes.facecolor":   _WHITE,
    "axes.spines.top":  False,
    "axes.spines.right": False,
})


def _to_png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ─────────────────────────────────────────────────────────────────────────────
# 1. DAILY IRRADIANCE PROFILE
# ─────────────────────────────────────────────────────────────────────────────

def chart_daily_irradiance(irradiance: dict,
                           hourly_kwh: "pd.Series | None" = None) -> bytes:
    """GHI line/fill (left axis) + hourly AC production bars (right axis)."""
    import matplotlib.dates as mdates

    ts: pd.Series = irradiance["timeseries"]
    fig, ax = plt.subplots(figsize=(7.0, 2.8), constrained_layout=True)

    if ts.empty:
        ax.text(0.5, 0.5, "No irradiance data available",
                ha="center", va="center", transform=ax.transAxes,
                color=_GREY, fontsize=9)
        return _to_png(fig)

    # ── Left axis: GHI line ───────────────────────────────────────────────
    ax.fill_between(ts.index, ts.values, alpha=0.18, color=_ORANGE)
    ax.plot(ts.index, ts.values, color=_ORANGE, lw=1.4, label="GHI (W/m²)")
    ax.axhline(1000, color=_GREY, ls="--", lw=0.8, label="STC 1 000 W/m²")
    ax.set_ylabel("GHI  (W/m²)", color=_ORANGE)
    ax.tick_params(axis="y", labelcolor=_ORANGE)
    ax.set_ylim(bottom=0)

    # ── Right axis: hourly AC production dotted line ──────────────────────
    has_prod = hourly_kwh is not None and not hourly_kwh.empty
    if has_prod:
        ax2 = ax.twinx()
        # Plot at mid-hour for a cleaner line
        mid_index = hourly_kwh.index + pd.Timedelta(minutes=30)
        ax2.plot(mid_index, hourly_kwh.values,
                 color=_BLUE, lw=1.6, ls=":", marker="o",
                 markersize=3.5, label="Prod. (kWh/h)", zorder=3)
        ax2.set_ylabel("AC Production  (kWh/h)", color=_BLUE)
        ax2.tick_params(axis="y", labelcolor=_BLUE)
        ax2.set_ylim(bottom=0)
        ax2.spines["right"].set_visible(True)

    # ── X axis ───────────────────────────────────────────────────────────
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    ax.tick_params(axis="x", rotation=0)

    # ── Legend ───────────────────────────────────────────────────────────
    handles, labels = ax.get_legend_handles_labels()
    if has_prod:
        h2, l2 = ax2.get_legend_handles_labels()
        handles += h2
        labels  += l2
    ax.legend(handles, labels, loc="upper left", fontsize=7, framealpha=0.6)

    insol = irradiance["insolation_kwh_m2"]
    total_kwh = hourly_kwh.sum() if has_prod else 0
    title = (f"Irradiance & Production  |  Insolation: {insol:.2f} kWh/m²  |  "
             f"Peak GHI: {irradiance['peak_ghi']:.0f} W/m²")
    if has_prod:
        title += f"  |  Daily output: {total_kwh:,.0f} kWh"
    ax.set_title(title, fontsize=8.5, pad=4)

    return _to_png(fig)


# ─────────────────────────────────────────────────────────────────────────────
# 2. PER-INVERTER SPECIFIC YIELD BAR CHART
# ─────────────────────────────────────────────────────────────────────────────

def chart_per_inverter_yield(per_inv: pd.DataFrame, pr_target: float) -> bytes:
    """Horizontal bar chart: specific yield per inverter, colour-coded by PR."""
    fig, ax = plt.subplots(figsize=(7.0, max(3.0, len(per_inv) * 0.22 + 0.8)),
                           constrained_layout=True)

    if per_inv.empty:
        ax.text(0.5, 0.5, "No inverter data", ha="center", va="center",
                transform=ax.transAxes, color=_GREY)
        return _to_png(fig)

    df = per_inv.sort_values("inverter").reset_index(drop=True)
    colors = [_GREEN if r else _RED for r in df["pr_ok"]]
    y = np.arange(len(df))

    ax.barh(y, df["spec_yield"], color=colors, alpha=0.85, height=0.65)

    # Reference line — target yield
    if pr_target and "insolation_kwh_m2" in per_inv.columns:
        pass  # computed externally; just annotate the bars

    ax.set_yticks(y)
    ax.set_yticklabels(df["inverter"], fontsize=6.5)
    ax.set_xlabel("Specific Yield  (kWh/kWp)")
    ax.set_title("Per-Inverter Specific Yield", fontsize=8.5, pad=4)

    # Colour legend
    patches = [
        mpatches.Patch(color=_GREEN, alpha=0.85, label="≥ Target PR"),
        mpatches.Patch(color=_RED,   alpha=0.85, label="< Target PR"),
    ]
    ax.legend(handles=patches, loc="lower right", fontsize=7)

    # Value labels
    for i, row in df.iterrows():
        ax.text(row["spec_yield"] + 0.01, i,
                f"{row['spec_yield']:.2f}", va="center", fontsize=5.8)

    ax.invert_yaxis()
    return _to_png(fig)


# ─────────────────────────────────────────────────────────────────────────────
# 3. PER-INVERTER AVAILABILITY BAR CHART
# ─────────────────────────────────────────────────────────────────────────────

def chart_per_inverter_availability(per_inv: pd.DataFrame) -> bytes:
    """Horizontal bar chart: availability % per inverter."""
    fig, ax = plt.subplots(figsize=(7.0, max(3.0, len(per_inv) * 0.22 + 0.8)),
                           constrained_layout=True)

    if per_inv.empty:
        ax.text(0.5, 0.5, "No inverter data", ha="center", va="center",
                transform=ax.transAxes, color=_GREY)
        return _to_png(fig)

    df = per_inv.sort_values("inverter").reset_index(drop=True)
    y = np.arange(len(df))
    avail_pct = df["availability"] * 100
    colors = [_GREEN if v >= 85 else (_AMBER if v > 0 else _RED) for v in avail_pct]

    ax.barh(y, avail_pct, color=colors, alpha=0.85, height=0.65)
    ax.axvline(100, color=_GREY, ls="--", lw=0.8)
    ax.axvline(85, color=_AMBER, ls=":", lw=0.8, label="85% threshold")
    ax.set_xlim(0, 105)
    ax.set_yticks(y)
    ax.set_yticklabels(df["inverter"], fontsize=6.5)
    ax.set_xlabel("Availability  (%)")
    ax.set_title("Per-Inverter Availability", fontsize=8.5, pad=4)
    ax.legend(loc="lower right", fontsize=7)

    for i, v in enumerate(avail_pct):
        ax.text(min(v + 0.5, 101), i, f"{v:.0f}%", va="center", fontsize=5.8)

    ax.invert_yaxis()
    return _to_png(fig)


# ─────────────────────────────────────────────────────────────────────────────
# 4. DAILY PR BAR CHART (per inverter, vs target line)
# ─────────────────────────────────────────────────────────────────────────────

def chart_per_inverter_pr(per_inv: pd.DataFrame, pr_target: float) -> bytes:
    """Horizontal bar: PR per inverter vs target."""
    fig, ax = plt.subplots(figsize=(7.0, max(3.0, len(per_inv) * 0.22 + 0.8)),
                           constrained_layout=True)

    if per_inv.empty:
        ax.text(0.5, 0.5, "No inverter data", ha="center", va="center",
                transform=ax.transAxes, color=_GREY)
        return _to_png(fig)

    df = per_inv.sort_values("inverter").reset_index(drop=True)
    y = np.arange(len(df))
    pr_pct = df["pr"] * 100
    colors = [_GREEN if r else _RED for r in df["pr_ok"]]

    ax.barh(y, pr_pct, color=colors, alpha=0.85, height=0.65)
    ax.axvline(pr_target * 100, color=_BLUE, ls="--", lw=1.0,
               label=f"Target {pr_target*100:.0f}%")
    ax.set_xlim(0, 110)
    ax.set_yticks(y)
    ax.set_yticklabels(df["inverter"], fontsize=6.5)
    ax.set_xlabel("Performance Ratio  (%)")
    ax.set_title("Per-Inverter Performance Ratio vs Target", fontsize=8.5, pad=4)
    ax.legend(loc="lower right", fontsize=7)

    for i, v in enumerate(pr_pct):
        ax.text(min(v + 0.3, 107), i, f"{v:.1f}%", va="center", fontsize=5.8)

    ax.invert_yaxis()
    return _to_png(fig)


# ─────────────────────────────────────────────────────────────────────────────
# 5. DAILY ENERGY LOSS WATERFALL
# ─────────────────────────────────────────────────────────────────────────────

def chart_daily_waterfall(waterfall: list[dict]) -> bytes:
    """Waterfall chart: theoretical → losses → measured output."""
    fig, ax = plt.subplots(figsize=(7.0, 3.2), constrained_layout=True)

    labels = [w["label"] for w in waterfall]
    values = [w["value"] for w in waterfall]
    bottoms = [w["bottom"] for w in waterfall]
    types   = [w["type"] for w in waterfall]

    color_map = {"base": _BLUE, "loss": _RED, "result": _GREEN}
    bar_colors = [color_map.get(t, _GREY) for t in types]
    alphas = [0.88 if t != "loss" else 0.75 for t in types]

    for i, (lbl, val, bot, col, alp) in enumerate(
            zip(labels, values, bottoms, bar_colors, alphas)):
        ax.bar(i, abs(val), bottom=bot, color=col, alpha=alp, width=0.55,
               edgecolor="white", linewidth=0.5)
        # Value annotation
        top = bot + abs(val)
        label_y = top + max(abs(v) for v in values) * 0.02
        ax.text(i, label_y, f"{abs(val):,.0f}", ha="center", va="bottom",
                fontsize=7, fontweight="600" if types[i] in ("base","result") else "400")

    # Connector lines
    cum = 0.0
    for i, w in enumerate(waterfall[:-1]):
        if w["type"] == "base":
            cum = w["value"]
        elif w["type"] == "loss":
            cum += w["value"]
        else:
            cum = w["value"]
        next_bot = waterfall[i + 1]["bottom"]
        ax.plot([i + 0.28, i + 0.72], [cum, cum],
                color=_GREY, lw=0.8, ls="--")

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=7.5)
    ax.set_ylabel("Energy  (kWh)")
    ax.set_title("Daily Energy Loss Waterfall", fontsize=8.5, pad=4)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: f"{x:,.0f}"))

    patches = [
        mpatches.Patch(color=_BLUE,  alpha=0.88, label="Theoretical"),
        mpatches.Patch(color=_RED,   alpha=0.75, label="Loss"),
        mpatches.Patch(color=_GREEN, alpha=0.88, label="Measured"),
    ]
    ax.legend(handles=patches, loc="upper right", fontsize=7)

    return _to_png(fig)
