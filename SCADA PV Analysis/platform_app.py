"""
platform_app.py — PVPAT Client Platform
=========================================
Login → Portfolio → Report Generation (Daily or Comprehensive)

Run:  streamlit run platform_app.py
Demo: demo@dolfines.com / pvpat2024
"""

import base64
import io
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from PIL import Image
import streamlit as st


# ── Playwright browser auto-install (needed on Streamlit Cloud) ────────────
@st.cache_resource(show_spinner=False)
def _ensure_playwright() -> bool:
    """Install Chromium browser binary if not already present. Cached once per session."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True, text=True, timeout=120,
        )
        return result.returncode == 0
    except Exception:
        return False

# ── Paths ─────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
LOGO_PATH    = SCRIPT_DIR / "8p2_logo_white.png"
FAVICON_PATH = SCRIPT_DIR / "8p2_favicon_sq.jpg"
BG_PATH      = SCRIPT_DIR / "bg_solar.jpg"

sys.path.insert(0, str(SCRIPT_DIR))
from platform_users import USERS, SITES, PRICING


# ── Page config ────────────────────────────────────────────────────────────
_fav = Image.open(FAVICON_PATH) if FAVICON_PATH.exists() else "☀️"
st.set_page_config(
    page_title="PVPAT Platform | 8p2 Advisory",
    page_icon=_fav,
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ─────────────────────────────────────────────────────────────────────────────
# ASSETS
# ─────────────────────────────────────────────────────────────────────────────

def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()

bg_b64     = _b64(BG_PATH)    if BG_PATH.exists()    else ""
logo_b64   = _b64(LOGO_PATH)  if LOGO_PATH.exists()  else ""

bg_css = (f"url('data:image/jpeg;base64,{bg_b64}')"
          if bg_b64 else
          "linear-gradient(135deg,#001a3a 0%,#003366 60%,#0a4d8c 100%)")

logo_img = (f'<img src="data:image/png;base64,{logo_b64}" '
            f'style="height:52px;width:auto;flex-shrink:0;" />'
            if logo_b64 else "")


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL CSS  (identical palette to pvpat_app.py)
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(f"""
<style>
  header[data-testid="stHeader"] {{ display:none !important; }}
  .main {{ padding-top:0 !important; }}
  [data-testid="stAppViewBlockContainer"] {{ padding-top:1.5rem !important; }}

  .stApp {{
    background-image: linear-gradient(rgba(0,10,35,0.72),rgba(0,10,35,0.72)), {bg_css};
    background-size:cover; background-position:center; background-attachment:fixed;
  }}
  .main .block-container,
  [data-testid="stAppViewBlockContainer"],
  section[data-testid="stMain"] .block-container {{
    background:rgba(0,18,55,0.82) !important; border-radius:14px;
    padding:2rem 2.5rem 2.5rem; max-width:1100px;
    box-shadow:0 8px 50px rgba(0,0,0,0.55); backdrop-filter:blur(6px);
  }}
  .stApp,.stApp p,.stApp span,.stApp label,.stApp div,
  .stApp h1,.stApp h2,.stApp h3,.stApp h4,
  .stMarkdown,.stMarkdown p,.stMarkdown li,
  [data-testid="stText"],.stCaption,
  [data-baseweb="select"] *,[data-baseweb="input"] *,
  [data-baseweb="radio"] *,[data-baseweb="checkbox"] *,
  .stSelectbox label,.stMultiSelect label,
  .stNumberInput label,.stTextInput label,
  .stTextArea label,.stDateInput label,
  .stRadio label,[data-testid="stCaptionContainer"],
  [data-testid="stWidgetLabel"],[data-testid="stHelperText"],
  [data-testid="InputInstructions"] {{ color:white !important; }}

  input::placeholder,textarea::placeholder {{
    color:rgba(255,255,255,0.40) !important; opacity:1 !important;
  }}
  input,textarea,[data-baseweb="input"] input,[data-baseweb="textarea"] textarea {{
    background:rgba(255,255,255,0.10) !important; color:white !important;
    border-color:rgba(255,255,255,0.25) !important; caret-color:white !important;
  }}
  [data-baseweb="select"] > div {{
    background:rgba(0,18,55,0.90) !important; border-color:rgba(255,255,255,0.25) !important;
  }}
  [data-baseweb="select"] [data-baseweb="select-input"],
  [data-baseweb="select"] [role="combobox"],
  [data-baseweb="select"] div[aria-selected],
  [data-baseweb="select"] span,[data-baseweb="select"] div {{ color:white !important; }}
  [data-baseweb="menu"],[data-baseweb="popover"] {{
    background:rgba(0,18,55,0.98) !important;
  }}
  [data-baseweb="menu"] li,[data-baseweb="option"] {{
    color:white !important; background:rgba(0,18,55,0.98) !important;
  }}
  [data-baseweb="menu"] li:hover,[data-baseweb="option"]:hover {{
    background:rgba(240,120,32,0.35) !important;
  }}
  [data-baseweb="tag"] {{
    background:rgba(240,120,32,0.60) !important; color:white !important;
  }}
  [data-testid="stNumberInput"] input {{
    background:rgba(0,18,55,0.70) !important; color:white !important;
    border-color:rgba(255,255,255,0.25) !important;
  }}
  [data-testid="stNumberInput"] button {{
    background:rgba(255,255,255,0.12) !important; color:white !important;
    border-color:rgba(255,255,255,0.20) !important;
  }}
  [data-baseweb="datepicker"] input,[data-testid="stDateInput"] input {{
    color:white !important;
  }}
  [data-baseweb="tab"] button,[role="tab"] {{ color:rgba(255,255,255,0.75) !important; }}
  [aria-selected="true"][role="tab"] {{
    color:white !important; border-bottom-color:#F07820 !important;
  }}
  hr {{ border-color:rgba(255,255,255,0.15) !important; }}
  html,body,[class*="css"] {{ font-family:'Open Sans',Arial,sans-serif; }}

  .step-hdr {{
    background:rgba(240,120,32,0.85); color:white; padding:0.45rem 1rem;
    border-radius:5px; font-weight:700; font-size:0.95rem; margin:1.2rem 0 0.5rem;
  }}
  .sub-hdr {{
    border-left:4px solid #F07820; padding:0.28rem 0.8rem;
    background:rgba(255,255,255,0.08); border-radius:0 4px 4px 0;
    margin:0.8rem 0 0.3rem; font-weight:600; color:white; font-size:0.87rem;
  }}
  .stButton > button {{
    background:#F07820 !important; color:white !important; border:none !important;
    border-radius:6px !important; font-weight:700 !important; font-size:1rem !important;
    padding:0.65rem 2rem !important; width:100%; transition:background 0.2s;
  }}
  .stButton > button:hover {{ background:#cc6415 !important; }}

  /* Site cards */
  .site-card {{
    background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.18);
    border-radius:10px; padding:1.1rem 1.4rem; margin-bottom:0.6rem;
    transition:border-color 0.2s;
  }}
  .site-card:hover {{ border-color:#F07820; }}
  .site-card-name {{ font-size:1.05rem; font-weight:700; color:white; margin-bottom:4px; }}
  .site-card-sub {{ font-size:0.82rem; color:rgba(255,255,255,0.62); }}
  .badge-op {{ background:#2E8B57; color:white; font-size:0.65rem; padding:2px 8px;
               border-radius:10px; margin-left:6px; vertical-align:middle; }}

  /* Login card */
  .login-card {{
    max-width:420px; margin:0 auto; background:rgba(255,255,255,0.07);
    border:1px solid rgba(255,255,255,0.18); border-radius:12px; padding:2rem 2.2rem;
  }}
  .login-title {{ font-size:1.3rem; font-weight:700; color:white; margin-bottom:4px; }}
  .login-sub {{ font-size:0.85rem; color:rgba(255,255,255,0.60); margin-bottom:1.4rem; }}

  /* Plan badge */
  .plan-unlimited {{ background:rgba(240,120,32,0.25); border:1px solid #F07820;
                      color:#F07820; border-radius:6px; padding:2px 10px;
                      font-size:0.78rem; font-weight:700; }}
  .plan-one-shot {{ background:rgba(255,255,255,0.10); border:1px solid rgba(255,255,255,0.30);
                     color:rgba(255,255,255,0.80); border-radius:6px; padding:2px 10px;
                     font-size:0.78rem; }}

  [data-testid="stExpander"] {{
    background:rgba(255,255,255,0.06) !important;
    border:1px solid rgba(255,255,255,0.15) !important; border-radius:6px;
  }}
  .stSuccess,.stError,.stWarning,.stInfo {{ border-radius:6px; }}
  [data-testid="stFileUploaderDropzone"] {{
    border:1.5px dashed rgba(255,255,255,0.30); border-radius:6px;
    background:rgba(255,255,255,0.06);
  }}
  [data-testid="stFileUploaderDropzoneInstructions"] span,
  [data-testid="stFileUploaderDropzoneInstructions"] p {{
    color:rgba(255,255,255,0.65) !important;
  }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _logged_in() -> bool:
    return st.session_state.get("user") is not None

def _logout():
    for k in ["user", "view", "selected_site", "report_type"]:
        st.session_state.pop(k, None)
    st.rerun()

def _set(key, val):
    st.session_state[key] = val
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# HEADER  (shown on all authenticated pages)
# ─────────────────────────────────────────────────────────────────────────────

def _render_header(show_logout=True):
    user = st.session_state.get("user", {})
    plan = user.get("plan", "")
    plan_html = (
        "<span class='plan-unlimited'>UNLIMITED</span>" if plan == "unlimited"
        else "<span class='plan-one-shot'>ONE-SHOT</span>"
    ) if plan else ""

    logout_link = ""
    col_hdr, col_btn = st.columns([5, 1])
    with col_hdr:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:1.4rem;margin-bottom:0.6rem;">
          {logo_img}
          <div>
            <div style="font-size:1.45rem;font-weight:700;color:white;line-height:1.2;">
              PVPAT — Performance Analysis Platform
            </div>
            <div style="font-size:0.84rem;color:rgba(255,255,255,0.55);margin-top:0.15rem;">
              8p2 Advisory &nbsp;·&nbsp; A Dolfines Company
              {"&nbsp;&nbsp;" + plan_html if plan_html else ""}
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    if show_logout and _logged_in():
        with col_btn:
            st.markdown("<div style='margin-top:1rem;'>", unsafe_allow_html=True)
            if st.button("Log out"):
                _logout()
            st.markdown("</div>", unsafe_allow_html=True)
    st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# VIEW: LOGIN
# ─────────────────────────────────────────────────────────────────────────────

def _view_login():
    _render_header(show_logout=False)

    st.markdown("""
    <div class="login-card">
      <div class="login-title">Client Login</div>
      <div class="login-sub">Enter your credentials to access your portfolio.</div>
    </div>
    """, unsafe_allow_html=True)

    # Centre the form
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        email    = st.text_input("Email address", placeholder="you@company.com", key="login_email")
        password = st.text_input("Password", type="password", key="login_pw")
        submit   = st.button("Sign In →")

        if submit:
            user = USERS.get(email.strip().lower())
            if user and user["password"] == password:
                st.session_state["user"]  = {**user, "email": email.strip().lower()}
                st.session_state["view"]  = "portfolio"
                st.rerun()
            else:
                st.error("Invalid email or password.")

    st.markdown("""
    <div style="text-align:center;margin-top:2rem;font-size:0.8rem;color:rgba(255,255,255,0.40);">
      Demo credentials: &nbsp;<code style="color:#F07820;">demo@dolfines.com</code>
      &nbsp;/&nbsp; <code style="color:#F07820;">pvpat2024</code>
    </div>
    """, unsafe_allow_html=True)

    # Pricing teaser
    st.markdown("---")
    st.markdown("""
    <div style="text-align:center;margin-top:0.8rem;">
      <span style="font-size:0.88rem;color:rgba(255,255,255,0.55);">
        No account yet?
        &nbsp;·&nbsp; One-Shot Report: <strong style="color:#F07820;">€3 500</strong>
        &nbsp;·&nbsp; Platform Access (unlimited reports): <strong style="color:#F07820;">€1 000/month</strong>
      </span><br/>
      <span style="font-size:0.8rem;color:rgba(255,255,255,0.35);margin-top:4px;display:block;">
        Contact <a href="mailto:contact@8p2advisory.com" style="color:#F07820;">contact@8p2advisory.com</a>
      </span>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# VIEW: PORTFOLIO
# ─────────────────────────────────────────────────────────────────────────────

def _view_portfolio():
    _render_header()
    user = st.session_state["user"]

    st.markdown(f"""
    <div style="margin-bottom:1.2rem;">
      <span style="font-size:1.05rem;color:rgba(255,255,255,0.90);">
        Welcome back, <strong>{user['display_name']}</strong>
        &nbsp;—&nbsp; {user['company']}
      </span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        "<div class='step-hdr'>Your Site Portfolio</div>",
        unsafe_allow_html=True)

    site_ids = user.get("sites", [])
    if not site_ids:
        st.info("No sites configured for your account. Contact your 8p2 advisor.")
        return

    for site_id in site_ids:
        site = SITES.get(site_id, {})
        if not site:
            continue
        status     = site.get("status", "operational")
        status_lbl = {"operational": "OPERATIONAL", "maintenance": "MAINTENANCE",
                      "offline": "OFFLINE"}.get(status, status.upper())
        status_col = {"operational": "#2E8B57", "maintenance": "#E67E22",
                      "offline": "#C0392B"}.get(status, "#888")

        col_info, col_btn = st.columns([4, 1])
        with col_info:
            st.markdown(f"""
            <div class="site-card">
              <div class="site-card-name">
                {site['display_name']}
                <span style="background:{status_col};color:white;font-size:0.62rem;
                  padding:2px 8px;border-radius:10px;margin-left:8px;vertical-align:middle;
                  font-weight:700;">{status_lbl}</span>
              </div>
              <div class="site-card-sub">
                📍 {site.get('region','')}, {site.get('country','')}
                &nbsp;·&nbsp; COD {site.get('cod','—')}
                &nbsp;·&nbsp; {site.get('n_inverters','?')} × {site.get('inverter_model','—')}
                &nbsp;·&nbsp; {site.get('cap_dc_kwp',0):.0f} kWp DC
                / {site.get('cap_ac_kw',0):.0f} kW AC
                &nbsp;·&nbsp; {site.get('technology','—')}
              </div>
            </div>
            """, unsafe_allow_html=True)
        with col_btn:
            st.markdown("<div style='margin-top:1.2rem;'>", unsafe_allow_html=True)
            if st.button("Generate Report →", key=f"go_{site_id}"):
                st.session_state["selected_site"] = site_id
                st.session_state["view"] = "report_select"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # Pricing reminder
    st.divider()
    plan = user.get("plan", "")
    if plan == "unlimited":
        st.markdown("""
        <div style="font-size:0.82rem;color:rgba(255,255,255,0.45);text-align:center;">
          ✅ Your plan includes <strong>unlimited reports</strong> for all sites.
          &nbsp;·&nbsp; €1 000/month
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="font-size:0.82rem;color:rgba(255,255,255,0.45);text-align:center;">
          One-Shot plan: each report generation counts as one use.
          Upgrade to unlimited for €1 000/month.
        </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# VIEW: REPORT TYPE SELECTION
# ─────────────────────────────────────────────────────────────────────────────

def _view_report_select():
    _render_header()

    site_id = st.session_state.get("selected_site", "")
    site    = SITES.get(site_id, {})

    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("← Back to Portfolio"):
            st.session_state["view"] = "portfolio"
            st.rerun()

    st.markdown(
        f"<div class='step-hdr'>Generate Report — {site.get('display_name','')}</div>",
        unsafe_allow_html=True)

    st.markdown("""
    <p style="color:rgba(255,255,255,0.75);font-size:0.90rem;margin-bottom:1.2rem;">
      Choose the type of report you want to generate for this site.
    </p>""", unsafe_allow_html=True)

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("""
        <div style="background:rgba(240,120,32,0.12);border:1.5px solid #F07820;
          border-radius:10px;padding:1.4rem 1.6rem;min-height:200px;">
          <div style="font-size:1.1rem;font-weight:700;color:#F07820;margin-bottom:8px;">
            ☀️ Simple Daily Report
          </div>
          <ul style="color:rgba(255,255,255,0.80);font-size:0.87rem;
            line-height:1.7;padding-left:1.2rem;">
            <li>4–5 pages, generated in seconds</li>
            <li>Specific yield &amp; PR per inverter</li>
            <li>Fleet availability dashboard</li>
            <li>Daily irradiance profile</li>
            <li>Energy loss waterfall</li>
            <li>Alerts &amp; alarms with recommended fixes</li>
          </ul>
        </div>""", unsafe_allow_html=True)
        st.markdown("<div style='margin-top:0.6rem;'>", unsafe_allow_html=True)
        if st.button("Create Daily Report →", key="btn_daily"):
            st.session_state["report_type"] = "daily"
            st.session_state["view"] = "daily_config"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_b:
        st.markdown("""
        <div style="background:rgba(0,61,107,0.35);border:1.5px solid rgba(255,255,255,0.20);
          border-radius:10px;padding:1.4rem 1.6rem;min-height:200px;">
          <div style="font-size:1.1rem;font-weight:700;color:white;margin-bottom:8px;">
            📊 Comprehensive Analysis Report
          </div>
          <ul style="color:rgba(255,255,255,0.75);font-size:0.87rem;
            line-height:1.7;padding-left:1.2rem;">
            <li>20–25 pages, full technical analysis</li>
            <li>Monthly energy, PR &amp; irradiance trends</li>
            <li>Inverter fleet comparison &amp; heatmaps</li>
            <li>Data quality &amp; SARAH coherence</li>
            <li>Loss analysis &amp; technology risk register</li>
            <li>Full action punchlist with EUR impact</li>
          </ul>
        </div>""", unsafe_allow_html=True)
        st.markdown("<div style='margin-top:0.6rem;'>", unsafe_allow_html=True)
        if st.button("Create Comprehensive Report →", key="btn_comp"):
            st.session_state["report_type"] = "comprehensive"
            st.session_state["view"] = "comp_info"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# VIEW: DAILY REPORT CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

def _view_daily_config():
    _render_header()

    site_id = st.session_state.get("selected_site", "")
    site    = SITES.get(site_id, {})

    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("← Back"):
            st.session_state["view"] = "report_select"
            st.rerun()

    st.markdown(
        f"<div class='step-hdr'>Daily Report — {site.get('display_name','')}</div>",
        unsafe_allow_html=True)

    st.markdown("""
    <div class="sub-hdr">Report Configuration</div>""", unsafe_allow_html=True)

    yesterday = date.today() - timedelta(days=1)
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        report_date = st.date_input(
            "Report date",
            value=yesterday,
            max_value=date.today(),
            help="Select the day you want to analyse.",
        )
    with c2:
        data_source = st.radio(
            "Data source",
            ["Site SCADA files (auto)", "Upload CSV files"],
            index=0,
        )

    uploaded_inv  = []
    uploaded_irr  = []
    tmp_data_dir  = None

    if data_source == "Upload CSV files":
        st.markdown("""<div class="sub-hdr">Upload SCADA Data</div>""",
                    unsafe_allow_html=True)
        cu1, cu2 = st.columns(2)
        with cu1:
            st.caption("Inverter power CSV(s) — columns: `Time_UDT ; EQUIP ; PAC`")
            uploaded_inv = st.file_uploader(
                "Inverter power files", type=["csv"],
                accept_multiple_files=True, key="up_inv")
        with cu2:
            st.caption("Irradiance CSV — columns: `Time_UDT ; GHI`")
            uploaded_irr = st.file_uploader(
                "Irradiance file", type=["csv"],
                accept_multiple_files=True, key="up_irr")

    st.divider()

    _, col_btn, _ = st.columns([2, 2, 2])
    with col_btn:
        generate = st.button("⚡ Generate Daily Report")

    if generate:
        import tempfile, shutil
        from pathlib import Path as _Path

        # Resolve data directory
        if data_source == "Upload CSV files" and (uploaded_inv or uploaded_irr):
            tmp = tempfile.mkdtemp(prefix="pvpat_daily_")
            tmp_data_dir = _Path(tmp)
            for f in (uploaded_inv or []):
                (tmp_data_dir / f.name).write_bytes(f.getbuffer().tobytes())
            for f in (uploaded_irr or []):
                name = f.name
                # Prefix with "irradiance_" so loader recognises it
                if not any(k in name.lower() for k in ("irr","ghi","irradiance","meteo")):
                    name = "irradiance_" + name
                (tmp_data_dir / name).write_bytes(f.getbuffer().tobytes())
        else:
            tmp_data_dir = _Path(site["data_dir"]) if "data_dir" in site else None

        with st.spinner("Installing browser runtime… (first run only, ~30 s)"):
            pw_ok = _ensure_playwright()

        with st.spinner("Analysing data and generating report…"):
            try:
                from report.build_daily_report_data import build_daily_report

                pdf_path, html_path = build_daily_report(
                    site_cfg    = site,
                    report_date = report_date,
                    data_dir    = tmp_data_dir,
                    skip_pdf    = not pw_ok,
                )

                if pdf_path and pdf_path.exists():
                    pdf_bytes = pdf_path.read_bytes()
                    st.success(f"✅ Daily report generated: **{pdf_path.name}**")
                    st.download_button(
                        label    = "⬇️  Download PDF Report",
                        data     = pdf_bytes,
                        file_name= pdf_path.name,
                        mime     = "application/pdf",
                    )
                else:
                    # PDF unavailable (no browser binary on this server) — offer HTML
                    html_bytes = html_path.read_bytes()
                    st.warning(
                        "PDF generation requires a local installation. "
                        "Downloading the report as HTML instead — open in any browser "
                        "and use **File → Print → Save as PDF**."
                    )
                    st.download_button(
                        label    = "⬇️  Download Report (HTML)",
                        data     = html_bytes,
                        file_name= html_path.name,
                        mime     = "text/html",
                    )

            except Exception as exc:
                st.error(f"Report generation failed: {exc}")
                st.exception(exc)
            finally:
                if data_source == "Upload CSV files" and tmp_data_dir:
                    try:
                        shutil.rmtree(str(tmp_data_dir), ignore_errors=True)
                    except Exception:
                        pass


# ─────────────────────────────────────────────────────────────────────────────
# SHAREPOINT HELPERS  (reused from pvpat_app.py)
# ─────────────────────────────────────────────────────────────────────────────

def _sharepoint_session():
    import msal, requests as _req
    cfg = st.secrets["sharepoint"]
    app = msal.ConfidentialClientApplication(
        cfg["client_id"],
        authority=f"https://login.microsoftonline.com/{cfg['tenant_id']}",
        client_credential=cfg["client_secret"],
    )
    tok = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in tok:
        raise RuntimeError(tok.get("error_description", "SharePoint auth failed"))
    token = tok["access_token"]
    import requests as _req
    sr = _req.get(
        "https://graph.microsoft.com/v1.0/sites/8p2france.sharepoint.com:/sites/Serveur",
        headers={"Authorization": f"Bearer {token}"}, timeout=15,
    )
    sr.raise_for_status()
    return token, sr.json()["id"]

def _sp_put(token, site_id, sp_path, data):
    import requests as _req
    url = (f"https://graph.microsoft.com/v1.0/sites/{site_id}"
           f"/drive/root:/{sp_path}:/content")
    r = _req.put(url,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/octet-stream"},
        data=data, timeout=300)
    r.raise_for_status()

def _count(v):
    if isinstance(v, dict): return sum(len(x) for x in v.values())
    if v is None: return 0
    return len(v)


# ─────────────────────────────────────────────────────────────────────────────
# VIEW: COMPREHENSIVE REPORT — DATA SUBMISSION
# ─────────────────────────────────────────────────────────────────────────────

def _view_comp_info():
    import io as _io, json as _json, zipfile as _zip
    from datetime import datetime as _dt

    _render_header()
    user    = st.session_state["user"]
    site_id = st.session_state.get("selected_site", "")
    site    = SITES.get(site_id, {})

    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("← Back"):
            st.session_state["view"] = "report_select"
            st.rerun()

    st.markdown(
        f"<div class='step-hdr'>Comprehensive Report — {site.get('display_name','')}</div>",
        unsafe_allow_html=True)

    st.markdown("""
    <p style="color:rgba(255,255,255,0.75);font-size:0.90rem;margin-bottom:0.4rem;">
      Upload your SCADA export files below. Once submitted, the 8p2 team will run the
      full analysis pipeline and deliver your PDF report within the agreed timeframe.
    </p>""", unsafe_allow_html=True)

    # ── Setup ──────────────────────────────────────────────────────────────────
    st.markdown("<div class='sub-hdr'>Data Configuration</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        data_years = st.multiselect(
            "Years covered by the data",
            [str(y) for y in range(2019, 2027)], default=[])
        inv_upload_mode = st.radio(
            "Inverter data organisation",
            ["All inverters in one set of files",
             "Split by inverter group / substation"], index=0)
    with c2:
        notes = st.text_area(
            "Notes for the analysis team (optional)",
            placeholder="Known data gaps, curtailment periods, maintenance events…",
            height=110)

    split_mode = (inv_upload_mode == "Split by inverter group / substation")

    # ── Inverter power files ────────────────────────────────────────────────────
    st.markdown("<div class='sub-hdr'>Inverter Power Data (10-min SCADA)</div>",
                unsafe_allow_html=True)
    st.caption("Expected columns: `Time_UDT ; EQUIP ; PAC` (semicolon-separated). "
               "One file per year, or multiple files if split by group.")

    inv_files: dict = {}
    if not split_mode:
        files = st.file_uploader(
            f"All inverter power files — {site.get('n_inverters','?')} inverters",
            type=["csv"], accept_multiple_files=True, key="comp_inv_all")
        inv_files["all"] = files or []
    else:
        n_groups = st.number_input("Number of inverter groups / substations",
                                   min_value=1, max_value=20, value=2, step=1,
                                   key="comp_ngroups")
        grp_cols = st.columns(min(int(n_groups), 4))
        for g in range(int(n_groups)):
            with grp_cols[g % 4]:
                files = st.file_uploader(
                    f"Group {g+1} files", type=["csv"],
                    accept_multiple_files=True, key=f"comp_inv_g{g}")
                inv_files[f"group_{g+1}"] = files or []

    # ── Irradiance ──────────────────────────────────────────────────────────────
    st.markdown("<div class='sub-hdr'>Irradiance Data</div>", unsafe_allow_html=True)
    st.caption("GHI (and optionally POA, ambient temperature). "
               "Expected columns: `Time_UDT ; GHI (W/m²)`.")
    irr_files = st.file_uploader(
        "Irradiance CSV files (one per year)",
        type=["csv"], accept_multiple_files=True, key="comp_irr") or []

    # ── Other ───────────────────────────────────────────────────────────────────
    st.markdown("<div class='sub-hdr'>Additional Data (optional)</div>",
                unsafe_allow_html=True)
    st.caption("Alarm/fault exports, grid metering, curtailment logs, maintenance records, "
               "string data, single-line diagram, site photos…")
    other_files = st.file_uploader(
        "Additional files (CSV, PDF, XLSX, JPG, PNG…)",
        type=["csv","pdf","xlsx","xls","docx","jpg","jpeg","png"],
        accept_multiple_files=True, key="comp_other") or []

    # ── Validation & summary ────────────────────────────────────────────────────
    st.divider()
    errors = []
    if _count(inv_files) == 0:
        errors.append("At least one inverter power CSV must be uploaded.")
    if _count(irr_files) == 0:
        errors.append("At least one irradiance CSV must be uploaded.")

    n_inv = _count(inv_files)
    n_irr = _count(irr_files)
    n_oth = _count(other_files)

    with st.expander(f"📍 {site.get('display_name','')} — submission summary",
                     expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"{'✅' if n_inv else '⚠️'} **Inverter power:** {n_inv} file(s)")
            st.markdown(f"{'✅' if n_irr else '⚠️'} **Irradiance:** {n_irr} file(s)")
        with c2:
            st.markdown(f"{'✅' if n_oth else '—'} **Other data:** {n_oth} file(s)")
            st.markdown(f"🏭 **{site.get('n_inverters','?')} inverters** × "
                        f"{site.get('inv_ac_kw',0):.0f} kW = "
                        f"{site.get('cap_ac_kw',0)/1000:.1f} MW AC")
        with c3:
            st.markdown(f"📍 {site.get('region','')}, {site.get('country','')}")
            st.markdown(f"📅 COD: {site.get('cod','—')}")
            if data_years:
                st.markdown(f"📆 Data years: {', '.join(data_years)}")

    for e in errors:
        st.error(e)

    col_btn, _ = st.columns([2, 5])
    with col_btn:
        submit = st.button("📤  Submit Data for Comprehensive Analysis",
                           disabled=bool(errors))

    # ── Submission ──────────────────────────────────────────────────────────────
    if submit and not errors:
        timestamp = _dt.now().strftime("%Y%m%d_%H%M%S")
        safe      = lambda s: "".join(c if c.isalnum() or c in "-_" else "_" for c in s)
        pkg_name  = f"PVPAT_{safe(user['company'])}_{safe(site.get('display_name','site'))}_{timestamp}"

        with st.spinner("Packaging and uploading your data…"):
            meta = {
                "timestamp": timestamp, "portal": "pvpat-platform",
                "client": user["company"], "contact_name": user["display_name"],
                "contact_email": user["email"],
                "site": site.get("display_name",""), "notes": notes,
                "inv_upload_mode": inv_upload_mode, "data_years": data_years,
            }

            buf     = _io.BytesIO()
            uploads = []

            with _zip.ZipFile(buf, "w", _zip.ZIP_DEFLATED) as zf:
                for grp, flist in inv_files.items():
                    for f in flist:
                        fbytes = f.getbuffer().tobytes()
                        rel    = f"inverter/{grp}/{f.name}"
                        zf.writestr(rel, fbytes)
                        uploads.append((rel, fbytes))

                for f in irr_files:
                    fbytes = f.getbuffer().tobytes()
                    rel    = f"irradiance/{f.name}"
                    zf.writestr(rel, fbytes)
                    uploads.append((rel, fbytes))

                for f in other_files:
                    fbytes = f.getbuffer().tobytes()
                    rel    = f"other/{f.name}"
                    zf.writestr(rel, fbytes)
                    uploads.append((rel, fbytes))

                meta_bytes = _json.dumps(meta, indent=2, ensure_ascii=False).encode()
                zf.writestr("submission_metadata.json", meta_bytes)
                uploads.append(("submission_metadata.json", meta_bytes))

            buf.seek(0)

            sp_ok, sp_err = False, ""
            if "sharepoint" in st.secrets:
                try:
                    sp_tok, sp_sid = _sharepoint_session()
                    for rel, fbytes in uploads:
                        _sp_put(sp_tok, sp_sid,
                                f"Partage client/{pkg_name}/{rel}", fbytes)
                    sp_ok = True
                except Exception as exc:
                    sp_err = str(exc)

        total = n_inv + n_irr + n_oth
        if sp_ok:
            st.success(f"""
            ✅ **Submission received — thank you, {user['display_name']}.**

            **{total} files** for **{site.get('display_name','')}** saved to SharePoint.
            The 8p2 team will contact you at **{user['email']}** to confirm receipt
            and schedule report delivery.
            """)
        elif sp_err:
            st.error(f"SharePoint upload failed — {sp_err}")
            st.warning("Please download the ZIP below and send it to your 8p2 contact.")
        else:
            st.success(f"✅ Packaged {total} files for **{site.get('display_name','')}**.")

        st.download_button(
            "⬇️  Download your submission package (ZIP)",
            data=buf, file_name=f"{pkg_name}.zip", mime="application/zip",
        )


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────────────────────────────────

if not _logged_in():
    _view_login()
else:
    view = st.session_state.get("view", "portfolio")
    if view == "portfolio":
        _view_portfolio()
    elif view == "report_select":
        _view_report_select()
    elif view == "daily_config":
        _view_daily_config()
    elif view == "comp_info":
        _view_comp_info()
    else:
        _view_portfolio()
