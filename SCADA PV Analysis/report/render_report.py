from __future__ import annotations

import platform
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


def normalise_report_stem(report_name: str) -> str:
    if not report_name:
        return "PVPAT_SCADA_Analysis_Report"
    return Path(report_name).stem


def build_output_paths(
    *,
    output_dir: Path,
    assets_dir: Path | None,
    report_name: str,
    output_format: str,
    keep_html: bool,
    pdf_engine: str,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = normalise_report_stem(report_name)
    html_path = output_dir / f"{stem}.html"
    pdf_path = output_dir / f"{stem}.pdf"
    resolved_assets_dir = assets_dir or output_dir / f"{stem}_assets"
    resolved_assets_dir.mkdir(parents=True, exist_ok=True)
    return {
        "stem": stem,
        "html_path": html_path,
        "pdf_path": pdf_path,
        "assets_dir": resolved_assets_dir,
        "output_format": output_format,
        "keep_html": keep_html,
        "pdf_engine": pdf_engine,
    }


def _load_css(static_dir: Path) -> dict:
    return {
        "report_css": (static_dir / "report.css").read_text(encoding="utf-8"),
        "print_css": (static_dir / "print.css").read_text(encoding="utf-8"),
        "debug_css": (static_dir / "debug.css").read_text(encoding="utf-8"),
    }


def render_report_html(report_data: dict, *, template_dir: Path, static_dir: Path) -> str:
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("base.html")
    return template.render(report=report_data, css=_load_css(static_dir))


def render_report_outputs(
    *,
    report_data: dict,
    output_paths: dict,
    template_dir: Path,
    static_dir: Path,
) -> dict:
    html = render_report_html(report_data, template_dir=template_dir, static_dir=static_dir)
    html_path: Path = output_paths["html_path"]
    pdf_path: Path = output_paths["pdf_path"]

    should_write_html = output_paths["output_format"] == "html" or output_paths["keep_html"]
    must_write_html = should_write_html or output_paths["output_format"] == "pdf"
    if must_write_html:
        html_path.write_text(html, encoding="utf-8")

    pdf_engine_used = None
    if output_paths["output_format"] == "pdf":
        pdf_engine_used = render_pdf(
            html=html,
            html_path=html_path,
            pdf_path=pdf_path,
            base_url=template_dir.parent.parent,
            requested_engine=output_paths["pdf_engine"],
        )
        if not output_paths["keep_html"]:
            html_path.unlink(missing_ok=True)

    return {
        "html_path": html_path if should_write_html else None,
        "pdf_path": pdf_path if output_paths["output_format"] == "pdf" else None,
        "assets_dir": output_paths["assets_dir"],
        "pdf_engine_used": pdf_engine_used,
    }


def render_pdf(*, html: str, html_path: Path, pdf_path: Path, base_url: Path, requested_engine: str) -> str:
    errors: list[str] = []
    for engine in preferred_pdf_engines(requested_engine):
        try:
            if engine == "playwright":
                render_pdf_with_playwright(html_path=html_path, pdf_path=pdf_path)
            elif engine == "weasyprint":
                render_pdf_with_weasyprint(html=html, pdf_path=pdf_path, base_url=base_url)
            else:  # pragma: no cover - guarded by CLI
                raise RuntimeError(f"Unsupported PDF engine: {engine}")
            return engine
        except Exception as exc:
            errors.append(f"{engine}: {exc}")
    raise RuntimeError("PDF rendering failed. " + " | ".join(errors))


def preferred_pdf_engines(requested_engine: str) -> list[str]:
    if requested_engine != "auto":
        return [requested_engine]
    if platform.system() == "Windows":
        return ["playwright", "weasyprint"]
    return ["weasyprint", "playwright"]


def render_pdf_with_weasyprint(*, html: str, pdf_path: Path, base_url: Path) -> None:
    try:
        from weasyprint import HTML
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError("WeasyPrint is not installed in this Python environment.") from exc
    except OSError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError("WeasyPrint native libraries are missing or not loadable.") from exc
    HTML(string=html, base_url=str(base_url)).write_pdf(str(pdf_path))


def render_pdf_with_playwright(*, html_path: Path, pdf_path: Path) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "Playwright is not installed in this Python environment. Install it and run 'python -m playwright install chromium'."
        ) from exc

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
            page.emulate_media(media="print")
            page.wait_for_function("Array.from(document.images).every((img) => img.complete)")
            page.pdf(
                path=str(pdf_path),
                format="A4",
                landscape=False,
                print_background=True,
                prefer_css_page_size=True,
                display_header_footer=True,
                header_template="<div></div>",
                footer_template=(
                    "<div style=\"width:100%; font-family:Aptos, Calibri, Arial, Helvetica, sans-serif; "
                    "font-size:9pt; font-weight:700; color:#F39200; padding:0 12mm 5mm 0; text-align:right;\">"
                    "<span class=\"pageNumber\"></span></div>"
                ),
                margin={"top": "0mm", "right": "0mm", "bottom": "12mm", "left": "0mm"},
            )
            browser.close()
    except Exception as exc:  # pragma: no cover - depends on environment
        raise RuntimeError(
            "Playwright could not render the PDF. Ensure Chromium is installed with 'python -m playwright install chromium'."
        ) from exc
