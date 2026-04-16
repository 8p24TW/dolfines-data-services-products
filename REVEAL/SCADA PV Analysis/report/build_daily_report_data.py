"""
build_daily_report_data.py — 4-5 page daily PDF report builder
===============================================================
Uses the same Jinja2 + Playwright pipeline as the comprehensive report.
Pages:
  1. Cover
  2. Daily KPIs + Irradiance profile
  3. Per-Inverter Specific Yield & PR
  4. Per-Inverter Availability
  5. Waterfall + Alerts / Alarms
"""

from __future__ import annotations

import base64
import os
import subprocess
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Optional

# ── Paths ──────────────────────────────────────────────────────────────────
_HERE   = Path(__file__).parent
_ROOT   = _HERE.parent                 # SCADA PV Analysis/
_STATIC = _HERE / "static"
_TMPL   = _HERE / "templates"


def _b64_png(png_bytes: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode()


def _b64_file(path: Path, mime: str = "image/png") -> str:
    if path.exists():
        return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# REPORT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_daily_report(
    site_cfg: dict,
    report_date: date,
    data_dir: Optional[Path] = None,
    out_dir: Optional[Path] = None,
    skip_pdf: bool = False,
) -> tuple[Optional[Path], Path]:
    """
    Run daily analysis, render HTML, convert to PDF with Playwright (if available).
    Returns (pdf_path | None, html_path).
    Pass skip_pdf=True to skip Playwright and return only the HTML path.
    """
    from report.daily_analysis import DailyAnalysis
    from report.daily_chart_factory import (
        chart_daily_irradiance,
        chart_per_inverter_yield,
        chart_per_inverter_availability,
        chart_per_inverter_pr,
        chart_daily_waterfall,
    )

    # ── 1. Analyse ──────────────────────────────────────────────────────────
    analysis = DailyAnalysis(site_cfg, report_date, data_dir)
    results  = analysis.run()

    has_real_inv  = not results.get("used_demo", False)
    has_irr       = results["irradiance"]["insolation_kwh_m2"] > 0

    irradiance  = results["irradiance"]
    per_inv     = results["per_inverter"]
    site_totals = results["site_totals"]
    waterfall   = results["waterfall"]
    alerts      = results["alerts"]

    # ── 2. Charts ───────────────────────────────────────────────────────────
    import pandas as _pd
    pr_target = site_cfg["operating_pr_target"]

    # Hourly AC production (kWh) for overlay on irradiance chart
    _power_ts = results.get("site_power_ts", _pd.Series(dtype=float))
    if not _power_ts.empty:
        _interval_h = site_cfg["interval_min"] / 60.0
        hourly_kwh = _power_ts.resample("1h").sum() * _interval_h
    else:
        hourly_kwh = _pd.Series(dtype=float)

    chart_irr    = _b64_png(chart_daily_irradiance(irradiance, hourly_kwh))
    chart_yield  = _b64_png(chart_per_inverter_yield(per_inv, pr_target))
    chart_avail  = _b64_png(chart_per_inverter_availability(per_inv))
    chart_pr     = _b64_png(chart_per_inverter_pr(per_inv, pr_target))
    chart_wfall  = _b64_png(chart_daily_waterfall(waterfall))

    # ── 3. Logo & cover image ────────────────────────────────────────────────
    logo_b64 = _b64_file(_ROOT / "dolfines_logo_white.png")
    if not logo_b64:
        logo_b64 = _b64_file(_ROOT / "8p2_logo_white.png")  # fallback

    # Cover hero image — try several candidate files
    cover_img_b64 = ""
    for _img in ("bg_solar.jpg", "00orig/solar_farm_2.jpg",
                 "00orig/solar_farm.jpg", "france.jpg"):
        _p = _ROOT / _img
        if _p.exists():
            cover_img_b64 = _b64_file(_p, mime="image/jpeg")
            break

    # ── 4. Alerts table rows ─────────────────────────────────────────────────
    severity_class = {"HIGH": "row-danger", "MEDIUM": "row-warning", "INFO": ""}

    # ── 5. Per-inverter table rows ────────────────────────────────────────────
    inv_rows = []
    for _, row in per_inv.iterrows():
        pr_pct   = row["pr"] * 100
        avail    = row["availability"] * 100
        # Colour-code by PR%: below 70% → red, below target → orange, else → green
        if avail == 0 or pr_pct < 70:
            ok_class = "row-danger"
        elif pr_pct < pr_target * 100:
            ok_class = "row-warning"
        else:
            ok_class = "row-success"
        inv_rows.append({
            "inverter":   row["inverter"],
            "spec_yield": f"{row['spec_yield']:.3f}",
            "energy_kwh": f"{row['energy_kwh']:.1f}",
            "pr_pct":     f"{pr_pct:.1f}%",
            "avail_pct":  f"{avail:.0f}%",
            "peak_kw":    f"{row['peak_kw']:.1f}",
            "row_class":  ok_class,
        })

    # ── 6. Build HTML ────────────────────────────────────────────────────────
    # ── Auto-commentary ──────────────────────────────────────────────────────
    commentary = _build_commentary(site_cfg, site_totals, per_inv, irradiance,
                                   alerts, has_real_inv, has_irr)
    data_quality = _build_data_quality(has_real_inv, has_irr,
                                        site_cfg, results)

    html = _render_html(
        site_cfg       = site_cfg,
        report_date    = report_date,
        logo_b64       = logo_b64,
        cover_img_b64  = cover_img_b64,
        irradiance  = irradiance,
        site_totals = site_totals,
        inv_rows    = inv_rows,
        alerts      = alerts,
        severity_class = severity_class,
        chart_irr   = chart_irr,
        chart_yield = chart_yield,
        chart_avail = chart_avail,
        chart_pr    = chart_pr,
        chart_wfall = chart_wfall,
        waterfall   = waterfall,
        commentary  = commentary,
        data_quality = data_quality,
    )

    # ── 7. Write HTML and convert to PDF ─────────────────────────────────────
    import tempfile as _tmpmod
    out_dir = (Path(out_dir) if out_dir else
               (_ROOT / "_report_test_output" if (_ROOT / "_report_test_output").exists()
                else Path(_tmpmod.gettempdir()) / "pvpat_reports"))
    out_dir.mkdir(parents=True, exist_ok=True)

    date_str  = report_date.strftime("%Y%m%d")
    site_safe = "".join(c if c.isalnum() else "_" for c in site_cfg["display_name"])
    html_path = out_dir / f"PVPAT_Daily_{site_safe}_{date_str}.html"
    pdf_path  = out_dir / f"PVPAT_Daily_{site_safe}_{date_str}.pdf"

    html_path.write_text(html, encoding="utf-8")

    if skip_pdf:
        return None, html_path

    # ── Try WeasyPrint first (renders the HTML faithfully) ───────────────────
    _pdf_rendered = False
    try:
        from weasyprint import HTML as _WP_HTML
        _WP_HTML(string=html, base_url=str(html_path.parent)).write_pdf(str(pdf_path))
        _pdf_rendered = True
    except Exception:
        pass

    # ── Fallback: fpdf2 pure-Python renderer ─────────────────────────────────
    if not _pdf_rendered:
        _fpdf2_pdf(
            pdf_path,
            site_cfg       = site_cfg,
            report_date    = report_date,
            site_totals    = site_totals,
            irradiance     = irradiance,
            per_inv        = per_inv,
            alerts         = alerts,
            chart_irr      = chart_irr,
            chart_yield    = chart_yield,
            chart_avail    = chart_avail,
            chart_pr       = chart_pr,
            chart_wfall    = chart_wfall,
            logo_b64       = logo_b64,
            cover_img_b64  = cover_img_b64,
            commentary     = commentary,
            data_quality   = data_quality,
        )

    return pdf_path, html_path


# ─────────────────────────────────────────────────────────────────────────────
# COMMENTARY & DATA QUALITY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _load_kb_relevant_faults(alerts: list, site_cfg: dict) -> list:
    """Return up to 4 knowledge-base fault entries relevant to detected alerts."""
    import json
    kb_path = _ROOT / "fault_knowledge_base.json"
    if not kb_path.exists():
        return []
    try:
        kb = json.loads(kb_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    # Detect preferred manufacturer from inverter model name
    inv_model = site_cfg.get("inverter_model", "").lower()
    if "sungrow" in inv_model or inv_model.startswith("sg"):
        preferred_mfr = "Sungrow"
    elif "sma" in inv_model or "sunny" in inv_model:
        preferred_mfr = "SMA"
    else:
        preferred_mfr = None

    # Flatten all inverter faults with manufacturer tag
    all_faults: list[dict] = []
    for mfr in kb.get("inverter_manufacturers", []):
        mfr_name = mfr.get("manufacturer", "")
        for fault in mfr.get("faults", []):
            all_faults.append({**fault, "_mfr": mfr_name})
    # Flatten any other top-level fault lists (module_degradation_modes, etc.)
    for key in ("module_degradation_modes", "string_and_combiner_faults",
                "soiling_degradation", "grid_and_curtailment_faults"):
        for fault in kb.get(key, []):
            all_faults.append({**fault, "_mfr": key})

    alert_codes = {a.get("code", "") for a in alerts}

    # Map alert codes → preferred KB fault IDs (Sungrow-first; SMA alternatives included)
    wanted: list[str] = []
    if "OFFLINE" in alert_codes:
        wanted += ["SUN-008", "SUN-003", "SMA-003"]       # AC relay / contactor
    if "LOW_PR" in alert_codes:
        wanted += ["SUN-002", "SUN-010", "SUN-011", "SMA-001"]  # DC insulation, MPPT mismatch
    if "LOW_AVAILABILITY" in alert_codes:
        wanted += ["SUN-001", "SUN-009", "SUN-004", "SMA-002"]  # grid, thermal
    if "BELOW_TARGET_PR" in alert_codes:
        wanted += ["SUN-014", "SUN-005", "SUN-012"]        # curtailment, low-irradiance start, clipping

    # Collect, preferring manufacturer match, deduplicated, max 4
    seen: set[str] = set()
    relevant: list[dict] = []
    # First pass: preferred manufacturer
    for fid in wanted:
        if fid in seen:
            continue
        match = next((f for f in all_faults
                      if f.get("id") == fid and
                      (preferred_mfr is None or f["_mfr"] == preferred_mfr)), None)
        if match:
            relevant.append(match)
            seen.add(fid)
    # Second pass: any manufacturer for missed IDs
    for fid in wanted:
        if fid in seen:
            continue
        match = next((f for f in all_faults if f.get("id") == fid), None)
        if match:
            relevant.append(match)
            seen.add(fid)
        if len(relevant) >= 4:
            break

    return relevant[:4]


def _build_commentary(site_cfg, site_totals, per_inv, irradiance,
                       alerts, has_real_inv, has_irr):
    """Generate automatic interpretive text for the report."""
    import pandas as pd
    lines = []
    pr_target = site_cfg["operating_pr_target"]
    pr_pct    = site_totals["pr_pct"]
    avail_pct = site_totals["availability_pct"]
    energy    = site_totals["total_energy_kwh"]
    delta     = site_totals["energy_delta_kwh"]
    n_inv     = len(per_inv) if not per_inv.empty else 0

    if not has_real_inv:
        lines.append(
            "<strong>Note:</strong> Per-inverter metrics are based on synthetic "
            "demo data — no matching SCADA CSV was found for this date. "
            "Upload real SCADA exports to see actual performance."
        )

    # Overall PR assessment
    if pr_pct >= pr_target * 100 - 1:
        lines.append(
            f"<strong>Overall performance is on target.</strong> "
            f"The site PR of <strong>{pr_pct:.1f}%</strong> is within 1 percentage point "
            f"of the {pr_target*100:.0f}% operating target, indicating normal operation."
        )
    elif pr_pct >= pr_target * 100 - 5:
        lines.append(
            f"<strong>Performance is slightly below target.</strong> "
            f"PR of {pr_pct:.1f}% is {pr_target*100 - pr_pct:.1f} pp below the "
            f"{pr_target*100:.0f}% target. This is within the acceptable variance "
            f"band and may reflect minor soiling or ambient temperature effects."
        )
    else:
        lines.append(
            f"<strong>Performance is significantly below target.</strong> "
            f"PR of {pr_pct:.1f}% is {pr_target*100 - pr_pct:.1f} pp below the "
            f"{pr_target*100:.0f}% target. Immediate investigation is recommended — "
            f"check inverter fault logs and DC string health."
        )

    # Energy delta
    if has_irr:
        if delta < 0:
            lines.append(
                f"The site produced <strong>{abs(delta):,.0f} kWh less</strong> than "
                f"expected at target PR ({site_totals['expected_energy_kwh']:,.0f} kWh expected, "
                f"{energy:,.0f} kWh measured). This shortfall corresponds to "
                f"approximately {abs(delta) / max(energy,1)*100:.1f}% of measured output."
            )
        else:
            lines.append(
                f"The site produced <strong>{delta:,.0f} kWh above</strong> the "
                f"target-PR expectation ({site_totals['expected_energy_kwh']:,.0f} kWh expected, "
                f"{energy:,.0f} kWh measured) — favourable conditions today."
            )

    # Availability commentary
    offline = per_inv[per_inv["availability"] == 0] if not per_inv.empty else pd.DataFrame()
    if not offline.empty:
        names = ", ".join(offline["inverter"].tolist())
        lines.append(
            f"<strong>{len(offline)} inverter(s) were offline for the full day</strong> "
            f"({names}). These units contributed zero energy and require urgent on-site "
            f"inspection or remote restart attempt via the SCADA portal."
        )
    elif avail_pct < 95:
        lines.append(
            f"Fleet availability of {avail_pct:.1f}% indicates some downtime events "
            f"during daylight hours. Review per-inverter fault logs to identify "
            f"the root cause."
        )
    else:
        lines.append(
            f"Fleet availability is <strong>{avail_pct:.1f}%</strong> — all inverters "
            f"operated throughout daylight hours."
        )

    # Irradiance commentary
    if has_irr:
        insol = irradiance["insolation_kwh_m2"]
        peak  = irradiance["peak_ghi"]
        if insol > 5.5:
            lines.append(
                f"Solar resource was strong today: insolation {insol:.2f} kWh/m², "
                f"peak GHI {peak:.0f} W/m². High-irradiance days amplify any "
                f"performance losses — PR deviations are more significant."
            )
        elif insol < 2.0:
            lines.append(
                f"Solar resource was low today (insolation {insol:.2f} kWh/m², "
                f"peak GHI {peak:.0f} W/m²). Low-irradiance days can produce "
                f"higher measurement uncertainty in PR calculations."
            )
        else:
            lines.append(
                f"Solar resource was moderate: insolation {insol:.2f} kWh/m², "
                f"peak GHI {peak:.0f} W/m²."
            )
    else:
        lines.append(
            "No irradiance sensor data is available for this date. "
            "PR and energy loss figures are estimated using a satellite irradiance "
            "fallback — actual deviations may differ."
        )

    # High alerts summary
    high_alerts = [a for a in alerts if a["severity"] == "HIGH"]
    if high_alerts:
        lines.append(
            f"<strong>{len(high_alerts)} HIGH-severity alert(s)</strong> require "
            f"immediate attention. Refer to the Alerts &amp; Alarms section for "
            f"recommended corrective actions."
        )

    # Knowledge base diagnostic insights
    kb_faults = _load_kb_relevant_faults(alerts, site_cfg)
    if kb_faults:
        sub_items = ""
        for f in kb_faults:
            mfr   = f.get("_mfr", "")
            fid   = f.get("id", "")
            fname = f.get("name", "")
            cats  = f.get("root_causes", [])[:2]
            acts  = f.get("actions", [])[:2]
            causes_str  = "; ".join(cats) if cats else "—"
            actions_str = "; ".join(acts) if acts else "—"
            sev   = f.get("severity", "")
            sub_items += (
                f"<li style='margin-bottom:4px;'>"
                f"<em style='color:#003D6B;'>[{fid} · {mfr} · {fname}]</em> "
                f"<span style='color:#888;font-size:7pt;'>({sev})</span> — "
                f"<strong>Typical causes:</strong> {causes_str}. "
                f"<strong>Recommended actions:</strong> {actions_str}."
                f"</li>"
            )
        lines.append(
            f"<strong>Knowledge Base — Diagnostic Guidance:</strong> "
            f"Based on the alerts detected, the following known fault patterns are relevant:"
            f"<ul style='margin-top:4px;margin-bottom:0;padding-left:18px;'>{sub_items}</ul>"
        )

    return lines


def _build_data_quality(has_real_inv, has_irr, site_cfg, results):
    """Build analysis capability table rows."""
    rows = []
    inv_status  = ("✓ Available", "#2E8B57") if has_real_inv else ("⚠ Demo data used", "#E67E22")
    irr_status  = ("✓ Available", "#2E8B57") if has_irr    else ("✗ Not found",       "#C0392B")
    rows.append(("Per-inverter power data",  inv_status, inv_status[1],
                  "Energy, PR, specific yield per inverter",
                  "SCADA CSV with EQUIP + PAC columns" if not has_real_inv else "—"))
    rows.append(("Irradiance / GHI data",    irr_status, irr_status[1],
                  "Insolation, PR calculation, waterfall losses",
                  "Pyranometer CSV with GHI column" if not has_irr else "—"))
    rows.append(("Performance Ratio",
                  ("✓ Calculated", "#2E8B57") if has_irr and has_real_inv else ("⚠ Estimated", "#E67E22"),
                  "#2E8B57" if has_irr and has_real_inv else "#E67E22",
                  "Core KPI — energy quality metric", "—"))
    rows.append(("Availability analysis",
                  ("✓ Calculated", "#2E8B57") if has_real_inv else ("⚠ Demo data", "#E67E22"),
                  "#2E8B57" if has_real_inv else "#E67E22",
                  "Fraction of daylight hours producing power", "—"))
    rows.append(("Energy loss waterfall",
                  ("✓ Calculated", "#2E8B57") if has_irr else ("⚠ Estimated", "#E67E22"),
                  "#2E8B57" if has_irr else "#E67E22",
                  "Loss decomposition: optical, inverter, downtime",
                  "Irradiance data needed for accurate losses" if not has_irr else "—"))
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# HTML RENDERER
# ─────────────────────────────────────────────────────────────────────────────

def _render_html(*, site_cfg, report_date, logo_b64, cover_img_b64="", irradiance, site_totals,
                 inv_rows, alerts, severity_class, chart_irr, chart_yield,
                 chart_avail, chart_pr, chart_wfall, waterfall,
                 commentary=None, data_quality=None) -> str:
    """Inline HTML/CSS – no Jinja dependency for the daily report."""

    site_name   = site_cfg["display_name"]
    date_str    = report_date.strftime("%d %B %Y")
    gen_dt      = datetime.now().strftime("%d/%m/%Y %H:%M")
    pr_target   = site_cfg["operating_pr_target"]
    cap_dc      = site_cfg["cap_dc_kwp"]
    cap_ac      = site_cfg["cap_ac_kw"]

    # ── KPI status-class helpers ─────────────────────────────────────────────
    def pr_status(pr_pct):
        if pr_pct >= pr_target * 100 - 2:
            return "status-success"
        elif pr_pct >= pr_target * 100 - 8:
            return "status-warning"
        return "status-danger"

    def avail_status(avail_pct):
        if avail_pct >= 95:
            return "status-success"
        elif avail_pct >= 85:
            return "status-warning"
        return "status-danger"

    # ── Pre-compute counts ────────────────────────────────────────────────────
    high_count   = sum(1 for a in alerts if a["severity"] == "HIGH")
    medium_count = sum(1 for a in alerts if a["severity"] == "MEDIUM")
    alert_summary = (f"{high_count} HIGH · {medium_count} MEDIUM"
                     if (high_count or medium_count) else "None")
    alerts_status = ("status-danger" if high_count
                     else "status-warning" if medium_count
                     else "status-success")
    delta_status  = ("status-success"
                     if site_totals["energy_delta_kwh"] >= 0
                     else "status-danger")
    delta_sign    = "+" if site_totals["energy_delta_kwh"] >= 0 else ""

    # ── Logo ──────────────────────────────────────────────────────────────────
    logo_img = (f'<img src="{logo_b64}" alt="Dolfines" />'
                if logo_b64 else "")

    # ── CSS (plain string – no f-string so CSS braces need no escaping) ───────
    css = """
:root {
  --c-pri:  #003D6B;
  --c-acc:  #F07820;
  --c-sec:  #3E516C;
  --c-txt:  #1F2933;
  --c-mut:  #6B7785;
  --c-bg:   #F4F6F8;
  --c-bdr:  #D9E0E6;
  --c-ok:   #70AD47;
  --c-warn: #C98A00;
  --c-err:  #C62828;
}
:root { color-scheme: light; }
* { box-sizing: border-box; margin: 0; padding: 0;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 9pt;
       color: #1F2933 !important; -webkit-text-fill-color: #1F2933 !important;
       background: #fff; }
@page { size: A4; margin: 0; }
.page { min-height: 297mm; background: #fff; page-break-after: always;
        overflow: hidden; }
.page:last-child { page-break-after: auto; }

/* ── Header ── */
.header-shell { }
.header-band {
  background: #003D6B; display: flex; align-items: center;
  justify-content: space-between; padding: 4mm 10mm;
}
.header-band img { max-height: 20mm; width: auto; }
.header-copy { text-align: right; }
.header-site { font-size: 11pt; font-weight: 700; color: #fff;
               letter-spacing: .05em; text-transform: uppercase; }
.header-company { font-size: 8pt; color: rgba(255,255,255,.70); margin-top: 2px; }
.header-accent {
  height: 4px; background: #F07820; position: relative; overflow: hidden;
}
.header-accent::after {
  content: ''; position: absolute; right: 0; top: 0;
  border-top: 4px solid #003D6B; border-left: 18px solid transparent;
}

/* ── Cover ── */
.cover-page { min-height: 297mm; background: #fff;
              page-break-after: always; overflow: hidden; }
.cover-band {
  background: #003D6B; display: flex; align-items: center;
  justify-content: space-between; padding: 4mm 10mm;
}
.cover-band img { max-height: 20mm; width: auto; }
.cover-logo { max-height: 20mm; width: auto; }
.cover-accent {
  height: 4px; background: #F07820; position: relative; overflow: hidden;
}
.cover-accent::after {
  content: ''; position: absolute; right: 0; top: 0;
  border-top: 4px solid #003D6B; border-left: 18px solid transparent;
}
.cover-body { padding: 8mm 10mm 10mm; }
.cover-hero { width: 100%; height: 90mm; border-radius: 10px; overflow: hidden;
              border: 1px solid #D9E0E6; margin-bottom: 8mm;
              background: linear-gradient(135deg, rgba(0,61,107,0.14), rgba(62,81,108,0.08)); }
.cover-hero img { width: 100%; height: 100%; object-fit: cover; display: block; }
.cover-panel {
  border: 2.5px solid #F07820; border-radius: 10px; padding: 7mm 8mm;
}
.cover-panel h1 { font-size: 18pt; font-weight: 700; color: #003D6B;
                  margin-bottom: 4px; }
.cover-subtitle { font-size: 10pt; color: #6B7785; margin-bottom: 6mm; }
.cover-metadata { display: grid; grid-template-columns: 1fr 1fr; gap: 2mm 6mm;
                  font-size: 8.5pt; }
.cover-metadata dt { color: #6B7785; font-weight: 600; text-transform: uppercase;
                     font-size: 7pt; letter-spacing: .06em; }
.cover-metadata dd { color: #1F2933; font-weight: 600; margin-top: 1px; }

/* ── Page content ── */
.page-content { padding: 0 10mm 8mm; }

/* ── Section heading ── */
.section-heading { margin-bottom: 3mm; }
.section-heading h2 { font-size: 14pt; font-weight: 700; color: #003D6B;
                      margin-bottom: 2px; }
.section-summary { font-size: 9pt; color: #6B7785; }
.eyebrow { text-transform: uppercase; letter-spacing: .12em; font-size: 7.5pt;
           color: #3E516C; margin-bottom: 3px; }

/* ── KPI cards ── */
.kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr);
            gap: 2.5mm; margin-bottom: 3mm; }
.kpi-grid.g3 { grid-template-columns: repeat(3, 1fr); }
.kpi-card { background: #F4F6F8; padding: 2.5mm 3mm;
            border: 1px solid #D9E0E6; border-radius: 8px; }
.kpi-label { font-size: 7pt; text-transform: uppercase; letter-spacing: .04em;
             color: #6B7785; font-weight: 600; margin-bottom: 2px; }
.kpi-value { font-size: 15pt; font-weight: 700; color: #003D6B;
             line-height: 1.1; }
.kpi-subtext, .kpi-target { font-size: 7pt; color: #6B7785; margin-top: 1px; }
.status-success .kpi-value { color: #70AD47; }
.status-warning .kpi-value { color: #C98A00; }
.status-danger  .kpi-value { color: #C62828; }
.status-info    .kpi-value { color: #3E516C; }

/* ── Commentary card ── */
.commentary-card {
  background: linear-gradient(180deg, #fbfcfd, #f6f8fa);
  border: 1px solid #D9E0E6; border-left: 3px solid #F07820;
  padding: 3mm 3.5mm; margin-bottom: 3mm;
  border-radius: 8px; break-inside: avoid;
}
.commentary-card h3 { font-size: 9.5pt; font-weight: 700; color: #003D6B;
                       margin-bottom: 3px; }
.commentary-card p { font-size: 8.5pt; color: #1F2933; line-height: 1.5;
                     margin-top: 3px; }

/* ── Figure cards ── */
.figure-grid { display: grid; grid-template-columns: repeat(2, 1fr);
               gap: 2.5mm; margin-bottom: 3mm; }
.figure-card { border: 1px solid #D9E0E6; border-radius: 8px;
               padding: 2.5mm; break-inside: avoid; }
.figure-card img { width: 100%; height: auto; max-height: 86mm;
                   object-fit: contain; display: block; }
.figure-card.full { grid-column: 1 / -1; }
.figure-card.full img { max-height: 112mm; }
.figure-card.half img { max-height: 72mm; }
figcaption { font-size: 7.5pt; color: #6B7785; margin-top: 4px; }

/* ── Table card ── */
.table-card { border: 1px solid #D9E0E6; border-radius: 8px;
              padding: 2.8mm; break-inside: avoid; margin-bottom: 3mm; }
.table-card-header { margin-bottom: 2.5mm; }
.table-card-header h3 { font-size: 10pt; font-weight: 700; color: #003D6B; }
.report-table { width: 100%; border-collapse: collapse; }
.report-table th,
.report-table td { border-top: 1px solid #D9E0E6; padding: 4px 5px;
                   font-size: 7.8pt; text-align: left; vertical-align: top; }
.report-table thead th { background: #F4F6F8; color: #003D6B;
                          font-weight: 700; border-top: none; }
.row-danger td  { background: #fdecea; }
.row-warning td { background: #fff5e6; }
.row-success td { background: #edf7e9; }

/* ── Findings card ── */
.findings-card { border: 1px solid #D9E0E6; border-radius: 8px;
                 padding: 2.8mm; margin-bottom: 3mm; }
.findings-list { display: grid; gap: 2.5mm; margin-top: 2.5mm; }
.finding { border-left: 3px solid #D9E0E6;
           padding: 1.5mm 0 1.5mm 2.5mm; }
.finding-danger  { border-left-color: #C62828; }
.finding-warning { border-left-color: #C98A00; }
.finding-info    { border-left-color: #3E516C; }
.finding h4 { font-size: 8.5pt; font-weight: 700; color: #1F2933;
              margin-bottom: 2px; }
.finding p  { font-size: 8pt; color: #1F2933; line-height: 1.45; }

/* ── Two-column layout ── */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 3mm; }

/* ── Footer ── */
.page-footer {
  border-top: 1px solid #D9E0E6; padding: 3mm 0 0;
  display: flex; justify-content: space-between;
  font-size: 7pt; color: #6B7785; margin-top: 4mm;
}
"""

    # ── Shared header / footer builders ──────────────────────────────────────
    def page_header(sub: str) -> str:
        return f"""<div class="header-shell">
  <div class="header-band">
    {logo_img}
    <div class="header-copy">
      <p class="header-site">{site_name}</p>
      <p class="header-company">Daily Performance Report · {date_str}</p>
    </div>
  </div>
  <div class="header-accent"></div>
</div>"""

    def page_footer(n: int, total: int = 6) -> str:
        return f"""<div class="page-footer">
  <span>PVPAT — Daily Performance Report · {site_name}</span>
  <span>CONFIDENTIAL — Dolfines</span>
  <span>Page {n} of {total}</span>
</div>"""

    # ── PAGE 1: COVER ─────────────────────────────────────────────────────────
    p1 = f"""<section class="page cover-page">
  <div class="cover-band">
    {logo_img}
    <div class="header-copy">
      <p class="header-site">{site_name}</p>
      <p class="header-company">Dolfines</p>
    </div>
  </div>
  <div class="cover-accent"></div>
  <div class="cover-body">
    {f'<div class="cover-hero"><img src="{cover_img_b64}" alt="Solar farm" /></div>' if cover_img_b64 else ''}
    <div class="cover-panel">
      <p class="eyebrow">Daily Performance Report</p>
      <h1>{site_name} — Daily Performance Report</h1>
      <p class="cover-subtitle">Automated SCADA-based daily performance analysis</p>
      <dl class="cover-metadata">
        <div><dt>Report date</dt><dd>{date_str}</dd></div>
        <div><dt>Asset</dt><dd>{cap_dc:.0f} kWp DC / {cap_ac:.0f} kW AC</dd></div>
        <div><dt>Technology</dt><dd>{site_cfg.get('technology', '—')}</dd></div>
        <div><dt>Inverters</dt><dd>{site_cfg.get('n_inverters', '—')} × {site_cfg.get('inverter_model', '—')}</dd></div>
        <div><dt>Generated</dt><dd>{gen_dt}</dd></div>
      </dl>
    </div>
  </div>
</section>"""

    # ── PAGE 2: DAILY KPIs + IRRADIANCE ──────────────────────────────────────
    pr_cls    = pr_status(site_totals["pr_pct"])
    avail_cls = avail_status(site_totals["availability_pct"])

    p2 = f"""<section class="page standard-page page-daily-kpis">
  {page_header("Daily Summary")}
  <div class="page-content">
    <div class="section-heading" style="margin-top:3mm;">
      <p class="eyebrow">Daily Summary</p>
      <h2>Daily Key Performance Indicators</h2>
      <p class="section-summary">Site-level KPIs for {date_str}.</p>
    </div>

    <div class="kpi-grid">
      <article class="kpi-card status-info">
        <p class="kpi-label">Total Energy</p>
        <p class="kpi-value">{site_totals["total_energy_kwh"]:,.0f}</p>
        <p class="kpi-subtext">kWh</p>
      </article>
      <article class="kpi-card status-info">
        <p class="kpi-label">Specific Yield</p>
        <p class="kpi-value">{site_totals["spec_yield"]:.3f}</p>
        <p class="kpi-subtext">kWh/kWp</p>
      </article>
      <article class="kpi-card {pr_cls}">
        <p class="kpi-label">Performance Ratio</p>
        <p class="kpi-value">{site_totals["pr_pct"]:.1f}%</p>
        <p class="kpi-subtext">Target {site_totals["pr_target_pct"]:.0f}%</p>
      </article>
      <article class="kpi-card {avail_cls}">
        <p class="kpi-label">Fleet Availability</p>
        <p class="kpi-value">{site_totals["availability_pct"]:.1f}%</p>
        <p class="kpi-subtext">daylight hours</p>
      </article>
      <article class="kpi-card {alerts_status}">
        <p class="kpi-label">Alerts</p>
        <p class="kpi-value" style="font-size:11pt;">{alert_summary}</p>
        <p class="kpi-subtext">today</p>
      </article>
    </div>

    <div class="kpi-grid g3">
      <article class="kpi-card status-info">
        <p class="kpi-label">Insolation</p>
        <p class="kpi-value">{irradiance["insolation_kwh_m2"]:.2f}</p>
        <p class="kpi-subtext">kWh/m²</p>
      </article>
      <article class="kpi-card status-info">
        <p class="kpi-label">Peak GHI</p>
        <p class="kpi-value">{irradiance["peak_ghi"]:.0f}</p>
        <p class="kpi-subtext">W/m²</p>
      </article>
      <article class="kpi-card {delta_status}">
        <p class="kpi-label">Energy vs Expected</p>
        <p class="kpi-value">{delta_sign}{site_totals["energy_delta_kwh"]:,.0f}</p>
        <p class="kpi-subtext">kWh vs target PR</p>
      </article>
    </div>

    <section class="commentary-card">
      <h3>Daily Overview</h3>
      <p>Performance summary for {site_name} on {date_str}. The site recorded a
      performance ratio of {site_totals["pr_pct"]:.1f}% against a target of
      {site_totals["pr_target_pct"]:.0f}%, fleet availability of
      {site_totals["availability_pct"]:.1f}%, and total AC energy output of
      {site_totals["total_energy_kwh"]:,.0f} kWh from
      {irradiance["insolation_kwh_m2"]:.2f} kWh/m² insolation.</p>
    </section>

    <div class="figure-grid">
      <figure class="figure-card full">
        <img src="{chart_irr}" alt="Irradiance profile" />
        <figcaption>Figure 1 — Daily GHI irradiance profile (W/m²) with AC power overlay.</figcaption>
      </figure>
    </div>

    {page_footer(2)}
  </div>
</section>"""

    # ── PAGE 3: PER-INVERTER YIELD & PR ──────────────────────────────────────
    inv_table_rows = ""
    for r in inv_rows:
        row_cls = r.get("row_class", "")
        inv_table_rows += f"""<tr class="{row_cls}">
          <td style="font-weight:600;">{r["inverter"]}</td>
          <td style="text-align:right;">{r["spec_yield"]}</td>
          <td style="text-align:right;">{r["energy_kwh"]}</td>
          <td style="text-align:right;">{r["pr_pct"]}</td>
          <td style="text-align:right;">{r["avail_pct"]}</td>
          <td style="text-align:right;">{r["peak_kw"]}</td>
        </tr>"""

    p3 = f"""<section class="page standard-page page-inverter-yield">
  {page_header("Per-Inverter Analysis")}
  <div class="page-content">
    <div class="section-heading" style="margin-top:3mm;">
      <p class="eyebrow">Per-Inverter Analysis</p>
      <h2>Specific Yield &amp; Performance Ratio</h2>
      <p class="section-summary">Inverter-level yield and PR breakdown for {date_str}.</p>
    </div>

    <section class="table-card">
      <div class="table-card-header">
        <h3>Inverter Summary Table</h3>
      </div>
      <table class="report-table">
        <thead>
          <tr>
            <th>Inverter</th>
            <th style="text-align:right;">Spec. Yield (kWh/kWp)</th>
            <th style="text-align:right;">Energy (kWh)</th>
            <th style="text-align:right;">PR (%)</th>
            <th style="text-align:right;">Availability</th>
            <th style="text-align:right;">Peak (kW)</th>
          </tr>
        </thead>
        <tbody>{inv_table_rows}</tbody>
      </table>
    </section>

    <div class="figure-grid">
      <figure class="figure-card half">
        <img src="{chart_yield}" alt="Specific yield per inverter" />
        <figcaption>Figure 2 — Specific yield (kWh/kWp) per inverter.</figcaption>
      </figure>
      <figure class="figure-card half">
        <img src="{chart_pr}" alt="Performance ratio per inverter" />
        <figcaption>Figure 3 — Performance ratio (%) per inverter vs fleet target.</figcaption>
      </figure>
    </div>

    {page_footer(3)}
  </div>
</section>"""

    # ── PAGE 4: AVAILABILITY ──────────────────────────────────────────────────
    p4 = f"""<section class="page standard-page page-availability">
  {page_header("Per-Inverter Availability")}
  <div class="page-content">
    <div class="section-heading" style="margin-top:3mm;">
      <p class="eyebrow">Availability Analysis</p>
      <h2>Per-Inverter Availability</h2>
      <p class="section-summary">Fraction of daylight intervals each inverter was operational.</p>
    </div>

    <section class="commentary-card">
      <h3>Availability Methodology</h3>
      <p>Availability is computed as the fraction of 10-minute intervals during daylight hours
      (GHI &gt; {site_cfg["irr_threshold"]:.0f} W/m²) where measured AC power exceeded the
      {site_cfg["power_threshold"]:.0f} kW detection threshold. Inverters with zero availability
      were offline for the full day and require immediate investigation.</p>
    </section>

    <div class="figure-grid">
      <figure class="figure-card full">
        <img src="{chart_avail}" alt="Inverter availability chart" />
        <figcaption>Figure 4 — Per-inverter availability (%) during daylight hours.</figcaption>
      </figure>
    </div>

    {page_footer(4)}
  </div>
</section>"""

    # ── PAGE 5: WATERFALL + ALERTS ────────────────────────────────────────────
    if alerts:
        findings_items = ""
        for a in alerts:
            sev = a["severity"]
            finding_cls = ("finding-danger"  if sev == "HIGH"
                           else "finding-warning" if sev == "MEDIUM"
                           else "finding-info")
            findings_items += f"""<article class="finding {finding_cls}">
          <h4>{a["inverter"]} — {a["description"]}</h4>
          <p><strong>Likely cause:</strong> {a["likely_cause"]}. <strong>Action:</strong> {a["recommended_action"]}.</p>
        </article>"""
        alerts_block = f"""<section class="findings-card">
      <div class="table-card-header"><h3>Alerts &amp; Alarms</h3></div>
      <div class="findings-list">
        {findings_items}
      </div>
    </section>"""
    else:
        alerts_block = """<section class="commentary-card">
      <h3>Alerts &amp; Alarms</h3>
      <p>No alerts detected for this reporting period. All inverters operated within expected parameters.</p>
    </section>"""

    p5 = f"""<section class="page standard-page page-waterfall">
  {page_header("Energy Losses")}
  <div class="page-content">
    <div class="section-heading" style="margin-top:3mm;">
      <p class="eyebrow">Energy Losses</p>
      <h2>Daily Energy Loss Waterfall</h2>
      <p class="section-summary">Decomposition of theoretical energy into successive loss categories.</p>
    </div>

    <section class="commentary-card">
      <h3>Waterfall Interpretation</h3>
      <p>The waterfall decomposes the theoretical energy (GHI × DC capacity) into successive
      loss categories down to the measured AC output. Curtailment &amp; downtime represents
      residual losses beyond the design optical/thermal budget.</p>
    </section>

    <div class="figure-grid">
      <figure class="figure-card full">
        <img src="{chart_wfall}" alt="Energy loss waterfall" />
        <figcaption>Figure 5 — Daily energy loss waterfall (kWh).</figcaption>
      </figure>
    </div>

    {alerts_block}

    {page_footer(5)}
  </div>
</section>"""

    # ── PAGE 6: COMMENTARY + DATA QUALITY ─────────────────────────────────────
    if commentary:
        commentary_paras = "".join(f"<p>{c}</p>" for c in commentary)
        commentary_block = f"""<section class="commentary-card">
      <h3>Automated Interpretation</h3>
      {commentary_paras}
    </section>"""
    else:
        commentary_block = """<section class="commentary-card">
      <h3>Automated Interpretation</h3>
      <p>No automated commentary available for this reporting period.</p>
    </section>"""

    if data_quality:
        dq_rows_html = ""
        for row in data_quality:
            analysis, (status_text, status_color), _, impact, remedy = row
            dq_rows_html += f"""<tr>
          <td>{analysis}</td>
          <td style="font-weight:700;color:{status_color};">{status_text}</td>
          <td>{impact}</td>
          <td>{remedy}</td>
        </tr>"""
        dq_block = f"""<section class="table-card">
      <div class="table-card-header">
        <h3>Analysis Capability Summary</h3>
      </div>
      <table class="report-table">
        <thead>
          <tr>
            <th>Analysis</th>
            <th>Status</th>
            <th>Impact on Report</th>
            <th>To Unlock</th>
          </tr>
        </thead>
        <tbody>{dq_rows_html}</tbody>
      </table>
    </section>"""
    else:
        dq_block = ""

    p6 = f"""<section class="page standard-page page-commentary">
  {page_header("Interpretation")}
  <div class="page-content">
    <div class="section-heading" style="margin-top:3mm;">
      <p class="eyebrow">Interpretation</p>
      <h2>Commentary &amp; Analysis Capability</h2>
      <p class="section-summary">Automated interpretation and data quality assessment.</p>
    </div>

    {commentary_block}

    {dq_block}

    {page_footer(6)}
  </div>
</section>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>PVPAT Daily Report — {site_name} — {date_str}</title>
  <style>{css}</style>
</head>
<body>
{p1}
{p2}
{p3}
{p4}
{p5}
{p6}
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# WEASYPRINT PDF CONVERSION
# ─────────────────────────────────────────────────────────────────────────────

def _playwright_pdf(html_path: Path, pdf_path: Path) -> None:
    """Generate PDF — delegates to the same function used by the comprehensive report."""
    # Ensure Chromium binary is present for the current user
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=True, text=True, timeout=180,
    )
    from report.render_report import render_pdf_with_playwright
    render_pdf_with_playwright(html_path=html_path, pdf_path=pdf_path)


# ─────────────────────────────────────────────────────────────────────────────
# FPDF2 PDF GENERATION (pure-Python, no Chromium)
# ─────────────────────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    """Remove HTML tags, decode entities, and strip non-latin1 chars for fpdf2."""
    import re, html as _html
    text = re.sub(r"<[^>]+>", " ", text)
    text = _html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return _latin1(text)


def _latin1(text: str) -> str:
    """Replace common Unicode chars with latin-1 equivalents for Helvetica font."""
    _MAP = {
        "\u2014": "--", "\u2013": "-",  "\u00b7": ".",
        "\u00d7": "x",  "\u00b2": "2",  "\u00b0": "deg",
        "\u2019": "'",  "\u2018": "'",  "\u201c": '"', "\u201d": '"',
        "\u2022": "-",  "\u2026": "...",
        "\u2713": "OK", "\u2714": "OK", "\u2717": "X", "\u2718": "X",
        "\u26a0": "(!)", "\u2713": "OK", "\u2192": "->",
        "\u00e9": "e",  "\u00e8": "e",  "\u00ea": "e",
    }
    for ch, rep in _MAP.items():
        text = text.replace(ch, rep)
    # Drop any remaining non-latin1 chars
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _fpdf2_pdf(
    pdf_path: Path,
    *,
    site_cfg: dict,
    report_date,
    site_totals: dict,
    irradiance: dict,
    per_inv,
    alerts: list,
    chart_irr: str,
    chart_yield: str,
    chart_avail: str,
    chart_pr: str,
    chart_wfall: str,
    logo_b64: str,
    cover_img_b64: str = "",
    commentary: list = None,
    data_quality: list = None,
) -> None:
    import io
    from fpdf import FPDF

    # ── Colours ───────────────────────────────────────────────────────────────
    NAVY   = ( 11,  42,  61)   # #0B2A3D
    ORANGE = (243, 146,   0)   # #F39200
    LGRAY  = (244, 246, 248)
    DTXT   = ( 31,  41,  51)
    MGRAY  = (107, 119, 133)
    GREEN  = ( 70, 173,  71)
    RED    = (198,  40,  40)
    AMBER  = (201, 138,   0)
    WHITE  = (255, 255, 255)
    BDRG   = (217, 224, 230)

    pr_target = site_cfg["operating_pr_target"]
    site_name = _latin1(site_cfg["display_name"])
    date_str  = _latin1(report_date.strftime("%d %B %Y"))
    gen_dt    = datetime.now().strftime("%d/%m/%Y %H:%M")

    # ── Decode helpers ────────────────────────────────────────────────────────
    def chart_bytes(b64_uri: str) -> io.BytesIO | None:
        if not b64_uri:
            return None
        try:
            raw = base64.b64decode(b64_uri.split(",", 1)[1])
            return io.BytesIO(raw)
        except Exception:
            return None

    def logo_bytes() -> io.BytesIO | None:
        if not logo_b64:
            return None
        try:
            raw = base64.b64decode(logo_b64.split(",", 1)[1])
            return io.BytesIO(raw)
        except Exception:
            return None

    def pr_color(pct):
        if pct >= pr_target * 100 - 2:  return GREEN
        if pct >= pr_target * 100 - 8:  return AMBER
        return RED

    def avail_color(pct):
        if pct >= 95: return GREEN
        if pct >= 85: return AMBER
        return RED

    # ── PDF object ────────────────────────────────────────────────────────────
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.set_margins(0, 0, 0)

    PAGE_W, PAGE_H = 210, 297

    # ── Shared: header band (navy + logo + site name + orange stripe) ─────────
    def draw_header():
        pdf.set_fill_color(*NAVY)
        pdf.rect(0, 0, PAGE_W, 18, "F")
        lb = logo_bytes()
        if lb:
            try:
                pdf.image(lb, x=5, y=2, h=14)
            except Exception:
                pass
        pdf.set_xy(10, 4)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*WHITE)
        pdf.cell(PAGE_W - 15, 6, site_name, align="R")
        pdf.set_xy(10, 11)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(200, 220, 240)
        pdf.cell(PAGE_W - 15, 5, f"Daily Performance Report - {date_str}", align="R")
        pdf.set_fill_color(*ORANGE)
        pdf.rect(0, 18, PAGE_W, 1.5, "F")
        pdf.set_text_color(*DTXT)

    # ── Shared: footer ────────────────────────────────────────────────────────
    def draw_footer(n: int, total: int = 6):
        pdf.set_xy(10, PAGE_H - 10)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*MGRAY)
        pdf.cell(63, 5, f"PVPAT -- Daily Performance Report - {site_name}", align="L")
        pdf.cell(64, 5, "CONFIDENTIAL -- Dolfines", align="C")
        pdf.cell(63, 5, f"Page {n} of {total}", align="R")

    # ── Shared: section heading ───────────────────────────────────────────────
    def section_heading(eyebrow: str, title: str, sub: str = "", y: float = 22):
        pdf.set_xy(10, y)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*MGRAY)
        pdf.cell(0, 4, eyebrow.upper())
        pdf.set_xy(10, y + 5)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 7, title)
        if sub:
            pdf.set_xy(10, y + 13)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*MGRAY)
            pdf.cell(0, 5, sub)

    # ── Shared: KPI card (used for secondary row) ─────────────────────────────
    def kpi_card(x, y, w, h, label, value, sub, val_color=NAVY):
        pdf.set_fill_color(*LGRAY)
        pdf.rect(x, y, w, h, "F")
        pdf.set_draw_color(*BDRG)
        pdf.rect(x, y, w, h)
        pdf.set_xy(x + 2, y + 2)
        pdf.set_font("Helvetica", "B", 6)
        pdf.set_text_color(*MGRAY)
        pdf.cell(w - 4, 4, label.upper())
        pdf.set_xy(x + 2, y + 7)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*val_color)
        pdf.cell(w - 4, 6, str(value))
        pdf.set_xy(x + 2, y + 14)
        pdf.set_font("Helvetica", "", 6)
        pdf.set_text_color(*MGRAY)
        pdf.cell(w - 4, 4, str(sub))

    # ── Orange KPI banner (primary KPIs, white text on orange) ───────────────
    CREAM = (255, 230, 170)  # label tint inside orange banner

    def kpi_banner(x, y, w, h, kpis):
        """Draw a single orange banner containing multiple KPI slots."""
        pdf.set_fill_color(*ORANGE)
        pdf.rect(x, y, w, h, "F")
        slot_w = w / len(kpis)
        for i, (label, value, sub) in enumerate(kpis):
            sx = x + i * slot_w
            # divider
            if i > 0:
                pdf.set_draw_color(*WHITE)
                pdf.set_line_width(0.2)
                pdf.line(sx, y + 4, sx, y + h - 4)
                pdf.set_line_width(0.2)
            # label
            pdf.set_xy(sx, y + 3)
            pdf.set_font("Helvetica", "B", 6)
            pdf.set_text_color(*CREAM)
            pdf.cell(slot_w, 4, label.upper(), align="C")
            # value
            pdf.set_xy(sx, y + 8)
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(*WHITE)
            pdf.cell(slot_w, 8, str(value), align="C")
            # sub
            pdf.set_xy(sx, y + 17)
            pdf.set_font("Helvetica", "", 6)
            pdf.set_text_color(*CREAM)
            pdf.cell(slot_w, 4, str(sub), align="C")

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 1 — COVER
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, PAGE_W, 22, "F")
    lb = logo_bytes()
    if lb:
        try:
            pdf.image(lb, x=5, y=3, h=16)
        except Exception:
            pass
    pdf.set_xy(10, 5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*WHITE)
    pdf.cell(PAGE_W - 15, 7, "Dolfines", align="R")
    pdf.set_xy(10, 13)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(200, 220, 240)
    pdf.cell(PAGE_W - 15, 5, site_name, align="R")
    pdf.set_fill_color(*ORANGE)
    pdf.rect(0, 22, PAGE_W, 2, "F")

    # Hero image (solar farm photo)
    hero_y = 26
    if cover_img_b64:
        try:
            hero_bytes = base64.b64decode(cover_img_b64.split(",", 1)[1])
            pdf.image(io.BytesIO(hero_bytes), x=10, y=hero_y, w=190, h=65)
        except Exception:
            pass
        text_y = hero_y + 68
    else:
        text_y = hero_y + 8

    pdf.set_xy(10, text_y)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*MGRAY)
    pdf.cell(0, 5, "DAILY PERFORMANCE REPORT")
    pdf.set_xy(10, text_y + 7)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*NAVY)
    pdf.multi_cell(190, 10, site_name)
    pdf.set_xy(10, pdf.get_y() + 1)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*MGRAY)
    pdf.cell(0, 5, "Automated SCADA-based daily performance analysis")

    # Orange border box for metadata
    box_y = pdf.get_y() + 8
    box_h = 75
    pdf.set_draw_color(*ORANGE)
    pdf.set_line_width(0.8)
    pdf.rect(10, box_y, 190, box_h)
    pdf.set_line_width(0.2)

    meta = [
        ("Report Date",  date_str),
        ("Asset",        f"{site_cfg['cap_dc_kwp']:.0f} kWp DC / {site_cfg['cap_ac_kw']:.0f} kW AC"),
        ("Technology",   site_cfg.get("technology", "-")),
        ("Inverters",    f"{site_cfg.get('n_inverters','-')} x {site_cfg.get('inverter_model','-')}"),
        ("Generated",    gen_dt),
    ]
    for i, (lbl, val) in enumerate(meta):
        col = i % 2
        row = i // 2
        mx = 18 + col * 97
        my = box_y + 8 + row * 22
        pdf.set_xy(mx, my)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*MGRAY)
        pdf.cell(90, 4, lbl.upper())
        pdf.set_xy(mx, my + 5)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*NAVY)
        pdf.cell(90, 6, _latin1(val))

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 2 — DAILY KPIs + IRRADIANCE CHART
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    draw_header()
    section_heading("Daily Summary", "Daily Key Performance Indicators",
                    f"Site-level KPIs for {date_str}.", y=22)

    high_c = sum(1 for a in alerts if a["severity"] == "HIGH")
    med_c  = sum(1 for a in alerts if a["severity"] == "MEDIUM")
    alert_txt = f"{high_c}H / {med_c}M" if (high_c or med_c) else "None"
    alert_col = RED if high_c else AMBER if med_c else GREEN

    # Primary KPI banner (orange, white text)
    kpis5 = [
        ("Total Energy",   f"{site_totals['total_energy_kwh']:,.0f} kWh",  "production today"),
        ("Specific Yield", f"{site_totals['spec_yield']:.3f}",             "kWh/kWp"),
        ("Perf. Ratio",    f"{site_totals['pr_pct']:.1f}%",               f"Target {site_totals['pr_target_pct']:.0f}%"),
        ("Fleet Avail.",   f"{site_totals['availability_pct']:.1f}%",      "daylight hours"),
        ("Alerts",         alert_txt,                                       "today"),
    ]
    kpi_banner(10, 40, 190, 26, kpis5)

    # Secondary row: irradiance + energy delta (navy cards)
    kpis3 = [
        ("Insolation",         f"{irradiance['insolation_kwh_m2']:.2f}",  "kWh/m2", NAVY),
        ("Peak GHI",           f"{irradiance['peak_ghi']:.0f}",           "W/m2",   NAVY),
        ("Energy vs Expected",
         f"{'+' if site_totals['energy_delta_kwh']>=0 else ''}{site_totals['energy_delta_kwh']:,.0f}",
         "kWh vs target PR",
         GREEN if site_totals["energy_delta_kwh"] >= 0 else RED),
    ]
    cw3 = 62
    for i, (lbl, val, sub, col) in enumerate(kpis3):
        kpi_card(10 + i * (cw3 + 2), 70, cw3, 22, lbl, val, sub, col)

    cb = chart_bytes(chart_irr)
    if cb:
        pdf.image(cb, x=10, y=95, w=190)

    draw_footer(2)

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 3 — PER-INVERTER TABLE + YIELD / PR CHARTS
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    draw_header()
    section_heading("Per-Inverter Analysis", "Specific Yield & Performance Ratio",
                    f"Inverter-level breakdown for {date_str}.", y=22)

    # Table
    tx, ty, tw = 10, 40, 190
    col_ws = [50, 32, 32, 28, 28, 20]
    headers = ["Inverter", "Spec. Yield\n(kWh/kWp)", "Energy\n(kWh)", "PR (%)", "Avail.", "Peak (kW)"]
    row_h = 7

    # Header row
    pdf.set_fill_color(*LGRAY)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*NAVY)
    cx = tx
    for h_lbl, cw in zip(headers, col_ws):
        pdf.set_xy(cx, ty)
        pdf.set_fill_color(*LGRAY)
        pdf.rect(cx, ty, cw, row_h, "FD")
        pdf.set_xy(cx + 1, ty + 1)
        pdf.multi_cell(cw - 2, 3, h_lbl, align="C")
        cx += cw

    # Data rows
    for ri, (_, row) in enumerate(per_inv.iterrows()):
        pr_pct  = row["pr"] * 100
        av_pct  = row["availability"] * 100
        if av_pct == 0 or pr_pct < 70:
            bg = (253, 236, 234)
        elif pr_pct < pr_target * 100:
            bg = (255, 245, 230)
        else:
            bg = (237, 247, 233)
        ry = ty + (ri + 1) * row_h
        vals = [row["inverter"], f"{row['spec_yield']:.3f}", f"{row['energy_kwh']:.1f}",
                f"{pr_pct:.1f}%", f"{av_pct:.0f}%", f"{row['peak_kw']:.1f}"]
        cx = tx
        for val, cw in zip(vals, col_ws):
            pdf.set_fill_color(*bg)
            pdf.rect(cx, ry, cw, row_h, "FD")
            pdf.set_xy(cx + 1, ry + 2)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*DTXT)
            pdf.cell(cw - 2, 4, str(val), align="R" if cx > tx else "L")
            cx += cw
        if ry > 160:  # Guard against table running off page
            break

    # Two charts side by side
    chart_y = ty + (min(len(per_inv), 15) + 1) * row_h + 5
    if chart_y > 170:
        chart_y = 170
    cby = chart_bytes(chart_yield)
    cbp = chart_bytes(chart_pr)
    if cby:
        pdf.image(cby, x=10, y=chart_y, w=93)
    if cbp:
        pdf.image(cbp, x=107, y=chart_y, w=93)

    draw_footer(3)

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 4 — AVAILABILITY
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    draw_header()
    section_heading("Availability Analysis", "Per-Inverter Availability",
                    "Fraction of daylight intervals each inverter was operational.", y=22)

    irr_thr = site_cfg.get("irr_threshold", 50)
    pwr_thr = site_cfg.get("power_threshold", 1)
    pdf.set_xy(10, 42)
    pdf.set_fill_color(251, 252, 253)
    pdf.set_draw_color(*BDRG)
    pdf.rect(10, 42, 190, 20, "FD")
    pdf.set_fill_color(*ORANGE)
    pdf.rect(10, 42, 3, 20, "F")
    pdf.set_draw_color(*BDRG)
    pdf.set_xy(15, 44)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 5, "Availability Methodology")
    pdf.set_xy(15, 50)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*DTXT)
    pdf.multi_cell(183, 4.5,
        f"Availability is the fraction of 10-min intervals during daylight hours "
        f"(GHI > {irr_thr:.0f} W/m2) where AC power exceeded {pwr_thr:.0f} kW. "
        f"Inverters with zero availability were offline all day.")

    cba = chart_bytes(chart_avail)
    if cba:
        pdf.image(cba, x=10, y=65, w=190)

    draw_footer(4)

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 5 — WATERFALL + ALERTS
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    draw_header()
    section_heading("Energy Losses", "Daily Energy Loss Waterfall",
                    "Decomposition of theoretical energy into successive loss categories.", y=22)

    cbw = chart_bytes(chart_wfall)
    if cbw:
        pdf.image(cbw, x=10, y=40, w=190)

    # Alerts
    alerts_y = 155
    pdf.set_xy(10, alerts_y)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 6, "Alerts & Alarms")
    alerts_y += 8

    if not alerts:
        pdf.set_xy(10, alerts_y)
        pdf.set_fill_color(251, 252, 253)
        pdf.rect(10, alerts_y, 190, 12, "FD")
        pdf.set_xy(13, alerts_y + 3)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*DTXT)
        pdf.cell(0, 5, "No alerts detected. All inverters operated within expected parameters.")
        alerts_y += 14
    else:
        for a in alerts:
            sev = a["severity"]
            bar_col = RED if sev == "HIGH" else AMBER if sev == "MEDIUM" else DTXT
            if alerts_y > 270:
                break
            pdf.set_fill_color(251, 252, 253)
            pdf.rect(10, alerts_y, 190, 18, "FD")
            pdf.set_fill_color(*bar_col)
            pdf.rect(10, alerts_y, 3, 18, "F")
            pdf.set_xy(15, alerts_y + 2)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*DTXT)
            pdf.cell(0, 4, _latin1(f"{a['inverter']} - {a['description']}"))
            pdf.set_xy(15, alerts_y + 7)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(*MGRAY)
            pdf.multi_cell(183, 4, _latin1(f"Cause: {a.get('likely_cause','')}. Action: {a.get('recommended_action','')}."))
            alerts_y += 20

    draw_footer(5)

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE 6 — COMMENTARY + DATA QUALITY
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()
    draw_header()
    section_heading("Interpretation", "Commentary & Analysis Capability",
                    "Automated interpretation and data quality assessment.", y=22)

    cy = 42
    # Commentary card — orange left stripe + border
    card_x, card_w = 10, 190
    stripe = 3
    pad_l  = stripe + 4   # text starts after stripe
    text_w = card_w - pad_l - 3
    card_start = cy

    # Title
    pdf.set_xy(card_x + pad_l, cy + 2)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*NAVY)
    pdf.cell(text_w, 5, "Automated Interpretation")
    cy += 9

    for para in (commentary or []):
        clean = _strip_html(para)
        if not clean:
            continue
        # Truncate very long paragraphs (KB guidance) to keep readable
        if len(clean) > 600:
            clean = clean[:597] + "..."
        pdf.set_xy(card_x + pad_l, cy)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*DTXT)
        pdf.multi_cell(text_w, 5, clean)
        cy = pdf.get_y() + 3
        if cy > 205:
            break

    cy += 2
    card_h = cy - card_start

    # Draw card background + orange stripe + border
    pdf.set_fill_color(251, 252, 253)
    pdf.rect(card_x, card_start, card_w, card_h, "F")
    pdf.set_fill_color(*ORANGE)
    pdf.rect(card_x, card_start, stripe, card_h, "F")
    pdf.set_draw_color(*BDRG)
    pdf.rect(card_x, card_start, card_w, card_h)

    # Data quality table
    cy += 4
    if data_quality and cy < 240:
        pdf.set_xy(10, cy)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 5, "Analysis Capability Summary")
        cy += 7
        dq_headers = ["Analysis", "Status", "Impact on Report", "To Unlock"]
        dq_cws     = [52, 32, 62, 44]
        pdf.set_fill_color(*LGRAY)
        dx = 10
        for dh, dcw in zip(dq_headers, dq_cws):
            pdf.set_xy(dx, cy)
            pdf.rect(dx, cy, dcw, 6, "FD")
            pdf.set_xy(dx + 1, cy + 1)
            pdf.set_font("Helvetica", "B", 6.5)
            pdf.set_text_color(*NAVY)
            pdf.cell(dcw - 2, 4, dh)
            dx += dcw
        cy += 6
        for drow in data_quality:
            if cy > 270:
                break
            analysis, (status_text, status_color_hex), _, impact, remedy = drow
            try:
                sc = tuple(int(status_color_hex.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
            except Exception:
                sc = DTXT
            dx = 10
            row_vals = [_latin1(analysis), _latin1(status_text), _latin1(impact), _latin1(remedy)]
            for rv, dcw in zip(row_vals, dq_cws):
                pdf.rect(dx, cy, dcw, 7, "D")
                pdf.set_xy(dx + 1, cy + 1.5)
                pdf.set_font("Helvetica", "B" if dx == 10 + dq_cws[0] else "", 6.5)
                pdf.set_text_color(*(sc if dx == 10 + dq_cws[0] else DTXT))
                pdf.multi_cell(dcw - 2, 3.5, rv)
                dx += dcw
            cy += 7

    draw_footer(6)

    # ── Save ──────────────────────────────────────────────────────────────────
    pdf.output(str(pdf_path))
