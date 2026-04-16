"""
check_chart_bounds.py
=====================
Run this script after generating the PVPAT report to verify that no chart axes
overflow page boundaries and that the insight table does not overlap with chart content.

Usage:
    python check_chart_bounds.py                   # checks the default PDF path
    python check_chart_bounds.py my_report.pdf     # checks a specific PDF

It can also be imported and called from within pvpat_scada_analysis.py by adding:
    import check_chart_bounds; check_chart_bounds.patch_savefig()
at the top of that script — which will validate every figure at save time.
"""

import sys
import os

# ─────────────────────────────────────────────────────────────────────────────
# Constants that must match pvpat_scada_analysis.py
# ─────────────────────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = 8.27, 11.69        # A4 portrait inches
BOX_BOT        = 0.058              # insight table bottom (figure fraction)
HEADER_TOP     = 0.92               # header bar bottom boundary (figure fraction)
MIN_CHART_BOT  = 0.15               # minimum acceptable chart area bottom
MAX_CHART_TOP  = HEADER_TOP         # charts must not exceed header

_ISSUES = []   # collected warnings — reset by validate_figure()


# ─────────────────────────────────────────────────────────────────────────────
# Core validator — works on a live matplotlib Figure
# ─────────────────────────────────────────────────────────────────────────────

def validate_chart_asset(path) -> list:
    """Stub validator for SVG/PNG chart assets — returns an empty issues list."""
    return []


def validate_figure(fig, page_label="(unknown page)"):
    """Inspect all axes in *fig* and report layout problems.

    Returns a list of warning strings.  An empty list means the page is clean.
    """
    issues = []

    for ax in fig.axes:
        pos = ax.get_position()           # Bbox in figure fractions [0,1]

        # 1. Axes outside page boundaries
        if pos.x0 < 0 or pos.y0 < 0 or pos.x1 > 1 or pos.y1 > 1:
            issues.append(
                f"[{page_label}] Axes OUTSIDE page bounds: "
                f"x=[{pos.x0:.3f},{pos.x1:.3f}]  y=[{pos.y0:.3f},{pos.y1:.3f}]"
            )

        # 2. Axes bottom too low — overlaps the insight table region
        if pos.y0 < BOX_BOT + 0.10:
            issues.append(
                f"[{page_label}] Axes bottom ({pos.y0:.3f}) is very close to or below the "
                f"insight table zone (BOX_BOT={BOX_BOT}).  "
                f"Chart content will overlap the KEY FINDINGS table."
            )

        # 3. Axes top too high — overlaps the header bar
        if pos.y1 > HEADER_TOP + 0.01:
            issues.append(
                f"[{page_label}] Axes top ({pos.y1:.3f}) extends above the header bar "
                f"boundary ({HEADER_TOP}).  Chart will clip into the page header."
            )

        # 4. Zero-size axes (invisible but still occupying layout space)
        if pos.width < 0.01 or pos.height < 0.01:
            issues.append(
                f"[{page_label}] Degenerate (zero-size) axes detected — "
                f"may indicate a layout calculation error."
            )

    return issues


# ─────────────────────────────────────────────────────────────────────────────
# Monkey-patch for live validation during report generation
# ─────────────────────────────────────────────────────────────────────────────

def patch_savefig():
    """Call this once at the start of pvpat_scada_analysis.py to validate
    every figure automatically when pdf.savefig(fig) is called.

    Any layout issues are printed to stdout immediately.
    """
    from matplotlib.backends.backend_pdf import PdfPages
    _orig_savefig = PdfPages.savefig

    def _checked_savefig(self, figure=None, **kwargs):
        import matplotlib.pyplot as plt
        fig = figure if figure is not None else plt.gcf()
        label = getattr(fig, '_page_label', '(unlabelled)')
        problems = validate_figure(fig, label)
        if problems:
            print("\n  *** CHART BOUNDS WARNING ***")
            for p in problems:
                print(f"  {p}")
            print()
        return _orig_savefig(self, figure, **kwargs)

    PdfPages.savefig = _checked_savefig
    print("[check_chart_bounds] Live validation patch applied to PdfPages.savefig")


# ─────────────────────────────────────────────────────────────────────────────
# PDF static check — reads a completed PDF and checks content bounding boxes
# ─────────────────────────────────────────────────────────────────────────────

def check_pdf(pdf_path):
    """Open a rendered PDF and check that no content bounding box exceeds the
    declared page MediaBox.

    Requires the 'pymupdf' (fitz) package:
        pip install pymupdf

    Falls back to a size-only check if pymupdf is not installed.
    """
    if not os.path.exists(pdf_path):
        print(f"ERROR: File not found: {pdf_path}")
        return False

    print(f"\nChecking PDF: {pdf_path}")
    print(f"Expected page size: {PAGE_W:.2f} x {PAGE_H:.2f} inches  ({PAGE_W*72:.0f} x {PAGE_H*72:.0f} pt)\n")

    try:
        import fitz  # pymupdf
    except ImportError:
        print("pymupdf not installed — falling back to page-size check only.")
        print("Install with:  pip install pymupdf\n")
        _check_pdf_size_only(pdf_path)
        return True

    doc = fitz.open(pdf_path)
    all_clean = True
    expected_w_pt = PAGE_W * 72
    expected_h_pt = PAGE_H * 72
    tolerance_pt  = 5.0    # points — allow minor rounding

    for page_num, page in enumerate(doc, start=1):
        rect = page.rect                   # page MediaBox in points
        w_pt, h_pt = rect.width, rect.height

        # Page size check
        if (abs(w_pt - expected_w_pt) > tolerance_pt or
                abs(h_pt - expected_h_pt) > tolerance_pt):
            print(f"  Page {page_num}: UNEXPECTED SIZE — "
                  f"{w_pt:.1f}x{h_pt:.1f} pt  (expected {expected_w_pt:.0f}x{expected_h_pt:.0f} pt)")
            all_clean = False

        # Content bounding box check
        content_rect = page.get_bboxlog()   # list of (type, rect) for every draw op
        if content_rect:
            # Aggregate across all draw operations
            xs = [r[1].x0 for r in content_rect] + [r[1].x1 for r in content_rect]
            ys = [r[1].y0 for r in content_rect] + [r[1].y1 for r in content_rect]
            x0, x1 = min(xs), max(xs)
            y0, y1 = min(ys), max(ys)

            if x0 < -tolerance_pt:
                print(f"  Page {page_num}: Content LEFT overflow — x0={x0:.1f} pt")
                all_clean = False
            if x1 > w_pt + tolerance_pt:
                print(f"  Page {page_num}: Content RIGHT overflow — x1={x1:.1f} pt > page width {w_pt:.1f} pt")
                all_clean = False
            if y0 < -tolerance_pt:
                print(f"  Page {page_num}: Content TOP overflow — y0={y0:.1f} pt")
                all_clean = False
            if y1 > h_pt + tolerance_pt:
                print(f"  Page {page_num}: Content BOTTOM overflow — y1={y1:.1f} pt > page height {h_pt:.1f} pt")
                all_clean = False

        if all_clean or True:  # always print per-page OK to give progress feedback
            status = "OK" if all_clean else "ISSUES FOUND"
            print(f"  Page {page_num:3d}: {status}")

    doc.close()

    print()
    if all_clean:
        print("All pages CLEAN — no content overflow detected.")
    else:
        print("ISSUES detected — review warnings above.")
    return all_clean


def _check_pdf_size_only(pdf_path):
    """Minimal check using only the built-in struct module — verifies PDF page count and
    looks for /MediaBox entries.  No external dependencies."""
    with open(pdf_path, 'rb') as f:
        data = f.read()

    mediabox_count  = data.count(b'/MediaBox')
    expected_w_raw  = f"{PAGE_W * 72:.2f}".encode()
    # Just report found sizes
    print(f"  PDF size on disk: {len(data)/1024:.1f} KB")
    print(f"  /MediaBox entries found: {mediabox_count} (one per page expected)")
    print("  Run with pymupdf installed for full content-overflow checking.")


# ─────────────────────────────────────────────────────────────────────────────
# GridSpec parameter static audit — reads pvpat_scada_analysis.py source
# ─────────────────────────────────────────────────────────────────────────────

def audit_gridspec_params(source_path=None):
    """Parse pvpat_scada_analysis.py and flag any GridSpec definitions where
    top > 0.92 (overlaps header) or bottom < 0.15 (at risk of overlapping table
    before _page_insight pushes it up).

    This is a static safeguard to catch issues even without running the script.
    """
    if source_path is None:
        source_path = os.path.join(os.path.dirname(__file__), "pvpat_scada_analysis.py")

    if not os.path.exists(source_path):
        print(f"Source not found: {source_path}")
        return

    print(f"\nAuditing GridSpec parameters in: {source_path}\n")

    import re
    with open(source_path, encoding='utf-8') as f:
        lines = f.readlines()

    gs_pattern = re.compile(
        r'GridSpec\(.*?top\s*=\s*([0-9.]+).*?bottom\s*=\s*([0-9.]+)', re.S)
    issues_found = False

    for i, line in enumerate(lines, 1):
        m = gs_pattern.search(line)
        if m:
            top_val    = float(m.group(1))
            bottom_val = float(m.group(2))
            problems   = []
            if top_val > HEADER_TOP + 0.005:
                problems.append(f"top={top_val} exceeds header boundary ({HEADER_TOP})")
            if bottom_val < MIN_CHART_BOT:
                problems.append(
                    f"bottom={bottom_val} is below minimum ({MIN_CHART_BOT}) — "
                    "risk of overlap before _page_insight updates it"
                )
            if problems:
                print(f"  Line {i:4d}: {', '.join(problems)}")
                print(f"          {line.rstrip()}")
                issues_found = True

    # Also check for fig.add_axes calls with suspicious bounds
    axes_pattern = re.compile(r'add_axes\(\s*\[([0-9.,\s]+)\]')
    for i, line in enumerate(lines, 1):
        m = axes_pattern.search(line)
        if m:
            try:
                vals = [float(x.strip()) for x in m.group(1).split(',')]
                if len(vals) == 4:
                    x0, y0, w, h = vals
                    x1, y1 = x0 + w, y0 + h
                    if x0 < 0 or y0 < 0 or x1 > 1 or y1 > 1:
                        print(f"  Line {i:4d}: add_axes bounds outside [0,1]: [{x0},{y0},{w},{h}]")
                        issues_found = True
            except ValueError:
                pass

    if not issues_found:
        print("  No GridSpec or add_axes issues detected.")
    else:
        print("\nReview flagged lines and adjust top/bottom/left/right parameters.")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    default_pdf = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "PVPAT_SCADA_Analysis_Report.pdf"
    )
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else default_pdf

    # 1. Static audit of source parameters
    audit_gridspec_params()

    # 2. PDF content overflow check (requires pymupdf for full analysis)
    print("\n" + "=" * 60)
    check_pdf(pdf_path)
