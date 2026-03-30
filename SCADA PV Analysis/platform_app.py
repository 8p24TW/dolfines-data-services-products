"""
platform_app.py — PVPAT Client Platform
=========================================
Login → Portfolio → Report Generation (Daily or Comprehensive)

Run:  streamlit run platform_app.py
Demo: demo@dolfines.com / pvpat2024
"""

import base64
import io
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from PIL import Image
import streamlit as st



# ── Paths ─────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
LOGO_PATH    = SCRIPT_DIR / "dolfines_logo_white.png"
FAVICON_PATH = SCRIPT_DIR / "dolfines_favicon.png"
BG_PATH       = SCRIPT_DIR / "bg_solar.jpg"
BG_SOLAR2_PATH = SCRIPT_DIR / "bg_solar2.jpg"
BG_WIND_PATH  = SCRIPT_DIR / "bg_wind.jpg"

sys.path.insert(0, str(SCRIPT_DIR))
from platform_users import USERS, SITES, PRICING

# ── Persistent custom-site storage ────────────────────────────────────────────
# L1: local filesystem — fast; present within a single deployment lifecycle
# L2: SharePoint — survives redeploys; loaded once then cached to L1
_CUSTOM_SITES_FILE = SCRIPT_DIR / "custom_sites.json"
_SP_CUSTOM_SITES_PATH = "pvpat_platform/custom_sites.json"


def _looks_like_site_cfg(value) -> bool:
    return isinstance(value, dict) and any(
        key in value for key in ("display_name", "site_type", "cap_dc_kwp", "technology")
    )


def _looks_like_report_entry(value) -> bool:
    return isinstance(value, dict) and any(
        key in value for key in ("report_type", "filename", "generated_at", "sp_path", "date")
    )


def _normalize_custom_sites_payload(raw) -> dict:
    if isinstance(raw, dict) and isinstance(raw.get("custom_sites"), dict):
        raw = raw["custom_sites"]
    if not isinstance(raw, dict):
        return {}
    return {site_id: cfg for site_id, cfg in raw.items() if _looks_like_site_cfg(cfg)}


def _normalize_report_history_payload(raw) -> dict:
    if isinstance(raw, dict) and isinstance(raw.get("report_history"), dict):
        raw = raw["report_history"]
    if not isinstance(raw, dict):
        return {}
    normalized = {}
    for site_id, entries in raw.items():
        if not isinstance(entries, list):
            continue
        cleaned = [entry for entry in entries if _looks_like_report_entry(entry)]
        if cleaned:
            normalized[site_id] = cleaned[:20]
    return normalized


def _load_custom_sites_from_disk() -> dict:
    # L1: local file (fast — available for all sessions in this deployment)
    try:
        if _CUSTOM_SITES_FILE.exists():
            return _normalize_custom_sites_payload(
                json.loads(_CUSTOM_SITES_FILE.read_text(encoding="utf-8"))
            )
    except Exception:
        pass
    # L2: SharePoint (called once after a redeploy wipes the local file)
    try:
        import requests as _req
        token, site_id = _sharepoint_session()
        url = (f"https://graph.microsoft.com/v1.0/sites/{site_id}"
               f"/drive/root:/{_SP_CUSTOM_SITES_PATH}:/content")
        r = _req.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
        if r.status_code == 200:
            data = _normalize_custom_sites_payload(r.json())
            # Populate L1 so subsequent sessions in this deployment skip SharePoint
            try:
                _CUSTOM_SITES_FILE.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass
            return data
    except Exception:
        pass
    return {}


def _save_custom_sites_to_disk() -> None:
    data = st.session_state.get("custom_sites", {})
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    # L1: local file
    try:
        _CUSTOM_SITES_FILE.write_text(payload, encoding="utf-8")
    except Exception:
        pass
    # L2: SharePoint (persists across redeploys)
    try:
        token, site_id = _sharepoint_session()
        _sp_put(token, site_id, _SP_CUSTOM_SITES_PATH, payload.encode())
    except Exception:
        pass
# ── Report history storage (same L1/L2 pattern as custom_sites) ───────────
_REPORT_HISTORY_FILE = SCRIPT_DIR / "report_history.json"
_SP_REPORT_HISTORY_PATH = "pvpat_platform/report_history.json"
_SP_REPORTS_DIR = "pvpat_platform/reports"
_LEGACY_REPORTS_DIR = SCRIPT_DIR / "previous reports"


def _list_legacy_reports() -> list[dict]:
    if not _LEGACY_REPORTS_DIR.exists():
        return []
    legacy = []
    for path in sorted(_LEGACY_REPORTS_DIR.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".pdf", ".doc", ".docx", ".ppt", ".pptx"}:
            continue
        legacy.append({
            "filename": path.name,
            "generated_at": date.fromtimestamp(path.stat().st_mtime).isoformat(),
            "local_path": str(path),
            "report_type": path.suffix.lower().lstrip("."),
            "date": "Legacy file",
        })
    return legacy[:20]


def _load_report_history() -> dict:
    """Return {site_id: [metadata, ...]} newest-first, up to 20 per site."""
    try:
        if _REPORT_HISTORY_FILE.exists():
            return _normalize_report_history_payload(
                json.loads(_REPORT_HISTORY_FILE.read_text(encoding="utf-8"))
            )
    except Exception:
        pass
    try:
        import requests as _req
        token, sp_site_id = _sharepoint_session()
        url = (f"https://graph.microsoft.com/v1.0/sites/{sp_site_id}"
               f"/drive/root:/{_SP_REPORT_HISTORY_PATH}:/content")
        r = _req.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
        if r.status_code == 200:
            data = _normalize_report_history_payload(r.json())
            try:
                _REPORT_HISTORY_FILE.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass
            return data
    except Exception:
        pass
    return {}


def _save_report_to_history(site_id: str, metadata: dict, pdf_bytes: bytes | None) -> None:
    """Append entry to history JSON and upload PDF to SharePoint."""
    from datetime import datetime as _dt
    history = _load_report_history()
    site_entries = history.setdefault(site_id, [])
    site_entries.insert(0, metadata)
    history[site_id] = site_entries[:20]  # keep newest 20 per site
    payload = json.dumps(history, ensure_ascii=False, indent=2)
    try:
        _REPORT_HISTORY_FILE.write_text(payload, encoding="utf-8")
    except Exception:
        pass
    try:
        token, sp_site_id = _sharepoint_session()
        _sp_put(token, sp_site_id, _SP_REPORT_HISTORY_PATH, payload.encode())
        if pdf_bytes and metadata.get("sp_path"):
            _sp_put(token, sp_site_id, metadata["sp_path"], pdf_bytes)
    except Exception:
        pass


from solar_farm_explorer import render_solar_farm_explorer


# ── Page config ────────────────────────────────────────────────────────────
_fav = Image.open(FAVICON_PATH) if FAVICON_PATH.exists() else "☀️"
st.set_page_config(
    page_title="PVPAT Platform | Dolfines",
    page_icon=_fav,
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ─────────────────────────────────────────────────────────────────────────────
# ASSETS
# ─────────────────────────────────────────────────────────────────────────────

def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()

bg_b64       = _b64(BG_PATH)        if BG_PATH.exists()        else ""
bg_solar2_b64 = _b64(BG_SOLAR2_PATH) if BG_SOLAR2_PATH.exists() else ""
bg_wind_b64  = _b64(BG_WIND_PATH)  if BG_WIND_PATH.exists()  else ""
logo_b64    = _b64(LOGO_PATH)    if LOGO_PATH.exists()    else ""

bg_css = (f"url('data:image/jpeg;base64,{bg_b64}')"
          if bg_b64 else
          "linear-gradient(135deg,#001a3a 0%,#003366 60%,#0a4d8c 100%)")

logo_img = (f'<img src="data:image/png;base64,{logo_b64}" class="pvpat-header-logo" '
            f'style="height:62px;width:auto;flex-shrink:0;" />'
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
    white-space:nowrap !important;
  }}
  .stButton > button:hover {{ background:#cc6415 !important; }}

  /* Logout button — right-aligned, auto width, flush with content edge */
  [data-testid="stHorizontalBlock"]:has(.pvpat-header-logo) > div:last-child .stButton {{
    display: flex !important;
    justify-content: flex-end !important;
  }}
  [data-testid="stHorizontalBlock"]:has(.pvpat-header-logo) > div:last-child .stButton > button {{
    width: auto !important;
    padding: 0.45rem 1.4rem !important;
  }}

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
    background:rgba(255,255,255,0.06); transition:border-color 0.2s, background 0.2s;
  }}
  [data-testid="stFileUploaderDropzone"]:hover,
  [data-testid="stFileUploaderDropzone"].drag-over {{
    border:2px dashed #F07820 !important; background:rgba(240,120,32,0.12) !important;
  }}
  [data-testid="stFileUploaderDropzoneInstructions"] span,
  [data-testid="stFileUploaderDropzoneInstructions"] p {{
    color:rgba(255,255,255,0.65) !important;
  }}
</style>
""", unsafe_allow_html=True)

# Inject drag-over highlight JS via components.html so it actually executes
# (st.markdown strips <script> tags; components.html runs in a real iframe
#  with access to the parent document via window.parent)
import streamlit.components.v1 as _components
_components.html("""
<script>
(function() {
  var doc = window.parent.document;
  function clearAll() {
    doc.querySelectorAll('[data-testid="stFileUploaderDropzone"].drag-over')
       .forEach(function(el) { el.classList.remove('drag-over'); });
  }
  function attach() {
    doc.querySelectorAll('[data-testid="stFileUploaderDropzone"]').forEach(function(el) {
      if (el._db) return;
      el._db = true;
      // Do NOT stopPropagation — Streamlit needs dragover to call preventDefault
      el.addEventListener('dragenter', function() { el.classList.add('drag-over'); });
      el.addEventListener('dragover',  function() { el.classList.add('drag-over'); });
      el.addEventListener('dragleave', function(e) {
        if (!el.contains(e.relatedTarget)) el.classList.remove('drag-over');
      });
    });
  }
  // Clear class on any drop or drag cancel anywhere in the document
  doc.addEventListener('drop',    clearAll);
  doc.addEventListener('dragend', clearAll);
  doc.addEventListener('dragleave', function(e) {
    if (!e.relatedTarget) clearAll(); // pointer left the browser window
  });
  attach();
  new MutationObserver(attach).observe(doc.body, {childList: true, subtree: true});
})();
</script>
""", height=0, scrolling=False)


# ─────────────────────────────────────────────────────────────────────────────
# WIND BACKGROUND
# ─────────────────────────────────────────────────────────────────────────────

def _apply_wind_bg():
    """Override background with wind farm image if available."""
    if not bg_wind_b64:
        return
    st.markdown(f"""
    <style>
    .stApp {{
      background-image:
        linear-gradient(rgba(0,10,35,0.72),rgba(0,10,35,0.72)),
        url('data:image/jpeg;base64,{bg_wind_b64}') !important;
      background-size: cover !important;
      background-position: center !important;
      background-attachment: fixed !important;
    }}
    </style>
    """, unsafe_allow_html=True)


def _apply_solar2_bg():
    """Override background with alternate solar farm image for report pages."""
    if not bg_solar2_b64:
        return
    st.markdown(f"""
    <style>
    .stApp {{
      background-image:
        linear-gradient(rgba(0,10,35,0.72),rgba(0,10,35,0.72)),
        url('data:image/jpeg;base64,{bg_solar2_b64}') !important;
      background-size: cover !important;
      background-position: center !important;
      background-attachment: fixed !important;
    }}
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SMART FILE IMPORT — column detection & normalisation
# ─────────────────────────────────────────────────────────────────────────────

# Keyword lists for each logical column role
_ROLE_KEYWORDS = {
    "time":         ["time", "date", "ts", "timestamp", "datetime", "horodatage",
                     "udt", "heure", "periode"],
    "power":        ["pac", "power", "p_ac", "kw", "puissance", "activepow",
                     "kwac", "pout", "p_kw", "energie_active", "eond", "eac",
                     "onduleur", "inverter", "inv_", "cb_", "combiner"],
    "irradiance":   ["ghi", "irr", "irradiance", "solar", "poa", "radiation",
                     "rayonnement", "g_inc", "g_poa", "soleil"],
    "turbine":      ["turbine", "turb", "wt", "windturbine", "generator",
                     "eolienne", "aerogenerateur"],
    "wind_speed":   ["wind_ms", "windspeed", "wind_speed", "v_wind", "vwind",
                     "ws", "v_10m", "vitesse_vent", "speed"],
    "wind_dir":     ["wind_dir", "direction", "dir", "wd", "azimuth",
                     "direction_vent"],
    "availability": ["avail", "disponibilite", "disponibility", "status",
                     "running", "dispo"],
}

# Maps role → standard column name expected by the pipeline
_STANDARD_NAMES = {
    "solar": {
        "time":       "Time_UDT",
        "power":      "PAC",        # multi-select: all selected cols are summed
        "irradiance": "GHI",        # optional
    },
    "wind": {
        "time":         "Time_UDT",
        "turbine":      "TURBINE",
        "power":        "POWER_KW",
        "wind_speed":   "WIND_MS",
        "wind_dir":     "WIND_DIR_DEG",
        "availability": "AVAILABILITY_PCT",
    },
}

# Roles that are optional (skipping does not block generation)
_ROLE_OPTIONAL = {
    "solar": {"irradiance"},        # irradiance may be in a separate file
    "wind":  {"wind_dir", "availability"},
}

# Roles where user can select multiple columns (values will be summed)
_ROLE_MULTI = {
    "solar": {"power"},
    "wind":  set(),
}

# Display labels shown in the mapper UI
_ROLE_LABEL = {
    "time":       "Time",
    "power":      "Power columns",
    "irradiance": "Irradiance",
    "turbine":    "Turbine ID",
    "wind_speed": "Wind Speed",
    "wind_dir":   "Wind Direction",
    "availability": "Availability",
}


def _smart_read_df(f) -> "pd.DataFrame":
    """Read a CSV or Excel uploaded file into a DataFrame."""
    import pandas as pd
    name = f.name.lower()
    f.seek(0)
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(f, engine="openpyxl")
    raw = f.read().decode("utf-8", errors="replace")
    f.seek(0)
    seps = {";": raw.count(";"), ",": raw.count(","), "\t": raw.count("\t")}
    sep = max(seps, key=seps.get)
    import io as _io
    decimal = "," if sep == ";" else "."
    return pd.read_csv(_io.StringIO(raw), sep=sep, decimal=decimal)


def _detect_role(col) -> str | None:
    """Return the best-matching role for a column name, or None.
    Accepts any column type (str, int, None) — non-string columns return None."""
    if not isinstance(col, str):
        return None
    c = col.lower().replace(" ", "_").replace("(", "").replace(")", "")
    for role, kws in _ROLE_KEYWORDS.items():
        for kw in kws:
            if kw in c:
                return role
    return None


def _auto_map_columns(df, site_type="solar") -> dict:
    """Return {role: col_or_list} for detected roles in df.
    Multi roles (e.g. power) return a list of all matching columns.
    Skips non-string or None column names safely."""
    roles_needed = set(_STANDARD_NAMES.get(site_type, {}).keys())
    multi_roles  = _ROLE_MULTI.get(site_type, set())
    mapping: dict = {r: [] for r in roles_needed if r in multi_roles}
    for col in df.columns:
        role = _detect_role(col)
        if role and role in roles_needed:
            if role in multi_roles:
                mapping[role].append(col)
            elif role not in mapping:
                mapping[role] = col
    return mapping


def _show_column_mapper(files, site_type="solar", state_key="col_maps"):
    """
    Render column-mapping UI for a list of uploaded files.
    - Multi roles (e.g. power) use st.multiselect.
    - Optional roles do not block generation if skipped.
    Returns {filename: (df, {role: col_or_list})} when all required roles are
    satisfied, or None if the user still needs to complete the mapping.
    """
    import pandas as pd

    roles_needed = _STANDARD_NAMES.get(site_type, {})
    optional     = _ROLE_OPTIONAL.get(site_type, set())
    multi_roles  = _ROLE_MULTI.get(site_type, set())

    if not files:
        return None
    if state_key not in st.session_state:
        st.session_state[state_key] = {}

    all_confirmed = True
    result = {}

    for f in files:
        fname = f.name
        try:
            df = _smart_read_df(f)
            # Normalise column names: convert anything non-string to "col_N"
            df.columns = [
                c if isinstance(c, str) else f"col_{i}"
                for i, c in enumerate(df.columns)
            ]
            cols = list(df.columns)
            auto = _auto_map_columns(df, site_type)
        except Exception as exc:
            st.error(f"Could not read **{fname}**: {exc}")
            all_confirmed = False
            continue

        saved = st.session_state[state_key].get(fname, auto.copy())

        # Determine if all required roles are already satisfied
        req_ok = all(
            (bool(saved.get(r)) if r in multi_roles else saved.get(r))
            for r in roles_needed if r not in optional
        )

        with st.expander(
            f"📄 {fname} — {len(df):,} rows × {len(cols)} columns",
            expanded=not req_ok,
        ):
            st.caption("Auto-detected column mapping — adjust if needed:")

            # Layout: one column per role
            n_cols = len(roles_needed)
            row_cols = st.columns(max(n_cols, 1))
            updated = {}
            req_satisfied = True

            for i, (role, std_name) in enumerate(roles_needed.items()):
                label     = _ROLE_LABEL.get(role, role)
                is_multi  = role in multi_roles
                is_opt    = role in optional

                with row_cols[i]:
                    lbl_text = (f"**{label}**"
                                + (" *(optional)*" if is_opt else ""))
                    st.markdown(lbl_text)

                    if is_multi:
                        # Multiselect — saved value is a list
                        default_sel = [c for c in saved.get(role, []) if c in cols]
                        chosen = st.multiselect(
                            f"_{std_name}_",
                            options=cols,
                            default=default_sel,
                            key=f"{state_key}_{fname}_{role}",
                            help=f"Select **all** columns that contain {label} data. "
                                 "They will be summed.",
                            label_visibility="collapsed",
                        )
                        updated[role] = chosen
                        if not chosen and role not in optional:
                            req_satisfied = False
                    else:
                        # Single selectbox — optional roles allow "— skip —"
                        sv = saved.get(role, "")
                        default_idx = (cols.index(sv) + 1) if sv in cols else 0
                        options = (["— skip —"] if is_opt else []) + cols
                        if not is_opt:
                            options = ["— skip —"] + cols
                        chosen = st.selectbox(
                            f"_{std_name}_",
                            options=options,
                            index=default_idx if sv in cols else 0,
                            key=f"{state_key}_{fname}_{role}",
                            help=f"Column containing **{label}** data.",
                            label_visibility="collapsed",
                        )
                        if chosen == "— skip —":
                            if role not in optional:
                                req_satisfied = False
                        else:
                            updated[role] = chosen

            st.session_state[state_key][fname] = updated

            if not req_satisfied:
                st.warning("Some required columns are not mapped — please select them above.")
                all_confirmed = False
            else:
                mapped_summary = []
                for role, val in updated.items():
                    if isinstance(val, list):
                        mapped_summary.append(f"**Power**: {', '.join(val)} ({len(val)} cols)")
                    else:
                        mapped_summary.append(f"**{_ROLE_LABEL.get(role, role)}**: {val}")
                st.success("Mapping confirmed ✔  —  " + "  ·  ".join(mapped_summary))

        result[fname] = (df, st.session_state[state_key].get(fname, {}))

    return result if all_confirmed else None


def _normalise_files(mapped_result, site_type="solar") -> list:
    """
    Given output of _show_column_mapper, return list of (filename, normalised_df).

    For solar with multi-select power columns:
      - Outputs a long-format inverter CSV: Time_UDT, EQUIP, PAC
        (each selected power column becomes rows with EQUIP = column name)
      - Outputs a separate irradiance CSV prefixed 'irradiance_': Time_UDT, GHI
    This ensures _load_inverter_csv and _load_irradiance_csv both find their data.
    """
    import pandas as pd
    multi_roles = _ROLE_MULTI.get(site_type, set())
    out = []

    for fname, (df, mapping) in mapped_result.items():
        base = fname.rsplit(".", 1)[0]
        time_col  = mapping.get("time")
        power_val = mapping.get("power")
        irr_col   = mapping.get("irradiance")

        time_series = df[time_col] if (time_col and time_col in df.columns) else None

        # ── Inverter file (long format) ──────────────────────────────────────
        if time_series is not None and power_val:
            if isinstance(power_val, list):
                power_cols = [c for c in power_val if c in df.columns]
            else:
                power_cols = [power_val] if power_val in df.columns else []

            if power_cols:
                # Convert timestamps to unambiguous ISO format so _filter_day
                # can reliably match dates regardless of original locale format
                time_iso = pd.to_datetime(time_series, dayfirst=True, errors="coerce")
                time_iso_str = time_iso.dt.strftime("%Y-%m-%d %H:%M:%S")

                # Detect interval so we can output PAC in kW.
                # BJ/inverter columns are typically in kWh/interval; dividing by
                # interval_h converts them to kW as build_scada_analysis_html expects.
                ts_unique = time_iso.dropna().sort_values().unique()
                if len(ts_unique) > 1:
                    _ivl_h = (ts_unique[1] - ts_unique[0]).total_seconds() / 3600.0
                else:
                    _ivl_h = 5 / 60.0

                frames = []
                for pcol in power_cols:
                    raw = pd.to_numeric(df[pcol], errors="coerce").fillna(0.0)
                    # Heuristic: if max value < 50 treat as kWh/interval → convert to kW
                    pac = raw / _ivl_h if (raw.max() < 50 and _ivl_h > 0) else raw
                    tmp = pd.DataFrame({
                        "Time_UDT": time_iso_str.values,
                        "EQUIP":    pcol,
                        "PAC":      pac.values,
                    })
                    frames.append(tmp)
                inv_df = pd.concat(frames, ignore_index=True)
                out.append((base + ".csv", inv_df))

        # ── Irradiance file ──────────────────────────────────────────────────
        if time_series is not None and irr_col and irr_col in df.columns:
            # Parse timestamps to ISO format so _load_irradiance_csv can always
            # unambiguously parse them regardless of the original locale format
            time_iso = pd.to_datetime(time_series, dayfirst=True, errors="coerce")
            irr_df = pd.DataFrame({
                "Time_UDT": time_iso.dt.strftime("%Y-%m-%d %H:%M:%S"),
                "GHI":      pd.to_numeric(df[irr_col], errors="coerce").fillna(0.0).values,
            })
            out.append(("irradiance_" + base + ".csv", irr_df))

    return out


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

_POSITIVE_NUMERIC_FIELDS = frozenset({
    "n_inverters", "inv_ac_kw", "cap_ac_kw", "cap_dc_kwp",
    "n_modules", "module_wp", "hub_height_m", "tip_height_m",
    "rotor_diameter_m", "expected_aep_gwh",
})

def _sync_custom_sites():
    """Merge custom/overridden sites into SITES.

    For built-in sites, zero/None values in the override dict are NOT allowed
    to overwrite valid positive-numeric base values — this prevents stale
    SharePoint data (e.g. n_inverters=0 from an old edit) from clobbering
    freshly updated platform_users.py entries.
    """
    from platform_users import SITES as _BASE_SITES
    for sid, cfg in st.session_state.get("custom_sites", {}).items():
        if sid in _BASE_SITES:
            # Merge: start from base, apply only meaningful overrides
            merged = dict(_BASE_SITES[sid])
            for k, v in cfg.items():
                if k in _POSITIVE_NUMERIC_FIELDS and not v:
                    continue  # skip zero/None — keep base value
                merged[k] = v
            SITES[sid] = merged
        else:
            SITES[sid] = cfg

def _logged_in() -> bool:
    return st.session_state.get("user") is not None

def _logout():
    for k in ["user", "view", "selected_site", "report_type"]:
        st.session_state.pop(k, None)
    st.rerun()

def _set(key, val):
    st.session_state[key] = val
    st.rerun()


_UI_TEXT = {
    "en": {
        "header.title": "Performance Analysis Platform",
        "header.logout": "Log out",
        "header.plan.unlimited": "UNLIMITED",
        "header.plan.one_shot": "ONE-SHOT",
        "login.subtitle": "Sign in to access your portfolio.",
        "login.email": "Email address",
        "login.password": "Password",
        "login.submit": "Sign In →",
        "login.invalid": "Invalid email or password.",
        "login.forgotten": "Forgotten your password? Contact us",
        "portfolio.welcome": "Welcome back, <strong>{name}</strong> &nbsp;—&nbsp; {company}",
        "portfolio.title": "Your Site Portfolio",
        "portfolio.empty": "No sites in your portfolio. Add one below.",
        "portfolio.delete.confirm": "⚠️ Permanently delete <strong>{site}</strong>? This cannot be undone.",
        "portfolio.delete.yes": "Confirm Delete",
        "portfolio.delete.no": "Cancel",
        "portfolio.status.operational": "OPERATIONAL",
        "portfolio.status.maintenance": "MAINTENANCE",
        "portfolio.status.offline": "OFFLINE",
        "portfolio.action.view": "View site",
        "portfolio.action.edit": "Edit site",
        "portfolio.action.generate": "Generate report",
        "portfolio.action.delete": "Delete site",
        "portfolio.add.title": "➕  Add a new site",
        "portfolio.add.name": "Site name *",
        "portfolio.add.capacity.wind": "Capacity (MW) *",
        "portfolio.add.capacity.solar": "Capacity (MWp DC) *",
        "portfolio.add.type": "Site type",
        "portfolio.add.submit": "Add site",
        "portfolio.add.error.name": "Site name is required.",
        "portfolio.add.error.capacity": "Capacity is required.",
        "portfolio.add.error.number": "Capacity must be a number (e.g. 9.84).",
        "nav.back_portfolio": "← Back to Portfolio",
        "nav.back": "← Back",
        "nav.previous_reports": "📋 Previous Reports",
        "report.generate.title": "Generate Report — {site}",
        "report.previous.title": "Previous Reports — {site}",
        "report.previous.empty": "No reports have been generated for this site yet.",
        "report.previous.loading": "Loading report history…",
        "report.previous.legacy": "Showing legacy files from the local `previous reports` folder because no structured report history was found.",
        "site.edit.title": "Edit Site — {site}",
        "site.edit.name": "Site name",
        "site.edit.status": "Status",
        "site.edit.country": "Country",
        "site.edit.region": "Region",
        "site.edit.cod": "COD date",
        "site.edit.wind.section": "Wind Turbine Details",
        "site.edit.wind.mfr": "Turbine manufacturer",
        "site.edit.wind.model": "Turbine model",
        "site.edit.wind.capacity": "Rated capacity per turbine (MW)",
        "site.edit.wind.count": "Number of turbines",
        "site.edit.wind.hub": "Hub height (m)",
        "site.edit.wind.tip": "Height to blade tip (m)",
        "site.edit.wind.aep": "Expected AEP (GWh/yr)",
        "site.edit.wind.total": "Calculated site capacity (MW)",
        "site.edit.wind.rotor": "Detected rotor diameter: {rotor:.0f} m",
        "site.edit.solar.section": "Solar Equipment Details",
        "site.edit.solar.multi": "Multiple module types on this site",
        "site.edit.solar.type_count": "Number of module types",
        "site.edit.solar.module_type": "Module Type {index}",
        "site.edit.solar.module_mfr": "Module manufacturer",
        "site.edit.solar.module_model": "Module model",
        "site.edit.solar.qty_power": "Module Quantities and Power",
        "site.edit.solar.qty": "Number of modules for type {index}",
        "site.edit.solar.power": "Capacity per module for type {index} (Wp)",
        "site.edit.solar.subtotal": "{label}: {mw:.3f} MWp DC",
        "site.edit.solar.inv_mfr": "Inverter manufacturer",
        "site.edit.solar.inv_model": "Inverter model",
        "site.edit.solar.inv_section": "Inverter Capacity",
        "site.edit.solar.inv_count": "Number of inverters",
        "site.edit.solar.inv_power": "Rated capacity per inverter (kW)",
        "site.edit.solar.total_dc": "Calculated DC capacity (MWp)",
        "site.edit.solar.total_ac": "Calculated AC capacity (MW)",
        "site.edit.solar.ratio": "Calculated DC/AC ratio",
        "site.edit.save": "💾 Save changes",
        "site.edit.error.site_missing": "Site not found.",
        "site.edit.error.wind_required": "Please provide a turbine model capacity and a positive turbine count.",
        "site.edit.error.solar_modules": "Please enter at least one valid module type with quantity and module power.",
        "site.edit.error.solar_inverters": "Please enter a positive inverter count and inverter capacity.",
        "site.edit.saved": "Changes saved.",
    },
    "fr": {
        "header.title": "Plateforme d'analyse de performance",
        "header.logout": "Se déconnecter",
        "header.plan.unlimited": "ILLIMITÉ",
        "header.plan.one_shot": "PONCTUEL",
        "login.subtitle": "Connectez-vous pour accéder à votre portefeuille.",
        "login.email": "Adresse e-mail",
        "login.password": "Mot de passe",
        "login.submit": "Se connecter →",
        "login.invalid": "Adresse e-mail ou mot de passe invalide.",
        "login.forgotten": "Mot de passe oublié ? Contactez-nous",
        "portfolio.welcome": "Bon retour, <strong>{name}</strong> &nbsp;—&nbsp; {company}",
        "portfolio.title": "Votre portefeuille de sites",
        "portfolio.empty": "Aucun site dans votre portefeuille. Ajoutez-en un ci-dessous.",
        "portfolio.delete.confirm": "⚠️ Supprimer définitivement <strong>{site}</strong> ? Cette action est irréversible.",
        "portfolio.delete.yes": "Confirmer",
        "portfolio.delete.no": "Annuler",
        "portfolio.status.operational": "EN SERVICE",
        "portfolio.status.maintenance": "MAINTENANCE",
        "portfolio.status.offline": "HORS SERVICE",
        "portfolio.action.view": "Voir le site",
        "portfolio.action.edit": "Modifier le site",
        "portfolio.action.generate": "Générer un rapport",
        "portfolio.action.delete": "Supprimer le site",
        "portfolio.add.title": "➕  Ajouter un site",
        "portfolio.add.name": "Nom du site *",
        "portfolio.add.capacity.wind": "Capacité (MW) *",
        "portfolio.add.capacity.solar": "Capacité (MWc DC) *",
        "portfolio.add.type": "Type de site",
        "portfolio.add.submit": "Ajouter le site",
        "portfolio.add.error.name": "Le nom du site est obligatoire.",
        "portfolio.add.error.capacity": "La capacité est obligatoire.",
        "portfolio.add.error.number": "La capacité doit être un nombre (ex. 9,84).",
        "nav.back_portfolio": "← Retour au portefeuille",
        "nav.back": "← Retour",
        "nav.previous_reports": "📋 Rapports précédents",
        "report.generate.title": "Générer un rapport — {site}",
        "report.previous.title": "Rapports précédents — {site}",
        "report.previous.empty": "Aucun rapport n'a encore été généré pour ce site.",
        "report.previous.loading": "Chargement de l'historique des rapports…",
        "report.previous.legacy": "Affichage des anciens fichiers du dossier local `previous reports` car aucun historique structuré n'a été trouvé.",
        "site.edit.title": "Modifier le site — {site}",
        "site.edit.name": "Nom du site",
        "site.edit.status": "Statut",
        "site.edit.country": "Pays",
        "site.edit.region": "Région",
        "site.edit.cod": "Date de mise en service",
        "site.edit.wind.section": "Détails de l'éolienne",
        "site.edit.wind.mfr": "Constructeur de l'éolienne",
        "site.edit.wind.model": "Modèle d'éolienne",
        "site.edit.wind.capacity": "Puissance nominale par éolienne (MW)",
        "site.edit.wind.count": "Nombre d'éoliennes",
        "site.edit.wind.hub": "Hauteur de moyeu (m)",
        "site.edit.wind.tip": "Hauteur en bout de pale (m)",
        "site.edit.wind.aep": "PEA attendue (GWh/an)",
        "site.edit.wind.total": "Capacité calculée du site (MW)",
        "site.edit.wind.rotor": "Diamètre de rotor détecté : {rotor:.0f} m",
        "site.edit.solar.section": "Détails des équipements solaires",
        "site.edit.solar.multi": "Plusieurs types de modules sur ce site",
        "site.edit.solar.type_count": "Nombre de types de modules",
        "site.edit.solar.module_type": "Type de module {index}",
        "site.edit.solar.module_mfr": "Fabricant du module",
        "site.edit.solar.module_model": "Modèle du module",
        "site.edit.solar.qty_power": "Quantités et puissances des modules",
        "site.edit.solar.qty": "Nombre de modules pour le type {index}",
        "site.edit.solar.power": "Puissance par module pour le type {index} (Wc)",
        "site.edit.solar.subtotal": "{label} : {mw:.3f} MWc DC",
        "site.edit.solar.inv_mfr": "Fabricant de l'onduleur",
        "site.edit.solar.inv_model": "Modèle d'onduleur",
        "site.edit.solar.inv_section": "Capacité des onduleurs",
        "site.edit.solar.inv_count": "Nombre d'onduleurs",
        "site.edit.solar.inv_power": "Puissance nominale par onduleur (kW)",
        "site.edit.solar.total_dc": "Capacité DC calculée (MWc)",
        "site.edit.solar.total_ac": "Capacité AC calculée (MW)",
        "site.edit.solar.ratio": "Ratio DC/AC calculé",
        "site.edit.save": "💾 Enregistrer les modifications",
        "site.edit.error.site_missing": "Site introuvable.",
        "site.edit.error.wind_required": "Veuillez renseigner une puissance d'éolienne et un nombre d'éoliennes positif.",
        "site.edit.error.solar_modules": "Veuillez renseigner au moins un type de module valide avec quantité et puissance.",
        "site.edit.error.solar_inverters": "Veuillez renseigner un nombre d'onduleurs et une puissance d'onduleur positifs.",
        "site.edit.saved": "Modifications enregistrées.",
    },
}


def _ui_lang() -> str:
    return st.session_state.get("ui_lang", "en")


def _t(key: str, **kwargs) -> str:
    lang = _ui_lang()
    text = _UI_TEXT.get(lang, _UI_TEXT["en"]).get(key, _UI_TEXT["en"].get(key, key))
    return text.format(**kwargs)


def _render_lang_toggle() -> None:
    active = _ui_lang()
    st.markdown(
        """
        <style>
          .lang-toggle-row div[data-testid="stButton"] > button {
            min-width: 2.7rem !important;
            padding: 0.2rem 0.45rem !important;
            font-size: 0 !important;
            line-height: 1.1 !important;
            background-position: center !important;
            background-repeat: no-repeat !important;
            background-size: 28px 20px !important;
          }
          .lang-toggle-row [data-testid="stColumn"]:nth-child(1) div[data-testid="stButton"] > button {
            background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='28' height='20' viewBox='0 0 28 20'><clipPath id='a'><rect width='28' height='20' rx='2'/></clipPath><g clip-path='url(%23a)'><rect width='28' height='20' fill='%23012169'/><path d='M0 0l28 20M28 0L0 20' stroke='%23fff' stroke-width='4'/><path d='M0 0l28 20M28 0L0 20' stroke='%23C8102E' stroke-width='2.2'/><path d='M14 0v20M0 10h28' stroke='%23fff' stroke-width='6'/><path d='M14 0v20M0 10h28' stroke='%23C8102E' stroke-width='4'/></g></svg>") !important;
          }
          .lang-toggle-row [data-testid="stColumn"]:nth-child(2) div[data-testid="stButton"] > button {
            background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='28' height='20' viewBox='0 0 28 20'><rect width='28' height='20' rx='2' fill='%23fff'/><path d='M0 0h9.33v20H0z' fill='%230055A4'/><path d='M18.67 0H28v20h-9.33z' fill='%23EF4135'/></svg>") !important;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="lang-toggle-row"></div>', unsafe_allow_html=True)
    col_en, col_fr = st.columns(2)
    with col_en:
        if st.button("English", key="lang_en", type="primary" if active == "en" else "secondary"):
            if active != "en":
                st.session_state["ui_lang"] = "en"
                st.rerun()
    with col_fr:
        if st.button("Français", key="lang_fr", type="primary" if active == "fr" else "secondary"):
            if active != "fr":
                st.session_state["ui_lang"] = "fr"
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# HEADER  (shown on all authenticated pages)
# ─────────────────────────────────────────────────────────────────────────────

def _render_header(show_logout=True):
    user = st.session_state.get("user", {})
    plan = user.get("plan", "")
    plan_html = (
        f"<span class='plan-unlimited'>{_t('header.plan.unlimited')}</span>" if plan == "unlimited"
        else f"<span class='plan-one-shot'>{_t('header.plan.one_shot')}</span>"
    ) if plan else ""

    if show_logout and _logged_in():
        col_hdr, col_lang, col_btn = st.columns([5, 1.2, 1])
        with col_hdr:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:1.4rem;margin-bottom:0.6rem;">
              {logo_img}
              <div>
                <div style="font-size:1.45rem;font-weight:700;color:white;line-height:1.2;white-space:nowrap;">
                  {_t("header.title")}
                </div>
                {('<div style="font-size:0.84rem;color:rgba(255,255,255,0.55);margin-top:0.15rem;white-space:nowrap;">' + plan_html + '</div>') if plan_html else ''}
              </div>
            </div>
            """, unsafe_allow_html=True)
        with col_lang:
            _render_lang_toggle()
        with col_btn:
            if st.button(_t("header.logout")):
                _logout()
    else:
        col_hdr, col_lang = st.columns([5, 1.2])
        with col_hdr:
            st.markdown(f"""
            <div style="display:flex;flex-direction:column;align-items:center;gap:10mm;margin-bottom:0.6rem;">
              {logo_img}
              <div style="font-size:1.35rem;font-weight:700;color:white;line-height:1.2;text-align:center;">
                {_t("header.title")}
              </div>
            </div>
            """, unsafe_allow_html=True)
        with col_lang:
            _render_lang_toggle()
    st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# VIEW: LOGIN
# ─────────────────────────────────────────────────────────────────────────────

def _view_login():
    # Shrink the container to match the header width on the login page
    st.markdown("""
    <style>
      .main .block-container,
      [data-testid="stAppViewBlockContainer"],
      section[data-testid="stMain"] .block-container {
        max-width: calc(580px - 20mm) !important;
        padding: calc(1.8rem - 1cm) 2rem 1.8rem 2rem !important;
        margin-top: 1cm !important;
      }
      /* Tighten element gaps and divider on login page only */
      section[data-testid="stMain"] .block-container hr {
        margin: 0.4rem 0 calc(0.6rem + 5mm) 0 !important;
      }
      section[data-testid="stMain"] .block-container [data-testid="stVerticalBlock"] > div {
        gap: 0.35rem !important;
      }
    </style>
    """, unsafe_allow_html=True)

    _render_header(show_logout=False)

    st.markdown("""
    <div style="margin-bottom:0.4rem;">
      <div style="font-size:1.05rem;font-weight:700;color:white;margin-bottom:3px;">
        Client Login
      </div>
      <div style="font-size:0.80rem;color:rgba(255,255,255,0.50);">
        {_t("login.subtitle")}
      </div>
    </div>
    """, unsafe_allow_html=True)

    email    = st.text_input(_t("login.email"), placeholder="you@company.com", key="login_email")
    password = st.text_input(_t("login.password"), type="password", key="login_pw")
    submit   = st.button(_t("login.submit"), width="stretch")

    if submit:
        user = USERS.get(email.strip().lower())
        if user and user["password"] == password:
            st.session_state["user"]  = {**user, "email": email.strip().lower()}
            st.session_state["view"]  = "portfolio"
            st.rerun()
        else:
            st.error(_t("login.invalid"))

    st.markdown("""
    <div style="text-align:center;margin-top:0.8rem;font-size:0.78rem;">
      <a href="mailto:consulting@8p2.fr?subject=Password%20Reset%20Request"
         style="color:rgba(255,255,255,0.40);text-decoration:none;">
        {_t("login.forgotten")}
      </a>
    </div>
    <div style="text-align:center;margin-top:1.1rem;font-size:0.73rem;
      color:rgba(255,255,255,0.28);">
      Demo: <code style="color:rgba(240,120,32,0.65);">demo@dolfines.com</code>
      &nbsp;/&nbsp; <code style="color:rgba(240,120,32,0.65);">pvpat2024</code>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# VIEW: PORTFOLIO
# ─────────────────────────────────────────────────────────────────────────────

def _view_portfolio():
    _render_header()
    user = st.session_state["user"]

    # Session-state stores for user-managed sites
    if "deleted_sites"  not in st.session_state: st.session_state["deleted_sites"]  = set()
    if "custom_sites"   not in st.session_state:
        st.session_state["custom_sites"] = _load_custom_sites_from_disk()

    # ── Portfolio-specific CSS ─────────────────────────────────────────────────
    st.markdown("""
    <style>
      /* Flashing alert dot for underperforming sites */
      @keyframes pvpat-pulse {
        0%, 100% { opacity: 1;   transform: scale(1); }
        50%       { opacity: 0.2; transform: scale(0.75); }
      }
      .pvpat-alert-dot {
        animation: pvpat-pulse 1.4s ease-in-out infinite;
      }
      /* Site row icon hover effect */
      .pvpat-icon:hover {
        background: rgba(255,255,255,0.10) !important;
        color: white !important;
      }
      .pvpat-icon-del:hover {
        background: rgba(229,57,53,0.18) !important;
        color: #ff4444 !important;
      }
      /* Icon buttons — target last div child of any row that has a pvpat-site-row.
         Avoids testid guessing; doesn't match logout (its block has no pvpat-site-row). */
      [data-testid="stHorizontalBlock"]:has(.pvpat-site-row) > div:last-child button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
        color: rgba(255,255,255,0.72) !important;
        padding: 5px 8px !important;
        min-height: 0 !important;
        font-size: 1.05rem !important;
        line-height: 1.3 !important;
      }
      [data-testid="stHorizontalBlock"]:has(.pvpat-site-row) > div:last-child button:hover {
        background: rgba(255,255,255,0.10) !important;
        color: white !important;
      }
      /* Delete icon — last div in the nested 4-button row */
      [data-testid="stHorizontalBlock"]:has(.pvpat-site-row) > div:last-child
        [data-testid="stHorizontalBlock"] > div:last-child button {
        color: rgba(229,57,53,0.85) !important;
      }
      [data-testid="stHorizontalBlock"]:has(.pvpat-site-row) > div:last-child
        [data-testid="stHorizontalBlock"] > div:last-child button:hover {
        background: rgba(229,57,53,0.15) !important;
        color: #ff4444 !important;
      }
      /* Red confirm button — 2nd column in a confirmation row */
      [data-testid="stHorizontalBlock"]:has(.pvpat-confirm-banner) [data-testid="stColumn"]:nth-child(2) .stButton > button {
        background: #e53935 !important;
      }
      [data-testid="stHorizontalBlock"]:has(.pvpat-confirm-banner) [data-testid="stColumn"]:nth-child(2) .stButton > button:hover {
        background: #b71c1c !important;
      }
      /* Grey cancel button — last column in a confirmation row */
      [data-testid="stHorizontalBlock"]:has(.pvpat-confirm-banner) [data-testid="stColumn"]:last-child .stButton > button {
        background: rgba(255,255,255,0.18) !important;
      }
      [data-testid="stHorizontalBlock"]:has(.pvpat-confirm-banner) [data-testid="stColumn"]:last-child .stButton > button:hover {
        background: rgba(255,255,255,0.30) !important;
      }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="margin-bottom:1.2rem;">
      <span style="font-size:1.05rem;color:rgba(255,255,255,0.90);">
        {_t("portfolio.welcome", name=user['display_name'], company=user['company'])}
      </span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        f"<div class='step-hdr'>{_t('portfolio.title')}</div>",
        unsafe_allow_html=True)

    # Build the full list: built-in sites (minus deleted) + user-added sites
    builtin_ids = [s for s in user.get("sites", [])
                   if s not in st.session_state["deleted_sites"]]
    all_items = (
        [(sid, SITES[sid], False) for sid in builtin_ids if sid in SITES]
        + [(sid, cfg, True)
           for sid, cfg in st.session_state["custom_sites"].items()
           if sid not in builtin_ids]   # skip overrides of built-in sites (already listed above)
    )

    if "pending_delete" not in st.session_state:
        st.session_state["pending_delete"] = None

    # Demo KPI values per site — realistic, will be replaced with live data
    _PR_WARN = 78.0   # below this → red PR chip + alert dot
    _SITE_DEMO = {
        "SOHMEX":        {"type": "solar", "pr": 82.4, "yield_kwh": 4.2, "avail": 98.1, "alarms": 0},
        "VENTOUX_PV":    {"type": "solar", "pr": 78.6, "yield_kwh": 3.9, "avail": 95.3, "alarms": 2},
        "LIMOUSIN_WIND": {"type": "wind",  "wind_avail": 71.2, "energy_mwh_mw": 42.1, "p50_dev": -8.3, "alarms": 5},
        "NORMANDIE_PV":  {"type": "solar", "pr": 74.8, "yield_kwh": 3.1, "avail": 89.6, "alarms": 7},
    }

    def _site_kpi_chips(site_id: str, site: dict) -> str:
        demo = _SITE_DEMO.get(site_id, {"type": site.get("site_type","solar"),
                                         "pr": 80.0, "yield_kwh": 4.0,
                                         "avail": 96.0, "alarms": 0})
        _ok  = ("rgba(96,165,250,0.12)", "rgba(96,165,250,0.35)", "#60a5fa")   # blue
        _bad = ("rgba(229,57,53,0.18)",  "rgba(229,57,53,0.55)",  "#ff6b6b")   # red
        chips = []
        if demo["type"] == "wind":
            wa = demo.get("wind_avail", 90)
            chips.append(_kpi_chip("Avail.", f"{wa:.1f}%", *(_ok if wa >= 85 else _bad)))
            dev = demo.get("p50_dev", 0)
            chips.append(_kpi_chip("P50 dev.", f"{dev:+.1f}%", *(_ok if dev >= -5 else _bad)))
            chips.append(_kpi_chip(
                "Energy", f"{demo.get('energy_mwh_mw', 0):.1f} MWh/MW", *_ok))
        else:
            pr = demo.get("pr", 80)
            chips.append(_kpi_chip("PR", f"{pr:.1f}%", *(_ok if pr >= _PR_WARN else _bad)))
            chips.append(_kpi_chip(
                "Yield", f"{demo.get('yield_kwh', 4):.1f} kWh/kWp", *_ok))
            av = demo.get("avail", 96)
            chips.append(_kpi_chip("Avail.", f"{av:.1f}%", *(_ok if av >= 93 else _bad)))
        alarms = demo.get("alarms", 0)
        chips.append(_kpi_chip(
            "Alarms", str(alarms),
            *(_bad if alarms > 0 else ("rgba(255,255,255,0.07)", "rgba(255,255,255,0.22)", "rgba(255,255,255,0.60)")),
        ))
        return " ".join(chips)

    def _kpi_chip(label: str, value: str, bg: str, border: str, color: str) -> str:
        return (
            f"<span style='background:{bg};border:1px solid {border};"
            f"color:{color};font-size:0.76rem;font-weight:600;"
            f"padding:3px 10px;border-radius:20px;white-space:nowrap;'>"
            f"{label} {value}</span>"
        )

    def _low_pr_dot(site_id: str, site: dict) -> str:
        demo = _SITE_DEMO.get(site_id, {})
        t = demo.get("type", "solar")
        bad = (t == "solar" and demo.get("pr", 100) < _PR_WARN) or \
              (t == "wind"  and demo.get("wind_avail", 100) < 85)
        if bad:
            return ("<span class='pvpat-alert-dot' style='display:inline-block;width:8px;height:8px;"
                    "background:#ff6b6b;border-radius:50%;margin-left:6px;"
                    "vertical-align:middle;flex-shrink:0;'></span>")
        return ""

    if not all_items:
        st.info(_t("portfolio.empty"))
    else:
        # Pending-delete confirmation rows — always full-width
        for site_id, site, is_custom in all_items:
            if st.session_state["pending_delete"] != site_id:
                continue
            col_msg, col_yes, col_no = st.columns([4, 1.5, 1.2], vertical_alignment="center")
            with col_msg:
                st.markdown(
                    f"<div class='pvpat-confirm-banner' style='background:rgba(229,57,53,0.15);"
                    f"border:1px solid #e53935;border-radius:8px;padding:0.75rem 1.1rem;"
                    f"color:white;font-size:0.92rem;'>"
                    f"{_t('portfolio.delete.confirm', site=site['display_name'])}</div>",
                    unsafe_allow_html=True)
            with col_yes:
                if st.button(_t("portfolio.delete.yes"), key=f"yes_del_{site_id}"):
                    st.session_state["pending_delete"] = None
                    if is_custom:
                        st.session_state["custom_sites"].pop(site_id, None)
                    else:
                        st.session_state["deleted_sites"].add(site_id)
                    st.rerun()
            with col_no:
                if st.button(_t("portfolio.delete.no"), key=f"cancel_del_{site_id}"):
                    st.session_state["pending_delete"] = None
                    st.rerun()

        # Normal sites — single-column list, one site per row
        normal_items = [(sid, s, c) for sid, s, c in all_items
                        if st.session_state["pending_delete"] != sid]
        for site_id, site, is_custom in normal_items:
            cap_mwp    = site.get("cap_dc_kwp", 0) / 1000
            status     = site.get("status", "operational")
            status_lbl = {"operational": _t("portfolio.status.operational"), "maintenance": _t("portfolio.status.maintenance"),
                          "offline": _t("portfolio.status.offline")}.get(status, status.upper())
            status_col = {"operational": "#2E8B57", "maintenance": "#E67E22",
                          "offline": "#C0392B"}.get(status, "#888")
            site_icon  = "🌬️" if site.get("site_type") == "wind" else "☀️"
            cap_label  = "MW" if site.get("site_type") == "wind" else "MWp"

            kpi_html  = _site_kpi_chips(site_id, site)
            alert_dot = _low_pr_dot(site_id, site)

            info_col, icon_col = st.columns([6, 1], vertical_alignment="center")
            with info_col:
                st.markdown(f"""
                <div class="pvpat-site-row" style="display:flex;align-items:center;
                  gap:0.65rem;flex-wrap:wrap;padding:0.35rem 0.85rem;
                  background:rgba(255,255,255,0.04);
                  border:1px solid rgba(255,255,255,0.11);border-radius:8px;">
                  <span style="font-weight:700;color:white;font-size:0.92rem;
                    white-space:nowrap;">{site_icon} {site['display_name']}</span>{alert_dot}
                  <span style="color:rgba(255,255,255,0.40);font-size:0.78rem;
                    white-space:nowrap;">{cap_mwp:.2f} {cap_label}</span>
                  <span style="background:{status_col};color:white;font-size:0.58rem;
                    padding:2px 7px;border-radius:7px;font-weight:700;
                    white-space:nowrap;">{status_lbl}</span>
                  <span style="display:flex;gap:0.3rem;flex-wrap:wrap;">
                    {kpi_html}
                  </span>
                </div>
                """, unsafe_allow_html=True)
            with icon_col:
                # Marker span lets CSS scope button styles to this column only
                st.markdown('<span class="pvpat-icons"></span>', unsafe_allow_html=True)
                ic1, ic2, ic3, ic4 = st.columns(4)
                with ic1:
                    if st.button("ⓘ", key=f"sc_{site_id}", help=_t("portfolio.action.view")):
                        st.session_state["selected_site"] = site_id
                        st.session_state["view"] = "site_detail"
                        st.rerun()
                with ic2:
                    if st.button("✎", key=f"ed_{site_id}", help=_t("portfolio.action.edit")):
                        st.session_state["selected_site"] = site_id
                        st.session_state["view"] = "site_edit"
                        st.rerun()
                with ic3:
                    if st.button("≡", key=f"go_{site_id}", help=_t("portfolio.action.generate")):
                        st.session_state["selected_site"] = site_id
                        st.session_state["view"] = "report_select"
                        st.rerun()
                with ic4:
                    if st.button("✕", key=f"del_{site_id}", help=_t("portfolio.action.delete")):
                        st.session_state["pending_delete"] = site_id
                        st.rerun()

    # ── Add new site ───────────────────────────────────────────────────────────
    st.divider()
    with st.expander(_t("portfolio.add.title")):
        _is_wind_add = st.session_state.get("ns_type", "☀️ Solar") == "🌬️ Wind"
        c1, c2, c3 = st.columns(3)
        with c1:
            _name_ph = "e.g. Nordex Wind Farm" if _is_wind_add else "e.g. Sahara Solar Park"
            new_name = st.text_input(_t("portfolio.add.name"), placeholder=_name_ph, key="ns_name")
        with c2:
            _cap_lbl = _t("portfolio.add.capacity.wind") if _is_wind_add else _t("portfolio.add.capacity.solar")
            new_cap  = st.text_input(_cap_lbl, placeholder="e.g. 9.84", key="ns_cap")
        with c3:
            new_type = st.radio(_t("portfolio.add.type"), ["☀️ Solar", "🌬️ Wind"], horizontal=True, key="ns_type")

        if st.button(_t("portfolio.add.submit"), key="btn_add_site"):
            if not new_name.strip():
                st.error(_t("portfolio.add.error.name"))
            elif not new_cap.strip():
                st.error(_t("portfolio.add.error.capacity"))
            else:
                try:
                    cap_kwp = float(new_cap.replace(",", ".")) * 1000
                except ValueError:
                    st.error(_t("portfolio.add.error.number"))
                    cap_kwp = None
                if cap_kwp is not None:
                    slug = "USR_" + "".join(c if c.isalnum() else "_" for c in new_name.upper())[:20]
                    stype = "wind" if "Wind" in new_type else "solar"
                    st.session_state["custom_sites"][slug] = {
                        "display_name":   new_name.strip(),
                        "cap_dc_kwp":     cap_kwp,
                        "cap_ac_kw":      cap_kwp * 0.9,
                        "site_type":      stype,
                        "status":         "operational",
                        "n_inverters":    0,
                        "inverter_model": "—",
                        "inv_ac_kw":      0,
                        "region": "", "country": "", "cod": "—", "technology": "—",
                    }
                    st.session_state.pop("ns_name", None)
                    st.session_state.pop("ns_cap",  None)
                    _save_custom_sites_to_disk()
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# VIEW: REPORT TYPE SELECTION
# ─────────────────────────────────────────────────────────────────────────────

def _view_report_select():
    _sync_custom_sites()
    _render_header()

    site_id   = st.session_state.get("selected_site", "")
    site      = SITES.get(site_id, {})
    is_wind   = site.get("site_type") == "wind"

    if is_wind:
        _apply_wind_bg()
    else:
        _apply_solar2_bg()

    # Initialise selection state (persists across reruns on this page)
    if "report_choice" not in st.session_state:
        st.session_state["report_choice"] = None

    col_back, col_hist, _ = st.columns([2, 2, 2])
    with col_back:
        if st.button(_t("nav.back_portfolio")):
            st.session_state.pop("report_choice", None)
            st.session_state["view"] = "portfolio"
            st.rerun()
    with col_hist:
        st.markdown(
            "<style>div[data-testid='stButton']:has(button[kind='secondary']#btn_prev_reports)"
            " button{background:#22c55e!important;color:#fff!important;"
            "border:none!important;font-weight:600!important;}</style>",
            unsafe_allow_html=True)
        if st.button(_t("nav.previous_reports"), key="btn_prev_reports",
                     width="stretch"):
            st.session_state["view"] = "report_history"
            st.rerun()

    st.markdown(
        f"<div class='step-hdr'>{_t('report.generate.title', site=site.get('display_name',''))}</div>",
        unsafe_allow_html=True)

    st.markdown("""
    <p style="color:rgba(255,255,255,0.75);font-size:0.90rem;margin-bottom:1.2rem;">
      Select the type of report you want to generate, then click the button below.
    </p>""", unsafe_allow_html=True)

    choice = st.session_state["report_choice"]

    # ── Card styles ────────────────────────────────────────────────────────────
    daily_sel   = choice == "daily"
    monthly_sel = choice == "monthly"
    comp_sel    = choice == "comprehensive"

    daily_border = "2px solid #F07820" if daily_sel else "1.5px solid rgba(255,255,255,0.18)"
    daily_bg     = "rgba(240,120,32,0.18)" if daily_sel else "rgba(255,255,255,0.06)"
    daily_check  = "<span style='float:right;font-size:1.1rem;color:#22c55e;'>✔</span>" if daily_sel else ""

    monthly_border = "2px solid #F07820" if monthly_sel else "1.5px solid rgba(255,255,255,0.18)"
    monthly_bg     = "rgba(240,120,32,0.18)" if monthly_sel else "rgba(255,255,255,0.06)"
    monthly_check  = "<span style='float:right;font-size:1.1rem;color:#22c55e;'>✔</span>" if monthly_sel else ""

    comp_border  = "2px solid #F07820" if comp_sel  else "1.5px solid rgba(255,255,255,0.18)"
    comp_bg      = "rgba(240,120,32,0.18)" if comp_sel  else "rgba(255,255,255,0.06)"
    comp_check   = "<span style='float:right;font-size:1.1rem;color:#22c55e;'>✔</span>" if comp_sel  else ""

    st.markdown("<style>.pvpat-report-card { cursor: pointer; }</style>",
                unsafe_allow_html=True)
    # Inject JS via components iframe so clicking a card triggers its Select button
    try:
        import streamlit.components.v1 as _comp
        _comp.html("""
        <script>
        (function() {
          function wire() {
            try {
              var doc = window.parent.document;
              doc.querySelectorAll('.pvpat-report-card').forEach(function(card) {
                if (card.dataset.wired) return;
                card.dataset.wired = '1';
                card.addEventListener('click', function() {
                  var col = card.closest('[data-testid="stColumn"]');
                  if (col) { var b = col.querySelector('button'); if (b) b.click(); }
                });
              });
              new MutationObserver(wire).observe(doc.body, {childList:true, subtree:true});
            } catch(e) {}
          }
          wire();
        })();
        </script>
        """, height=1)
    except Exception:
        pass

    col_a, col_b, col_c = st.columns(3)

    daily_icon  = "🌬️" if is_wind else "☀️"
    daily_title = "Simple Daily Wind Report" if is_wind else "Simple Daily Report"
    daily_bullets = (
        ["4–5 pages, generated instantly",
         "Turbine availability per unit",
         "Daily energy production",
         "Average wind speed &amp; direction",
         "Wind rose summary",
         "Alerts &amp; alarms with recommended fixes"]
        if is_wind else
        ["4–5 pages, generated instantly",
         "Specific yield &amp; PR per inverter",
         "Fleet availability dashboard",
         "Daily irradiance profile",
         "Energy loss waterfall",
         "Alerts &amp; alarms with recommended fixes"]
    )

    with col_a:
        st.markdown(f"""
        <div class="pvpat-report-card" style="background:{daily_bg};border:{daily_border};
          border-radius:10px;padding:1.4rem 1.6rem;height:250px;overflow:auto;
          cursor:pointer;transition:border 0.15s,background 0.15s;">
          <div style="font-size:1.05rem;font-weight:700;color:#F07820;margin-bottom:8px;">
            {daily_icon} {daily_title} {daily_check}
          </div>
          <ul style="color:rgba(255,255,255,0.82);font-size:0.87rem;
            line-height:1.75;padding-left:1.2rem;margin:0;">
            {"".join(f"<li>{b}</li>" for b in daily_bullets)}
          </ul>
        </div>""", unsafe_allow_html=True)
        if st.button("Select Daily Report", key="btn_daily", width="stretch"):
            st.session_state["report_choice"] = "daily"
            st.rerun()

    monthly_icon   = "🌬️" if is_wind else "☀️"
    monthly_title  = "Monthly Wind Report" if is_wind else "Monthly Report"
    monthly_bullets = (
        ["8–12 pages, monthly rollup",
         "Energy &amp; availability summary",
         "Turbine performance ranking",
         "Wind resource &amp; power curve",
         "Month-on-month trend comparison",
         "Alerts &amp; maintenance review"]
        if is_wind else
        ["8–12 pages, monthly rollup",
         "Energy, PR &amp; irradiance summary",
         "Inverter performance ranking",
         "Month-on-month trend comparison",
         "Data quality review",
         "Alerts &amp; maintenance review"]
    )

    with col_b:
        st.markdown(f"""
        <div class="pvpat-report-card" style="background:{monthly_bg};border:{monthly_border};
          border-radius:10px;padding:1.4rem 1.6rem;height:250px;overflow:auto;
          cursor:pointer;transition:border 0.15s,background 0.15s;">
          <div style="font-size:1.05rem;font-weight:700;color:#60a5fa;margin-bottom:8px;">
            📅 {monthly_title} {monthly_check}
          </div>
          <ul style="color:rgba(255,255,255,0.82);font-size:0.87rem;
            line-height:1.75;padding-left:1.2rem;margin:0;">
            {"".join(f"<li>{b}</li>" for b in monthly_bullets)}
          </ul>
        </div>""", unsafe_allow_html=True)
        if st.button("Select Monthly Report", key="btn_monthly", width="stretch"):
            st.session_state["report_choice"] = "monthly"
            st.rerun()

    with col_c:
        st.markdown(f"""
        <div class="pvpat-report-card" style="background:{comp_bg};border:{comp_border};
          border-radius:10px;padding:1.4rem 1.6rem;height:250px;overflow:auto;
          cursor:pointer;transition:border 0.15s,background 0.15s;">
          <div style="font-size:1.05rem;font-weight:700;color:white;margin-bottom:8px;">
            📊 Comprehensive Analysis Report {comp_check}
          </div>
          <ul style="color:rgba(255,255,255,0.75);font-size:0.87rem;
            line-height:1.75;padding-left:1.2rem;margin:0;">
            {"".join(f"<li>{b}</li>" for b in (
              ["20–25 pages, full technical analysis",
               "Monthly energy, availability &amp; wind trends",
               "Turbine fleet comparison &amp; heatmaps",
               "Wind rose &amp; power curve analysis",
               "Loss analysis &amp; OEM benchmarking",
               "Full action punchlist with EUR impact"]
              if is_wind else
              ["20–25 pages, full technical analysis",
               "Monthly energy, PR &amp; irradiance trends",
               "Inverter fleet comparison &amp; heatmaps",
               "Data quality &amp; SARAH coherence",
               "Loss analysis &amp; technology risk register",
               "Full action punchlist with EUR impact"]
            ))}
          </ul>
        </div>""", unsafe_allow_html=True)
        if st.button("Select Comprehensive Report", key="btn_comp", width="stretch"):
            st.session_state["report_choice"] = "comprehensive"
            st.rerun()

    # ── Generate button — bottom right ─────────────────────────────────────────
    st.markdown("<div style='margin-top:1.4rem;'>", unsafe_allow_html=True)
    _, _, col_gen = st.columns([2, 2, 2])
    with col_gen:
        if choice is None:
            st.markdown(
                "<p style='color:rgba(255,255,255,0.40);font-size:0.85rem;"
                "text-align:right;margin-top:0.5rem;'>← Select a report type first</p>",
                unsafe_allow_html=True)
        else:
            btn_label = (
                f"{'🌬️' if is_wind else '⚡'} Generate Daily Report →" if choice == "daily"
                else "📅 Generate Monthly Report →" if choice == "monthly"
                else "📊 Generate Comprehensive Report →"
            )
            if st.button(btn_label, key="btn_generate", width="stretch"):
                st.session_state["report_type"] = choice
                st.session_state.pop("report_choice", None)
                st.session_state["view"] = (
                    ("wind_daily_config" if is_wind else "daily_config")
                    if choice == "daily"
                    else "monthly_config" if choice == "monthly"
                    else "comp_info"
                )
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# VIEW: DAILY REPORT CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

def _view_daily_config():
    _sync_custom_sites()
    _render_header()
    _apply_solar2_bg()

    site_id = st.session_state.get("selected_site", "")
    site    = SITES.get(site_id, {})

    col_back, col_port, _ = st.columns([1, 2, 3])
    with col_back:
        if st.button("← Back"):
            st.session_state["view"] = "report_select"
            st.rerun()
    with col_port:
        if st.button("← Back to Portfolio"):
            st.session_state["view"] = "portfolio"
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
            ["Site SCADA files (auto)", "Upload files"],
            index=0,
        )

    _ACCEPTED = ["csv", "xlsx", "xls", "txt"]
    uploaded_files = []
    mapped_files   = None
    tmp_data_dir   = None

    if data_source == "Upload files":
        st.markdown("""<div class="sub-hdr">Upload SCADA Data</div>""",
                    unsafe_allow_html=True)
        st.caption(
            "Upload one or more CSV / Excel files. Each file can contain "
            "time, power (inverters, combiner boxes — all selected columns are summed) "
            "and irradiance columns. The platform auto-detects and lets you confirm."
        )
        uploaded_files = st.file_uploader(
            "SCADA data files (CSV / Excel)", type=_ACCEPTED,
            accept_multiple_files=True, key="up_files")

        # ── Column mapping preview ─────────────────────────────────────────────
        if uploaded_files:
            st.markdown("<div class='sub-hdr'>Column Mapping</div>",
                        unsafe_allow_html=True)
            mapped_files = _show_column_mapper(
                uploaded_files, site_type="solar", state_key="cm_files")

    st.divider()

    # Disable generate button if files uploaded but mapping not yet confirmed
    _files_pending = bool(
        data_source == "Upload files" and
        uploaded_files and
        mapped_files is None
    )
    if _files_pending:
        st.info("✏️ Confirm the column mapping above, then click Generate.")

    _, col_btn, _ = st.columns([2, 2, 2])
    with col_btn:
        generate = st.button("⚡ Generate Daily Report", disabled=_files_pending)

    if generate:
        import tempfile, shutil
        from pathlib import Path as _Path

        # Resolve data directory
        if data_source == "Upload files" and uploaded_files:
            tmp = tempfile.mkdtemp(prefix="pvpat_daily_")
            tmp_data_dir = _Path(tmp)

            if mapped_files:
                # Write normalised files (power summed, irradiance included if mapped)
                for fname, norm_df in _normalise_files(mapped_files, "solar"):
                    norm_df.to_csv(tmp_data_dir / fname, index=False, sep=";")
            else:
                # Fallback: write raw files as-is
                for f in uploaded_files:
                    (tmp_data_dir / f.name).write_bytes(f.getbuffer().tobytes())
        else:
            raw_dir = site.get("data_dir")
            tmp_data_dir = _Path(raw_dir) if raw_dir else None

        # Guard: if data dir doesn't exist (e.g. running on Cloud) abort early
        if tmp_data_dir is None or not tmp_data_dir.exists():
            if data_source != "Upload files":
                st.warning(
                    "⚠️ No SCADA data files found for this site on this server. "
                    "Switch to **'Upload files'** and provide your CSV or Excel exports "
                    "to generate the report."
                )
            else:
                st.error("Could not write uploaded files to a temp directory.")
        else:
            with st.spinner("Analysing data and generating report…"):
                try:
                    from report.build_scada_analysis_html import build_scada_analysis_html

                    site_safe = "".join(
                        c if c.isalnum() else "_"
                        for c in site.get("display_name", "site")
                    )
                    date_str  = report_date.strftime("%Y%m%d")
                    out_html  = (
                        _Path(tempfile.mkdtemp(prefix="pvpat_daily_"))
                        / f"PVPAT_Daily_{site_safe}_{date_str}.html"
                    )

                    result = build_scada_analysis_html(
                        site_cfg = site,
                        data_dir = tmp_data_dir,
                        out_path = out_html,
                    )
                    pdf_path, html_path = result[0], result[1]
                    pdf_errors = result[2] if len(result) > 2 else []

                    if pdf_path and pdf_path.exists():
                        pdf_bytes = pdf_path.read_bytes()
                        st.success(f"✅ Daily report generated: **{pdf_path.name}**")
                        st.download_button(
                            label    = "⬇️  Download PDF Report",
                            data     = pdf_bytes,
                            file_name= pdf_path.name,
                            mime     = "application/pdf",
                        )
                        from datetime import datetime as _dt
                        _sp_path = f"{_SP_REPORTS_DIR}/{site_id}/{pdf_path.name}"
                        _save_report_to_history(site_id, {
                            "report_type": "daily",
                            "date":        report_date.strftime("%d %b %Y"),
                            "filename":    pdf_path.name,
                            "sp_path":     _sp_path,
                            "generated_at": _dt.now().strftime("%Y-%m-%d %H:%M"),
                        }, pdf_bytes)
                    elif html_path and html_path.exists():
                        st.warning(
                            "PDF generation requires WeasyPrint or Playwright. "
                            "Downloading as HTML instead — open in any browser and use "
                            "**File → Print → Save as PDF**."
                        )
                        if pdf_errors:
                            with st.expander("🔧 PDF engine errors (for diagnosis)"):
                                for err in pdf_errors:
                                    st.code(err)
                        st.download_button(
                            label    = "⬇️  Download Report (HTML)",
                            data     = html_path.read_bytes(),
                            file_name= html_path.name,
                            mime     = "text/html",
                        )
                    else:
                        st.error("Report generation produced no output file. "
                                 "Check that your SCADA data covers the selected date.")

                except Exception as exc:
                    st.error(f"Report generation failed: {exc}")
                    st.exception(exc)
                finally:
                    if data_source == "Upload files" and tmp_data_dir:
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
# VIEW: COMPREHENSIVE REPORT — AUTO-GENERATE
# ─────────────────────────────────────────────────────────────────────────────

def _view_comp_info():
    import shutil as _shutil, tempfile as _tmpfile
    from pathlib import Path as _Path

    _sync_custom_sites()
    _render_header()
    _apply_solar2_bg()
    site_id = st.session_state.get("selected_site", "")
    site    = SITES.get(site_id, {})

    col_back, col_port, _ = st.columns([1, 2, 3])
    with col_back:
        if st.button("← Back"):
            st.session_state["view"] = "report_select"
            st.rerun()
    with col_port:
        if st.button("← Back to Portfolio"):
            st.session_state["view"] = "portfolio"
            st.rerun()

    st.markdown(
        f"<div class='step-hdr'>Comprehensive SCADA Analysis — {site.get('display_name','')}</div>",
        unsafe_allow_html=True)

    st.markdown("""
    <p style="color:rgba(255,255,255,0.75);font-size:0.90rem;margin-bottom:1.2rem;">
      Upload your SCADA export files (CSV or Excel) and click <strong>Generate</strong>.
      The platform will produce a full multi-section PDF report — completeness heatmap,
      energy &amp; irradiance overview, per-inverter specific yield, loss waterfall, and
      action punchlist — in seconds.
    </p>""", unsafe_allow_html=True)

    # ── Data source ────────────────────────────────────────────────────────────
    _ACCEPTED_COMP = ["csv", "xlsx", "xls", "txt"]
    st.markdown("<div class='sub-hdr'>Upload SCADA Data</div>", unsafe_allow_html=True)
    st.caption(
        "Upload one or more CSV / Excel files containing timestamped inverter power "
        "(or energy) and irradiance. The report adapts automatically to the time span "
        "of your data — day, month, or multi-year."
    )
    comp_uploaded = st.file_uploader(
        "SCADA data files (CSV / Excel)",
        type=_ACCEPTED_COMP, accept_multiple_files=True, key="comp_scada") or []

    tmp_data_dir = None
    _files_pending = False

    if comp_uploaded:
        st.markdown("<div class='sub-hdr'>Column Mapping</div>", unsafe_allow_html=True)
        comp_mapped = _show_column_mapper(comp_uploaded, site_type="solar",
                                          state_key="cm_comp")
        _files_pending = comp_mapped is None
        if _files_pending:
            st.info("✏️ Confirm the column mapping above, then click Generate.")
    else:
        comp_mapped = None
        raw_dir = site.get("data_dir")
        if raw_dir and _Path(raw_dir).exists():
            tmp_data_dir = _Path(raw_dir)

    st.divider()

    if not comp_uploaded and tmp_data_dir is None:
        st.warning(
            "⚠️ No SCADA data files found for this site on this server. "
            "Switch to **'Upload files'** and provide your CSV or Excel exports "
            "to generate the report."
        )

    _, col_btn, _ = st.columns([2, 2, 2])
    with col_btn:
        generate = st.button(
            "📊 Generate Comprehensive Report",
            disabled=_files_pending or (not comp_uploaded and tmp_data_dir is None),
        )

    if generate:
        if comp_uploaded:
            tmp = _tmpfile.mkdtemp(prefix="pvpat_comp_")
            tmp_data_dir = _Path(tmp)
            if comp_mapped:
                for fname, norm_df in _normalise_files(comp_mapped, "solar"):
                    norm_df.to_csv(tmp_data_dir / fname, index=False, sep=";")
            else:
                for f in comp_uploaded:
                    (tmp_data_dir / f.name).write_bytes(f.getbuffer().tobytes())

        with st.spinner("Analysing data and generating comprehensive report…"):
            try:
                import sys as _sys
                _sys.path.insert(0, str(SCRIPT_DIR))
                from report.build_scada_analysis_html import build_scada_analysis_html

                result = build_scada_analysis_html(
                    site_cfg = site,
                    data_dir = tmp_data_dir,
                )
                pdf_path, html_path = result[0], result[1]
                pdf_errors = result[2] if len(result) > 2 else []

                if pdf_path and pdf_path.exists():
                    pdf_bytes = pdf_path.read_bytes()
                    st.success(f"✅ Comprehensive report generated: **{pdf_path.name}**")
                    st.download_button(
                        label     = "⬇️  Download PDF Report",
                        data      = pdf_bytes,
                        file_name = pdf_path.name,
                        mime      = "application/pdf",
                    )
                    from datetime import datetime as _dt
                    _sp_path = f"{_SP_REPORTS_DIR}/{site_id}/{pdf_path.name}"
                    _save_report_to_history(site_id, {
                        "report_type": "comprehensive",
                        "date":        _dt.now().strftime("%d %b %Y"),
                        "filename":    pdf_path.name,
                        "sp_path":     _sp_path,
                        "generated_at": _dt.now().strftime("%Y-%m-%d %H:%M"),
                    }, pdf_bytes)
                elif html_path and html_path.exists():
                    st.warning(
                        "PDF generation requires WeasyPrint system libraries. "
                        "Downloading as HTML instead — open in any browser and use "
                        "**File → Print → Save as PDF**."
                    )
                    if pdf_errors:
                        with st.expander("🔧 PDF engine errors (for diagnosis)"):
                            for err in pdf_errors:
                                st.code(err)
                    st.download_button(
                        label     = "⬇️  Download Report (HTML)",
                        data      = html_path.read_bytes(),
                        file_name = html_path.name,
                        mime      = "text/html",
                    )
                else:
                    st.error("Report generation produced no output. "
                             "Check that your SCADA data covers the selected period.")

            except Exception as exc:
                st.error(f"Report generation failed: {exc}")
                st.exception(exc)
            finally:
                if comp_uploaded and tmp_data_dir:
                    _shutil.rmtree(str(tmp_data_dir), ignore_errors=True)


# ─────────────────────────────────────────────────────────────────────────────
# VIEW: WIND DAILY REPORT CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

def _view_wind_daily_config():
    _sync_custom_sites()
    _render_header()
    _apply_wind_bg()

    site_id = st.session_state.get("selected_site", "")
    site    = SITES.get(site_id, {})

    col_back, col_port, _ = st.columns([1, 2, 3])
    with col_back:
        if st.button("← Back"):
            st.session_state["view"] = "report_select"
            st.rerun()
    with col_port:
        if st.button("← Back to Portfolio"):
            st.session_state["view"] = "portfolio"
            st.rerun()

    st.markdown(
        f"<div class='step-hdr'>🌬️ Wind Daily Report — {site.get('display_name','')}</div>",
        unsafe_allow_html=True)

    st.markdown("""<div class="sub-hdr">Report Configuration</div>""", unsafe_allow_html=True)

    yesterday = date.today() - timedelta(days=1)
    c1, c2 = st.columns([1, 1])
    with c1:
        report_date = st.date_input(
            "Report date", value=yesterday, max_value=date.today(),
            help="Select the day you want to analyse.")
    with c2:
        data_source = st.radio(
            "Data source",
            ["Upload SCADA files"],
            index=0)

    st.markdown("""<div class="sub-hdr">Upload Wind SCADA Data</div>""", unsafe_allow_html=True)
    st.caption(
        "10-min turbine SCADA export. Expected columns: "
        "`Time_UDT ; TURBINE ; POWER_KW ; WIND_MS ; WIND_DIR_DEG ; AVAILABILITY_PCT`")

    cu1, cu2 = st.columns(2)
    with cu1:
        uploaded_power = st.file_uploader(
            "Turbine power / status files", type=["csv","txt"],
            accept_multiple_files=True, key="wind_up_power")
    with cu2:
        uploaded_met = st.file_uploader(
            "Met mast / wind data (optional)", type=["csv","txt"],
            accept_multiple_files=True, key="wind_up_met")

    st.divider()

    _, col_btn, _ = st.columns([2, 2, 2])
    with col_btn:
        generate = st.button("🌬️ Generate Wind Daily Report")

    if generate:
        st.info(
            "Wind daily report generation is coming soon. "
            "Your data has been noted — the 8p2 team will process it manually "
            "and deliver the report within 24 hours.",
            icon="🔧")
        if uploaded_power:
            st.markdown(
                f"**{len(uploaded_power)} file(s) uploaded** for "
                f"{site.get('display_name','')} — {report_date.strftime('%d %b %Y')}",
                unsafe_allow_html=False)


# ─────────────────────────────────────────────────────────────────────────────
# VIEW: SITE DETAIL  (intro page with key info, technical specs, map)
# ─────────────────────────────────────────────────────────────────────────────

def _view_site_detail():
    _sync_custom_sites()
    _render_header()

    site_id  = st.session_state.get("selected_site", "")
    site     = SITES.get(site_id, {})
    is_wind  = site.get("site_type") == "wind"
    site_icon = "🌬️" if is_wind else "☀️"

    if is_wind:
        _apply_wind_bg()

    col_back, col_explorer, _ = st.columns([1.6, 1.9, 3.5])
    with col_back:
        if st.button("← Back to Portfolio"):
            st.session_state["view"] = "portfolio"
            st.rerun()
    with col_explorer:
        if (not is_wind) and st.button("Open Solar Explorer", key="site_open_solar_explorer"):
            st.session_state["view"] = "solar_explorer"
            st.rerun()

    st.markdown(
        f"<div class='step-hdr'>{site_icon} {site.get('display_name', '')}</div>",
        unsafe_allow_html=True)

    cap_mwp   = site.get("cap_dc_kwp", 0) / 1000
    cap_ac    = site.get("cap_ac_kw",  0) / 1000
    status    = site.get("status", "operational")
    status_col = {"operational": "#2E8B57", "maintenance": "#E67E22",
                  "offline": "#C0392B"}.get(status, "#888")

    col_left, col_right = st.columns([1.1, 1])

    with col_left:
        st.markdown("<div class='sub-hdr'>Site Information</div>", unsafe_allow_html=True)
        loc_parts = [site.get("region", ""), site.get("country", "")]
        location  = ", ".join(p for p in loc_parts if p)
        info_rows = [
            ("Location",   location or "—"),
            ("Status",     f"<span style='color:{status_col};font-weight:700;'>"
                           f"{status.upper()}</span>"),
            ("COD",        site.get("cod", "—")),
            ("Technology", site.get("technology", "—")),
        ]
        if is_wind:
            info_rows.append(("Capacity", f"{cap_mwp:.2f} MW"))
        else:
            info_rows += [
                ("DC Capacity", f"{cap_mwp:.2f} MWp"),
                ("AC Capacity", f"{cap_ac:.2f} MW"),
            ]
        _TD_LBL = ("color:rgba(255,255,255,0.55);font-size:0.83rem;"
                   "padding:5px 16px 5px 0;white-space:nowrap;"
                   "vertical-align:top;width:130px;")
        _TD_VAL = "color:white;font-size:0.88rem;padding:5px 0;"

        st.markdown(
            "<table style='border-collapse:collapse;width:100%;'><tbody>"
            + "".join(
                f"<tr><td style='{_TD_LBL}'>{k}</td>"
                f"<td style='{_TD_VAL}'>{v}</td></tr>"
                for k, v in info_rows
            )
            + "</tbody></table>",
            unsafe_allow_html=True)

        st.markdown("<div class='sub-hdr' style='margin-top:1rem;'>Technical Details</div>",
                    unsafe_allow_html=True)
        if is_wind:
            tech_rows = [
                ("Turbine model",    site.get("technology", "—")),
                ("No. of turbines",  str(site.get("n_inverters", "—"))),
                ("Unit capacity",    (f"{site['inv_ac_kw']/1000:.1f} MW"
                                      if site.get("inv_ac_kw") else "—")),
                ("Hub height",       (f"{site['hub_height_m']} m"
                                      if site.get("hub_height_m") else "—")),
                ("Height to blade tip", (f"{site['tip_height_m']} m"
                                         if site.get("tip_height_m") else "—")),
                ("Expected AEP",     (f"{site['expected_aep_gwh']:.1f} GWh/yr"
                                      if site.get("expected_aep_gwh") else "—")),
            ]
        else:
            tech_rows = [
                ("Inverter model",   site.get("inverter_model", "—")),
                ("No. of inverters", str(site.get("n_inverters", "—"))),
                ("Inverter size",    (f"{site['inv_ac_kw']:.0f} kW"
                                      if site.get("inv_ac_kw") else "—")),
                ("No. of modules",   (f"{site['n_modules']:,}"
                                      if site.get("n_modules") else "—")),
                ("Module Wp",        (f"{site['module_wp']:.0f} Wp"
                                      if site.get("module_wp") else "—")),
                ("DC/AC ratio",      (f"{site['dc_ac_ratio']:.2f}"
                                      if site.get("dc_ac_ratio") else "—")),
                ("Design PR",        (f"{site['design_pr']*100:.1f}%"
                                      if site.get("design_pr") else "—")),
            ]
        st.markdown(
            "<table style='border-collapse:collapse;width:100%;'><tbody>"
            + "".join(
                f"<tr><td style='{_TD_LBL}'>{k}</td>"
                f"<td style='{_TD_VAL}'>{v}</td></tr>"
                for k, v in tech_rows
            )
            + "</tbody></table>",
            unsafe_allow_html=True)

    with col_right:
        lat = site.get("lat")
        lon = site.get("lon")
        if lat and lon:
            st.markdown("<div class='sub-hdr'>Location Map</div>", unsafe_allow_html=True)
            bbox = f"{lon-15},{lat-10},{lon+15},{lat+10}"
            st.markdown(f"""
            <iframe
              src="https://www.openstreetmap.org/export/embed.html?bbox={bbox}&layer=mapnik&marker={lat},{lon}"
              style="width:100%;height:185px;border:1px solid rgba(255,255,255,0.15);
                     border-radius:8px;" loading="lazy">
            </iframe>
            <div style="font-size:0.70rem;color:rgba(255,255,255,0.35);
                        margin-top:4px;text-align:right;">
              Map © <a href="https://www.openstreetmap.org/"
                       style="color:rgba(255,255,255,0.35);">OpenStreetMap</a> contributors
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(
                "<p style='color:rgba(255,255,255,0.45);font-size:0.85rem;margin-top:2rem;'>"
                "No GPS coordinates configured for this site.</p>",
                unsafe_allow_html=True)

        # ── Performance Overview card ──────────────────────────────────────
        st.markdown(
            "<div class='sub-hdr' style='margin-top:1.1rem;'>Performance Overview</div>",
            unsafe_allow_html=True)

        import numpy as _np
        import matplotlib.pyplot as _plt
        import matplotlib.patches as _mpatches

        _fig, _ax = _plt.subplots(figsize=(4.2, 2.0))
        _fig.patch.set_facecolor("#0d1b2a")
        _ax.set_facecolor("#0d1b2a")

        if is_wind:
            # ── Wind: power curve scatter plot ────────────────────────────
            _inv_kw  = site.get("inv_ac_kw") or 0
            _n_turb  = max(site.get("n_inverters") or 1, 1)
            rated_kw = _inv_kw or (site.get("cap_ac_kw", 0) / _n_turb) or 4500.0
            cut_in, rated_ws, cut_out = 3.0, 13.0, 22.0

            def _mfr_curve(ws):
                p = _np.zeros_like(ws, dtype=float)
                mask = (ws >= cut_in) & (ws < rated_ws)
                p[mask] = rated_kw * ((ws[mask] - cut_in) / (rated_ws - cut_in)) ** 3
                p[(ws >= rated_ws) & (ws < cut_out)] = rated_kw
                return p

            _rng = _np.random.default_rng(42)
            _ws_scatter = _np.clip(_rng.weibull(2.2, 320) * 9.0, 0, 25)
            _pw_scatter = _np.clip(
                _mfr_curve(_ws_scatter) + _rng.normal(0, 90, len(_ws_scatter)),
                0, rated_kw * 1.02,
            )
            # Inject ~6 % curtailment / stop points
            _stop_idx = _rng.choice(len(_ws_scatter), size=20, replace=False)
            _pw_scatter[_stop_idx] = _rng.uniform(0, 40, 20)

            _ax.scatter(_ws_scatter, _pw_scatter / 1000,
                        color="#5B9BD5", alpha=0.45, s=7, zorder=3,
                        label="SCADA (indicative)")

            _ws_line = _np.linspace(0, 25, 200)
            _ax.plot(_ws_line, _mfr_curve(_ws_line) / 1000,
                     color="#F39200", linewidth=1.6, zorder=4,
                     label="Mfr. curve")

            _ax.set_xlim(0, 25)
            _ax.set_ylim(-0.1, rated_kw / 1000 * 1.12)
            _ax.set_xlabel("Wind speed (m/s)", color=(1,1,1,0.55), fontsize=6.5)
            _ax.set_ylabel("Power (MW)", color=(1,1,1,0.55), fontsize=6.5)
            _ax.tick_params(colors="white", labelsize=6.5)
            for spine in _ax.spines.values():
                spine.set_visible(False)
            _ax.grid(color="white", alpha=0.07, zorder=0)
            _ax.legend(fontsize=6, facecolor="#0d1b2a", labelcolor="white",
                       framealpha=0.5, loc="upper left")
            _plt.tight_layout(pad=0.3)
            st.pyplot(_fig, width="stretch")
            _plt.close(_fig)
            st.markdown(
                "<p style='color:rgba(255,255,255,0.38);font-size:0.70rem;margin-top:0;'>"
                "Indicative power curve — connect SCADA or upload data for live results.</p>",
                unsafe_allow_html=True)

        else:
            # ── Solar: monthly PR bar chart ───────────────────────────────
            design_pr = site.get("design_pr") or 0.80
            target_pr = site.get("operating_pr_target") or max(design_pr - 0.02, 0.55)

            _months = ["Jan","Feb","Mar","Apr","May","Jun",
                       "Jul","Aug","Sep","Oct","Nov","Dec"]
            _seasonal = _np.array([0.02,0.02,0.01,0,-0.01,-0.03,
                                    -0.04,-0.03,-0.01, 0, 0.01,0.02])
            _pr_vals  = _np.clip(design_pr + _seasonal - 0.03, 0.55, 0.99)

            _colors = ["#2E8B57" if v >= target_pr else "#E67E22" for v in _pr_vals]
            _ax.bar(_months, _pr_vals * 100, color=_colors, width=0.65, zorder=3)
            _ax.axhline(target_pr * 100, color="#f0c040", linewidth=1.2,
                        linestyle="--", zorder=4)

            _ymin = max(0,   (float(_pr_vals.min()) - 0.06) * 100)
            _ymax = min(100, (float(_pr_vals.max()) + 0.06) * 100)
            _ax.set_ylim(_ymin, _ymax)
            _ax.tick_params(colors="white", labelsize=6.5)
            for spine in _ax.spines.values():
                spine.set_visible(False)
            _ax.set_ylabel("PR (%)", color=(1, 1, 1, 0.55), fontsize=6.5)
            _ax.grid(axis="y", color="white", alpha=0.08, zorder=0)

            _patch = _mpatches.Patch(color="#f0c040",
                                      label=f"Target {target_pr*100:.0f}%")
            _ax.legend(handles=[_patch], fontsize=6, facecolor="#0d1b2a",
                       labelcolor="white", framealpha=0.5, loc="lower right")

            _plt.tight_layout(pad=0.3)
            st.pyplot(_fig, width="stretch")
            _plt.close(_fig)
            st.markdown(
                "<p style='color:rgba(255,255,255,0.38);font-size:0.70rem;margin-top:0;'>"
                "Indicative monthly PR — connect SCADA for live data.</p>",
                unsafe_allow_html=True)

    st.divider()
    _, col_gen, _ = st.columns([2, 2, 2])
    with col_gen:
        if st.button(f"{'🌬️' if is_wind else '⚡'} Generate Report →",
                     key="btn_detail_gen", width="stretch"):
            st.session_state["view"] = "report_select"
            st.rerun()


def _view_solar_explorer():
    _sync_custom_sites()
    _render_header()

    site_id = st.session_state.get("selected_site", "")
    site = SITES.get(site_id, {})
    site_name = site.get("display_name") if site.get("site_type") != "wind" else None

    col_back, _ = st.columns([1.6, 4])
    with col_back:
        if st.button("← Back", key="back_from_solar_explorer"):
            st.session_state["view"] = "site_detail" if site_name else "portfolio"
            st.rerun()

    st.markdown(
        "<div class='step-hdr'>Solar Farm Anatomy Explorer</div>",
        unsafe_allow_html=True)
    st.markdown(
        "<p style='color:rgba(255,255,255,0.72);margin-bottom:1rem;'>"
        "A client-facing interactive reference page for utility-scale PV and battery storage architecture."
        "</p>",
        unsafe_allow_html=True)
    # render_solar_farm_explorer(site_name=site_name)  # TODO: visual redesign in progress


# ─────────────────────────────────────────────────────────────────────────────
# VIEW: SITE EDIT
# ─────────────────────────────────────────────────────────────────────────────

def _view_site_edit():
    _sync_custom_sites()
    _render_header()

    import equipment_kb as _kb

    WIND_TURBINES = getattr(_kb, "WIND_TURBINES", {})
    SOLAR_INVERTERS = getattr(_kb, "SOLAR_INVERTERS", {})
    SOLAR_MODULES = getattr(_kb, "SOLAR_MODULES", {})
    SOLAR_MODULE_MANUFACTURERS = getattr(
        _kb, "SOLAR_MODULE_MANUFACTURERS", list(SOLAR_MODULES.keys())
    )
    detect_wind_manufacturer = getattr(_kb, "detect_wind_manufacturer", lambda _value: "")
    detect_inverter_manufacturer = getattr(_kb, "detect_inverter_manufacturer", lambda _value: "")

    def detect_module_manufacturer(module_model: str) -> str:
        custom_detector = getattr(_kb, "detect_module_manufacturer", None)
        if callable(custom_detector):
            return custom_detector(module_model)
        if not module_model:
            return ""
        text = str(module_model).lower()
        for manufacturer in SOLAR_MODULE_MANUFACTURERS:
            short_name = str(manufacturer).lower().split("/")[0].strip()
            if short_name and short_name in text:
                return manufacturer
        return ""

    def get_wind_turbine_spec(manufacturer: str, model: str) -> dict:
        getter = getattr(_kb, "get_wind_turbine_spec", None)
        if callable(getter):
            return getter(manufacturer, model)
        return {}

    def get_inverter_spec(manufacturer: str, model: str) -> dict:
        getter = getattr(_kb, "get_inverter_spec", None)
        if callable(getter):
            return getter(manufacturer, model)
        return {}

    def get_solar_module_spec(manufacturer: str, model: str) -> dict:
        getter = getattr(_kb, "get_solar_module_spec", None)
        if callable(getter):
            return getter(manufacturer, model)
        models = SOLAR_MODULES.get(manufacturer, [])
        if model in models:
            return {}
        return {}

    def _init_state(key: str, value):
        if key not in st.session_state:
            st.session_state[key] = value

    def _safe_float(raw):
        try:
            return float(str(raw).replace(",", ".").strip())
        except (TypeError, ValueError, AttributeError):
            return None

    def _safe_int(raw):
        try:
            return int(str(raw).replace(" ", "").strip())
        except (TypeError, ValueError, AttributeError):
            return None

    def _fmt_number(value, decimals: int = 3) -> str:
        if value in (None, ""):
            return ""
        text = f"{float(value):.{decimals}f}"
        return text.rstrip("0").rstrip(".")

    def _find_matching_model(candidates: list[str], text: str) -> str:
        _txt = (text or "").lower()
        for candidate in candidates:
            if candidate.lower() in _txt:
                return candidate
        return ""

    def _derive_wind_defaults(spec: dict, turbine_count: int) -> tuple[float | None, int | None, int | None, float | None]:
        rotor = _safe_float(spec.get("rotor_diameter_m")) if spec else None
        rated_mw = _safe_float(spec.get("rated_mw")) if spec else None
        hub_height = int(round(max(rotor * 0.82, 80))) if rotor else None
        tip_height = int(round(hub_height + rotor / 2)) if hub_height and rotor else None
        expected_aep = round(rated_mw * max(turbine_count, 1) * 2.9, 1) if rated_mw else None
        return rated_mw, hub_height, tip_height, expected_aep

    def _infer_module_rows(site_cfg: dict) -> list[dict]:
        module_mix = site_cfg.get("module_mix")
        if isinstance(module_mix, list):
            rows = []
            for entry in module_mix:
                if not isinstance(entry, dict):
                    continue
                rows.append({
                    "manufacturer": str(entry.get("manufacturer", "")).strip(),
                    "model": str(entry.get("model", "")).strip(),
                    "quantity": int(entry.get("quantity", 0) or 0),
                    "power_wp": float(entry.get("power_wp", 0) or 0),
                })
            if rows:
                return rows

        technology = site_cfg.get("technology", "")
        manufacturer = detect_module_manufacturer(technology)
        model = _find_matching_model(SOLAR_MODULES.get(manufacturer, []), technology)
        power_wp = float(site_cfg.get("module_wp", 0) or 0)
        if not power_wp and manufacturer and model:
            power_wp = float(get_solar_module_spec(manufacturer, model).get("power_wp", 0) or 0)
        quantity = int(site_cfg.get("n_modules", 0) or 0)
        return [{
            "manufacturer": manufacturer,
            "model": model,
            "quantity": quantity,
            "power_wp": power_wp,
        }]

    def _build_module_summary(rows: list[dict]) -> str:
        clean_rows = []
        for row in rows:
            qty = int(row.get("quantity", 0) or 0)
            power_wp = float(row.get("power_wp", 0) or 0)
            manufacturer = str(row.get("manufacturer", "")).strip()
            model = str(row.get("model", "")).strip()
            if qty <= 0 or power_wp <= 0:
                continue
            label = " ".join(part for part in (manufacturer, model) if part).strip() or "Module"
            clean_rows.append(f"{qty:,} x {label} ({power_wp:.0f} Wp)")
        if not clean_rows:
            return site.get("technology", "—")
        if len(clean_rows) == 1:
            return clean_rows[0]
        return "Mixed modules: " + " + ".join(clean_rows)

    site_id   = st.session_state.get("selected_site", "")
    site      = dict(SITES.get(site_id, {}))
    is_custom = site_id in st.session_state.get("custom_sites", {})

    col_back, _ = st.columns([2, 4])
    with col_back:
        if st.button(_t("nav.back_portfolio"), key="edit_back"):
            st.session_state["view"] = "portfolio"
            st.rerun()

    st.markdown(
        f"<div class='step-hdr'>{_t('site.edit.title', site=site.get('display_name', site_id))}</div>",
        unsafe_allow_html=True)

    if not site:
        st.error(_t("site.edit.error.site_missing"))
        return

    is_wind = site.get("site_type") == "wind"

    prefix = f"edit_{site_id}"
    _div = "<hr style='border-color:rgba(255,255,255,0.1);margin:0.6rem 0;'>"

    _init_state(f"{prefix}_name", site.get("display_name", ""))
    _init_state(f"{prefix}_status", site.get("status", "operational"))
    _init_state(f"{prefix}_country", site.get("country", ""))
    _init_state(f"{prefix}_region", site.get("region", ""))
    _init_state(f"{prefix}_cod", site.get("cod", ""))

    if is_wind:
        st.markdown(f"<div class='sub-hdr'>{_t('site.edit.wind.section')}</div>", unsafe_allow_html=True)
        _mfr_list = [""] + list(WIND_TURBINES.keys())
        _cur_mfr  = detect_wind_manufacturer(site.get("technology", ""))
        _mfr_idx  = _mfr_list.index(_cur_mfr) if _cur_mfr in _mfr_list else 0
        new_turbine_mfr = st.selectbox(
            _t("site.edit.wind.mfr"),
            _mfr_list,
            index=_mfr_idx,
            key=f"edit_wind_mfr_{site_id}",
        )
        _turbine_models = WIND_TURBINES.get(new_turbine_mfr, [])

        _wind_model_key = f"{prefix}_wind_model"
        _wind_capacity_key = f"{prefix}_wind_unit_cap_mw"
        _wind_last_model_key = f"{prefix}_wind_last_model"
        _wind_qty_key = f"{prefix}_wind_qty"
        _wind_hub_key = f"{prefix}_wind_hub"
        _wind_tip_key = f"{prefix}_wind_tip"
        _wind_aep_key = f"{prefix}_wind_aep"

        _wind_model_default = _find_matching_model(_turbine_models, site.get("technology", ""))
        _init_state(_wind_model_key, _wind_model_default)
        _init_state(_wind_qty_key, str(site.get("n_inverters", "") or ""))
        _init_state(_wind_hub_key, str(site.get("hub_height_m", "") or ""))
        _init_state(_wind_tip_key, str(site.get("tip_height_m", "") or ""))
        _init_state(_wind_aep_key, str(site.get("expected_aep_gwh", "") or ""))

        if _turbine_models:
            if st.session_state.get(_wind_model_key) not in _turbine_models:
                st.session_state[_wind_model_key] = _wind_model_default if _wind_model_default in _turbine_models else ""
            st.selectbox(_t("site.edit.wind.model"), [""] + _turbine_models, key=_wind_model_key)
            new_tech = st.session_state.get(_wind_model_key, "")
        else:
            _init_state(_wind_model_key, site.get("technology", ""))
            st.text_input(_t("site.edit.wind.model"), key=_wind_model_key, placeholder="e.g. V136-4.5")
            new_tech = st.session_state.get(_wind_model_key, "")

        _wind_spec = get_wind_turbine_spec(new_turbine_mfr, new_tech)
        _current_turbine_count = _safe_int(st.session_state.get(_wind_qty_key)) or _safe_int(site.get("n_inverters")) or 1
        _wind_default_capacity, _wind_default_hub, _wind_default_tip, _wind_default_aep = _derive_wind_defaults(
            _wind_spec, _current_turbine_count
        )
        if _wind_default_capacity is None:
            _wind_default_capacity = (site.get("inv_ac_kw") or 0) / 1000 if site.get("inv_ac_kw") else None
        if _wind_default_hub is None:
            _wind_default_hub = _safe_int(site.get("hub_height_m"))
        if _wind_default_tip is None:
            _wind_default_tip = _safe_int(site.get("tip_height_m"))
        if _wind_default_aep is None:
            _wind_default_aep = _safe_float(site.get("expected_aep_gwh"))

        _init_state(_wind_capacity_key, _fmt_number(_wind_default_capacity, 3))
        if st.session_state.get(_wind_last_model_key) != new_tech:
            st.session_state[_wind_last_model_key] = new_tech
            st.session_state[_wind_capacity_key] = _fmt_number(_wind_default_capacity, 3)
            st.session_state[_wind_hub_key] = str(_wind_default_hub or "")
            st.session_state[_wind_tip_key] = str(_wind_default_tip or "")
            st.session_state[_wind_aep_key] = _fmt_number(_wind_default_aep, 1)
    else:
        st.markdown(f"<div class='sub-hdr'>{_t('site.edit.solar.section')}</div>", unsafe_allow_html=True)
        _module_rows = _infer_module_rows(site)
        _module_type_default = max(1, min(len(_module_rows), 4))
        _init_state(f"{prefix}_module_multi", _module_type_default > 1)
        _init_state(f"{prefix}_module_type_count", _module_type_default)

        _multi_modules = st.checkbox(
            _t("site.edit.solar.multi"),
            key=f"{prefix}_module_multi",
        )
        if not _multi_modules:
            st.session_state[f"{prefix}_module_type_count"] = 1
        else:
            current_count = int(st.session_state.get(f"{prefix}_module_type_count", _module_type_default) or 2)
            count_options = [1, 2, 3, 4]
            count_index = count_options.index(current_count) if current_count in count_options else 1
            st.selectbox(
                _t("site.edit.solar.type_count"),
                count_options,
                index=count_index,
                key=f"{prefix}_module_type_count",
            )
        module_type_count = int(st.session_state.get(f"{prefix}_module_type_count", 1) or 1)

        for idx in range(module_type_count):
            existing = _module_rows[idx] if idx < len(_module_rows) else {}
            mfr_key = f"{prefix}_module_mfr_{idx}"
            model_key = f"{prefix}_module_model_{idx}"
            power_key = f"{prefix}_module_power_wp_{idx}"
            qty_key = f"{prefix}_module_qty_{idx}"
            last_model_key = f"{prefix}_module_last_model_{idx}"

            _init_state(mfr_key, existing.get("manufacturer", ""))
            _init_state(model_key, existing.get("model", ""))
            _init_state(power_key, _fmt_number(existing.get("power_wp"), 1))
            _init_state(qty_key, str(existing.get("quantity", "") or ""))

            st.markdown(f"**{_t('site.edit.solar.module_type', index=idx + 1)}**")
            mod_col1, mod_col2 = st.columns(2)
            with mod_col1:
                st.selectbox(
                    _t("site.edit.solar.module_mfr"),
                    [""] + SOLAR_MODULE_MANUFACTURERS,
                    key=mfr_key,
                )
            with mod_col2:
                _module_models = SOLAR_MODULES.get(st.session_state.get(mfr_key, ""), [])
                if _module_models:
                    if st.session_state.get(model_key) not in _module_models:
                        st.session_state[model_key] = existing.get("model", "") if existing.get("model", "") in _module_models else ""
                    st.selectbox(
                        _t("site.edit.solar.module_model"),
                        [""] + _module_models,
                        key=model_key,
                    )
                else:
                    st.text_input(_t("site.edit.solar.module_model"), key=model_key, placeholder="e.g. Hi-MO 6 LR5-72HTH")

            _module_spec = get_solar_module_spec(st.session_state.get(mfr_key, ""), st.session_state.get(model_key, ""))
            _module_default_power = _module_spec.get("power_wp")
            if not _module_default_power:
                _module_default_power = _safe_float(existing.get("power_wp"))
            if st.session_state.get(last_model_key) != st.session_state.get(model_key):
                st.session_state[last_model_key] = st.session_state.get(model_key)
                if _module_default_power:
                    st.session_state[power_key] = _fmt_number(_module_default_power, 1)

        _inv_mfr_list = [""] + list(SOLAR_INVERTERS.keys())
        _cur_inv_mfr  = detect_inverter_manufacturer(site.get("inverter_model", ""))
        _inv_mfr_idx  = _inv_mfr_list.index(_cur_inv_mfr) if _cur_inv_mfr in _inv_mfr_list else 0
        new_inv_mfr = st.selectbox(
            _t("site.edit.solar.inv_mfr"),
            _inv_mfr_list,
            index=_inv_mfr_idx,
            key=f"edit_inv_mfr_{site_id}",
        )
        _inv_models = SOLAR_INVERTERS.get(new_inv_mfr, [])
        _inv_model_key = f"{prefix}_inv_model"
        _inv_last_model_key = f"{prefix}_inv_last_model"
        _inv_power_key = f"{prefix}_inv_ac_kw"
        _inv_qty_key = f"{prefix}_inv_qty"
        _init_state(_inv_model_key, _find_matching_model(_inv_models, site.get("inverter_model", "")))
        _init_state(_inv_qty_key, str(site.get("n_inverters", "") or ""))
        _init_state(_inv_power_key, _fmt_number(site.get("inv_ac_kw"), 1))

        if _inv_models:
            if st.session_state.get(_inv_model_key) not in _inv_models:
                st.session_state[_inv_model_key] = _find_matching_model(_inv_models, site.get("inverter_model", ""))
            st.selectbox(_t("site.edit.solar.inv_model"), [""] + _inv_models, key=_inv_model_key)
        else:
            st.text_input(_t("site.edit.solar.inv_model"), key=_inv_model_key, placeholder="e.g. SG250HX")

        _inv_spec = get_inverter_spec(new_inv_mfr, st.session_state.get(_inv_model_key, ""))
        _inv_default_power = _inv_spec.get("ac_kw")
        if not _inv_default_power:
            _inv_default_power = site.get("inv_ac_kw")
        if st.session_state.get(_inv_last_model_key) != st.session_state.get(_inv_model_key):
            st.session_state[_inv_last_model_key] = st.session_state.get(_inv_model_key)
            if _inv_default_power:
                st.session_state[_inv_power_key] = _fmt_number(_inv_default_power, 1)

    st.markdown(_div, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.text_input(_t("site.edit.name"), key=f"{prefix}_name")
        st.selectbox(
            _t("site.edit.status"),
            ["operational", "maintenance", "offline"],
            key=f"{prefix}_status",
        )
    with c2:
        st.text_input(_t("site.edit.country"), key=f"{prefix}_country")
        st.text_input(_t("site.edit.region"), key=f"{prefix}_region")
        st.text_input(_t("site.edit.cod"), key=f"{prefix}_cod")

    if is_wind:
        _wind_unit_mw = _safe_float(st.session_state.get(_wind_capacity_key)) or 0.0
        _wind_qty = _safe_int(st.session_state.get(_wind_qty_key)) or 0
        _wind_total_mw = _wind_unit_mw * _wind_qty

        w1, w2 = st.columns(2)
        with w1:
            st.text_input(
                _t("site.edit.wind.capacity"),
                key=_wind_capacity_key,
                placeholder="e.g. 4.5",
            )
            st.text_input(
                _t("site.edit.wind.hub"),
                key=_wind_hub_key,
                placeholder="e.g. 112",
            )
        with w2:
            st.text_input(
                _t("site.edit.wind.count"),
                key=_wind_qty_key,
                placeholder="e.g. 4",
            )
            st.text_input(
                _t("site.edit.wind.tip"),
                key=_wind_tip_key,
                placeholder="e.g. 180",
            )

        st.text_input(
            _t("site.edit.wind.aep"),
            key=_wind_aep_key,
            placeholder="e.g. 52.4",
        )
        st.text_input(_t("site.edit.wind.total"), value=_fmt_number(_wind_total_mw, 3), disabled=True)
        if _wind_spec.get("rotor_diameter_m"):
            st.caption(_t("site.edit.wind.rotor", rotor=_wind_spec["rotor_diameter_m"]))
        saved = st.button(_t("site.edit.save"), key=f"{prefix}_save", width="content")

    else:
        solar_rows = []
        st.markdown(f"**{_t('site.edit.solar.qty_power')}**")
        for idx in range(module_type_count):
            mfr_key = f"{prefix}_module_mfr_{idx}"
            model_key = f"{prefix}_module_model_{idx}"
            power_key = f"{prefix}_module_power_wp_{idx}"
            qty_key = f"{prefix}_module_qty_{idx}"

            row_col1, row_col2 = st.columns(2)
            with row_col1:
                st.text_input(
                    _t("site.edit.solar.qty", index=idx + 1),
                    key=qty_key,
                    placeholder="e.g. 10815",
                )
            with row_col2:
                st.text_input(
                    _t("site.edit.solar.power", index=idx + 1),
                    key=power_key,
                    placeholder="e.g. 585",
                )

            qty = _safe_int(st.session_state.get(qty_key)) or 0
            power_wp = _safe_float(st.session_state.get(power_key)) or 0.0
            subtotal_kwp = qty * power_wp / 1000.0
            manufacturer = st.session_state.get(mfr_key, "")
            model = st.session_state.get(model_key, "")
            label = " ".join(part for part in (manufacturer, model) if part).strip() or _t("site.edit.solar.module_type", index=idx + 1)
            st.caption(_t("site.edit.solar.subtotal", label=label, mw=subtotal_kwp / 1000.0))
            solar_rows.append({
                "manufacturer": manufacturer,
                "model": model,
                "quantity": qty,
                "power_wp": power_wp,
            })

        st.markdown(f"**{_t('site.edit.solar.inv_section')}**")
        inv_col1, inv_col2 = st.columns(2)
        with inv_col1:
            st.text_input(_t("site.edit.solar.inv_count"), key=_inv_qty_key, placeholder="e.g. 21")
        with inv_col2:
            st.text_input(_t("site.edit.solar.inv_power"), key=_inv_power_key, placeholder="e.g. 250")

        total_modules = sum(row["quantity"] for row in solar_rows)
        total_dc_kwp = sum(row["quantity"] * row["power_wp"] / 1000.0 for row in solar_rows)
        weighted_module_wp = (total_dc_kwp * 1000.0 / total_modules) if total_modules else 0.0
        inv_count = _safe_int(st.session_state.get(_inv_qty_key)) or 0
        inv_unit_kw = _safe_float(st.session_state.get(_inv_power_key)) or 0.0
        total_ac_kw = inv_count * inv_unit_kw
        dc_ac_ratio = total_dc_kwp / total_ac_kw if total_ac_kw > 0 else 0.0

        sum_col1, sum_col2, sum_col3 = st.columns(3)
        with sum_col1:
            st.text_input(_t("site.edit.solar.total_dc"), value=_fmt_number(total_dc_kwp / 1000.0, 3), disabled=True)
        with sum_col2:
            st.text_input(_t("site.edit.solar.total_ac"), value=_fmt_number(total_ac_kw / 1000.0, 3), disabled=True)
        with sum_col3:
            st.text_input(_t("site.edit.solar.ratio"), value=_fmt_number(dc_ac_ratio, 3), disabled=True)

        saved = st.button(_t("site.edit.save"), key=f"{prefix}_save", width="content")

    if saved:
        updates: dict = {
            "display_name": str(st.session_state.get(f"{prefix}_name", "")).strip() or site.get("display_name", ""),
            "status": str(st.session_state.get(f"{prefix}_status", site.get("status", "operational"))),
            "country": str(st.session_state.get(f"{prefix}_country", "")).strip(),
            "region": str(st.session_state.get(f"{prefix}_region", "")).strip(),
            "cod": str(st.session_state.get(f"{prefix}_cod", "")).strip(),
        }

        if is_wind:
            unit_cap_mw = _safe_float(st.session_state.get(_wind_capacity_key))
            n_turbines = _safe_int(st.session_state.get(_wind_qty_key))
            if not unit_cap_mw or unit_cap_mw <= 0 or not n_turbines or n_turbines <= 0:
                st.error(_t("site.edit.error.wind_required"))
                return

            total_kw = unit_cap_mw * n_turbines * 1000.0
            updates.update({
                "technology": " ".join(part for part in (new_turbine_mfr, new_tech) if part).strip() or site.get("technology", ""),
                "inverter_model": site.get("inverter_model", "—"),
                "inv_ac_kw": unit_cap_mw * 1000.0,
                "n_inverters": n_turbines,
                "cap_ac_kw": total_kw,
                "cap_dc_kwp": total_kw,
            })
            hub_height = _safe_int(st.session_state.get(_wind_hub_key))
            tip_height = _safe_int(st.session_state.get(_wind_tip_key))
            aep_gwh = _safe_float(st.session_state.get(_wind_aep_key))
            if hub_height and hub_height > 0:
                updates["hub_height_m"] = hub_height
            if tip_height and tip_height > 0:
                updates["tip_height_m"] = tip_height
            if aep_gwh and aep_gwh > 0:
                updates["expected_aep_gwh"] = aep_gwh
            if _wind_spec.get("rotor_diameter_m"):
                updates["rotor_diameter_m"] = int(_wind_spec["rotor_diameter_m"])
        else:
            clean_rows = [
                row for row in solar_rows
                if row["quantity"] > 0 and row["power_wp"] > 0
            ]
            if not clean_rows:
                st.error(_t("site.edit.error.solar_modules"))
                return
            if total_ac_kw <= 0 or inv_count <= 0:
                st.error(_t("site.edit.error.solar_inverters"))
                return

            updates.update({
                "technology": _build_module_summary(clean_rows),
                "inverter_model": str(st.session_state.get(_inv_model_key, "")).strip() or site.get("inverter_model", ""),
                "module_mix": clean_rows,
                "n_modules": total_modules,
                "module_wp": weighted_module_wp,
                "cap_dc_kwp": total_dc_kwp,
                "n_inverters": inv_count,
                "inv_ac_kw": inv_unit_kw,
                "cap_ac_kw": total_ac_kw,
                "dc_ac_ratio": dc_ac_ratio if dc_ac_ratio > 0 else site.get("dc_ac_ratio", 1.0),
            })

        if is_custom:
            st.session_state["custom_sites"][site_id].update(updates)
        else:
            SITES[site_id].update(updates)
            overrides = st.session_state.setdefault("custom_sites", {})
            if site_id not in overrides:
                overrides[site_id] = dict(SITES[site_id])
            else:
                overrides[site_id].update(updates)

        _sync_custom_sites()
        _save_custom_sites_to_disk()
        st.success(_t("site.edit.saved"))
        st.session_state["view"] = "portfolio"
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# VIEW: MONTHLY REPORT CONFIGURATION  (stub — coming soon)
# ─────────────────────────────────────────────────────────────────────────────

def _view_monthly_config():
    _sync_custom_sites()
    _render_header()

    site_id = st.session_state.get("selected_site", "")
    site    = SITES.get(site_id, {})

    col_back, col_port, _ = st.columns([1, 2, 3])
    with col_back:
        if st.button("← Back", key="monthly_cfg_back"):
            st.session_state["view"] = "report_select"
            st.rerun()
    with col_port:
        if st.button("← Back to Portfolio", key="monthly_cfg_back_port"):
            st.session_state["view"] = "portfolio"
            st.rerun()

    st.markdown(
        f"<div class='step-hdr'>Monthly Report — {site.get('display_name','')}</div>",
        unsafe_allow_html=True)

    st.markdown("""
    <div style="background:rgba(96,165,250,0.10);border:1.5px solid rgba(96,165,250,0.35);
      border-radius:10px;padding:1.2rem 1.6rem;color:rgba(255,255,255,0.85);font-size:0.92rem;
      margin-top:1rem;">
      📅 &nbsp;<strong>Monthly Report</strong> — configuration coming soon.<br>
      <span style="color:rgba(255,255,255,0.55);font-size:0.85rem;">
        This module is under development. Check back in the next release.
      </span>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# VIEW: REPORT HISTORY
# ─────────────────────────────────────────────────────────────────────────────

def _view_report_history():
    _sync_custom_sites()
    _render_header()

    site_id = st.session_state.get("selected_site", "")
    site    = SITES.get(site_id, {})
    is_wind = site.get("site_type") == "wind"
    if is_wind:
        _apply_wind_bg()
    else:
        _apply_solar2_bg()

    col_back, _ = st.columns([2, 4])
    with col_back:
        if st.button(_t("nav.back"), key="hist_back"):
            st.session_state["view"] = "report_select"
            st.rerun()

    st.markdown(
        f"<div class='step-hdr'>{_t('report.previous.title', site=site.get('display_name', ''))}</div>",
        unsafe_allow_html=True)

    with st.spinner(_t("report.previous.loading")):
        history = _load_report_history()
    reports = history.get(site_id, [])
    legacy_reports = _list_legacy_reports() if not reports else []

    if not reports and not legacy_reports:
        st.markdown(
            "<p style='color:rgba(255,255,255,0.55);margin-top:1.5rem;'>"
            + _t("report.previous.empty") + "</p>",
            unsafe_allow_html=True)
        return

    if legacy_reports:
        st.caption(_t("report.previous.legacy"))
        reports = legacy_reports

    # Track which entry the user wants to download (avoids loading all PDFs at once)
    if "hist_dl_idx" not in st.session_state:
        st.session_state["hist_dl_idx"] = None

    for i, entry in enumerate(reports):
        rtype    = entry.get("report_type", "report").title()
        rdate    = entry.get("date", "—")
        gen_at   = entry.get("generated_at", "")
        filename = entry.get("filename", "report.pdf")
        sp_path  = entry.get("sp_path")

        col_info, col_dl = st.columns([3, 1])
        with col_info:
            st.markdown(
                f"<div style='padding:0.55rem 0;"
                f"border-bottom:1px solid rgba(255,255,255,0.10);'>"
                f"<span style='color:white;font-weight:600;'>{rtype}</span>"
                f"<span style='color:rgba(255,255,255,0.50);font-size:0.82rem;'>"
                f" &nbsp;·&nbsp; {rdate} &nbsp;·&nbsp; generated {gen_at}</span>"
                f"</div>",
                unsafe_allow_html=True)

        with col_dl:
            if entry.get("local_path"):
                try:
                    with open(entry["local_path"], "rb") as fh:
                        st.download_button(
                            label="⬇️ Save file",
                            data=fh.read(),
                            file_name=filename,
                            mime="application/octet-stream",
                            key=f"save_local_{i}",
                            width="stretch",
                        )
                except Exception as _exc:
                    st.error(f"Failed: {_exc}")
            elif st.session_state["hist_dl_idx"] == i and sp_path:
                # Fetch PDF from SharePoint and offer download
                try:
                    import requests as _req
                    token, sp_site_id = _sharepoint_session()
                    url = (f"https://graph.microsoft.com/v1.0/sites/{sp_site_id}"
                           f"/drive/root:/{sp_path}:/content")
                    r = _req.get(url, headers={"Authorization": f"Bearer {token}"},
                                 timeout=30)
                    if r.status_code == 200:
                        st.download_button(
                            label     = "⬇️ Save PDF",
                            data      = r.content,
                            file_name = filename,
                            mime      = "application/pdf",
                            key       = f"save_{i}",
                            width     = "stretch",
                        )
                    else:
                        st.error("Not found in storage.")
                except Exception as _exc:
                    st.error(f"Failed: {_exc}")
                st.session_state["hist_dl_idx"] = None
            else:
                if st.button("⬇️ Download", key=f"fetch_{i}",
                             width="stretch"):
                    st.session_state["hist_dl_idx"] = i
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────────────────────────────────

if not _logged_in():
    _view_login()
else:
    _sync_custom_sites()          # always keep SITES in sync on every render
    view = st.session_state.get("view", "portfolio")
    if view == "portfolio":
        _view_portfolio()
    elif view == "site_detail":
        _view_site_detail()
    elif view == "report_select":
        _view_report_select()
    elif view == "daily_config":
        _view_daily_config()
    elif view == "wind_daily_config":
        _view_wind_daily_config()
    elif view == "comp_info":
        _view_comp_info()
    elif view == "monthly_config":
        _view_monthly_config()
    elif view == "site_edit":
        _view_site_edit()
    elif view == "solar_explorer":
        _view_solar_explorer()
    elif view == "report_history":
        _view_report_history()
    else:
        _view_portfolio()
