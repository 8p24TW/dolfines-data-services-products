from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path

import numpy as np


def _fmt_pct(value: float | int | None, digits: int = 1) -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    return f"{value:.{digits}f}%"


def _fmt_num(value: float | int | None, digits: int = 0, suffix: str = "") -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    return f"{value:,.{digits}f}{suffix}"


def _figure_block(charts: dict, chart_id: str, title: str, caption: str, width: str = "full") -> dict | None:
    meta = charts.get(chart_id)
    if not meta:
        return None
    return {
        "title": title,
        "caption": caption,
        "src": Path(meta["path"]).as_uri(),
        "width": width,
        "alt": meta.get("alt", title),
    }


def _table_block(title: str, columns: list[str], rows: list[dict], caption: str = "", appendix_only: bool = False) -> dict:
    return {
        "title": title,
        "columns": columns,
        "rows": rows,
        "caption": caption,
        "appendix_only": appendix_only,
    }


def _kpi(label: str, value: str, target: str = "", status: str = "neutral", subtext: str = "") -> dict:
    return {
        "label": label,
        "value": value,
        "target": target,
        "status": status,
        "subtext": subtext,
    }


def _severity(level: str) -> str:
    mapping = {"HIGH": "danger", "MEDIUM": "warning", "LOW": "success", "INFO": "info"}
    return mapping.get(level, "info")


def _top_actions(punchlist: list[dict], limit: int = 6) -> list[dict]:
    ranked = sorted(punchlist, key=lambda item: item.get("mwh_loss", 0.0), reverse=True)
    return ranked[:limit]


def _status_from_threshold(value: float | int | None, threshold: float, reverse: bool = False) -> str:
    if value is None or not np.isfinite(value):
        return "neutral"
    if reverse:
        return "success" if value <= threshold else "warning"
    return "success" if value >= threshold else "warning"


def _pr_status(value: float | int | None, target: float = 78.0) -> str:
    if value is None or not np.isfinite(value):
        return "neutral"
    if value >= target:
        return "success"
    if value >= target - 5.0:
        return "warning"
    return "danger"


def _status_row_class(status: str) -> str:
    return {
        "success": "row-success",
        "warning": "row-warning",
        "danger": "row-danger",
        "info": "row-info",
    }.get(status, "")


def _clone_page_shell(page: dict, *, page_id: str, continued: bool) -> dict:
    cloned = deepcopy(page)
    cloned["id"] = page_id
    cloned["continued"] = continued
    cloned["toc_hide"] = continued
    if continued:
        cloned["summary"] = ""
    cloned["commentary"] = []
    cloned["kpis"] = []
    cloned["figures"] = []
    cloned["tables"] = []
    cloned["findings"] = []
    cloned["notes"] = []
    return cloned


def _table_row_limit(table: dict, template: str) -> int:
    title = str(table.get("title", "")).lower()
    columns = [str(col).lower() for col in table.get("columns", [])]
    if any(key in title for key in {"technical configuration", "full action punchlist", "mttf detail - all inverters"}):
        return max(len(table.get("rows", [])), 1)
    if any("recommended action" in col or "issue" in col or "action" in col for col in columns):
        return 6 if template == "section" else 8
    if len(columns) >= 6:
        return 10 if template == "section" else 12
    return 14 if template == "appendix" else 10


def _split_table_chunks(tables: list[dict], template: str) -> list[dict]:
    chunks: list[dict] = []
    for table in tables:
        rows = table.get("rows", [])
        row_limit = _table_row_limit(table, template)
        if len(rows) <= row_limit:
            chunks.append(table)
            continue
        for idx in range(0, len(rows), row_limit):
            part = deepcopy(table)
            part["rows"] = rows[idx : idx + row_limit]
            if idx > 0:
                part["title"] = f"{table['title']} (continued)"
                part["caption"] = ""
            chunks.append(part)
    return chunks


def _chunk_findings(findings: list[dict], chunk_size: int = 3) -> list[list[dict]]:
    return [findings[idx : idx + chunk_size] for idx in range(0, len(findings), chunk_size)] if findings else []


def _page_block_limit(page: dict) -> int:
    if page["template"] == "appendix":
        return 7
    if page.get("id") == "data-quality":
        return 5
    if page.get("id") == "data-quality-detail":
        return 7
    if page.get("id") in {"irradiance-coherence", "performance-overview", "losses"}:
        return 6
    return 6


def _block_weight(block_type: str, payload) -> int:
    if block_type == "commentary":
        return 2 if len(payload) > 2 else 1
    if block_type == "kpis":
        return 2 if len(payload) > 4 else 1
    if block_type == "figures":
        width = payload[0].get("width", "full")
        return 3 if width == "full" else 2
    if block_type == "tables":
        rows = len(payload[0].get("rows", []))
        return 3 if rows > 8 else 2
    if block_type == "findings":
        return 2 if len(payload) > 2 else 1
    if block_type == "notes":
        return 1
    return 1


def _paginate_section_like_page(page: dict) -> list[dict]:
    if page["template"] not in {"section", "appendix"}:
        return [page]
    if page.get("paginate") is False:
        return [page]

    blocks: list[tuple[str, object]] = []
    if page.get("commentary"):
        blocks.append(("commentary", deepcopy(page["commentary"])))
    if page.get("kpis"):
        blocks.append(("kpis", deepcopy(page["kpis"])))
    for figure in page.get("figures", []):
        blocks.append(("figures", [deepcopy(figure)]))
    for table in _split_table_chunks(page.get("tables", []), page["template"]):
        blocks.append(("tables", [table]))
    for finding_chunk in _chunk_findings(page.get("findings", []), 3):
        blocks.append(("findings", deepcopy(finding_chunk)))
    if page.get("notes"):
        blocks.append(("notes", deepcopy(page["notes"])))

    if not blocks:
        return [page]

    page_limit = _page_block_limit(page)
    expanded: list[dict] = []
    current = _clone_page_shell(page, page_id=page["id"], continued=False)
    current_weight = 0
    continuation_index = 1

    for block_type, payload in blocks:
        weight = _block_weight(block_type, payload)
        if current_weight and current_weight + weight > page_limit:
            expanded.append(current)
            current = _clone_page_shell(page, page_id=f"{page['id']}-cont-{continuation_index}", continued=True)
            continuation_index += 1
            current_weight = 0
        if block_type in {"figures", "tables", "findings"}:
            current.setdefault(block_type, [])
            current[block_type].extend(payload)
        else:
            current[block_type] = payload
        current_weight += weight

    expanded.append(current)
    return expanded


def _cover_page(config: dict, analysis: dict, generated_at: str) -> dict:
    first_ts = analysis["piv"].index.min()
    last_ts = analysis["piv"].index.max()
    module_wp = config.get("module_wp") or round(config["cap_dc_kwp"] * 1000.0 / max(config["n_modules"], 1))
    return {
        "template": "cover",
        "title": config["report_title"],
        "subtitle": "SCADA Performance Analysis Report",
        "metadata": [
            ("Project", config["site_name"]),
            ("Asset", f"{config['cap_dc_kwp']:,.0f} kWp DC / {config['cap_ac_kw']:,.0f} kW AC"),
            ("Analysis period", f"{first_ts:%d %b %Y} to {last_ts:%d %b %Y}"),
            ("Technology", f"{config['inv_model']} and {config['module_brand']} {module_wp:.0f}Wp"),
            ("Issued", generated_at),
        ],
    }


def _executive_summary_page(config: dict, analysis: dict, charts: dict) -> dict:
    annual = analysis["pr_res"]["annual"]
    monthly = analysis["pr_res"]["monthly"]
    avail_res = analysis["avail_res"]
    data_avail = analysis["data_avail"]
    wf = analysis["wf"]
    punchlist = analysis["punchlist"]
    pr_map = analysis["pr_res"]["per_inverter"]
    irr_coh = analysis.get("irr_coh") or {}

    mean_pr = float(annual["PR"].mean()) if len(annual) else np.nan
    last_pr = float(annual["PR"].iloc[-1]) if len(annual) else np.nan
    total_energy_mwh = float(annual["E_act"].sum() / 1000.0) if len(annual) else np.nan
    high_actions = sum(1 for item in punchlist if item["priority"] == "HIGH")
    medium_actions = sum(1 for item in punchlist if item["priority"] == "MEDIUM")
    low_pr_units = sorted(pr_map.items(), key=lambda item: item[1])[:2]
    worst_label = ", ".join(f"{name} ({value:.1f}%)" for name, value in low_pr_units) if low_pr_units else "No clear outlier"
    irr_ok = all(metrics["correlation"] > 0.95 and metrics["suspect_pct"] < 5 for metrics in irr_coh.values()) if irr_coh else False
    pr_target = 78.0
    critical_months = int((monthly["PR"] < 65).sum()) if len(monthly) else 0
    alert_months = int(((monthly["PR"] >= 65) & (monthly["PR"] < pr_target)).sum()) if len(monthly) else 0

    # ── Recoverable loss financials (€0.10/kWh = €100/MWh) ──────────────
    TARIFF = 100.0
    n_years = max(len(annual), 1)
    avail_loss_mwh  = abs(float(wf.get("avail_loss", 0.0)))
    tech_loss_mwh   = abs(float(wf.get("technical_loss", 0.0)))
    total_recov_ann = (avail_loss_mwh + tech_loss_mwh) / n_years
    avail_loss_eur  = avail_loss_mwh  / n_years * TARIFF
    tech_loss_eur   = tech_loss_mwh   / n_years * TARIFF
    total_recov_eur = total_recov_ann * TARIFF

    return {
        "template": "section",
        "id": "executive-summary",
        "toc_group": "Overview",
        "title": "Executive Summary",
        "kicker": "Highest-value findings",
        "summary": (
            "Portfolio-level findings on performance, availability, data quality, and corrective priorities."
        ),
        "commentary_title": "Overall assessment",
        "commentary": [
            (
                f"Average annual PR is {_fmt_pct(mean_pr)} and the latest annual PR is {_fmt_pct(last_pr)}. "
                f"Total realised production across the analysed period is {_fmt_num(total_energy_mwh, 0, ' MWh')}."
            ),
            (
                f"Site availability averages {_fmt_pct(avail_res['mean'])}. "
                f"{avail_res['whole_site_events']} whole-site outage event(s) were inferred from simultaneous daytime inverter dropouts, "
                "which indicates a grid or site-level disturbance rather than isolated inverter trips."
            ),
            (
                f"Power completeness is {_fmt_pct(data_avail['overall_power'])} and irradiance completeness is {_fmt_pct(data_avail['irradiance'])}. "
                + (
                    "Both inputs are strong enough for confident interpretation."
                    if data_avail["overall_power"] >= 95 and data_avail["irradiance"] >= 95 and irr_ok
                    else "Input quality remains a material constraint on fault attribution and any contractual energy discussion."
                )
            ),
            (f"The fleet recorded {critical_months} critical PR month(s) below 65% and {alert_months} further month(s) between 65% and {pr_target:.0f}%."),
            (
                f"Annualised recoverable losses are estimated at €{total_recov_eur:,.0f}/yr "
                f"(downtime: €{avail_loss_eur:,.0f}/yr  +  technical underperformance: €{tech_loss_eur:,.0f}/yr), "
                f"based on {TARIFF:.0f} €/MWh and averaged over {n_years} year(s). "
                "Addressing the HIGH-priority action items is expected to recover the majority of this gap."
            ),
        ],
        "kpis": [
            _kpi("Average PR", _fmt_pct(mean_pr), f"Target >= {pr_target:.0f}%", _pr_status(mean_pr, pr_target)),
            _kpi("Fleet availability", _fmt_pct(avail_res["mean"]), "Target >= 95%", _status_from_threshold(avail_res["mean"], 95)),
            _kpi("Actual energy", _fmt_num(total_energy_mwh, 0, " MWh")),
            _kpi("Priority actions", f"{high_actions} high / {medium_actions} medium", "", "danger" if high_actions else "warning" if medium_actions else "success"),
            _kpi("Recoverable losses (ann.)", f"€{total_recov_eur:,.0f} /yr", f"Downtime €{avail_loss_eur:,.0f}  +  Tech. €{tech_loss_eur:,.0f}", "danger" if total_recov_eur > 50_000 else "warning"),
        ],
        "figures": [],
        "tables": [
            _table_block(
                "Top Recommended Actions",
                ["Priority", "Category", "Estimated loss", "Action"],
                [
                    {
                        "Priority": item["priority"],
                        "Category": item["category"],
                        "Estimated loss": _fmt_num(float(item.get("mwh_loss", 0.0)), 0, " MWh"),
                        "Action": item["action"],
                        "_row_class": "row-danger" if item["priority"] == "HIGH" else "row-warning" if item["priority"] == "MEDIUM" else "row-success",
                    }
                    for item in _top_actions(punchlist, limit=3)
                ],
                "",
            )
        ],
        "findings": [
            {
                "title": "Underperformance",
                "severity": "warning" if mean_pr < pr_target else "success",
                "body": (
                    f"The site remains below the PR target of {pr_target:.0f}%, so the performance gap remains operationally material."
                    if mean_pr < pr_target
                    else f"The site is operating at or above the PR target of {pr_target:.0f}% across the analysed period."
                ),
            },
            {
                "title": "Data confidence",
                "severity": "warning" if data_avail["overall_power"] < 95 or data_avail["irradiance"] < 95 or not irr_ok else "success",
                "body": "Measured irradiance remains coherent against satellite reference." if irr_ok else "Irradiance quality or completeness still requires engineering caution.",
            },
        ],
        "notes": [],
    }


def _site_overview_page(config: dict, analysis: dict, charts: dict) -> dict:
    annual = analysis["pr_res"]["annual"]
    monthly = analysis["pr_res"]["monthly"]
    month_count = int(len(monthly))
    annual_rows = []
    for year, row in annual.iterrows():
        annual_rows.append(
            {
                "Year": str(year),
                "PR": _fmt_pct(float(row["PR"])),
                "Energy": _fmt_num(float(row["E_act"] / 1e6), 2, " GWh"),
                "Irradiation": _fmt_num(float(row["irrad"]), 0, " kWh/m²"),
            }
        )
    map_figure = _figure_block(
        charts,
        "site_map",
        "Site Location",
        "GPS coordinates: 44°41′08.3″N, 0°33′34.0″W — PVPAT Solar PV Farm, SW France.",
        width="full",
    )
    return {
        "template": "section",
        "id": "site-overview",
        "toc_group": "Overview",
        "title": "Site Overview And Technical Scope",
        "kicker": "Project baseline",
        "summary": (
            "Project context, calculation basis, and fixed site metadata."
        ),
        "commentary_title": "Method and asset summary",
        "commentary": [
            (
                f"{config['site_name']} is a utility-scale solar photovoltaic site with {config['cap_dc_kwp']:,.0f} kWp DC and "
                f"{config['cap_ac_kw']:,.0f} kW AC, using {config['n_inverters']} {config['inv_model']} inverters and {config['n_modules']:,} "
                f"{config['module_brand']} modules."
            ),
            (
                f"The report covers {month_count} analysed months of {config['interval_min']}-minute SCADA data. "
                "Performance Ratio remains on the IEC 61724 DC-nameplate basis, and SARAH satellite irradiance remains the reference for budget comparison."
            ),
        ],
        "kpis": [
            _kpi("DC/AC ratio", _fmt_num(config["dc_ac_ratio"], 2)),
            _kpi("Sampling interval", f"{config['interval_min']} min"),
            _kpi("Modules", _fmt_num(config["n_modules"], 0)),
            _kpi("Inverters", _fmt_num(config["n_inverters"], 0)),
        ],
        "figures": [fig for fig in [map_figure] if fig],
        "tables": [
            _table_block(
                "Annual Performance Summary",
                ["Year", "PR", "Energy", "Irradiation"],
                annual_rows,
                "Yearly performance values provide the annual production and irradiance context for the assessment period.",
            )
        ],
        "findings": [
            {
                "title": "Design benchmark",
                "severity": "info",
                "body": "The report uses a 78% operating PR target and an 80% design PR assumption for budget and loss discussions.",
            }
        ],
        "notes": [],
    }


def _technical_parameters_page(config: dict) -> dict:
    module_wp = config.get("module_wp") or round(config["cap_dc_kwp"] * 1000.0 / max(config["n_modules"], 1))
    spec_rows = [
        {"Parameter": "Site Name", "Value": config["site_name"]},
        {"Parameter": "Analysis Period", "Value": "2023 - 2024"},
        {"Parameter": "DC Capacity", "Value": f"{config['cap_dc_kwp']:.2f} kWp"},
        {"Parameter": "AC Capacity", "Value": f"{config['cap_ac_kw']:.0f} kW"},
        {"Parameter": "DC / AC Ratio", "Value": f"{config['dc_ac_ratio']:.2f}"},
        {"Parameter": "Number of Modules", "Value": f"{config['n_modules']:,}"},
        {"Parameter": "Module Power", "Value": f"{module_wp:.0f} Wp"},
        {"Parameter": "Module Brand", "Value": config["module_brand"]},
        {"Parameter": "Module Temp. Coefficient", "Value": f"{config['temp_coeff'] * 100:.2f} %/°C"},
        {"Parameter": "Number of Inverters", "Value": f"{config['n_inverters']}"},
        {"Parameter": "Inverter Model", "Value": config["inv_model"]},
        {"Parameter": "Inverter AC Power", "Value": f"{config['inv_ac_kw']:.0f} kW each"},
        {"Parameter": "Strings per Inverter", "Value": f"{config['n_strings_inv']}"},
        {"Parameter": "Structure Types", "Value": config["structure_types"]},
        {"Parameter": "Transformer Substations", "Value": f"{config['n_ptr']}"},
        {"Parameter": "SCADA Data Interval", "Value": f"{config['interval_min']} minutes"},
        {"Parameter": "PR Calculation Method", "Value": "IEC 61724 - AC energy / (G_meas/G_STC x P_DC_kWp)"},
        {"Parameter": "Budget PR Assumption", "Value": f"{config['design_pr'] * 100:.0f}%"},
        {"Parameter": "Irradiance Threshold", "Value": f"{config['irr_threshold']:.0f} W/m² (daytime cut-off)"},
        {"Parameter": "Reference Irradiance", "Value": "SARAH-3 satellite POA data (Nord & Sud orientations)"},
    ]
    return {
        "template": "section",
        "id": "technical-parameters",
        "toc_group": "Overview",
        "title": "Technical Configuration & Analysis Parameters",
        "kicker": "Technical basis",
        "summary": "Full plant configuration and calculation assumptions used throughout the assessment.",
        "commentary_title": "Configuration summary",
        "commentary": [
            f"{config['site_name']} uses {config['n_inverters']} {config['inv_model']} inverters and {config['n_modules']:,} {config['module_brand']} modules; the table below consolidates the fixed inputs and thresholds used throughout the analysis.",
        ],
        "kpis": [],
        "figures": [],
        "tables": [
            _table_block(
                "Technical Configuration & Analysis Parameters",
                ["Parameter", "Value"],
                spec_rows,
                "Plant configuration, modelling assumptions, and screening thresholds used throughout the report.",
            )
        ],
        "findings": [],
        "notes": [],
    }


def _performance_kpi_dashboard_page(config: dict, analysis: dict) -> dict:
    annual = analysis["pr_res"]["annual"]
    avail_res = analysis["avail_res"]
    data_avail = analysis["data_avail"]
    wf = analysis["wf"]
    punchlist = analysis["punchlist"]
    irr_coh = analysis.get("irr_coh") or {}
    last_year = int(annual.index[-1]) if len(annual) else "--"
    last_pr = float(annual["PR"].iloc[-1]) if len(annual) else np.nan
    all_pr = float(annual["PR"].mean()) if len(annual) else np.nan
    total_energy = float(annual["E_act"].sum()) / 1000 if len(annual) else np.nan
    specific_yield = total_energy * 1000 / max(config["cap_dc_kwp"], 1) / max(len(annual), 1) if len(annual) else np.nan
    irr_ok = all(d["correlation"] > 0.95 and d["suspect_pct"] < 5 for d in irr_coh.values()) if irr_coh else False
    design_pr = config["design_pr"] * 100
    pr_target = 78.0
    e_ref_total = float(annual["E_ref"].sum()) / 1000 if len(annual) else 0
    clean_pr = (total_energy + abs(wf.get("avail_loss", 0)) + abs(wf.get("technical_loss", 0))) / e_ref_total * 100 if e_ref_total > 0 else np.nan
    last_pr_status = _pr_status(last_pr, pr_target)
    all_pr_status = _pr_status(all_pr, pr_target)
    rows = [
        {"Metric": f"Site PR ({last_year})", "Value": _fmt_pct(last_pr), "Target": f">= {pr_target:.0f}%", "Status": "On target" if last_pr_status == "success" else "Watch" if last_pr_status == "warning" else "Below target", "_row_class": _status_row_class(last_pr_status)},
        {"Metric": "PR Average (all years)", "Value": _fmt_pct(all_pr), "Target": f">= {pr_target:.0f}%", "Status": "On target" if all_pr_status == "success" else "Watch" if all_pr_status == "warning" else "Below target", "_row_class": _status_row_class(all_pr_status)},
        {"Metric": "Total Energy Produced", "Value": _fmt_num(total_energy, 0, " MWh"), "Target": "-", "Status": "Reference", "_row_class": "row-info"},
        {"Metric": "Specific Yield (annual avg.)", "Value": _fmt_num(specific_yield, 0, " kWh/kWp/yr"), "Target": "-", "Status": "Reference", "_row_class": "row-info"},
        {"Metric": "Mean Inverter Availability", "Value": _fmt_pct(avail_res["mean"]), "Target": ">= 95%", "Status": "On target" if avail_res["mean"] >= 95 else "Below target", "_row_class": "row-success" if avail_res["mean"] >= 95 else "row-warning"},
        {"Metric": "Power Data Completeness", "Value": _fmt_pct(data_avail["overall_power"]), "Target": ">= 95%", "Status": "On target" if data_avail["overall_power"] >= 95 else "Below target", "_row_class": "row-success" if data_avail["overall_power"] >= 95 else "row-warning"},
        {"Metric": "Irradiance Data Completeness", "Value": _fmt_pct(data_avail["irradiance"]), "Target": ">= 95%", "Status": "On target" if data_avail["irradiance"] >= 95 else "Below target", "_row_class": "row-success" if data_avail["irradiance"] >= 95 else "row-warning"},
        {"Metric": "Irradiance Sensor Quality", "Value": "Coherent" if irr_ok else "Review", "Target": "Coherent", "Status": "Coherent" if irr_ok else "Review required", "_row_class": "row-success" if irr_ok else "row-warning"},
        {"Metric": "High Priority Action Items", "Value": str(sum(1 for item in punchlist if item["priority"] == "HIGH")), "Target": "0", "Status": "None" if not any(item["priority"] == "HIGH" for item in punchlist) else "Open", "_row_class": "row-success" if not any(item["priority"] == "HIGH" for item in punchlist) else "row-danger"},
        {"Metric": "Potential PR (no downtime)", "Value": _fmt_pct(clean_pr), "Target": f"Indicative vs {design_pr:.0f}% design", "Status": "Indicative scenario", "_row_class": "row-info"},
    ]
    return {
        "template": "section",
        "id": "performance-kpi-dashboard",
        "toc_group": "Overview",
        "title": "Performance KPI Dashboard",
        "kicker": "KPI screen",
        "summary": "High-level screen of performance, availability, data quality, and corrective-action exposure.",
        "commentary_title": "Dashboard interpretation",
        "commentary": [
            "This dashboard provides a consolidated technical read-out of performance, availability, data quality, and corrective priority exposure.",
        ],
        "kpis": [],
        "figures": [],
        "tables": [
            _table_block(
                "Performance KPI Dashboard",
                ["Metric", "Value", "Target", "Status"],
                rows,
            )
        ],
        "findings": [],
        "notes": [],
    }


def _data_quality_page(analysis: dict, charts: dict) -> dict:
    data_avail = analysis["data_avail"]
    irr_coh = analysis.get("irr_coh") or {}
    worst = sorted(data_avail["per_inverter"].items(), key=lambda item: item[1])[:6]
    n_below95 = sum(1 for value in data_avail["per_inverter"].values() if value < 95)
    n_below90 = sum(1 for value in data_avail["per_inverter"].values() if value < 90)
    worst_inv, worst_value = worst[0] if worst else ("n/a", np.nan)
    commentary = [
        (
            f"Power completeness is {_fmt_pct(data_avail['overall_power'])} and irradiance completeness is {_fmt_pct(data_avail['irradiance'])}. "
            + (
                "Both are at or above the 95% target, so the main energy and PR indicators are suitable for engineering interpretation."
                if data_avail["overall_power"] >= 95 and data_avail["irradiance"] >= 95
                else "One or both channels remain below the 95% target, so KPI values during missing-data periods carry elevated uncertainty and should not be used for contractual conclusions without gap recovery."
            )
        )
    ]
    if n_below95:
        commentary.append(
            f"{n_below95} inverter(s) fall below 95% telemetry completeness and {n_below90} fall below 90%; the weakest channel is {worst_inv} at {_fmt_pct(worst_value)}. Persistent single-inverter gaps bias availability and reliability metrics disproportionately on those units."
        )
    if irr_coh:
        best_name, best_metrics = sorted(irr_coh.items(), key=lambda item: item[1]["correlation"], reverse=True)[0]
        ratio = best_metrics["mean_ratio"]
        ratio_text = (
            "no material irradiance bias is visible."
            if 0.90 <= ratio <= 1.10
            else "sensor bias remains plausible and should be checked in the field."
        )
        commentary.append(
            (
                f"Against SARAH_{best_name}, measured irradiance correlation is {best_metrics['correlation']:.3f} with "
                f"{best_metrics['suspect_pct']:.1f}% suspect readings; {ratio_text}"
            )
        )
    else:
        commentary.append("No SARAH comparison is available, so the report relies only on measured irradiance completeness and consistency checks.")

    return {
        "template": "section",
        "id": "data-quality",
        "toc_group": "Overview",
        "paginate": False,
        "title": "Data Quality And Irradiance Confidence",
        "kicker": "Input quality",
        "summary": (
            "Telemetry completeness and irradiance confidence review."
        ),
        "commentary_title": "Engineering interpretation",
        "commentary": commentary,
        "kpis": [
            _kpi("Power completeness", _fmt_pct(data_avail["overall_power"]), "Target >= 95%", _status_from_threshold(data_avail["overall_power"], 95)),
            _kpi("Irradiance completeness", _fmt_pct(data_avail["irradiance"]), "Target >= 95%", _status_from_threshold(data_avail["irradiance"], 95)),
        ],
        "figures": [
            figure
            for figure in [
                _figure_block(
                    charts,
                    "data_availability_overview",
                    "Telemetry Completeness Overview",
                    "Per-inverter completeness is compared with site-wide power and irradiance coverage to highlight the most material telemetry risks.",
                ),
            ]
            if figure
        ],
        "tables": [],
        "findings": [],
        "notes": [],
    }


def _irradiance_coherence_pages(analysis: dict, charts: dict) -> list[dict]:
    irr_coh = analysis.get("irr_coh") or {}
    if not irr_coh:
        return []
    rows = [
        {
            "Reference": f"SARAH_{name}",
            "R (corr.)": f"{metrics['correlation']:.3f}",
            "Ratio ± σ": f"{metrics['mean_ratio']:.2f} ± {metrics['std_ratio']:.2f}",
            "Suspect %": _fmt_pct(metrics["suspect_pct"], 1),
            "Gap days": _fmt_num(metrics.get("days_with_gaps"), 0),
            "Status": "OK" if metrics["correlation"] > 0.95 and metrics["suspect_pct"] < 5 else "Review",
            "_row_class": "row-success" if metrics["correlation"] > 0.95 and metrics["suspect_pct"] < 5 else "row-warning",
        }
        for name, metrics in sorted(irr_coh.items())
    ]
    chart_page = {
        "template": "section",
        "id": "irradiance-coherence",
        "toc_group": "Overview",
        "paginate": False,
        "title": "Irradiance Data Coherence Analysis",
        "kicker": "Sensor confidence",
        "summary": "Measured irradiance cross-checked against SARAH to screen bias, suspect readings, and PR denominator reliability.",
        "commentary_title": "Engineering interpretation",
        "commentary": [],
        "kpis": [],
        "figures": [
            figure
            for figure in [
                _figure_block(
                    charts,
                    "irradiance_monthly_comparison",
                    "Measured Irradiance Vs SARAH Monthly Totals",
                    "Measured monthly irradiation is compared against each SARAH reference, with monthly bias shown on the secondary axis.",
                    width="full",
                ),
            ]
            if figure
        ],
        "tables": [],
        "findings": [],
        "notes": [],
    }
    summary_page = {
        "template": "section",
        "id": "irradiance-coherence-cont-1",
        "toc_group": "Overview",
        "toc_hide": True,
        "paginate": False,
        "continued": True,
        "title": "Irradiance Data Coherence Analysis",
        "kicker": "Sensor confidence",
        "summary": "",
        "commentary_title": "Engineering interpretation",
        "commentary": [],
        "kpis": [],
        "figures": [
            figure
            for figure in [
                _figure_block(
                    charts,
                    "irradiance_scatter",
                    "Measured Irradiance Vs SARAH Scatter",
                    "The scatter highlights overall correlation and the extent of random or systematic sensor deviation.",
                    width="full",
                ),
            ]
            if figure
        ],
        "tables": [
            _table_block(
                "Irradiance Coherence Summary",
                ["Reference", "R (corr.)", "Ratio ± σ", "Suspect %", "Gap days", "Status"],
                rows,
            )
        ],
        "findings": [],
        "notes": [],
    }
    return [chart_page, summary_page]


def _data_quality_detail_page(analysis: dict, charts: dict) -> dict:
    data_avail = analysis["data_avail"]
    monthly = data_avail.get("monthly", {})
    monthly_df = monthly if hasattr(monthly, "empty") else None
    if monthly_df is None:
        import pandas as pd  # local import to avoid broad module dependency change

        monthly_df = pd.DataFrame(monthly)

    n_sitewide = 0
    if not monthly_df.empty:
        n_sitewide = int((monthly_df.min(axis=1) < 90).sum())

    findings = []
    if n_sitewide:
        findings.append(
            {
                "title": "Site-wide outage pattern",
                "severity": "warning",
                "body": f"{n_sitewide} month-level periods show broad site-wide degradation in completeness, which remains more consistent with logger, network, or export interruptions than isolated inverter faults.",
            }
        )
    if not monthly_df.empty:
        weakest_month = monthly_df.min(axis=1).sort_values().index[0]
        findings.append(
            {
                "title": "Weakest completeness window",
                "severity": "warning",
                "body": f"The weakest month-level completeness window occurs in {weakest_month:%b %Y}, where several inverters degrade simultaneously and the period should be reconciled against SCADA buffer recovery and logger event history.",
            }
        )

    return {
        "template": "section",
        "id": "data-quality-detail",
        "toc_group": "Overview",
        "paginate": False,
        "title": "Data Quality Detail",
        "kicker": "Gap pattern review",
        "summary": "Monthly missing-data pattern review.",
        "commentary_title": "Detailed interpretation",
        "commentary": [],
        "kpis": [],
        "figures": [
            figure
            for figure in [
                _figure_block(
                    charts,
                    "data_availability_heatmap",
                    "Monthly Inverter Completeness Heatmap",
                    "Vertical low-completeness bands indicate site-wide outages; horizontal bands indicate inverter-specific communication gaps.",
                ),
            ]
            if figure
        ],
        "tables": [],
        "findings": findings,
        "notes": [],
    }


def _losses_page(analysis: dict, charts: dict) -> dict:
    wf = analysis["wf"]
    top_actions = _top_actions(analysis["punchlist"], limit=3)
    residual_direction = "underperformance" if wf["residual"] < 0 else "overperformance"
    recovery_mwh = abs(wf["avail_loss"]) * 0.40

    return {
        "template": "section",
        "id": "losses",
        "toc_group": "Technical Findings",
        "title": "Losses And Recoverability",
        "kicker": "Budget-to-actual bridge",
        "summary": (
            "Budget-to-actual energy bridge and recoverable loss summary."
        ),
        "commentary_title": "Interpretation",
        "commentary": [
            (
                f"The weather-corrected budget is {_fmt_num(wf['weather_corrected'], 0, ' MWh')} against actual production of {_fmt_num(wf['actual'], 0, ' MWh')}."
            ),
            (
                f"Availability loss is {_fmt_num(abs(wf['avail_loss']), 0, ' MWh')}, technical loss is {_fmt_num(abs(wf['technical_loss']), 0, ' MWh')}, and the residual term indicates {residual_direction} of {_fmt_num(abs(wf['residual']), 0, ' MWh')}."
            ),
            (
                f"Availability loss remains the most recoverable component: a disciplined maintenance-response improvement could recover approximately {_fmt_num(recovery_mwh, 0, ' MWh')} over an equivalent period, while the residual technical loss still requires targeted field checks for soiling, string faults, MPPT detuning, or DC-side resistance."
            ),
        ],
        "kpis": [
            _kpi("Weather-corrected budget", _fmt_num(wf["weather_corrected"], 0, " MWh")),
            _kpi("Availability loss", _fmt_num(abs(wf["avail_loss"]), 0, " MWh"), "", "warning"),
            _kpi("Technical loss", _fmt_num(abs(wf["technical_loss"]), 0, " MWh"), "", "danger" if abs(wf["technical_loss"]) > abs(wf["avail_loss"]) else "warning"),
        ],
        "figures": [
            figure
            for figure in [
                _figure_block(
                    charts,
                    "waterfall",
                    "Energy Loss Waterfall",
                    "The waterfall converts the principal loss drivers into energy impact and recovery priority.",
                ),
                _figure_block(
                    charts,
                    "monthly_availability_loss",
                    "Monthly Availability Loss Breakdown",
                    "This view shows which months drove the availability deficit across the analysed period.",
                )
            ]
            if figure
        ],
        "tables": [
            _table_block(
                "Highest Energy-Recovery Opportunities",
                ["Priority", "Category", "Estimated loss", "Action"],
                [
                    {
                        "Priority": item["priority"],
                        "Category": item["category"],
                        "Estimated loss": _fmt_num(float(item.get("mwh_loss", 0.0)), 0, " MWh"),
                        "Action": item["action"],
                    }
                    for item in top_actions
                ],
            )
        ],
        "findings": [],
        "notes": [],
    }


def _targeted_diagnostics_page(analysis: dict, charts: dict) -> dict:
    start_stop_df = analysis["start_stop_df"]
    max_start = float(start_stop_df["start_dev"].abs().max()) if not start_stop_df.empty else np.nan
    max_stop = float(start_stop_df["stop_dev"].abs().max()) if not start_stop_df.empty else np.nan
    red_threshold = 15.0
    amber_threshold = 8.0
    flagged_red = sorted(
        {
            name
            for name, row in start_stop_df.iterrows()
            if abs(float(row["start_dev"])) > red_threshold or abs(float(row["stop_dev"])) > red_threshold
        }
    )
    flagged_amber = sorted(
        {
            name
            for name, row in start_stop_df.iterrows()
            if amber_threshold < max(abs(float(row["start_dev"])), abs(float(row["stop_dev"]))) <= red_threshold
        }
        - set(flagged_red)
    )

    commentary = [
        (
            f"Maximum fleet-relative startup deviation is {_fmt_num(max_start, 1, ' min')} and maximum stop deviation is {_fmt_num(max_stop, 1, ' min')}. "
            "Persistent late start / early stop signatures remain an efficient screen for non-harmonised inverter thresholds."
        )
    ]
    if max(max_start, max_stop) > 15:
        commentary.append(
            "Deviations beyond roughly 15 minutes are unlikely to be explained by noise alone and remain consistent with high startup voltage thresholds, wake-up sensitivity, or recurrent local trips."
        )
    else:
        commentary.append("Start/stop deviations are present but relatively contained, so they remain a secondary issue compared with the dominant availability and PR losses.")
    if flagged_red:
        commentary.append(
            f"Red-coded outliers above 15 minutes are {', '.join(flagged_red[:6])}{' and others' if len(flagged_red) > 6 else ''}; these units warrant configuration review before further hardware intervention."
        )
    elif flagged_amber:
        commentary.append(
            f"Amber-zone deviations between 8 and 15 minutes remain visible on {', '.join(flagged_amber[:6])}{' and others' if len(flagged_amber) > 6 else ''}; these units should be monitored for seasonal persistence."
        )

    return {
        "template": "section",
        "id": "targeted-diagnostics",
        "toc_group": "Technical Findings",
        "title": "Targeted Diagnostics",
        "kicker": "Threshold behaviour",
        "summary": (
            "Start and stop behaviour screening for threshold or wake-up anomalies."
        ),
        "commentary_title": "Interpretation",
        "commentary": commentary,
        "kpis": [],
        "figures": [
            figure
            for figure in [
                _figure_block(
                    charts,
                    "start_stop",
                    "Start And Stop Deviation",
                    "Start and stop deviations highlight threshold non-uniformity, wake-up sensitivity, and recurrent switching anomalies.",
                )
            ]
            if figure
        ],
        "tables": [],
        "findings": [],
        "notes": [],
    }


def _conclusion_page(analysis: dict) -> dict:
    annual = analysis["pr_res"]["annual"]
    avail_res = analysis["avail_res"]
    data_avail = analysis["data_avail"]
    wf = analysis["wf"]
    punchlist = analysis["punchlist"]
    top_actions = _top_actions(punchlist, limit=4)
    mean_pr = float(annual["PR"].mean()) if len(annual) else np.nan
    fleet_av = float(avail_res["mean"])

    commentary = [
        (
            f"The site closes the period at {_fmt_pct(mean_pr)} average PR and {_fmt_pct(fleet_av)} average availability. "
            "The dominant loss mechanisms remain operational rather than purely meteorological."
        ),
        (
            f"Whole-site events, low-performing inverters, and the waterfall all point toward recoverable energy rather than an irreducible weather effect. "
            f"Availability loss remains {_fmt_num(abs(wf['avail_loss']), 0, ' MWh')} and technical loss remains {_fmt_num(abs(wf['technical_loss']), 0, ' MWh')}."
        ),
        (
            f"Data quality remains adequate for engineering triage but not perfect: power completeness is {_fmt_pct(data_avail['overall_power'])} and irradiance completeness is {_fmt_pct(data_avail['irradiance'])}."
        ),
    ]

    findings = []
    for item in top_actions:
        findings.append(
            {
                "title": item["category"],
                "severity": _severity(item["priority"]),
                "body": f"{item['issue']} Recommended action: {item['action']}",
            }
        )
    if not findings:
        findings.append(
            {
                "title": "No critical actions",
                "severity": "success",
                "body": "No high-priority corrective action was generated by the current thresholds.",
            }
        )

    return {
        "template": "section",
        "id": "conclusions",
        "toc_group": "Close-out",
        "title": "Conclusions And Recommendations",
        "kicker": "Synthesis",
        "summary": (
            "Consolidated technical conclusions and recommended next actions."
        ),
        "commentary_title": "Conclusion",
        "commentary": commentary,
        "kpis": [
            _kpi("Average PR", _fmt_pct(mean_pr), "Target >= 78%", _pr_status(mean_pr, 78)),
            _kpi("Fleet availability", _fmt_pct(fleet_av), "Target >= 95%", _status_from_threshold(fleet_av, 95)),
            _kpi("High-priority actions", str(sum(1 for item in punchlist if item["priority"] == "HIGH")), "", "danger" if any(item["priority"] == "HIGH" for item in punchlist) else "success"),
        ],
        "figures": [],
        "tables": [],
        "findings": findings,
        "notes": [],
    }


def _appendix_mttf_overview_page(analysis: dict, charts: dict) -> dict:
    mttf_res = analysis["mttf_res"]
    finite = [row["mttf_days"] for row in mttf_res.values() if np.isfinite(row["mttf_days"]) and row["n_failures"] > 0]
    fleet_mttf = float(np.nanmean(finite)) if finite else np.nan
    ranked = sorted(
        [(name, row["n_failures"], row["mttf_days"]) for name, row in mttf_res.items()],
        key=lambda item: item[1],
        reverse=True,
    )
    worst_faults = [item for item in ranked if item[1] > 0][:3]
    high_fault = sum(1 for _, faults, _ in ranked if faults > 100)
    med_fault = sum(1 for _, faults, _ in ranked if 30 < faults <= 100)

    commentary = [
        f"Fleet mean MTTF is {_fmt_num(fleet_mttf, 1, ' days')} against the 90-day reliability benchmark used for maintenance screening. {high_fault} inverter(s) exceed 100 fault events and {med_fault} more sit in the 30–100 fault range.",
    ]
    if worst_faults:
        commentary.append(
            "The highest recurring-fault units are "
            + ", ".join(f"{name} ({faults} faults, MTTF={days:.1f} d)" for name, faults, days in worst_faults if np.isfinite(days))
            + "."
        )
    commentary.append(
        "The ranking charts screen recurrence severity, while the following detail table preserves the all-inverter traceability needed for maintenance planning."
    )

    return {
        "template": "appendix",
        "id": "appendix-mttf-overview",
        "toc_group": "Appendix",
        "title": "Appendix - Reliability Overview",
        "summary": "Fleet-wide MTTF and failure-count diagnostics for maintenance planning.",
        "commentary_title": "Reliability interpretation",
        "commentary": commentary,
        "figures": [
            figure
            for figure in [
                _figure_block(
                    charts,
                    "mttf_failures",
                    "Failure Count Ranking",
                    "Highest fault-event counts identify the units requiring immediate root-cause review.",
                    width="half",
                ),
                _figure_block(
                    charts,
                    "mttf_days",
                    "Lowest Mean Time To Failure",
                    "MTTF highlights the units with the fastest recurrence rate, not just the largest lifetime count.",
                    width="half",
                ),
            ]
            if figure
        ],
        "tables": [],
        "findings": [],
        "notes": [
            "SCADA confirms recurrence patterns but cannot identify exact trip modes without OEM alarm and fault-code exports.",
        ],
    }


def _appendix_mttf_detail_page(analysis: dict) -> dict:
    mttf_res = analysis["mttf_res"]
    rows = []
    for name in sorted(mttf_res, key=lambda inv: [int(part) if part.isdigit() else part for part in inv.replace(".", " ").split()]):
        row = mttf_res[name]
        faults = int(row.get("n_failures", 0))
        status = "Critical" if faults > 100 else "Warning" if faults > 30 else "Normal"
        rows.append(
            {
                "Inverter": name,
                "Faults": str(faults),
                "Run hrs": _fmt_num(row.get("running_hours"), 0, " h"),
                "MTTF (d)": _fmt_num(row.get("mttf_days"), 1),
                "MTTF (h)": _fmt_num(row.get("mttf_hours"), 0),
                "Status": status,
                "_row_class": "row-danger" if status == "Critical" else "row-warning" if status == "Warning" else "row-success",
            }
        )

    return {
        "template": "appendix",
        "id": "appendix-mttf-detail",
        "toc_group": "Appendix",
        "title": "Appendix - MTTF Detail - All Inverters",
        "summary": "All-inverter reliability detail retained for engineering traceability.",
        "tables": [
            _table_block(
                "MTTF Detail - All Inverters",
                ["Inverter", "Faults", "Run hrs", "MTTF (d)", "MTTF (h)", "Status"],
                rows,
                "Critical = more than 100 fault events over the analysed period; Warning = 31 to 100 events.",
                appendix_only=True,
            )
        ],
        "findings": [],
    }


def _weather_correlation_appendix_page(charts: dict) -> dict | None:
    figure = _figure_block(
        charts,
        "weather_correlation",
        "PR Vs Temperature And Rainfall",
        "Monthly PR is compared against rainfall and temperature, alongside a daily temperature-coloured PR view.",
    )
    if not figure:
        return None
    return {
        "template": "appendix",
        "id": "weather-correlation-appendix",
        "toc_group": "Appendix",
        "paginate": False,
        "title": "Appendix - Weather Correlation",
        "summary": "Secondary weather-context diagnostics retained in appendix to preserve readability of the main narrative.",
        "commentary_title": "Weather-context interpretation",
        "commentary": [],
        "figures": [figure],
        "tables": [],
        "findings": [],
        "notes": [],
    }


def _appendix_clipping_page(config: dict, analysis: dict, charts: dict) -> dict:
    piv = analysis["piv"]
    irr = analysis["irr_data"]
    cap_kw = config["cap_ac_kw"]
    site_pwr = piv.sum(axis=1, min_count=1)
    ghi_s = irr.set_index("ts")["GHI"].reindex(site_pwr.index)
    valid = (ghi_s > config["irr_threshold"]) & site_pwr.notna() & ghi_s.notna()
    near_site = valid & (site_pwr >= 0.97 * cap_kw)
    near_pct = 100.0 * near_site.sum() / max(valid.sum(), 1)
    return {
        "template": "appendix",
        "id": "appendix-clipping",
        "toc_group": "Appendix",
        "paginate": False,
        "title": "Appendix - Clipping Analysis",
        "summary": "Near-clipping diagnostics for inverter loading review.",
        "commentary_title": "Clipping interpretation",
        "commentary": [
            f"Near-clipping occurs on {_fmt_pct(near_pct, 1)} of valid daytime intervals at the site level, which is useful for screening possible AC-ceiling exposure during high-irradiance periods.",
        ],
        "figures": [
            figure
            for figure in [
                _figure_block(
                    charts,
                    "clipping",
                    "Clipping Diagnostics",
                    "Power-distribution, irradiance-bin, and top-inverter views screen where near-ceiling operation is concentrated.",
                )
            ]
            if figure
        ],
        "tables": [],
        "findings": [],
    }


def _action_punchlist_page(analysis: dict) -> dict:
    tariff_eur_per_kwh = 0.09
    rows = []
    for item in sorted(analysis["punchlist"], key=lambda row: ({"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(row["priority"], 3), -float(row.get("mwh_loss", 0.0)))):
        priority = item["priority"]
        mwh_loss = float(item.get("mwh_loss", 0.0))
        rows.append(
            {
                "Priority": priority,
                "Category": item["category"],
                "Estimated loss": _fmt_num(mwh_loss, 0, " MWh"),
                "Estimated loss (EUR)": _fmt_num(mwh_loss * 1000.0 * tariff_eur_per_kwh, 0, " EUR"),
                "Issue": item["issue"],
                "Recommended action": item["action"],
                "_row_class": "row-danger" if priority == "HIGH" else "row-warning" if priority == "MEDIUM" else "row-success",
            }
        )
    return {
        "template": "section",
        "id": "action-punchlist",
        "toc_group": "Close-out",
        "title": "Action Punchlist",
        "kicker": "Corrective-action register",
        "summary": "Full action register for maintenance planning and client follow-up.",
        "commentary_title": "Action register summary",
        "commentary": [
            f"The punchlist contains {len(rows)} actions ranked by priority and estimated energy impact. High-priority items should be treated as the first corrective phase; medium-priority items remain relevant once the dominant downtime and PR losses are stabilised.",
        ],
        "kpis": [],
        "figures": [],
        "tables": [
            _table_block(
                "Full Action Punchlist",
                ["Priority", "Category", "Estimated loss", "Estimated loss (EUR)", "Issue", "Recommended action"],
                rows,
            )
        ],
        "findings": [],
        "notes": [],
    }


def _appendix_pages(config: dict, preflight: dict, analysis: dict, charts: dict) -> list[dict]:
    top_actions = _top_actions(analysis["punchlist"], limit=5)
    weather_page = _weather_correlation_appendix_page(charts)
    performed_rows = [
        {"Activity": "Data availability assessment", "Status": "Completed", "Notes": "Per-inverter and site-level telemetry completeness reviewed.", "_row_class": "row-success"},
        {"Activity": "Performance ratio assessment", "Status": "Completed", "Notes": "Monthly and annual PR calculated on the IEC 61724 DC-kWp basis.", "_row_class": "row-success"},
        {"Activity": "Irradiance coherence (SARAH-3)", "Status": "Completed", "Notes": "On-site irradiance cross-checked against SARAH reference, including bias and suspect-reading screening.", "_row_class": "row-success"},
        {"Activity": "Availability and reliability review", "Status": "Completed", "Notes": "Fleet uptime, inverter-level availability, and fault recurrence screened.", "_row_class": "row-success"},
        {"Activity": "Loss attribution", "Status": "Completed", "Notes": "Budget, weather correction, availability loss, technical loss, and residual reviewed.", "_row_class": "row-success"},
        {"Activity": "Per-inverter specific yield", "Status": "Completed", "Notes": "Monthly inverter heatmaps reviewed for recurring underperformance patterns.", "_row_class": "row-success"},
        {"Activity": "Start/stop signature screening", "Status": "Completed", "Notes": "Fleet-relative wake-up and shut-down timing deviations screened for threshold anomalies.", "_row_class": "row-success"},
        {"Activity": "Weather-correlation review", "Status": "Completed", "Notes": "Rainfall and temperature context considered in the diagnostic workflow.", "_row_class": "row-success"},
    ]
    limitation_rows = [
        {"Analysis": "Inverter AC/DC efficiency", "Status": "Not possible", "Notes": "No DC current or DC power channels are available in the export.", "_row_class": "row-danger"},
        {"Analysis": "String-level fault detection", "Status": "Not possible", "Notes": "The SCADA extract is limited to inverter-level AC production.", "_row_class": "row-danger"},
        {"Analysis": "Short transients", "Status": "Limited", "Notes": "The 10-minute sampling interval is too coarse for sub-interval fault isolation.", "_row_class": "row-warning"},
        {"Analysis": "Downtime root cause", "Status": "Limited", "Notes": "Alarm and fault-code channels are absent, so trips are classified indirectly.", "_row_class": "row-warning"},
        {"Analysis": "Curtailment certainty", "Status": "Limited", "Notes": "Without explicit export-limit flags, curtailment remains heuristic.", "_row_class": "row-warning"},
        {"Analysis": "Degradation certainty", "Status": "Limited", "Notes": "The available time horizon remains too short for a statistically robust long-term degradation estimate.", "_row_class": "row-warning"},
        {"Analysis": "Soiling quantification", "Status": "Not possible", "Notes": "No dedicated soiling sensor or IV-curve dataset is available to isolate accumulation rates.", "_row_class": "row-danger"},
    ]
    return [
        _appendix_mttf_detail_page(analysis),
        _appendix_clipping_page(config, analysis, charts),
        *([weather_page] if weather_page else []),
        {
            "template": "appendix",
            "id": "appendix-limitations",
            "toc_group": "Appendix",
            "title": "Appendix - Analytical Scope And Data Limitations",
            "summary": (
                "Summary of the analytical scope completed for this assessment and the principal data constraints affecting interpretation."
            ),
            "tables": [
                _table_block("Analytical Scope Completed", ["Activity", "Status", "Notes"], performed_rows, appendix_only=True),
                _table_block("Analytical Constraints", ["Analysis", "Status", "Notes"], limitation_rows, appendix_only=True),
                _table_block(
                    "Priority Action Snapshot",
                    ["Priority", "Category", "Estimated loss", "Recommended action"],
                    [
                        {
                            "Priority": item["priority"],
                            "Category": item["category"],
                            "Estimated loss": _fmt_num(float(item.get("mwh_loss", 0.0)), 0, " MWh"),
                            "Recommended action": item["action"],
                        }
                        for item in top_actions
                    ],
                    appendix_only=True,
                ),
            ],
            "findings": [],
        }
    ]


def build_report_data(*, config: dict, analysis: dict, charts: dict, outputs: dict, preflight: dict) -> dict:
    generated_at = config.get("generated_at") or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    cover_image = config.get("cover_image_path")
    cover_image_uri = Path(cover_image).as_uri() if cover_image and Path(cover_image).exists() else None

    report = {
        "document": {
            "report_title": config["report_title"],
            "site_name": config["site_name"],
            "generated_at": generated_at,
            "data_dir": str(config["data_dir"]),
            "output_dir": str(config["output_dir"]),
            "output_format": outputs["output_format"],
            "company": "8.2 Advisory | A Dolfines Company",
            "logo_white": Path(config["logo_white"]).as_uri(),
            "logo_color": Path(config["logo_color"]).as_uri(),
            "favicon": Path(config["favicon"]).as_uri(),
            "cover_image": cover_image_uri,
            "debug_layout": preflight["debug_layout"],
            "tokens": config["style_tokens"],
            "preflight": preflight,
        },
        "pages": [],
    }

    pages = [
        _cover_page(config, analysis, generated_at),
        {"template": "toc", "title": "Table of Contents"},
        _executive_summary_page(config, analysis, charts),
        _performance_kpi_dashboard_page(config, analysis),
        _site_overview_page(config, analysis, charts),
        _technical_parameters_page(config),
        _data_quality_page(analysis, charts),
        _data_quality_detail_page(analysis, charts),
        _performance_page(config, analysis, charts),
        _inverter_performance_page(analysis, charts),
        _specific_yield_page(analysis, charts),
        _availability_reliability_page(analysis, charts),
        _losses_page(analysis, charts),
        _targeted_diagnostics_page(analysis, charts),
        _conclusion_page(analysis),
        _action_punchlist_page(analysis),
    ]
    pages = [page for page in pages if page]
    pages[8:8] = _irradiance_coherence_pages(analysis, charts)
    pages.extend(_appendix_pages(config, preflight, analysis, charts))
    expanded_pages: list[dict] = []
    for page in pages:
        expanded_pages.extend(_paginate_section_like_page(page))
    pages = expanded_pages

    toc_groups: list[dict] = []
    group_index: dict[str, dict] = {}
    for page in pages:
        if page["template"] in {"cover", "toc"} or page.get("toc_hide"):
            continue
        entry = {"title": page.get("title", ""), "template": page["template"]}
        group_name = page.get("toc_group", "Report")
        if group_name not in group_index:
            group_index[group_name] = {"title": group_name, "entries": []}
            toc_groups.append(group_index[group_name])
        group_index[group_name]["entries"].append(entry)

    pages[1]["groups"] = toc_groups
    report["pages"] = pages
    return report


def _performance_page(config: dict, analysis: dict, charts: dict) -> dict:
    annual = analysis["pr_res"]["annual"]
    monthly = analysis["pr_res"]["monthly"]
    rows = []
    for year, row in annual.iterrows():
        gap_pct = max(0.0, 78.0 - float(row["PR"]))
        rows.append(
            {
                "Year": str(year),
                "PR": _fmt_pct(float(row["PR"])),
                "Actual energy": _fmt_num(float(row["E_act"] / 1000.0), 0, " MWh"),
                "Reference energy": _fmt_num(float(row["E_ref"] / 1000.0), 0, " MWh"),
                "Gap to 78%": _fmt_num(gap_pct, 1, " pp"),
            }
        )

    commentary = []
    years = list(annual.index)
    if len(years) >= 2:
        pr_drop = float(annual.loc[years[0], "PR"] - annual.loc[years[-1], "PR"])
        irr_drop = float(annual.loc[years[0], "irrad"] - annual.loc[years[-1], "irrad"])
        commentary.append(
            (
                f"Year-on-year PR moved from {annual.loc[years[0], 'PR']:.1f}% to {annual.loc[years[-1], 'PR']:.1f}%, "
                f"while annual irradiation shifted by {irr_drop:.0f} kWh/m². "
                + (
                    "The PR decline is larger than the irradiation shift alone would justify, which confirms an operational loss mechanism."
                    if pr_drop > 5
                    else "The PR movement is broadly aligned with the irradiation change, so weather remains a major driver of variance."
                )
            )
        )

    critical_months = int((monthly["PR"] < 65).sum()) if len(monthly) else 0
    warning_months = int(((monthly["PR"] >= 65) & (monthly["PR"] < 75)).sum()) if len(monthly) else 0
    spec_yield = float(annual["E_act"].sum() / max(config["cap_dc_kwp"], 1) / max(len(annual), 1))
    commentary.append(
        (
            f"Average specific yield is {_fmt_num(spec_yield, 0, ' kWh/kWp/yr')}. "
            f"The period contains {critical_months} month(s) below the 65% critical threshold and {warning_months} month(s) between 65% and 78%."
        )
    )
    commentary.append(
        "If summer PR remains weak while irradiation peaks, weather alone is not the cause; soiling accumulation, latent downtime, or inverter quality losses become the leading hypotheses."
    )

    return {
        "template": "section",
        "id": "performance-overview",
        "toc_group": "Technical Findings",
        "title": "Performance Overview",
        "kicker": "Energy and PR",
        "summary": (
            "Monthly and annual PR trends benchmark energy delivery against the weather-adjusted site reference."
        ),
        "commentary_title": "Performance interpretation",
        "commentary": commentary,
        "kpis": [
            _kpi("Design PR", _fmt_pct(config["design_pr"] * 100)),
            _kpi("Average annual PR", _fmt_pct(float(annual["PR"].mean()) if len(annual) else np.nan), "Target >= 78%", _pr_status(float(annual["PR"].mean()) if len(annual) else np.nan, 78)),
        ],
        "figures": [
            figure
            for figure in [
                _figure_block(
                    charts,
                    "monthly_pr_energy",
                    "Monthly Energy, Irradiation And PR",
                    "Energy bars (left), irradiation line (right, green dashes) and PR line (right, orange) are overlaid to separate weather-driven output variation from operational underperformance.",
                    width="full",
                ),
                _figure_block(
                    charts,
                    "daily_specific_yield",
                    "Daily Specific Yield And 30-day Rolling Mean",
                    "The daily-yield view highlights sustained low-output windows that monthly averages alone can hide.",
                    width="full",
                )
            ]
            if figure
        ],
        "tables": [],
        "findings": [],
        "notes": [],
    }


def _inverter_performance_page(analysis: dict, charts: dict) -> dict:
    pr_map = analysis["pr_res"]["per_inverter"]
    avail_map = analysis["avail_res"]["per_inverter"]
    inv_rows = []
    for name in sorted(pr_map):
        inv_rows.append(
            {
                "Inverter": name,
                "PR": _fmt_pct(pr_map[name]),
                "Availability": _fmt_pct(avail_map.get(name, np.nan)),
            }
        )
    worst_rows = sorted(inv_rows, key=lambda row: float(row["PR"].rstrip("%")) if row["PR"] != "n/a" else 999.0)[:8]

    pr_values = np.array([value for value in pr_map.values() if np.isfinite(value)], dtype=float)
    fleet_mean = float(np.nanmean(pr_values)) if len(pr_values) else np.nan
    fleet_std = float(np.nanstd(pr_values)) if len(pr_values) else np.nan
    low_both = [
        name
        for name, pr_value in pr_map.items()
        if np.isfinite(pr_value)
        and np.isfinite(avail_map.get(name, np.nan))
        and pr_value < fleet_mean - fleet_std
        and avail_map.get(name, np.nan) < 95
    ]
    low_pr_good_av = [
        name
        for name, pr_value in pr_map.items()
        if np.isfinite(pr_value)
        and np.isfinite(avail_map.get(name, np.nan))
        and pr_value < fleet_mean - fleet_std
        and avail_map.get(name, np.nan) >= 95
    ]

    return {
        "template": "section",
        "id": "inverter-performance",
        "toc_group": "Technical Findings",
        "paginate": False,
        "title": "Fleet Inverter Comparison",
        "kicker": "Inverter-level spread",
        "summary": (
            "Inverter fleet comparison between performance and availability."
        ),
        "commentary_title": "Interpretation",
        "commentary": [
            (
                f"Fleet mean inverter PR is {_fmt_pct(fleet_mean)} with a standard deviation of {_fmt_num(fleet_std, 1, ' pp')}. "
                f"{len(low_both)} inverter(s) sit in the low-PR / low-availability quadrant, where uptime recovery is the first lever. "
                f"{len(low_pr_good_av)} inverter(s) have low PR despite acceptable availability, which points instead toward soiling, string issues, or MPPT behaviour."
            ),
        ],
        "kpis": [
            _kpi("Fleet mean PR", _fmt_pct(fleet_mean)),
            _kpi("Low PR + low availability", str(len(low_both)), "", "warning" if low_both else "success"),
            _kpi("Low PR + good availability", str(len(low_pr_good_av)), "", "warning" if low_pr_good_av else "success"),
        ],
        "figures": [
            figure
            for figure in [
                _figure_block(
                    charts,
                    "inverter_pr_vs_availability",
                    "PR Versus Availability",
                    "The scatter separates downtime-driven losses from running underperformance across the fleet.",
                )
            ]
            if figure
        ],
        "tables": [_table_block("Lowest PR Inverters", ["Inverter", "PR", "Availability"], worst_rows[:3])],
        "findings": [],
        "notes": [],
    }


def _specific_yield_page(analysis: dict, charts: dict) -> dict:
    pr_map = analysis["pr_res"]["per_inverter"]
    inv_sy_df = analysis["inv_sy_df"]
    fleet_mean = float(np.nanmean(list(pr_map.values()))) if pr_map else np.nan
    low_pr_names = [name for name, value in sorted(pr_map.items(), key=lambda item: item[1])[:3]]
    dev_pct = inv_sy_df.subtract(inv_sy_df.mean(axis=1), axis=0).divide(inv_sy_df.mean(axis=1).clip(lower=1), axis=0) * 100
    worst_dev = dev_pct.abs().max().sort_values(ascending=False).head(3)

    commentary = [
        (
            "Persistent red months indicate an inverter was running but underperforming relative to its peers, not merely offline."
        ),
        (
            f"The fleet mean PR is {_fmt_pct(fleet_mean)}. The three lowest average PR inverters are {', '.join(low_pr_names) if low_pr_names else 'n/a'}."
        ),
    ]
    if len(worst_dev):
        commentary.append(
            "Largest month-level deviations from fleet behaviour occur on "
            + ", ".join(f"{name} ({value:.1f}%)" for name, value in worst_dev.items())
            + ". Summer-only degradation that recovers after rain remains consistent with soiling; persistent cross-season impairment suggests structural electrical loss."
        )

    return {
        "template": "section",
        "id": "specific-yield",
        "toc_group": "Technical Findings",
        "title": "Per-Inverter Specific Yield",
        "kicker": "Quality-loss screening",
        "summary": (
            "Monthly heatmaps highlighting persistent inverter underperformance and peer-relative quality loss."
        ),
        "commentary_title": "Interpretation",
        "commentary": commentary,
        "kpis": [],
        "figures": [
            figure
            for figure in [
                _figure_block(
                    charts,
                    "specific_yield_heatmap",
                    "Specific Yield And PR Heatmaps",
                    "The top view separates peer-relative yield quality; the bottom view keeps downtime inside PR so both mechanisms remain visible.",
                )
            ]
            if figure
        ],
        "tables": [],
        "findings": [],
        "notes": [],
    }


def _availability_reliability_page(analysis: dict, charts: dict) -> dict:
    avail_res = analysis["avail_res"]
    mttf_res = analysis["mttf_res"]
    worst_av = sorted(avail_res["per_inverter"].items(), key=lambda item: item[1])[:3]
    fault_counts = sorted(mttf_res.items(), key=lambda item: item[1]["n_failures"], reverse=True)[:5]
    finite_mttf = [row["mttf_days"] for row in mttf_res.values() if np.isfinite(row["mttf_days"]) and row["n_failures"] > 0]
    fleet_mttf = float(np.nanmean(finite_mttf)) if finite_mttf else np.nan

    commentary = [
        (
            f"Fleet mean availability is {_fmt_pct(avail_res['mean'])}, with {sum(1 for _, value in avail_res['per_inverter'].items() if value < 95)} inverter(s) below the 95% threshold."
        ),
        (
            f"{avail_res['whole_site_events']} whole-site simultaneous outage event(s) were detected. Mean time to failure across inverters with recorded faults is {_fmt_num(fleet_mttf, 1, ' days')}."
        ),
        (
            "Common Sungrow SG250HX trip families remain consistent with grid-voltage disturbances, insulation alarms, AC contactor wear, and low-irradiance startup sensitivity. Without inverter alarm logs, SCADA can confirm the recurrence pattern but not the root cause classification."
        ),
    ]

    return {
        "template": "section",
        "id": "availability-reliability",
        "toc_group": "Technical Findings",
        "paginate": False,
        "title": "Availability And Reliability",
        "kicker": "Uptime and fault recurrence",
        "summary": ("Fleet uptime, grid-event exposure, and reliability screening."),
        "commentary_title": "Interpretation",
        "commentary": [
            (
                f"Fleet mean availability is {_fmt_pct(avail_res['mean'])}, with {sum(1 for _, value in avail_res['per_inverter'].items() if value < 95)} inverter(s) below the 95% threshold and {avail_res['whole_site_events']} whole-site simultaneous outage event(s) detected. "
                f"Mean time to failure across inverters with recorded faults is {_fmt_num(fleet_mttf, 1, ' days')}. Common Sungrow SG250HX trip families remain consistent with grid-voltage disturbances, insulation alarms, AC contactor wear, and low-irradiance startup sensitivity, although SCADA alone cannot confirm the exact alarm class."
            )
        ],
        "kpis": [
            _kpi("Fleet availability", _fmt_pct(avail_res["mean"]), "Target >= 95%", _status_from_threshold(avail_res["mean"], 95)),
            _kpi("Fleet mean MTTF", _fmt_num(fleet_mttf, 1, " days"), "Target >= 90 days", _status_from_threshold(fleet_mttf, 90)),
        ],
        "figures": [
            figure
            for figure in [
                _figure_block(
                    charts,
                    "availability_trend",
                    "Monthly Site Availability",
                    "Monthly availability shows whether the loss exposure is persistent or concentrated into a small number of events.",
                ),
            ]
            if figure
        ],
        "tables": [
            _table_block(
                "Lowest Availability / Highest Failure Units",
                ["Metric", "Value"],
                [
                    {"Metric": "Worst availability units", "Value": ", ".join(f"{name} ({value:.1f}%)" for name, value in worst_av) if worst_av else "n/a"},
                    {"Metric": "Top failure counts", "Value": ", ".join(f"{name} ({metrics['n_failures']} faults)" for name, metrics in fault_counts) if fault_counts else "n/a"},
                ],
            )
        ],
        "findings": [],
        "notes": [],
    }
