from __future__ import annotations

from pathlib import Path

try:
    import check_chart_bounds
except Exception:  # pragma: no cover - best effort
    check_chart_bounds = None


def _warn_if(condition: bool, warnings: list[str], message: str) -> None:
    if condition:
        warnings.append(message)


def run_preflight(report_data: dict, chart_manifest: dict, config: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    document = report_data.get("document", {})
    required_fields = {
        "site_name": "Site name is required.",
        "report_title": "Report title is required.",
        "generated_at": "Generation timestamp is required.",
        "data_dir": "Input data directory must be recorded.",
    }
    for field, message in required_fields.items():
        if not document.get(field):
            errors.append(message)

    for chart_key, meta in sorted(chart_manifest.items()):
        chart_path = Path(meta["path"])
        if not chart_path.exists():
            errors.append(f"Missing chart asset: {chart_key} -> {chart_path}")
            continue
        if check_chart_bounds is not None:
            for issue in check_chart_bounds.validate_chart_asset(chart_path):
                warnings.append(f"{chart_key}: {issue}")

    for page in report_data.get("pages", []):
        page_title = page.get("title", page.get("template", "page"))
        summary = page.get("summary", "")
        findings = page.get("findings", [])
        tables = page.get("tables", [])
        _warn_if(
            isinstance(summary, str) and len(summary) > 1800,
            warnings,
            f"{page_title}: summary text is long and may impact pagination stability.",
        )
        _warn_if(
            len(findings) > 8 and page.get("template") not in {"appendix", "section_divider"},
            warnings,
            f"{page_title}: findings list exceeds the recommended in-body cap of 8 items.",
        )
        for table in tables:
            _warn_if(
                len(table.get("columns", [])) > 7 and not table.get("appendix_only"),
                warnings,
                f"{page_title}: table '{table.get('title', 'Untitled')}' is wide and may be better suited to an appendix.",
            )
            _warn_if(
                len(table.get("rows", [])) > 24 and not table.get("appendix_only"),
                warnings,
                f"{page_title}: table '{table.get('title', 'Untitled')}' is long and may span multiple pages.",
            )

    if not report_data.get("pages"):
        errors.append("No report pages were generated.")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "debug_layout": bool(config.get("debug_layout")),
    }
