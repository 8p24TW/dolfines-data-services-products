"""
Report builder for REVEAL.

Daily and comprehensive solar reports are delegated to the legacy
SCADA PV Analysis templates so the generated output matches the
established Dolfines formatting. Monthly still falls back to the
lightweight REVEAL summary until its dedicated template is restored.
"""

from __future__ import annotations

import asyncio
import importlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from datetime import date, datetime
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

# Keep the embedded solar engine available for any legacy imports that still
# resolve through the REVEAL analysis-service bundle.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../..", "solar_engine"))


async def generate_report_file(
    data_files: list[str],
    site_config: dict[str, Any],
    column_mappings: dict[str, Any],
    report_type: str,
    lang: str,
    report_date: str | None,
    logo_variant: str,
    output_dir: str,
    output_format: str = "pdf",
) -> tuple[str, str]:
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        _run_pipeline_sync,
        data_files,
        site_config,
        column_mappings,
        report_type,
        lang,
        report_date,
        logo_variant,
        output_dir,
        output_format,
    )
    return result


async def generate_pdf(
    data_files: list[str],
    site_config: dict[str, Any],
    column_mappings: dict[str, Any],
    report_type: str,
    lang: str,
    report_date: str | None,
    logo_variant: str,
    output_dir: str,
) -> str:
    report_path, _media_type = await generate_report_file(
        data_files=data_files,
        site_config=site_config,
        column_mappings=column_mappings,
        report_type=report_type,
        lang=lang,
        report_date=report_date,
        logo_variant=logo_variant,
        output_dir=output_dir,
        output_format="pdf",
    )
    return report_path


def _run_pipeline_sync(
    data_files: list[str],
    site_config: dict[str, Any],
    column_mappings: dict[str, Any],
    report_type: str,
    lang: str,
    report_date: str | None,
    logo_variant: str,
    output_dir: str,
    output_format: str,
) -> tuple[str, str]:
    try:
        legacy_result = _try_generate_legacy_report(
            data_files=data_files,
            site_config=site_config,
            column_mappings=column_mappings,
            report_type=report_type,
            report_date=report_date,
            output_dir=output_dir,
            output_format=output_format,
        )
        if legacy_result is not None:
            return legacy_result
    except Exception as exc:
        if output_format == "html":
            return _generate_fallback_report_html(
                data_files=data_files,
                site_config=site_config,
                column_mappings=column_mappings,
                report_type=report_type,
                lang=lang,
                report_date=report_date,
                output_dir=output_dir,
                legacy_error=str(exc),
                legacy_traceback=traceback.format_exc(),
            )
        raise

    if output_format == "html":
        return _generate_fallback_report_html(
            data_files=data_files,
            site_config=site_config,
            column_mappings=column_mappings,
            report_type=report_type,
            lang=lang,
            report_date=report_date,
            output_dir=output_dir,
        )

    return _generate_fallback_report_pdf(
        data_files=data_files,
        site_config=site_config,
        column_mappings=column_mappings,
        report_type=report_type,
        lang=lang,
        report_date=report_date,
        output_dir=output_dir,
    )


def _try_generate_legacy_report(
    data_files: list[str],
    site_config: dict[str, Any],
    column_mappings: dict[str, Any],
    report_type: str,
    report_date: str | None,
    output_dir: str,
    output_format: str,
) -> tuple[str, str] | None:
    try:
        debug_context: dict[str, Any] = {}
        if report_type not in {"daily", "comprehensive"}:
            return None

        legacy_root = _find_legacy_solar_root()
        if not legacy_root.exists():
            return None

        legacy_root_str = str(legacy_root)
        if legacy_root_str not in sys.path:
            sys.path.insert(0, legacy_root_str)

        if str(site_config.get("site_type", "solar")).lower() == "wind":
            return _try_generate_wind_report(
                data_files=data_files,
                site_config=site_config,
                report_type=report_type,
                output_dir=output_dir,
                shared_report_root=legacy_root,
                output_format=output_format,
            )

        site_cfg = _normalise_site_config(site_config)
        data_dir = Path(data_files[0]).resolve().parent if data_files else Path(output_dir)
        legacy_input_dir = data_dir
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        if site_cfg.get("site_type", "solar") == "solar":
            legacy_input_dir, site_cfg = _prepare_legacy_solar_inputs(
                data_files=data_files,
                column_mappings=column_mappings,
                site_cfg=site_cfg,
                output_dir=out_dir,
            )
            debug_context = {
                "legacy_input_dir": str(legacy_input_dir),
                "effective_n_inverters": site_cfg.get("n_inverters"),
                "column_mappings": column_mappings,
                "input_files": [str(Path(p).name) for p in data_files],
            }

        if report_type == "daily":
            module = importlib.import_module("report.build_daily_report_data")
            build_daily_report = getattr(module, "build_daily_report")
            report_day = _resolve_report_date(report_date, data_files=data_files, column_mappings=column_mappings)
            _pdf_path, html_path = build_daily_report(
                site_cfg=site_cfg,
                report_date=report_day,
                data_dir=legacy_input_dir,
                out_dir=out_dir,
                skip_pdf=True,
            )
            if output_format == "html":
                return str(html_path), "text/html; charset=utf-8"
            return _render_pdf_from_html(
                html_path=Path(html_path),
                pdf_path=out_dir / f"{Path(html_path).stem}.pdf",
            )

        if report_type == "comprehensive":
            script_path = legacy_root / "pvpat_scada_analysis.py"
            if script_path.exists():
                return _run_true_comprehensive_solar_report(
                    legacy_root=legacy_root,
                    data_dir=legacy_input_dir,
                    out_dir=out_dir,
                    output_format=output_format,
                )
            # PVPAT script not available on this deployment — fall through to the
            # solar-engine rich SCADA analysis report (same template used for monthly)

        module = importlib.import_module("report.build_scada_analysis_html")
        build_scada_analysis_html = getattr(module, "build_scada_analysis_html")
        html_path = out_dir / "REVEAL_SCADA_Analysis_Report.html"
        result = build_scada_analysis_html(
            site_cfg=site_cfg,
            data_dir=legacy_input_dir,
            out_path=html_path,
            skip_pdf=output_format == "html",
        )
        if not isinstance(result, tuple) or not result:
            raise RuntimeError("Legacy comprehensive report template returned an invalid result.")
        if output_format == "html":
            html_result_path = result[1] if len(result) > 1 else None
            if html_result_path is None:
                raise RuntimeError("Legacy comprehensive report template returned no HTML output.")
            return str(html_result_path), "text/html; charset=utf-8"
        pdf_path = result[0]
        if pdf_path is None:
            errors = result[2] if len(result) > 2 else []
            raise RuntimeError(
                "Legacy comprehensive report template returned no PDF output."
                + (f" Errors: {errors}" if errors else "")
            )
        return str(pdf_path), "application/pdf"
    except Exception as exc:
        debug_suffix = f" Debug: {debug_context}" if 'debug_context' in locals() and debug_context else ""
        raise RuntimeError(f"Legacy {report_type} report generation failed ({type(exc).__name__}): {exc}{debug_suffix}") from exc


def _find_legacy_solar_root() -> Path:
    env_path = os.getenv("LEGACY_SCADA_PV_ROOT")
    if env_path:
        candidate = Path(env_path)
        if candidate.exists():
            return candidate

    direct_candidates = [
        Path("/app/legacy_scada_pv"),
        Path("/app/SCADA PV Analysis"),
    ]
    for candidate in direct_candidates:
        if candidate.exists():
            return candidate

    current = Path(__file__).resolve()
    for parent in current.parents:
        for child_name in ("SCADA PV Analysis", "legacy_scada_pv"):
            candidate = parent / child_name
            if candidate.exists():
                return candidate
        repat_candidate = parent / "REVEAL" / "SCADA PV Analysis"
        if repat_candidate.exists():
            return repat_candidate

    return Path("/app/legacy_scada_pv")


def _try_generate_wind_report(
    data_files: list[str],
    site_config: dict[str, Any],
    report_type: str,
    output_dir: str,
    shared_report_root: Path,
    output_format: str,
) -> tuple[str, str] | None:
    if report_type != "comprehensive":
        return None

    wind_root = shared_report_root.parent / "REVEAL" / "SCADA Wind Analysis"
    if not wind_root.exists():
        return None

    wind_root_str = str(wind_root)
    if wind_root_str not in sys.path:
        sys.path.insert(0, wind_root_str)

    wind_module = importlib.import_module("windpat_scada_analysis")
    wind_report_module = importlib.import_module("wind_report")
    render_report_module = importlib.import_module("report.render_report")
    style_tokens_module = importlib.import_module("report.style_tokens")

    data_dir = Path(data_files[0]).resolve().parent if data_files else Path(output_dir)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    operation = wind_module.load_operation_data(data_dir)
    messages = wind_module.load_message_data(data_dir)
    derived_config, analysis = wind_module.build_analysis(operation, messages, float(site_config.get("tariff_eur_per_kwh") or 0.09))

    display_name = str(site_config.get("display_name") or site_config.get("site_name") or "REVEAL Wind Site")
    site_kmz_path = wind_module.detect_site_kmz_path(None)
    site_location = wind_module.extract_site_location_from_kmz(site_kmz_path)

    config = {
        **derived_config,
        "site_name": display_name,
        "report_title": display_name,
        "data_dir": data_dir,
        "output_dir": out_dir,
        "report_name": "WINDPAT_SCADA_Analysis_Report.pdf",
        "style_tokens": style_tokens_module.get_style_tokens(debug_layout=False),
        "logo_white": shared_report_root / "8p2_logo_white.png",
        "logo_color": shared_report_root / "8p2_logo.png",
        "favicon": shared_report_root / "8p2_favicon_sq.jpg",
        "cover_image_path": wind_root / "bg_wind.jpg",
        "site_kmz_path": site_kmz_path,
        "site_location": site_location,
        "country": site_config.get("country") or "",
        "region": site_config.get("region") or "",
    }

    output_paths = render_report_module.build_output_paths(
        output_dir=out_dir,
        assets_dir=None,
        report_name="WINDPAT_SCADA_Analysis_Report.pdf",
        output_format="pdf",
        keep_html=True,
        pdf_engine="auto",
    )
    charts = wind_report_module.build_wind_report_assets(config=config, analysis=analysis, assets_dir=output_paths["assets_dir"])
    report_data = wind_report_module.build_wind_report_data(config=config, analysis=analysis, charts=charts, outputs=output_paths)
    results = render_report_module.render_report_outputs(
        report_data=report_data,
        output_paths=output_paths,
        template_dir=shared_report_root / "report" / "templates",
        static_dir=shared_report_root / "report" / "static",
    )
    if output_format == "html":
        html_path = results.get("html_path")
        return (str(html_path), "text/html; charset=utf-8") if html_path else None
    pdf_path = results.get("pdf_path")
    return (str(pdf_path), "application/pdf") if pdf_path else None


def _normalise_site_config(site_config: dict[str, Any]) -> dict[str, Any]:
    display_name = str(site_config.get("display_name") or site_config.get("site_name") or "REVEAL Site")
    inverter_model = str(site_config.get("inverter_model") or site_config.get("inv_model") or "")
    operating_pr_target = float(
        site_config.get("operating_pr_target")
        or site_config.get("design_pr")
        or 0.79
    )

    return {
        **site_config,
        "display_name": display_name,
        "site_name": display_name,
        "technology": str(site_config.get("technology") or "Solar PV"),
        "site_type": str(site_config.get("site_type") or "solar"),
        "cap_ac_kw": float(site_config.get("cap_ac_kw") or 0),
        "cap_dc_kwp": float(site_config.get("cap_dc_kwp") or 0),
        "n_inverters": int(site_config.get("n_inverters") or 1),
        "inv_ac_kw": float(site_config.get("inv_ac_kw") or 0),
        "inverter_model": inverter_model,
        "inv_model": inverter_model,
        "module_brand": str(site_config.get("module_brand") or ""),
        "module_wp": float(site_config.get("module_wp") or 0),
        "n_modules": int(site_config.get("n_modules") or 0),
        "dc_ac_ratio": float(site_config.get("dc_ac_ratio") or 1.0),
        "design_pr": float(site_config.get("design_pr") or operating_pr_target),
        "operating_pr_target": operating_pr_target,
        "interval_min": int(site_config.get("interval_min") or 10),
        "irr_threshold": float(site_config.get("irr_threshold") or 50),
        "power_threshold": float(site_config.get("power_threshold") or 5),
        "country": str(site_config.get("country") or ""),
        "region": str(site_config.get("region") or ""),
        "cod": str(site_config.get("cod") or ""),
    }


def _prepare_legacy_solar_inputs(
    data_files: list[str],
    column_mappings: dict[str, Any],
    site_cfg: dict[str, Any],
    output_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    if not data_files:
        return (Path(data_files[0]).resolve().parent if data_files else output_dir, site_cfg)

    frames: list[pd.DataFrame] = []
    irr_frames: list[pd.DataFrame] = []
    selected_power_labels: set[str] = set()
    power_by_year_ptr: dict[tuple[int, str], list[pd.DataFrame]] = {}
    irradiance_by_year: dict[int, list[pd.DataFrame]] = {}

    for file_path in data_files:
        source = Path(file_path)
        if not source.exists():
            continue

        mapping = _resolve_mapping_for_file(column_mappings, source)
        worksheet = _mapping_worksheet(mapping)
        power_columns = [str(col).strip() for col in (mapping.get("power") or []) if str(col).strip()]
        time_column = str(mapping.get("time") or "").strip()
        irradiance_column = str(mapping.get("irradiance") or "").strip()
        ambient_temperature_column = str(mapping.get("ambientTemperature") or mapping.get("temperature") or "").strip()
        module_temperature_column = str(mapping.get("moduleTemperature") or "").strip()

        if not time_column or not power_columns:
            continue

        if source.suffix.lower() in {".xlsx", ".xls"}:
            read_kwargs: dict[str, Any] = {}
            if worksheet:
                read_kwargs["sheet_name"] = worksheet
            df = pd.read_excel(source, **read_kwargs)
        else:
            df = pd.read_csv(source)

        df.columns = [str(col).strip() for col in df.columns]
        if time_column not in df.columns:
            continue

        df[time_column] = pd.to_datetime(df[time_column], dayfirst=True, errors="coerce")
        df = df.dropna(subset=[time_column]).copy()
        if df.empty:
            continue

        available_power_cols = [col for col in power_columns if col in df.columns]
        if available_power_cols:
            selected_power_labels.update(available_power_cols)
            inv_df = df[[time_column] + available_power_cols].copy()
            melted = inv_df.melt(id_vars=time_column, var_name="EQUIP", value_name="PAC")
            melted = melted.rename(columns={time_column: "Time_UDT"})
            melted["PAC"] = pd.to_numeric(melted["PAC"], errors="coerce").fillna(0.0)
            melted = melted[["Time_UDT", "EQUIP", "PAC"]]
            frames.append(melted)

            fallback_ptr_map = _build_fallback_ptr_map(available_power_cols)
            for year, year_frame in melted.groupby(melted["Time_UDT"].dt.year):
                for ptr_name, ptr_frame in year_frame.groupby(year_frame["EQUIP"].map(lambda label: _infer_ptr_name(str(label), fallback_ptr_map))):
                    if ptr_frame.empty:
                        continue
                    power_by_year_ptr.setdefault((int(year), ptr_name), []).append(ptr_frame)

        if irradiance_column and irradiance_column in df.columns:
            irr_cols = [time_column, irradiance_column]
            if ambient_temperature_column and ambient_temperature_column in df.columns:
                irr_cols.append(ambient_temperature_column)
            if module_temperature_column and module_temperature_column in df.columns:
                irr_cols.append(module_temperature_column)
            irr_df = df[irr_cols].copy()
            rename_map = {time_column: "Time_UDT", irradiance_column: "GHI"}
            if ambient_temperature_column and ambient_temperature_column in irr_df.columns:
                rename_map[ambient_temperature_column] = "T_amb"
            if module_temperature_column and module_temperature_column in irr_df.columns:
                rename_map[module_temperature_column] = "T_panel"
            irr_df = irr_df.rename(columns=rename_map)
            irr_df["GHI"] = pd.to_numeric(irr_df["GHI"], errors="coerce").fillna(0.0)
            irr_df["T_amb"] = pd.to_numeric(irr_df.get("T_amb"), errors="coerce")
            irr_df["T_panel"] = pd.to_numeric(irr_df.get("T_panel"), errors="coerce")
            irr_df = irr_df[["Time_UDT", "GHI", "T_amb", "T_panel"]]
            irr_frames.append(irr_df)
            for year, year_frame in irr_df.groupby(irr_df["Time_UDT"].dt.year):
                irradiance_by_year.setdefault(int(year), []).append(year_frame)

    if not frames:
        return (Path(data_files[0]).resolve().parent if data_files else output_dir, site_cfg)

    tmp_root = Path(tempfile.mkdtemp(prefix="reveal-legacy-solar-", dir=str(output_dir)))
    inverter_csv = tmp_root / "inverter_power.csv"
    pd.concat(frames, ignore_index=True).to_csv(inverter_csv, index=False, sep=";")

    if irr_frames:
        irradiance_csv = tmp_root / "irradiance.csv"
        pd.concat(irr_frames, ignore_index=True).to_csv(irradiance_csv, index=False, sep=";")

    for (year, ptr_name), ptr_frames in power_by_year_ptr.items():
        ptr_output = tmp_root / f"{ptr_name}_{year}.csv"
        ptr_df = pd.concat(ptr_frames, ignore_index=True).copy()
        ptr_df["Time_UDT"] = ptr_df["Time_UDT"].dt.strftime("%d/%m/%Y %H:%M")
        ptr_df = ptr_df[["Time_UDT", "EQUIP", "PAC"]]
        ptr_df.to_csv(ptr_output, index=False, sep=";", header=True)

    for year, year_frames in irradiance_by_year.items():
        irr_output = tmp_root / f"Irradiance_{year}.csv"
        irr_year_df = pd.concat(year_frames, ignore_index=True).copy()
        irr_year_df["Time_UTC"] = irr_year_df["Time_UDT"].dt.strftime("%d/%m/%Y %H:%M")
        irr_year_df = irr_year_df.rename(columns={"GHI": "WSIrradianceA", "T_amb": "WSTExt", "T_panel": "WSTPanneau"})
        irr_year_df = irr_year_df[["Time_UTC", "WSIrradianceA", "WSTExt", "WSTPanneau"]]
        irr_year_df.to_csv(irr_output, index=False, sep=";", header=True)

    _copy_legacy_solar_assets(tmp_root)

    adjusted_site_cfg = {
        **site_cfg,
        "n_inverters": max(len(selected_power_labels), 1),
    }
    return tmp_root, adjusted_site_cfg


def _build_fallback_ptr_map(power_columns: list[str]) -> dict[str, str]:
    ordered = sorted({str(col).strip() for col in power_columns if str(col).strip()})
    midpoint = max((len(ordered) + 1) // 2, 1)
    return {
        label: "PTR1" if index < midpoint else "PTR2"
        for index, label in enumerate(ordered)
    }


def _infer_ptr_name(label: str, fallback_map: dict[str, str]) -> str:
    lowered = label.lower()
    if lowered.startswith("ond1") or lowered.startswith("ptr1") or lowered.startswith("inv1"):
        return "PTR1"
    if lowered.startswith("ond2") or lowered.startswith("ptr2") or lowered.startswith("inv2"):
        return "PTR2"
    match = re.search(r"(\d+)", lowered)
    if match:
        leading_group = match.group(1)
        if leading_group.startswith("1"):
            return "PTR1"
        if leading_group.startswith("2"):
            return "PTR2"
    return fallback_map.get(label, "PTR1")


def _copy_legacy_solar_assets(target_dir: Path) -> None:
    legacy_root = _find_legacy_solar_root()
    asset_sources = [
        legacy_root / "00orig" / "8p2 advisory white.png",
        legacy_root / "00orig" / "solar_farm_2.jpg",
        legacy_root / "00orig" / "Test.csv",
        legacy_root / "00orig" / "SARAH_Nord.csv",
        legacy_root / "00orig" / "SARAH_Sud.csv",
    ]
    for source in asset_sources:
        if source.exists():
            shutil.copy2(source, target_dir / source.name)


def _run_true_comprehensive_solar_report(
    legacy_root: Path,
    data_dir: Path,
    out_dir: Path,
    output_format: str,
) -> tuple[str, str]:
    script_path = legacy_root / "pvpat_scada_analysis.py"
    if not script_path.exists():
        raise FileNotFoundError(f"Comprehensive PVPAT script not found at {script_path}")

    report_name = "PVPAT_SCADA_Analysis_Report.pdf"
    command = [
        sys.executable,
        str(script_path),
        "--data-dir",
        str(data_dir),
        "--out-dir",
        str(out_dir),
        "--report-name",
        report_name,
    ]
    result = subprocess.run(
        command,
        cwd=str(legacy_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "PVPAT comprehensive report generation failed: "
            f"{result.stderr.strip() or result.stdout.strip() or f'exit code {result.returncode}'}"
        )

    pdf_path = out_dir / report_name
    if not pdf_path.exists():
        raise FileNotFoundError(f"PVPAT comprehensive report did not produce {pdf_path}")

    if output_format == "html":
        html_path = out_dir / "PVPAT_SCADA_Analysis_Report.html"
        html_content = (
            "<!doctype html><html><body style=\"font-family:Arial,sans-serif;padding:24px;\">"
            "<h1>PVPAT Comprehensive Report Ready</h1>"
            "<p>The comprehensive report was generated as a PDF for this run.</p>"
            f"<p>PDF file: {escape(pdf_path.name)}</p>"
            "</body></html>"
        )
        html_path.write_text(html_content, encoding="utf-8")
        return str(html_path), "text/html; charset=utf-8"

    return str(pdf_path), "application/pdf"


def _resolve_mapping_for_file(
    column_mappings: dict[str, Any],
    source: Path,
) -> dict[str, Any]:
    if not isinstance(column_mappings, dict):
        return {}

    # Flat mapping shape.
    if any(key in column_mappings for key in ("time", "power", "irradiance", "temperature")):
        return column_mappings

    candidates = [
        source.name,
        source.name.lower(),
        source.stem,
        source.stem.lower(),
    ]
    for key in candidates:
        value = column_mappings.get(key)
        if isinstance(value, dict):
            return value

    for key, value in column_mappings.items():
        if isinstance(value, dict) and str(key).lower() == source.name.lower():
            return value

    return {}


def _mapping_worksheet(mapping: dict[str, Any]) -> str | None:
    worksheet = mapping.get("worksheet") if isinstance(mapping, dict) else None
    if worksheet is None:
        return None
    value = str(worksheet).strip()
    return value or None


def _resolve_report_date(
    report_date: str | None,
    data_files: list[str] | None = None,
    column_mappings: dict[str, Any] | None = None,
) -> date:
    if not report_date:
        inferred = _infer_single_report_date(data_files or [], column_mappings or {})
        return inferred or datetime.utcnow().date()

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(report_date, fmt).date()
        except ValueError:
            continue
    inferred = _infer_single_report_date(data_files or [], column_mappings or {})
    return inferred or datetime.utcnow().date()


def _infer_single_report_date(data_files: list[str], column_mappings: dict[str, Any]) -> date | None:
    if not data_files:
        return None

    try:
        import pandas as pd
    except Exception:
        return None

    time_aliases = {
        "time_udt", "time_utc", "time_local", "time", "datetime",
        "timestamp", "date_time", "horodate", "date",
    }

    for file_path in data_files:
        path = Path(file_path)
        mapping = _resolve_mapping_for_file(column_mappings, path)
        worksheet = _mapping_worksheet(mapping)
        try:
            if path.suffix.lower() in {".xlsx", ".xls"}:
                read_kwargs: dict[str, Any] = {}
                if worksheet:
                    read_kwargs["sheet_name"] = worksheet
                df = pd.read_excel(path, **read_kwargs)
            else:
                df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig", low_memory=False)
        except Exception:
            continue

        if df.empty:
            continue

        df.columns = [str(c).strip() for c in df.columns]
        time_col = next((c for c in df.columns if c.lower() in time_aliases), None)
        if time_col is None:
            time_col = str(df.columns[0])

        series = pd.to_datetime(df[time_col], dayfirst=True, errors="coerce")
        unique_dates = sorted({ts.date() for ts in series.dropna()})
        if len(unique_dates) == 1:
            return unique_dates[0]

    return None


def _generate_fallback_report_pdf(
    data_files: list[str],
    site_config: dict[str, Any],
    column_mappings: dict[str, Any],
    report_type: str,
    lang: str,
    report_date: str | None,
    output_dir: str,
) -> tuple[str, str]:
    from playwright.sync_api import sync_playwright

    title = "REVEAL Reporting Summary" if lang == "en" else "Synthèse de rapport REVEAL"
    site_name = str(site_config.get("site_name") or site_config.get("display_name") or "REVEAL Site")
    technology = str(site_config.get("technology", site_config.get("site_type", "solar"))).strip() or "solar"
    cap_ac = site_config.get("cap_ac_kw", "—")
    cap_dc = site_config.get("cap_dc_kwp", "—")
    n_inverters = site_config.get("n_inverters", "—")
    report_date_label = report_date or ("Not specified" if lang == "en" else "Non précisée")

    file_sections: list[str] = []
    for file_path in data_files:
        file_name = os.path.basename(file_path)
        mapping = column_mappings.get(file_name, {})
        power_cols = mapping.get("power", [])
        worksheet = mapping.get("worksheet", "—")
        if isinstance(power_cols, str):
            power_cols = [power_cols]
        power_text = ", ".join(power_cols) if power_cols else "—"
        file_sections.append(
            f"""
            <div class="file-card">
              <h3>{escape(file_name)}</h3>
              <p><strong>{'Worksheet' if lang == 'en' else 'Feuille'}:</strong> {escape(str(worksheet))}</p>
              <p><strong>{'Timestamp' if lang == 'en' else 'Horodatage'}:</strong> {escape(str(mapping.get('time', '—')))}</p>
              <p><strong>{'Power columns' if lang == 'en' else 'Colonnes de puissance'}:</strong> {escape(power_text)}</p>
              <p><strong>{'Irradiance' if lang == 'en' else 'Irradiance'}:</strong> {escape(str(mapping.get('irradiance', '—')))}</p>
              <p><strong>{'Temperature' if lang == 'en' else 'Température'}:</strong> {escape(str(mapping.get('temperature', '—')))}</p>
            </div>
            """
        )

    html = f"""<!doctype html>
<html lang="{escape(lang)}">
  <head>
    <meta charset="utf-8" />
    <title>{escape(title)}</title>
    <style>
      body {{
        font-family: Arial, sans-serif;
        margin: 0;
        background: #051b2b;
        color: #f6f8fb;
      }}
      .page {{
        padding: 36px 42px 48px;
      }}
      .hero {{
        border-radius: 24px;
        padding: 28px 30px;
        background: linear-gradient(135deg, rgba(4,18,28,0.94), rgba(8,39,59,0.88));
        border: 1px solid rgba(255,255,255,0.12);
      }}
      .eyebrow {{
        text-transform: uppercase;
        letter-spacing: 0.3em;
        color: rgba(255,255,255,0.62);
        font-size: 11px;
        font-weight: 700;
      }}
      h1 {{
        margin: 12px 0 8px;
        font-size: 30px;
      }}
      .subtitle {{
        color: rgba(255,255,255,0.82);
        font-size: 14px;
        line-height: 1.6;
      }}
      .kpis {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 14px;
        margin: 22px 0 0;
      }}
      .kpi {{
        border-radius: 18px;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        padding: 16px;
      }}
      .kpi-label {{
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        color: rgba(255,255,255,0.58);
        margin-bottom: 10px;
      }}
      .kpi-value {{
        font-size: 22px;
        font-weight: 700;
      }}
      .section {{
        margin-top: 22px;
        border-radius: 22px;
        background: rgba(4,18,28,0.84);
        border: 1px solid rgba(255,255,255,0.1);
        padding: 22px 24px;
      }}
      .section h2 {{
        margin: 0 0 14px;
        font-size: 18px;
      }}
      .files {{
        display: grid;
        gap: 12px;
      }}
      .file-card {{
        border-radius: 16px;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        padding: 14px 16px;
      }}
      .file-card h3 {{
        margin: 0 0 10px;
        color: #ea7824;
        font-size: 15px;
      }}
      .file-card p {{
        margin: 6px 0;
        font-size: 13px;
        line-height: 1.5;
      }}
    </style>
  </head>
  <body>
    <div class="page">
      <section class="hero">
        <div class="eyebrow">REVEAL Renewable Energy Valuation, Evaluation and Analytics Lab</div>
        <h1>{escape(title)} · {escape(site_name)}</h1>
        <div class="subtitle">
          {'Fallback PDF generated from the active REVEAL job pipeline while the legacy template is unavailable.' if lang == 'en' else 'PDF de secours généré depuis le pipeline REVEAL actif pendant l’indisponibilité du modèle historique.'}
        </div>
        <div class="kpis">
          <div class="kpi"><div class="kpi-label">{'Report type' if lang == 'en' else 'Type de rapport'}</div><div class="kpi-value">{escape(report_type.title())}</div></div>
          <div class="kpi"><div class="kpi-label">{'Technology' if lang == 'en' else 'Technologie'}</div><div class="kpi-value">{escape(technology)}</div></div>
          <div class="kpi"><div class="kpi-label">AC</div><div class="kpi-value">{escape(str(cap_ac))}</div></div>
          <div class="kpi"><div class="kpi-label">{'Report date' if lang == 'en' else 'Date du rapport'}</div><div class="kpi-value">{escape(report_date_label)}</div></div>
        </div>
      </section>
      <section class="section">
        <h2>{'Asset context' if lang == 'en' else 'Contexte de l’actif'}</h2>
        <p><strong>{'DC capacity' if lang == 'en' else 'Puissance DC'}:</strong> {escape(str(cap_dc))}</p>
        <p><strong>{'Inverters' if lang == 'en' else 'Onduleurs'}:</strong> {escape(str(n_inverters))}</p>
      </section>
      <section class="section">
        <h2>{'Uploaded files and selected mappings' if lang == 'en' else 'Fichiers chargés et mappings sélectionnés'}</h2>
        <div class="files">
          {''.join(file_sections)}
        </div>
      </section>
    </div>
  </body>
</html>"""

    output_path = Path(output_dir)
    html_path = output_path / "reveal_report_fallback.html"
    pdf_path = output_path / "reveal_report_fallback.pdf"
    html_path.write_text(html, encoding="utf-8")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(html_path.as_uri(), wait_until="networkidle")
        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            margin={"top": "18mm", "bottom": "18mm", "left": "14mm", "right": "14mm"},
        )
        browser.close()

    return str(pdf_path), "application/pdf"


def _generate_fallback_report_html(
    data_files: list[str],
    site_config: dict[str, Any],
    column_mappings: dict[str, Any],
    report_type: str,
    lang: str,
    report_date: str | None,
    output_dir: str,
    legacy_error: str | None = None,
    legacy_traceback: str | None = None,
) -> tuple[str, str]:
    title = "REVEAL Reporting Summary" if lang == "en" else "Synthèse de rapport REVEAL"
    site_name = str(site_config.get("site_name") or site_config.get("display_name") or "REVEAL Site")
    technology = str(site_config.get("technology", site_config.get("site_type", "solar"))).strip() or "solar"
    cap_ac = site_config.get("cap_ac_kw", "—")
    cap_dc = site_config.get("cap_dc_kwp", "—")
    n_inverters = site_config.get("n_inverters", "—")
    report_date_label = report_date or ("Not specified" if lang == "en" else "Non précisée")

    file_sections: list[str] = []
    for file_path in data_files:
        file_name = os.path.basename(file_path)
        mapping = column_mappings.get(file_name, {})
        power_cols = mapping.get("power", [])
        if isinstance(power_cols, str):
            power_cols = [power_cols]
        power_text = ", ".join(power_cols) if power_cols else "—"
        file_sections.append(
            f"""
            <div class="file-card">
              <h3>{escape(file_name)}</h3>
              <p><strong>{'Timestamp' if lang == 'en' else 'Horodatage'}:</strong> {escape(str(mapping.get('time', '—')))}</p>
              <p><strong>{'Power columns' if lang == 'en' else 'Colonnes de puissance'}:</strong> {escape(power_text)}</p>
              <p><strong>{'Irradiance' if lang == 'en' else 'Irradiance'}:</strong> {escape(str(mapping.get('irradiance', '—')))}</p>
              <p><strong>{'Temperature' if lang == 'en' else 'Température'}:</strong> {escape(str(mapping.get('temperature', '—')))}</p>
            </div>
            """
        )

    legacy_note = ""
    if legacy_error:
        legacy_note = f"""
      <section class="section">
        <h2>{'Legacy template status' if lang == 'en' else 'Statut du modèle historique'}</h2>
        <p><strong>{'The legacy template failed and REVEAL generated this HTML fallback so the report can still be reviewed.' if lang == 'en' else 'Le modèle historique a échoué et REVEAL a généré ce HTML de secours afin que le rapport puisse quand même être consulté.'}</strong></p>
        <p><code>{escape(legacy_error)}</code></p>
        {'<details><summary>Traceback</summary><pre>' + escape(legacy_traceback or '') + '</pre></details>' if legacy_traceback else ''}
      </section>"""

    html = f"""<!doctype html>
<html lang="{escape(lang)}">
  <head>
    <meta charset="utf-8" />
    <title>{escape(title)}</title>
    <style>
      body {{
        font-family: Arial, sans-serif;
        margin: 0;
        background: #051b2b;
        color: #f6f8fb;
      }}
      .page {{
        padding: 36px 42px 48px;
      }}
      .hero {{
        border-radius: 24px;
        padding: 28px 30px;
        background: linear-gradient(135deg, rgba(4,18,28,0.94), rgba(8,39,59,0.88));
        border: 1px solid rgba(255,255,255,0.12);
      }}
      .eyebrow {{
        text-transform: uppercase;
        letter-spacing: 0.3em;
        color: rgba(255,255,255,0.62);
        font-size: 11px;
        font-weight: 700;
      }}
      h1 {{
        margin: 12px 0 8px;
        font-size: 30px;
      }}
      .subtitle {{
        color: rgba(255,255,255,0.82);
        font-size: 14px;
        line-height: 1.6;
      }}
      .kpis {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 14px;
        margin: 22px 0 0;
      }}
      .kpi {{
        border-radius: 18px;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        padding: 16px;
      }}
      .kpi-label {{
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        color: rgba(255,255,255,0.58);
        margin-bottom: 10px;
      }}
      .kpi-value {{
        font-size: 22px;
        font-weight: 700;
      }}
      .section {{
        margin-top: 22px;
        border-radius: 22px;
        background: rgba(4,18,28,0.84);
        border: 1px solid rgba(255,255,255,0.1);
        padding: 22px 24px;
      }}
      .section h2 {{
        margin: 0 0 14px;
        font-size: 18px;
      }}
      .files {{
        display: grid;
        gap: 12px;
      }}
      .file-card {{
        border-radius: 16px;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        padding: 14px 16px;
      }}
      .file-card h3 {{
        margin: 0 0 10px;
        color: #ea7824;
        font-size: 15px;
      }}
      .file-card p {{
        margin: 6px 0;
        font-size: 13px;
        line-height: 1.5;
      }}
    </style>
  </head>
  <body>
    <div class="page">
      <section class="hero">
        <div class="eyebrow">REVEAL Renewable Energy Valuation, Evaluation and Analytics Lab</div>
        <h1>{escape(title)} · {escape(site_name)}</h1>
        <div class="subtitle">
          {'HTML fallback generated from the active REVEAL job pipeline so the legacy report content can be inspected directly.' if lang == 'en' else 'HTML de secours généré depuis le pipeline REVEAL actif afin d’inspecter directement le contenu du rapport historique.'}
        </div>
        <div class="kpis">
          <div class="kpi"><div class="kpi-label">{'Report type' if lang == 'en' else 'Type de rapport'}</div><div class="kpi-value">{escape(report_type.title())}</div></div>
          <div class="kpi"><div class="kpi-label">{'Technology' if lang == 'en' else 'Technologie'}</div><div class="kpi-value">{escape(technology)}</div></div>
          <div class="kpi"><div class="kpi-label">AC</div><div class="kpi-value">{escape(str(cap_ac))}</div></div>
          <div class="kpi"><div class="kpi-label">{'Report date' if lang == 'en' else 'Date du rapport'}</div><div class="kpi-value">{escape(report_date_label)}</div></div>
        </div>
      </section>
      <section class="section">
        <h2>{'Asset context' if lang == 'en' else 'Contexte de l’actif'}</h2>
        <p><strong>{'DC capacity' if lang == 'en' else 'Puissance DC'}:</strong> {escape(str(cap_dc))}</p>
        <p><strong>{'Inverters' if lang == 'en' else 'Onduleurs'}:</strong> {escape(str(n_inverters))}</p>
      </section>
      <section class="section">
        <h2>{'Uploaded files and selected mappings' if lang == 'en' else 'Fichiers chargés et mappings sélectionnés'}</h2>
        <div class="files">
          {''.join(file_sections)}
        </div>
      </section>
      {legacy_note}
    </div>
  </body>
</html>"""

    output_path = Path(output_dir)
    html_path = output_path / "reveal_report_fallback.html"
    html_path.write_text(html, encoding="utf-8")
    return str(html_path), "text/html; charset=utf-8"


def _render_pdf_from_html(html_path: Path, pdf_path: Path) -> str:
    from playwright.sync_api import sync_playwright

    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page()
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            margin={"top": "8mm", "right": "8mm", "bottom": "8mm", "left": "8mm"},
        )
        browser.close()

    return str(pdf_path)
