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
    pr_target = site_cfg["operating_pr_target"]

    chart_irr    = _b64_png(chart_daily_irradiance(irradiance))
    chart_yield  = _b64_png(chart_per_inverter_yield(per_inv, pr_target))
    chart_avail  = _b64_png(chart_per_inverter_availability(per_inv))
    chart_pr     = _b64_png(chart_per_inverter_pr(per_inv, pr_target))
    chart_wfall  = _b64_png(chart_daily_waterfall(waterfall))

    # ── 3. Logo ─────────────────────────────────────────────────────────────
    logo_b64 = _b64_file(_ROOT / "dolfines_logo_white.png")
    if not logo_b64:
        logo_b64 = _b64_file(_ROOT / "8p2_logo_white.png")  # fallback

    # ── 4. Alerts table rows ─────────────────────────────────────────────────
    severity_class = {"HIGH": "row-danger", "MEDIUM": "row-warning", "INFO": ""}

    # ── 5. Per-inverter table rows ────────────────────────────────────────────
    inv_rows = []
    for _, row in per_inv.iterrows():
        pr_pct   = row["pr"] * 100
        avail    = row["availability"] * 100
        ok_class = "" if row["pr_ok"] else "row-warning"
        if avail == 0:
            ok_class = "row-danger"
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
        site_cfg    = site_cfg,
        report_date = report_date,
        logo_b64    = logo_b64,
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

    try:
        _playwright_pdf(html_path, pdf_path)
        return pdf_path, html_path
    except Exception:
        # Playwright unavailable — caller receives html_path only
        return None, html_path


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

def _render_html(*, site_cfg, report_date, logo_b64, irradiance, site_totals,
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

    # KPI colour helpers
    def pr_color(pr_pct):
        if pr_pct >= pr_target * 100 - 2:
            return "#2E8B57"
        elif pr_pct >= pr_target * 100 - 8:
            return "#E67E22"
        return "#C0392B"

    def avail_color(avail_pct):
        return "#2E8B57" if avail_pct >= 95 else ("#E67E22" if avail_pct >= 85 else "#C0392B")

    # Alerts HTML
    alerts_html = ""
    if not alerts:
        alerts_html = "<p style='color:#2E8B57;font-weight:600;'>✓ No alerts detected for this date.</p>"
    else:
        rows_html = ""
        for a in alerts:
            bg = {"HIGH": "#fff0f0", "MEDIUM": "#fff8e1", "INFO": "#f0f4ff"}.get(a["severity"], "#fff")
            badge_col = {"HIGH": "#C0392B", "MEDIUM": "#E67E22", "INFO": "#5B8DD9"}.get(a["severity"], "#999")
            rows_html += f"""
            <tr style="background:{bg};">
              <td style="padding:4px 8px;font-size:8pt;">
                <span style="background:{badge_col};color:white;padding:1px 7px;
                  border-radius:10px;font-size:7pt;font-weight:700;">{a["severity"]}</span>
              </td>
              <td style="padding:4px 8px;font-size:8pt;font-weight:600;">{a["inverter"]}</td>
              <td style="padding:4px 8px;font-size:8pt;">{a["description"]}</td>
              <td style="padding:4px 8px;font-size:8pt;color:#555;">{a["likely_cause"]}</td>
              <td style="padding:4px 8px;font-size:8pt;">{a["recommended_action"]}</td>
            </tr>"""
        alerts_html = f"""
        <table style="width:100%;border-collapse:collapse;font-family:'Open Sans',Arial,sans-serif;">
          <thead>
            <tr style="background:#003D6B;color:white;">
              <th style="padding:5px 8px;font-size:8pt;text-align:left;">Severity</th>
              <th style="padding:5px 8px;font-size:8pt;text-align:left;">Inverter</th>
              <th style="padding:5px 8px;font-size:8pt;text-align:left;">Description</th>
              <th style="padding:5px 8px;font-size:8pt;text-align:left;">Likely Cause</th>
              <th style="padding:5px 8px;font-size:8pt;text-align:left;">Recommended Action</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>"""

    # Inverter table
    inv_table_rows = ""
    for r in inv_rows:
        bg = {"row-danger": "#fff0f0", "row-warning": "#fff8e1"}.get(r["row_class"], "")
        inv_table_rows += f"""
        <tr style="background:{bg};">
          <td style="padding:3px 6px;font-size:7.5pt;font-weight:600;">{r["inverter"]}</td>
          <td style="padding:3px 6px;font-size:7.5pt;text-align:right;">{r["spec_yield"]}</td>
          <td style="padding:3px 6px;font-size:7.5pt;text-align:right;">{r["energy_kwh"]}</td>
          <td style="padding:3px 6px;font-size:7.5pt;text-align:right;">{r["pr_pct"]}</td>
          <td style="padding:3px 6px;font-size:7.5pt;text-align:right;">{r["avail_pct"]}</td>
          <td style="padding:3px 6px;font-size:7.5pt;text-align:right;">{r["peak_kw"]}</td>
        </tr>"""

    logo_html = (f'<img src="{logo_b64}" style="height:48px;width:auto;" />'
                 if logo_b64 else "")

    high_count   = sum(1 for a in alerts if a["severity"] == "HIGH")
    medium_count = sum(1 for a in alerts if a["severity"] == "MEDIUM")
    alert_summary = (f"{high_count} HIGH · {medium_count} MEDIUM"
                     if (high_count or medium_count) else "None")

    css = """
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&display=swap');
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Open Sans', Arial, sans-serif; font-size: 9pt; color: #1a1a2e;
           background: white; }
    @page { size: A4; margin: 12mm 14mm 14mm 14mm; }
    .page { page-break-after: always; min-height: 257mm; }
    .page:last-child { page-break-after: auto; }
    .header { display: flex; align-items: center; justify-content: space-between;
               border-bottom: 2px solid #003D6B; padding-bottom: 6px; margin-bottom: 10px; }
    .header-left { display: flex; align-items: center; gap: 14px; }
    .header-site { font-size: 11pt; font-weight: 700; color: #003D6B; letter-spacing: 0.05em;
                    text-transform: uppercase; }
    .header-sub { font-size: 8pt; color: #666; }
    .header-right { font-size: 7.5pt; color: #888; text-align: right; }
    .section-title { font-size: 10.5pt; font-weight: 700; color: #003D6B;
                      border-left: 4px solid #F07820; padding-left: 8px; margin: 10px 0 6px 0; }
    .kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin-bottom: 10px; }
    .kpi-card { background: #f5f8fc; border: 1px solid #dce6f0; border-radius: 6px;
                 padding: 8px 10px; text-align: center; }
    .kpi-label { font-size: 7pt; color: #555; font-weight: 600; text-transform: uppercase;
                  letter-spacing: 0.04em; margin-bottom: 3px; }
    .kpi-value { font-size: 14pt; font-weight: 700; line-height: 1.1; }
    .kpi-sub { font-size: 6.5pt; color: #888; margin-top: 2px; }
    .chart-card { border: 1px solid #dce6f0; border-radius: 6px; padding: 6px;
                   margin-bottom: 8px; background: #fafcff; }
    .chart-card img { width: 100%; height: auto; display: block; }
    .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .cover-page { background: linear-gradient(135deg, #001a3a 0%, #003366 60%, #0a4d8c 100%);
                   color: white; display: flex; flex-direction: column;
                   justify-content: center; align-items: center; text-align: center;
                   min-height: 257mm; }
    .cover-logo { margin-bottom: 30px; }
    .cover-title { font-size: 22pt; font-weight: 700; letter-spacing: 0.06em;
                    text-transform: uppercase; margin-bottom: 8px; }
    .cover-subtitle { font-size: 13pt; color: rgba(255,255,255,0.75); margin-bottom: 24px; }
    .cover-date { font-size: 15pt; font-weight: 600; color: #F07820; margin-bottom: 8px; }
    .cover-site { font-size: 10pt; color: rgba(255,255,255,0.60); }
    .cover-badge { display: inline-block; background: #F07820; color: white;
                    padding: 4px 16px; border-radius: 20px; font-size: 9pt;
                    font-weight: 700; margin-top: 30px; }
    .footer { border-top: 1px solid #dce6f0; padding-top: 4px; margin-top: 8px;
               font-size: 6.5pt; color: #aaa; display: flex;
               justify-content: space-between; }
    """

    def page_header(title: str) -> str:
        return f"""
        <div class="header">
          <div class="header-left">
            {logo_html}
            <div>
              <div class="header-site">{site_name}</div>
              <div class="header-sub">{title}</div>
            </div>
          </div>
          <div class="header-right">
            Daily Report &nbsp;·&nbsp; {date_str}<br/>
            Generated {gen_dt}
          </div>
        </div>"""

    def page_footer(page_num: int, total: int = 6) -> str:
        return f"""
        <div class="footer">
          <span>PVPAT — Daily Performance Report &nbsp;·&nbsp; {site_name}</span>
          <span>CONFIDENTIAL — Dolfines</span>
          <span>Page {page_num} of {total}</span>
        </div>"""

    # ── PAGE 1: COVER ────────────────────────────────────────────────────────
    p1 = f"""
    <div class="page cover-page">
      <div class="cover-logo">{logo_html}</div>
      <div class="cover-title">Daily Performance Report</div>
      <div class="cover-subtitle">{site_name}</div>
      <div class="cover-date">{date_str}</div>
      <div class="cover-site">
        {site_cfg.get('technology','—')} &nbsp;·&nbsp;
        {cap_dc:.0f} kWp DC &nbsp;/&nbsp; {cap_ac:.0f} kW AC<br/>
        {site_cfg.get('n_inverters','—')} × {site_cfg.get('inverter_model','—')}
      </div>
      <div class="cover-badge">PVPAT Platform &nbsp;·&nbsp; Dolfines</div>
    </div>"""

    # ── PAGE 2: DAILY KPIs + IRRADIANCE ─────────────────────────────────────
    pr_col    = pr_color(site_totals["pr_pct"])
    avail_col = avail_color(site_totals["availability_pct"])

    p2 = f"""
    <div class="page">
      {page_header("Daily Summary & Irradiance")}

      <div class="section-title">Daily Key Performance Indicators</div>
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">Total Energy</div>
          <div class="kpi-value" style="color:#003D6B;">{site_totals["total_energy_kwh"]:,.0f}</div>
          <div class="kpi-sub">kWh</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Specific Yield</div>
          <div class="kpi-value" style="color:#003D6B;">{site_totals["spec_yield"]:.3f}</div>
          <div class="kpi-sub">kWh/kWp</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Performance Ratio</div>
          <div class="kpi-value" style="color:{pr_col};">{site_totals["pr_pct"]:.1f}%</div>
          <div class="kpi-sub">Target {site_totals["pr_target_pct"]:.0f}%</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Fleet Availability</div>
          <div class="kpi-value" style="color:{avail_col};">{site_totals["availability_pct"]:.1f}%</div>
          <div class="kpi-sub">daylight hours</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Alerts</div>
          <div class="kpi-value" style="color:{'#C0392B' if high_count else '#E67E22' if medium_count else '#2E8B57'};font-size:11pt;">
            {alert_summary}
          </div>
          <div class="kpi-sub">today</div>
        </div>
      </div>

      <div class="kpi-grid" style="grid-template-columns:repeat(3,1fr);">
        <div class="kpi-card">
          <div class="kpi-label">Insolation</div>
          <div class="kpi-value" style="color:#003D6B;">{irradiance["insolation_kwh_m2"]:.2f}</div>
          <div class="kpi-sub">kWh/m²</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Peak GHI</div>
          <div class="kpi-value" style="color:#003D6B;">{irradiance["peak_ghi"]:.0f}</div>
          <div class="kpi-sub">W/m²</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Energy vs Expected</div>
          <div class="kpi-value" style="color:{'#2E8B57' if site_totals['energy_delta_kwh'] >= 0 else '#C0392B'};">
            {'+' if site_totals['energy_delta_kwh'] >= 0 else ''}{site_totals['energy_delta_kwh']:,.0f}
          </div>
          <div class="kpi-sub">kWh vs target PR</div>
        </div>
      </div>

      <div class="section-title">Daily Irradiance Profile</div>
      <div class="chart-card"><img src="{chart_irr}" /></div>

      {page_footer(2)}
    </div>"""

    # ── PAGE 3: PER-INVERTER YIELD & PR ─────────────────────────────────────
    p3 = f"""
    <div class="page">
      {page_header("Per-Inverter Specific Yield & Performance Ratio")}

      <div class="section-title">Per-Inverter Metrics Summary</div>
      <table style="width:100%;border-collapse:collapse;margin-bottom:10px;">
        <thead>
          <tr style="background:#003D6B;color:white;">
            <th style="padding:4px 6px;font-size:7.5pt;text-align:left;">Inverter</th>
            <th style="padding:4px 6px;font-size:7.5pt;text-align:right;">Spec. Yield (kWh/kWp)</th>
            <th style="padding:4px 6px;font-size:7.5pt;text-align:right;">Energy (kWh)</th>
            <th style="padding:4px 6px;font-size:7.5pt;text-align:right;">PR (%)</th>
            <th style="padding:4px 6px;font-size:7.5pt;text-align:right;">Availability</th>
            <th style="padding:4px 6px;font-size:7.5pt;text-align:right;">Peak (kW)</th>
          </tr>
        </thead>
        <tbody>{inv_table_rows}</tbody>
      </table>

      <div class="two-col">
        <div>
          <div class="section-title" style="font-size:9pt;">Specific Yield</div>
          <div class="chart-card"><img src="{chart_yield}" /></div>
        </div>
        <div>
          <div class="section-title" style="font-size:9pt;">Performance Ratio</div>
          <div class="chart-card"><img src="{chart_pr}" /></div>
        </div>
      </div>

      {page_footer(3)}
    </div>"""

    # ── PAGE 4: AVAILABILITY ────────────────────────────────────────────────
    p4 = f"""
    <div class="page">
      {page_header("Per-Inverter Availability")}

      <div class="section-title">Inverter Availability — Daylight Hours</div>
      <p style="font-size:8pt;color:#444;margin-bottom:8px;line-height:1.45;">
        Availability is computed as the fraction of 10-minute intervals (during daylight hours,
        GHI &gt; {site_cfg["irr_threshold"]:.0f} W/m²) where measured AC power exceeded the
        {site_cfg["power_threshold"]:.0f} kW detection threshold. Inverters with zero availability
        were offline for the full day and require immediate investigation.
      </p>

      <div class="chart-card"><img src="{chart_avail}" /></div>

      {page_footer(4)}
    </div>"""

    # ── PAGE 5: WATERFALL + ALERTS ──────────────────────────────────────────
    p5 = f"""
    <div class="page">
      {page_header("Energy Waterfall & Alerts")}

      <div class="section-title">Daily Energy Loss Waterfall</div>
      <p style="font-size:8pt;color:#444;margin-bottom:6px;line-height:1.45;">
        The waterfall decomposes the theoretical energy (GHI × DC capacity) into successive
        loss categories down to the measured AC output.  Curtailment &amp; downtime represents
        residual losses beyond the design optical/thermal budget.
      </p>
      <div class="chart-card"><img src="{chart_wfall}" /></div>

      <div class="section-title">Alerts &amp; Alarms</div>
      {alerts_html}

      {page_footer(5)}
    </div>"""

    # ── PAGE 6: COMMENTARY + DATA QUALITY TABLE ──────────────────────────────
    commentary_html = ""
    if commentary:
        items_html = "".join(
            f"<li style='margin-bottom:5px;line-height:1.5;'>{c}</li>"
            for c in commentary
        )
        commentary_html = f"""
        <div class="section-title">Automated Interpretation</div>
        <ul style="font-size:8.5pt;color:#333;padding-left:18px;margin-bottom:12px;">
          {items_html}
        </ul>"""

    dq_rows_html = ""
    if data_quality:
        for row in data_quality:
            analysis, (status_text, status_color), _, impact, remedy = row
            dq_rows_html += f"""
            <tr>
              <td style="padding:4px 8px;font-size:8pt;">{analysis}</td>
              <td style="padding:4px 8px;font-size:8pt;font-weight:700;color:{status_color};">{status_text}</td>
              <td style="padding:4px 8px;font-size:8pt;color:#555;">{impact}</td>
              <td style="padding:4px 8px;font-size:8pt;color:#777;">{remedy}</td>
            </tr>"""

    dq_table_html = f"""
        <div class="section-title">Analysis Capability Summary</div>
        <p style="font-size:8pt;color:#444;margin-bottom:6px;">
          This table shows which analyses were possible given the data available
          for this report, and what data would be needed to unlock missing analyses.
        </p>
        <table style="width:100%;border-collapse:collapse;">
          <thead>
            <tr style="background:#003D6B;color:white;">
              <th style="padding:5px 8px;font-size:8pt;text-align:left;">Analysis</th>
              <th style="padding:5px 8px;font-size:8pt;text-align:left;">Status</th>
              <th style="padding:5px 8px;font-size:8pt;text-align:left;">Impact on Report</th>
              <th style="padding:5px 8px;font-size:8pt;text-align:left;">To Unlock</th>
            </tr>
          </thead>
          <tbody>{dq_rows_html}</tbody>
        </table>""" if data_quality else ""

    p6 = f"""
    <div class="page">
      {page_header("Commentary & Data Quality")}
      {commentary_html}
      {dq_table_html}
      {page_footer(6)}
    </div>"""

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
# PLAYWRIGHT PDF CONVERSION
# ─────────────────────────────────────────────────────────────────────────────

def _playwright_pdf(html_path: Path, pdf_path: Path) -> None:
    """Call Playwright via subprocess (same approach as run_jinja_report.py)."""
    script = f"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("file:///{html_path.as_posix()}", wait_until="networkidle")
        await page.pdf(
            path=r"{pdf_path}",
            format="A4",
            print_background=True,
            margin={{"top":"12mm","bottom":"14mm","left":"14mm","right":"14mm"}},
        )
        await browser.close()

asyncio.run(main())
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Playwright PDF failed:\n{result.stderr}")
