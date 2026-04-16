# SCADA Analysis Report Pipeline

`pvpat_scada_analysis.py` now uses an HTML-first reporting flow:

1. Existing data loading and engineering calculations run unchanged.
2. `report/chart_factory.py` exports reusable chart assets as SVG.
3. `report/build_report_data.py` converts analytical outputs into a structured report object.
4. `report/render_report.py` renders branded HTML with Jinja2 templates and optional PDF output via a pluggable backend.
5. `report/preflight.py` validates metadata, chart assets, and layout-sensitive content before final rendering.

## Dependencies

Install the repository requirements:

```bash
pip install -r requirements.txt
```

Key additions for the report pipeline:

- `Jinja2`
- `WeasyPrint`
- `playwright`
- `matplotlib`
- `pandas`
- `numpy`

## Generate HTML

```bash
python "SCADA Analysis/pvpat_scada_analysis.py" --output-format html --output-dir "C:\path\to\output" --keep-html
```

## Generate PDF

```bash
python "SCADA Analysis/pvpat_scada_analysis.py" --output-format pdf --output-dir "C:\path\to\output" --keep-html
```

## Useful options

- `--assets-dir`: send exported SVG charts to a custom folder
- `--debug-layout`: add faint layout boundaries around report blocks
- `--keep-html`: keep the rendered HTML alongside the PDF
- `--data-dir`: override the SCADA input folder
- `--pdf-engine auto|playwright|weasyprint`: select the PDF backend explicitly

## Minimal example

```bash
python "SCADA Analysis/pvpat_scada_analysis.py" --output-format pdf --keep-html
```

## PDF backends

`--pdf-engine auto` prefers:

- `playwright` on Windows
- `weasyprint` on Linux/macOS

Fallback order is automatic. This keeps the HTML templates and print CSS stable while allowing the PDF engine to change per environment.

Playwright setup:

```bash
python -m pip install playwright
python -m playwright install chromium
```

WeasyPrint setup still requires native rendering libraries on the host.

## Containerized runtime

For reproducible PDF builds independent of the workstation Python/GTK stack:

```bash
docker build -f "SCADA Analysis/Dockerfile.report" -t scada-report .
```

Run the report with a mounted data folder and mounted output folder:

```bash
docker run --rm ^
  -v "C:\path\to\data:/data" ^
  -v "C:\path\to\output:/output" ^
  scada-report ^
  --data-dir /data ^
  --output-dir /output ^
  --output-format pdf ^
  --pdf-engine weasyprint ^
  --keep-html
```

Inside the container, Python and native libraries are pinned, which is the recommended long-term path for stable PDF generation.

## Assumptions

- The analytical thresholds and KPI formulas remain in `pvpat_scada_analysis.py`.
- Branding assets are loaded from the `SCADA Analysis` folder, not from the data directory.
- Weather data remains best-effort and the corresponding section is omitted if unavailable.
- The Docker runtime is pinned to Python 3.12 for reproducible PDF builds.
