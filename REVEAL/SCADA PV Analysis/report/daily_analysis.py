"""
daily_analysis.py — Single-day SCADA analysis engine for PVPAT Daily Report
=============================================================================
Computes per-inverter specific yield, PR, availability, irradiance,
waterfall losses, and alerts for a given calendar date.
"""

from __future__ import annotations

import warnings
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _find_time_col(df: pd.DataFrame) -> str | None:
    """Return the column name that represents the timestamp, or None."""
    _TIME_ALIASES = {
        "time_udt", "time_utc", "time_local", "time", "datetime",
        "timestamp", "date_time", "horodate", "date",
    }
    for c in df.columns:
        if c.lower() in _TIME_ALIASES:
            return c
    # Fallback: any column whose first non-null value looks like a date string
    for c in df.columns:
        sample = df[c].dropna().head(3).astype(str)
        if sample.str.match(
            r"\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{2}[/\-]\d{2}|\d{8}:"
        ).any():
            return c
    return None


def _load_inverter_csv(data_dir: Path) -> pd.DataFrame:
    """Load all inverter CSVs from data_dir, concatenate, return tidy DataFrame."""
    frames = []
    for p in sorted(data_dir.glob("*.csv")):
        name_lower = p.stem.lower()
        # Skip irradiance files
        if any(k in name_lower for k in ("irr", "ghi", "irradiance", "meteo")):
            continue
        try:
            df = pd.read_csv(p, sep=";", decimal=",", encoding="utf-8-sig",
                             low_memory=False)
            # Normalise column names
            df.columns = [c.strip() for c in df.columns]
            if "Time_UDT" not in df.columns:
                t = _find_time_col(df)
                if t:
                    df = df.rename(columns={t: "Time_UDT"})
                else:
                    df = df.rename(columns={df.columns[0]: "Time_UDT"})
            frames.append(df)
        except Exception:
            continue
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out["Time_UDT"] = pd.to_datetime(out["Time_UDT"], dayfirst=True, errors="coerce")
    out = out.dropna(subset=["Time_UDT"])
    # Normalise equipment / power column names
    eq_col = next((c for c in out.columns if c.upper() in ("EQUIP", "EQUIPMENT", "INV", "INVERTER")), None)
    pac_col = next((c for c in out.columns if c.upper() in ("PAC", "P_AC", "POWER", "ACTIVE_POWER")), None)
    if eq_col and eq_col != "EQUIP":
        out = out.rename(columns={eq_col: "EQUIP"})
    if pac_col and pac_col != "PAC":
        out = out.rename(columns={pac_col: "PAC"})
    if "PAC" in out.columns:
        out["PAC"] = pd.to_numeric(out["PAC"], errors="coerce").fillna(0.0)
    return out


def _load_irradiance_csv(data_dir: Path) -> pd.DataFrame:
    """Load irradiance CSV(s), return tidy DataFrame with Time_UDT + GHI.

    Scans ALL csv files and keeps only those that contain a GHI/irr-like
    column — this avoids missing data when the filename doesn't have an
    obvious irradiance keyword.
    """
    frames = []
    for p in sorted(data_dir.glob("*.csv")):
        try:
            df = pd.read_csv(p, sep=";", decimal=",", encoding="utf-8-sig",
                             low_memory=False)
            df.columns = [c.strip() for c in df.columns]
            # Only keep files that actually have an irradiance-like column
            ghi_col = next((c for c in df.columns if "ghi" in c.lower() or
                            "irr" in c.lower() or "global" in c.lower()), None)
            if ghi_col is None:
                continue
            if "Time_UDT" not in df.columns:
                t = _find_time_col(df)
                if t:
                    df = df.rename(columns={t: "Time_UDT"})
                else:
                    df = df.rename(columns={df.columns[0]: "Time_UDT"})
            frames.append(df)
        except Exception:
            continue
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out["Time_UDT"] = pd.to_datetime(out["Time_UDT"], dayfirst=True, errors="coerce")
    out = out.dropna(subset=["Time_UDT"])
    # Normalise the GHI column name
    ghi_col = next((c for c in out.columns if "ghi" in c.lower() or
                    "irr" in c.lower() or "global" in c.lower()), None)
    if ghi_col and ghi_col != "GHI":
        out = out.rename(columns={ghi_col: "GHI"})
    if "GHI" in out.columns:
        out["GHI"] = pd.to_numeric(out["GHI"], errors="coerce").fillna(0.0)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ANALYSIS CLASS
# ─────────────────────────────────────────────────────────────────────────────

class DailyAnalysis:
    """
    Compute all metrics needed for the daily report for a single calendar date.

    Parameters
    ----------
    site_cfg : dict   — site config dict from platform_users.SITES
    report_date : date
    data_dir : Path | None   — override site_cfg["data_dir"] if needed
    """

    def __init__(self, site_cfg: dict, report_date: date,
                 data_dir: Optional[Path] = None):
        self.cfg = site_cfg
        self.date = report_date
        self.data_dir = Path(data_dir) if data_dir else Path(site_cfg["data_dir"])

        self._inv_raw: Optional[pd.DataFrame] = None
        self._irr_raw: Optional[pd.DataFrame] = None
        self._results: Optional[dict] = None

    # ── public ────────────────────────────────────────────────

    def run(self) -> dict:
        """Run all analysis steps. Returns results dict."""
        if self._results is not None:
            return self._results

        self._inv_raw = _load_inverter_csv(self.data_dir)
        self._irr_raw = _load_irradiance_csv(self.data_dir)

        inv_day  = self._filter_day(self._inv_raw)
        irr_day  = self._filter_day(self._irr_raw)

        irradiance      = self._daily_irradiance(irr_day)
        per_inv         = self._per_inverter_metrics(inv_day, irradiance)
        site_totals     = self._site_totals(per_inv, irradiance)
        waterfall       = self._waterfall(site_totals, irradiance)
        alerts          = self._detect_alerts(per_inv, irr_day)
        site_power_ts   = self._site_power_timeseries(inv_day)

        self._results = {
            "date":           self.date,
            "site_name":      self.cfg["display_name"],
            "irradiance":     irradiance,
            "per_inverter":   per_inv,
            "site_totals":    site_totals,
            "waterfall":      waterfall,
            "alerts":         alerts,
            "site_power_ts":  site_power_ts,
            "used_demo":      getattr(self, "_used_demo", False),
        }
        return self._results

    # ── filtering ─────────────────────────────────────────────

    def _filter_day(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or "Time_UDT" not in df.columns:
            return df
        mask = df["Time_UDT"].dt.date == self.date
        filtered = df[mask].copy()
        # Fallback: if the file only contains one unique date (user uploaded a
        # single-day file), use all rows regardless of the selected report date.
        if filtered.empty:
            unique_dates = df["Time_UDT"].dt.date.dropna().unique()
            if len(unique_dates) == 1:
                return df.copy()
        return filtered

    # ── irradiance ────────────────────────────────────────────

    def _daily_irradiance(self, irr_day: pd.DataFrame) -> dict:
        """Return dict with timeseries and summary stats."""
        interval_h = self.cfg["interval_min"] / 60.0
        irr_threshold = self.cfg["irr_threshold"]

        if irr_day.empty or "GHI" not in irr_day.columns:
            return {
                "timeseries": pd.Series(dtype=float),
                "insolation_kwh_m2": 0.0,
                "peak_ghi": 0.0,
                "daylight_hours": 0.0,
            }

        ts = irr_day.set_index("Time_UDT")["GHI"].sort_index()
        ts = ts.clip(lower=0)

        # Auto-detect actual interval from timestamps (don't trust cfg value)
        if len(ts) > 1:
            interval_h = (ts.index[1] - ts.index[0]).total_seconds() / 3600.0

        # Auto-detect Wh/m² per-interval values (e.g. max ~86 for 5-min slots)
        # and convert to W/m² instantaneous by dividing by hours-per-interval
        if 0 < ts.max() < 200:
            ts = ts / interval_h  # Wh/interval  -->  W/m²

        insolation = ts.sum() * interval_h / 1000.0   # kWh/m²
        peak_ghi   = ts.max()
        daylight   = (ts >= irr_threshold).sum() * interval_h

        return {
            "timeseries": ts,
            "insolation_kwh_m2": round(insolation, 3),
            "peak_ghi": round(peak_ghi, 1),
            "daylight_hours": round(daylight, 1),
        }

    # ── per-inverter ───────────────────────────────────────────

    def _per_inverter_metrics(self, inv_day: pd.DataFrame,
                               irradiance: dict) -> pd.DataFrame:
        """Return DataFrame with one row per inverter."""
        cap_ac_kw     = self.cfg["inv_ac_kw"]
        cap_dc_kwp    = self.cfg["cap_dc_kwp"] / self.cfg["n_inverters"]
        pr_target     = self.cfg["operating_pr_target"]
        interval_h    = self.cfg["interval_min"] / 60.0
        irr_threshold = self.cfg["irr_threshold"]
        pwr_threshold = self.cfg["power_threshold"]
        insolation    = irradiance["insolation_kwh_m2"]

        self._used_demo = False
        records = []

        if inv_day.empty or "EQUIP" not in inv_day.columns or "PAC" not in inv_day.columns:
            # Return synthetic demo data if no real data available
            self._used_demo = True
            return self._demo_per_inverter(insolation, pr_target, cap_ac_kw, cap_dc_kwp)

        inv_day = inv_day.copy()
        inv_day["PAC"] = pd.to_numeric(inv_day["PAC"], errors="coerce").fillna(0.0)

        # Irradiance timeseries for merging
        irr_ts = irradiance["timeseries"]

        for equip, grp in inv_day.groupby("EQUIP"):
            grp = grp.set_index("Time_UDT").sort_index()
            grp["PAC"] = grp["PAC"].clip(lower=0)

            # Energy (kWh)
            energy_kwh = grp["PAC"].sum() * interval_h

            # Specific yield (kWh/kWp)
            spec_yield = energy_kwh / cap_dc_kwp if cap_dc_kwp > 0 else 0.0

            # PR
            pr = (spec_yield / insolation) if insolation > 0 else 0.0
            pr = min(pr, 1.10)   # cap at 110%

            # Availability — daylight hours
            if not irr_ts.empty:
                irr_aligned = irr_ts.reindex(grp.index, method="nearest", tolerance="11min")
                daylight_mask = (irr_aligned >= irr_threshold)
                avail_denom = daylight_mask.sum()
                avail_num   = ((grp["PAC"] >= pwr_threshold) & daylight_mask).sum()
                availability = (avail_num / avail_denom) if avail_denom > 0 else 1.0
            else:
                availability = 1.0 if energy_kwh > 0 else 0.0

            # Peak power
            peak_kw = grp["PAC"].max()

            records.append({
                "inverter":      str(equip),
                "energy_kwh":    round(energy_kwh, 2),
                "spec_yield":    round(spec_yield, 3),
                "pr":            round(pr, 4),
                "availability":  round(availability, 4),
                "peak_kw":       round(peak_kw, 1),
                "pr_ok":         pr >= (pr_target - 0.05),   # 5% tolerance
            })

        if not records:
            self._used_demo = True
            return self._demo_per_inverter(insolation, pr_target, cap_ac_kw, cap_dc_kwp)

        df = pd.DataFrame(records).sort_values("inverter").reset_index(drop=True)
        return df

    def _site_power_timeseries(self, inv_day: pd.DataFrame) -> pd.Series:
        """Return site-level total AC power (kW) as a 10-min timeseries."""
        if inv_day.empty or "PAC" not in inv_day.columns or "Time_UDT" not in inv_day.columns:
            return pd.Series(dtype=float)
        ts = inv_day.groupby("Time_UDT")["PAC"].sum().clip(lower=0).sort_index()
        return ts

    def _demo_per_inverter(self, insolation: float, pr_target: float,
                            cap_ac_kw: float, cap_dc_kwp: float) -> pd.DataFrame:
        """Generate realistic-looking demo data when no raw CSVs match the date."""
        rng = np.random.default_rng(seed=int(self.date.strftime("%Y%m%d")))
        n = self.cfg["n_inverters"]
        records = []
        for i in range(1, n + 1):
            base_pr   = pr_target + rng.normal(0, 0.025)
            base_pr   = np.clip(base_pr, 0.55, 1.0)
            # 2 inverters underperform (demo alerts)
            if i in (8, 21):
                base_pr *= 0.72
            avail = 1.0 if i not in (8,) else 0.0
            spec_yield = base_pr * insolation if insolation > 0 else base_pr * 4.5
            energy_kwh = spec_yield * cap_dc_kwp
            records.append({
                "inverter":     f"INV{i:02d}",
                "energy_kwh":   round(energy_kwh, 2),
                "spec_yield":   round(spec_yield, 3),
                "pr":           round(base_pr, 4),
                "availability": avail,
                "peak_kw":      round(cap_ac_kw * base_pr * 0.95, 1),
                "pr_ok":        base_pr >= (pr_target - 0.05),
            })
        return pd.DataFrame(records)

    # ── site totals ───────────────────────────────────────────

    def _site_totals(self, per_inv: pd.DataFrame, irradiance: dict) -> dict:
        cap_dc_kwp = self.cfg["cap_dc_kwp"]
        pr_target  = self.cfg["operating_pr_target"]
        insolation = irradiance["insolation_kwh_m2"]

        total_energy = per_inv["energy_kwh"].sum()
        spec_yield   = total_energy / cap_dc_kwp if cap_dc_kwp > 0 else 0.0
        pr           = (spec_yield / insolation) if insolation > 0 else 0.0
        availability = per_inv["availability"].mean() if not per_inv.empty else 0.0

        # Expected energy at target PR
        expected_energy = pr_target * insolation * cap_dc_kwp if insolation > 0 else 0.0

        return {
            "total_energy_kwh":  round(total_energy, 1),
            "spec_yield":        round(spec_yield, 3),
            "pr":                round(pr, 4),
            "pr_pct":            round(pr * 100, 1),
            "pr_target_pct":     round(pr_target * 100, 1),
            "availability_pct":  round(availability * 100, 1),
            "expected_energy_kwh": round(expected_energy, 1),
            "energy_delta_kwh":  round(total_energy - expected_energy, 1),
        }

    # ── waterfall ─────────────────────────────────────────────

    def _waterfall(self, site_totals: dict, irradiance: dict) -> list[dict]:
        """
        Simplified waterfall: theoretical → optical/temp → inverter → grid.
        Returns list of dicts: {label, value_kwh, cumulative, type}.
        """
        cap_dc_kwp = self.cfg["cap_dc_kwp"]
        design_pr  = self.cfg["design_pr"]
        pr_target  = self.cfg["operating_pr_target"]
        insolation = irradiance["insolation_kwh_m2"]

        theoretical    = insolation * cap_dc_kwp  # kWh (100% efficiency)
        optical_temp   = theoretical * (1 - design_pr)  # losses to get to design PR
        inverter_loss  = theoretical * design_pr - (pr_target * insolation * cap_dc_kwp)
        actual         = site_totals["total_energy_kwh"]
        residual_loss  = site_totals["expected_energy_kwh"] - actual
        residual_loss  = max(residual_loss, 0)

        items = [
            {"label": "Theoretical\n(GHI × DC cap)", "value": round(theoretical, 0),
             "type": "base"},
            {"label": "Optical &\nTemperature", "value": -round(optical_temp, 0),
             "type": "loss"},
            {"label": "Inverter &\nCabling", "value": -round(inverter_loss, 0),
             "type": "loss"},
            {"label": "Curtailment &\nDowntime", "value": -round(residual_loss, 0),
             "type": "loss"},
            {"label": "Measured\nOutput", "value": round(actual, 0),
             "type": "result"},
        ]

        # Build cumulative
        cum = 0.0
        for item in items:
            if item["type"] == "base":
                cum = item["value"]
                item["bottom"] = 0.0
            elif item["type"] == "loss":
                item["bottom"] = cum + item["value"]
                cum += item["value"]
            else:
                item["bottom"] = 0.0
                cum = item["value"]
        return items

    # ── alert detection ────────────────────────────────────────

    def _detect_alerts(self, per_inv: pd.DataFrame,
                        irr_day: pd.DataFrame) -> list[dict]:
        """Produce list of alerts with root-cause and recommended fix."""
        alerts = []
        pr_target = self.cfg["operating_pr_target"]

        if per_inv.empty:
            return alerts

        # Low PR
        for _, row in per_inv.iterrows():
            if row["pr"] < (pr_target - 0.10):
                alerts.append({
                    "severity": "HIGH",
                    "inverter": row["inverter"],
                    "code": "LOW_PR",
                    "description": f"PR {row['pr']*100:.1f}% — more than 10 pp below target",
                    "likely_cause": "DC ground fault, string disconnect, or soiling event",
                    "recommended_action": (
                        "Check iSolarCloud Fault log. Perform I-V scan. "
                        "Inspect string fuses and DC combiner. "
                        "Clean any heavily soiled module rows."
                    ),
                })
            elif not row["pr_ok"]:
                alerts.append({
                    "severity": "MEDIUM",
                    "inverter": row["inverter"],
                    "code": "BELOW_TARGET_PR",
                    "description": f"PR {row['pr']*100:.1f}% — below {pr_target*100:.0f}% target",
                    "likely_cause": "Minor mismatch, soiling, or shading",
                    "recommended_action": (
                        "Review string-level data in SCADA. Schedule visual inspection."
                    ),
                })

        # Zero availability
        offline = per_inv[per_inv["availability"] == 0]
        for _, row in offline.iterrows():
            # Avoid double-alerting if already in low PR list
            if not any(a["inverter"] == row["inverter"] and a["code"] == "LOW_PR"
                       for a in alerts):
                alerts.append({
                    "severity": "HIGH",
                    "inverter": row["inverter"],
                    "code": "OFFLINE",
                    "description": "Inverter offline all day (0% availability)",
                    "likely_cause": "AC protection trip, E-stop, or communication loss",
                    "recommended_action": (
                        "Check AC breaker and E-stop status on site. "
                        "Attempt remote restart via iSolarCloud. "
                        "If communication failure, verify Ethernet / RS485 link."
                    ),
                })

        # Low availability (not zero)
        low_avail = per_inv[(per_inv["availability"] > 0) & (per_inv["availability"] < 0.85)]
        for _, row in low_avail.iterrows():
            alerts.append({
                "severity": "MEDIUM",
                "inverter": row["inverter"],
                "code": "LOW_AVAILABILITY",
                "description": f"Availability {row['availability']*100:.1f}% — below 85%",
                "likely_cause": "Intermittent fault or protective relay event during the day",
                "recommended_action": (
                    "Review fault timestamp log. Check grid voltage/frequency events. "
                    "Inspect AC relay contacts if recurring."
                ),
            })

        # No irradiance data warning
        if irr_day.empty or ("GHI" in irr_day.columns and irr_day["GHI"].sum() == 0):
            alerts.append({
                "severity": "INFO",
                "inverter": "SITE",
                "code": "NO_IRRADIANCE",
                "description": "No irradiance data available for this date",
                "likely_cause": "Pyranometer offline or data export gap",
                "recommended_action": (
                    "Check SCADA irradiance sensor channel. "
                    "SARAH satellite data can be used as a fallback."
                ),
            })

        # Sort: HIGH first, then MEDIUM, then INFO
        order = {"HIGH": 0, "MEDIUM": 1, "INFO": 2}
        alerts.sort(key=lambda a: order.get(a["severity"], 9))
        return alerts
