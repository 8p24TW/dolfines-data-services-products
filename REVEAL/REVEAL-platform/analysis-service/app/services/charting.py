from __future__ import annotations

import io
import csv
import re
from pathlib import Path
from typing import Any

import pandas as pd
from zoneinfo import ZoneInfo

from app.services.long_term import (
    _cache_target,
    _normalize_reference_frame,
    _read_reference_csv,
    _transpose_reference_irradiance,
    fetch_reference_weather,
)

_EXCEL_HEADER_KEYWORDS = re.compile(
    r"date|time|heure|hour|mois|month|prod|production|pv|conso|consomm|import|export|soc|temp|irr|power|puissance|charge|decharge|décharge|grid|reseau|réseau",
    re.I,
)


def _guess_csv_separator(file_bytes: bytes) -> str:
    sample = file_bytes[:8192].decode("utf-8-sig", errors="ignore")
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t|")
        if dialect.delimiter:
            return dialect.delimiter
    except Exception:
        pass

    lines = [line for line in sample.splitlines() if line.strip()]
    first_line = lines[0] if lines else sample
    counts = {sep: first_line.count(sep) for sep in [";", ",", "\t", "|"]}
    best_sep = max(counts, key=counts.get)
    return best_sep if counts[best_sep] > 0 else ","


def _normalize_header_value(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).replace("\n", " ").strip()
    return re.sub(r"\s+", " ", text)


def _is_data_like(value: Any) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    if isinstance(value, (int, float, pd.Timestamp)):
        return True
    text = str(value).strip()
    if not text:
        return False
    if re.fullmatch(r"[-+]?\d+(?:[.,]\d+)?%?", text):
        return True
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return True
    return False


def _make_unique_headers(headers: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    unique: list[str] = []
    for header in headers:
        base = header or "column"
        count = counts.get(base, 0)
        unique.append(base if count == 0 else f"{base}_{count + 1}")
        counts[base] = count + 1
    return unique


def _score_header_candidate(preview: pd.DataFrame, row_index: int) -> tuple[float, list[int]]:
    row = preview.iloc[row_index]
    normalized = [_normalize_header_value(value) for value in row.tolist()]
    non_empty = [(col_index, value) for col_index, value in enumerate(normalized) if value]
    if len(non_empty) < 2:
        return float("-inf"), []

    keyword_hits = sum(1 for _, value in non_empty if _EXCEL_HEADER_KEYWORDS.search(value))
    short_labels = sum(1 for _, value in non_empty if len(value) <= 40)
    unique_labels = len({value.lower() for _, value in non_empty})
    data_like_hits = sum(1 for _, value in non_empty if _is_data_like(value))

    next_row = preview.iloc[row_index + 1] if row_index + 1 < len(preview) else None
    next_data_like = 0
    if next_row is not None:
        next_values = [next_row.iloc[col_index] for col_index, _ in non_empty]
        next_data_like = sum(1 for value in next_values if _is_data_like(value))

    preceding_sparse_rows = 0
    for previous_index in range(row_index):
        previous_values = [_normalize_header_value(value) for value in preview.iloc[previous_index].tolist()]
        previous_non_empty = sum(1 for value in previous_values if value)
        if previous_non_empty <= 1:
            preceding_sparse_rows += 1
        else:
            break

    first_row_bonus = 8 if row_index == 0 else 0
    leading_blank_bonus = min(preceding_sparse_rows, 4) * 3
    score = (
        (len(non_empty) * 3)
        + (keyword_hits * 5)
        + short_labels
        + unique_labels
        + (next_data_like * 3)
        + first_row_bonus
        + leading_blank_bonus
        - (data_like_hits * 6)
    )
    return score, [col_index for col_index, _ in non_empty]


def _extract_excel_table_frame(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df.empty:
        return raw_df

    preview = raw_df.iloc[: min(len(raw_df), 50), : min(raw_df.shape[1], 50)]
    best_row_index: int | None = None
    best_columns: list[int] = []
    best_score = float("-inf")

    for row_index in range(len(preview)):
        score, candidate_columns = _score_header_candidate(preview, row_index)
        if not candidate_columns:
            continue
        if score > best_score:
            best_score = score
            best_row_index = row_index
            best_columns = candidate_columns

    if best_row_index is None or not best_columns:
        fallback = pd.DataFrame(raw_df)
        fallback = fallback.dropna(axis=0, how="all").dropna(axis=1, how="all")
        return fallback

    header_values = [_normalize_header_value(raw_df.iloc[best_row_index, col_index]) for col_index in best_columns]
    headers = _make_unique_headers(header_values)
    data = raw_df.iloc[best_row_index + 1 :, best_columns].copy()
    data.columns = headers
    data = data.dropna(axis=0, how="all")
    return data.reset_index(drop=True)


def _read_uploaded_frame(file_bytes: bytes, filename: str, worksheet: str | None = None) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    buffer = io.BytesIO(file_bytes)
    if suffix in {".xlsx", ".xls"}:
        read_kwargs: dict[str, Any] = {"header": None}
        if worksheet:
            read_kwargs["sheet_name"] = worksheet
        raw_df = pd.read_excel(buffer, **read_kwargs)
        return _extract_excel_table_frame(raw_df)
    sep = _guess_csv_separator(file_bytes)
    return pd.read_csv(buffer, sep=sep, engine="python", encoding="utf-8-sig")


def _parse_timestamps(series: pd.Series) -> pd.Series:
    text = series.dropna().astype(str).str.strip()
    if text.empty:
        return pd.to_datetime(series, errors="coerce", dayfirst=True)

    iso_like_ratio = (
        text.str.match(r"^\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?$", na=False).mean()
        if len(text) > 0
        else 0
    )

    if iso_like_ratio >= 0.6:
        parsed = pd.to_datetime(series, errors="coerce", dayfirst=False)
        if parsed.notna().any():
            return parsed

    parsed_dayfirst = pd.to_datetime(series, errors="coerce", dayfirst=True)
    parsed_monthfirst = pd.to_datetime(series, errors="coerce", dayfirst=False)
    return parsed_dayfirst if parsed_dayfirst.notna().sum() >= parsed_monthfirst.notna().sum() else parsed_monthfirst


def _localize_wall_clock_timestamp(value: Any, timezone: ZoneInfo) -> pd.Timestamp:
    if pd.isna(value):
        return pd.NaT
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp):
        return pd.NaT
    naive_timestamp = timestamp.tz_localize(None) if timestamp.tzinfo is not None else timestamp
    return naive_timestamp.tz_localize(
        timezone,
        nonexistent="shift_forward",
        ambiguous=False,
    )


def detect_chart_time_range(
    file_bytes: bytes,
    filename: str,
    time_column: str,
    worksheet: str | None = None,
) -> dict[str, Any]:
    if not time_column:
        raise ValueError("A timestamp column is required to detect the date range.")

    frame = _read_uploaded_frame(file_bytes, filename, worksheet).copy()
    if time_column not in frame.columns:
        raise ValueError(f"Selected timestamp column not found in file: {time_column}")

    timestamps = _parse_timestamps(frame[time_column]).dropna().sort_values()
    if timestamps.empty:
        raise ValueError("No valid timestamps were found in the selected timestamp column.")

    return {
        "timeColumn": time_column,
        "worksheet": worksheet,
        "dateRange": [
            timestamps.iloc[0].date().isoformat(),
            timestamps.iloc[-1].date().isoformat(),
        ],
        "rowCount": int(timestamps.shape[0]),
    }


def fetch_chart_reference_irradiance(
    *,
    source: str,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    aggregation: str = "hourly",
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

    try:
        timezone = ZoneInfo(site_timezone or "UTC")
    except Exception as exc:
        raise ValueError(f"Unsupported site timezone: {site_timezone}") from exc

    reference_df = reference_df.copy()
    timestamps = pd.to_datetime(reference_df["timestamp"], errors="coerce", utc=True)
    reference_df["timestamp"] = timestamps.dt.tz_convert(timezone)
    reference_df = reference_df.dropna(subset=["timestamp"]).sort_values("timestamp")
    start_ts = _localize_wall_clock_timestamp(start_date, timezone)
    end_ts = _localize_wall_clock_timestamp(end_date, timezone) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    reference_df = reference_df[
        (reference_df["timestamp"] >= start_ts)
        & (reference_df["timestamp"] <= end_ts)
    ]
    if reference_df.empty:
        raise ValueError("No reference irradiance rows were returned for the selected period.")

    native_step_hours = (
        reference_df["timestamp"]
        .sort_values()
        .diff()
        .dt.total_seconds()
        .dropna()
        .median()
    )
    if pd.isna(native_step_hours) or native_step_hours <= 0:
        native_step_hours = 3600.0
    native_step_hours = float(native_step_hours) / 3600.0
    if native_step_hours <= 0:
        native_step_hours = 1.0

    reference_df["reference_irradiance_w_m2"] = pd.to_numeric(
        reference_df["reference_irradiance_kwh_m2"], errors="coerce"
    ) * (1000.0 / native_step_hours)

    frequency_map = {
        "raw": None,
        "hourly": "h",
        "daily": "D",
        "monthly": "MS",
    }
    freq = frequency_map.get(aggregation, "h")

    is_energy_view = aggregation in {"daily", "monthly"}
    if is_energy_view:
        value_column = "reference_irradiation_kwh_m2"
        if freq:
            aggregated = (
                reference_df.set_index("timestamp")[["reference_irradiance_kwh_m2"]]
                .resample(freq)
                .sum()
                .dropna(how="all")
                .reset_index()
                .rename(columns={"reference_irradiance_kwh_m2": value_column})
            )
        else:
            aggregated = reference_df[["timestamp", "reference_irradiance_kwh_m2"]].copy().rename(
                columns={"reference_irradiance_kwh_m2": value_column}
            )
        label = "Reference irradiation (ERA5-Land)"
        unit = "kWh/m2/day" if aggregation == "daily" else "kWh/m2/month"
    else:
        value_column = "reference_irradiance_w_m2"
        if freq:
            aggregated = (
                reference_df.set_index("timestamp")[[value_column]]
                .resample(freq)
                .mean()
                .dropna(how="all")
                .reset_index()
            )
        else:
            aggregated = reference_df[["timestamp", value_column]].copy()
            if len(aggregated) > 4000:
                step = max(len(aggregated) // 4000, 1)
                aggregated = aggregated.iloc[::step].copy()
        label = "Reference irradiance (ERA5-Land)"
        unit = "W/m2"

    rows = [
        {
            "timestamp": pd.Timestamp(row["timestamp"]).isoformat(),
            "reference_irradiance_era5_land": None if pd.isna(row[value_column]) else round(float(row[value_column]), 2),
        }
        for _, row in aggregated.iterrows()
    ]
    return {
        "source": source,
        "label": label,
        "unit": unit,
        "mode": str(reference_df.get("reference_irradiance_mode", pd.Series(["ghi"])).iloc[0]),
        "rows": rows,
        "summary": {
            "rowCount": len(rows),
            "aggregation": aggregation,
            "dateRange": [
                pd.Timestamp(aggregated["timestamp"].min()).isoformat(),
                pd.Timestamp(aggregated["timestamp"].max()).isoformat(),
            ],
        },
    }


def build_chart_data(
    file_bytes: bytes,
    filename: str,
    time_column: str,
    series: list[dict[str, Any]],
    worksheet: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    aggregation: str = "hourly",
    site_timezone: str = "UTC",
) -> dict[str, Any]:
    if not time_column:
        raise ValueError("A timestamp column is required for charting.")
    if not series:
        raise ValueError("At least one series must be selected for charting.")

    try:
        timezone = ZoneInfo(site_timezone or "UTC")
    except Exception as exc:
        raise ValueError(f"Unsupported site timezone: {site_timezone}") from exc

    requested_columns = [time_column]
    for item in series:
        column = str(item.get("sourceColumn") or item.get("column") or "").strip()
        if column:
            requested_columns.append(column)
    requested_columns = list(dict.fromkeys(requested_columns))

    frame = _read_uploaded_frame(file_bytes, filename, worksheet).copy()
    missing_columns = [column for column in requested_columns if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"Selected column(s) not found in file: {', '.join(missing_columns)}")

    frame = frame[requested_columns].copy()
    frame["timestamp"] = _parse_timestamps(frame[time_column])
    # Uploaded SCADA files are treated as already being in site-local wall-clock time.
    # If a source file carries a timezone suffix, ignore that offset instead of shifting
    # the data, then localize the wall-clock timestamp to the configured site timezone.
    frame["timestamp"] = frame["timestamp"].apply(lambda value: _localize_wall_clock_timestamp(value, timezone))
    frame = frame.dropna(subset=["timestamp"]).sort_values("timestamp")
    if frame.empty:
        raise ValueError("No valid timestamps were found in the uploaded data.")

    selected_columns: list[str] = []
    derived_metrics_by_column: dict[str, str | None] = {}
    chart_series: list[dict[str, Any]] = []
    for item in series:
        source_column = str(item.get("sourceColumn") or item.get("column") or "").strip()
        output_column = str(item.get("column") or source_column).strip()
        if not source_column or not output_column:
            continue
        selected_columns.append(output_column)
        derived_metrics_by_column[output_column] = str(item.get("derivedMetric") or "") or None
        chart_series.append(
            {
                "column": output_column,
                "sourceColumn": source_column,
                "label": str(item.get("label") or output_column),
                "chartType": str(item.get("chartType") or "line"),
                "color": str(item.get("color") or "#60a5fa"),
                "yAxis": str(item.get("yAxis") or "left"),
                "derivedMetric": str(item.get("derivedMetric") or "") or None,
                "capacityKwp": float(item.get("capacityKwp") or 0) if item.get("capacityKwp") is not None else None,
            }
        )
        frame[source_column] = pd.to_numeric(frame[source_column], errors="coerce")
        if str(item.get("derivedMetric") or "") == "specific_yield":
            capacity_kwp = float(item.get("capacityKwp") or 0)
            if capacity_kwp <= 0:
                raise ValueError(f"A positive inverter capacity is required for {output_column}.")
            interval_hours = frame["timestamp"].sort_values().diff().dt.total_seconds().median()
            if pd.isna(interval_hours) or interval_hours <= 0:
                interval_hours = 3600.0
            else:
                interval_hours = float(interval_hours)
            frame[output_column] = (frame[source_column] * (interval_hours / 3600.0)) / capacity_kwp
        elif output_column != source_column:
            frame[output_column] = frame[source_column]

    if not selected_columns:
        raise ValueError("At least one valid numeric series must be selected.")

    if start_date:
        start_ts = _localize_wall_clock_timestamp(start_date, timezone)
        if pd.notna(start_ts):
            frame = frame[frame["timestamp"] >= start_ts]
    if end_date:
        end_ts = _localize_wall_clock_timestamp(end_date, timezone)
        if pd.notna(end_ts):
            frame = frame[frame["timestamp"] <= (end_ts + pd.Timedelta(days=1) - pd.Timedelta(seconds=1))]

    frame = frame.dropna(how="all", subset=selected_columns)
    if frame.empty:
        raise ValueError("No chart rows remain after applying the selected date range.")

    frequency_map = {
        "raw": None,
        "hourly": "h",
        "daily": "D",
        "monthly": "MS",
    }
    freq = frequency_map.get(aggregation, "h")

    if freq:
        aggregation_map: dict[str, str] = {}
        for column in selected_columns:
            aggregation_map[column] = "sum" if derived_metrics_by_column.get(column) == "specific_yield" else "mean"
        aggregated = (
            frame.set_index("timestamp")[selected_columns]
            .resample(freq)
            .agg(aggregation_map)
            .dropna(how="all")
            .reset_index()
        )
    else:
        aggregated = frame[["timestamp", *selected_columns]].copy()
        if len(aggregated) > 4000:
            step = max(len(aggregated) // 4000, 1)
            aggregated = aggregated.iloc[::step].copy()

    rows = []
    for _, row in aggregated.iterrows():
        entry: dict[str, Any] = {"timestamp": pd.Timestamp(row["timestamp"]).isoformat()}
        for column in selected_columns:
            value = row[column]
            entry[column] = None if pd.isna(value) else round(float(value), 5)
        rows.append(entry)

    return {
        "series": chart_series,
        "rows": rows,
        "summary": {
            "filename": filename,
            "worksheet": worksheet,
            "rowCount": len(rows),
            "aggregation": aggregation,
            "dateRange": [
                pd.Timestamp(aggregated["timestamp"].min()).isoformat(),
                pd.Timestamp(aggregated["timestamp"].max()).isoformat(),
            ],
        },
    }
