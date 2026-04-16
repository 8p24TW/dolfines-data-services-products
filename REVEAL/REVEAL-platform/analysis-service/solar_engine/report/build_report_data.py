from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Callable

import numpy as np

from report.i18n import get_translator

# Module-level translator — overridden by build_report_data(lang=...) at runtime
_T: Callable[..., str] = get_translator("en")


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


_TARIFF_EUR_KWH = 0.09  # €/kWh — used for all EUR loss calculations


def _eur_priority(mwh_loss: float) -> tuple[str, str]:
    """Return (priority_label, css_row_class) based on EUR loss at the standard tariff."""
    eur = float(mwh_loss) * 1000.0 * _TARIFF_EUR_KWH
    if eur >= 1000:
        return "HIGH", "row-danger"
    return "MEDIUM", "row-warning"


def _status_from_threshold(value: float | int | None, threshold: float, reverse: bool = False) -> str:
    if value is None or not np.isfinite(value):
        return "neutral"
    if reverse:
        return "success" if value <= threshold else "warning"
    return "success" if value >= threshold else "warning"


def _pr_status(value: float | int | None, target: float = 79.0) -> str:
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
    if any(key in title for key in {"technical configuration", "full action punchlist", "mttf detail - all inverters", "technology risk register"}):
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
    if page.get("id") in {"executive-summary", "site-overview"}:
        return 8
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
        "subtitle": _T("cover.subtitle"),
        "metadata": [
            (_T("cover.metadata.project"), config["site_name"]),
            (_T("cover.metadata.asset"), f"{config['cap_dc_kwp']:,.0f} kWp DC / {config['cap_ac_kw']:,.0f} kW AC"),
            (_T("cover.metadata.analysis_period"), f"{first_ts:%d %b %Y} to {last_ts:%d %b %Y}"),
            (_T("cover.metadata.technology"), f"{config['inv_model']} and {config['module_brand']} {module_wp:.0f}Wp"),
            (_T("cover.metadata.issued"), generated_at),
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
    high_actions = sum(1 for item in punchlist if _eur_priority(item.get("mwh_loss", 0))[0] == "HIGH")
    medium_actions = sum(1 for item in punchlist if _eur_priority(item.get("mwh_loss", 0))[0] == "MEDIUM")
    low_pr_units = sorted(pr_map.items(), key=lambda item: item[1])[:2]
    worst_label = ", ".join(f"{name} ({value:.1f}%)" for name, value in low_pr_units) if low_pr_units else "No clear outlier"
    irr_ok = all(metrics["correlation"] > 0.95 and metrics["suspect_pct"] < 5 for metrics in irr_coh.values()) if irr_coh else False
    pr_target = 79.0
    critical_months = int((monthly["PR"] < 65).sum()) if len(monthly) else 0
    alert_months = int(((monthly["PR"] >= 65) & (monthly["PR"] < pr_target)).sum()) if len(monthly) else 0

    # ── Recoverable loss financials (€90/MWh = €0.09/kWh) ───────────────
    TARIFF = _TARIFF_EUR_KWH * 1000.0  # €/MWh
    n_years = max(len(annual), 1)
    avail_loss_mwh  = abs(float(wf.get("avail_loss", 0.0)))
    tech_loss_mwh   = abs(float(wf.get("technical_loss", 0.0)))
    total_recov_ann = (avail_loss_mwh + tech_loss_mwh) / n_years
    avail_loss_eur  = avail_loss_mwh  / n_years * TARIFF
    tech_loss_eur   = tech_loss_mwh   / n_years * TARIFF
    total_recov_eur = total_recov_ann * TARIFF

    _data_qual_good = data_avail["overall_power"] >= 95 and data_avail["irradiance"] >= 95 and irr_ok
    return {
        "template": "section",
        "id": "executive-summary",
        "toc_group": "Overview",
        "findings_first": True,
        "title": _T("exec.title"),
        "kicker": _T("exec.kicker"),
        "summary": _T("exec.summary"),
        "commentary_title": _T("exec.commentary_title"),
        "commentary": [
            _T("exec.commentary.performance",
               mean_pr=_fmt_pct(mean_pr), last_pr=_fmt_pct(last_pr),
               total_energy_mwh=_fmt_num(total_energy_mwh, 0, " MWh")),
            _T("exec.commentary.availability.good",
               avail_pct=_fmt_pct(avail_res["mean"]),
               outage_count=avail_res["whole_site_events"]),
            _T("exec.commentary.data_quality.good" if _data_qual_good else "exec.commentary.data_quality.poor",
               power_pct=_fmt_pct(data_avail["overall_power"]),
               irr_pct=_fmt_pct(data_avail["irradiance"])),
            _T("exec.commentary.critical_months",
               critical_months=critical_months, alert_months=alert_months, pr_target=f"{pr_target:.0f}"),
            _T("exec.commentary.recoverable_losses",
               total_eur=f"{total_recov_eur:,.0f}", avail_eur=f"{avail_loss_eur:,.0f}",
               tech_eur=f"{tech_loss_eur:,.0f}", tariff=f"{TARIFF:.0f}", n_years=n_years),
        ],
        "kpis": [
            _kpi(_T("exec.kpi.avg_pr.label"), _fmt_pct(mean_pr),
                 _T("exec.kpi.avg_pr.target", target=f"{pr_target:.0f}"), _pr_status(mean_pr, pr_target)),
            _kpi(_T("exec.kpi.fleet_av.label"), _fmt_pct(avail_res["mean"]),
                 _T("exec.kpi.fleet_av.target"), _status_from_threshold(avail_res["mean"], 95)),
            _kpi(_T("exec.kpi.energy.label"), _fmt_num(total_energy_mwh, 0, " MWh")),
            _kpi(_T("exec.kpi.actions.label"),
                 f"{high_actions} high / <span style='color:var(--color-warning)'>{medium_actions} medium</span>",
                 "", "danger" if high_actions else "warning" if medium_actions else "success"),
            _kpi(_T("exec.kpi.losses.label"), f"\u20ac{total_recov_eur:,.0f} /yr",
                 _T("exec.kpi.losses.target", avail_eur=f"{avail_loss_eur:,.0f}", tech_eur=f"{tech_loss_eur:,.0f}"),
                 "danger" if total_recov_eur > 50_000 else "warning"),
        ],
        "figures": [],
        "tables": [
            _table_block(
                _T("exec.table.top_actions.title"),
                [_T("exec.table.top_actions.col.priority"), _T("exec.table.top_actions.col.category"),
                 _T("exec.table.top_actions.col.loss_mwh"), _T("exec.table.top_actions.col.loss_eur"),
                 _T("exec.table.top_actions.col.action")],
                [
                    {
                        _T("exec.table.top_actions.col.priority"): _eur_priority(item.get("mwh_loss", 0))[0],
                        _T("exec.table.top_actions.col.category"): item["category"],
                        _T("exec.table.top_actions.col.loss_mwh"): _fmt_num(float(item.get("mwh_loss", 0.0)), 0, " MWh"),
                        _T("exec.table.top_actions.col.loss_eur"): _fmt_num(float(item.get("mwh_loss", 0.0)) * 1000.0 * _TARIFF_EUR_KWH, 0, ""),
                        _T("exec.table.top_actions.col.action"): item["action"],
                        "_row_class": _eur_priority(item.get("mwh_loss", 0))[1],
                    }
                    for item in _top_actions(punchlist, limit=3)
                ],
                "",
            )
        ],
        "findings": [
            {
                "title": _T("exec.finding.underperformance.title"),
                "severity": "warning" if mean_pr < pr_target else "success",
                "body": _T(
                    "exec.finding.underperformance.body.below" if mean_pr < pr_target
                    else "exec.finding.underperformance.body.on_target",
                    pr_target=f"{pr_target:.0f}",
                ),
            },
            {
                "title": _T("exec.finding.data_confidence.title"),
                "severity": "warning" if not _data_qual_good else "success",
                "body": _T("exec.finding.data_confidence.body.coherent" if irr_ok
                            else "exec.finding.data_confidence.body.review"),
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
        _T("site_overview.figure.map.title"),
        _T("site_overview.figure.map.caption"),
        width="full",
    )
    return {
        "template": "section",
        "id": "site-overview",
        "toc_group": "Overview",
        "title": _T("site_overview.title"),
        "kicker": _T("site_overview.kicker"),
        "summary": _T("site_overview.summary"),
        "commentary_title": _T("site_overview.commentary_title"),
        "commentary": [
            _T("site_overview.commentary.asset",
               site_name=config["site_name"],
               dc_kwp=f"{config['cap_dc_kwp']:,.0f}",
               ac_kw=f"{config['cap_ac_kw']:,.0f}",
               n_inverters=config["n_inverters"],
               inv_model=config["inv_model"],
               n_modules=f"{config['n_modules']:,}",
               module_brand=config["module_brand"]),
            _T("site_overview.commentary.method",
               month_count=month_count,
               interval_min=config["interval_min"]),
        ],
        "kpis": [
            _kpi(_T("site_overview.kpi.dc_ac.label"), _fmt_num(config["dc_ac_ratio"], 2)),
            _kpi(_T("site_overview.kpi.interval.label"), _T("site_overview.kpi.interval.value", interval_min=config["interval_min"])),
            _kpi(_T("site_overview.kpi.modules.label"), _fmt_num(config["n_modules"], 0)),
            _kpi(_T("site_overview.kpi.inverters.label"), _fmt_num(config["n_inverters"], 0)),
        ],
        "figures": [fig for fig in [map_figure] if fig],
        "tables": [
            _table_block(
                _T("site_overview.table.annual.title"),
                [_T("site_overview.table.annual.col.year"), _T("site_overview.table.annual.col.pr"),
                 _T("site_overview.table.annual.col.energy"), _T("site_overview.table.annual.col.irradiation")],
                annual_rows,
                _T("site_overview.table.annual.caption"),
            )
        ],
        "findings": [
            {
                "title": _T("site_overview.finding.benchmark.title"),
                "severity": "info",
                "body": _T("site_overview.finding.benchmark.body"),
            }
        ],
        "notes": [],
    }


def _technical_parameters_page(config: dict) -> dict:
    module_wp = config.get("module_wp") or round(config["cap_dc_kwp"] * 1000.0 / max(config["n_modules"], 1))
    _P = _T("tech_params.table.col.parameter")
    _V = _T("tech_params.table.col.value")
    spec_rows = [
        {_P: _T("tech_params.row.site_name"), _V: config["site_name"]},
        {_P: _T("tech_params.row.cod"), _V: "01/06/2022"},
        {_P: _T("tech_params.row.analysis_period"), _V: "2023 - 2024"},
        {_P: _T("tech_params.row.dc_capacity"), _V: f"{config['cap_dc_kwp']:.2f} kWp"},
        {_P: _T("tech_params.row.ac_capacity"), _V: f"{config['cap_ac_kw']:.0f} kW"},
        {_P: _T("tech_params.row.dc_ac_ratio"), _V: f"{config['dc_ac_ratio']:.2f}"},
        {_P: _T("tech_params.row.n_modules"), _V: f"{config['n_modules']:,}"},
        {_P: _T("tech_params.row.module_power"), _V: f"{module_wp:.0f} Wp"},
        {_P: _T("tech_params.row.module_brand"), _V: config["module_brand"]},
        {_P: _T("tech_params.row.module_temp_coeff"), _V: f"{config['temp_coeff'] * 100:.2f} %/\u00b0C"},
        {_P: _T("tech_params.row.n_inverters"), _V: f"{config['n_inverters']}"},
        {_P: _T("tech_params.row.inv_model"), _V: config["inv_model"]},
        {_P: _T("tech_params.row.inv_ac_power"), _V: _T("tech_params.row.inv_ac_power.each", value=f"{config['inv_ac_kw']:.0f}")},
        {_P: _T("tech_params.row.strings_per_inv"), _V: f"{config['n_strings_inv']}"},
        {_P: _T("tech_params.row.structure_types"), _V: config["structure_types"]},
        {_P: _T("tech_params.row.n_ptr"), _V: f"{config['n_ptr']}"},
        {_P: _T("tech_params.row.scada_interval"), _V: _T("tech_params.row.scada_interval.value", interval_min=config["interval_min"])},
        {_P: _T("tech_params.row.pr_method"), _V: _T("tech_params.row.pr_method.value")},
        {_P: _T("tech_params.row.budget_pr"), _V: f"{config['design_pr'] * 100:.0f}%"},
        {_P: _T("tech_params.row.irr_threshold"), _V: _T("tech_params.row.irr_threshold.value", irr_threshold=config["irr_threshold"])},
        {_P: _T("tech_params.row.ref_irradiance"), _V: _T("tech_params.row.ref_irradiance.value")},
    ]
    return {
        "template": "section",
        "id": "technical-parameters",
        "toc_group": "Overview",
        "title": _T("tech_params.title"),
        "kicker": _T("tech_params.kicker"),
        "summary": _T("tech_params.summary"),
        "commentary_title": _T("tech_params.commentary_title"),
        "commentary": [
            _T("tech_params.commentary",
               site_name=config["site_name"], n_inverters=config["n_inverters"],
               inv_model=config["inv_model"], n_modules=f"{config['n_modules']:,}",
               module_brand=config["module_brand"]),
        ],
        "kpis": [],
        "figures": [],
        "tables": [
            _table_block(
                _T("tech_params.table.title"),
                [_T("tech_params.table.col.parameter"), _T("tech_params.table.col.value")],
                spec_rows,
                _T("tech_params.table.caption"),
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
    pr_target = 79.0
    e_ref_total = float(annual["E_ref"].sum()) / 1000 if len(annual) else 0
    clean_pr = (total_energy + abs(wf.get("avail_loss", 0)) + abs(wf.get("technical_loss", 0))) / e_ref_total * 100 if e_ref_total > 0 else np.nan
    last_pr_status = _pr_status(last_pr, pr_target)
    all_pr_status = _pr_status(all_pr, pr_target)
    _M = _T("perf_kpi.table.col.metric")
    _V2 = _T("perf_kpi.table.col.value")
    _TG = _T("perf_kpi.table.col.target")
    _ST = _T("perf_kpi.table.col.status")
    _on = _T("perf_kpi.status.on_target")
    _watch = _T("perf_kpi.status.watch")
    _below = _T("perf_kpi.status.below_target")
    _ref = _T("perf_kpi.status.reference")
    _coh = _T("perf_kpi.status.coherent")
    _rev = _T("perf_kpi.status.review_required")
    _none_s = _T("perf_kpi.status.none")
    _open_s = _T("perf_kpi.status.open")
    _indic = _T("perf_kpi.status.indicative")
    _high_count = sum(1 for item in punchlist if _eur_priority(item.get("mwh_loss", 0))[0] == "HIGH")
    rows = [
        {_M: _T("perf_kpi.row.pr_year", year=last_year), _V2: _fmt_pct(last_pr),
         _TG: _T("perf_kpi.target.pr", target=f"{pr_target:.0f}"),
         _ST: _on if last_pr_status == "success" else _watch if last_pr_status == "warning" else _below,
         "_row_class": _status_row_class(last_pr_status)},
        {_M: _T("perf_kpi.row.pr_avg"), _V2: _fmt_pct(all_pr),
         _TG: _T("perf_kpi.target.pr", target=f"{pr_target:.0f}"),
         _ST: _on if all_pr_status == "success" else _watch if all_pr_status == "warning" else _below,
         "_row_class": _status_row_class(all_pr_status)},
        {_M: _T("perf_kpi.row.energy"), _V2: _fmt_num(total_energy, 0, " MWh"),
         _TG: _T("perf_kpi.target.dash"), _ST: _ref, "_row_class": "row-info"},
        {_M: _T("perf_kpi.row.specific_yield"), _V2: _fmt_num(specific_yield, 0, " kWh/kWp/yr"),
         _TG: _T("perf_kpi.target.dash"), _ST: _ref, "_row_class": "row-info"},
        {_M: _T("perf_kpi.row.availability"), _V2: _fmt_pct(avail_res["mean"]),
         _TG: _T("perf_kpi.target.gte95"),
         _ST: _on if avail_res["mean"] >= 95 else _below,
         "_row_class": "row-success" if avail_res["mean"] >= 95 else "row-warning"},
        {_M: _T("perf_kpi.row.power_completeness"), _V2: _fmt_pct(data_avail["overall_power"]),
         _TG: _T("perf_kpi.target.gte95"),
         _ST: _on if data_avail["overall_power"] >= 95 else _below,
         "_row_class": "row-success" if data_avail["overall_power"] >= 95 else "row-warning"},
        {_M: _T("perf_kpi.row.irr_completeness"), _V2: _fmt_pct(data_avail["irradiance"]),
         _TG: _T("perf_kpi.target.gte95"),
         _ST: _on if data_avail["irradiance"] >= 95 else _below,
         "_row_class": "row-success" if data_avail["irradiance"] >= 95 else "row-warning"},
        {_M: _T("perf_kpi.row.irr_quality"),
         _V2: _coh if irr_ok else _T("perf_kpi.status.review_required"),
         _TG: _T("perf_kpi.target.coherent"),
         _ST: _coh if irr_ok else _rev,
         "_row_class": "row-success" if irr_ok else "row-warning"},
        {_M: _T("perf_kpi.row.high_actions"), _V2: str(_high_count),
         _TG: _T("perf_kpi.target.zero"),
         _ST: _none_s if not _high_count else _open_s,
         "_row_class": "row-success" if not _high_count else "row-danger"},
        {_M: _T("perf_kpi.row.clean_pr"), _V2: _fmt_pct(clean_pr),
         _TG: _T("perf_kpi.row.clean_pr.target", design_pr=f"{design_pr:.0f}"),
         _ST: _indic, "_row_class": "row-info"},
    ]
    return {
        "template": "section",
        "id": "performance-kpi-dashboard",
        "toc_group": "Overview",
        "title": _T("perf_kpi.title"),
        "kicker": _T("perf_kpi.kicker"),
        "summary": _T("perf_kpi.summary"),
        "commentary_title": _T("perf_kpi.commentary_title"),
        "commentary": [_T("perf_kpi.commentary")],
        "kpis": [],
        "figures": [],
        "tables": [
            _table_block(
                _T("perf_kpi.table.title"),
                [_T("perf_kpi.table.col.metric"), _T("perf_kpi.table.col.value"),
                 _T("perf_kpi.table.col.target"), _T("perf_kpi.table.col.status")],
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
    _dq_good = data_avail["overall_power"] >= 95 and data_avail["irradiance"] >= 95
    commentary = [
        _T("data_qual.commentary.power_irr.good" if _dq_good else "data_qual.commentary.power_irr.poor",
           power_pct=_fmt_pct(data_avail["overall_power"]), irr_pct=_fmt_pct(data_avail["irradiance"]))
    ]
    if n_below95:
        commentary.append(
            _T("data_qual.commentary.below95",
               n_below95=n_below95, n_below90=n_below90,
               worst_inv=worst_inv, worst_value=_fmt_pct(worst_value))
        )
    if irr_coh:
        best_name, best_metrics = sorted(irr_coh.items(), key=lambda item: item[1]["correlation"], reverse=True)[0]
        ratio = best_metrics["mean_ratio"]
        _sarah_key = "data_qual.commentary.sarah_good" if 0.90 <= ratio <= 1.10 else "data_qual.commentary.sarah_poor"
        commentary.append(
            _T(_sarah_key,
               name=best_name,
               correlation=f"{best_metrics['correlation']:.3f}",
               suspect_pct=f"{best_metrics['suspect_pct']:.1f}%")
        )
    else:
        commentary.append(_T("data_qual.commentary.no_sarah"))

    n_inv = len(data_avail["per_inverter"])
    commentary.append(_T("data_qual.commentary.stuck", n_inverters=n_inv))

    return {
        "template": "section",
        "id": "data-quality",
        "toc_group": "Overview",
        "paginate": False,
        "title": _T("data_qual.title"),
        "kicker": _T("data_qual.kicker"),
        "summary": _T("data_qual.summary"),
        "commentary_title": _T("data_qual.commentary_title"),
        "commentary": commentary,
        "kpis": [
            _kpi(_T("data_qual.kpi.power_completeness.label"), _fmt_pct(data_avail["overall_power"]),
                 _T("data_qual.kpi.power_completeness.target"), _status_from_threshold(data_avail["overall_power"], 95)),
            _kpi(_T("data_qual.kpi.irr_completeness.label"), _fmt_pct(data_avail["irradiance"]),
                 _T("data_qual.kpi.irr_completeness.target"), _status_from_threshold(data_avail["irradiance"], 95)),
        ],
        "figures": [
            figure
            for figure in [
                _figure_block(
                    charts,
                    "data_availability_overview",
                    _T("data_qual.figure.telemetry.title"),
                    _T("data_qual.figure.telemetry.caption"),
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
            _T("irr_coherence.table.col.reference"): f"SARAH_{name}",
            _T("irr_coherence.table.col.correlation"): f"{metrics['correlation']:.3f}",
            _T("irr_coherence.table.col.ratio"): f"{metrics['mean_ratio']:.2f} \u00b1 {metrics['std_ratio']:.2f}",
            _T("irr_coherence.table.col.suspect_pct"): _fmt_pct(metrics["suspect_pct"], 1),
            _T("irr_coherence.table.col.gap_days"): _fmt_num(metrics.get("days_with_gaps"), 0),
            _T("irr_coherence.table.col.status"): _T("irr_coherence.status.ok") if metrics["correlation"] > 0.95 and metrics["suspect_pct"] < 5 else _T("irr_coherence.status.review"),
            "_row_class": "row-success" if metrics["correlation"] > 0.95 and metrics["suspect_pct"] < 5 else "row-warning",
        }
        for name, metrics in sorted(irr_coh.items())
    ]
    chart_page = {
        "template": "section",
        "id": "irradiance-coherence",
        "toc_group": "Overview",
        "paginate": False,
        "title": _T("irr_coherence.title"),
        "kicker": _T("irr_coherence.kicker"),
        "summary": _T("irr_coherence.summary"),
        "commentary_title": _T("irr_coherence.commentary_title"),
        "commentary": [],
        "kpis": [],
        "figures": [
            figure
            for figure in [
                _figure_block(
                    charts,
                    "irradiance_monthly_comparison",
                    _T("irr_coherence.figure.monthly.title"),
                    _T("irr_coherence.figure.monthly.caption"),
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
        "title": _T("irr_coherence.title"),
        "kicker": _T("irr_coherence.kicker"),
        "summary": "",
        "commentary_title": _T("irr_coherence.commentary_title"),
        "commentary": [],
        "kpis": [],
        "figures": [
            figure
            for figure in [
                _figure_block(
                    charts,
                    "irradiance_scatter",
                    _T("irr_coherence.figure.scatter.title"),
                    _T("irr_coherence.figure.scatter.caption"),
                    width="full",
                ),
            ]
            if figure
        ],
        "tables": [
            _table_block(
                _T("irr_coherence.table.title"),
                [_T("irr_coherence.table.col.reference"), _T("irr_coherence.table.col.correlation"),
                 _T("irr_coherence.table.col.ratio"), _T("irr_coherence.table.col.suspect_pct"),
                 _T("irr_coherence.table.col.gap_days"), _T("irr_coherence.table.col.status")],
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
                "title": _T("data_qual_detail.finding.sitewide.title"),
                "severity": "warning",
                "body": _T("data_qual_detail.finding.sitewide.body", n_sitewide=n_sitewide),
            }
        )
    if not monthly_df.empty:
        weakest_month = monthly_df.min(axis=1).sort_values().index[0]
        findings.append(
            {
                "title": _T("data_qual_detail.finding.weakest.title"),
                "severity": "warning",
                "body": _T("data_qual_detail.finding.weakest.body", weakest_month=f"{weakest_month:%b %Y}"),
            }
        )

    return {
        "template": "section",
        "id": "data-quality-detail",
        "toc_group": "Overview",
        "paginate": False,
        "title": _T("data_qual_detail.title"),
        "kicker": _T("data_qual_detail.kicker"),
        "summary": _T("data_qual_detail.summary"),
        "commentary_title": _T("data_qual_detail.commentary_title"),
        "commentary": [],
        "kpis": [],
        "figures": [
            figure
            for figure in [
                _figure_block(
                    charts,
                    "data_availability_heatmap",
                    _T("data_qual_detail.figure.heatmap.title"),
                    _T("data_qual_detail.figure.heatmap.caption"),
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

    _res_dir = _T("losses.residual.underperformance" if wf["residual"] < 0 else "losses.residual.overperformance")
    return {
        "template": "section",
        "id": "losses",
        "toc_group": "Technical Findings",
        "title": _T("losses.title"),
        "kicker": _T("losses.kicker"),
        "summary": _T("losses.summary"),
        "commentary_title": _T("losses.commentary_title"),
        "commentary": [
            _T("losses.commentary.budget",
               weather_corrected=_fmt_num(wf["weather_corrected"], 0, " MWh"),
               actual=_fmt_num(wf["actual"], 0, " MWh")),
            _T("losses.commentary.breakdown",
               avail_loss=_fmt_num(abs(wf["avail_loss"]), 0, " MWh"),
               tech_loss=_fmt_num(abs(wf["technical_loss"]), 0, " MWh"),
               residual_direction=_res_dir,
               residual=_fmt_num(abs(wf["residual"]), 0, " MWh")),
            _T("losses.commentary.recovery", recovery_mwh=_fmt_num(recovery_mwh, 0, " MWh")),
            _T("losses.commentary.grid"),
        ],
        "kpis": [
            _kpi(_T("losses.kpi.weather_corrected.label"), _fmt_num(wf["weather_corrected"], 0, " MWh")),
            _kpi(_T("losses.kpi.avail_loss.label"), _fmt_num(abs(wf["avail_loss"]), 0, " MWh"), "", "warning"),
            _kpi(_T("losses.kpi.tech_loss.label"), _fmt_num(abs(wf["technical_loss"]), 0, " MWh"), "",
                 "danger" if abs(wf["technical_loss"]) > abs(wf["avail_loss"]) else "warning"),
        ],
        "figures": [
            figure
            for figure in [
                _figure_block(charts, "waterfall",
                              _T("losses.figure.waterfall.title"), _T("losses.figure.waterfall.caption")),
                _figure_block(charts, "monthly_availability_loss",
                              _T("losses.figure.monthly_avail.title"), _T("losses.figure.monthly_avail.caption")),
            ]
            if figure
        ],
        "tables": [
            _table_block(
                _T("losses.table.top_opps.title"),
                [_T("losses.table.top_opps.col.priority"), _T("losses.table.top_opps.col.category"),
                 _T("losses.table.top_opps.col.loss_mwh"), _T("losses.table.top_opps.col.loss_eur"),
                 _T("losses.table.top_opps.col.action")],
                [
                    {
                        _T("losses.table.top_opps.col.priority"): _eur_priority(item.get("mwh_loss", 0))[0],
                        _T("losses.table.top_opps.col.category"): item["category"],
                        _T("losses.table.top_opps.col.loss_mwh"): _fmt_num(float(item.get("mwh_loss", 0.0)), 0, " MWh"),
                        _T("losses.table.top_opps.col.loss_eur"): _fmt_num(float(item.get("mwh_loss", 0.0)) * 1000.0 * _TARIFF_EUR_KWH, 0, ""),
                        _T("losses.table.top_opps.col.action"): item["action"],
                        "_row_class": _eur_priority(item.get("mwh_loss", 0))[1],
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
        _T("diag.commentary.max_dev",
           max_start=_fmt_num(max_start, 1, " min"),
           max_stop=_fmt_num(max_stop, 1, " min"))
    ]
    if max(max_start, max_stop) > 15:
        commentary.append(_T("diag.commentary.large_dev"))
    else:
        commentary.append(_T("diag.commentary.contained_dev"))
    if flagged_red:
        _red_str = ", ".join(flagged_red[:6]) + (" and others" if len(flagged_red) > 6 else "")
        commentary.append(_T("diag.commentary.red_outliers", flagged_red=_red_str))
    elif flagged_amber:
        _amb_str = ", ".join(flagged_amber[:6]) + (" and others" if len(flagged_amber) > 6 else "")
        commentary.append(_T("diag.commentary.amber_zone", flagged_amber=_amb_str))
    commentary.append(_T("diag.commentary.late_start"))

    return {
        "template": "section",
        "id": "targeted-diagnostics",
        "toc_group": "Technical Findings",
        "title": _T("diag.title"),
        "kicker": _T("diag.kicker"),
        "summary": _T("diag.summary"),
        "commentary_title": _T("diag.commentary_title"),
        "commentary": commentary,
        "kpis": [],
        "figures": [
            figure
            for figure in [
                _figure_block(
                    charts,
                    "start_stop",
                    _T("diag.figure.start_stop.title"),
                    _T("diag.figure.start_stop.caption"),
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
                "severity": _severity(_eur_priority(item.get("mwh_loss", 0))[0]),
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
            _kpi("High-priority actions", str(sum(1 for item in punchlist if _eur_priority(item.get("mwh_loss", 0))[0] == "HIGH")), "", "danger" if any(_eur_priority(item.get("mwh_loss", 0))[0] == "HIGH" for item in punchlist) else "success"),
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
    rows = []
    for item in sorted(analysis["punchlist"], key=lambda row: -float(row.get("mwh_loss", 0.0))):
        mwh_loss = float(item.get("mwh_loss", 0.0))
        eur_loss = mwh_loss * 1000.0 * _TARIFF_EUR_KWH
        if eur_loss >= 1000:
            priority = "HIGH"
            row_class = "row-danger"
        else:
            priority = "MEDIUM"
            row_class = "row-warning"
        rows.append(
            {
                "Priority": priority,
                "Category": item["category"],
                "Estimated loss (MWh)": _fmt_num(mwh_loss, 0, ""),
                "Estimated loss (€)": _fmt_num(eur_loss, 0, ""),
                "Issue": item["issue"],
                "Recommended action": item["action"],
                "_row_class": row_class,
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
                ["Priority", "Category", "Estimated loss (MWh)", "Estimated loss (€)", "Issue", "Recommended action"],
                rows,
            )
        ],
        "findings": [],
        "notes": [],
    }


def _technology_risk_page() -> dict:
    """One-page technology risk register for Sungrow SG250HX + First Solar CdTe."""
    rows = [
        # ── HIGH ─────────────────────────────────────────────────────────────
        {
            "Priority": "HIGH", "Equipment": "Sungrow SG250HX",
            "Risk / What to Watch": "AC Relay Wear (Fault 038) — high trip-count sites develop pitted contacts; inverter fails to reconnect after trip.",
            "Diagnostic / Action": "Extract trip count from iSolarCloud Event Log. If >500 trips/yr, replace relay proactively. Check SPDs in LV cabinet for earth short. Listen for relay click on restart — absent = failed relay.",
            "_row_class": "row-danger",
        },
        {
            "Priority": "HIGH", "Equipment": "Sungrow SG250HX",
            "Risk / What to Watch": "DC Insulation Fault (Fault 039) — triggered after rain if string Riso < 50 kΩ. High risk with third-party MC4 connectors or cables pinched under tracker rails.",
            "Diagnostic / Action": "String-by-string isolation test to locate affected string. Megger at 1000 V DC (target >1 MΩ). Replace third-party MC4 connectors with OEM-compatible type.",
            "_row_class": "row-danger",
        },
        {
            "Priority": "HIGH", "Equipment": "Sungrow SG250HX",
            "Risk / What to Watch": "MPPT Wiring Error — persistent single-inverter PR 10–15% below fleet with no fault alarms and no seasonal variation. Can persist for years undetected.",
            "Diagnostic / Action": "Audit strings per MPPT vs single-line diagram. Calculate DC power per MPPT vs rated input. Run iSolarCloud I-V curve scan to identify anomalous MPPT channels.",
            "_row_class": "row-danger",
        },
        {
            "Priority": "HIGH", "Equipment": "First Solar Series 6",
            "Risk / What to Watch": "PID / TCO Corrosion — power loss at negative-string-end modules from sodium migration and TCO corrosion. Risk elevated in ungrounded high-voltage systems.",
            "Diagnostic / Action": "EL imaging survey prioritising negative-string-end modules. IV-curve for Voc and fill factor loss signature. Verify edge seal integrity on suspect modules.",
            "_row_class": "row-danger",
        },
        {
            "Priority": "HIGH", "Equipment": "First Solar Series 6",
            "Risk / What to Watch": "PR Decline Exceeding Warranted Rate — warranted 0.55%/yr (Cu back contact) or 0.2%/yr (CuRe). Fleet-wide PR decline >1%/yr requires priority investigation.",
            "Diagnostic / Action": "EL/IV testing on module sample. Review soiling log and cleaning records. Check inverter efficiency trending. Compare irradiance sensor vs PVGIS-SARAH3 for sensor drift.",
            "_row_class": "row-danger",
        },
        # ── MEDIUM ───────────────────────────────────────────────────────────
        {
            "Priority": "MEDIUM", "Equipment": "Sungrow SG250HX",
            "Risk / What to Watch": "Thermal Overtemperature (Faults 036/037) — summer midday trips if ambient >45°C near cabinet, seized fan bearings, or blocked air inlet filters.",
            "Diagnostic / Action": "Inspect fans and air filters at every maintenance visit. 500 mm clearance required around enclosure. Install shade canopy if ambient routinely >45°C in summer.",
            "_row_class": "row-warning",
        },
        {
            "Priority": "MEDIUM", "Equipment": "Sungrow SG250HX",
            "Risk / What to Watch": "French Grid Curtailment Not Logged (SUN-014) — RTE/Enedis curtailment appearing as unexplained PR dips. ~3 TWh curtailed in France in 2025, rising sharply.",
            "Diagnostic / Action": "Verify curtailment command timestamps logged in SCADA. Cross-reference with grid operator records for months with unexplained PR drops. Exclude curtailed periods from contractual PR.",
            "_row_class": "row-warning",
        },
        {
            "Priority": "MEDIUM", "Equipment": "SCADA / Irradiance",
            "Risk / What to Watch": "Irradiance Sensor Drift — thermopile pyranometers drift +1–3%/yr without heating in humid climates, making PR appear to decline. Reference cells overestimate daily irradiation by >2%.",
            "Diagnostic / Action": "Monthly comparison of on-site irradiation vs PVGIS-SARAH3. Annual sensor calibration (IEC 61724-1 Class A). Weekly cleaning log. Replace Class C instruments with ISO 9060 Class A for contractual PR.",
            "_row_class": "row-warning",
        },
        {
            "Priority": "MEDIUM", "Equipment": "First Solar Series 6",
            "Risk / What to Watch": "Hot Spot Detection Difficulty — monolithic CdTe structure and glass-glass encapsulation produce smaller surface temperature gradients than c-Si; standard IR surveys miss them.",
            "Diagnostic / Action": "Use high-sensitivity IR camera (NETD <50 mK). Perform thermographic survey at >600 W/m² irradiance. Confirm with IV-curve fill factor loss measurement on suspect modules.",
            "_row_class": "row-warning",
        },
        # ── INFO ─────────────────────────────────────────────────────────────
        {
            "Priority": "INFO", "Equipment": "First Solar Series 6",
            "Risk / What to Watch": "CdTe Temperature Coefficient Advantage — Pmax coeff. −0.28%/°C vs c-Si −0.35 to −0.50%/°C. Summer PR should exceed c-Si benchmarks — this is expected, not a fault.",
            "Diagnostic / Action": "Do not apply c-Si PR benchmarks to CdTe plants in hot conditions. Summer PR declining toward c-Si levels may signal module degradation or soiling eroding the thermal advantage.",
            "_row_class": "row-info",
        },
        {
            "Priority": "INFO", "Equipment": "Sungrow SG250HX",
            "Risk / What to Watch": "iSolarCloud Remote I-V Curve Scan — full-plant diagnostic identifies dust, cracks, diode shorts, MPPT mismatch, and PID attenuation in ~15 minutes with <0.5% accuracy.",
            "Diagnostic / Action": "Schedule remote I-V curve scan via iSolarCloud before any field dispatch for unexplained underperformance. Results localise affected strings without site visit.",
            "_row_class": "row-info",
        },
        {
            "Priority": "INFO", "Equipment": "Sungrow SG250HX",
            "Risk / What to Watch": "Clipping Loss Underestimation — at DC/AC ratio 1.27 (this site), clipping occurs ~3–4% of annual operating hours. 10-min SCADA averages mask true clipping magnitude.",
            "Diagnostic / Action": "Configure SCADA at 5-min resolution to capture clipping accurately. Apply clipping correction factor when comparing SCADA PR to hourly yield model.",
            "_row_class": "row-info",
        },
    ]
    high_count = sum(1 for r in rows if r["Priority"] == "HIGH")
    med_count = sum(1 for r in rows if r["Priority"] == "MEDIUM")
    return {
        "template": "section",
        "id": "technology-risk",
        "toc_group": "Technical Findings",
        "title": "Technology Risk Register",
        "kicker": "Sungrow SG250HX & First Solar CdTe",
        "summary": "Key failure modes, performance risks, and diagnostic actions specific to the inverter and module technologies deployed at this site.",
        "commentary_title": "Risk context",
        "commentary": [
            f"This register consolidates {high_count} HIGH-priority and {med_count} MEDIUM-priority technology-specific risks derived from field experience across comparable French utility-scale PV sites, Sungrow EMEA fault documentation, First Solar technical papers, and NREL/IEA monitoring standards.",
            "HIGH items represent failure modes with confirmed field precedent and material energy loss potential that can persist undetected without targeted inspection. MEDIUM items are relevant operational watch-points. INFO items provide benchmarking context to avoid misinterpreting normal technology behaviour as faults.",
        ],
        "kpis": [],
        "figures": [],
        "tables": [
            _table_block(
                "Technology Risk Register — Sungrow SG250HX & First Solar Series 6",
                ["Priority", "Equipment", "Risk / What to Watch", "Diagnostic / Action"],
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
                            "Priority": _eur_priority(item.get("mwh_loss", 0))[0],
                            "Category": item["category"],
                            "Estimated loss": _fmt_num(float(item.get("mwh_loss", 0.0)), 0, " MWh"),
                            "Recommended action": item["action"],
                            "_row_class": _eur_priority(item.get("mwh_loss", 0))[1],
                        }
                        for item in top_actions
                    ],
                    appendix_only=True,
                ),
            ],
            "findings": [],
        }
    ]


def build_report_data(*, config: dict, analysis: dict, charts: dict, outputs: dict, preflight: dict, lang: str = "en") -> dict:
    global _T
    _T = get_translator(lang)
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
        _technology_risk_page(),
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

    _pr_tgt = 79.0
    critical_months = int((monthly["PR"] < 65).sum()) if len(monthly) else 0
    warning_months = int(((monthly["PR"] >= 65) & (monthly["PR"] < _pr_tgt)).sum()) if len(monthly) else 0
    spec_yield = float(annual["E_act"].sum() / max(config["cap_dc_kwp"], 1) / max(len(annual), 1))
    commentary.append(
        (
            f"Average specific yield is {_fmt_num(spec_yield, 0, ' kWh/kWp/yr')}. "
            f"The period contains {critical_months} month(s) below the 65% critical threshold and {warning_months} month(s) between 65% and {_pr_tgt:.0f}%."
        )
    )
    commentary.append(
        "If summer PR remains weak while irradiation peaks, soiling, latent downtime, or inverter quality losses are the likely causes — a dry-season PR decline with full recovery after autumn rain is the soiling signature (2–8% typical for SW France). "
        "CdTe's −0.28%/°C temperature coefficient means summer PR should nominally exceed c-Si benchmarks; if it does not, soiling or degradation is eroding that thermal advantage."
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
                f"{len(low_pr_good_av)} inverter(s) have low PR despite acceptable availability, pointing toward soiling, string issues, or MPPT behaviour. "
                "Inverters in this second group are priority candidates for an iSolarCloud remote I-V curve scan before any field dispatch — the most common causes are unequal MPPT string loading, soiling heterogeneity, or partial shading. "
                "A persistent spread exceeding 5 pp between best and worst inverters with no correlated availability gap is the classic DC-side quality-loss signature."
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

    worst_dev_str = (
        "Largest deviations on " + ", ".join(f"{name} ({value:.1f}%)" for name, value in worst_dev.items()) + ". "
        if len(worst_dev) else ""
    )
    commentary = [
        (
            f"Fleet mean PR is {_fmt_pct(fleet_mean)}; lowest inverters: {', '.join(low_pr_names) if low_pr_names else 'n/a'}. "
            "Persistent red months = running but underperforming, not offline. "
            f"{worst_dev_str}"
            "Post-rain yield spikes confirm soiling; a stable year-round deficit unresponsive to rainfall points to a permanent electrical loss (MPPT imbalance, bypassed strings, or junction-box fault)."
        ),
    ]

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
                f"Mean time to failure across inverters with recorded faults is {_fmt_num(fleet_mttf, 1, ' days')}. "
                "For inverters with MTTF below 5 days, AC relay wear (Fault 038) is the primary suspect — trip counts above 500/yr cause contact pitting that prevents reconnection, readable directly from iSolarCloud Event Log before any field visit. "
                "Whole-site simultaneous drops are grid-event signatures (overvoltage or curtailment) addressed at MV transformer or DSO level, not at the inverter. "
                "Summer-only availability dips confined to midday hours are typically resolved by cleaning air inlet filters and verifying fan operation (Fault 036/037)."
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
