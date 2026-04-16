from __future__ import annotations

import hashlib
import io
import re
import zipfile
from datetime import time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from pandas.errors import ParserError

from app.core.config import settings


SOLAR_VARIABLES = [
    "2m_temperature",
    "surface_solar_radiation_downwards",
    "total_precipitation",
]

IRRADIANCE_DAY_START = time(5, 30)
IRRADIANCE_DAY_END = time(21, 0)

WIND_VARIABLES = [
    "2m_temperature",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
]


def _rounded_location(latitude: float, longitude: float) -> tuple[float, float]:
    return (round(latitude, 1), round(longitude, 1))


def _dataset_for_source(source: str) -> str:
    source = source.lower()
    if source == "era5-land":
        return "reanalysis-era5-land-timeseries"
    raise ValueError(f"Unsupported reference source: {source}")


def _variables_for_site_type(site_type: str) -> list[str]:
    return SOLAR_VARIABLES if site_type == "solar" else WIND_VARIABLES


def _cache_target(
    source: str,
    site_type: str,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> Path:
    lat, lon = _rounded_location(latitude, longitude)
    fingerprint = hashlib.sha256(
        f"{source}|{site_type}|{lat}|{lon}|{start_date}|{end_date}".encode("utf-8")
    ).hexdigest()[:16]
    base = Path(settings.long_term_cache_dir)
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{source}_{site_type}_{lat}_{lon}_{start_date}_{end_date}_{fingerprint}.csv"


def _build_client():
    import cdsapi

    if settings.cds_api_url and settings.cds_api_key:
        return cdsapi.Client(url=settings.cds_api_url, key=settings.cds_api_key, quiet=True)
    return cdsapi.Client(quiet=True)


def _read_uploaded_frame(file_bytes: bytes, filename: str) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    buffer = io.BytesIO(file_bytes)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(buffer)
    return pd.read_csv(buffer)


def _read_reference_csv(path: Path) -> pd.DataFrame:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            frames: list[pd.DataFrame] = []
            for member in archive.namelist():
                if not member.lower().endswith(".csv"):
                    continue
                with archive.open(member) as handle:
                    frames.append(pd.read_csv(handle))
        if not frames:
            raise ValueError("Reference archive did not contain any CSV files.")
        merged = frames[0]
        for frame in frames[1:]:
            join_keys = [column for column in ("valid_time", "date", "time", "latitude", "longitude") if column in merged.columns and column in frame.columns]
            if not join_keys:
                raise ValueError("Reference archive CSV files did not share compatible join columns.")
            merged = merged.merge(frame, on=join_keys, how="outer")
        return merged

    last_error: Exception | None = None
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin1"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
        except ParserError:
            try:
                return pd.read_csv(path, encoding=encoding, engine="python", on_bad_lines="skip")
            except Exception as exc:  # pragma: no cover - fallback path
                last_error = exc
                continue
    if last_error:
        raise last_error
    try:
        return pd.read_csv(path)
    except ParserError:
        return pd.read_csv(path, engine="python", on_bad_lines="skip")


def _find_column(columns: list[str], patterns: list[str]) -> str:
    normalized_columns = {
        column: re.sub(r"[^a-z0-9]+", "", column.lower())
        for column in columns
    }
    for column in columns:
        lowered = column.lower()
        if any(pattern in lowered for pattern in patterns):
            return column
    normalized_patterns = [re.sub(r"[^a-z0-9]+", "", pattern.lower()) for pattern in patterns]
    for column, normalized in normalized_columns.items():
        if any(pattern in normalized for pattern in normalized_patterns):
            return column
    raise ValueError(f"Could not infer a matching column for patterns: {patterns}")


def _normalize_reference_frame(df: pd.DataFrame) -> pd.DataFrame:
    columns = list(df.columns)
    time_col = _find_column(columns, ["date", "time", "valid_time", "datetime"])
    irr_col = _find_column(columns, ["surface_solar_radiation_downwards", "ssrd", "solar_radiation_downwards"])
    temp_col = _find_column(columns, ["2m_temperature", "t2m", "temperature_2m"])

    ref = df.rename(columns={time_col: "timestamp", irr_col: "reference_ssrd", temp_col: "reference_temperature_raw"}).copy()
    ref["timestamp"] = pd.to_datetime(ref["timestamp"], utc=False)
    ref["reference_ssrd"] = pd.to_numeric(ref["reference_ssrd"], errors="coerce")
    ref["reference_temperature_raw"] = pd.to_numeric(ref["reference_temperature_raw"], errors="coerce")

    # Normalize reference irradiance to kWh/m² per timestep.
    # We receive mixed cache/source formats depending on how the ERA payload was exported:
    # - J/m² over timestep: typical CDS raw export, values often far above 2,000
    # - Wh/m² over timestep: values typically in the tens to low thousands
    # - kWh/m² over timestep: values typically below ~2 for hourly solar data
    reference_ssrd_median = ref["reference_ssrd"].dropna().median()
    if pd.notna(reference_ssrd_median) and reference_ssrd_median > 2000:
        ref["reference_irradiance_kwh_m2"] = ref["reference_ssrd"] / 3_600_000.0
    elif pd.notna(reference_ssrd_median) and reference_ssrd_median > 5:
        ref["reference_irradiance_kwh_m2"] = ref["reference_ssrd"] / 1000.0
    else:
        ref["reference_irradiance_kwh_m2"] = ref["reference_ssrd"]

    # ERA temperature is Kelvin; convert if needed.
    if ref["reference_temperature_raw"].dropna().median() > 150:
        ref["reference_temperature_c"] = ref["reference_temperature_raw"] - 273.15
    else:
        ref["reference_temperature_c"] = ref["reference_temperature_raw"]

    ref["month"] = ref["timestamp"].dt.month
    ref["hour"] = ref["timestamp"].dt.hour

    return ref[["timestamp", "reference_irradiance_kwh_m2", "reference_temperature_c", "month", "hour"]].dropna(
        subset=["timestamp"]
    )


def _full_calendar_years(hourly_local: pd.DataFrame) -> list[int]:
    if hourly_local.empty:
        return []

    years: list[int] = []
    for year in sorted(hourly_local["timestamp_local"].dt.year.dropna().unique()):
        year_rows = hourly_local[hourly_local["timestamp_local"].dt.year == year]
        if year_rows.empty:
            continue

        start_expected = pd.Timestamp(year=year, month=1, day=1, hour=0)
        end_expected = pd.Timestamp(year=year, month=12, day=31, hour=23)
        if year_rows["timestamp_local"].min() > start_expected or year_rows["timestamp_local"].max() < end_expected:
            continue

        expected_hours = len(pd.date_range(start=start_expected, end=end_expected, freq="1h"))
        actual_hours = int(year_rows["timestamp_local"].nunique())
        if actual_hours >= expected_hours * 0.98:
            years.append(int(year))

    return years


def _summarize_repeated_runs(
    measured: pd.DataFrame,
    signature_frame: pd.DataFrame,
    value_series: pd.Series,
    *,
    step_hours: float,
    minimum_consecutive_rows: int,
) -> tuple[pd.Series, list[dict[str, Any]]]:
    signatures = pd.util.hash_pandas_object(signature_frame.fillna(-999_999.0), index=False)
    run_id = signatures.ne(signatures.shift()).cumsum()
    run_length = signatures.groupby(run_id).transform("size")
    non_zero_mask = value_series.abs().fillna(0.0) > 1e-6
    flagged_mask = (run_length >= minimum_consecutive_rows) & non_zero_mask

    flagged_rows = measured.loc[flagged_mask, ["timestamp_local"]].copy()
    flagged_rows["representative_value"] = value_series.loc[flagged_mask].to_numpy()
    flagged_rows["run_id"] = run_id.loc[flagged_mask].to_numpy()

    event_windows: list[dict[str, Any]] = []
    if not flagged_rows.empty:
        grouped_events = (
            flagged_rows.groupby("run_id", as_index=False)
            .agg(
                start=("timestamp_local", "min"),
                end=("timestamp_local", "max"),
                row_count=("timestamp_local", "size"),
                representative_value=("representative_value", "first"),
            )
            .sort_values("row_count", ascending=False)
        )
        event_windows = [
            {
                "start": str(row["start"]),
                "end": str(row["end"]),
                "rowCount": int(row["row_count"]),
                "durationHours": round(float(row["row_count"]) * step_hours, 2),
                "representativeValue": round(float(row["representative_value"]), 4) if pd.notna(row["representative_value"]) else None,
            }
            for row in grouped_events.head(5).to_dict("records")
        ]
    return flagged_mask, event_windows


def _screen_bad_power_data(
    measured: pd.DataFrame,
    power_cols: list[str],
    *,
    step_hours: float,
    minimum_consecutive_rows: int = 3,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    power_frame = measured[power_cols].apply(pd.to_numeric, errors="coerce")
    power_flagged_mask, power_windows = _summarize_repeated_runs(
        measured,
        power_frame,
        measured["power_kw_total"],
        step_hours=step_hours,
        minimum_consecutive_rows=minimum_consecutive_rows,
    )
    irradiance_flagged_mask, irradiance_windows = _summarize_repeated_runs(
        measured,
        measured[["irradiance_raw"]].apply(pd.to_numeric, errors="coerce"),
        measured["irradiance_raw"],
        step_hours=step_hours,
        minimum_consecutive_rows=minimum_consecutive_rows,
    )
    flagged_mask = power_flagged_mask | irradiance_flagged_mask
    power_flagged_dates = (
        measured.loc[power_flagged_mask, "timestamp_local"].dt.strftime("%Y-%m-%d").dropna().drop_duplicates().sort_values().tolist()
    )
    weather_flagged_dates = (
        measured.loc[irradiance_flagged_mask, "timestamp_local"].dt.strftime("%Y-%m-%d").dropna().drop_duplicates().sort_values().tolist()
    )

    cleaned = measured.loc[~flagged_mask].copy()
    screening_summary = {
        "badDataRule": f"Remove non-zero periods where the selected power-channel state or the site irradiance value repeats for at least {minimum_consecutive_rows} consecutive records.",
        "badDataMinimumConsecutiveRows": int(minimum_consecutive_rows),
        "totalMeasuredRows": int(len(measured.index)),
        "badDataRows": int(flagged_mask.sum()),
        "badDataHours": round(float(flagged_mask.sum()) * step_hours, 2),
        "badPowerRows": int(power_flagged_mask.sum()),
        "badWeatherRows": int(irradiance_flagged_mask.sum()),
        "badDataEvents": len(power_windows) + len(irradiance_windows),
        "badPowerEvents": len(power_windows),
        "badWeatherEvents": len(irradiance_windows),
        "badDataApplied": bool(flagged_mask.any()),
        "badPowerDates": power_flagged_dates,
        "badWeatherDates": weather_flagged_dates,
        "badPowerWindows": [
            {key: value for key, value in window.items() if key != "representativeValue"} | {"stuckPowerKw": window.get("representativeValue")}
            for window in power_windows
        ],
        "badWeatherWindows": [
            {key: value for key, value in window.items() if key != "representativeValue"} | {"stuckIrradiance": window.get("representativeValue")}
            for window in irradiance_windows
        ],
    }
    return cleaned, screening_summary


def _erbs_diffuse_fraction(kt: np.ndarray) -> np.ndarray:
    kd = np.empty_like(kt)
    kd[kt <= 0.22] = 1.0 - 0.09 * kt[kt <= 0.22]
    mid = (kt > 0.22) & (kt <= 0.8)
    kd[mid] = (
        0.9511
        - 0.1604 * kt[mid]
        + 4.388 * kt[mid] ** 2
        - 16.638 * kt[mid] ** 3
        + 12.336 * kt[mid] ** 4
    )
    kd[kt > 0.8] = 0.165
    return np.clip(kd, 0.0, 1.0)


def _transpose_reference_irradiance(
    reference_df: pd.DataFrame,
    *,
    latitude: float,
    longitude: float,
    irradiance_basis: str,
    tracker_mode: str,
    irradiance_tilt_deg: float,
) -> pd.DataFrame:
    adjusted = reference_df.copy()
    adjusted["reference_irradiance_horizontal_kwh_m2"] = adjusted["reference_irradiance_kwh_m2"]

    basis = (irradiance_basis or "").lower()
    tracker = (tracker_mode or "").lower()
    tilt_deg = max(float(irradiance_tilt_deg or 0.0), 0.0)

    if basis == "ghi":
        adjusted["reference_irradiance_mode"] = "ghi"
        return adjusted

    if tracker in {"single-axis-tracker", "dual-axis-tracker"}:
        factor = 1.12 if tracker == "single-axis-tracker" else 1.18
        adjusted["reference_irradiance_kwh_m2"] = adjusted["reference_irradiance_kwh_m2"] * factor
        adjusted["reference_irradiance_mode"] = "tracker-adjusted"
        return adjusted

    if tilt_deg <= 0:
        adjusted["reference_irradiance_mode"] = "ghi"
        return adjusted

    timestamps = pd.to_datetime(adjusted["timestamp"], errors="coerce")
    day_of_year = timestamps.dt.dayofyear.to_numpy(dtype=float)
    hour_utc = timestamps.dt.hour.to_numpy(dtype=float) + timestamps.dt.minute.to_numpy(dtype=float) / 60.0

    gamma = 2.0 * np.pi * (day_of_year - 1.0) / 365.0
    decl = (
        0.006918
        - 0.399912 * np.cos(gamma)
        + 0.070257 * np.sin(gamma)
        - 0.006758 * np.cos(2 * gamma)
        + 0.000907 * np.sin(2 * gamma)
        - 0.002697 * np.cos(3 * gamma)
        + 0.00148 * np.sin(3 * gamma)
    )
    equation_of_time_min = 229.18 * (
        0.000075
        + 0.001868 * np.cos(gamma)
        - 0.032077 * np.sin(gamma)
        - 0.014615 * np.cos(2 * gamma)
        - 0.040849 * np.sin(2 * gamma)
    )

    latitude_rad = np.radians(latitude)
    tilt_rad = np.radians(tilt_deg)
    solar_time = hour_utc + longitude / 15.0 + equation_of_time_min / 60.0
    hour_angle = np.radians(15.0 * (solar_time - 12.0))

    cos_zenith = np.sin(latitude_rad) * np.sin(decl) + np.cos(latitude_rad) * np.cos(decl) * np.cos(hour_angle)
    cos_zenith = np.clip(cos_zenith, 0.0, None)

    effective_latitude = latitude_rad - np.sign(latitude if latitude != 0 else 1.0) * tilt_rad
    cos_incidence = np.sin(decl) * np.sin(effective_latitude) + np.cos(decl) * np.cos(effective_latitude) * np.cos(hour_angle)
    cos_incidence = np.clip(cos_incidence, 0.0, None)

    ghi = adjusted["reference_irradiance_kwh_m2"].to_numpy(dtype=float)
    eccentricity = (
        1.00011
        + 0.034221 * np.cos(gamma)
        + 0.00128 * np.sin(gamma)
        + 0.000719 * np.cos(2 * gamma)
        + 0.000077 * np.sin(2 * gamma)
    )
    extra_horizontal = 1.367 * eccentricity * cos_zenith
    kt = np.divide(ghi, extra_horizontal, out=np.zeros_like(ghi), where=extra_horizontal > 1e-6)
    kt = np.clip(kt, 0.0, 1.2)
    kd = _erbs_diffuse_fraction(kt)

    dhi = ghi * kd
    bhi = np.clip(ghi - dhi, 0.0, None)
    rb = np.divide(cos_incidence, cos_zenith, out=np.zeros_like(cos_incidence), where=cos_zenith > 1e-6)
    albedo = 0.2
    poa = bhi * rb + dhi * (1.0 + np.cos(tilt_rad)) / 2.0 + ghi * albedo * (1.0 - np.cos(tilt_rad)) / 2.0

    adjusted["reference_irradiance_kwh_m2"] = np.clip(poa, 0.0, None)
    adjusted["reference_irradiance_mode"] = "tilt-adjusted"
    return adjusted


def fetch_reference_weather(
    *,
    source: str,
    site_type: str,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    dataset = _dataset_for_source(source)
    variables = _variables_for_site_type(site_type)
    lat, lon = _rounded_location(latitude, longitude)
    target = _cache_target(source, site_type, latitude, longitude, start_date, end_date)
    cached = target.exists()

    request = {
        "variable": variables,
        "location": {"longitude": lon, "latitude": lat},
        "date": [f"{start_date}/{end_date}"],
        "data_format": "csv",
    }

    if not cached:
        client = _build_client()
        client.retrieve(dataset, request).download(str(target))

    try:
        df = _read_reference_csv(target)
    except (ParserError, UnicodeDecodeError, ValueError, OSError):
        # Cached downloads can occasionally be truncated or contain malformed rows.
        # Re-fetch once before surfacing an API error to the frontend.
        if target.exists():
            target.unlink(missing_ok=True)
        client = _build_client()
        client.retrieve(dataset, request).download(str(target))
        df = _read_reference_csv(target)

    return {
        "dataset": dataset,
        "source": source,
        "siteType": site_type,
        "cached": cached,
        "locationRequested": {"latitude": latitude, "longitude": longitude},
        "locationUsed": {"latitude": lat, "longitude": lon},
        "dateRange": {"start": start_date, "end": end_date},
        "variables": variables,
        "fileName": target.name,
        "rowCount": int(len(df.index)),
        "columns": list(df.columns),
    }


def correlate_long_term_solar(
    *,
    file_bytes: bytes,
    filename: str,
    column_mappings: dict[str, Any],
    source: str,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    correlation_years: int,
    dc_capacity_kwp: float = 0.0,
    ac_capacity_kw: float = 0.0,
    specific_yield_kwh_kwp: float = 0.0,
    yield_scenario: str = "measured",
    run_mode: str = "preview",
    site_timezone: str = "UTC",
    irradiance_basis: str = "poa",
    tracker_mode: str = "fixed-tilt",
    irradiance_tilt_deg: float = 0.0,
    ) -> dict[str, Any]:
    fetch_reference_weather(
        source=source,
        site_type="solar",
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
    )
    reference_path = _cache_target(source, "solar", latitude, longitude, start_date, end_date)
    reference_df = _normalize_reference_frame(_read_reference_csv(reference_path))
    reference_df = _transpose_reference_irradiance(
        reference_df,
        latitude=latitude,
        longitude=longitude,
        irradiance_basis=irradiance_basis,
        tracker_mode=tracker_mode,
        irradiance_tilt_deg=irradiance_tilt_deg,
    )

    raw = _read_uploaded_frame(file_bytes, filename)
    mapping = column_mappings or {}
    time_col = mapping.get("time")
    power_cols = [value for value in mapping.get("power", []) if value in raw.columns]
    irr_col = mapping.get("irradiance")
    ambient_col = mapping.get("ambientTemperature")
    module_col = mapping.get("moduleTemperature")

    if not time_col or time_col not in raw.columns:
        raise ValueError("Timestamp column is required for long-term correlation.")
    if not power_cols:
        raise ValueError("At least one power channel must be selected for long-term correlation.")
    if not irr_col or irr_col not in raw.columns:
        raise ValueError("An irradiance column is required for long-term solar correlation.")

    try:
        timezone = ZoneInfo(site_timezone)
    except Exception as exc:
        raise ValueError(f"Unsupported site timezone: {site_timezone}") from exc

    measured = raw.copy()
    measured["timestamp_local"] = pd.to_datetime(measured[time_col], errors="coerce", dayfirst=True)
    measured = measured.dropna(subset=["timestamp_local"]).sort_values("timestamp_local")

    if measured.empty:
        raise ValueError("Measured SCADA file did not contain any valid timestamps.")

    step_hours = (
        measured["timestamp_local"].sort_values().diff().dropna().dt.total_seconds().median() / 3600.0
        if len(measured.index) > 1
        else 1 / 6
    )
    if not step_hours or pd.isna(step_hours) or step_hours <= 0:
        step_hours = 1 / 6

    measured["power_kw_total"] = measured[power_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1, min_count=1)
    measured["irradiance_raw"] = pd.to_numeric(measured[irr_col], errors="coerce")
    local_clock = measured["timestamp_local"].dt.time
    daylight_mask = (local_clock >= IRRADIANCE_DAY_START) & (local_clock <= IRRADIANCE_DAY_END)
    measured.loc[~daylight_mask, "irradiance_raw"] = pd.NA
    measured["irradiance_kwh_m2_interval"] = measured["irradiance_raw"] * step_hours / 1000.0
    measured["ambient_temperature_c"] = pd.to_numeric(measured[ambient_col], errors="coerce") if ambient_col in measured.columns else None
    measured["module_temperature_c"] = pd.to_numeric(measured[module_col], errors="coerce") if module_col in measured.columns else None
    measured["energy_mwh_interval"] = measured["power_kw_total"] * step_hours / 1000.0

    measured, screening_summary = _screen_bad_power_data(
        measured,
        power_cols,
        step_hours=step_hours,
        minimum_consecutive_rows=3,
    )

    if measured.empty:
        raise ValueError("All measured rows were excluded by the bad-data screening rule. Please review the selected power channels or relax the screening logic.")

    if run_mode == "screening":
        measured_start_local = measured["timestamp_local"].min().floor("min")
        measured_end_local = measured["timestamp_local"].max().floor("min")
        measured_duration_hours = max((measured_end_local - measured_start_local).total_seconds() / 3600.0 + step_hours, step_hours)
        measured_duration_years = measured_duration_hours / (24.0 * 365.25)
        measured_total_energy_mwh = float(measured["energy_mwh_interval"].sum())
        measured_annualized_aep_mwh = measured_total_energy_mwh / measured_duration_years if measured_duration_years > 0 else 0.0
        measured_specific_yield_kwh_kwp = measured_annualized_aep_mwh * 1000.0 / dc_capacity_kwp if dc_capacity_kwp > 0 else None
        return {
            "summary": {
                "siteType": "solar",
                "measuredStart": str(measured_start_local),
                "measuredEnd": str(measured_end_local),
                "measuredDurationYears": round(float(measured_duration_years), 2),
                "measuredTotalEnergyMwh": round(float(measured_total_energy_mwh), 1),
                "measuredAnnualizedAepMwh": round(float(measured_annualized_aep_mwh), 1),
                "measuredSpecificYieldKwhKwp": round(float(measured_specific_yield_kwh_kwp), 1) if measured_specific_yield_kwh_kwp is not None else None,
                "selectedPowerChannels": len(power_cols),
                "selectedPowerColumnNames": power_cols,
                "referenceSource": source,
                "referenceDataset": _dataset_for_source(source),
                **screening_summary,
                "note": "Bad-data screening removes flatlined non-zero power periods before the fit-and-yield review and the long-term projection. REVEAL applies the same cleaned measured dataset in the later steps.",
            },
            "charts": {
                "annualEnergy": [],
                "monthlyEnergy": [],
                "irradianceFit": [],
            },
            "csvContent": "",
            "csvFileName": "",
        }

    hourly_local = measured.set_index("timestamp_local").resample("1h").agg(
        {
            "energy_mwh_interval": "sum",
            "irradiance_kwh_m2_interval": "sum",
            "irradiance_raw": "count",
            "power_kw_total": "count",
            "ambient_temperature_c": "mean" if ambient_col in measured.columns else "first",
            "module_temperature_c": "mean" if module_col in measured.columns else "first",
        }
    )
    hourly_local = hourly_local.reset_index()
    localized_timestamps = hourly_local["timestamp_local"].dt.tz_localize(
        timezone,
        ambiguous="NaT",
        nonexistent="shift_forward",
    )
    ambiguous_mask = localized_timestamps.isna()
    if ambiguous_mask.any():
        fallback_localized = hourly_local.loc[ambiguous_mask, "timestamp_local"].dt.tz_localize(
            timezone,
            ambiguous=False,
            nonexistent="shift_forward",
        )
        localized_timestamps.loc[ambiguous_mask] = fallback_localized

    hourly_local["timestamp"] = localized_timestamps.dt.tz_convert("UTC").dt.tz_localize(None)
    hourly_local = hourly_local.rename(
        columns={
            "irradiance_kwh_m2_interval": "site_irradiance_kwh_m2",
            "irradiance_raw": "irradiance_sample_count",
            "power_kw_total": "power_sample_count",
        }
    )
    expected_samples_per_hour = max(int(round(1.0 / step_hours)), 1)
    minimum_samples_per_hour = max(expected_samples_per_hour - 1, 1)
    hourly = hourly_local.copy()
    hourly["month"] = hourly["timestamp"].dt.month
    hourly["hour"] = hourly["timestamp"].dt.hour

    full_years = _full_calendar_years(hourly_local)
    full_years_mask = hourly_local["timestamp_local"].dt.year.isin(full_years)
    benchmark_local = hourly_local[full_years_mask].copy() if full_years else hourly_local.copy()

    calibration = hourly.merge(
        reference_df.drop(columns=["month", "hour"], errors="ignore"),
        on="timestamp",
        how="inner",
    )
    valid = calibration[
        (calibration["site_irradiance_kwh_m2"] > 0.02)
        & (calibration["reference_irradiance_kwh_m2"] > 0.001)
        & (calibration["energy_mwh_interval"] >= 0)
        & (calibration["power_sample_count"] >= minimum_samples_per_hour)
        & (calibration["irradiance_sample_count"] >= minimum_samples_per_hour)
    ].copy()

    if valid.empty:
        raise ValueError("No valid matched irradiance periods were found between the measured data and ERA reference.")

    valid["poa_factor"] = valid["site_irradiance_kwh_m2"] / valid["reference_irradiance_kwh_m2"]
    valid["energy_per_poa"] = valid["energy_mwh_interval"] / valid["site_irradiance_kwh_m2"]
    if dc_capacity_kwp > 0:
        valid["specific_yield_per_irradiance"] = (
            valid["energy_mwh_interval"] * 1000.0 / dc_capacity_kwp / valid["site_irradiance_kwh_m2"]
        )
    else:
        valid["specific_yield_per_irradiance"] = pd.NA
    valid["poa_factor"] = valid["poa_factor"].clip(lower=0.2, upper=4.0)
    valid["energy_per_poa"] = valid["energy_per_poa"].clip(lower=0.0, upper=50.0)
    if dc_capacity_kwp > 0:
        valid["specific_yield_per_irradiance"] = pd.to_numeric(valid["specific_yield_per_irradiance"], errors="coerce").clip(lower=0.0, upper=5.0)

    fit_daily = (
        valid.assign(date_local=valid["timestamp_local"].dt.date)
        .groupby("date_local", as_index=False)
        .agg(
            reference_irradiance_kwh_m2=("reference_irradiance_kwh_m2", "sum"),
            site_irradiance_kwh_m2=("site_irradiance_kwh_m2", "sum"),
            valid_hour_count=("timestamp", "count"),
        )
    )
    irradiance_fit = fit_daily[
        fit_daily["valid_hour_count"] >= 6
    ][["reference_irradiance_kwh_m2", "site_irradiance_kwh_m2"]].dropna().copy()
    total_fit_days = int(len(fit_daily.index))
    matched_fit_days = int(len(irradiance_fit.index))
    excluded_fit_days = max(total_fit_days - matched_fit_days, 0)
    if irradiance_fit.empty:
        irradiance_fit = valid[["reference_irradiance_kwh_m2", "site_irradiance_kwh_m2"]].dropna().copy()
    irradiance_fit_r = irradiance_fit["reference_irradiance_kwh_m2"].corr(irradiance_fit["site_irradiance_kwh_m2"])
    irradiance_fit_r2 = float(irradiance_fit_r**2) if irradiance_fit_r is not None and not pd.isna(irradiance_fit_r) else 0.0
    reference_variance = float(irradiance_fit["reference_irradiance_kwh_m2"].var()) if len(irradiance_fit.index) > 1 else 0.0
    irradiance_fit_slope = (
        float(irradiance_fit["reference_irradiance_kwh_m2"].cov(irradiance_fit["site_irradiance_kwh_m2"])) / reference_variance
        if reference_variance > 0
        else 0.0
    )
    irradiance_fit_intercept = (
        float(irradiance_fit["site_irradiance_kwh_m2"].mean()) - irradiance_fit_slope * float(irradiance_fit["reference_irradiance_kwh_m2"].mean())
        if len(irradiance_fit.index) > 0
        else 0.0
    )
    sample_size = min(500, len(irradiance_fit.index))
    if sample_size > 0:
        sampled_fit = irradiance_fit.iloc[:: max(len(irradiance_fit.index) // sample_size, 1)].head(sample_size)
    else:
        sampled_fit = irradiance_fit.head(0)
    fit_points = [
        {
            "reference_irradiance_kwh_m2": round(float(row["reference_irradiance_kwh_m2"]), 4),
            "site_irradiance_kwh_m2": round(float(row["site_irradiance_kwh_m2"]), 4),
        }
        for row in sampled_fit.to_dict("records")
    ]

    profile = (
        valid.groupby(["month", "hour"], as_index=False)
        .agg(
            poa_factor=("poa_factor", "median"),
            energy_per_poa=("energy_per_poa", "median"),
            specific_yield_per_irradiance=("specific_yield_per_irradiance", "median"),
            ambient_temperature_c=("ambient_temperature_c", "median"),
            module_temperature_c=("module_temperature_c", "median"),
        )
        .fillna(0)
    )

    measured_start = hourly["timestamp"].min().floor("h")
    measured_end = hourly["timestamp"].max().floor("h")
    measured_end_local = hourly_local["timestamp_local"].max().floor("h")
    projection_start_local = pd.Timestamp(year=int(measured_end_local.year) + 1, month=1, day=1, hour=0)
    projection_start = projection_start_local.tz_localize(timezone).tz_convert("UTC").tz_localize(None)
    projection_end = projection_start + pd.DateOffset(years=correlation_years)
    future_index = pd.date_range(start=projection_start, end=projection_end, freq="1h", inclusive="left")

    projection_reference_start = f"{projection_start_local.year - correlation_years:04d}-01-01"
    projection_reference_end = f"{projection_start_local.year - 1:04d}-12-31"
    fetch_reference_weather(
        source=source,
        site_type="solar",
        latitude=latitude,
        longitude=longitude,
        start_date=projection_reference_start,
        end_date=projection_reference_end,
    )
    projection_reference_path = _cache_target(
        source,
        "solar",
        latitude,
        longitude,
        projection_reference_start,
        projection_reference_end,
    )
    projection_reference_df = _normalize_reference_frame(_read_reference_csv(projection_reference_path))
    projection_reference_df = _transpose_reference_irradiance(
        projection_reference_df,
        latitude=latitude,
        longitude=longitude,
        irradiance_basis=irradiance_basis,
        tracker_mode=tracker_mode,
        irradiance_tilt_deg=irradiance_tilt_deg,
    )
    projection_reference_df = projection_reference_df.merge(profile, on=["month", "hour"], how="left").fillna(
        {
            "poa_factor": float(valid["poa_factor"].median()),
            "energy_per_poa": float(valid["energy_per_poa"].median()),
            "specific_yield_per_irradiance": float(pd.to_numeric(valid["specific_yield_per_irradiance"], errors="coerce").dropna().median())
            if dc_capacity_kwp > 0 and not pd.to_numeric(valid["specific_yield_per_irradiance"], errors="coerce").dropna().empty
            else 0.0,
        }
    )
    projection_reference_df["projected_site_irradiance_kwh_m2"] = (
        projection_reference_df["reference_irradiance_kwh_m2"] * projection_reference_df["poa_factor"]
    )
    if dc_capacity_kwp > 0:
        projection_reference_df["projected_specific_yield_kwh_kwp"] = (
            projection_reference_df["projected_site_irradiance_kwh_m2"] * projection_reference_df["specific_yield_per_irradiance"]
        )
        projection_reference_df["projected_energy_mwh"] = (
            projection_reference_df["projected_specific_yield_kwh_kwp"] * dc_capacity_kwp / 1000.0
        )
    else:
        projection_reference_df["projected_specific_yield_kwh_kwp"] = pd.NA
        projection_reference_df["projected_energy_mwh"] = (
            projection_reference_df["projected_site_irradiance_kwh_m2"] * projection_reference_df["energy_per_poa"]
        )

    projection_reference_lookup = projection_reference_df.set_index("timestamp")[
        [
            "reference_irradiance_kwh_m2",
            "reference_temperature_c",
            "projected_site_irradiance_kwh_m2",
            "projected_specific_yield_kwh_kwp",
            "projected_energy_mwh",
        ]
    ]
    projected = pd.DataFrame({"timestamp": future_index})
    projected["historical_reference_timestamp"] = projected["timestamp"] - pd.DateOffset(years=correlation_years)
    projected = projected.join(projection_reference_lookup, on="historical_reference_timestamp")
    if dc_capacity_kwp > 0 and specific_yield_kwh_kwp > 0:
        raw_specific_yield = float(projected["projected_specific_yield_kwh_kwp"].sum()) / correlation_years
        if raw_specific_yield > 0:
            yield_scale_factor = specific_yield_kwh_kwp / raw_specific_yield
            projected["projected_specific_yield_kwh_kwp"] = projected["projected_specific_yield_kwh_kwp"] * yield_scale_factor
            projected["projected_energy_mwh"] = projected["projected_energy_mwh"] * yield_scale_factor
    projected["mode"] = "projected"

    measured_export = benchmark_local[
        [
            "timestamp_local",
            "timestamp",
            "energy_mwh_interval",
            "site_irradiance_kwh_m2",
            "ambient_temperature_c",
            "module_temperature_c",
        ]
    ].rename(
        columns={
            "energy_mwh_interval": "expected_energy_mwh",
            "site_irradiance_kwh_m2": "site_equivalent_irradiance_kwh_m2",
        }
    )
    measured_export["reference_irradiance_kwh_m2"] = pd.NA
    measured_export["reference_temperature_c"] = pd.NA
    measured_export["specific_yield_kwh_kwp"] = (
        measured_export["expected_energy_mwh"] * 1000.0 / dc_capacity_kwp if dc_capacity_kwp > 0 else pd.NA
    )
    measured_export["mode"] = "actual"
    measured_chart_export = hourly_local[
        [
            "timestamp_local",
            "timestamp",
            "energy_mwh_interval",
            "site_irradiance_kwh_m2",
            "ambient_temperature_c",
            "module_temperature_c",
        ]
    ].rename(
        columns={
            "energy_mwh_interval": "expected_energy_mwh",
            "site_irradiance_kwh_m2": "site_equivalent_irradiance_kwh_m2",
        }
    )
    measured_chart_export["reference_irradiance_kwh_m2"] = pd.NA
    measured_chart_export["reference_temperature_c"] = pd.NA
    measured_chart_export["specific_yield_kwh_kwp"] = (
        measured_chart_export["expected_energy_mwh"] * 1000.0 / dc_capacity_kwp if dc_capacity_kwp > 0 else pd.NA
    )
    measured_chart_export["mode"] = "actual"

    projected_export = projected[
        [
            "timestamp",
            "mode",
            "reference_irradiance_kwh_m2",
            "projected_site_irradiance_kwh_m2",
            "projected_specific_yield_kwh_kwp",
            "projected_energy_mwh",
            "reference_temperature_c",
        ]
    ].rename(
        columns={
            "projected_site_irradiance_kwh_m2": "site_equivalent_irradiance_kwh_m2",
            "projected_specific_yield_kwh_kwp": "specific_yield_kwh_kwp",
            "projected_energy_mwh": "expected_energy_mwh",
        }
    )
    projected_export["ambient_temperature_c"] = pd.NA
    projected_export["module_temperature_c"] = pd.NA
    projected_export["timestamp_local"] = (
        pd.to_datetime(projected_export["timestamp"], utc=True)
        .dt.tz_convert(timezone)
        .dt.tz_localize(None)
    )

    export_df = pd.concat([measured_export, projected_export], ignore_index=True, sort=False)
    export_df = export_df[
        [
            "timestamp_local",
            "timestamp",
            "mode",
            "reference_irradiance_kwh_m2",
            "site_equivalent_irradiance_kwh_m2",
            "expected_energy_mwh",
            "specific_yield_kwh_kwp",
            "reference_temperature_c",
            "ambient_temperature_c",
            "module_temperature_c",
        ]
    ]
    export_df = export_df.sort_values("timestamp")
    chart_export_df = pd.concat([measured_chart_export, projected_export], ignore_index=True, sort=False)
    chart_export_df = chart_export_df[
        [
            "timestamp_local",
            "timestamp",
            "mode",
            "reference_irradiance_kwh_m2",
            "site_equivalent_irradiance_kwh_m2",
            "expected_energy_mwh",
            "specific_yield_kwh_kwp",
            "reference_temperature_c",
            "ambient_temperature_c",
            "module_temperature_c",
        ]
    ].sort_values("timestamp")

    benchmark_start = benchmark_local["timestamp"].min().floor("h")
    benchmark_end = benchmark_local["timestamp"].max().floor("h")
    benchmark_start_local = benchmark_local["timestamp_local"].min().floor("h")
    benchmark_end_local = benchmark_local["timestamp_local"].max().floor("h")
    measured_duration_hours = max((benchmark_end - benchmark_start).total_seconds() / 3600.0 + 1.0, 1.0)
    measured_duration_years = measured_duration_hours / (24.0 * 365.25)
    measured_total_energy_mwh = float(measured_export["expected_energy_mwh"].sum())
    measured_annualized_aep_mwh = measured_total_energy_mwh / measured_duration_years if measured_duration_years > 0 else 0.0
    projected_total_energy_mwh = float(projected_export["expected_energy_mwh"].sum())
    projected_average_aep_mwh = projected_total_energy_mwh / correlation_years if correlation_years > 0 else 0.0
    measured_specific_yield_kwh_kwp = measured_annualized_aep_mwh * 1000.0 / dc_capacity_kwp if dc_capacity_kwp > 0 else None
    projected_specific_yield_kwh_kwp = projected_average_aep_mwh * 1000.0 / dc_capacity_kwp if dc_capacity_kwp > 0 else None

    annual = (
        chart_export_df.assign(year=lambda df: pd.to_datetime(df["timestamp"]).dt.year)
        .groupby(["year", "mode"], as_index=False)["expected_energy_mwh"]
        .sum()
    )
    annual_rows = [
        {
            "year": int(row["year"]),
            "mode": row["mode"],
            "energy_mwh": round(float(row["expected_energy_mwh"]), 1),
        }
        for row in annual.to_dict("records")
    ]
    actual_reference_local = reference_df.assign(
        timestamp_local=(
            pd.to_datetime(reference_df["timestamp"], utc=True)
            .dt.tz_convert(timezone)
            .dt.tz_localize(None)
        )
    )
    actual_reference_years = sorted(actual_reference_local["timestamp_local"].dt.year.dropna().unique())
    annual_reference_actual = (
        actual_reference_local[actual_reference_local["timestamp_local"].dt.year.isin(actual_reference_years)]
        .assign(year=lambda df: pd.to_datetime(df["timestamp_local"]).dt.year)
        .groupby("year", as_index=False)["reference_irradiance_kwh_m2"]
        .sum()
    )
    annual_rows.extend(
        [
            {
                "year": int(row["year"]),
                "mode": "reference",
                "energy_mwh": 0.0,
                "irradiation_kwh_m2": round(float(row["reference_irradiance_kwh_m2"]), 2),
            }
            for row in annual_reference_actual.to_dict("records")
        ]
    )
    annual_reference_projected = (
        projected_export.assign(year=lambda df: pd.to_datetime(df["timestamp_local"]).dt.year)
        .groupby("year", as_index=False)["reference_irradiance_kwh_m2"]
        .sum()
    )
    annual_rows.extend(
        [
            {
                "year": int(row["year"]),
                "mode": "reference",
                "energy_mwh": 0.0,
                "irradiation_kwh_m2": round(float(row["reference_irradiance_kwh_m2"]), 2),
            }
            for row in annual_reference_projected.to_dict("records")
        ]
    )
    monthly = (
        chart_export_df.assign(
            year=lambda df: pd.to_datetime(df["timestamp"]).dt.year,
            month=lambda df: pd.to_datetime(df["timestamp"]).dt.month,
        )
        .groupby(["year", "month", "mode"], as_index=False)["expected_energy_mwh"]
        .sum()
        .groupby(["month", "mode"], as_index=False)["expected_energy_mwh"]
        .mean()
    )
    monthly_rows = [
        {
            "month": int(row["month"]),
            "mode": row["mode"],
            "energy_mwh": round(float(row["expected_energy_mwh"]), 1),
        }
        for row in monthly.to_dict("records")
    ]
    monthly_reference = (
        valid.assign(
            year=lambda df: pd.to_datetime(df["timestamp_local"]).dt.year,
            month=lambda df: pd.to_datetime(df["timestamp_local"]).dt.month,
        )
        .groupby(["year", "month"], as_index=False)["reference_irradiance_kwh_m2"]
        .sum()
        .groupby("month", as_index=False)["reference_irradiance_kwh_m2"]
        .mean()
    )
    monthly_rows.extend(
        [
            {
                "month": int(row["month"]),
                "mode": "reference",
                "energy_mwh": 0.0,
                "irradiation_kwh_m2": round(float(row["reference_irradiance_kwh_m2"]), 2),
            }
            for row in monthly_reference.to_dict("records")
        ]
    )

    csv_content = export_df.to_csv(index=False)

    return {
        "summary": {
            "siteType": "solar",
            "measuredStart": str(benchmark_start_local),
            "measuredEnd": str(benchmark_end_local),
            "correlationYears": correlation_years,
            "measuredDurationYears": round(float(measured_duration_years), 2),
            "siteTimezone": site_timezone,
            "fullMeasuredYears": len(full_years),
            "projectionStart": str(projection_start_local),
            "measuredTotalEnergyMwh": round(float(measured_total_energy_mwh), 1),
            "measuredAnnualizedAepMwh": round(float(measured_annualized_aep_mwh), 1),
            "projectedAverageAepMwh": round(float(projected_average_aep_mwh), 1),
            "measuredSpecificYieldKwhKwp": round(float(measured_specific_yield_kwh_kwp), 1) if measured_specific_yield_kwh_kwp is not None else None,
            "projectedSpecificYieldKwhKwp": round(float(projected_specific_yield_kwh_kwp), 1) if projected_specific_yield_kwh_kwp is not None else None,
            "yieldScenario": yield_scenario,
            "specificYieldInputKwhKwp": round(float(specific_yield_kwh_kwp), 1) if specific_yield_kwh_kwp > 0 else None,
            "dcCapacityKwp": round(float(dc_capacity_kwp), 1) if dc_capacity_kwp > 0 else None,
            "acCapacityKw": round(float(ac_capacity_kw), 1) if ac_capacity_kw > 0 else None,
            "selectedPowerChannels": len(power_cols),
            "selectedPowerColumnNames": power_cols,
            "referenceSource": source,
            "referenceDataset": _dataset_for_source(source),
            **screening_summary,
            "referenceIrradianceMode": str(reference_df.get("reference_irradiance_mode", pd.Series(["ghi"])).iloc[0]),
            "irradianceFitR2": round(float(irradiance_fit_r2), 3),
            "irradianceFitSlope": round(float(irradiance_fit_slope), 3),
            "irradianceFitIntercept": round(float(irradiance_fit_intercept), 3),
            "irradianceFitPoints": int(len(irradiance_fit.index)),
            "irradianceFitAggregation": "daily matched days",
            "irradianceFitTotalDays": total_fit_days,
            "irradianceFitMatchedDays": matched_fit_days,
            "irradianceFitExcludedDays": excluded_fit_days,
            "note": "Methodology: REVEAL first removes flatlined non-zero power periods from the measured dataset. Measured site timestamps are then converted from the confirmed site timezone into UTC to align with the ERA reference record. REVEAL calibrates irradiation fit over matched valid days, where a matched day means at least 6 aligned hourly periods with valid values on the same day in both the site and ERA datasets. REVEAL then derives specific yield from the cleaned measured operating data, uses complete measured years where available for the benchmarking metrics, and starts the projection at the next full calendar year after the measured period.",
        },
        "charts": {
            "annualEnergy": annual_rows,
            "monthlyEnergy": monthly_rows,
            "irradianceFit": fit_points,
        },
        "csvContent": csv_content,
        "csvFileName": f"long_term_{Path(filename).stem}_{correlation_years}y.csv",
    }
