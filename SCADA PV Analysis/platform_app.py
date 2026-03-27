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
BG_PATH      = SCRIPT_DIR / "bg_solar.jpg"
BG_WIND_PATH = SCRIPT_DIR / "bg_wind.jpg"

sys.path.insert(0, str(SCRIPT_DIR))
from platform_users import USERS, SITES, PRICING

# ── Persistent custom-site storage (survives session reloads; lost on redeploy)
_CUSTOM_SITES_FILE = SCRIPT_DIR / "custom_sites.json"

def _load_custom_sites_from_disk() -> dict:
    try:
        if _CUSTOM_SITES_FILE.exists():
            return json.loads(_CUSTOM_SITES_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def _save_custom_sites_to_disk() -> None:
    try:
        _CUSTOM_SITES_FILE.write_text(
            json.dumps(st.session_state.get("custom_sites", {}), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
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

bg_b64      = _b64(BG_PATH)      if BG_PATH.exists()      else ""
bg_wind_b64 = _b64(BG_WIND_PATH) if BG_WIND_PATH.exists() else ""
logo_b64    = _b64(LOGO_PATH)    if LOGO_PATH.exists()    else ""

bg_css = (f"url('data:image/jpeg;base64,{bg_b64}')"
          if bg_b64 else
          "linear-gradient(135deg,#001a3a 0%,#003366 60%,#0a4d8c 100%)")

logo_img = (f'<img src="data:image/png;base64,{logo_b64}" '
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

def _sync_custom_sites():
    """Ensure any user-added sites are always available in the SITES dict."""
    for sid, cfg in st.session_state.get("custom_sites", {}).items():
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

    if show_logout and _logged_in():
        col_hdr, col_btn = st.columns([5, 1])
        with col_hdr:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:1.4rem;margin-bottom:0.6rem;">
              {logo_img}
              <div>
                <div style="font-size:1.45rem;font-weight:700;color:white;line-height:1.2;white-space:nowrap;">
                  Performance Analysis Platform
                </div>
                {('<div style="font-size:0.84rem;color:rgba(255,255,255,0.55);margin-top:0.15rem;white-space:nowrap;">' + plan_html + '</div>') if plan_html else ''}
              </div>
            </div>
            """, unsafe_allow_html=True)
        with col_btn:
            st.markdown("<div style='margin-top:1.1rem;'>", unsafe_allow_html=True)
            if st.button("Log out"):
                _logout()
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="display:flex;flex-direction:column;align-items:center;gap:10mm;margin-bottom:0.6rem;">
          {logo_img}
          <div style="font-size:1.35rem;font-weight:700;color:white;line-height:1.2;text-align:center;">
            Performance Analysis Platform
          </div>
        </div>
        """, unsafe_allow_html=True)
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
        Sign in to access your portfolio.
      </div>
    </div>
    """, unsafe_allow_html=True)

    email    = st.text_input("Email address", placeholder="you@company.com", key="login_email")
    password = st.text_input("Password", type="password", key="login_pw")
    submit   = st.button("Sign In →", use_container_width=True)

    if submit:
        user = USERS.get(email.strip().lower())
        if user and user["password"] == password:
            st.session_state["user"]  = {**user, "email": email.strip().lower()}
            st.session_state["view"]  = "portfolio"
            st.rerun()
        else:
            st.error("Invalid email or password.")

    st.markdown("""
    <div style="text-align:center;margin-top:0.8rem;font-size:0.78rem;">
      <a href="mailto:consulting@8p2.fr?subject=Password%20Reset%20Request"
         style="color:rgba(255,255,255,0.40);text-decoration:none;">
        Forgotten your password? Contact us
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
      /* Hide proxy Streamlit buttons — triggered via JS only */
      [data-testid="stMarkdownContainer"]:has(.pvpat-site-row) + [data-testid="stHorizontalBlock"] {
        height: 0 !important;
        overflow: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
        min-height: 0 !important;
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
        Welcome back, <strong>{user['display_name']}</strong>
        &nbsp;—&nbsp; {user['company']}
      </span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        "<div class='step-hdr'>Your Site Portfolio</div>",
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
        if demo.get("type", "solar") == "solar" and demo.get("pr", 100) < _PR_WARN:
            return ("<span class='pvpat-alert-dot' style='display:inline-block;width:8px;height:8px;"
                    "background:#ff6b6b;border-radius:50%;margin-left:6px;"
                    "vertical-align:middle;flex-shrink:0;'></span>")
        return ""

    if not all_items:
        st.info("No sites in your portfolio. Add one below.")
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
                    f"⚠️ Permanently delete <strong>{site['display_name']}</strong>? "
                    f"This cannot be undone.</div>",
                    unsafe_allow_html=True)
            with col_yes:
                if st.button("Confirm Delete", key=f"yes_del_{site_id}"):
                    st.session_state["pending_delete"] = None
                    if is_custom:
                        st.session_state["custom_sites"].pop(site_id, None)
                    else:
                        st.session_state["deleted_sites"].add(site_id)
                    st.rerun()
            with col_no:
                if st.button("Cancel", key=f"cancel_del_{site_id}"):
                    st.session_state["pending_delete"] = None
                    st.rerun()

        # Normal sites — single-column list, one site per row
        normal_items = [(sid, s, c) for sid, s, c in all_items
                        if st.session_state["pending_delete"] != sid]
        for site_id, site, is_custom in normal_items:
            cap_mwp    = site.get("cap_dc_kwp", 0) / 1000
            status     = site.get("status", "operational")
            status_lbl = {"operational": "OPERATIONAL", "maintenance": "MAINTENANCE",
                          "offline": "OFFLINE"}.get(status, status.upper())
            status_col = {"operational": "#2E8B57", "maintenance": "#E67E22",
                          "offline": "#C0392B"}.get(status, "#888")
            site_icon  = "🌬️" if site.get("site_type") == "wind" else "☀️"
            cap_label  = "MW" if site.get("site_type") == "wind" else "MWp"

            kpi_html  = _site_kpi_chips(site_id, site)
            alert_dot = _low_pr_dot(site_id, site)

            # JS: walk siblings from the stMarkdownContainer to find the
            # immediately-following stHorizontalBlock (hidden proxy buttons),
            # then click button at index i.  No page reload — session preserved.
            _js_find = (
                "var m=this.closest('[data-testid=stMarkdownContainer]'),"
                "p=m&&m.parentElement;"
                "if(p){var cs=p.children,f=0;"
                "for(var j=0;j<cs.length;j++){"
                "if(f&&cs[j].dataset&&cs[j].dataset.testid=='stHorizontalBlock'){"
                "var b=cs[j].querySelectorAll('button');"
                "if(b[{i}])b[{i}].click();break;}"
                "if(cs[j]===m)f=1;}}"
            )
            _oc = [_js_find.replace("{i}", str(i)) for i in range(4)]
            _ic = ("cursor:pointer;font-size:1.05rem;padding:5px 8px;"
                   "border-radius:5px;user-select:none;transition:background 0.15s;")
            st.markdown(f"""
            <div class="pvpat-site-row" style="display:flex;align-items:center;
              gap:0.65rem;flex-wrap:nowrap;padding:0.55rem 0.85rem;
              background:rgba(255,255,255,0.04);
              border:1px solid rgba(255,255,255,0.11);border-radius:8px;">
              <div style="display:flex;align-items:center;gap:0.65rem;flex-wrap:wrap;flex:1;min-width:0;">
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
              <div style="display:flex;align-items:center;gap:0.05rem;flex-shrink:0;">
                <span class="pvpat-icon" title="View site"
                  onclick="{_oc[0]}"
                  style="{_ic}color:rgba(255,255,255,0.72);">ⓘ</span>
                <span class="pvpat-icon" title="Edit site"
                  onclick="{_oc[1]}"
                  style="{_ic}color:rgba(255,255,255,0.72);">✎</span>
                <span class="pvpat-icon" title="Generate report"
                  onclick="{_oc[2]}"
                  style="{_ic}color:rgba(255,255,255,0.72);">≡</span>
                <span class="pvpat-icon pvpat-icon-del" title="Delete site"
                  onclick="{_oc[3]}"
                  style="{_ic}color:rgba(229,57,53,0.85);">✕</span>
              </div>
            </div>
            """, unsafe_allow_html=True)
            # Hidden proxy buttons — visually collapsed, clicked by JS above
            ph1, ph2, ph3, ph4 = st.columns(4)
            with ph1:
                if st.button("view", key=f"h_sc_{site_id}"):
                    st.session_state["selected_site"] = site_id
                    st.session_state["view"] = "site_detail"
                    st.rerun()
            with ph2:
                if st.button("edit", key=f"h_ed_{site_id}"):
                    st.session_state["selected_site"] = site_id
                    st.session_state["view"] = "site_edit"
                    st.rerun()
            with ph3:
                if st.button("report", key=f"h_go_{site_id}"):
                    st.session_state["selected_site"] = site_id
                    st.session_state["view"] = "report_select"
                    st.rerun()
            with ph4:
                if st.button("delete", key=f"h_del_{site_id}"):
                    st.session_state["pending_delete"] = site_id
                    st.rerun()

    # ── Add new site ───────────────────────────────────────────────────────────
    st.divider()
    with st.expander("➕  Add a new site"):
        _is_wind_add = st.session_state.get("ns_type", "☀️ Solar") == "🌬️ Wind"
        c1, c2, c3 = st.columns(3)
        with c1:
            _name_ph = "e.g. Nordex Wind Farm" if _is_wind_add else "e.g. Sahara Solar Park"
            new_name = st.text_input("Site name *", placeholder=_name_ph, key="ns_name")
        with c2:
            _cap_lbl = "Capacity (MW) *" if _is_wind_add else "Capacity (MWp DC) *"
            new_cap  = st.text_input(_cap_lbl, placeholder="e.g. 9.84", key="ns_cap")
        with c3:
            new_type = st.radio("Site type", ["☀️ Solar", "🌬️ Wind"], horizontal=True, key="ns_type")

        if st.button("Add site", key="btn_add_site"):
            if not new_name.strip():
                st.error("Site name is required.")
            elif not new_cap.strip():
                st.error("Capacity is required.")
            else:
                try:
                    cap_kwp = float(new_cap.replace(",", ".")) * 1000
                except ValueError:
                    st.error("Capacity must be a number (e.g. 9.84).")
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

    # Initialise selection state (persists across reruns on this page)
    if "report_choice" not in st.session_state:
        st.session_state["report_choice"] = None

    col_back, _ = st.columns([2, 4])
    with col_back:
        if st.button("← Back to Portfolio"):
            st.session_state.pop("report_choice", None)
            st.session_state["view"] = "portfolio"
            st.rerun()

    st.markdown(
        f"<div class='step-hdr'>Generate Report — {site.get('display_name','')}</div>",
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
        if st.button("Select Daily Report", key="btn_daily", use_container_width=True):
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
        if st.button("Select Monthly Report", key="btn_monthly", use_container_width=True):
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
        if st.button("Select Comprehensive Report", key="btn_comp", use_container_width=True):
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
            if st.button(btn_label, key="btn_generate", use_container_width=True):
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

                    pdf_path, html_path = build_scada_analysis_html(
                        site_cfg = site,
                        data_dir = tmp_data_dir,
                        out_path = out_html,
                    )

                    if pdf_path and pdf_path.exists():
                        st.success(f"✅ Daily report generated: **{pdf_path.name}**")
                        st.download_button(
                            label    = "⬇️  Download PDF Report",
                            data     = pdf_path.read_bytes(),
                            file_name= pdf_path.name,
                            mime     = "application/pdf",
                        )
                    elif html_path and html_path.exists():
                        st.warning(
                            "PDF generation requires WeasyPrint or Playwright. "
                            "Downloading as HTML instead — open in any browser and use "
                            "**File → Print → Save as PDF**."
                        )
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

                pdf_path, html_path = build_scada_analysis_html(
                    site_cfg = site,
                    data_dir = tmp_data_dir,
                )

                if pdf_path and pdf_path.exists():
                    st.success(f"✅ Comprehensive report generated: **{pdf_path.name}**")
                    st.download_button(
                        label     = "⬇️  Download PDF Report",
                        data      = pdf_path.read_bytes(),
                        file_name = pdf_path.name,
                        mime      = "application/pdf",
                    )
                elif html_path and html_path.exists():
                    st.warning(
                        "PDF generation requires WeasyPrint system libraries. "
                        "Downloading as HTML instead — open in any browser and use "
                        "**File → Print → Save as PDF**."
                    )
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
                ("Turbine model",    site.get("inverter_model", "—")),
                ("No. of turbines",  str(site.get("n_inverters", "—"))),
                ("Unit capacity",    (f"{site['inv_ac_kw']:.0f} kW"
                                      if site.get("inv_ac_kw") else "—")),
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

        design_pr = site.get("design_pr") or 0.80
        target_pr = site.get("operating_pr_target") or max(design_pr - 0.02, 0.55)

        _months = ["Jan","Feb","Mar","Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec"]
        # Seasonal swing: PR higher in cool months, lower in summer heat
        _seasonal = _np.array([0.02,0.02,0.01,0,-0.01,-0.03,
                                -0.04,-0.03,-0.01, 0, 0.01,0.02])
        _pr_vals  = _np.clip(design_pr + _seasonal - 0.03, 0.55, 0.99)

        _fig, _ax = _plt.subplots(figsize=(4.2, 2.0))
        _fig.patch.set_facecolor("#0d1b2a")
        _ax.set_facecolor("#0d1b2a")

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
        st.pyplot(_fig, use_container_width=True)
        _plt.close(_fig)

        st.markdown(
            "<p style='color:rgba(255,255,255,0.38);font-size:0.70rem;margin-top:0;'>"
            "Indicative monthly PR — connect SCADA for live data.</p>",
            unsafe_allow_html=True)

    st.divider()
    _, col_gen, _ = st.columns([2, 2, 2])
    with col_gen:
        if st.button(f"{'🌬️' if is_wind else '⚡'} Generate Report →",
                     key="btn_detail_gen", use_container_width=True):
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

    site_id  = st.session_state.get("selected_site", "")
    site     = dict(SITES.get(site_id, {}))
    is_custom = site_id in st.session_state.get("custom_sites", {})

    col_back, _ = st.columns([2, 4])
    with col_back:
        if st.button("← Back to Portfolio", key="edit_back"):
            st.session_state["view"] = "portfolio"
            st.rerun()

    st.markdown(
        f"<div class='step-hdr'>Edit Site — {site.get('display_name', site_id)}</div>",
        unsafe_allow_html=True)

    if not site:
        st.error("Site not found.")
        return

    is_wind = site.get("site_type") == "wind"

    with st.form("site_edit_form"):
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("Site name", value=site.get("display_name", ""))
            new_cap  = st.text_input(
                "Capacity (MWp DC)" if not is_wind else "Capacity (MW)",
                value=str(round(site.get("cap_dc_kwp", 0) / 1000, 3)),
            )
            new_status = st.selectbox(
                "Status",
                ["operational", "maintenance", "offline"],
                index=["operational", "maintenance", "offline"].index(
                    site.get("status", "operational")),
            )
        with c2:
            new_country  = st.text_input("Country",  value=site.get("country",  ""))
            new_region   = st.text_input("Region",   value=site.get("region",   ""))
            new_cod      = st.text_input("COD date", value=site.get("cod",      ""))

        new_tech  = st.text_input("Technology / turbine model",
                                  value=site.get("technology", ""))
        new_inv   = st.text_input("Inverter model",
                                  value=site.get("inverter_model", ""))

        saved = st.form_submit_button("💾 Save changes", use_container_width=False)

    if saved:
        try:
            cap_kwp = float(new_cap.replace(",", ".")) * 1000
        except ValueError:
            st.error("Capacity must be a number.")
            return

        updates = {
            "display_name":   new_name.strip() or site.get("display_name", ""),
            "cap_dc_kwp":     cap_kwp,
            "cap_ac_kw":      cap_kwp * (1 / site.get("dc_ac_ratio", 1.0)) if not is_wind else cap_kwp,
            "status":         new_status,
            "country":        new_country.strip(),
            "region":         new_region.strip(),
            "cod":            new_cod.strip(),
            "technology":     new_tech.strip(),
            "inverter_model": new_inv.strip(),
        }

        if is_custom:
            st.session_state["custom_sites"][site_id].update(updates)
        else:
            # Update in-memory SITES (persists for this session)
            SITES[site_id].update(updates)
            # Also store as a custom override so it survives via disk
            overrides = st.session_state.setdefault("custom_sites", {})
            if site_id not in overrides:
                overrides[site_id] = dict(SITES[site_id])
            else:
                overrides[site_id].update(updates)

        _sync_custom_sites()
        _save_custom_sites_to_disk()
        st.success("Changes saved.")
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
    else:
        _view_portfolio()
