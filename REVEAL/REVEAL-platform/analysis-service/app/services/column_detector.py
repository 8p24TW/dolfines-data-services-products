"""
Port of the column-mapping logic from the legacy solar ingestion app.
Reads the first few rows of a CSV and returns detected column roles.
"""

import os
import re
from typing import Any

import pandas as pd


_TIME_PATTERNS = re.compile(r"time|date|ts|timestamp|datetime|heure|createdat|created_at|created", re.I)
_POWER_PATTERNS = re.compile(r"pac|p_ac|power|puissance|kw|mw|pout|ond|inv|inverter", re.I)
_IRR_PATTERNS = re.compile(r"ghi|irr|irradiance|g\(i\)|radiation|gh|poa|g_poa", re.I)
_TEMP_PATTERNS = re.compile(r"temp|t_amb|t_panel|tamb|tmod|temperature|celsius", re.I)
_AMBIENT_TEMP_PATTERNS = re.compile(r"text|ext|ambient|amb|t_amb|tamb|outside|meteo", re.I)
_MODULE_TEMP_PATTERNS = re.compile(r"panel|module|mod|cell|backsheet|t_panel|tmod|tpv|panneau", re.I)
_WIND_SPEED_PATTERNS = re.compile(r"wind_speed|vitesse|ws|v_vent|wind|speed", re.I)
_WIND_DIR_PATTERNS = re.compile(r"wind_dir|direction|dir|wd|d_vent", re.I)
_EXCEL_HEADER_KEYWORDS = re.compile(
    r"time|date|heure|hour|mois|month|prod|production|pv|conso|consomm|import|export|soc|temp|irr|power|puissance|charge|decharge|décharge|grid|reseau|réseau",
    re.I,
)


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


def _list_excel_sheets(filepath: str) -> list[str]:
    try:
        workbook = pd.ExcelFile(filepath, engine="openpyxl")
        return [str(name) for name in workbook.sheet_names]
    except Exception:
        return []


def _smart_read(filepath: str, worksheet: str | None = None) -> tuple[pd.DataFrame, str, list[str], str | None]:
    """Read CSV or Excel inputs and return a preview frame plus a separator hint."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in {".xlsx", ".xls"}:
        sheet_names = _list_excel_sheets(filepath)
        selected_sheet = worksheet.strip() if worksheet else (sheet_names[0] if sheet_names else None)
        read_kwargs: dict[str, Any] = {"header": None, "engine": "openpyxl"}
        if selected_sheet:
            read_kwargs["sheet_name"] = selected_sheet
        raw_df = pd.read_excel(filepath, **read_kwargs)
        return _extract_excel_table_frame(raw_df), "excel", sheet_names, selected_sheet

    for sep in [";", ",", "\t", "|"]:
        try:
            df = pd.read_csv(filepath, sep=sep, nrows=5, encoding="utf-8-sig")
            if len(df.columns) > 1:
                return df, sep, [], None
        except Exception:
            pass
    return pd.read_csv(filepath, nrows=5), ",", [], None


def detect_columns(filepath: str, original_name: str, site_type: str = "solar", worksheet: str | None = None) -> dict[str, Any]:
    df, sep, worksheets, selected_worksheet = _smart_read(filepath, worksheet)
    columns = list(df.columns)

    if sep != "excel":
        try:
            with open(filepath, encoding="utf-8-sig") as fh:
                first_line = fh.readline()
            for s in [";", ",", "\t", "|"]:
                if first_line.count(s) > 1:
                    sep = s
                    break
        except Exception:
            pass

    mapping: dict[str, Any] = {}

    for col in columns:
        if _TIME_PATTERNS.search(col) and "time" not in mapping:
            mapping["time"] = col
        elif _POWER_PATTERNS.search(col):
            mapping.setdefault("power", [])
            mapping["power"].append(col)  # type: ignore[union-attr]
        elif _IRR_PATTERNS.search(col) and "irradiance" not in mapping:
            mapping["irradiance"] = col
        elif _TEMP_PATTERNS.search(col):
            if site_type == "solar":
                if _MODULE_TEMP_PATTERNS.search(col) and "moduleTemperature" not in mapping:
                    mapping["moduleTemperature"] = col
                elif _AMBIENT_TEMP_PATTERNS.search(col) and "ambientTemperature" not in mapping:
                    mapping["ambientTemperature"] = col
                elif "ambientTemperature" not in mapping:
                    mapping["ambientTemperature"] = col
                elif "moduleTemperature" not in mapping:
                    mapping["moduleTemperature"] = col
            elif "temperature" not in mapping:
                mapping["temperature"] = col
        elif site_type == "wind":
            if _WIND_SPEED_PATTERNS.search(col) and "wind_speed" not in mapping:
                mapping["wind_speed"] = col
            elif _WIND_DIR_PATTERNS.search(col) and "wind_dir" not in mapping:
                mapping["wind_dir"] = col

    # Row count estimate
    row_count = -1
    try:
        if sep == "excel":
            row_count = max(len(df), 0)
        else:
            with open(filepath, encoding="utf-8-sig") as fh:
                row_count = sum(1 for _ in fh) - 1
    except Exception:
        pass

    data_date_range: list[str] | None = None
    time_column = mapping.get("time")
    if time_column:
        try:
            ext = os.path.splitext(filepath)[1].lower()
            if ext in {".xlsx", ".xls"}:
                full_df = df[[time_column]].copy()
            else:
                full_df = pd.read_csv(filepath, sep=sep, engine="python", usecols=[time_column], encoding="utf-8-sig")

            timestamps = _parse_timestamps(full_df[time_column]).dropna().sort_values()
            if not timestamps.empty:
                data_date_range = [
                    timestamps.iloc[0].date().isoformat(),
                    timestamps.iloc[-1].date().isoformat(),
                ]
        except Exception:
            pass

    return {
        "filename": original_name,
        "columns": columns,
        "mapping": {
            **mapping,
            **(
                {"temperature": mapping["ambientTemperature"]}
                if site_type == "solar" and "temperature" not in mapping and "ambientTemperature" in mapping
                else {}
            ),
        },
        "row_count": row_count,
        "separator_detected": sep,
        "data_date_range": data_date_range,
        "worksheets": worksheets,
        "selected_worksheet": selected_worksheet,
    }
