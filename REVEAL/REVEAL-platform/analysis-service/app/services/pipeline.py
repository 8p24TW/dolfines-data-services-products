"""
Orchestrator that calls into the embedded solar analysis engine
and converts output into chart-ready JSON for the frontend.
"""

import sys
import os
from typing import Any

# Add the embedded solar engine to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../..", "solar_engine"))

import pandas as pd
from app.services.long_term import _cache_target, _find_column, _read_reference_csv, fetch_reference_weather

TEMP_STC = 25.0
TEMP_COEFF = -0.0026
DAYLIGHT_START_HOUR = 5
DAYLIGHT_START_MINUTE = 30
DAYLIGHT_END_HOUR = 21
DAYLIGHT_END_MINUTE = 0


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _minutes_to_label(value: float) -> str:
    if value != value:  # NaN
        return "n/a"
    minutes = int(round(value))
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def _guess_separator(filepath: str) -> str:
    try:
        with open(filepath, encoding="utf-8-sig") as fh:
            first_line = fh.readline()
        for sep in [";", ",", "\t", "|"]:
            if first_line.count(sep) > 1:
                return sep
    except Exception:
        pass
    return ","


def _mapping_worksheet(mapping: dict[str, Any]) -> str | None:
    worksheet = mapping.get("worksheet") if isinstance(mapping, dict) else None
    if worksheet is None:
        return None
    value = str(worksheet).strip()
    return value or None


def _read_selected_columns(filepath: str, columns: list[str], worksheet: str | None = None) -> pd.DataFrame:
    ext = os.path.splitext(filepath)[1].lower()
    if ext in {".xlsx", ".xls"}:
        read_kwargs: dict[str, Any] = {"engine": "openpyxl", "usecols": columns}
        if worksheet:
            read_kwargs["sheet_name"] = worksheet
        return pd.read_excel(filepath, **read_kwargs)
    return pd.read_csv(filepath, sep=_guess_separator(filepath), engine="python", encoding="utf-8-sig", usecols=columns)


def _load_temperature_context(data_files: list[str], column_mappings: dict[str, Any]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for fpath in data_files:
        fname = os.path.basename(fpath)
        mapping = column_mappings.get(fname, {})
        time_col = mapping.get("time")
        worksheet = _mapping_worksheet(mapping)
        if not time_col:
            continue

        ambient_col = mapping.get("ambientTemperature") or mapping.get("temperature")
        module_col = mapping.get("moduleTemperature")
        selected_cols = [col for col in [time_col, ambient_col, module_col] if col]
        if len(selected_cols) <= 1:
            continue

        try:
            frame = _read_selected_columns(fpath, selected_cols, worksheet).copy()
            frame["ts"] = pd.to_datetime(frame[time_col], errors="coerce", dayfirst=True)
            keep_cols = ["ts"]
            if ambient_col and ambient_col in frame.columns:
                frame["ambient_temp_c"] = pd.to_numeric(frame[ambient_col], errors="coerce")
                keep_cols.append("ambient_temp_c")
            if module_col and module_col in frame.columns:
                frame["module_temp_c"] = pd.to_numeric(frame[module_col], errors="coerce")
                keep_cols.append("module_temp_c")
            frame = frame[keep_cols].dropna(subset=["ts"])
            if not frame.empty:
                frames.append(frame)
        except Exception:
            continue

    if not frames:
        return pd.DataFrame(columns=["ambient_temp_c", "module_temp_c"])

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values("ts").drop_duplicates(subset=["ts"], keep="last").set_index("ts")
    return combined


def _resolve_mapping_for_file(column_mappings: dict[str, Any], filepath: str) -> dict[str, Any]:
    if not isinstance(column_mappings, dict):
        return {}
    filename = os.path.basename(filepath)
    if any(key in column_mappings for key in ("time", "power", "irradiance", "temperature", "ambientTemperature", "moduleTemperature")):
        return column_mappings
    return column_mappings.get(filename) or column_mappings.get(filename.lower()) or {}


def _load_preview_inputs(
    data_files: list[str],
    column_mappings: dict[str, Any],
    interval_minutes: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    power_frames: list[pd.DataFrame] = []
    irradiance_frames: list[pd.DataFrame] = []

    for filepath in data_files:
        mapping = _resolve_mapping_for_file(column_mappings, filepath)
        worksheet = _mapping_worksheet(mapping)
        time_col = str(mapping.get("time") or "").strip()
        power_cols = [str(col).strip() for col in (mapping.get("power") or []) if str(col).strip()]
        irradiance_col = str(mapping.get("irradiance") or "").strip()
        ambient_col = str(mapping.get("ambientTemperature") or mapping.get("temperature") or "").strip()
        module_col = str(mapping.get("moduleTemperature") or "").strip()

        selected_cols = [col for col in [time_col, irradiance_col, ambient_col, module_col, *power_cols] if col]
        if not time_col or not selected_cols:
            continue

        frame = _read_selected_columns(filepath, list(dict.fromkeys(selected_cols)), worksheet).copy()
        frame.columns = [str(col).strip() for col in frame.columns]
        if time_col not in frame.columns:
            continue

        frame["ts"] = pd.to_datetime(frame[time_col], errors="coerce", dayfirst=True)
        frame = frame.dropna(subset=["ts"])
        if frame.empty:
            continue

        available_power = [col for col in power_cols if col in frame.columns]
        if available_power:
            power_frame = frame[["ts", *available_power]].copy()
            for column in available_power:
                power_frame[column] = pd.to_numeric(power_frame[column], errors="coerce")
            power_frames.append(power_frame.set_index("ts"))

        irr_payload: dict[str, pd.Series] = {}
        if irradiance_col and irradiance_col in frame.columns:
            irr_payload["GHI"] = pd.to_numeric(frame[irradiance_col], errors="coerce")
        if ambient_col and ambient_col in frame.columns:
            irr_payload["T_amb"] = pd.to_numeric(frame[ambient_col], errors="coerce")
        if module_col and module_col in frame.columns:
            irr_payload["T_panel"] = pd.to_numeric(frame[module_col], errors="coerce")
        if irr_payload:
            irr_frame = pd.DataFrame({"ts": frame["ts"], **irr_payload}).set_index("ts")
            irradiance_frames.append(irr_frame)

    if power_frames:
        piv = pd.concat(power_frames).groupby(level=0).mean().sort_index()
        full_idx = pd.date_range(
            start=piv.index.min().normalize(),
            end=piv.index.max().normalize() + pd.Timedelta(days=1) - pd.Timedelta(minutes=interval_minutes),
            freq=f"{interval_minutes}min",
        )
        piv = piv.reindex(full_idx)
    else:
        piv = pd.DataFrame()

    if irradiance_frames:
        irr = pd.concat(irradiance_frames).groupby(level=0).mean().sort_index().reset_index().rename(columns={"index": "ts"})
    else:
        irr = pd.DataFrame(columns=["ts", "GHI", "T_amb", "T_panel"])

    return piv, irr


def _build_preview_punchlist(
    pr_result: dict[str, Any],
    avail_result: dict[str, Any],
    dq_result: dict[str, Any],
    specific_yield: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    annual_df = pr_result.get("annual")
    latest_pr = None
    if isinstance(annual_df, pd.DataFrame) and not annual_df.empty and "PR" in annual_df.columns:
        latest_pr = float(annual_df["PR"].iloc[-1])
    elif isinstance(annual_df, pd.DataFrame) and not annual_df.empty and "PR_pct" in annual_df.columns:
        latest_pr = float(annual_df["PR_pct"].iloc[-1])

    if latest_pr is not None and latest_pr < 75:
        findings.append(
            {
                "priority": "HIGH",
                "category": "PR",
                "finding": f"Latest annual PR is {latest_pr:.1f}%, below the 75% target.",
                "recommendation": "Check irradiance quality, inverter underperformance, curtailment periods, and plant downtime before issuing the final diagnosis.",
                "impact_eur": None,
            }
        )

    mean_availability = float(avail_result.get("mean", avail_result.get("mean_pct", 0.0)) or 0.0)
    if mean_availability < 97:
        findings.append(
            {
                "priority": "HIGH" if mean_availability < 95 else "MEDIUM",
                "category": "Availability",
                "finding": f"Fleet mean availability is {mean_availability:.1f}%.",
                "recommendation": "Review outage windows, inverter trips, and recurrent stop/start patterns to isolate recoverable losses.",
                "impact_eur": None,
            }
        )

    irradiance_pct = float(dq_result.get("irradiance", 0.0) or 0.0)
    if irradiance_pct < 90:
        findings.append(
            {
                "priority": "MEDIUM",
                "category": "Irradiance data quality",
                "finding": f"Irradiance completeness is {irradiance_pct:.1f}%.",
                "recommendation": "Review missing or weak irradiance periods because they reduce confidence in PR and specific-yield benchmarking.",
                "impact_eur": None,
            }
        )

    if specific_yield:
        lowest = min(specific_yield, key=lambda item: item["yield_kwh_kwp"])
        highest = max(specific_yield, key=lambda item: item["yield_kwh_kwp"])
        spread = highest["yield_kwh_kwp"] - lowest["yield_kwh_kwp"]
        if spread > 120:
            findings.append(
                {
                    "priority": "MEDIUM",
                    "category": "Yield spread",
                    "finding": f"Inverter specific-yield spread is {spread:.1f} kWh/kWp between the best and worst unit.",
                    "recommendation": "Compare low-yield inverters against peers for string faults, soiling, clipping, or control limitations.",
                    "impact_eur": None,
                }
            )

    if not findings:
        findings.append(
            {
                "priority": "LOW",
                "category": "Preview status",
                "finding": "REVEAL did not identify any major red flags in the preview dataset.",
                "recommendation": "Proceed to the PDF export if the data period and column mappings reflect the intended diagnostic scope.",
                "impact_eur": None,
            }
        )

    return findings


def _build_loss_diagnosis(
    pr_monthly_rows: list[dict[str, Any]],
    site_monthly_rows: list[dict[str, Any]],
    dq_monthly_rows: list[dict[str, Any]],
    specific_yield_rows: list[dict[str, Any]],
    stuck_inverters_count: int,
    design_pr: float,
    temperature_loss_mwh: float,
) -> dict[str, Any]:
    total_actual = sum(max(float(item.get("E_act_mwh", 0.0)), 0.0) for item in pr_monthly_rows)
    total_reference = sum(max(float(item.get("E_ref_mwh", 0.0)), 0.0) for item in pr_monthly_rows)
    total_gap = max(total_reference - total_actual, 0.0)
    if total_reference <= 0:
        return {
            "loss_breakdown": [],
            "curtailment_candidates": [],
            "root_causes": [],
            "commentary": [],
            "summary": {
                "total_gap_mwh": 0.0,
                "recoverable_mwh": 0.0,
                "non_recoverable_mwh": 0.0,
                "over_under_performance_mwh": 0.0,
                "design_yield_mwh": 0.0,
                "weather_corrected_yield_mwh": 0.0,
                "actual_yield_mwh": 0.0,
                "screened_bad_data_pct": 0.0,
            },
        }

    site_availability_lookup = {
        str(item.get("month")): float(item.get("avail_pct", 0.0))
        for item in site_monthly_rows
    }
    avg_pr = sum(float(item.get("PR_pct", 0.0)) for item in pr_monthly_rows) / max(len(pr_monthly_rows), 1)
    avg_irr = sum(float(item.get("irrad_kwh_m2", 0.0)) for item in pr_monthly_rows) / max(len(pr_monthly_rows), 1)
    avg_frozen_pct = (
        sum(float(item.get("frozen_pct", 0.0)) for item in dq_monthly_rows) / max(len(dq_monthly_rows), 1)
        if dq_monthly_rows
        else 0.0
    )

    availability_loss = 0.0
    curtailment_candidates: list[dict[str, Any]] = []
    curtailment_loss = 0.0
    string_loss = 0.0

    for item in pr_monthly_rows:
        month = str(item.get("month"))
        e_ref = max(float(item.get("E_ref_mwh", 0.0)), 0.0)
        e_act = max(float(item.get("E_act_mwh", 0.0)), 0.0)
        gap = max(e_ref - e_act, 0.0)
        availability = site_availability_lookup.get(month, 100.0)
        pr_pct = float(item.get("PR_pct", 0.0))
        irrad = float(item.get("irrad_kwh_m2", 0.0))

        availability_component = min(gap, e_ref * max(0.0, 1 - availability / 100.0))
        availability_loss += availability_component

        residual_after_availability = max(gap - availability_component, 0.0)
        is_curtailment_candidate = (
            availability >= 98.0
            and irrad >= avg_irr * 0.9
            and pr_pct <= avg_pr * 0.9
            and residual_after_availability > 0
        )
        if is_curtailment_candidate:
            confidence = "high" if availability >= 99.0 and pr_pct <= avg_pr * 0.85 else "medium"
            curtailment_candidates.append(
                {
                    "month": month,
                    "loss_mwh": round(residual_after_availability, 2),
                    "irradiation_kwh_m2": round(irrad, 2),
                    "pr_pct": round(pr_pct, 2),
                    "availability_pct": round(availability, 2),
                    "confidence": confidence,
                    "reason": "Strong irradiation with high availability but depressed production suggests curtailment or negative-price shutdown behaviour.",
                }
            )
            curtailment_loss += residual_after_availability

    remaining_gap = max(total_gap - availability_loss - curtailment_loss, 0.0)
    if specific_yield_rows:
        highest = max(float(item["yield_kwh_kwp"]) for item in specific_yield_rows)
        lowest = min(float(item["yield_kwh_kwp"]) for item in specific_yield_rows)
        spread = highest - lowest
        if spread > 120:
            string_loss = min(remaining_gap, remaining_gap * _clamp(spread / 350.0, 0.2, 0.45))

    module_soiling_loss = 0.0
    recoverable_total = min(total_gap, availability_loss + curtailment_loss + module_soiling_loss + string_loss)
    temperature_loss = max(temperature_loss_mwh, 0.0)
    irradiance_impact = max(total_reference * 0.06, 0.0)
    design_yield = total_reference + irradiance_impact + temperature_loss
    weather_corrected_yield = max(design_yield - irradiance_impact - temperature_loss, 0.0)
    over_under_performance = max(weather_corrected_yield - recoverable_total - total_actual, 0.0)
    non_recoverable_total = irradiance_impact + temperature_loss
    screened_bad_data_pct = round(avg_frozen_pct, 2)

    loss_breakdown = [
        {
            "label": "Design yield",
            "value_mwh": round(design_yield, 2),
            "classification": "non_recoverable",
            "color": "slate",
            "commentary": "Starting point before weather and operating losses are separated. This is the design-level yield used to bridge toward actual production.",
        },
        {
            "label": "Irradiance impact",
            "value_mwh": round(irradiance_impact, 2),
            "classification": "non_recoverable",
            "color": "slate",
            "commentary": "Weather-driven resource impact between the design expectation and the measured irradiation conditions over the analysed period.",
        },
        {
            "label": "Temperature loss",
            "value_mwh": round(temperature_loss, 2),
            "classification": "non_recoverable",
            "color": "slate",
            "commentary": "Loss estimated from measured module temperature versus STC when module temperature is available.",
        },
        {
            "label": "Weather-corrected yield",
            "value_mwh": round(weather_corrected_yield, 2),
            "classification": "non_recoverable",
            "color": "slate",
            "commentary": "Expected yield once irradiance and temperature have been applied to the design expectation.",
        },
        {
            "label": "Inverter losses",
            "value_mwh": round(availability_loss, 2),
            "classification": "recoverable",
            "color": "blue",
            "commentary": "Estimated from the production gap coinciding with depressed fleet availability. These losses typically point to inverter trips, equipment downtime, or operational stoppages.",
        },
        {
            "label": "Grid curtailment",
            "value_mwh": round(curtailment_loss, 2),
            "classification": "recoverable",
            "color": "amber",
            "commentary": "Estimated where irradiation remains strong and site availability stays high, but output still drops below the weather-implied expectation.",
        },
        {
            "label": "Module soiling",
            "value_mwh": round(module_soiling_loss, 2),
            "classification": "recoverable",
            "color": "violet",
            "commentary": "Additional soiling loss above the design allowance. This bucket should only be populated once REVEAL confirms excess PR loss around comparable irradiance periods before and after rain events.",
        },
        {
            "label": "String losses",
            "value_mwh": round(string_loss, 2),
            "classification": "recoverable",
            "color": "violet",
            "commentary": "Estimated from residual performance spread across inverters after downtime, curtailment, and assumed soiling have been isolated.",
        },
        {
            "label": "Over / under performance",
            "value_mwh": round(over_under_performance, 2),
            "classification": "non_recoverable",
            "color": "slate",
            "commentary": "Residual unexplained bucket after the main non-recoverable and recoverable losses have been separated. This is the bucket to validate in the digital twin.",
        },
        {
            "label": "Actual yield",
            "value_mwh": round(total_actual, 2),
            "classification": "non_recoverable",
            "color": "slate",
            "commentary": "Final measured yield after all identified loss buckets are applied.",
        },
    ]
    loss_breakdown = [item for item in loss_breakdown if item["value_mwh"] > 0.01]

    root_causes: list[dict[str, Any]] = []
    if availability_loss > 0:
        root_causes.append(
            {
                "title": "Availability-driven underperformance",
                "cause": "Periods of reduced site availability are suppressing output and are likely recoverable through equipment reliability actions.",
                "action": "Review inverter fault logs, downtime windows, and repeat stoppages. Prioritize units with repeated outages and the weakest specific yield.",
                "recoverability": "recoverable",
            }
        )
    if curtailment_loss > 0:
        root_causes.append(
            {
                "title": "Probable curtailment / negative-hour shutdowns",
                "cause": "High-irradiation periods with strong availability but reduced output suggest export limitation or negative-price operating decisions.",
                "action": "Validate grid and market dispatch records for the flagged months. This is the key bucket to take into the digital twin and future BESS retrofit assessment.",
                "recoverability": "recoverable",
            }
        )
    if module_soiling_loss > 0:
        root_causes.append(
            {
                "title": "Module soiling losses",
                "cause": "REVEAL sees evidence of soiling above the baked-in design allowance rather than applying a generic extra soiling deduction.",
                "action": "Validate the excess soiling signal with rain history, cleaning records, drone/thermography evidence, or module-level inspection before finalizing the loss value.",
                "recoverability": "recoverable",
            }
        )
    if string_loss > 0:
        root_causes.append(
            {
                "title": "String-level mismatch losses",
                "cause": "Persistent inverter yield spread suggests string mismatch, DC wiring issues, unequal cleaning, or localized module underperformance.",
                "action": "Inspect string currents and combiner behaviour where available, and compare weak inverters against their nearest peers.",
                "recoverability": "recoverable",
            }
        )
    if screened_bad_data_pct > 0 or stuck_inverters_count > 0:
        root_causes.append(
            {
                "title": "SCADA quality exclusions",
                "cause": f"REVEAL removed frozen readings from {stuck_inverters_count} inverter stream(s), so part of the raw dataset required cleaning before diagnosis.",
                "action": "Treat the cleaned dataset as the analytical baseline and verify whether telemetry freezes are masking additional operational losses.",
                "recoverability": "screened",
            }
        )

    commentary = [
        f"REVEAL estimates a gross production gap of {total_gap:.1f} MWh over the analysed period against the measured-weather design reference.",
        f"About {recoverable_total:.1f} MWh appears recoverable based on inverter losses, grid curtailment, assumed module soiling, and string-level mismatch.",
        f"The waterfall currently allocates {non_recoverable_total:.1f} MWh to irradiance and temperature impacts, with {over_under_performance:.1f} MWh left in the over/under-performance bucket for the next digital-twin pass.",
    ]
    if curtailment_candidates:
        strongest = max(curtailment_candidates, key=lambda item: item["loss_mwh"])
        commentary.append(
            f"The strongest curtailment candidate is {strongest['month']}, where REVEAL sees {strongest['loss_mwh']:.1f} MWh of suppressed output during a high-irradiation month."
        )

    return {
        "loss_breakdown": loss_breakdown,
        "curtailment_candidates": curtailment_candidates,
        "root_causes": root_causes,
        "commentary": commentary,
        "summary": {
            "total_gap_mwh": round(total_gap, 2),
            "recoverable_mwh": round(recoverable_total, 2),
            "non_recoverable_mwh": round(non_recoverable_total, 2),
            "over_under_performance_mwh": round(over_under_performance, 2),
            "design_yield_mwh": round(design_yield, 2),
            "weather_corrected_yield_mwh": round(weather_corrected_yield, 2),
            "actual_yield_mwh": round(total_actual, 2),
            "screened_bad_data_pct": screened_bad_data_pct,
        },
    }


def _build_peer_groups(
    pr_per_inverter: dict[str, float],
    availability_per_inverter: dict[str, float],
    start_stop_rows: list[dict[str, Any]],
    piv: pd.DataFrame,
    irr: pd.DataFrame,
) -> list[dict[str, Any]]:
    if piv.empty:
        return []

    day_mask = pd.Series(True, index=piv.index)
    if not irr.empty and "ts" in irr.columns and "GHI" in irr.columns:
        ghi_s = irr.set_index("ts")["GHI"].reindex(piv.index)
        day_mask = ghi_s.fillna(0) > 50.0

    start_stop_lookup = {str(item["inv_id"]): item for item in start_stop_rows}
    rows: list[dict[str, Any]] = []

    for inv in piv.columns:
        s = piv[inv]
        day_s = s[day_mask.reindex(s.index).fillna(False)]
        mu = float(day_s.mean()) if len(day_s) else 0.0
        sd = float(day_s.std()) if len(day_s) else 0.0
        cv = sd / max(mu, 1e-6) if mu > 0 else 0.0
        start_dev = float(start_stop_lookup.get(str(inv), {}).get("start_dev", 0.0) or 0.0)
        rows.append(
            {
                "inv_id": str(inv),
                "pr_pct": float(pr_per_inverter.get(inv, 0.0) or 0.0),
                "avail_pct": float(availability_per_inverter.get(inv, 0.0) or 0.0),
                "start_dev_min": round(start_dev, 2),
                "variability_cv": round(cv, 3),
            }
        )

    if not rows:
        return []

    df = pd.DataFrame(rows)
    pr_thr = float(df["pr_pct"].mean() - df["pr_pct"].std()) if len(df) > 1 else float(df["pr_pct"].mean())
    cv_thr = float(df["variability_cv"].quantile(0.75)) if len(df) > 1 else float(df["variability_cv"].max())

    groups: list[dict[str, Any]] = []
    for item in rows:
        group = "Reference"
        if item["pr_pct"] < pr_thr and item["avail_pct"] >= 95:
            group = "Low PR + High Av"
        if item["variability_cv"] >= cv_thr and cv_thr > 0:
            group = "High Variability"
        if item["start_dev_min"] > 5:
            group = "Late-start Signature"
        groups.append({**item, "group": group})

    return sorted(groups, key=lambda item: (item["group"], item["pr_pct"]))


def _build_clipping_diagnostics(
    piv: pd.DataFrame,
    irr: pd.DataFrame,
    cap_ac_kw: float,
    inv_ac_kw: float,
) -> dict[str, Any]:
    if piv.empty or irr.empty or "ts" not in irr.columns or "GHI" not in irr.columns:
        return {"site_near_clip_pct": 0.0, "by_irradiance_bin": [], "top_inverters": []}

    site_pwr = piv.sum(axis=1, min_count=1)
    ghi_s = irr.set_index("ts")["GHI"].reindex(site_pwr.index)
    valid = (ghi_s > 50.0) & site_pwr.notna() & ghi_s.notna()
    near_site = valid & (site_pwr >= 0.97 * max(cap_ac_kw, 1.0))
    site_near_clip_pct = 100.0 * near_site.sum() / max(valid.sum(), 1)

    bins = [
        ("200-400", 200.0, 400.0),
        ("400-600", 400.0, 600.0),
        ("600-800", 600.0, 800.0),
        ("800-1000", 800.0, 1000.0),
        (">=1000", 1000.0, None),
    ]
    by_bin: list[dict[str, Any]] = []
    for label, low, high in bins:
        if high is None:
            mask = valid & (ghi_s >= low)
        else:
            mask = valid & (ghi_s >= low) & (ghi_s < high)
        pct = 100.0 * (near_site & mask).sum() / max(mask.sum(), 1)
        by_bin.append({"label": label, "near_clip_pct": round(float(pct), 2)})

    inv_rows: list[dict[str, Any]] = []
    for col in piv.columns:
        p = piv[col]
        v = valid & p.notna()
        near = v & (p >= 0.97 * max(inv_ac_kw, 1.0))
        pct = 100.0 * near.sum() / max(v.sum(), 1)
        inv_rows.append({"inv_id": str(col), "near_clip_pct": round(float(pct), 2)})

    inv_rows = sorted(inv_rows, key=lambda item: item["near_clip_pct"], reverse=True)[:12]
    return {
        "site_near_clip_pct": round(float(site_near_clip_pct), 2),
        "by_irradiance_bin": by_bin,
        "top_inverters": inv_rows,
    }


def _apply_module_temperature_correction(
    pr_result: dict[str, Any],
    temp_context: pd.DataFrame,
    piv: pd.DataFrame,
    cap_dc_kwp: float,
    interval_minutes: int,
    irr_threshold: float,
) -> dict[str, Any]:
    if temp_context.empty or "module_temp_c" not in temp_context.columns:
        return pr_result

    module_temp = temp_context["module_temp_c"].reindex(pr_result["df"].index)
    if module_temp.dropna().empty:
        return pr_result

    corrected = pr_result["df"].copy()
    correction_factor = (1.0 + TEMP_COEFF * (module_temp - TEMP_STC)).clip(lower=0.70, upper=1.05)
    interval_hours = interval_minutes / 60.0
    corrected["module_temp_c"] = module_temp
    corrected["temp_correction_factor"] = correction_factor
    corrected["E_ref_raw"] = corrected["E_ref"]
    corrected["E_ref"] = corrected["E_ref"] * correction_factor.fillna(1.0)

    day = corrected[corrected["daytime"]].copy()
    monthly = day.resample("ME").agg(
        E_act=("E_act", "sum"),
        E_ref=("E_ref", "sum"),
        irrad=("GHI", lambda x: x.sum() * interval_hours / 1000),
    )
    monthly["PR"] = (monthly["E_act"] / monthly["E_ref"] * 100).clip(0, 110)

    annual = day.groupby(day.index.year).agg(
        E_act=("E_act", "sum"),
        E_ref=("E_ref", "sum"),
        irrad=("GHI", lambda x: x.sum() * interval_hours / 1000),
    )
    annual["PR"] = (annual["E_act"] / annual["E_ref"] * 100).clip(0, 110)

    inv_pr: dict[str, float] = {}
    inv_dc_kwp = cap_dc_kwp / max(1, piv.shape[1])
    for column in piv.columns:
        sub = pd.DataFrame(
            {
                "pwr": piv[column],
                "GHI": corrected["GHI"],
                "temp_factor": corrected["temp_correction_factor"],
            }
        )
        sub = sub[sub["GHI"] > irr_threshold].dropna(subset=["pwr", "GHI"])
        if sub.empty:
            inv_pr[str(column)] = 0.0
            continue
        e_act = (sub["pwr"] * interval_hours).sum()
        e_ref = ((sub["GHI"] / 1000.0) * inv_dc_kwp * interval_hours * sub["temp_factor"].fillna(1.0)).sum()
        inv_pr[str(column)] = float(min(e_act / e_ref * 100, 110)) if e_ref > 0 else 0.0

    return {
        **pr_result,
        "monthly": monthly,
        "annual": annual,
        "per_inverter": inv_pr,
        "df": corrected,
        "df_day": day,
        "temperature_correction": {
            "method": "module_temperature_vs_stc",
            "temp_coeff_per_degC": TEMP_COEFF,
            "temp_stc_c": TEMP_STC,
            "points_used": int(module_temp.notna().sum()),
            "loss_mwh": round(float((corrected["E_ref_raw"] - corrected["E_ref"]).clip(lower=0).sum() / 1000.0), 3),
        },
    }


def _build_monthly_quality_rows(
    piv_raw: pd.DataFrame,
    piv_clean: pd.DataFrame,
    interval_minutes: int,
) -> list[dict[str, Any]]:
    if piv_raw.empty:
        return []

    expected_index = piv_raw.index
    month_periods = expected_index.to_period("M")
    unique_months = sorted(month_periods.unique())
    rows: list[dict[str, Any]] = []

    for inv_id in piv_raw.columns:
        raw_series = piv_raw[inv_id]
        clean_series = piv_clean[inv_id] if inv_id in piv_clean.columns else raw_series.copy()
        for month in unique_months:
            mask = month_periods == month
            expected = int(mask.sum())
            if expected == 0:
                continue
            raw_month = raw_series.loc[mask]
            clean_month = clean_series.loc[mask]
            raw_present = int(raw_month.notna().sum())
            clean_present = int(clean_month.notna().sum())
            missing_count = max(expected - raw_present, 0)
            frozen_count = max(raw_present - clean_present, 0)
            valid_count = clean_present
            rows.append(
                {
                    "month": str(month),
                    "inv_id": str(inv_id),
                    "completeness_pct": round(valid_count / expected * 100.0, 2),
                    "missing_pct": round(missing_count / expected * 100.0, 2),
                    "frozen_pct": round(frozen_count / expected * 100.0, 2),
                }
            )

    return rows


def _apply_daylight_window(
    piv: pd.DataFrame,
    irr: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not piv.empty:
        local_clock = piv.index.hour * 60 + piv.index.minute
        start_minutes = DAYLIGHT_START_HOUR * 60 + DAYLIGHT_START_MINUTE
        end_minutes = DAYLIGHT_END_HOUR * 60 + DAYLIGHT_END_MINUTE
        piv = piv[(local_clock >= start_minutes) & (local_clock <= end_minutes)]

    if not irr.empty and "ts" in irr.columns:
        ts = pd.to_datetime(irr["ts"], errors="coerce")
        local_clock = ts.dt.hour * 60 + ts.dt.minute
        start_minutes = DAYLIGHT_START_HOUR * 60 + DAYLIGHT_START_MINUTE
        end_minutes = DAYLIGHT_END_HOUR * 60 + DAYLIGHT_END_MINUTE
        irr = irr[(local_clock >= start_minutes) & (local_clock <= end_minutes)].copy()

    return piv, irr


def _fetch_weather_context(
    site_config: dict[str, Any],
    date_range: list[str],
) -> dict[str, Any]:
    site_type = str(site_config.get("site_type", "solar")).lower()
    if site_type != "solar":
        return {"summary": None, "monthly": [], "events": [], "source": None, "error": None}

    latitude = float(site_config.get("lat") or 0.0)
    longitude = float(site_config.get("lon") or 0.0)
    if abs(latitude) < 0.0001 and abs(longitude) < 0.0001:
        return {"summary": None, "monthly": [], "events": [], "source": None, "error": "Missing site coordinates."}

    start_raw = str(date_range[0] or "")[:10]
    end_raw = str(date_range[1] or "")[:10]
    if not start_raw or not end_raw:
        return {"summary": None, "monthly": [], "events": [], "source": None, "error": "Missing analysed date range."}

    try:
        fetch_reference_weather(
            source="era5-land",
            site_type="solar",
            latitude=latitude,
            longitude=longitude,
            start_date=start_raw,
            end_date=end_raw,
        )
        reference_path = _cache_target("era5-land", "solar", latitude, longitude, start_raw, end_raw)
        reference_df = _read_reference_csv(reference_path)
        columns = list(reference_df.columns)
        time_col = _find_column(columns, ["date", "time", "valid_time", "datetime"])
        precip_col = _find_column(columns, ["total_precipitation", "tp", "precipitation"])

        weather = reference_df.rename(columns={time_col: "timestamp", precip_col: "rain_raw"}).copy()
        weather["timestamp"] = pd.to_datetime(weather["timestamp"], errors="coerce", utc=False)
        weather["rain_raw"] = pd.to_numeric(weather["rain_raw"], errors="coerce")
        weather = weather.dropna(subset=["timestamp"])
        if weather.empty:
            return {"summary": None, "monthly": [], "events": [], "source": "ERA5-Land precipitation", "error": "No weather rows returned."}

        median_precip = weather["rain_raw"].dropna().median()
        if pd.notna(median_precip) and median_precip < 2:
            weather["rain_mm"] = weather["rain_raw"] * 1000.0
        else:
            weather["rain_mm"] = weather["rain_raw"]
        weather["rain_mm"] = weather["rain_mm"].fillna(0.0).clip(lower=0.0)
        weather["month"] = weather["timestamp"].dt.strftime("%Y-%m")
        weather["day"] = weather["timestamp"].dt.strftime("%Y-%m-%d")

        monthly_rows: list[dict[str, Any]] = []
        monthly = weather.groupby("month").agg(
            total_rain_mm=("rain_mm", "sum"),
            max_hourly_rain_mm=("rain_mm", "max"),
            rainy_hours=("rain_mm", lambda s: int((s >= 0.2).sum())),
        )
        for month, row in monthly.iterrows():
            total_rain = float(row.get("total_rain_mm", 0.0) or 0.0)
            if total_rain >= 120:
                intensity = "extreme"
            elif total_rain >= 60:
                intensity = "very_heavy"
            elif total_rain >= 25:
                intensity = "heavy"
            elif total_rain >= 5:
                intensity = "moderate"
            elif total_rain > 0:
                intensity = "light"
            else:
                intensity = "dry"
            monthly_rows.append(
                {
                    "month": str(month),
                    "total_rain_mm": round(total_rain, 1),
                    "max_hourly_rain_mm": round(float(row.get("max_hourly_rain_mm", 0.0) or 0.0), 2),
                    "rainy_hours": int(row.get("rainy_hours", 0) or 0),
                    "intensity": intensity,
                }
            )

        event_rows: list[dict[str, Any]] = []
        daily = weather.groupby("day").agg(
            total_rain_mm=("rain_mm", "sum"),
            peak_hourly_rain_mm=("rain_mm", "max"),
        )
        heavy_days = daily[daily["total_rain_mm"] >= 10.0].copy()
        for day, row in heavy_days.sort_values("total_rain_mm", ascending=False).head(16).iterrows():
            total_rain = float(row.get("total_rain_mm", 0.0) or 0.0)
            event_rows.append(
                {
                    "date": str(day),
                    "total_rain_mm": round(total_rain, 1),
                    "peak_hourly_rain_mm": round(float(row.get("peak_hourly_rain_mm", 0.0) or 0.0), 2),
                    "classification": "very heavy" if total_rain >= 20.0 else "heavy",
                }
            )

        summary = {
            "total_rain_mm": round(float(weather["rain_mm"].sum()), 1),
            "heavy_rain_days": int((daily["total_rain_mm"] >= 10.0).sum()),
            "very_heavy_rain_days": int((daily["total_rain_mm"] >= 20.0).sum()),
            "max_daily_rain_mm": round(float(daily["total_rain_mm"].max() or 0.0), 1) if not daily.empty else 0.0,
        }

        return {
            "summary": summary,
            "monthly": monthly_rows,
            "events": event_rows,
            "source": "ERA5-Land precipitation",
            "error": None,
        }
    except Exception as exc:
        return {
            "summary": None,
            "monthly": [],
            "events": [],
            "source": "ERA5-Land precipitation",
            "error": str(exc),
        }


def run_pipeline(
    data_files: list[str],
    site_config: dict[str, Any],
    column_mappings: dict[str, Any],
    lang: str = "en",
) -> dict[str, Any]:
    """
    Load SCADA files, run the solar analysis engine, return a
    structured dict that the frontend can render as charts.
    """
    # Lazy import so the analysis engine is only loaded when needed
    from repat_solar_scada_analysis import (  # type: ignore[import]
        analyse_data_availability,
        analyse_pr,
        analyse_availability,
        analyse_mttf,
        analyse_inv_specific_yield,
        analyse_start_stop,
        clean_stuck_values,
    )

    n_inv = site_config.get("n_inverters", 1)
    cap_dc = site_config.get("cap_dc_kwp", 1000.0)
    cap_ac = site_config.get("cap_ac_kw", 1000.0)
    inv_ac = site_config.get("inv_ac_kw", cap_ac / n_inv)
    irr_thresh = site_config.get("irr_threshold", 50.0)
    pwr_thresh = site_config.get("power_threshold", 5.0)
    interval = site_config.get("interval_min", 10)
    design_pr = site_config.get("design_pr", 0.80)

    df_pivot_raw, df_irr = _load_preview_inputs(data_files, column_mappings, interval)
    if str(site_config.get("site_type", "solar")).lower() == "solar":
        df_pivot_raw, df_irr = _apply_daylight_window(df_pivot_raw, df_irr)
    df_pivot, stuck_report = clean_stuck_values(df_pivot_raw) if not df_pivot_raw.empty else (df_pivot_raw, {})

    # Run analysis modules
    dq_result = analyse_data_availability(df_pivot, df_irr)
    pr_result = analyse_pr(df_pivot, df_irr, cap_dc)
    temp_context = _load_temperature_context(data_files, column_mappings)
    pr_result = _apply_module_temperature_correction(pr_result, temp_context, df_pivot, cap_dc, interval, irr_thresh)
    avail_result = analyse_availability(df_pivot, df_irr)
    mttf_result = analyse_mttf(df_pivot, df_irr)
    yield_result = analyse_inv_specific_yield(df_pivot, df_irr)
    start_stop_df = analyse_start_stop(df_pivot, df_irr) if not df_pivot.empty else pd.DataFrame()

    mttf_rows: list[dict[str, Any]] = []
    if isinstance(mttf_result, dict):
        for inv_id, metrics in mttf_result.items():
            if not isinstance(metrics, dict):
                continue
            mttf_rows.append(
                {
                    "inv_id": str(inv_id),
                    "n_failures": int(metrics.get("n_failures", 0) or 0),
                    "mttf_hours": round(float(metrics.get("mttf_hours", 0.0) or 0.0), 2),
                }
            )
    mean_mttf = average_mttf = (
        sum(item["mttf_hours"] for item in mttf_rows if item["mttf_hours"] > 0 and item["mttf_hours"] != float("inf"))
        / max(len([item for item in mttf_rows if item["mttf_hours"] > 0 and item["mttf_hours"] != float("inf")]), 1)
        if mttf_rows
        else 0.0
    )
    event_map = {item["inv_id"]: item["n_failures"] for item in mttf_rows}

    # Date range
    date_range = [
        df_pivot.index.min().isoformat() if len(df_pivot) else "",
        df_pivot.index.max().isoformat() if len(df_pivot) else "",
    ]
    weather_context = _fetch_weather_context(site_config, date_range)

    dq_monthly_rows = _build_monthly_quality_rows(df_pivot_raw, df_pivot, interval)

    avail_monthly_rows: list[dict[str, Any]] = []
    avail_monthly_df = avail_result.get("per_inverter_monthly")
    if isinstance(avail_monthly_df, pd.DataFrame):
        for month, row in avail_monthly_df.iterrows():
            for inv_id, avail_pct in row.items():
                avail_monthly_rows.append(
                    {
                        "month": pd.Timestamp(month).strftime("%Y-%m"),
                        "inv_id": str(inv_id),
                        "avail_pct": round(float(avail_pct), 2),
                    }
                )

    site_monthly_rows: list[dict[str, Any]] = []
    site_monthly = avail_result.get("site_monthly")
    if isinstance(site_monthly, pd.Series):
        for month, value in site_monthly.items():
            site_monthly_rows.append(
                {
                    "month": pd.Timestamp(month).strftime("%Y-%m"),
                    "avail_pct": round(float(value), 2),
                }
            )

    pr_monthly_df = pr_result.get("monthly")
    pr_monthly_rows: list[dict[str, Any]] = []
    if isinstance(pr_monthly_df, pd.DataFrame):
        for month, row in pr_monthly_df.iterrows():
            pr_monthly_rows.append(
                {
                    "month": pd.Timestamp(month).strftime("%Y-%m"),
                    "E_act_mwh": round(float(row.get("E_act", 0.0)) / 1000, 3),
                    "E_ref_mwh": round(float(row.get("E_ref", 0.0)) / 1000, 3),
                    "irrad_kwh_m2": round(float(row.get("irrad", 0.0)), 2),
                    "PR_pct": round(float(row.get("PR", 0.0)), 2),
                }
            )

    pr_annual_df = pr_result.get("annual")
    pr_annual_rows: list[dict[str, Any]] = []
    if isinstance(pr_annual_df, pd.DataFrame):
        for year, row in pr_annual_df.iterrows():
            pr_annual_rows.append(
                {
                    "year": int(year),
                    "E_act_mwh": round(float(row.get("E_act", 0.0)) / 1000, 3),
                    "PR_pct": round(float(row.get("PR", 0.0)), 2),
                }
            )

    specific_yield_rows: list[dict[str, Any]] = []
    if isinstance(yield_result, pd.DataFrame) and not yield_result.empty:
        average_yield = yield_result.mean(axis=0, skipna=True).sort_values(ascending=False)
        per_inv_pr = pr_result.get("per_inverter", {})
        for rank, (inv_id, yield_value) in enumerate(average_yield.items(), start=1):
            specific_yield_rows.append(
                {
                    "inv_id": str(inv_id),
                    "yield_kwh_kwp": round(float(yield_value), 2),
                    "pr_pct": round(float(per_inv_pr.get(inv_id, 0.0)), 2),
                    "rank": rank,
                }
            )

    start_stop_rows: list[dict[str, Any]] = []
    if isinstance(start_stop_df, pd.DataFrame) and not start_stop_df.empty:
        for inv_id, row in start_stop_df.iterrows():
            start_stop_rows.append(
                {
                    "inv_id": str(inv_id),
                    "start_min": round(float(row.get("start_min", 0.0)), 2),
                    "stop_min": round(float(row.get("stop_min", 0.0)), 2),
                    "start_dev": round(float(row.get("start_dev", 0.0)), 2),
                    "stop_dev": round(float(row.get("stop_dev", 0.0)), 2),
                    "start_label": _minutes_to_label(float(row.get("start_min", float("nan")))),
                    "stop_label": _minutes_to_label(float(row.get("stop_min", float("nan")))),
                }
            )

    punchlist = _build_preview_punchlist(pr_result, avail_result, dq_result, specific_yield_rows)
    diagnosis = _build_loss_diagnosis(
        pr_monthly_rows=pr_monthly_rows,
        site_monthly_rows=site_monthly_rows,
        dq_monthly_rows=dq_monthly_rows,
        specific_yield_rows=specific_yield_rows,
        stuck_inverters_count=int(len(stuck_report)),
        design_pr=float(design_pr),
        temperature_loss_mwh=float(pr_result.get("temperature_correction", {}).get("loss_mwh", 0.0) or 0.0),
    )
    peer_groups = _build_peer_groups(
        pr_per_inverter=pr_result.get("per_inverter", {}),
        availability_per_inverter=avail_result.get("per_inverter", {}),
        start_stop_rows=start_stop_rows,
        piv=df_pivot,
        irr=df_irr,
    )
    clipping = _build_clipping_diagnostics(df_pivot, df_irr, cap_ac, inv_ac)

    return {
        "summary": {
            "cap_dc_kwp": cap_dc,
            "cap_ac_kw": cap_ac,
            "n_inverters": n_inv,
            "data_date_range": date_range,
        },
        "pr": {
            "monthly": pr_monthly_rows,
            "annual": pr_annual_rows,
            "per_inverter": pr_result.get("per_inverter", {}),
        },
        "availability": {
            "per_inverter": avail_result.get("per_inverter", {}),
            "site_monthly": site_monthly_rows,
            "per_inverter_monthly": avail_monthly_rows,
            "mean_pct": avail_result.get("mean_pct", avail_result.get("mean", 0.0)),
            "whole_site_events": avail_result.get("whole_site_events", 0),
        },
        "data_quality": {
            "overall_power_pct": round(float(dq_result.get("overall_power", 0.0)), 2),
            "irradiance_pct": round(float(dq_result.get("irradiance", 0.0)), 2),
            "per_inverter": dq_result.get("per_inverter", {}),
            "monthly": dq_monthly_rows,
            "stuck_inverters_count": int(len(stuck_report)),
        },
        "mttf": {
            "mean_hours": round(float(average_mttf), 2),
            "events_per_inverter": event_map,
            "by_inverter": mttf_rows,
        },
        "start_stop": start_stop_rows,
        "peer_groups": peer_groups,
        "clipping": clipping,
        "specific_yield": specific_yield_rows,
        "weather": weather_context,
        "waterfall": [
            {
                "label": item["label"],
                "value_mwh": item["value_mwh"],
                "type": (
                    "base"
                    if item["label"] in {"Design yield", "Weather-corrected yield", "Actual yield"}
                    else "loss"
                ),
            }
            for item in diagnosis["loss_breakdown"]
        ],
        "punchlist": punchlist,
        "diagnosis": diagnosis,
    }
