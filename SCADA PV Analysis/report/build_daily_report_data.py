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
    logo_b64 = _b64_file(_ROOT / "8p2_logo_white.png")

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
# HTML RENDERER
# ─────────────────────────────────────────────────────────────────────────────

def _render_html(*, site_cfg, report_date, logo_b64, irradiance, site_totals,
                 inv_rows, alerts, severity_class, chart_irr, chart_yield,
                 chart_avail, chart_pr, chart_wfall, waterfall) -> str:
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

    def page_footer(page_num: int, total: int = 5) -> str:
        return f"""
        <div class="footer">
          <span>PVPAT — Daily Performance Report &nbsp;·&nbsp; {site_name}</span>
          <span>CONFIDENTIAL — 8p2 Advisory / Dolfines</span>
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
      <div class="cover-badge">PVPAT Platform &nbsp;·&nbsp; 8p2 Advisory</div>
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
