#!/usr/bin/env python3
"""
Jinja2 report runner for Sohmex SCADA Analysis.

Loads data via pvpat_scada_analysis, runs the full analysis pipeline,
then generates HTML + PDF via the report/ Jinja2 template pipeline
(chart_factory → build_report_data → render_report).

Output: _report_test_output/PVPAT_SCADA_Analysis_Report.html + .pdf
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime

# Ensure this script's directory is on sys.path so report/ sub-package is found
SCRIPT_DIR = Path(__file__).parent.resolve()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Import all analysis helpers from the existing SCADA analysis module
import pvpat_scada_analysis as _pv

# ── Output paths ─────────────────────────────────────────────
DATA_DIR    = _pv.DATA_DIR
OUT_DIR     = _pv.OUT_DIR
ASSETS_DIR  = OUT_DIR / "PVPAT_SCADA_Analysis_Report_assets"
REPORT_STEM = "PVPAT_SCADA_Analysis_Report"

TEMPLATE_DIR = SCRIPT_DIR / "report" / "templates"
STATIC_DIR   = SCRIPT_DIR / "report" / "static"


def main() -> None:
    print("=" * 65)
    print("  Sohmex SCADA Analysis — Jinja2 Report Pipeline")
    print("=" * 65)
    print(f"  Data directory  : {DATA_DIR}")
    print(f"  Output directory: {OUT_DIR}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Phase 1: Load data ────────────────────────────────────
    print("\n[1/5] Loading data …")
    inv_data     = _pv.load_inverter_data()
    irr_data     = _pv.load_irradiance_data()
    sarah        = _pv.load_sarah_data()

    # ── Phase 2: Process ──────────────────────────────────────
    print("\n[2/5] Processing …")
    piv_raw          = _pv.pivot_power(inv_data)
    cap_kw, inv_caps = _pv.estimate_site_capacity(piv_raw, irr_data)
    piv, stuck_report = _pv.clean_stuck_values(piv_raw)
    if stuck_report:
        print(f"  NOTE: {len(stuck_report)} inverter(s) had stuck readings removed.")

    # ── Phase 3: Analyse ──────────────────────────────────────
    print("\n[3/5] Analysing …")
    data_avail    = _pv.analyse_data_availability(piv, irr_data)
    pr_res        = _pv.analyse_pr(piv, irr_data, cap_kw)
    avail_res     = _pv.analyse_availability(piv, irr_data)
    irr_coh       = _pv.analyse_irradiance_coherence(irr_data, sarah)
    mttf_res      = _pv.analyse_mttf(piv, irr_data)
    inv_sy_df     = _pv.analyse_inv_specific_yield(piv, irr_data)
    start_stop_df = _pv.analyse_start_stop(piv, irr_data)
    wf            = _pv.build_waterfall(pr_res, irr_data, sarah, avail_res, cap_kw)
    punchlist     = _pv.generate_punchlist(
        avail_res, pr_res, irr_coh, mttf_res, data_avail, cap_kw,
        wf=wf, start_stop_df=start_stop_df,
    )
    weather_data  = _pv.fetch_weather_data(OUT_DIR / "weather_cache.json")

    # ── Phase 4: Build Jinja2 report ──────────────────────────
    print("\n[4/5] Generating charts via Jinja2 pipeline …")

    from report.style_tokens import get_style_tokens
    from report.chart_factory import build_report_assets
    from report.build_report_data import build_report_data
    from report.render_report import render_report_outputs, build_output_paths
    from report.preflight import run_preflight

    style_tokens = get_style_tokens()

    config: dict = {
        # Style
        "style_tokens":   style_tokens,
        "sort_key":       _pv._nat,
        "debug_layout":   False,
        # Capacities
        "cap_dc_kwp":     _pv.CAP_DC_KWP,
        "cap_ac_kw":      _pv.CAP_AC_KW,
        "dc_ac_ratio":    _pv.DC_AC_RATIO,
        "inv_ac_kw":      _pv.INV_AC_KW,
        # Technology
        "n_modules":      _pv.N_MODULES,
        "module_wp":      _pv.MODULE_WP,
        "module_brand":   _pv.MODULE_BRAND,
        "n_inverters":    _pv.N_INVERTERS,
        "inv_model":      _pv.INV_MODEL,
        "n_strings_inv":  _pv.N_STRINGS_INV,
        "n_ptr":          _pv.N_PTR,
        "structure_types":_pv.STRUCT_TYPES,
        # Analysis params
        "interval_h":     _pv.INTERVAL_H,
        "interval_min":   _pv.INTERVAL_MIN,
        "irr_threshold":  _pv.IRR_THRESHOLD,
        "design_pr":      _pv.DESIGN_PR,
        "temp_coeff":     _pv.TEMP_COEFF,
        # Metadata
        "site_name":      _pv.SITE_NAME,
        "report_title":   f"{_pv.SITE_NAME} – SCADA Performance Analysis",
        "generated_at":   datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "data_dir":       DATA_DIR,
        "output_dir":     OUT_DIR,
        # Assets
        "logo_white":     str(SCRIPT_DIR / "8p2_logo_white.png"),
        "logo_color":     str(SCRIPT_DIR / "8p2_logo.png"),
        "favicon":        str(SCRIPT_DIR / "8p2_favicon.png"),
        "cover_image_path": str(SCRIPT_DIR / "00orig" / "solar_farm_2.jpg"),
    }

    analysis: dict = {
        "pr_res":        pr_res,
        "avail_res":     avail_res,
        "data_avail":    data_avail,
        "irr_coh":       irr_coh,
        "mttf_res":      mttf_res,
        "inv_sy_df":     inv_sy_df,
        "start_stop_df": start_stop_df,
        "wf":            wf,
        "punchlist":     punchlist,
        "piv":           piv,
        "irr_data":      irr_data,
        "cap_kw":        cap_kw,
        "weather_data":  weather_data,
    }

    # Generate all SVG/PNG charts
    charts = build_report_assets(config=config, analysis=analysis, assets_dir=ASSETS_DIR)
    print(f"  Generated {len(charts)} chart asset(s).")

    # Build output path descriptors
    output_paths = build_output_paths(
        output_dir=OUT_DIR,
        assets_dir=ASSETS_DIR,
        report_name=REPORT_STEM,
        output_format="pdf",
        keep_html=True,
        pdf_engine="auto",
    )

    # Initial preflight stub (pages not yet built)
    initial_preflight: dict = {
        "ok":           True,
        "errors":       [],
        "warnings":     [],
        "debug_layout": False,
    }

    # Build structured page data
    print("  Building report page data …")
    report_data = build_report_data(
        config=config,
        analysis=analysis,
        charts=charts,
        outputs=output_paths,
        preflight=initial_preflight,
    )

    # Full preflight (checks chart files, page limits, etc.)
    preflight = run_preflight(report_data, charts, config)
    if preflight["errors"]:
        print("  PREFLIGHT ERRORS:")
        for err in preflight["errors"]:
            print(f"    ✗ {err}")
    if preflight["warnings"]:
        for w in preflight["warnings"]:
            print(f"    ⚠ {w}")

    # ── Phase 5: Render ───────────────────────────────────────
    print("\n[5/5] Rendering HTML + PDF …")
    result = render_report_outputs(
        report_data=report_data,
        output_paths=output_paths,
        template_dir=TEMPLATE_DIR,
        static_dir=STATIC_DIR,
    )

    print("\n" + "=" * 65)
    if result.get("html_path"):
        print(f"  HTML : {result['html_path']}")
    if result.get("pdf_path"):
        print(f"  PDF  : {result['pdf_path']}")
    engine = result.get("pdf_engine_used")
    if engine:
        print(f"  Engine: {engine}")
    print("=" * 65)


if __name__ == "__main__":
    main()
