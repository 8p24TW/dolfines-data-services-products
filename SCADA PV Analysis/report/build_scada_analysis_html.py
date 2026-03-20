"""
build_scada_analysis_html.py  —  SCADA Daily Performance Analysis HTML report
==============================================================================
Generates a single self-contained HTML file (charts as base64 PNG) using the
exact visual style of PVPAT_SCADA_Analysis_Report.

Sections
--------
  1. Cover page
  2. Data quality  —  completeness heatmap
  3. Performance overview  —  monthly energy, irradiation, PR
  4. Per-inverter specific yield  —  heatmap
  5. Energy loss waterfall
  6. Action punchlist

Entry point
-----------
  html_path = build_scada_analysis_html(site_cfg, data_dir, out_path)
"""
from __future__ import annotations

import base64
import io
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

_HERE = Path(__file__).parent
_ROOT = _HERE.parent          # SCADA PV Analysis/

import re as _re

def _natural_key(s: str) -> list:
    """Sort key for natural ordering: BJ1, BJ2 … BJ21 instead of BJ1, BJ10, BJ11 …"""
    return [int(t) if t.isdigit() else t.lower() for t in _re.split(r"(\d+)", str(s))]

# ── Design tokens (match style_tokens.py) ────────────────────────────────────
_T = {
    "navy":    "#0B2A3D",
    "orange":  "#F39200",
    "slate":   "#3E516C",
    "text":    "#1F2933",
    "muted":   "#6B7785",
    "bg":      "#F4F6F8",
    "border":  "#D9E0E6",
    "green":   "#70AD47",
    "amber":   "#C98A00",
    "red":     "#C62828",
    "white":   "#FFFFFF",
}

# ── CSS: load verbatim from the same static files the comprehensive report uses ──
_ROOT_VARS = """
:root {
  --color-primary:   #0B2A3D;
  --color-accent:    #F39200;
  --color-secondary: #3E516C;
  --color-indigo:    #27275A;
  --color-text:      #1F2933;
  --color-muted:     #6B7785;
  --color-bg:        #F4F6F8;
  --color-border:    #D9E0E6;
  --color-success:   #70AD47;
  --color-warning:   #C98A00;
  --color-danger:    #C62828;
  --font-sans: Aptos, Calibri, Arial, Helvetica, sans-serif;
  --page-margin-top: 12mm;
  --page-margin-right: 12mm;
  --page-margin-bottom: 14mm;
  --page-margin-left: 12mm;
}
"""

def _load_static_css() -> tuple[str, str]:
    """Read report.css and print.css from report/static/."""
    report_css = (_HERE / "static" / "report.css").read_text(encoding="utf-8")
    print_css  = (_HERE / "static" / "print.css").read_text(encoding="utf-8")
    return report_css, print_css


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────────────────────────────────────

def _load_xlsx_wide(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load wide-format Excel files (e.g. test_data.xlsx).
    Expects: date column, BJ*/inverter energy columns (kWh/interval), irr_sat column (W/m²).
    Returns (inv_long, irr_df) both ready for the analysis pipeline.
    """
    inv_frames, irr_frames = [], []
    for p in sorted(data_dir.glob("*.xlsx")):
        try:
            df = pd.read_excel(p)
            df.columns = [c.strip() for c in df.columns]
            # Find timestamp column
            time_col = next((c for c in df.columns
                             if c.lower() in ("date", "time", "time_udt", "datetime", "timestamp")), None)
            if time_col is None:
                continue
            df[time_col] = pd.to_datetime(df[time_col], dayfirst=True, errors="coerce")
            df = df.dropna(subset=[time_col])

            # Detect interval from timestamps
            ts_sorted = df[time_col].sort_values().unique()
            interval_h = 0.0
            if len(ts_sorted) > 1:
                interval_h = (pd.Timestamp(ts_sorted[1]) - pd.Timestamp(ts_sorted[0])).total_seconds() / 3600.0
            if interval_h <= 0:
                interval_h = 5 / 60.0

            # ── Inverter columns: any column matching BJ*, INV*, or similar numeric patterns ──
            inv_cols = [c for c in df.columns
                        if c != time_col and pd.api.types.is_numeric_dtype(df[c])
                        and any(c.upper().startswith(pfx) for pfx in ("BJ", "INV", "WR", "G", "UNIT"))]
            # Fallback: any numeric column that isn't a known non-inverter column
            if not inv_cols:
                skip = {"irr_sat", "irr", "eond", "month", "prond"}
                inv_cols = [c for c in df.columns
                            if c != time_col and pd.api.types.is_numeric_dtype(df[c])
                            and c.lower() not in skip
                            and not c.lower().startswith("pr")]

            if inv_cols:
                melted = df[[time_col] + inv_cols].melt(
                    id_vars=time_col, var_name="EQUIP", value_name="_energy_kwh")
                melted = melted.rename(columns={time_col: "Time_UDT"})
                melted["_energy_kwh"] = pd.to_numeric(melted["_energy_kwh"], errors="coerce").fillna(0.0)
                # Convert kWh/interval → kW (power) so downstream code works correctly
                melted["PAC"] = melted["_energy_kwh"] / interval_h
                inv_frames.append(melted[["Time_UDT", "EQUIP", "PAC"]])

            # ── Irradiance: prefer irr_sat (W/m² instantaneous) ──
            ghi_col = next((c for c in df.columns if c.lower() == "irr_sat"), None)
            if ghi_col is None:
                ghi_col = next((c for c in df.columns
                                if "irr" in c.lower() or "ghi" in c.lower()), None)
            if ghi_col:
                irr_df = df[[time_col, ghi_col]].copy()
                irr_df = irr_df.rename(columns={time_col: "Time_UDT", ghi_col: "GHI"})
                irr_df["GHI"] = pd.to_numeric(irr_df["GHI"], errors="coerce").fillna(0.0)
                irr_frames.append(irr_df)

        except Exception:
            continue

    inv = pd.concat(inv_frames, ignore_index=True) if inv_frames else pd.DataFrame()
    irr = pd.concat(irr_frames, ignore_index=True) if irr_frames else pd.DataFrame()
    return inv, irr


def _load_inv(data_dir: Path) -> pd.DataFrame:
    # Excel files take priority — if xlsx has inverter data, skip CSVs entirely
    xlsx_inv, _ = _load_xlsx_wide(data_dir)
    if not xlsx_inv.empty:
        xlsx_inv["Time_UDT"] = pd.to_datetime(xlsx_inv["Time_UDT"], dayfirst=True, errors="coerce")
        xlsx_inv = xlsx_inv.dropna(subset=["Time_UDT"])
        xlsx_inv["PAC"] = pd.to_numeric(xlsx_inv["PAC"], errors="coerce").fillna(0.0)
        return xlsx_inv

    frames = []
    for p in sorted(data_dir.glob("*.csv")):
        nl = p.stem.lower()
        if any(k in nl for k in ("irr", "ghi", "irradiance", "meteo")):
            continue
        try:
            df = pd.read_csv(p, sep=";", decimal=",", encoding="utf-8-sig", low_memory=False)
            df.columns = [c.strip() for c in df.columns]
            if "Time_UDT" not in df.columns:
                df = df.rename(columns={df.columns[0]: "Time_UDT"})
            eq  = next((c for c in df.columns if c.upper() in ("EQUIP","EQUIPMENT","INV","INVERTER")), None)
            pac = next((c for c in df.columns if c.upper() in ("PAC","P_AC","POWER","ACTIVE_POWER")), None)
            if eq  and eq  != "EQUIP": df = df.rename(columns={eq:  "EQUIP"})
            if pac and pac != "PAC":   df = df.rename(columns={pac: "PAC"})
            frames.append(df)
        except Exception:
            continue
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out["Time_UDT"] = pd.to_datetime(out["Time_UDT"], dayfirst=True, errors="coerce")
    out = out.dropna(subset=["Time_UDT"])
    if "PAC" in out.columns:
        out["PAC"] = pd.to_numeric(out["PAC"], errors="coerce").fillna(0.0)
    return out


def _load_irr(data_dir: Path) -> pd.DataFrame:
    # Excel files take priority — if xlsx has irradiance data, skip CSVs entirely
    _, xlsx_irr = _load_xlsx_wide(data_dir)
    if not xlsx_irr.empty:
        xlsx_irr["Time_UDT"] = pd.to_datetime(xlsx_irr["Time_UDT"], dayfirst=True, errors="coerce")
        xlsx_irr = xlsx_irr.dropna(subset=["Time_UDT"])
        xlsx_irr["GHI"] = pd.to_numeric(xlsx_irr["GHI"], errors="coerce").fillna(0.0)
        return xlsx_irr

    frames = []
    for p in sorted(data_dir.glob("*.csv")):
        try:
            df = pd.read_csv(p, sep=";", decimal=",", encoding="utf-8-sig", low_memory=False)
            df.columns = [c.strip() for c in df.columns]
            ghi_col = next((c for c in df.columns
                            if "ghi" in c.lower() or "irr" in c.lower() or "global" in c.lower()), None)
            if ghi_col is None:
                continue
            if "Time_UDT" not in df.columns:
                df = df.rename(columns={df.columns[0]: "Time_UDT"})
            if ghi_col != "GHI":
                df = df.rename(columns={ghi_col: "GHI"})
            frames.append(df[["Time_UDT", "GHI"]])
        except Exception:
            continue
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out["Time_UDT"] = pd.to_datetime(out["Time_UDT"], dayfirst=True, errors="coerce")
    out = out.dropna(subset=["Time_UDT"])
    out["GHI"] = pd.to_numeric(out["GHI"], errors="coerce").fillna(0.0)
    return out


def _normalise_ghi(irr: pd.DataFrame, interval_h: float) -> pd.DataFrame:
    """Convert Wh/m²-per-interval → W/m² instantaneous if values look like Wh."""
    if irr.empty or "GHI" not in irr.columns:
        return irr
    # Auto-detect interval from data
    ts = irr.set_index("Time_UDT")["GHI"].sort_index()
    if len(ts) > 1:
        interval_h = (ts.index[1] - ts.index[0]).total_seconds() / 3600.0
    ghi = irr["GHI"].clip(lower=0)
    if ghi.max() < 200 and ghi.max() > 0:
        irr = irr.copy()
        irr["GHI"] = ghi / interval_h   # Wh/interval → W/m²
    return irr


# ─────────────────────────────────────────────────────────────────────────────
# ANALYSIS HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _detect_interval(df: pd.DataFrame, fallback_min: int = 10) -> float:
    """Return actual data interval in hours, inferred from timestamps."""
    if df.empty or "Time_UDT" not in df.columns:
        return fallback_min / 60.0
    ts = df["Time_UDT"].dropna().sort_values().unique()
    if len(ts) > 1:
        diff = (pd.Timestamp(ts[1]) - pd.Timestamp(ts[0])).total_seconds()
        if 0 < diff <= 3600:
            return diff / 3600.0
    return fallback_min / 60.0


def _choose_freq(inv: pd.DataFrame) -> str:
    """Return granularity for heatmap columns: 'interval', 'D', or 'ME'."""
    if inv.empty or "Time_UDT" not in inv.columns:
        return "D"
    span_days = (inv["Time_UDT"].max() - inv["Time_UDT"].min()).total_seconds() / 86400
    if span_days <= 3:
        return "interval"
    elif span_days <= 90:
        return "D"
    else:
        return "ME"


def _completeness_pivot(inv: pd.DataFrame, interval_h: float, freq: str = "D") -> pd.DataFrame:
    if inv.empty or "EQUIP" not in inv.columns:
        return pd.DataFrame()
    inv = inv.copy()
    if freq == "interval":
        slot_min = max(1, round(interval_h * 60))
        inv["slot"] = inv["Time_UDT"].dt.floor(f"{slot_min}min")
        all_slots = sorted(inv["slot"].unique())
        all_equip = sorted(inv["EQUIP"].unique())
        pres = inv.groupby(["EQUIP", "slot"])["PAC"].count().clip(0, 1)
        idx = pd.MultiIndex.from_product([all_equip, all_slots], names=["EQUIP", "slot"])
        pres = pres.reindex(idx, fill_value=0).reset_index()
        pres.columns = ["EQUIP", "slot", "pct"]
        pivot = pres.pivot(index="EQUIP", columns="slot", values="pct")
        pivot.columns = [pd.Timestamp(c).strftime("%H:%M") for c in pivot.columns]
        return pivot
    elif freq == "ME":
        inv["period"] = inv["Time_UDT"].dt.to_period("M").astype(str)
        inv["date"] = inv["Time_UDT"].dt.date
        all_days = inv.groupby("period")["date"].nunique()
        days_inv = inv.groupby(["EQUIP", "period"])["date"].nunique().reset_index()
        days_inv["pct"] = days_inv.apply(lambda r: r["date"] / all_days[r["period"]], axis=1)
        return days_inv.pivot(index="EQUIP", columns="period", values="pct").clip(0, 1)
    else:  # "D"
        expected = round(24 / interval_h)
        inv["date"] = inv["Time_UDT"].dt.date
        counts = inv.groupby(["EQUIP", "date"])["PAC"].count().reset_index()
        counts["pct"] = (counts["PAC"] / expected).clip(0, 1)
        return counts.pivot(index="EQUIP", columns="date", values="pct")


def _specific_yield_pivot(inv: pd.DataFrame, cap_per_inv: float,
                           interval_h: float, freq: str = "D") -> pd.DataFrame:
    if inv.empty or "EQUIP" not in inv.columns:
        return pd.DataFrame()
    inv = inv.copy()
    if freq == "interval":
        slot_min = max(1, round(interval_h * 60))
        inv["slot"] = inv["Time_UDT"].dt.floor(f"{slot_min}min")
        energy = inv.groupby(["EQUIP", "slot"])["PAC"].sum() * interval_h
        pivot = energy.reset_index().pivot(index="EQUIP", columns="slot", values="PAC")
        pivot.columns = [pd.Timestamp(c).strftime("%H:%M") for c in pivot.columns]
        return pivot / cap_per_inv
    elif freq == "ME":
        inv["period"] = inv["Time_UDT"].dt.to_period("M").astype(str)
        energy = inv.groupby(["EQUIP", "period"])["PAC"].sum() * interval_h
        pivot = energy.reset_index().pivot(index="EQUIP", columns="period", values="PAC")
        return pivot / cap_per_inv
    else:  # "D"
        inv["date"] = inv["Time_UDT"].dt.date
        daily = inv.groupby(["EQUIP", "date"])["PAC"].sum() * interval_h
        pivot = daily.reset_index().pivot(index="EQUIP", columns="date", values="PAC")
        return pivot / cap_per_inv


def _period_overview(inv: pd.DataFrame, irr: pd.DataFrame,
                     cap_dc: float, interval_h: float, freq: str = "ME") -> pd.DataFrame:
    """Energy / irradiation / PR grouped at the granularity chosen by _choose_freq."""
    rows: dict = {}
    slot_min = max(1, round(interval_h * 60))

    def _period_col(df: pd.DataFrame) -> pd.Series:
        if freq == "interval":
            return df["Time_UDT"].dt.floor(f"{slot_min}min")
        elif freq == "D":
            return df["Time_UDT"].dt.date
        else:
            return df["Time_UDT"].dt.to_period("M")

    if not inv.empty and "PAC" in inv.columns:
        inv = inv.copy()
        inv["_p"] = _period_col(inv)
        rows["energy_kwh"] = inv.groupby("_p")["PAC"].sum() * interval_h

    if not irr.empty and "GHI" in irr.columns:
        irr = irr.copy()
        irr["_p"] = _period_col(irr)
        if freq == "interval":
            # Keep as W/m² (instantaneous mean per slot)
            rows["ghi_w_m2"] = irr.groupby("_p")["GHI"].mean()
        else:
            rows["irradiation_kwh_m2"] = irr.groupby("_p")["GHI"].sum() * interval_h / 1000

    if not rows:
        return pd.DataFrame()
    overview = pd.DataFrame(rows)

    irr_min = 50   # W/m² — only compute PR where irradiance > 50 W/m²

    if "energy_kwh" in overview:
        if "irradiation_kwh_m2" in overview:
            denom = overview["irradiation_kwh_m2"] * cap_dc
            overview["pr_pct"] = overview["energy_kwh"] / denom.replace(0, np.nan) * 100
            min_irr_kwh = irr_min / 1000 * 4  # ~0.2 kWh/m² minimum
            overview.loc[overview["irradiation_kwh_m2"] < min_irr_kwh, "pr_pct"] = np.nan
        elif "ghi_w_m2" in overview:
            # PR = actual_kW / (GHI_kW/m² × cap_dc_kWp)
            actual_kw = overview["energy_kwh"] / interval_h
            ref_kw    = overview["ghi_w_m2"] / 1000 * cap_dc
            overview["pr_pct"] = actual_kw / ref_kw.replace(0, np.nan) * 100
            # Only suppress slots below irradiance threshold; show all other values as-is
            overview.loc[overview["ghi_w_m2"] < irr_min, "pr_pct"] = np.nan

    return overview.dropna(how="all")


def _waterfall(inv: pd.DataFrame, irr: pd.DataFrame,
               cap_dc: float, pr_target: float, interval_h: float) -> dict:
    irradiation = 0.0
    if not irr.empty and "GHI" in irr.columns:
        irradiation = irr["GHI"].clip(lower=0).sum() * interval_h / 1000   # kWh/m²
    ref    = irradiation * cap_dc
    target = ref * pr_target
    actual = (inv["PAC"].sum() * interval_h) if not inv.empty else 0.0
    pr_loss    = max(0.0, ref    - target)
    opex_loss  = max(0.0, target - actual)
    return dict(reference=ref, target=target, actual=actual,
                pr_loss=pr_loss, opex_loss=opex_loss, irradiation=irradiation)


def _punchlist(inv: pd.DataFrame, irr: pd.DataFrame,
               site_cfg: dict, interval_h: float) -> list[dict]:
    if inv.empty or "EQUIP" not in inv.columns:
        return []
    cap_per_inv = site_cfg["cap_dc_kwp"] / max(site_cfg["n_inverters"], 1)
    pr_target   = site_cfg.get("operating_pr_target", 0.80)
    irr_thr     = site_cfg.get("irr_threshold", 50)

    irradiation = 0.0
    daylight_ts: set = set()
    if not irr.empty and "GHI" in irr.columns:
        irradiation = irr["GHI"].clip(lower=0).sum() * interval_h / 1000
        daylight_ts = set(irr.loc[irr["GHI"] > irr_thr, "Time_UDT"].dt.floor("min"))

    issues: list[dict] = []
    for equip, grp in inv.groupby("EQUIP"):
        energy = grp["PAC"].sum() * interval_h
        sy     = energy / cap_per_inv

        # availability
        if daylight_ts:
            grp_ts = set(grp["Time_UDT"].dt.floor("min"))
            avail  = len(grp_ts & daylight_ts) / max(len(daylight_ts), 1)
        else:
            avail = (grp["PAC"] > 1.0).sum() / max(len(grp), 1)

        # PR
        pr = (energy / (irradiation * cap_per_inv) * 100) if irradiation > 0 else None

        # completeness
        total_ts = inv["Time_UDT"].nunique()
        completeness = len(grp) / max(total_ts, 1)

        energy_loss = 0.0
        issue_type = sev = desc = action = ""

        if avail < 0.85:
            energy_loss = (1 - avail) * cap_per_inv * irradiation * pr_target if irradiation > 0 else 0
            issue_type = "Low Availability"
            sev  = "HIGH" if avail < 0.50 else "MEDIUM"
            desc = f"Availability {avail*100:.1f}% (target ≥85%). Inverter may have experienced outages."
            action = "Check fault log, verify AC/DC breakers, attempt remote restart."
        elif pr is not None and pr < (pr_target * 100) - 5:
            energy_loss = max(0, (pr_target - pr/100) * irradiation * cap_per_inv) if irradiation > 0 else 0
            issue_type = "Below-Target PR"
            sev  = "HIGH" if pr < (pr_target*100 - 15) else "MEDIUM"
            desc = f"PR {pr:.1f}% vs target {pr_target*100:.0f}%. Underperformance detected."
            action = "Inspect string health, check soiling level, verify MPPT tracking."
        elif completeness < 0.80:
            issue_type = "Data Gaps"
            sev  = "MEDIUM"
            desc = f"Data completeness {completeness*100:.1f}% — records missing from SCADA export."
            action = "Check SCADA data logger connectivity and export schedule."
        else:
            continue

        issues.append(dict(equip=equip, type=issue_type, severity=sev,
                           sy=round(sy, 3), avail=f"{avail*100:.1f}%",
                           pr=f"{pr:.1f}%" if pr is not None else "n/a",
                           energy_loss=round(energy_loss, 0),
                           description=desc, action=action))

    issues.sort(key=lambda x: x["energy_loss"], reverse=True)

    # ── Irradiance sensor quality check ────────────────────────────────────
    if not irr.empty and "GHI" in irr.columns:
        ghi = irr["GHI"].clip(lower=0).sort_values().reset_index(drop=True)
        active = ghi[ghi > 0]
        if len(active) >= 10:
            # Detect sensor floor: if the first 10 non-zero readings are all the same value
            first10_std = active.iloc[:10].std()
            sensor_floor = active.iloc[:10].min()
            if first10_std < 1.0 and sensor_floor > 50:
                issues.append(dict(
                    equip="Site",
                    type="Irradiance Sensor",
                    severity="MEDIUM",
                    sy="-", avail="-", pr="-",
                    energy_loss=0,
                    description=(
                        f"Irradiance sensor (irr_sat) appears to have a measurement floor at "
                        f"{sensor_floor:.0f}\u00a0W/m\u00b2. The sensor reports a constant minimum "
                        f"during morning and evening ramp-up instead of the actual irradiance. "
                        f"This inflates per-slot PR calculations and may affect energy yield assessments."
                    ),
                    action=(
                        "Recalibrate or replace the irradiance sensor. Clean the sensor surface. "
                        "Verify wiring and data logger settings. "
                        "Cross-check against an alternative GHI measurement source."
                    ),
                ))

    return issues


# ─────────────────────────────────────────────────────────────────────────────
# CHART GENERATORS  (return base64 PNG string or "")
# ─────────────────────────────────────────────────────────────────────────────

def _b64_png(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return "data:image/png;base64," + base64.b64encode(buf.read()).decode()


def _cmap_completeness():
    """Red (missing) → orange → light grey → slate blue (complete) — matches reference report."""
    return mcolors.LinearSegmentedColormap.from_list(
        "dq_heatmap",
        [_T["red"], _T["amber"], "#F4F6F8", _T["slate"]])


def _cmap_yield():
    """RdYlBu: red = low yield (bad), blue = high yield (good) — matches reference report."""
    return plt.get_cmap("RdYlBu")


def _apply_spine(ax):
    ax.set_facecolor("white")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(_T["border"])
    ax.spines["bottom"].set_color(_T["border"])
    ax.tick_params(colors=_T["text"], labelsize=8.5)
    ax.grid(True, axis="y", color=_T["border"], alpha=0.5, linewidth=0.7, zorder=0)


def chart_completeness(pivot: pd.DataFrame, freq: str = "D") -> str:
    if pivot.empty:
        return ""
    pivot = pivot.loc[sorted(pivot.index, key=_natural_key)]
    cols = list(pivot.columns)
    max_cols = 288 if freq == "interval" else 90
    if len(cols) > max_cols:
        step = max(1, len(cols) // max_cols)
        pivot = pivot.iloc[:, ::step]
        cols = list(pivot.columns)

    _titles = {"interval": "Data Completeness — by Inverter & Time Slot",
               "D":        "Data Completeness Heatmap — by Inverter & Day",
               "ME":       "Data Completeness Heatmap — by Inverter & Month"}
    _xlabels = {"interval": "Time", "D": "Date", "ME": "Month"}

    n_inv = len(pivot)
    fig, ax = plt.subplots(figsize=(11, max(3.5, n_inv * 0.35 + 1.5)))
    im = ax.imshow(pivot.values, aspect="auto", cmap=_cmap_completeness(), vmin=0, vmax=1,
                   interpolation="nearest")
    ax.set_yticks(range(n_inv))
    ax.set_yticklabels(list(pivot.index), fontsize=8)
    max_ticks = 30 if freq == "interval" else 20
    step = max(1, len(cols) // max_ticks)
    ax.set_xticks(range(0, len(cols), step))
    ax.set_xticklabels([str(cols[i]) for i in range(0, len(cols), step)],
                       rotation=45, ha="right", fontsize=7)
    cbar = plt.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    cbar.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    cbar.ax.tick_params(labelsize=8)
    ax.set_title(_titles.get(freq, _titles["D"]),
                 color=_T["navy"], fontsize=10, fontweight="bold", pad=8)
    ax.set_xlabel(_xlabels.get(freq, "Date"), fontsize=8.5, color=_T["text"])
    ax.set_ylabel("Inverter / Unit", fontsize=8.5, color=_T["text"])
    fig.patch.set_facecolor("white")
    plt.tight_layout()
    return _b64_png(fig)


def chart_period_overview(overview: pd.DataFrame, pr_target: float,
                           freq: str = "ME") -> str:
    if overview.empty:
        return ""

    x_labels = [str(m) for m in overview.index]
    x = np.arange(len(x_labels))

    # Axis labels / units depend on freq
    if freq == "interval":
        energy_col   = "energy_kwh"
        energy_label = "Energy (kWh)"
        irr_col      = "ghi_w_m2"
        irr_label    = "GHI (W/m\u00b2)"
        title        = "Intra-day Energy, GHI & Performance Ratio"
        marker_size  = 3
        bar_offset   = 0.15
    elif freq == "D":
        energy_col   = "energy_kwh"
        energy_label = "Energy (kWh)"
        irr_col      = "irradiation_kwh_m2"
        irr_label    = "Irradiation (kWh/m\u00b2)"
        title        = "Daily Energy, Irradiation & Performance Ratio"
        marker_size  = 5
        bar_offset   = 0.2
    else:  # ME
        energy_col   = "energy_kwh"
        energy_label = "Energy (MWh)"
        irr_col      = "irradiation_kwh_m2"
        irr_label    = "Irradiation (kWh/m\u00b2)"
        title        = "Monthly Energy, Irradiation & Performance Ratio"
        marker_size  = 6
        bar_offset   = 0.2

    fig, ax1 = plt.subplots(figsize=(11, 4.8))
    _apply_spine(ax1)

    # Irradiance / irradiation bars (orange)
    ax_irr = None
    ax_pr  = None
    if irr_col in overview.columns:
        ax_irr = ax1.twinx()
        iv = overview[irr_col]
        iv_max = max(iv.max(), 0.1)
        ax_irr.bar(x, iv, width=bar_offset * 2,
                   color=_T["orange"], alpha=0.75, label=irr_label, zorder=2)
        ax_irr.set_ylabel(irr_label, color=_T["orange"], fontsize=9)
        ax_irr.set_ylim(0, iv_max * 1.45)
        ax_irr.spines["top"].set_visible(False)
        ax_irr.spines["left"].set_visible(False)
        ax_irr.tick_params(colors=_T["orange"], labelsize=8.5)
        ax_irr.grid(False)

    # Energy line (slate grey)
    if energy_col in overview.columns:
        raw = overview[energy_col]
        ev  = raw / 1000 if freq == "ME" else raw   # MWh for monthly, kWh otherwise
        ev_max = max(ev.max(), 0.1)
        ax1.plot(x, ev, color=_T["slate"], linewidth=1.8, marker="o",
                 markersize=marker_size, label=energy_label, zorder=3)
        ax1.set_ylabel(energy_label, color=_T["slate"], fontsize=9)
        ax1.set_ylim(0, ev_max * 1.45)
        ax1.tick_params(axis="y", colors=_T["slate"])

    # PR line
    if "pr_pct" in overview.columns:
        ax_pr = ax1.twinx()
        if ax_irr:
            ax_pr.spines["right"].set_position(("axes", 1.10))
        pr_vals = overview["pr_pct"].clip(lower=0)
        pr_ymax = max(pr_vals.dropna().max() * 1.15, 110) if not pr_vals.dropna().empty else 110
        ax_pr.plot(x, pr_vals, color=_T["green"],
                   marker="o", markersize=marker_size, linewidth=1.5,
                   zorder=4, label="PR (%)")
        ax_pr.axhline(pr_target * 100, color=_T["green"], linestyle=":",
                      linewidth=1, alpha=0.7)
        ax_pr.set_ylabel("PR (%)", color=_T["green"], fontsize=9)
        ax_pr.set_ylim(0, pr_ymax)
        ax_pr.spines["top"].set_visible(False)
        ax_pr.spines["left"].set_visible(False)
        ax_pr.tick_params(colors=_T["green"], labelsize=8.5)
        ax_pr.grid(False)

    # X-axis ticks — limit labels when many points
    max_ticks = 30 if freq == "interval" else len(x)
    step = max(1, len(x) // max_ticks)
    ax1.set_xticks(x[::step])
    ax1.set_xticklabels(x_labels[::step], rotation=45, ha="right", fontsize=8)
    ax1.set_title(title, color=_T["navy"], fontsize=10, fontweight="bold", pad=8)

    # Unified legend
    handles, lbls = ax1.get_legend_handles_labels()
    for _axx in [ax_irr, ax_pr]:
        if _axx:
            h, l = _axx.get_legend_handles_labels()
            handles += h; lbls += l
    ax1.legend(handles, lbls, loc="upper left", fontsize=8, framealpha=0.9)

    fig.patch.set_facecolor("white")
    plt.tight_layout()
    return _b64_png(fig)


def chart_specific_yield(pivot: pd.DataFrame, freq: str = "D") -> str:
    if pivot.empty:
        return ""
    pivot = pivot.loc[sorted(pivot.index, key=_natural_key)]
    cols = list(pivot.columns)
    max_cols = 288 if freq == "interval" else 90
    if len(cols) > max_cols:
        step = max(1, len(cols) // max_cols)
        pivot = pivot.iloc[:, ::step]
        cols = list(pivot.columns)

    _titles = {"interval": "Per-Inverter Specific Yield (kWh/kWp per Interval)",
               "D":        "Per-Inverter Specific Yield Heatmap (kWh/kWp per Day)",
               "ME":       "Per-Inverter Specific Yield Heatmap (kWh/kWp per Month)"}
    _xlabels = {"interval": "Time", "D": "Date", "ME": "Month"}
    _cbarlabels = {"interval": "kWh/kWp / interval", "D": "kWh/kWp / day",
                   "ME": "kWh/kWp / month"}

    n_inv = len(pivot)
    fig, ax = plt.subplots(figsize=(11, max(3.5, n_inv * 0.35 + 1.5)))
    vmax = np.nanpercentile(pivot.values[pivot.values > 0], 98) if (pivot.values > 0).any() else 1
    im = ax.imshow(pivot.values, aspect="auto", cmap=_cmap_yield(),
                   vmin=0, vmax=vmax, interpolation="nearest")
    ax.set_yticks(range(n_inv))
    ax.set_yticklabels(list(pivot.index), fontsize=8)
    max_ticks = 30 if freq == "interval" else 20
    step = max(1, len(cols) // max_ticks)
    ax.set_xticks(range(0, len(cols), step))
    ax.set_xticklabels([str(cols[i]) for i in range(0, len(cols), step)],
                       rotation=45, ha="right", fontsize=7)
    cbar = plt.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    cbar.set_label(_cbarlabels.get(freq, "kWh/kWp"), fontsize=8)
    cbar.ax.tick_params(labelsize=8)
    ax.set_title(_titles.get(freq, _titles["D"]),
                 color=_T["navy"], fontsize=10, fontweight="bold", pad=8)
    ax.set_xlabel(_xlabels.get(freq, "Date"), fontsize=8.5, color=_T["text"])
    ax.set_ylabel("Inverter / Unit", fontsize=8.5, color=_T["text"])
    fig.patch.set_facecolor("white")
    plt.tight_layout()
    return _b64_png(fig)


def chart_waterfall(wf: dict) -> str:
    ref    = wf.get("reference", 0)
    target = wf.get("target",    0)
    actual = wf.get("actual",    0)
    if ref <= 0:
        return ""

    pr_loss   = wf.get("pr_loss",   0)   # = ref - target  (always ≥ 0)
    opex_loss = wf.get("opex_loss", 0)   # = max(0, target - actual)

    # Choose display unit: kWh if ref < 5000 kWh, else MWh
    if ref < 5000:
        scale, unit = 1.0, "kWh"
        fmt = lambda v: f"{v:,.0f}"
    else:
        scale, unit = 1000.0, "MWh"
        fmt = lambda v: f"{v/1000:,.1f}"

    # Bars: (height, bottom, color, label)
    # Amber bar bottom MUST be target (= ref - pr_loss), not actual
    bars = [
        (ref,       0,      _T["navy"],  "Reference\nEnergy"),
        (pr_loss,   target, _T["amber"], "Efficiency\n& Temp Loss"),
        (opex_loss, actual, _T["red"],   "Operational\nLoss"),
        (actual,    0,      _T["green"], "Actual\nEnergy"),
    ]

    fig, ax = plt.subplots(figsize=(8, 5))
    for i, (val, bot, col, _lbl) in enumerate(bars):
        if val <= 0:
            continue
        ax.bar(i, val, bottom=bot, color=col, alpha=0.88, width=0.55, zorder=2,
               edgecolor="white", linewidth=0.5)
        mid = bot + val / 2
        ax.text(i, mid, fmt(val), ha="center", va="center",
                fontsize=9, color="white", fontweight="bold")

    # Connector lines (dashed, at the top of each segment)
    connector_ys = [ref, target, actual]
    for i, y in enumerate(connector_ys):
        ax.plot([i + 0.275, i + 0.725], [y, y],
                color=_T["border"], linewidth=0.8, linestyle="--", zorder=1)

    ax.set_xticks(range(4))
    ax.set_xticklabels([b[3] for b in bars], fontsize=9)
    ax.set_ylabel(f"Energy ({unit})", fontsize=9, color=_T["text"])
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"{v:,.0f}" if scale == 1.0 else f"{v/1000:,.0f}"))
    ax.set_title("Energy Loss Waterfall",
                 color=_T["navy"], fontsize=10, fontweight="bold", pad=8)
    _apply_spine(ax)
    fig.patch.set_facecolor("white")
    plt.tight_layout()
    return _b64_png(fig)


# ─────────────────────────────────────────────────────────────────────────────
# HTML ASSEMBLY
# ─────────────────────────────────────────────────────────────────────────────

def _b64_file(path: Path, mime: str = "image/png") -> str:
    if path and path.exists():
        return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()
    return ""


def _header(logo_b64: str, site_name: str, report_title: str) -> str:
    logo_tag = f'<img src="{logo_b64}" alt="logo">' if logo_b64 else ""
    return f"""
<div class="header-shell">
  <div class="header-band">
    {logo_tag}
    <div class="header-copy">
      <p class="header-site">{site_name}</p>
      <p class="header-company">{report_title}</p>
    </div>
  </div>
  <div class="header-accent"></div>
</div>"""


def _section_heading(eyebrow: str, title: str, summary: str = "") -> str:
    s = f'<p class="section-summary">{summary}</p>' if summary else ""
    return f"""
<div class="section-heading">
  <p class="eyebrow">{eyebrow}</p>
  <h2>{title}</h2>
  {s}
</div>"""


def _kpi_card(label: str, value: str, sub: str = "", status: str = "") -> str:
    return f"""
<div class="kpi-card {status}">
  <p class="kpi-label">{label}</p>
  <p class="kpi-value">{value}</p>
  <p class="kpi-subtext">{sub}</p>
</div>"""


def _figure(img_b64: str, caption: str = "", full: bool = True) -> str:
    w_cls = "width-full" if full else "width-half"
    cap = f"<figcaption>{caption}</figcaption>" if caption else ""
    return f"""
<div class="figure-card {w_cls}">
  <figure>
    <img src="{img_b64}" alt="{caption}">
    {cap}
  </figure>
</div>"""


def _assemble_html(*, site_cfg: dict, report_date_str: str, period_str: str,
                   logo_b64: str, cover_img_b64: str,
                   img_completeness: str, img_monthly: str,
                   img_sy: str, img_waterfall: str,
                   overview: pd.DataFrame, wf: dict,
                   issues: list[dict], pr_target: float) -> str:

    report_css, print_css = _load_static_css()

    site_name    = site_cfg["display_name"]
    cap_dc       = site_cfg["cap_dc_kwp"]
    cap_ac       = site_cfg.get("cap_ac_kw", 0)
    n_inv        = site_cfg["n_inverters"]
    technology   = site_cfg.get("technology", "-")
    inv_model    = site_cfg.get("inverter_model", "-")
    report_title = "SCADA Daily Performance Analysis"
    generated    = datetime.now().strftime("%Y-%m-%d %H:%M UTC")

    logo_tag  = f'<img class="cover-logo" src="{logo_b64}" alt="logo">' if logo_b64 else ""
    hero_html = (f'<div class="cover-hero"><img src="{cover_img_b64}" alt="Solar farm"></div>'
                 if cover_img_b64 else '<div class="cover-hero"></div>')

    hdr = _header(logo_b64, site_name, report_title)

    # ── KPIs from overview + waterfall ──────────────────────────────────────
    total_energy = overview["energy_kwh"].sum() if "energy_kwh" in overview.columns else 0
    total_irr    = (overview["irradiation_kwh_m2"].sum()
                    if "irradiation_kwh_m2" in overview.columns
                    else overview["ghi_w_m2"].mean() if "ghi_w_m2" in overview.columns else 0)
    mean_pr      = overview["pr_pct"].mean() if "pr_pct" in overview.columns else 0
    spec_yield   = (total_energy / cap_dc) if cap_dc > 0 else 0
    n_high       = sum(1 for i in issues if i["severity"] == "HIGH")
    n_med        = sum(1 for i in issues if i["severity"] == "MEDIUM")

    def pr_status(pr):
        if pr >= pr_target * 100 - 2:  return "status-success"
        if pr >= pr_target * 100 - 8:  return "status-warning"
        return "status-danger"

    kpi_html = "".join([
        _kpi_card("Total Energy (period)", f"{total_energy/1000:,.1f} MWh", "measured output"),
        _kpi_card("Specific Yield",        f"{spec_yield:.2f}",             "kWh/kWp"),
        _kpi_card("Mean PR",               f"{mean_pr:.1f}%",
                  f"Target {pr_target*100:.0f}%", pr_status(mean_pr)),
        _kpi_card("Total Irradiation",     f"{total_irr:.1f}",              "kWh/m\u00b2"),
        _kpi_card("Actual Energy",         f"{wf.get('actual',0)/1000:,.1f} MWh",
                  f"vs {wf.get('reference',0)/1000:,.1f} MWh ref."),
        _kpi_card("Issues Detected",       f"{n_high}H / {n_med}M",
                  "HIGH / MEDIUM",
                  "status-danger" if n_high else "status-warning" if n_med else "status-success"),
    ])

    # ── Punchlist rows (6 columns) ─────────────────────────────────────────
    sev_class = {"HIGH": "row-danger", "MEDIUM": "row-warning", "LOW": "row-success"}
    punchlist_rows = ""
    for iss in issues:
        rc  = sev_class.get(iss["severity"], "")
        metrics = f"SY&#160;{iss['sy']}&#160;kWh/kWp | Avail.&#160;{iss['avail']} | PR&#160;{iss['pr']}"
        punchlist_rows += f"""
<tr class="{rc}">
  <td>{iss['equip']}</td>
  <td>{iss['severity']}</td>
  <td>{iss['type']}</td>
  <td style="white-space:nowrap">{iss['energy_loss']:,.0f}</td>
  <td>{iss['description']}<br><span style="color:#6B7785;font-size:6.4pt">{metrics}</span></td>
  <td>{iss['action']}</td>
</tr>"""
    if not punchlist_rows:
        punchlist_rows = """<tr class="row-success">
  <td colspan="6" style="text-align:center;font-style:italic;color:#6B7785;">
    No significant issues detected &#8212; all inverters within normal operating parameters.
  </td></tr>"""

    # ── Waterfall summary rows ──────────────────────────────────────────────
    ref    = wf.get("reference", 0)
    actual = wf.get("actual",    0)
    wf_rows = f"""
<tr><td>Reference Energy</td><td>{ref/1000:,.1f} MWh</td>
    <td>Theoretical maximum at full irradiance conversion</td></tr>
<tr class="row-warning"><td>Efficiency &amp; Temp Losses</td>
    <td>&#8722;{wf.get('pr_loss',0)/1000:,.1f} MWh</td>
    <td>PR-driven losses: temperature, optical, cable, clipping</td></tr>
<tr class="row-danger"><td>Operational Losses</td>
    <td>&#8722;{wf.get('opex_loss',0)/1000:,.1f} MWh</td>
    <td>Downtime, curtailment, communications faults</td></tr>
<tr class="row-success"><td><strong>Actual Energy</strong></td>
    <td><strong>{actual/1000:,.1f} MWh</strong></td>
    <td>Measured SCADA output</td></tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{site_name} &#8212; {report_title}</title>
  <style>{_ROOT_VARS}</style>
  <style>{report_css}</style>
  <style>{print_css}</style>
  <style>
/* ── Per-section overrides for this report ── */
.page-performance-overview .kpi-grid {{
  grid-template-columns: repeat(3, minmax(0, 1fr));
}}
.page-data-quality .figure-card img      {{ max-height: 200mm; }}
.page-specific-yield .figure-card img    {{ max-height: 220mm; }}
.page-performance-overview .figure-card.width-full img {{ max-height: 112mm; }}
.page-losses .figure-card img            {{ max-height: 90mm; }}
/* ── Punchlist column widths (6-col layout) ── */
.page-action-punchlist .report-table {{
  table-layout: fixed;
  width: 100%;
}}
.page-action-punchlist .report-table th:nth-child(1),
.page-action-punchlist .report-table td:nth-child(1) {{ width: 9%; white-space: nowrap; }}
.page-action-punchlist .report-table th:nth-child(2),
.page-action-punchlist .report-table td:nth-child(2) {{ width: 7%; }}
.page-action-punchlist .report-table th:nth-child(3),
.page-action-punchlist .report-table td:nth-child(3) {{ width: 12%; }}
.page-action-punchlist .report-table th:nth-child(4),
.page-action-punchlist .report-table td:nth-child(4) {{ width: 9%; }}
.page-action-punchlist .report-table th:nth-child(5),
.page-action-punchlist .report-table td:nth-child(5) {{ width: 32%; }}
.page-action-punchlist .report-table th:nth-child(6),
.page-action-punchlist .report-table td:nth-child(6) {{ width: 31%; }}
  </style>
</head>
<body>

<!-- ═══════════════ PAGE 1: COVER ═══════════════ -->
<section class="page cover-page">
  <div class="cover-band">
    {logo_tag}
    <div class="header-copy">
      <p class="header-site">{site_name}</p>
      <p class="header-company">8.2 Advisory | A Dolfines Company</p>
    </div>
  </div>
  <div class="cover-accent"></div>
  <div class="cover-body layout-block">
    {hero_html}
    <div class="cover-panel">
      <p class="eyebrow">Renewable Energy SCADA Assessment</p>
      <h1>{site_name} &#8212; {report_title}</h1>
      <p class="cover-subtitle">SCADA Performance Analysis Report</p>
      <dl class="cover-metadata">
        <div><dt>Project</dt><dd>{site_name}</dd></div>
        <div><dt>Asset</dt><dd>{cap_dc:,.0f} kWp DC / {cap_ac:,.0f} kW AC</dd></div>
        <div><dt>Analysis period</dt><dd>{period_str}</dd></div>
        <div><dt>Technology</dt><dd>{technology}</dd></div>
        <div><dt>Inverters</dt><dd>{n_inv} &#215; {inv_model}</dd></div>
        <div><dt>Issued</dt><dd>{generated}</dd></div>
      </dl>
    </div>
  </div>
</section>

<!-- ═══════════════ PAGE 2: DATA QUALITY ═══════════════ -->
<section class="page standard-page page-data-quality">
  {hdr}
  <div class="page-content layout-block">
    {_section_heading("Data Quality", "Data Completeness Heatmap",
        "Fraction of expected records received per inverter per day. "
        "Red&#160;=&#160;missing data, green&#160;=&#160;full coverage.")}
    <div class="figure-grid">
      {_figure(img_completeness, "Data completeness &#8212; % of expected intervals with valid readings.") if img_completeness else
       '<div class="figure-card width-full"><p style="color:#6B7785;font-style:italic;padding:8mm 4mm;">No inverter data available.</p></div>'}
    </div>
    <div class="commentary-card">
      <h3>Interpretation</h3>
      <p>Cells at 100% (green) indicate all expected data records were received. Amber/red cells
         highlight days with gaps &#8212; check SCADA data-logger connectivity and export schedule for
         the flagged inverters and dates.</p>
    </div>
  </div>
</section>

<!-- ═══════════════ PAGE 3: PERFORMANCE OVERVIEW ═══════════════ -->
<section class="page standard-page page-performance-overview">
  {hdr}
  <div class="page-content layout-block">
    {_section_heading("Performance Overview",
        "Monthly Energy, Irradiation &amp; Performance Ratio",
        "Site-level monthly aggregation of energy output, solar resource and PR.")}
    <div class="kpi-grid">
      {kpi_html}
    </div>
    <div class="figure-grid">
      {_figure(img_monthly, "Orange bars&#160;=&#160;energy (MWh), grey bars&#160;=&#160;irradiation (kWh/m&#178;), green line&#160;=&#160;PR (%).") if img_monthly else ""}
    </div>
  </div>
</section>

<!-- ═══════════════ PAGE 4: SPECIFIC YIELD HEATMAP ═══════════════ -->
<section class="page standard-page page-specific-yield">
  {hdr}
  <div class="page-content layout-block">
    {_section_heading("Per-Inverter Analysis", "Specific Yield Heatmap",
        "Daily specific yield (kWh/kWp) per inverter. Darker green&#160;=&#160;stronger output.")}
    <div class="commentary-card">
      <p>Compare rows horizontally &#8212; an inverter consistently below its peers indicates a
         systematic underperformance issue (soiling, shading, MPPT fault, string disconnection).
         Compare columns vertically to identify site-wide low-irradiance days vs.&#160;isolated faults.</p>
    </div>
    <div class="figure-grid">
      {_figure(img_sy, "Specific yield (kWh/kWp) &#8212; per inverter per day.") if img_sy else
       '<div class="figure-card width-full"><p style="color:#6B7785;font-style:italic;padding:8mm 4mm;">Insufficient data to generate heatmap.</p></div>'}
    </div>
  </div>
</section>

<!-- ═══════════════ PAGE 5: ENERGY LOSS WATERFALL ═══════════════ -->
<section class="page standard-page page-losses">
  {hdr}
  <div class="page-content layout-block">
    {_section_heading("Energy Losses", "Energy Loss Waterfall",
        "Decomposition of reference energy into successive loss categories through to actual measured output.")}
    <div class="figure-grid">
      {_figure(img_waterfall, "Waterfall: reference (GHI &#215; capacity) &#8594; efficiency losses &#8594; operational losses &#8594; actual.") if img_waterfall else ""}
    </div>
    <div class="table-card">
      <div class="table-card-header"><h3>Waterfall Summary</h3></div>
      <table class="report-table" style="table-layout:auto;">
        <thead><tr><th>Category</th><th style="width:14%">Energy (MWh)</th><th>Description</th></tr></thead>
        <tbody>{wf_rows}</tbody>
      </table>
    </div>
  </div>
</section>

<!-- ═══════════════ PAGE 6: PUNCHLIST ═══════════════ -->
<section class="page standard-page page-action-punchlist">
  {hdr}
  <div class="page-content layout-block">
    {_section_heading("Action Punchlist", "Prioritised Issue Register",
        "Issues ranked by estimated energy loss impact. HIGH&#160;=&#160;immediate action required.")}
    <div class="commentary-card">
      <h3>Methodology</h3>
      <p>Inverters are flagged if availability &lt;85%, PR is &gt;5pp below target, or data
         completeness &lt;80%. Energy loss is estimated using actual irradiation data and the
         operating PR target.</p>
    </div>
    <div class="table-card">
      <div class="table-card-header"><h3>Issue Register</h3></div>
      <table class="report-table" style="table-layout:auto;">
        <thead><tr>
          <th>Inverter</th><th>Sev.</th><th>Issue Type</th>
          <th>Est.&#160;Loss<br>(kWh)</th>
          <th>Description &amp; Key Metrics</th>
          <th>Recommended Action</th>
        </tr></thead>
        <tbody>{punchlist_rows}</tbody>
      </table>
    </div>
  </div>
</section>

</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def build_scada_analysis_html(
    site_cfg: dict,
    data_dir: Path,
    out_path: Optional[Path] = None,
) -> Path:
    """
    Generate the SCADA analysis HTML report and return the output path.

    Parameters
    ----------
    site_cfg  : dict  — platform site configuration
    data_dir  : Path  — directory containing normalised inverter & irradiance CSVs
    out_path  : Path  — where to write the HTML (default: temp dir)
    """
    import tempfile
    data_dir = Path(data_dir)

    if out_path is None:
        td = Path(tempfile.mkdtemp(prefix="pvpat_"))
        site_safe = "".join(c if c.isalnum() else "_" for c in site_cfg["display_name"])
        out_path = td / f"PVPAT_SCADA_{site_safe}.html"
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Load data ─────────────────────────────────────────────────────────
    inv = _load_inv(data_dir)
    irr = _load_irr(data_dir)

    interval_h = _detect_interval(inv if not inv.empty else irr,
                                   fallback_min=site_cfg.get("interval_min", 10))
    irr = _normalise_ghi(irr, interval_h)

    cap_dc      = site_cfg["cap_dc_kwp"]
    n_inv       = max(site_cfg["n_inverters"], 1)
    cap_per_inv = cap_dc / n_inv
    pr_target   = site_cfg.get("operating_pr_target", 0.80)

    # ── Analysis ──────────────────────────────────────────────────────────
    freq       = _choose_freq(inv)
    comp_pivot = _completeness_pivot(inv, interval_h, freq)
    sy_pivot   = _specific_yield_pivot(inv, cap_per_inv, interval_h, freq)
    overview   = _period_overview(inv, irr, cap_dc, interval_h, freq)
    wf         = _waterfall(inv, irr, cap_dc, pr_target, interval_h)
    issues     = _punchlist(inv, irr, site_cfg, interval_h)

    # ── Period string ─────────────────────────────────────────────────────
    if not inv.empty:
        d0 = inv["Time_UDT"].min().strftime("%d %b %Y")
        d1 = inv["Time_UDT"].max().strftime("%d %b %Y")
        period_str = f"{d0} to {d1}"
    else:
        period_str = "n/a"

    # ── Charts ────────────────────────────────────────────────────────────
    img_completeness = chart_completeness(comp_pivot, freq)
    img_monthly      = chart_period_overview(overview, pr_target, freq)
    img_sy           = chart_specific_yield(sy_pivot, freq)
    img_wf           = chart_waterfall(wf)

    # ── Assets ────────────────────────────────────────────────────────────
    logo_b64 = (_b64_file(_ROOT / "dolfines_logo_white.png") or
                _b64_file(_ROOT / "8p2_logo_white.png"))

    cover_img_b64 = ""
    for candidate in ("bg_solar.jpg", "00orig/solar_farm_2.jpg",
                      "00orig/solar_farm.jpg", "france.jpg"):
        p = _ROOT / candidate
        if p.exists():
            cover_img_b64 = _b64_file(p, mime="image/jpeg")
            break

    # ── Assemble ──────────────────────────────────────────────────────────
    html = _assemble_html(
        site_cfg       = site_cfg,
        report_date_str= datetime.now().strftime("%d %B %Y"),
        period_str     = period_str,
        logo_b64       = logo_b64,
        cover_img_b64  = cover_img_b64,
        img_completeness = img_completeness,
        img_monthly      = img_monthly,
        img_sy           = img_sy,
        img_waterfall    = img_wf,
        overview         = overview,
        wf               = wf,
        issues           = issues,
        pr_target        = pr_target,
    )

    out_path.write_text(html, encoding="utf-8")
    return out_path
