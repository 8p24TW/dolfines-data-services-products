#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import re
import sys
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import matplotlib

matplotlib.use("Agg")
import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_REPORT_DIR = SCRIPT_DIR.parent / "SCADA Analysis"
if str(SHARED_REPORT_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_REPORT_DIR))

from report.render_report import build_output_paths, render_report_outputs
from report.style_tokens import get_style_tokens
from wind_report import build_wind_report_assets, build_wind_report_data

warnings.filterwarnings("ignore")

DEFAULT_DATA_DIR = Path(r"C:\Users\RichardMUSI\OneDrive - Dolfines\Bureau\AI\SCADA analysis test")
DEFAULT_OUT_DIR = SCRIPT_DIR / "_windpat_output"
DEFAULT_REPORT = "WINDPAT_SCADA_Analysis_Report.pdf"

LOGO_WHITE = SHARED_REPORT_DIR / "8p2_logo_white.png"
LOGO_COLOR = SHARED_REPORT_DIR / "8p2_logo.png"
FAVICON = SHARED_REPORT_DIR / "8p2_favicon_sq.jpg"
DEFAULT_COVER = SCRIPT_DIR / "bg_wind.jpg"


def _sort_key(name: str) -> tuple[int, str]:
    match = re.search(r"(\d+)", str(name))
    return (int(match.group(1)), str(name)) if match else (9999, str(name))


def _extract_turbine_name(path: Path) -> str:
    match = re.search(r"-\s*(LU\d+)", path.name)
    return match.group(1) if match else path.stem


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def detect_site_kmz_path(explicit_path: Path | None = None) -> Path | None:
    if explicit_path:
        resolved = explicit_path.resolve()
        return resolved if resolved.exists() else None
    candidates = sorted(SCRIPT_DIR.glob("*.kmz"))
    return candidates[0] if candidates else None


def extract_site_location_from_kmz(kmz_path: Path | None) -> dict | None:
    if not kmz_path or not kmz_path.exists():
        return None

    namespaces = {
        "kml": "http://www.opengis.net/kml/2.2",
        "gx": "http://www.google.com/kml/ext/2.2",
        "atom": "http://www.w3.org/2005/Atom",
    }
    try:
        with ZipFile(kmz_path) as archive:
            kml_name = next((name for name in archive.namelist() if name.lower().endswith(".kml")), None)
            if not kml_name:
                return None
            root = ET.fromstring(archive.read(kml_name))
    except Exception:
        return None

    placemark = root.find(".//kml:Placemark", namespaces)
    if placemark is None:
        return None

    point_coordinates = placemark.findtext(".//kml:Point/kml:coordinates", default="", namespaces=namespaces).strip()
    if point_coordinates:
        parts = [part.strip() for part in point_coordinates.split(",")]
        if len(parts) >= 2:
            try:
                longitude = float(parts[0])
                latitude = float(parts[1])
            except ValueError:
                longitude = None
                latitude = None
        else:
            longitude = None
            latitude = None
    else:
        try:
            longitude = float(placemark.findtext(".//kml:LookAt/kml:longitude", default="", namespaces=namespaces))
            latitude = float(placemark.findtext(".//kml:LookAt/kml:latitude", default="", namespaces=namespaces))
        except ValueError:
            longitude = None
            latitude = None

    if longitude is None or latitude is None:
        return None

    name = placemark.findtext("kml:name", default=kmz_path.stem, namespaces=namespaces).strip() or kmz_path.stem
    return {
        "name": name,
        "latitude": latitude,
        "longitude": longitude,
        "source_path": str(kmz_path),
    }


def load_operation_data(data_dir: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for fp in sorted(data_dir.glob("Wind turbine operation data*.csv")):
        turbine = _extract_turbine_name(fp)
        df = pd.read_csv(fp, encoding="latin1", low_memory=False)
        df["ts"] = pd.to_datetime(df["date"], errors="coerce")
        df["turbine"] = turbine
        df["power_kw"] = _to_numeric(df["Power [kW]"]).clip(lower=0)
        df["wind_ms"] = _to_numeric(df["Wind [m/s]"])
        df["wind_dir_deg"] = _to_numeric(df["Wind direction [°]"])
        df["nacelle_deg"] = _to_numeric(df["Nacelle position [°]"])
        df["rotor_rpm"] = _to_numeric(df["Rotor speed [1/min]"])
        df["generator_rpm"] = _to_numeric(df["Generator speed [1/min]"])
        df["interval_s"] = _to_numeric(df["TimeInterval [s]"])
        df["counter_kwh"] = _to_numeric(df["Counter [kWh]"])
        # Optional pitch angle (column name varies by OEM)
        for _pitch_col in ("Pitch angle [°]", "Pitch angle blade A [°]", "Blade pitch angle [°]", "Mean pitch [°]"):
            if _pitch_col in df.columns:
                df["pitch_angle_deg"] = _to_numeric(df[_pitch_col])
                break
        else:
            df["pitch_angle_deg"] = np.nan
        frames.append(
            df[
                [
                    "ts",
                    "turbine",
                    "power_kw",
                    "wind_ms",
                    "wind_dir_deg",
                    "nacelle_deg",
                    "rotor_rpm",
                    "generator_rpm",
                    "interval_s",
                    "counter_kwh",
                    "pitch_angle_deg",
                ]
            ].dropna(subset=["ts"])
        )
    if not frames:
        raise FileNotFoundError(f"No wind operation CSV files found in {data_dir}")
    return pd.concat(frames, ignore_index=True).sort_values(["turbine", "ts"]).reset_index(drop=True)


def load_message_data(data_dir: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for fp in sorted(data_dir.glob("Wind turbine message data*.csv")):
        turbine = _extract_turbine_name(fp)
        df = pd.read_csv(fp, encoding="latin1", low_memory=False)
        df["turbine"] = turbine
        df["start_ts"] = pd.to_datetime(df["Start date"], errors="coerce")
        df["end_ts"] = pd.to_datetime(df["End date"], errors="coerce")
        df["duration_h"] = (df["end_ts"] - df["start_ts"]).dt.total_seconds().fillna(0) / 3600.0
        df["fault_family"] = df["Manufacturer status"].fillna(df["Error text"]).fillna("Unclassified event")
        frames.append(
            df[
                [
                    "turbine",
                    "start_ts",
                    "end_ts",
                    "duration_h",
                    "Error number",
                    "fault_family",
                    "Category",
                    "Error text",
                ]
            ].dropna(subset=["start_ts", "end_ts"])
        )
    if not frames:
        return pd.DataFrame(columns=["turbine", "start_ts", "end_ts", "duration_h", "Error number", "fault_family", "Category", "Error text"])
    return pd.concat(frames, ignore_index=True).sort_values(["turbine", "start_ts"]).reset_index(drop=True)


def derive_reference_curve(operation: pd.DataFrame, rated_power_kw: float) -> tuple[pd.Series, pd.DataFrame, pd.Series, dict[str, pd.Series]]:
    valid = operation.dropna(subset=["wind_ms", "power_kw"]).copy()
    valid = valid[(valid["wind_ms"] >= 0) & (valid["wind_ms"] <= 28)]
    bins = np.arange(0.0, 28.5, 0.5)
    valid["wind_bin"] = pd.cut(valid["wind_ms"], bins=bins, include_lowest=True, right=False)
    grouped = valid.groupby("wind_bin")["power_kw"]
    reference = grouped.quantile(0.9)
    reference_counts = grouped.count()
    centers = pd.Index([(interval.left + interval.right) / 2.0 for interval in reference.index], name="wind_ms")
    reference = pd.Series(reference.to_numpy(dtype=float), index=centers).interpolate(limit_direction="both")
    reference_counts = pd.Series(reference_counts.to_numpy(dtype=float), index=centers)
    reference = reference.rolling(3, min_periods=1, center=True).mean().clip(lower=0, upper=rated_power_kw)
    binned_rows = []
    turbine_counts: dict[str, pd.Series] = {}
    for turbine, subset in valid.groupby("turbine"):
        per_bin = subset.groupby("wind_bin")["power_kw"].median()
        per_bin_counts = subset.groupby("wind_bin")["power_kw"].count()
        per_bin.index = centers
        per_bin = per_bin.reindex(centers).interpolate(limit_direction="both").clip(lower=0, upper=rated_power_kw)
        turbine_counts[turbine] = pd.Series(per_bin_counts.to_numpy(dtype=float), index=centers)
        binned_rows.append(pd.DataFrame({"turbine": turbine, "wind_ms": per_bin.index, "power_kw": per_bin.values}))
    binned = pd.concat(binned_rows, ignore_index=True) if binned_rows else pd.DataFrame(columns=["turbine", "wind_ms", "power_kw"])
    return reference, binned, reference_counts, turbine_counts


def interpolate_expected_power(wind_values: pd.Series, reference_curve: pd.Series) -> np.ndarray:
    x = reference_curve.index.to_numpy(dtype=float)
    y = reference_curve.to_numpy(dtype=float)
    return np.interp(wind_values.to_numpy(dtype=float), x, y, left=0.0, right=0.0)


def build_analysis(operation: pd.DataFrame, messages: pd.DataFrame, tariff_eur_per_kwh: float) -> tuple[dict, dict]:
    interval_minutes = float(operation["interval_s"].dropna().median() / 60.0) if operation["interval_s"].notna().any() else 5.0
    interval_h = interval_minutes / 60.0
    turbines = sorted(operation["turbine"].unique(), key=_sort_key)
    rated_power_kw = float(np.nanmedian(operation.groupby("turbine")["power_kw"].quantile(0.995)))
    cap_ac_kw = rated_power_kw * len(turbines)
    period_start = operation["ts"].min()
    period_end = operation["ts"].max()
    analysis_duration_days = max((period_end - period_start).total_seconds() / 86400.0 + interval_h / 24.0, 1.0)
    annualization_factor = 365.25 / analysis_duration_days

    expected_index = pd.date_range(period_start.floor("D"), period_end.ceil("D"), freq=f"{int(interval_minutes)}min")
    power_pivot = operation.pivot_table(index="ts", columns="turbine", values="power_kw", aggfunc="mean").reindex(expected_index)
    wind_pivot = operation.pivot_table(index="ts", columns="turbine", values="wind_ms", aggfunc="mean").reindex(expected_index)
    dir_pivot = operation.pivot_table(index="ts", columns="turbine", values="wind_dir_deg", aggfunc="mean").reindex(expected_index)

    power_completeness = (power_pivot.notna().mean() * 100).sort_index(key=lambda idx: [_sort_key(item) for item in idx])
    wind_completeness = (wind_pivot.notna().mean() * 100).sort_index(key=lambda idx: [_sort_key(item) for item in idx])
    dir_completeness = (dir_pivot.notna().mean() * 100).sort_index(key=lambda idx: [_sort_key(item) for item in idx])
    monthly_power_completeness = (power_pivot.notna().resample("ME").mean() * 100).round(1)

    reference_curve, binned_curves, reference_counts, turbine_curve_counts = derive_reference_curve(operation, rated_power_kw)
    op = operation.copy()
    op["expected_kw"] = interpolate_expected_power(op["wind_ms"].fillna(0), reference_curve)
    op["potential_mwh"] = op["expected_kw"] * interval_h / 1000.0
    op["actual_mwh"] = op["power_kw"] * interval_h / 1000.0
    op["eligible"] = op["expected_kw"] >= rated_power_kw * 0.15
    op["available_flag"] = np.where(op["eligible"], op["power_kw"] >= np.maximum(op["expected_kw"] * 0.1, rated_power_kw * 0.03), np.nan)
    op["availability_loss_mwh"] = np.where(op["eligible"] & (op["available_flag"] == 0), np.maximum(op["expected_kw"] - op["power_kw"], 0) * interval_h / 1000.0, 0.0)
    op["performance_loss_mwh"] = np.where(op["eligible"] & (op["available_flag"] == 1), np.maximum(op["expected_kw"] - op["power_kw"], 0) * interval_h / 1000.0, 0.0)

    monthly = op.groupby(pd.Grouper(key="ts", freq="ME")).agg(
        energy_mwh=("actual_mwh", "sum"),
        potential_mwh=("potential_mwh", "sum"),
        availability_loss_mwh=("availability_loss_mwh", "sum"),
        performance_loss_mwh=("performance_loss_mwh", "sum"),
        wind_speed_ms=("wind_ms", "mean"),
    )
    hours_per_month = monthly.index.days_in_month * 24
    monthly["capacity_factor_pct"] = monthly["energy_mwh"] * 1000.0 / (cap_ac_kw * hours_per_month) * 100.0
    monthly["performance_index_pct"] = monthly["energy_mwh"] / monthly["potential_mwh"].replace(0, np.nan) * 100.0

    site_daily = op.groupby(pd.Grouper(key="ts", freq="D")).agg(energy_mwh=("actual_mwh", "sum"))
    site_daily["specific_yield"] = site_daily["energy_mwh"] * 1000.0 / cap_ac_kw
    site_daily["rolling_30d"] = site_daily["specific_yield"].rolling(30, center=True, min_periods=5).mean()

    fleet = op.groupby("turbine").agg(
        actual_mwh=("actual_mwh", "sum"),
        potential_mwh=("potential_mwh", "sum"),
        availability_loss_mwh=("availability_loss_mwh", "sum"),
        performance_loss_mwh=("performance_loss_mwh", "sum"),
        eligible_intervals=("eligible", "sum"),
        available_intervals=("available_flag", "sum"),
    )
    fleet["availability_pct"] = fleet["available_intervals"] / fleet["eligible_intervals"].replace(0, np.nan) * 100.0
    fleet["performance_index_pct"] = fleet["actual_mwh"] / fleet["potential_mwh"].replace(0, np.nan) * 100.0
    fleet["recoverable_mwh"] = fleet["availability_loss_mwh"] + fleet["performance_loss_mwh"]
    fleet["recoverable_eur"] = fleet["recoverable_mwh"] * 1000.0 * tariff_eur_per_kwh
    fleet["recoverable_mwh_year"] = fleet["recoverable_mwh"] * annualization_factor
    fleet["recoverable_eur_year"] = fleet["recoverable_eur"] * annualization_factor

    valid_messages = messages.copy()
    if not valid_messages.empty:
        exclude_patterns = ("lowstartcondition", "lowyavenable", "wtg system ok")
        valid_messages = valid_messages[
            ~valid_messages["fault_family"].str.lower().fillna("").str.contains("|".join(exclude_patterns), regex=True)
        ].copy()
        fault_family_summary = (
            valid_messages.groupby(["fault_family", "turbine"], as_index=False)
            .agg(duration_h=("duration_h", "sum"), count=("fault_family", "size"))
            .sort_values(["duration_h", "count"], ascending=False)
        )
        fault_family_summary["operational_implication"] = "Inspect the repeated fault family and associated subsystem."
        top_fault_by_turbine = (
            fault_family_summary.sort_values(["turbine", "duration_h"], ascending=[True, False])
            .drop_duplicates("turbine")
            .set_index("turbine")["fault_family"]
        )
    else:
        fault_family_summary = pd.DataFrame(columns=["fault_family", "turbine", "duration_h", "count", "operational_implication"])
        top_fault_by_turbine = pd.Series(dtype="object")

    fleet["top_fault_family"] = fleet.index.to_series().map(top_fault_by_turbine).fillna("")
    fleet["downtime_h"] = fleet["availability_loss_mwh"] * 1000.0 / rated_power_kw
    fleet = fleet.sort_index(key=lambda idx: [_sort_key(item) for item in idx])

    potential_mwh = float(op["potential_mwh"].sum())
    actual_mwh = float(op["actual_mwh"].sum())
    availability_loss_mwh = float(op["availability_loss_mwh"].sum())
    performance_loss_mwh = float(op["performance_loss_mwh"].sum())
    residual_mwh = max(potential_mwh - actual_mwh - availability_loss_mwh - performance_loss_mwh, 0.0)
    recoverable_mwh = availability_loss_mwh + performance_loss_mwh

    punchlist: list[dict] = []
    for turbine, row in fleet.sort_values("recoverable_eur", ascending=False).iterrows():
        if row["recoverable_mwh"] <= 1.0:
            continue
        category = "Availability" if row["availability_loss_mwh"] >= row["performance_loss_mwh"] else "Performance"
        issue = (
            f"{turbine} is losing wind-resource capture through repeated downtime during wind-eligible intervals."
            if category == "Availability"
            else f"{turbine} remains available but underperforms the fleet reference power curve."
        )
        action = (
            f"Review recurring stop conditions on {turbine}, inspect the dominant subsystem alerts, and confirm return-to-service latency."
            if category == "Availability"
            else f"Perform a targeted power-curve review on {turbine}, including anemometry, yaw alignment, pitch behaviour, and control settings."
        )
        eur_loss = float(row["recoverable_eur"])
        eur_loss_year = float(row["recoverable_eur_year"])
        punchlist.append(
            {
                "priority": "HIGH" if eur_loss_year >= 5000 else "MEDIUM",
                "category": category,
                "issue": issue,
                "action": action,
                "mwh_loss": float(row["recoverable_mwh"]),
                "mwh_loss_year": float(row["recoverable_mwh_year"]),
                "eur_loss": eur_loss,
                "eur_loss_year": eur_loss_year,
            }
        )
    if not fault_family_summary.empty:
        for _, row in fault_family_summary.head(3).iterrows():
            eur_loss = float(min(availability_loss_mwh * 0.25, row["duration_h"] * rated_power_kw / 1000.0) * 1000.0 * tariff_eur_per_kwh)
            eur_loss_year = eur_loss * annualization_factor
            punchlist.append(
                {
                    "priority": "HIGH" if eur_loss_year >= 5000 else "MEDIUM",
                    "category": "Reliability",
                    "issue": f"{row['fault_family']} is a recurring downtime driver, particularly on {row['turbine']}.",
                    "action": "Review the underlying subsystem history, confirm spare-parts strategy, and close the recurrence root cause.",
                    "mwh_loss": eur_loss / (1000.0 * tariff_eur_per_kwh) if tariff_eur_per_kwh else 0.0,
                    "mwh_loss_year": (eur_loss / (1000.0 * tariff_eur_per_kwh) * annualization_factor) if tariff_eur_per_kwh else 0.0,
                    "eur_loss": eur_loss,
                    "eur_loss_year": eur_loss_year,
                }
            )
    if float(power_completeness.min()) < 97:
        dq_loss_eur = recoverable_mwh * 1000.0 * tariff_eur_per_kwh * 0.05
        punchlist.append(
            {
                "priority": "MEDIUM",
                "category": "Data quality",
                "issue": "Telemetry completeness is uneven across the fleet, which weakens confidence in month-specific attribution.",
                "action": "Stabilise missing data channels and verify SCADA historian continuity before the next diagnostic cycle.",
                "mwh_loss": recoverable_mwh * 0.05,
                "mwh_loss_year": recoverable_mwh * 0.05 * annualization_factor,
                "eur_loss": dq_loss_eur,
                "eur_loss_year": dq_loss_eur * annualization_factor,
            }
        )
    punchlist = sorted(punchlist, key=lambda item: item["eur_loss_year"], reverse=True)[:8]

    # Per-turbine monthly availability
    turbine_monthly_avail = {}
    for turbine in turbines:
        t_op = op[op["turbine"] == turbine].copy()
        t_monthly = t_op.groupby(pd.Grouper(key="ts", freq="ME")).apply(
            lambda df: float(df.loc[df["eligible"], "available_flag"].mean() * 100.0)
            if df["eligible"].any() else np.nan
        )
        turbine_monthly_avail[turbine] = t_monthly

    # Wind rose data per turbine (sampled)
    wind_rose_data = {}
    for turbine, grp in operation.groupby("turbine"):
        wd = grp[["wind_dir_deg", "wind_ms"]].dropna()
        wind_rose_data[turbine] = wd.sample(min(len(wd), 8000), random_state=42) if len(wd) > 8000 else wd.copy()

    # RPM scatter per turbine
    rpm_scatter_data = {}
    for turbine, grp in operation.groupby("turbine"):
        rpm_data = grp[["rotor_rpm", "power_kw"]].dropna()
        rpm_data = rpm_data[(rpm_data["rotor_rpm"] > 0) & (rpm_data["power_kw"] >= 0)]
        rpm_scatter_data[turbine] = rpm_data.sample(min(len(rpm_data), 3000), random_state=42) if len(rpm_data) > 3000 else rpm_data.copy()

    # Monthly power curve data per turbine
    monthly_pc_data = {}
    bins_edges = np.arange(0.0, 26.0, 1.0)
    bin_centers = [(bins_edges[i] + bins_edges[i+1]) / 2.0 for i in range(len(bins_edges)-1)]
    for turbine, grp in operation.groupby("turbine"):
        m_curves = {}
        grp = grp.dropna(subset=["wind_ms", "power_kw"])
        for period, m_grp in grp.groupby(pd.Grouper(key="ts", freq="ME")):
            if len(m_grp) < 20:
                continue
            m_grp = m_grp.copy()
            m_grp["wind_bin"] = pd.cut(m_grp["wind_ms"], bins=bins_edges, include_lowest=True, right=False)
            curve = m_grp.groupby("wind_bin", observed=False)["power_kw"].median()
            m_curves[period.strftime("%Y-%m")] = pd.Series(curve.values, index=bin_centers)
        monthly_pc_data[turbine] = m_curves

    # Pitch scatter per turbine (if available)
    pitch_scatter_data = {}
    if "pitch_angle_deg" in operation.columns and operation["pitch_angle_deg"].notna().any():
        for turbine, grp in operation.groupby("turbine"):
            p_data = grp[["pitch_angle_deg", "power_kw"]].dropna()
            p_data = p_data[(p_data["power_kw"] >= 0)]
            pitch_scatter_data[turbine] = p_data.sample(min(len(p_data), 3000), random_state=42) if len(p_data) > 3000 else p_data.copy()

    # Log code frequency summary
    if not messages.empty and "Error number" in messages.columns:
        lc_summary = (
            messages.dropna(subset=["Error number"])
            .assign(**{"Error number": lambda x: x["Error number"].astype(str).str.strip()})
            .groupby(["Error number", "Error text", "Category"], as_index=False, dropna=False)
            .agg(count=("Error number", "size"), total_duration_h=("duration_h", "sum"))
            .sort_values("count", ascending=False)
            .head(10)
        )
    else:
        lc_summary = pd.DataFrame(columns=["Error number", "Error text", "Category", "count", "total_duration_h"])

    config = {
        "site_name": "WINDPAT Wind Farm",
        "report_title": "WINDPAT Wind Farm",
        "n_turbines": len(turbines),
        "rated_power_kw": rated_power_kw,
        "cap_ac_kw": cap_ac_kw,
        "interval_minutes": interval_minutes,
        "tariff_eur_per_kwh": tariff_eur_per_kwh,
        "capacity_factor_target_pct": 35.0,
    }

    analysis = {
        "period_start": period_start,
        "period_end": period_end,
        "period_days": analysis_duration_days,
        "annualization_factor": annualization_factor,
        "data_quality": {
            "overall_power_pct": float(power_completeness.mean()),
            "overall_wind_pct": float(wind_completeness.mean()),
            "overall_direction_pct": float(dir_completeness.mean()),
            "power_completeness": power_completeness.to_dict(),
            "monthly_power_completeness": monthly_power_completeness,
            "valid_operating_records": int(op[["power_kw", "wind_ms"]].dropna().shape[0]),
        },
        "performance": {
            "monthly": monthly,
            "actual_energy_mwh": actual_mwh,
            "potential_energy_mwh": potential_mwh,
            "fleet_performance_index_pct": float(actual_mwh / potential_mwh * 100.0) if potential_mwh else np.nan,
            "daily_specific_yield": site_daily,
        },
        "fleet": fleet,
        "availability": {
            "site_availability_pct": float(fleet["available_intervals"].sum() / fleet["eligible_intervals"].sum() * 100.0) if fleet["eligible_intervals"].sum() else np.nan,
            "site_monthly": op.assign(month=op["ts"].dt.to_period("M").dt.to_timestamp("M")).groupby("month").apply(lambda df: float(df.loc[df["eligible"], "available_flag"].mean() * 100.0) if df["eligible"].any() else np.nan),
        },
        "losses": {
            "potential_mwh": potential_mwh,
            "actual_mwh": actual_mwh,
            "availability_loss_mwh": availability_loss_mwh,
            "performance_loss_mwh": performance_loss_mwh,
            "residual_mwh": residual_mwh,
            "recoverable_loss_mwh": recoverable_mwh,
            "recoverable_loss_eur": recoverable_mwh * 1000.0 * tariff_eur_per_kwh,
            "recoverable_loss_mwh_year": recoverable_mwh * annualization_factor,
            "recoverable_loss_eur_year": recoverable_mwh * 1000.0 * tariff_eur_per_kwh * annualization_factor,
            "monthly_availability_loss_mwh": monthly["availability_loss_mwh"],
            "waterfall": {
                "potential_mwh": potential_mwh,
                "availability_loss_mwh": availability_loss_mwh,
                "performance_loss_mwh": performance_loss_mwh,
                "residual_mwh": residual_mwh,
                "actual_mwh": actual_mwh,
            },
        },
        "messages": {
            "fault_family_summary": fault_family_summary,
            "log_code_summary": lc_summary,
        },
        "power_curve": {
            "reference_curve": reference_curve,
            "reference_curve_counts": reference_counts,
            "binned_by_turbine": {turbine: grp.set_index("wind_ms")["power_kw"] for turbine, grp in binned_curves.groupby("turbine")},
            "binned_counts_by_turbine": turbine_curve_counts,
            "scatter_by_turbine": {
                turbine: (
                    grp[["wind_ms", "power_kw"]].dropna()
                    .pipe(lambda df: df.sample(min(len(df), 3000), random_state=42) if len(df) > 3000 else df)
                )
                for turbine, grp in op.groupby("turbine")
            },
        },
        "punchlist": punchlist,
        "availability_monthly_by_turbine": turbine_monthly_avail,
        "wind_rose_data": wind_rose_data,
        "rpm_scatter_data": rpm_scatter_data,
        "monthly_pc_data": monthly_pc_data,
        "pitch_scatter_data": pitch_scatter_data,
    }
    return config, analysis


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate WINDPAT wind-farm SCADA reports.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--assets-dir", type=Path, default=None)
    parser.add_argument("--output-format", choices=["html", "pdf"], default="pdf")
    parser.add_argument("--pdf-engine", choices=["auto", "playwright", "weasyprint"], default="auto")
    parser.add_argument("--keep-html", action="store_true")
    parser.add_argument("--debug-layout", action="store_true")
    parser.add_argument("--cover-image-path", type=Path, default=DEFAULT_COVER)
    parser.add_argument("--site-kmz-path", type=Path, default=None)
    parser.add_argument("--report-name", default=DEFAULT_REPORT)
    parser.add_argument("--tariff-eur-per-kwh", type=float, default=0.09)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_dir = args.data_dir.resolve()
    output_dir = args.output_dir.resolve()
    assets_dir = args.assets_dir.resolve() if args.assets_dir else None

    operation = load_operation_data(data_dir)
    messages = load_message_data(data_dir)
    derived_config, analysis = build_analysis(operation, messages, args.tariff_eur_per_kwh)

    # Override rated power with Nordex N131 nameplate spec (SCADA 99.5th percentile
    # slightly overshoots due to boost mode; nameplate is 3,900 kW per turbine).
    RATED_KW_SPEC = 3900.0
    derived_config["rated_power_kw"] = RATED_KW_SPEC
    derived_config["cap_ac_kw"] = RATED_KW_SPEC * derived_config["n_turbines"]
    derived_config["turbine_manufacturer"] = "nordex"
    derived_config["turbine_model_id"] = "n131_3900"

    site_kmz_path = detect_site_kmz_path(args.site_kmz_path)
    site_location = extract_site_location_from_kmz(site_kmz_path)

    config = {
        **derived_config,
        "data_dir": data_dir,
        "output_dir": output_dir,
        "report_name": args.report_name,
        "style_tokens": get_style_tokens(debug_layout=args.debug_layout),
        "logo_white": LOGO_WHITE,
        "logo_color": LOGO_COLOR,
        "favicon": FAVICON,
        "cover_image_path": args.cover_image_path,
        "site_kmz_path": site_kmz_path,
        "site_location": site_location,
    }

    output_paths = build_output_paths(
        output_dir=output_dir,
        assets_dir=assets_dir,
        report_name=args.report_name,
        output_format=args.output_format,
        keep_html=args.keep_html,
        pdf_engine=args.pdf_engine,
    )
    charts = build_wind_report_assets(config=config, analysis=analysis, assets_dir=output_paths["assets_dir"])
    report_data = build_wind_report_data(config=config, analysis=analysis, charts=charts, outputs=output_paths)
    results = render_report_outputs(
        report_data=report_data,
        output_paths=output_paths,
        template_dir=SHARED_REPORT_DIR / "report" / "templates",
        static_dir=SHARED_REPORT_DIR / "report" / "static",
    )

    print("WINDPAT report generated.")
    if results.get("html_path"):
        print(f"HTML: {results['html_path']}")
    if results.get("pdf_path"):
        print(f"PDF: {results['pdf_path']}")
        print(f"PDF engine: {results.get('pdf_engine_used')}")
    print(f"Assets: {results['assets_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
