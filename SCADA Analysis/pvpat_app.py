"""
pvpat_app.py — PVPAT SCADA Data Collection Portal
===================================================
Client-facing upload portal for 8p2 Advisory PVPAT engagements.
Run locally:  streamlit run pvpat_app.py
"""

import base64
import io
import json
import zipfile
from datetime import datetime
from pathlib import Path

import streamlit as st

# ─────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
LOGO_PATH    = SCRIPT_DIR / "8p2_logo_white.png"   # white version for dark background
FAVICON_PATH = SCRIPT_DIR / "8p2_favicon.png"
BG_PATH      = SCRIPT_DIR / "bg_solar.jpg"


# ─────────────────────────────────────────────────────────────
# FAVICON
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PVPAT Data Portal | 8p2 Advisory",
    page_icon=str(FAVICON_PATH) if FAVICON_PATH.exists() else "☀️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ─────────────────────────────────────────────────────────────
# BACKGROUND IMAGE (base64-encoded for portability)
# ─────────────────────────────────────────────────────────────
def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()

if BG_PATH.exists():
    bg_b64 = _b64(BG_PATH)
    bg_css = f"url('data:image/jpeg;base64,{bg_b64}')"
else:
    bg_css = "linear-gradient(135deg,#001a3a 0%,#003366 60%,#0a4d8c 100%)"

# Encode logo and favicon as base64 for HTML injection (avoids Streamlit image expand button)
logo_b64    = _b64(LOGO_PATH)    if LOGO_PATH.exists()    else ""
favicon_b64 = _b64(FAVICON_PATH) if FAVICON_PATH.exists() else ""

# Inject real favicon via <link> tag (overrides any stretching from page_icon)
if favicon_b64:
    st.markdown(
        f'<link rel="shortcut icon" href="data:image/png;base64,{favicon_b64}">',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  /* ── Hide Streamlit's fixed top header so logo isn't clipped ── */
  header[data-testid="stHeader"] {{
      display: none !important;
  }}
  /* Remove the gap that was reserved for the header */
  .main {{ padding-top: 0 !important; }}
  [data-testid="stAppViewBlockContainer"] {{ padding-top: 1.5rem !important; }}

  /* ── Full-page background ── */
  .stApp {{
      background-image: linear-gradient(rgba(0,10,35,0.70), rgba(0,10,35,0.70)),
                        {bg_css};
      background-size: cover;
      background-position: center;
      background-attachment: fixed;
  }}

  /* ── Main content: dark glass card ── */
  .main .block-container,
  [data-testid="stAppViewBlockContainer"],
  section[data-testid="stMain"] .block-container {{
      background: rgba(0, 18, 55, 0.78) !important;
      border-radius: 14px;
      padding: 2rem 2.5rem 2.5rem 2.5rem;
      max-width: 1100px;
      box-shadow: 0 8px 50px rgba(0,0,0,0.55);
      backdrop-filter: blur(6px);
  }}

  /* ── All text white ── */
  .stApp, .stApp p, .stApp span, .stApp label, .stApp div,
  .stApp h1, .stApp h2, .stApp h3, .stApp h4,
  .stMarkdown, .stMarkdown p, .stMarkdown li,
  [data-testid="stText"], .stCaption,
  [data-baseweb="select"] *, [data-baseweb="input"] *,
  [data-baseweb="radio"] *, [data-baseweb="checkbox"] *,
  .stSelectbox label, .stMultiSelect label,
  .stNumberInput label, .stTextInput label,
  .stTextArea label, .stDateInput label,
  .stRadio label, [data-testid="stCaptionContainer"],
  [data-testid="stWidgetLabel"], [data-testid="stHelperText"],
  [data-testid="InputInstructions"] {{
      color: white !important;
  }}

  /* ── Placeholder text ── */
  input::placeholder, textarea::placeholder {{
      color: rgba(255,255,255,0.40) !important;
      opacity: 1 !important;
  }}

  /* ── Input fields: dark tinted ── */
  input, textarea,
  [data-baseweb="input"] input,
  [data-baseweb="textarea"] textarea {{
      background: rgba(255,255,255,0.10) !important;
      color: white !important;
      border-color: rgba(255,255,255,0.25) !important;
      caret-color: white !important;
  }}

  /* ── Select / dropdown ── */
  [data-baseweb="select"] > div,
  [data-baseweb="select"] [data-baseweb="popover"] {{
      background: rgba(0, 18, 55, 0.95) !important;
      color: white !important;
      border-color: rgba(255,255,255,0.25) !important;
  }}
  [data-baseweb="menu"] li, [data-baseweb="option"] {{
      color: white !important;
      background: rgba(0, 18, 55, 0.95) !important;
  }}
  [data-baseweb="menu"] li:hover, [data-baseweb="option"]:hover {{
      background: rgba(240,120,32,0.35) !important;
  }}

  /* ── Multiselect tags ── */
  [data-baseweb="tag"] {{
      background: rgba(240,120,32,0.60) !important;
      color: white !important;
  }}
  [data-baseweb="tag"] span {{ color: white !important; }}

  /* ── Number input spinners ── */
  [data-testid="stNumberInput"] button {{
      background: rgba(255,255,255,0.12) !important;
      color: white !important;
      border-color: rgba(255,255,255,0.20) !important;
  }}

  /* ── Date input ── */
  [data-baseweb="datepicker"] input {{ color: white !important; }}
  [data-testid="stDateInput"] input {{ color: white !important; }}

  /* ── Tab labels ── */
  [data-baseweb="tab"] button, [role="tab"] {{
      color: rgba(255,255,255,0.75) !important;
  }}
  [aria-selected="true"][role="tab"] {{
      color: white !important;
      border-bottom-color: #F07820 !important;
  }}

  /* ── Divider ── */
  hr {{ border-color: rgba(255,255,255,0.15) !important; }}

  /* ── Typography ── */
  html, body, [class*="css"] {{
      font-family: 'Open Sans', Arial, sans-serif;
  }}

  /* ── Step header bar ── */
  .step-hdr {{
      background: rgba(240,120,32,0.85);
      color: white;
      padding: 0.45rem 1rem;
      border-radius: 5px;
      font-weight: 700;
      font-size: 0.95rem;
      margin: 1.2rem 0 0.5rem 0;
  }}

  /* ── Sub-section label ── */
  .sub-hdr {{
      border-left: 4px solid #F07820;
      padding: 0.28rem 0.8rem;
      background: rgba(255,255,255,0.08);
      border-radius: 0 4px 4px 0;
      margin: 0.8rem 0 0.3rem 0;
      font-weight: 600;
      color: white;
      font-size: 0.87rem;
  }}

  /* ── Badges ── */
  .req {{ background:#F07820; color:white; font-size:0.64rem;
          padding:1px 6px; border-radius:10px; margin-left:5px; vertical-align:middle; }}
  .opt {{ background:rgba(255,255,255,0.25); color:white; font-size:0.64rem;
          padding:1px 6px; border-radius:10px; margin-left:5px; vertical-align:middle; }}

  /* ── Submit button ── */
  .stButton > button {{
      background:#F07820 !important; color:white !important;
      border:none !important; border-radius:6px !important;
      font-weight:700 !important; font-size:1rem !important;
      padding:0.65rem 2rem !important; width:100%;
      transition: background 0.2s;
  }}
  .stButton > button:hover {{ background:#cc6415 !important; }}

  /* ── Uploader ── */
  [data-testid="stFileUploaderDropzone"] {{
      border: 1.5px dashed rgba(255,255,255,0.30);
      border-radius: 6px;
      background: rgba(255,255,255,0.06);
  }}
  [data-testid="stFileUploaderDropzoneInstructions"] span,
  [data-testid="stFileUploaderDropzoneInstructions"] p {{
      color: rgba(255,255,255,0.65) !important;
  }}

  /* ── Expander ── */
  [data-testid="stExpander"] {{
      background: rgba(255,255,255,0.06) !important;
      border: 1px solid rgba(255,255,255,0.15) !important;
      border-radius: 6px;
  }}

  /* ── Success / error ── */
  .stSuccess, .stError {{ border-radius: 6px; }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# HEADER  (inside the white card, above form)
# ─────────────────────────────────────────────────────────────
col_logo, col_title = st.columns([1, 6])
with col_logo:
    if logo_b64:
        st.markdown(
            f'<img src="data:image/png;base64,{logo_b64}" '
            f'style="width:260px;max-width:100%;display:block;margin-top:0.3rem;" />',
            unsafe_allow_html=True,
        )

with col_title:
    st.markdown(
        "<h2 style='margin:0.3rem 0 0.1rem 0;color:white;font-size:1.55rem'>"
        "PVPAT — SCADA Data Submission Portal</h2>"
        "<p style='margin:0;color:rgba(255,255,255,0.65);font-size:0.88rem'>"
        "8p2 Advisory &nbsp;·&nbsp; A Dolfines Company</p>",
        unsafe_allow_html=True,
    )

st.markdown(
    "<p style='color:rgba(255,255,255,0.80);font-size:0.88rem;margin:0.6rem 0 0 0;max-width:750px'>"
    "Please answer the setup questions below — the upload sections will adapt to your "
    "site configuration automatically. Once submitted, our team will contact you to "
    "confirm receipt and schedule the analysis.</p>",
    unsafe_allow_html=True,
)
st.divider()


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def step(n: int, title: str):
    st.markdown(f"<div class='step-hdr'>Step {n} — {title}</div>",
                unsafe_allow_html=True)

def sub(title: str, required: bool = True):
    badge = "<span class='req'>REQUIRED</span>" if required \
            else "<span class='opt'>OPTIONAL</span>"
    st.markdown(f"<div class='sub-hdr'>{title} {badge}</div>",
                unsafe_allow_html=True)

def _count(v):
    if isinstance(v, dict): return sum(len(x) for x in v.values())
    if v is None: return 0
    return len(v)


# ═════════════════════════════════════════════════════════════
# STEP 1 — SETUP
# ═════════════════════════════════════════════════════════════
step(1, "Submission Setup")
st.caption("These answers control how the upload sections below are structured.")

c1, c2, c3 = st.columns(3)
with c1:
    n_sites = st.selectbox(
        "How many sites are you submitting data for?",
        [1, 2, 3, 4, 5], index=0)
with c2:
    inv_upload_mode = st.radio(
        "How is your inverter data organised?",
        ["All inverters in one set of files",
         "Split by inverter group / substation"],
        index=0,
        help="Choose 'split' if your SCADA exports one file per group of inverters.")
with c3:
    data_years = st.multiselect(
        "Which years does your data cover?",
        [str(y) for y in range(2019, 2027)],
        default=[])

st.divider()

split_mode = (inv_upload_mode == "Split by inverter group / substation")


# ═════════════════════════════════════════════════════════════
# STEP 2 — CONTACT & PROJECT
# ═════════════════════════════════════════════════════════════
step(2, "Contact & Project Details")

c1, c2, c3 = st.columns(3)
with c1:
    contact_name  = st.text_input("Your full name *",     placeholder="Your name")
    contact_email = st.text_input("Your email address *", placeholder="your@company.com")
with c2:
    client_name   = st.text_input("Client / Company *",   placeholder="Solar Company")
    client_ref    = st.text_input("Contract / PO reference (optional)")
with c3:
    notes = st.text_area(
        "Notes for the analysis team (optional)",
        placeholder="Known data gaps, curtailment periods, maintenance events…",
        height=103)

st.divider()


# ═════════════════════════════════════════════════════════════
# STEP 3 — PER-SITE DATA
# ═════════════════════════════════════════════════════════════
step(3, f"Site Data — {int(n_sites)} site(s)")

site_tabs = st.tabs([f"Site {i+1}" for i in range(int(n_sites))])
site_data = []

for idx, tab in enumerate(site_tabs):
    with tab:

        # ── Site identification ───────────────────────────────
        sub("Site Identification")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            s_name    = st.text_input("Site name *",       key=f"sn_{idx}", placeholder="Solar Farm")
            s_country = st.text_input("Country *",         key=f"sc_{idx}", placeholder="e.g. France")
        with c2:
            s_region  = st.text_input("Region / Dept.",    key=f"sr_{idx}", placeholder="e.g. Meuse")
            s_cod     = st.date_input("Commercial Op. Date (approx.)", key=f"cod_{idx}", value=None)
        with c3:
            s_n_inv   = st.number_input("Total number of inverters *", key=f"ni_{idx}",
                                        min_value=1, value=31, step=1)
            s_inv_kw  = st.number_input("Inverter AC rating (kW)",    key=f"ik_{idx}",
                                        min_value=1.0, value=250.0, step=5.0)
            s_inv_mdl = st.text_input( "Inverter brand / model",      key=f"im_{idx}",
                                       placeholder="e.g. Sungrow SG250HX")
        with c4:
            s_n_mod   = st.number_input("Number of modules",          key=f"nm_{idx}",
                                        min_value=1, value=21402, step=100)
            s_mod_wp  = st.number_input("Module power (Wp)",          key=f"mw_{idx}",
                                        min_value=1.0, value=460.0, step=5.0)
            s_mod_br  = st.text_input( "Module brand / model",        key=f"mb_{idx}",
                                       placeholder="e.g. First Solar Series 6")

        # ── Inverter power data ───────────────────────────────
        sub("Inverter Power Data (10-min SCADA)")
        st.caption("Expected columns: `Time_UDT ; EQUIP ; PAC` (semicolon-separated). "
                   "Upload one file per year, or multiple files if split by group.")

        inv_files = {}
        if not split_mode:
            files = st.file_uploader(
                f"All inverter power files — {int(s_n_inv)} inverters",
                type=["csv"], accept_multiple_files=True, key=f"inv_{idx}")
            inv_files["all"] = files or []
        else:
            n_groups = st.number_input(
                "How many inverter groups / substations?",
                min_value=1, max_value=20, value=2, step=1, key=f"ng_{idx}")
            grp_cols = st.columns(min(int(n_groups), 4))
            for g in range(int(n_groups)):
                with grp_cols[g % 4]:
                    files = st.file_uploader(
                        f"Group {g+1} inverter files",
                        type=["csv"], accept_multiple_files=True, key=f"inv_g{g}_{idx}")
                    inv_files[f"group_{g+1}"] = files or []

        # ── Irradiance ────────────────────────────────────────
        sub("On-site Irradiance Data")
        st.caption("GHI (and optionally POA, ambient temperature). "
                   "Expected columns: `Time_UDT ; GHI (W/m²)`.")
        irr_files = st.file_uploader(
            "Irradiance CSV files (one per year)",
            type=["csv"], accept_multiple_files=True, key=f"irr_{idx}") or []

        # ── Any other data ────────────────────────────────────
        sub("Any Other Data", required=False)
        st.caption("Anything additional — alarm/fault export, grid metering, curtailment log, "
                   "maintenance records, string data, site single-line diagram, photos…")
        other_files = st.file_uploader(
            "Additional files (CSV, PDF, XLSX, JPG, PNG…)",
            type=["csv","pdf","xlsx","xls","docx","jpg","jpeg","png"],
            accept_multiple_files=True, key=f"other_{idx}") or []

        site_data.append({
            "name":      s_name,
            "country":   s_country,
            "region":    s_region,
            "cod":       str(s_cod) if s_cod else None,
            "n_inv":     int(s_n_inv),
            "inv_kw":    float(s_inv_kw),
            "inv_model": s_inv_mdl,
            "n_mod":     int(s_n_mod),
            "mod_wp":    float(s_mod_wp),
            "mod_brand": s_mod_br,
            "inv_files": inv_files,
            "irr_files": irr_files,
            "other_files": other_files,
        })

st.divider()


# ═════════════════════════════════════════════════════════════
# STEP 4 — REVIEW & SUBMIT
# ═════════════════════════════════════════════════════════════
step(4, "Review & Submit")

# Validation
errors = []
if not contact_name.strip():
    errors.append("Your full name is required (Step 2).")
if not contact_email.strip() or "@" not in contact_email:
    errors.append("A valid email address is required (Step 2).")
if not client_name.strip():
    errors.append("Client / Company name is required (Step 2).")
for i, s in enumerate(site_data):
    if not s["name"].strip():
        errors.append(f"Site {i+1}: site name is required.")
    if not s["country"].strip():
        errors.append(f"Site {i+1}: country is required.")
    if _count(s["inv_files"]) == 0:
        errors.append(f"Site {i+1}: at least one inverter power CSV must be uploaded.")
    if _count(s["irr_files"]) == 0:
        errors.append(f"Site {i+1}: at least one irradiance CSV must be uploaded.")

# Summary
for i, s in enumerate(site_data):
    label = s["name"] or f"Site {i+1}"
    n_inv = _count(s["inv_files"])
    n_irr = _count(s["irr_files"])
    n_oth = _count(s["other_files"])
    with st.expander(f"📍 {label} — summary", expanded=(int(n_sites) == 1)):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"{'✅' if n_inv else '⚠️'} **Inverter power:** {n_inv} file(s)")
            st.markdown(f"{'✅' if n_irr else '⚠️'} **Irradiance:** {n_irr} file(s)")
        with c2:
            st.markdown(f"{'✅' if n_oth else '—'} **Other data:** {n_oth} file(s)")
            st.markdown(f"🏭 **{s['n_inv']} inverters** × {s['inv_kw']:.0f} kW = "
                        f"{s['n_inv']*s['inv_kw']/1000:.1f} MW AC")
        with c3:
            st.markdown(f"📍 {s['country']}" + (f", {s['region']}" if s["region"] else ""))
            if s["cod"]:
                st.markdown(f"📅 COD: {s['cod']}")

for e in errors:
    st.error(e)

col_btn, _ = st.columns([2, 5])
with col_btn:
    submit = st.button("📤  Submit Data Package", disabled=bool(errors))


# ═════════════════════════════════════════════════════════════
# SUBMISSION
# ═════════════════════════════════════════════════════════════
if submit and not errors:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe      = lambda s: "".join(c if c.isalnum() or c in "-_" else "_" for c in s)
    pkg_name  = f"{safe(client_name.strip())}_{timestamp}"

    (SCRIPT_DIR / "submissions").mkdir(exist_ok=True)
    pkg_dir = SCRIPT_DIR / "submissions" / pkg_name
    pkg_dir.mkdir()

    def _save(f, rel):
        dest = pkg_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(f.getbuffer())

    with st.spinner("Packaging your data…"):
        meta = {
            "timestamp": timestamp,
            "client": client_name, "contact_name": contact_name,
            "contact_email": contact_email, "contract_ref": client_ref,
            "notes": notes,
            "inv_upload_mode": inv_upload_mode,
            "data_years": data_years,
            "sites": [],
        }

        for i, s in enumerate(site_data):
            folder = safe(f"site_{i+1}_{s['name'] or f'site{i+1}'}")
            sm = {k: s[k] for k in
                  ("name","country","region","cod","n_inv","inv_kw",
                   "inv_model","n_mod","mod_wp","mod_brand")}
            sm["files"] = {"inverter": {}, "irradiance": [], "other": []}

            for grp, flist in s["inv_files"].items():
                sm["files"]["inverter"][grp] = [f.name for f in flist]
                for f in flist: _save(f, f"{folder}/inverter/{grp}/{f.name}")

            for f in s["irr_files"]:
                _save(f, f"{folder}/irradiance/{f.name}")
                sm["files"]["irradiance"].append(f.name)

            for f in s["other_files"]:
                _save(f, f"{folder}/other/{f.name}")
                sm["files"]["other"].append(f.name)

            meta["sites"].append(sm)

        (pkg_dir / "submission_metadata.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp in pkg_dir.rglob("*"):
                if fp.is_file():
                    zf.write(fp, fp.relative_to(pkg_dir))
        buf.seek(0)

    total = sum(_count(s["inv_files"]) + _count(s["irr_files"]) +
                _count(s["other_files"]) for s in site_data)

    st.success(f"""
    ✅  **Thank you, {contact_name} — your submission has been received.**

    **{int(n_sites)} site(s) · {total} files** packaged for **{client_name}**.
    Our team will contact you at **{contact_email}** to confirm receipt
    and schedule the analysis and report delivery.
    """)

    st.download_button(
        "⬇️  Download your submission package (ZIP)",
        data=buf,
        file_name=f"{pkg_name}.zip",
        mime="application/zip",
    )
