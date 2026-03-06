#!/usr/bin/env python3
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
"""
PVPAT SCADA Analysis Tool
Solar PV Site Performance Analysis Report Generator
=========================================================
Analyses inverter power data, irradiance, and availability
and generates a comprehensive PDF report.

Data location: 00orig/
Output: PVPAT_SCADA_Analysis_Report.pdf
"""

import sys
import os
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch

warnings.filterwarnings('ignore')

# ── Typography: Open Sans ────────────────────────────────────
import matplotlib.font_manager as _fm
import os as _os
# Explicitly register every Open Sans TTF so the font is available
# regardless of whether the cache has been rebuilt.
_mpl_font_dir = _os.path.join(_os.path.dirname(matplotlib.__file__),
                               'mpl-data', 'fonts', 'ttf')
for _f in _os.listdir(_mpl_font_dir):
    if _f.lower().startswith('opensans'):
        _fm.fontManager.addfont(_os.path.join(_mpl_font_dir, _f))

plt.rcParams.update({
    'font.family':      'sans-serif',
    'font.sans-serif':  ['Open Sans', 'Arial', 'Helvetica', 'DejaVu Sans'],
    'axes.titlesize':   9,
    'axes.labelsize':   8,
    'xtick.labelsize':  7,
    'ytick.labelsize':  7,
    'legend.fontsize':  7,
})

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────
DATA_DIR  = Path(r"C:\Users\RichardMUSI\OneDrive - Dolfines\Bureau\PVPAT\00orig")
OUT_DIR   = Path(r"C:\Users\RichardMUSI\OneDrive - Dolfines\Bureau\PVPAT")
REPORT    = "PVPAT_SCADA_Analysis_Report.pdf"

SITE_NAME        = "PVPAT Solar PV Farm"

# ── Known site configuration ──────────────────────────────────
N_MODULES        = 21_402
MODULE_WP        = 460.0                        # Wp per module (First Solar)
MODULE_BRAND     = "First Solar"
N_INVERTERS      = 31
INV_MODEL        = "Sungrow SG250HX"
INV_AC_KW        = 250.0                        # kW per inverter (AC rated)
N_PTR            = 2                            # transformer substations
N_STRINGS_INV    = 12                           # strings per inverter
STRUCT_TYPES     = "3V18 & 3V24 (36 and 46 modules/structure)"

CAP_DC_KWP       = N_MODULES * MODULE_WP / 1000.0   # 9,844.92 kWp DC
CAP_AC_KW        = N_INVERTERS * INV_AC_KW           # 7,750.0  kW  AC
DC_AC_RATIO      = CAP_DC_KWP / CAP_AC_KW            # ~1.27

GHI_STC          = 1000.0   # W/m² at STC
TEMP_STC         = 25.0     # °C
# First Solar CdTe modules have better temp. coeff. than crystalline Si
TEMP_COEFF       = -0.0026  # /°C  (-0.26 %/°C for First Solar Series 6)
DESIGN_PR        = 0.80     # assumed design PR for budget calculation
INTERVAL_MIN     = 10       # minutes between records
INTERVAL_H       = INTERVAL_MIN / 60.0

IRR_THRESHOLD    = 50.0     # W/m² - below this = night-time
POWER_THRESHOLD  = 5.0      # kW   - below this = inverter not running

# Logo (8.2 Advisory | A Dolfines Company) – white version for navy backgrounds
LOGO_PATH        = DATA_DIR / '8p2 advisory white.png'
SOLAR_FARM_IMAGE = DATA_DIR / 'solar_farm_2.jpg'   # Pexels free-to-use photo
_LOGO_IMG = None   # lazy-loaded

def get_logo():
    global _LOGO_IMG
    if _LOGO_IMG is None and LOGO_PATH.exists():
        _LOGO_IMG = plt.imread(str(LOGO_PATH))
    return _LOGO_IMG

# Colour palette  (orange = 8.2 Advisory brand orange)
C = dict(
    primary   = '#1F4E79',
    secondary = '#2E75B6',
    accent    = '#00B0F0',
    green     = '#70AD47',
    red       = '#CC0000',
    orange    = '#F0921E',   # 8.2 Advisory brand orange
    yellow    = '#FFD966',
    budget    = '#4472C4',
    actual    = '#ED7D31',
    light_bg  = '#EBF3FB',
    dark_grey = '#333333',
)


# ─────────────────────────────────────────────────────────────
# SECTION 1 - DATA LOADING
# ─────────────────────────────────────────────────────────────

def load_inverter_data():
    """Load PTR1/PTR2 CSV files (long format: Time_UDT, EQUIP, PAC)."""
    print("  Loading inverter data …")
    frames = []
    for fname in ['PTR1_2023.csv', 'PTR1_2024.csv',
                  'PTR2_2023.csv', 'PTR2_2024.csv']:
        fp = DATA_DIR / fname
        if not fp.exists():
            print(f"    [skip] {fname} not found")
            continue
        try:
            df = pd.read_csv(fp, sep=';', header=0,
                             names=['ts', 'inverter', 'PAC'],
                             dtype={'PAC': str},
                             encoding='utf-8', low_memory=False)
            df['ts']  = pd.to_datetime(df['ts'],
                                        format='%d/%m/%Y %H:%M',
                                        errors='coerce')
            df['PAC'] = pd.to_numeric(df['PAC'], errors='coerce').fillna(0).clip(lower=0)
            df = df.dropna(subset=['ts', 'inverter'])
            frames.append(df)
            print(f"    {fname}: {len(df):,} rows, "
                  f"{df['inverter'].nunique()} inverters")
        except Exception as exc:
            print(f"    WARNING: {fname} -> {exc}")

    if not frames:
        raise FileNotFoundError("No inverter CSV files found in " + str(DATA_DIR))

    data = (pd.concat(frames, ignore_index=True)
              .drop_duplicates(subset=['ts', 'inverter'])
              .sort_values(['inverter', 'ts'])
              .reset_index(drop=True))
    print(f"    Total records: {len(data):,}  |  "
          f"Inverters: {sorted(data['inverter'].unique())}")
    return data


def load_irradiance_data():
    """Load measured irradiance CSV files (10-min)."""
    print("  Loading irradiance data …")
    frames = []
    for fname in ['Irradiance_2023.csv', 'Irradiance_2024.csv']:
        fp = DATA_DIR / fname
        if not fp.exists():
            continue
        try:
            df = pd.read_csv(fp, sep=';', header=0, low_memory=False)
            df.columns = df.columns.str.strip()
            df['ts']        = pd.to_datetime(df['Time_UTC'],
                                              format='%d/%m/%Y %H:%M',
                                              errors='coerce')
            df['GHI']       = pd.to_numeric(df['WSIrradianceA'], errors='coerce')
            df['T_amb']     = pd.to_numeric(df['WSTExt'],        errors='coerce')
            df['T_panel']   = pd.to_numeric(df['WSTPanneau'],    errors='coerce')
            df = df[['ts', 'GHI', 'T_amb', 'T_panel']].dropna(subset=['ts'])
            frames.append(df)
            print(f"    {fname}: {len(df):,} rows")
        except Exception as exc:
            print(f"    WARNING: {fname} -> {exc}")

    if not frames:
        print("    WARNING: No irradiance data found - PR will be approximate")
        return pd.DataFrame(columns=['ts', 'GHI', 'T_amb', 'T_panel'])

    data = (pd.concat(frames, ignore_index=True)
              .drop_duplicates(subset=['ts'])
              .sort_values('ts')
              .reset_index(drop=True))
    data['GHI'] = data['GHI'].clip(lower=0)
    return data


def _parse_sarah_time(t):
    """Parse SARAH timestamp YYYYMMDD:HHMM."""
    try:
        s = str(t)
        return pd.Timestamp(int(s[0:4]), int(s[4:6]), int(s[6:8]),
                            int(s[9:11]), int(s[11:13]))
    except Exception:
        return pd.NaT


def load_sarah_data():
    """Load SARAH_Nord / SARAH_Sud satellite reference files (hourly)."""
    print("  Loading SARAH reference data …")
    sarah = {}
    for name, fname in [('Nord', 'SARAH_Nord.csv'), ('Sud', 'SARAH_Sud.csv')]:
        fp = DATA_DIR / fname
        if not fp.exists():
            continue
        try:
            df = pd.read_csv(fp, sep=';', header=0, low_memory=False)
            df.columns = df.columns.str.strip()
            df['ts']      = df['time'].apply(_parse_sarah_time)
            df['GHI_ref'] = pd.to_numeric(df['G(i)'],   errors='coerce').clip(lower=0)
            df['H_sun']   = pd.to_numeric(df['H_sun'],  errors='coerce').clip(lower=0)
            df['T2m']     = pd.to_numeric(df['T2m'],    errors='coerce')
            df['WS10m']   = pd.to_numeric(df['WS10m'],  errors='coerce')
            df = (df[['ts', 'GHI_ref', 'H_sun', 'T2m', 'WS10m']]
                    .dropna(subset=['ts'])
                    .drop_duplicates(subset=['ts'])
                    .sort_values('ts')
                    .reset_index(drop=True))
            sarah[name] = df
            print(f"    SARAH_{name}: {len(df):,} rows  "
                  f"({df['ts'].dt.year.min()}-{df['ts'].dt.year.max()})")
        except Exception as exc:
            print(f"    WARNING: {fname} -> {exc}")
    return sarah


def load_test_csv():
    """Load Test.csv (daily Nord vs Pyrano comparison)."""
    fp = DATA_DIR / 'Test.csv'
    if not fp.exists():
        return None
    try:
        df = pd.read_csv(fp, sep=';', header=0)
        df.columns = df.columns.str.strip()
        df['date']  = pd.to_datetime(df['day'], format='%d/%m/%Y', errors='coerce')
        df['Nord']  = pd.to_numeric(df['Nord'],   errors='coerce')
        df['Pyrano']= pd.to_numeric(df['Pyrano'], errors='coerce')
        return df.dropna(subset=['date']).set_index('date').sort_index()
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# SECTION 2 - DATA PROCESSING
# ─────────────────────────────────────────────────────────────

def pivot_power(inv_data):
    """Convert long-format inverter data to wide pivot (ts × inverter)."""
    print("  Building power matrix …")
    piv = inv_data.pivot_table(index='ts', columns='inverter',
                                values='PAC', aggfunc='mean')
    # Fill complete time index
    full_idx = pd.date_range(
        start=piv.index.min().normalize(),
        end  =piv.index.max().normalize() + pd.Timedelta(days=1) - pd.Timedelta(minutes=INTERVAL_MIN),
        freq =f'{INTERVAL_MIN}min'
    )
    piv = piv.reindex(full_idx)
    print(f"  Power matrix: {piv.shape[0]:,} timestamps × {piv.shape[1]} inverters")
    return piv


def estimate_site_capacity(piv, irr):
    """Return known site AC capacity (kW) and per-inverter nominal capacity."""
    # Use known nameplate values rather than data-derived estimates
    cap     = CAP_AC_KW               # 31 × 250 kW = 7,750 kW AC
    inv_cap = INV_AC_KW               # 250 kW per inverter
    inv_caps = {col: inv_cap for col in piv.columns}
    print(f"  Site AC capacity (nameplate): {cap:.0f} kW  "
          f"({N_INVERTERS} × {INV_AC_KW:.0f} kW {INV_MODEL})")
    print(f"  Site DC capacity (nameplate): {CAP_DC_KWP:.0f} kWp  "
          f"({N_MODULES:,} × {MODULE_WP:.0f} Wp {MODULE_BRAND})")
    print(f"  DC/AC ratio: {DC_AC_RATIO:.2f}")
    return cap, inv_caps


# ─────────────────────────────────────────────────────────────
# SECTION 3 - ANALYSIS FUNCTIONS
# ─────────────────────────────────────────────────────────────

def analyse_data_availability(piv, irr):
    """Return data-availability metrics."""
    print("  Analysing data availability …")
    per_inv = {}
    for col in piv.columns:
        avail = piv[col].notna().sum() / len(piv) * 100
        per_inv[col] = round(float(avail), 2)
    overall = piv.notna().sum().sum() / piv.size * 100

    if len(irr) > 0:
        full = pd.date_range(
            irr['ts'].min().normalize(),
            irr['ts'].max().normalize() + pd.Timedelta(days=1),
            freq=f'{INTERVAL_MIN}min'
        )
        irr_avail = len(irr) / len(full) * 100
    else:
        irr_avail = 0.0

    # Monthly completeness per inverter
    monthly = {}
    for col in piv.columns:
        monthly[col] = (piv[col].resample('ME')
                               .apply(lambda x: x.notna().sum() / max(len(x),1) * 100))
    return dict(per_inverter=per_inv, overall_power=overall,
                irradiance=irr_avail, monthly=monthly)


def analyse_pr(piv, irr, cap_kw):
    """Performance Ratio at site & inverter level (monthly & annual)."""
    print("  Calculating Performance Ratio (IEC 61724 – DC kWp basis) …")
    site_pwr = piv.sum(axis=1, min_count=1)
    ghi_s    = irr.set_index('ts')['GHI'].reindex(site_pwr.index) if len(irr) else pd.Series(np.nan, index=site_pwr.index)

    df = pd.DataFrame({'pwr': site_pwr, 'GHI': ghi_s})
    df['daytime'] = df['GHI'] > IRR_THRESHOLD
    df['E_act']   = df['pwr'] * INTERVAL_H
    # IEC PR formula: E_ref = (G_POA / G_STC) × P_DC_kWp × dt
    # Using measured GHI as proxy for in-plane irradiance
    df['E_ref']   = (df['GHI'] / GHI_STC) * CAP_DC_KWP * INTERVAL_H

    day = df[df['daytime']].copy()

    monthly = day.resample('ME').agg(
        E_act =('E_act', 'sum'),
        E_ref =('E_ref', 'sum'),
        irrad =('GHI', lambda x: x.sum() * INTERVAL_H / 1000)
    )
    monthly['PR'] = (monthly['E_act'] / monthly['E_ref'] * 100).clip(0, 110)

    annual = day.groupby(day.index.year).agg(
        E_act =('E_act', 'sum'),
        E_ref =('E_ref', 'sum'),
        irrad =('GHI', lambda x: x.sum() * INTERVAL_H / 1000)
    )
    annual['PR'] = (annual['E_act'] / annual['E_ref'] * 100).clip(0, 110)

    # Per-inverter PR – each inverter is allocated 1/31 of DC capacity
    inv_pr = {}
    inv_dc = CAP_DC_KWP / piv.shape[1]   # DC kWp per inverter
    for col in piv.columns:
        sub = pd.DataFrame({'pwr': piv[col], 'GHI': ghi_s})
        sub = sub[sub['GHI'] > IRR_THRESHOLD].dropna()
        if len(sub) == 0:
            inv_pr[col] = 0.0; continue
        e_act = (sub['pwr'] * INTERVAL_H).sum()
        e_ref = ((sub['GHI'] / GHI_STC) * inv_dc * INTERVAL_H).sum()
        inv_pr[col] = float(min(e_act / e_ref * 100, 110)) if e_ref > 0 else 0.0

    return dict(monthly=monthly, annual=annual,
                per_inverter=inv_pr, df=df, df_day=day)


def analyse_availability(piv, irr):
    """Technical availability: fraction of daytime when inverter is running."""
    print("  Calculating availability …")
    ghi_s = irr.set_index('ts')['GHI'].reindex(piv.index) if len(irr) else pd.Series(np.nan, index=piv.index)
    daytime = ghi_s > IRR_THRESHOLD

    per_inv = {}
    for col in piv.columns:
        n_day = int(daytime.sum())
        n_run = int(((piv[col] > POWER_THRESHOLD) & daytime).sum())
        per_inv[col] = round(n_run / n_day * 100, 2) if n_day > 0 else 100.0

    # Site monthly (mean across inverters)
    monthly_frames = []
    for col in piv.columns:
        tmp = pd.DataFrame({'pwr': piv[col], 'day': daytime})
        m = (tmp[tmp['day']]
             .resample('ME')['pwr']
             .apply(lambda x: (x > POWER_THRESHOLD).sum() / max(len(x),1) * 100))
        monthly_frames.append(m)

    site_monthly = pd.concat(monthly_frames, axis=1).mean(axis=1)

    # Identify whole-site outage periods (all inverters down during daytime)
    site_pwr = piv.sum(axis=1, min_count=1)
    all_down = (site_pwr <= POWER_THRESHOLD * piv.shape[1]) & daytime
    n_all_down = int(all_down.sum())
    whole_site_events = int(all_down.astype(int).diff().clip(lower=0).sum())

    # Per-inverter monthly availability (for heatmap on page 10)
    per_inv_monthly = {}
    for col in piv.columns:
        tmp = pd.DataFrame({'pwr': piv[col], 'day': daytime})
        m = (tmp[tmp['day']].resample('ME')['pwr']
             .apply(lambda x: (x > POWER_THRESHOLD).sum() / max(len(x), 1) * 100))
        per_inv_monthly[col] = m
    per_inv_monthly_df = pd.DataFrame(per_inv_monthly)  # index=month-end, cols=inverters

    return dict(per_inverter=per_inv,
                site_monthly=site_monthly,
                per_inverter_monthly=per_inv_monthly_df,
                mean=float(np.mean(list(per_inv.values()))),
                whole_site_outage_intervals=n_all_down,
                whole_site_events=whole_site_events)


def analyse_irradiance_coherence(irr, sarah):
    """Compare measured GHI vs SARAH satellite reference."""
    print("  Checking irradiance coherence …")
    results = {}
    if len(irr) == 0 or not sarah:
        return results

    measured = irr.set_index('ts')['GHI']

    for name, s_df in sarah.items():
        ref = s_df.set_index('ts')['GHI_ref']
        # Upsample SARAH (hourly -> 10-min) by forward-fill
        ref_10 = ref.resample(f'{INTERVAL_MIN}min').ffill()

        common = measured.index.intersection(ref_10.index)
        if len(common) < 200:
            continue

        m = measured.reindex(common).clip(lower=0)
        r = ref_10.reindex(common).clip(lower=0)
        mask = (m > 20) & (r > 20)
        m_d = m[mask]; r_d = r[mask]
        if len(m_d) < 100:
            continue

        # Correlation
        corr = float(np.corrcoef(m_d.values, r_d.values)[0, 1])

        # Ratio stats
        ratio = (m_d / r_d.replace(0, np.nan)).dropna()
        mean_ratio = float(ratio.mean())
        std_ratio  = float(ratio.std())

        # Daily totals
        daily_m = (m.groupby(m.index.date).sum() * INTERVAL_H / 1000)   # kWh/m²
        daily_r = (r.groupby(r.index.date).sum() * INTERVAL_H / 1000)
        common_d = daily_m.index[np.isin(daily_m.index, daily_r.index)]
        dm = daily_m.loc[common_d]; dr = daily_r.loc[common_d]
        daily_diff = ((dm - dr) / dr.replace(0, np.nan) * 100).dropna()

        # Suspect (ratio > 1.3 or < 0.5 during significant irradiance)
        suspect = ((ratio > 1.3) | (ratio < 0.5)) & (r_d > 200)
        suspect_n   = int(suspect.sum())
        suspect_pct = float(suspect_n / len(m_d) * 100)

        # Sensor gap analysis
        gaps = m.isna().resample('D').sum()
        days_with_gaps = int((gaps > 0).sum())

        results[name] = dict(
            correlation     = corr,
            mean_ratio      = mean_ratio,
            std_ratio       = std_ratio,
            daily_diff_mean = float(daily_diff.mean()),
            daily_diff_std  = float(daily_diff.std()),
            suspect_n       = suspect_n,
            suspect_pct     = suspect_pct,
            days_with_gaps  = days_with_gaps,
            daily_df        = pd.DataFrame({'measured': dm, 'reference': dr}),
            scatter_m       = m_d,
            scatter_r       = r_d,
        )
        status = 'OK' if (corr > 0.95 and suspect_pct < 5) else 'REVIEW NEEDED'
        print(f"    SARAH_{name}: R={corr:.3f}  ratio={mean_ratio:.2f}  "
              f"suspect={suspect_pct:.1f}%  -> {status}")
    return results


def analyse_mttf(piv, irr):
    """MTTF per inverter (daytime failure events only)."""
    print("  Calculating MTTF …")
    ghi_s   = irr.set_index('ts')['GHI'].reindex(piv.index) if len(irr) else pd.Series(np.nan, index=piv.index)
    daytime = ghi_s > IRR_THRESHOLD

    results = {}
    # Identify whole-site events to exclude from per-inverter analysis
    site_pwr  = piv.sum(axis=1, min_count=1)
    whole_down = (site_pwr <= POWER_THRESHOLD * piv.shape[1]) & daytime

    for col in piv.columns:
        pwr     = piv[col].fillna(0)
        running = (pwr > POWER_THRESHOLD) & daytime
        # Transition running -> stopped (excluding whole-site events)
        trans   = running.astype(int).diff()
        fail_mask = (trans == -1) & daytime & ~whole_down
        n_fail  = int(fail_mask.sum())
        run_h   = float(running.sum() * INTERVAL_H)
        day_h   = float(daytime.sum() * INTERVAL_H)
        mttf_h  = run_h / n_fail if n_fail > 0 else np.inf
        results[col] = dict(n_failures=n_fail, running_hours=run_h,
                            daytime_hours=day_h,
                            mttf_hours=mttf_h,
                            mttf_days=mttf_h/24 if np.isfinite(mttf_h) else np.inf)
    return results



def _nat(s):
    """Natural sort key: '1.10' > '1.9' (not lexicographic)."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]


def clean_stuck_values(piv):
    """Replace stuck/frozen PAC readings with NaN.

    A stuck value is a non-zero PAC that repeats UNCHANGED for more than
    12 consecutive 10-min intervals (= 2 hours).  This catches SCADA
    communication freezes where the last-known value is held.

    Returns the cleaned pivot DataFrame and a dict describing what was removed.
    """
    print("  Cleaning stuck/frozen inverter readings …")
    cleaned = piv.copy()
    report  = {}
    for col in cleaned.columns:
        s     = cleaned[col].copy()
        # Mask of non-zero, non-NaN values
        nz    = s.notna() & (s > 0)
        # Find runs of identical values
        changed = s.ne(s.shift())   # True when value changes
        run_id  = changed.cumsum()
        # For each run, check length and value
        runs = s.groupby(run_id)
        bad_idx = []
        for rid, grp in runs:
            if len(grp) > 12 and grp.iloc[0] > 0 and grp.notna().all():
                # Stuck: same non-zero value for > 2 hours
                bad_idx.extend(grp.index.tolist())
        if bad_idx:
            n = len(bad_idx)
            report[col] = dict(n_stuck=n,
                               value=float(s.loc[bad_idx[0]]),
                               start=bad_idx[0],
                               end=bad_idx[-1])
            cleaned.loc[bad_idx, col] = np.nan
            print(f"    {col}: {n} intervals set to NaN  "
                  f"(value={report[col]['value']:.1f} kW  "
                  f"{report[col]['start']} → {report[col]['end']})")
    if not report:
        print("    No stuck values detected.")
    return cleaned, report


def analyse_start_stop(piv, irr):
    """Average inverter start/stop time per day — detect voltage threshold issues.

    Returns a DataFrame with columns:
        start_min   : mean start time (minutes since midnight)
        stop_min    : mean stop time (minutes since midnight)
        start_dev   : deviation from fleet mean start (minutes; positive = later)
        stop_dev    : deviation from fleet mean stop (minutes; negative = earlier)
    Only days with daily irradiation > 2 kWh/m² are included.
    """
    print("  Analysing inverter start/stop times …")
    ghi_s = (irr.set_index('ts')['GHI'].reindex(piv.index)
             if len(irr) else pd.Series(np.nan, index=piv.index))
    daily_irr = ghi_s.resample('D').sum() * INTERVAL_H / 1000  # kWh/m²/day
    good_days = daily_irr[daily_irr > 2].index

    starts, stops = {col: [] for col in piv.columns}, {col: [] for col in piv.columns}
    for day in good_days:
        day_slice = piv.loc[str(day.date())]
        if len(day_slice) == 0:
            continue
        for col in piv.columns:
            producing = day_slice[col] > POWER_THRESHOLD
            producing = producing.dropna()
            if producing.sum() < 2:
                continue
            first_idx = producing[producing].index[0]
            last_idx  = producing[producing].index[-1]
            starts[col].append(first_idx.hour * 60 + first_idx.minute)
            stops[col].append(last_idx.hour  * 60 + last_idx.minute)

    rows = {}
    for col in piv.columns:
        s = starts[col]; e = stops[col]
        rows[col] = {
            'start_min': float(np.mean(s)) if s else np.nan,
            'stop_min':  float(np.mean(e)) if e else np.nan,
        }
    df_ss = pd.DataFrame(rows).T
    fleet_start = df_ss['start_min'].mean()
    fleet_stop  = df_ss['stop_min'].mean()
    df_ss['start_dev'] = df_ss['start_min'] - fleet_start   # >0 = starts later
    df_ss['stop_dev']  = df_ss['stop_min']  - fleet_stop    # <0 = stops earlier
    return df_ss


def analyse_inv_specific_yield(piv, irr):
    """Specific yield per inverter per month (kWh/kWp, daytime only).

    Daytime = GHI > 50 W/m².  Down-time intervals (PAC = 0 or NaN
    during daytime) are excluded from the denominator so the metric
    reflects yield when actually producing (soiling / degradation
    signal), not availability.
    """
    print("  Calculating per-inverter monthly specific yield …")
    inv_dc_kwp = CAP_DC_KWP / max(piv.shape[1], 1)  # DC kWp per inverter
    ghi_s = (irr.set_index('ts')['GHI'].reindex(piv.index)
             if len(irr) else pd.Series(np.nan, index=piv.index))
    daytime = ghi_s > IRR_THRESHOLD

    results = {}
    for col in piv.columns:
        # Only daytime + producing intervals (exclude downtime from denominator)
        producing = (piv[col] > POWER_THRESHOLD) & daytime
        e_mwh = (piv[col].where(producing, 0) * INTERVAL_H
                 ).resample('ME').sum() / 1000   # MWh per month
        # Denominator: hours actually producing × kWp → kWh ref per kWp
        prod_h = producing.resample('ME').sum() * INTERVAL_H   # hours producing
        # Specific yield = E_produced / (DC_kWp × producing_fraction)
        # = kWh / kWp  (normalised so we see performance, not availability)
        sy = (e_mwh * 1000 / inv_dc_kwp)   # kWh/kWp per month
        results[col] = sy
    return pd.DataFrame(results)


def build_waterfall(pr_res, irr, sarah, avail_res, cap_kw):
    """Calculate waterfall energy components (MWh)."""
    print("  Building waterfall components …")
    day = pr_res['df_day']

    # ── Budget (theoretical from SARAH reference) ──────────────
    sarah_key = 'Sud' if 'Sud' in sarah else ('Nord' if 'Nord' in sarah else None)
    if sarah_key:
        s_df  = sarah[sarah_key]
        ref   = s_df.set_index('ts')['GHI_ref']
        ref10 = ref.resample(f'{INTERVAL_MIN}min').ffill().reindex(day.index)
        # For periods without SARAH coverage (e.g. 2024), fall back to measured GHI
        # so weather correction = 0 rather than making the budget = 0
        budget_irr = ref10.fillna(day['GHI'])
    else:
        budget_irr = day['GHI']

    # Budget uses DC kWp (IEC standard): E_budget = H_ref × P_DC × PR_design
    budget_E  = float((budget_irr / GHI_STC * CAP_DC_KWP * INTERVAL_H * DESIGN_PR).sum()) / 1000  # MWh

    # ── Weather correction ──────────────────────────────────────
    if sarah_key:
        meas10 = day['GHI']
        diff10 = meas10 - budget_irr.reindex(meas10.index).fillna(meas10)
        weather_corr_E = float((diff10 / GHI_STC * CAP_DC_KWP * INTERVAL_H * DESIGN_PR).sum()) / 1000
    else:
        weather_corr_E = 0.0

    weather_corrected_E = budget_E + weather_corr_E

    # ── Actual energy ───────────────────────────────────────────
    actual_E = float(day['E_act'].sum()) / 1000  # MWh

    # ── Availability loss ───────────────────────────────────────
    mean_avail   = avail_res['mean'] / 100.0
    avail_loss_E = weather_corrected_E * (1.0 - mean_avail)

    # ── Technical / residual loss ───────────────────────────────
    total_loss_E   = weather_corrected_E - actual_E
    technical_loss = max(0.0, total_loss_E - avail_loss_E)

    # ── Residual (over/under after losses) ──────────────────────
    # If actual > weather_corrected - avail_loss - technical then site over-performs
    expected_after_losses = weather_corrected_E - avail_loss_E - technical_loss
    residual_E = actual_E - expected_after_losses

    return dict(
        budget         = budget_E,
        weather_corr   = weather_corr_E,
        weather_corrected = weather_corrected_E,
        avail_loss     = -avail_loss_E,
        technical_loss = -technical_loss,
        residual       = residual_E,
        actual         = actual_E,
    )


def generate_punchlist(avail_res, pr_res, irr_coh, mttf_res, data_avail, cap_kw, wf=None,
                       start_stop_df=None):
    """Build prioritised action punchlist, sorted by estimated MWh loss."""
    items = []
    # Reference energy for loss estimates
    wc_mwh   = wf['weather_corrected'] if wf else 0.0   # weather-corrected budget MWh
    n_inv    = max(len(avail_res['per_inverter']), 1)
    inv_share = 1.0 / n_inv
    pr_vals_all = [v for v in pr_res['per_inverter'].values() if v > 0]
    fleet_pr_frac = (np.mean(pr_vals_all) / 100) if pr_vals_all else 0.80
    e_ref_total = pr_res['annual']['E_ref'].sum() / 1000 if len(pr_res['annual']) > 0 else 0  # MWh

    def add(priority, cat, issue, action, mwh_loss=0.0):
        items.append(dict(priority=priority, category=cat,
                          issue=issue, action=action,
                          mwh_loss=round(mwh_loss, 1)))

    # ── Data quality ─────────────────────────────────────────────
    if data_avail['overall_power'] < 95:
        add('HIGH', 'Data Quality',
            f"Power data availability {data_avail['overall_power']:.1f}% < 95% target",
            "Investigate SCADA logger connectivity; check data export configuration")
    if data_avail['irradiance'] < 95:
        add('MEDIUM', 'Data Quality',
            f"Irradiance data availability {data_avail['irradiance']:.1f}% < 95%",
            "Check pyranometer datalogger and communication link")
    # Per-inverter data completeness
    _n_inv_da = sum(1 for v in data_avail['per_inverter'].values() if v < 95)
    if _n_inv_da > 3:
        _wda = sorted(data_avail['per_inverter'].items(), key=lambda x: x[1])[:4]
        add('HIGH', 'Data Quality',
            f'{_n_inv_da} inverters below 95% data completeness — likely RS485/Modbus faults. '
            'Worst: ' + ', '.join(f'{i}({v:.0f}%)' for i, v in _wda),
            'Inspect RS485 chain for listed inverters; check SCADA polling config and datalogger event log.')
    elif _n_inv_da > 0:
        _wda = sorted(data_avail['per_inverter'].items(), key=lambda x: x[1])[:3]
        add('MEDIUM', 'Data Quality',
            f'{_n_inv_da} inverter(s) below 95% data completeness: ' + ', '.join(f'{i}({v:.0f}%)' for i, v in _wda),
            'Check RS485 connectivity; inspect SCADA polling configuration.')

    # ── Irradiance coherence ─────────────────────────────────────
    for name, coh in irr_coh.items():
        if coh['correlation'] < 0.90:
            add('HIGH', 'Irradiance Sensor',
                f"Measured vs SARAH_{name} correlation R={coh['correlation']:.2f} (target >0.95)",
                "Inspect pyranometer: clean dome, verify alignment, check calibration certificate")
        elif coh['correlation'] < 0.95:
            add('MEDIUM', 'Irradiance Sensor',
                f"Measured vs SARAH_{name} correlation R={coh['correlation']:.2f} (target >0.95)",
                "Schedule pyranometer verification; cross-check with portable reference sensor")
        if coh['suspect_pct'] > 10:
            add('HIGH', 'Irradiance Sensor',
                f"{coh['suspect_pct']:.1f}% of daytime readings are anomalous vs SARAH_{name}",
                "Likely sensor soiling, shading or calibration drift; clean and recalibrate")
        elif coh['suspect_pct'] > 5:
            add('MEDIUM', 'Irradiance Sensor',
                f"{coh['suspect_pct']:.1f}% suspect irradiance readings vs SARAH_{name}",
                "Cross-check sensor readings; inspect for partial shading of pyranometer")
        if abs(coh['mean_ratio'] - 1.0) > 0.10:
            add('MEDIUM', 'Irradiance Sensor',
                f"Mean measured/reference ratio = {coh['mean_ratio']:.2f} (target ~1.0)",
                "Recalibrate pyranometer; verify mounting tilt/azimuth matches modelled value")

    # ── Site-level performance ────────────────────────────────────
    annual = pr_res['annual']
    for yr, row in annual.iterrows():
        pr_loss_mwh = max(0, (75 - row['PR']) / 100 * (row['E_ref'] / 1000)) if row['PR'] < 75 else 0
        if row['PR'] < 65:
            add('HIGH', 'Performance',
                f"Year {yr} site PR = {row['PR']:.1f}% (below 65% alert threshold)",
                "Deep-dive loss analysis; audit inverters, strings, and soiling levels",
                mwh_loss=pr_loss_mwh)
        elif row['PR'] < 75:
            add('MEDIUM', 'Performance',
                f"Year {yr} site PR = {row['PR']:.1f}% (below 75% target)",
                "Review inverter efficiency curves; check for clipping, temperature, soiling",
                mwh_loss=pr_loss_mwh)
    # Monthly PR alerts
    _monthly_pr = pr_res.get('monthly')
    if _monthly_pr is not None and len(_monthly_pr) > 0:
        _n_red_m = int((_monthly_pr['PR'] < 65).sum())
        _n_yel_m = int(((_monthly_pr['PR'] >= 65) & (_monthly_pr['PR'] < 75)).sum())
        if _n_red_m > 0:
            _bad_m = _monthly_pr[_monthly_pr['PR'] < 65].index
            _ms = ', '.join(m.strftime('%b-%y') for m in _bad_m[:4])
            add('HIGH', 'Performance',
                f'{_n_red_m} month(s) below 65% PR alert threshold: {_ms}',
                'Cross-reference with availability and irradiance logs; identify downtime vs quality loss driver.')
        elif _n_yel_m > 0:
            add('MEDIUM', 'Performance',
                f'{_n_yel_m} month(s) in the 65–75% PR danger zone — borderline performance',
                'Inspect O&M logs for those months; check soiling and curtailment events.')

    # ── Inverter PR outliers  (grouped) ──────────────────────────
    pr_vals = [v for v in pr_res['per_inverter'].values() if v > 0]
    e_ref_per_inv = e_ref_total / n_inv
    if pr_vals:
        fleet_mean = np.mean(pr_vals)
        fleet_std  = np.std(pr_vals)
        high_pr = sorted([(i, p) for i, p in pr_res['per_inverter'].items()
                          if p > 0 and p < fleet_mean - 2 * fleet_std],
                         key=lambda x: x[1])
        med_pr  = sorted([(i, p) for i, p in pr_res['per_inverter'].items()
                          if p > 0 and fleet_mean - 2*fleet_std <= p < fleet_mean - fleet_std],
                         key=lambda x: x[1])
        if high_pr:
            s = ', '.join(f'{i}({p:.0f}%)' for i, p in high_pr[:6])
            if len(high_pr) > 6: s += f' +{len(high_pr)-6} more'
            # Loss = sum of (fleet_mean - inv_pr)/100 × E_ref_per_inv for each outlier
            loss = sum((fleet_mean - p) / 100 * e_ref_per_inv for _, p in high_pr)
            add('HIGH', 'Inverter PR',
                f'{len(high_pr)} inv. >2σ below fleet PR ({fleet_mean:.1f}%): {s}',
                'Inspect string fuses, IV curves, soiling & error logs for listed inverters',
                mwh_loss=loss)
        if med_pr:
            s = ', '.join(f'{i}({p:.0f}%)' for i, p in med_pr[:6])
            if len(med_pr) > 6: s += f' +{len(med_pr)-6} more'
            loss = sum((fleet_mean - p) / 100 * e_ref_per_inv for _, p in med_pr)
            add('MEDIUM', 'Inverter PR',
                f'{len(med_pr)} inv. 1-2σ below fleet PR ({fleet_mean:.1f}%): {s}',
                'Monitor; schedule string-level inspection for listed inverters',
                mwh_loss=loss)

    # ── Availability  (grouped) ───────────────────────────────────
    high_av = sorted([(i, v) for i, v in avail_res['per_inverter'].items() if v < 90],
                     key=lambda x: x[1])
    med_av  = sorted([(i, v) for i, v in avail_res['per_inverter'].items()
                      if 90 <= v < 95], key=lambda x: x[1])
    if high_av:
        s = ', '.join(f'{i}({v:.0f}%)' for i, v in high_av[:6])
        if len(high_av) > 6: s += f' +{len(high_av)-6} more'
        loss = sum((1 - v/100) * inv_share * wc_mwh for _, v in high_av)
        add('HIGH', 'Availability',
            f'{len(high_av)} inv. <90% avail.: {s}',
            'Review SCADA alarms; schedule O&M visit; check protection settings',
            mwh_loss=loss)
    if med_av:
        s = ', '.join(f'{i}({v:.0f}%)' for i, v in med_av[:6])
        if len(med_av) > 6: s += f' +{len(med_av)-6} more'
        loss = sum((1 - v/100) * inv_share * wc_mwh for _, v in med_av)
        add('MEDIUM', 'Availability',
            f'{len(med_av)} inv. 90-95% avail.: {s}',
            'Obtain fault logs; verify trip thresholds and re-connection delays',
            mwh_loss=loss)

    if avail_res['whole_site_events'] > 5:
        site_loss = wc_mwh * (1 - avail_res['mean'] / 100)
        add('HIGH', 'Grid / Site',
            f"{avail_res['whole_site_events']} periods where ALL inverters were simultaneously offline (grid-level events)",
            "Obtain MV protection relay logs and correlate with DSO records; consider power quality study at connection point",
            mwh_loss=site_loss)

    # ── MTTF / reliability  (grouped) ────────────────────────────
    high_mttf = sorted([(i, m) for i, m in mttf_res.items() if m['n_failures'] > 100],
                       key=lambda x: x[1]['n_failures'], reverse=True)
    med_mttf  = sorted([(i, m) for i, m in mttf_res.items()
                        if 30 < m['n_failures'] <= 100],
                       key=lambda x: x[1]['n_failures'], reverse=True)
    if high_mttf:
        s = ', '.join(f'{i}({m["n_failures"]}f)' for i, m in high_mttf[:6])
        if len(high_mttf) > 6: s += f' +{len(high_mttf)-6} more'
        loss = sum((1 - min(m['running_hours'], m['daytime_hours']) /
                    max(m['daytime_hours'], 1)) * inv_share * wc_mwh
                   for _, m in high_mttf)
        add('HIGH', 'Reliability',
            f'{len(high_mttf)} inv. >100 trip events: {s}',
            'Contact inverter OEM; check AC protection, grid quality, firmware version',
            mwh_loss=loss)
    if med_mttf:
        s = ', '.join(f'{i}({m["n_failures"]}f)' for i, m in med_mttf[:6])
        if len(med_mttf) > 6: s += f' +{len(med_mttf)-6} more'
        loss = sum((1 - min(m['running_hours'], m['daytime_hours']) /
                    max(m['daytime_hours'], 1)) * inv_share * wc_mwh
                   for _, m in med_mttf)
        add('MEDIUM', 'Reliability',
            f'{len(med_mttf)} inv. 30-100 trip events: {s}',
            'Review trip logs; check earthing, capacitor health, thermal behaviour',
            mwh_loss=loss)

    # ── Inverter start / stop timing anomalies ────────────────────
    if start_stop_df is not None and len(start_stop_df) > 0:
        SS_THRESHOLD    = 5.0    # minutes — flag persistent late starters for voltage-threshold investigation
        SS_RAMP_FACTOR  = 0.10   # fraction of rated capacity during morning ramp-up
        # Good production days: ~250 clear days/year × number of years in dataset
        n_good_days_est = max(len(pr_res['annual']), 1) * 250
        inv_kw_each     = cap_kw / max(n_inv, 1)        # kW per inverter

        late = sorted(
            [(inv, float(row['start_dev'])) for inv, row in start_stop_df.iterrows()
             if row['start_dev'] > SS_THRESHOLD],
            key=lambda x: -x[1])
        if late:
            # Per-inverter loss: delay × rated_kW × ramp_fraction / 60 × n_days
            total_mwh = sum(
                delay * inv_kw_each * SS_RAMP_FACTOR / 60 * n_good_days_est / 1000
                for _, delay in late)
            inv_str = ', '.join(f'{inv} ({delay:.0f} min late)' for inv, delay in late[:6])
            if len(late) > 6:
                inv_str += f' +{len(late)-6} more'
            add('MEDIUM', 'Start/Stop',
                f'{len(late)} inverter(s) consistently start >{SS_THRESHOLD:.0f} min later than fleet mean: {inv_str}. '
                f'Systematic delay indicates Vdc_min startup voltage set too high. '
                f'Estimated production loss ≈ {total_mwh:.1f} MWh '
                f'(€{total_mwh * 100:.0f} at €100/MWh) over the analysis period.',
                'Lower the minimum DC startup voltage threshold (Vdc_min) on the flagged Sungrow SG250HX '
                'inverters to match the fleet mean morning startup profile. '
                'Requires a qualified electrical engineer — document before/after start times to confirm fix.',
                mwh_loss=total_mwh)

        early = sorted(
            [(inv, float(row['stop_dev'])) for inv, row in start_stop_df.iterrows()
             if row['stop_dev'] < -SS_THRESHOLD],
            key=lambda x: x[1])
        if early:
            total_mwh_e = sum(
                abs(dev) * inv_kw_each * SS_RAMP_FACTOR / 60 * n_good_days_est / 1000
                for _, dev in early)
            inv_str_e = ', '.join(f'{inv} ({abs(dev):.0f} min early)' for inv, dev in early[:6])
            if len(early) > 6:
                inv_str_e += f' +{len(early)-6} more'
            add('MEDIUM', 'Start/Stop',
                f'{len(early)} inverter(s) stop >{SS_THRESHOLD:.0f} min earlier than fleet mean: {inv_str_e}. '
                f'Estimated loss ≈ {total_mwh_e:.1f} MWh '
                f'(€{total_mwh_e * 100:.0f}) over the analysis period.',
                'Check Vac_min and under-voltage trip thresholds — evening grid voltage sag may be '
                'causing premature disconnect. Review O&M records for grid curtailment events.',
                mwh_loss=total_mwh_e)

    # Sort by MWh loss descending (highest production impact first)
    items.sort(key=lambda x: x.get('mwh_loss', 0), reverse=True)
    print(f"  Punchlist: {len(items)} items  "
          f"({sum(1 for i in items if i['priority']=='HIGH')} HIGH, "
          f"{sum(1 for i in items if i['priority']=='MEDIUM')} MEDIUM)")
    return items


# ─────────────────────────────────────────────────────────────
# SECTION 4 - REPORT HELPERS
# ─────────────────────────────────────────────────────────────

PAGE_W, PAGE_H = 8.27, 11.69   # A4 portrait inches

# ── Header / footer draw once on the figure canvas (no extra axes) ──
def _header_bar(fig, title, subtitle=''):
    """Navy band + orange accent at top; logo top-right; title left-aligned."""
    fig.patch.set_facecolor('white')
    # Navy band — extended 2 mm downward so subtitle has breathing room
    # (navy bottom: 0.943, orange bottom: 0.936 – both 2 mm lower than before)
    fig.add_artist(FancyBboxPatch((0, 0.943), 1, 0.057,
                                   boxstyle='square,pad=0',
                                   facecolor=C['primary'], edgecolor='none',
                                   transform=fig.transFigure, zorder=10))
    # Orange accent line immediately below navy
    fig.add_artist(FancyBboxPatch((0, 0.938), 1, 0.005,
                                   boxstyle='square,pad=0',
                                   facecolor=C['orange'], edgecolor='none',
                                   transform=fig.transFigure, zorder=10))
    # Title – LEFT aligned
    fig.text(0.03, 0.973, title, ha='left', va='center',
             fontsize=11, fontweight='bold', color='white',
             transform=fig.transFigure, zorder=11)
    if subtitle:
        fig.text(0.03, 0.952, subtitle, ha='left', va='center',
                 fontsize=7.5, color='#B8D4EA',
                 transform=fig.transFigure, zorder=11)
    # Logo – right-aligned, equal margin (0.008) from top and right edges.
    # Band: y=0.943–1.0 (h=0.057).  Desired logo height = 0.041 fig-frac.
    # Width is computed from the image's pixel aspect ratio so aspect='equal'
    # produces zero letter-boxing.  zorder=20 ensures it sits above all patches.
    logo = get_logo()
    if logo is not None:
        h_px, w_px = logo.shape[:2]
        disp_h = 0.031          # logo height in figure fraction (75 % of 0.041)
        # Convert pixel aspect to figure-fraction aspect (A4 is not square)
        disp_w = (w_px / h_px) * disp_h * (PAGE_H / PAGE_W)
        disp_w = min(disp_w, 0.30)   # hard cap so it never overlaps the title
        ax_left = 0.997 - disp_w     # right edge flush (~0.003 margin)
        ax_lg = fig.add_axes([ax_left, 0.957, disp_w, disp_h])
        ax_lg.set_zorder(20)          # must be > FancyBboxPatch zorder (10)
        ax_lg.imshow(logo, aspect='equal')
        ax_lg.set_facecolor(C['primary'])
        ax_lg.axis('off')


def _footer(fig, page_num, total=''):
    """Light-grey band at bottom; orange top border; ≥5 mm gap orange-to-text.
    Orange line sits 5 mm lower than original (y ≈ 0.049) to free up page space.
    """
    # Grey band – 0.052 figure fraction ≈ 15 mm on A4 (reduced from 20 mm)
    fig.add_artist(FancyBboxPatch((0, 0), 1, 0.052,
                                   boxstyle='square,pad=0',
                                   facecolor='#F2F2F2', edgecolor='none',
                                   transform=fig.transFigure, zorder=10))
    # Orange accent at top of grey band (y=0.049-0.052, ~5 mm lower than before)
    fig.add_artist(FancyBboxPatch((0, 0.049), 1, 0.003,
                                   boxstyle='square,pad=0',
                                   facecolor=C['orange'], edgecolor='none',
                                   transform=fig.transFigure, zorder=10))
    # Footer text sits in the lower half of the band, ~12 mm below orange line
    pg = f'Page {page_num}' + (f' / {total}' if total else '')
    fig.text(0.02, 0.025,
             f'{SITE_NAME}  |  SCADA Performance Analysis  |  '
             f'{datetime.now().strftime("%d %b %Y")}',
             ha='left', va='center', fontsize=6.5, color='#555555',
             transform=fig.transFigure, zorder=11)
    fig.text(0.98, 0.025, pg, ha='right', va='center',
             fontsize=6.5, color='#555555',
             transform=fig.transFigure, zorder=11)


def _kpi_box(ax, value, label, target='', ok=True):
    """Clean text-style KPI card: coloured top rule + large value + label."""
    ax.axis('off')
    # Use brand orange for warnings (avoids harsh red), green for on-target
    status_color = '#1A7A3C' if ok else C['orange']
    marker       = '✓' if ok else '▲'

    # Very subtle card background
    ax.add_patch(FancyBboxPatch((0.04, 0.04), 0.92, 0.92,
                                boxstyle='square,pad=0',
                                facecolor='#F6F8FA', edgecolor='#E4E8EE',
                                linewidth=0.6,
                                transform=ax.transAxes, clip_on=False))
    # Coloured top rule (status indicator)
    ax.plot([0.04, 0.96], [0.96, 0.96], color=status_color, linewidth=3.5,
            transform=ax.transAxes, clip_on=False, solid_capstyle='butt')

    # Large bold value in primary navy
    ax.text(0.50, 0.64, value, ha='center', va='center', fontsize=18,
            fontweight='bold', color=C['primary'], transform=ax.transAxes)
    # Label
    ax.text(0.50, 0.38, label, ha='center', va='center', fontsize=7.5,
            color='#555555', transform=ax.transAxes)
    # Status line
    if target and target != '--':
        ax.text(0.50, 0.17, f'{marker}  {target}', ha='center', va='center',
                fontsize=7, color=status_color, fontweight='bold',
                transform=ax.transAxes)


def _style_table(table, header_color=None):
    header_color = header_color or C['primary']
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.6)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor('#CCCCCC')
        if r == 0:
            cell.set_facecolor(header_color)
            cell.get_text().set_color('white')
            cell.get_text().set_fontweight('bold')
        elif r % 2 == 0:
            cell.set_facecolor('#F5F5F5')


def _page_insight(fig, rows, gs=None, has_rotated_labels=False, caption=None):
    """Mini punchlist table at bottom of page — three columns: LEVEL | KEY FINDING | RECOMMENDED ACTION.

    Parameters
    ----------
    fig  : matplotlib.figure.Figure
    rows : list — each element is either:
             • a dict  {'sev': 'HIGH'|'MEDIUM'|'OK'|'INFO',
                        'finding': str,
                        'action':  str (optional)}
             • a plain str  (backward-compat: treated as INFO finding, no action)
    gs   : GridSpec | None — updated so charts don't overlap the table.
    has_rotated_labels : bool — adds extra clearance above the table.
    caption : str | None — brief explanatory text rendered between charts and insight table.
    """
    if not rows:
        return
    import textwrap as _tw

    # ── Normalise input ───────────────────────────────────────────
    norm = []
    for r in rows:
        if isinstance(r, str):
            norm.append({'sev': 'INFO', 'finding': r, 'action': ''})
        else:
            norm.append({
                'sev':     str(r.get('sev', 'INFO')).upper(),
                'finding': r.get('finding', ''),
                'action':  r.get('action', ''),
            })
    norm = norm[:5]

    # ── Column geometry (figure fractions) ───────────────────────
    BOX_X  = 0.030;  BOX_W  = 0.940
    SEV_W  = 0.082   # severity badge column
    ACT_W  = 0.285   # action column
    FIND_W = BOX_W - SEV_W - ACT_W   # ≈ 0.573

    SEV_TX  = BOX_X + 0.005
    FIND_TX = BOX_X + SEV_W + 0.008
    ACT_TX  = BOX_X + SEV_W + FIND_W + 0.008
    DIV1_X  = BOX_X + SEV_W + 0.001
    DIV2_X  = BOX_X + SEV_W + FIND_W + 0.003

    WRAP_F = 100;  WRAP_A = 37
    LINE_PT = 6.8
    LINE_H  = LINE_PT / (PAGE_H * 72) * 1.38   # ≈ 0.01125 fig-frac per line
    HDR_H   = 0.0168
    ROW_PAD = 0.0055
    BOX_BOT = 0.058

    SEV_CFG = {
        'HIGH':   ('● HIGH', '#B71C1C', '#FDECEA'),
        'MEDIUM': ('● MED',  '#BF6000', '#FFF3E0'),
        'OK':     ('✔  OK',  '#1A6B35', '#E8F5EC'),
        'INFO':   ('ℹ  INFO','#1F4E79', '#EEF3FA'),
    }

    def _rh(r):
        fl = max(len(_tw.wrap(r['finding'], width=WRAP_F) or ['']), 1)
        al = max(len(_tw.wrap(r['action'],  width=WRAP_A) or ['']), 1) if r.get('action') else 0
        return max(fl, al, 1) * LINE_H + ROW_PAD

    total_row_h = sum(_rh(r) for r in norm)
    box_h   = max(HDR_H + total_row_h + 0.010, 0.055)
    box_top = BOX_BOT + box_h

    # ── Caption height (text rendered above insight box) ──────────
    CAP_LINE_H = 6.0 / (PAGE_H * 72) * 1.38   # figure-fraction per line at 6pt
    _CAP_WIDTH = 200   # characters per line
    if caption:
        _raw_lines = _tw.wrap(caption, width=_CAP_WIDTH)
        _justified = []
        for _li, _ln in enumerate(_raw_lines):
            if _li < len(_raw_lines) - 1:   # justify all but last line
                _words = _ln.split()
                if len(_words) > 1:
                    _need = _CAP_WIDTH - sum(len(_w) for _w in _words)
                    _gaps = len(_words) - 1
                    _base, _rem = divmod(_need, _gaps)
                    _jl = _words[0]
                    for _j, _w in enumerate(_words[1:]):
                        _jl += ' ' * (_base + (1 if _j < _rem else 0)) + _w
                    _justified.append(_jl)
                else:
                    _justified.append(_ln)
            else:
                _justified.append(_ln)   # last line: left-aligned
        _cap_wrapped = '\n'.join(_justified)
        _cap_lines   = len(_raw_lines)
        cap_h = _cap_lines * CAP_LINE_H * 1.45 + 0.012
    else:
        _cap_wrapped = ''
        cap_h = 0.0

    # ── Update GridSpec ───────────────────────────────────────────
    if gs is not None:
        label_extra = 0.042 if has_rotated_labels else 0.0
        gs.update(bottom=box_top + cap_h + 0.015 + label_extra)

    # ── Caption text above insight box ───────────────────────────
    if caption:
        fig.text(BOX_X, box_top + 0.004, _cap_wrapped,
                 fontsize=6.0, color='#444444', style='italic',
                 va='bottom', transform=fig.transFigure,
                 linespacing=1.35)

    # ── Outer border ─────────────────────────────────────────────
    fig.add_artist(FancyBboxPatch(
        (BOX_X, BOX_BOT), BOX_W, box_h,
        boxstyle='square,pad=0',
        facecolor='white', edgecolor='#B0C4DE', linewidth=0.8,
        transform=fig.transFigure, zorder=5))
    # Orange left accent strip
    fig.add_artist(FancyBboxPatch(
        (BOX_X, BOX_BOT), 0.006, box_h,
        boxstyle='square,pad=0',
        facecolor=C['orange'], edgecolor='none',
        transform=fig.transFigure, zorder=6))

    # ── Header row (navy) ─────────────────────────────────────────
    hdr_top = box_top - 0.003
    fig.add_artist(FancyBboxPatch(
        (BOX_X + 0.006, hdr_top - HDR_H), BOX_W - 0.006, HDR_H,
        boxstyle='square,pad=0',
        facecolor=C['primary'], edgecolor='none',
        transform=fig.transFigure, zorder=6))
    hdr_mid = hdr_top - HDR_H / 2
    for tx, lbl in [(SEV_TX + 0.008, 'LEVEL'),
                    (FIND_TX,         'KEY FINDING'),
                    (ACT_TX,          'RECOMMENDED ACTION')]:
        fig.text(tx, hdr_mid, lbl,
                 ha='left', va='center', fontsize=6.5, fontweight='bold',
                 color='white', transform=fig.transFigure, zorder=7)
    for dx in [DIV1_X, DIV2_X]:
        fig.add_artist(FancyBboxPatch(
            (dx, hdr_top - HDR_H), 0.0009, HDR_H,
            boxstyle='square,pad=0', facecolor='#4472A0', edgecolor='none',
            transform=fig.transFigure, zorder=7))

    # ── Data rows ─────────────────────────────────────────────────
    y = hdr_top - HDR_H
    for idx, r in enumerate(norm):
        rh  = _rh(r)
        sev = r['sev'] if r['sev'] in SEV_CFG else 'INFO'
        sev_label, sev_color, sev_bg = SEV_CFG[sev]
        row_bg = '#F8FAFD' if idx % 2 == 0 else '#FFFFFF'

        # Row background
        fig.add_artist(FancyBboxPatch(
            (BOX_X + 0.006, y - rh), BOX_W - 0.006, rh,
            boxstyle='square,pad=0',
            facecolor=row_bg, edgecolor='#D8E4F0', linewidth=0.3,
            transform=fig.transFigure, zorder=6))
        # Severity cell coloured background
        fig.add_artist(FancyBboxPatch(
            (BOX_X + 0.006, y - rh), SEV_W - 0.002, rh,
            boxstyle='square,pad=0', facecolor=sev_bg, edgecolor='none',
            transform=fig.transFigure, zorder=6))
        # Vertical dividers
        for dx in [DIV1_X, DIV2_X]:
            fig.add_artist(FancyBboxPatch(
                (dx, y - rh), 0.0009, rh,
                boxstyle='square,pad=0', facecolor='#D0DCEA', edgecolor='none',
                transform=fig.transFigure, zorder=7))

        # Severity label (vertically centred)
        fig.text(SEV_TX + 0.008, y - rh / 2, sev_label,
                 ha='left', va='center', fontsize=6.2, fontweight='bold',
                 color=sev_color, transform=fig.transFigure, zorder=7)

        # Finding + action text (top-aligned)
        text_top = y - ROW_PAD * 0.4 - 0.001
        fl = _tw.wrap(r['finding'], width=WRAP_F) or ['']
        fig.text(FIND_TX, text_top, '\n'.join(fl),
                 ha='left', va='top', fontsize=LINE_PT - 0.2, color='#111111',
                 transform=fig.transFigure, zorder=7, linespacing=1.32)
        if r.get('action'):
            al = _tw.wrap(r['action'], width=WRAP_A) or ['']
            fig.text(ACT_TX, text_top, '\n'.join(al),
                     ha='left', va='top', fontsize=LINE_PT - 0.8,
                     color='#1F4E79', style='italic',
                     transform=fig.transFigure, zorder=7, linespacing=1.32)
        y -= rh


# ─────────────────────────────────────────────────────────────
# SECTION 5 - PAGE CREATION FUNCTIONS
# ─────────────────────────────────────────────────────────────

def page_cover(pdf):
    """Cover page: solar farm photo + site name + 8.2 Advisory branding only."""
    fig = plt.figure(figsize=(PAGE_W, PAGE_H), facecolor='white')
    ax  = fig.add_axes([0, 0, 1, 1])
    ax.axis('off')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # ── Solar farm photo (full width, upper ~55% of page) ─────────
    img_y0, img_h = 0.32, 0.68          # photo sits from 32% to 100% height
    if SOLAR_FARM_IMAGE.exists():
        img = plt.imread(str(SOLAR_FARM_IMAGE))
        ax_img = fig.add_axes([0, img_y0, 1, img_h])
        ax_img.imshow(img, aspect='auto', extent=[0, 1, 0, 1],
                      origin='upper')
        ax_img.axis('off')
        # Dark gradient overlay so logo/text sit cleanly on the photo
        import numpy as np
        grad = np.zeros((100, 2, 4))
        for i in range(100):
            t = i / 99.0           # 0=bottom, 1=top of photo
            alpha = 0.55 * (1 - t) + 0.10 * t   # heavier fade at bottom edge
            grad[i, :, :] = [0.12, 0.30, 0.50, alpha]
        ax_img.imshow(grad, extent=[0, 1, 0, 1], aspect='auto',
                      origin='lower', zorder=5)
    else:
        # Fallback: gradient rectangle if image missing
        ax.add_patch(plt.Rectangle((0, img_y0), 1, img_h,
                                    facecolor=C['secondary'], edgecolor='none'))

    # ── Navy band across the top of the photo with 8.2 logo ───────
    band_h = 0.13                         # ~15mm band at very top
    ax.add_patch(plt.Rectangle((0, 1 - band_h), 1, band_h,
                                facecolor=C['primary'], edgecolor='none', zorder=10))
    ax.add_patch(plt.Rectangle((0, 1 - band_h - 0.004), 1, 0.004,
                                facecolor=C['orange'], edgecolor='none', zorder=10))

    logo = get_logo()
    if logo is not None:
        # Left margin = 0.03 figure-fraction = 0.03 × 8.27" = 0.248".
        # To make the top gap physically equal, use top_margin_fig = 0.03 × PAGE_W/PAGE_H
        # so that top_margin_fig × PAGE_H" = 0.03 × PAGE_W" = 0.248".
        h_px, w_px = logo.shape[:2]
        disp_h = 0.07
        disp_w = (w_px / h_px) * disp_h * (PAGE_H / PAGE_W)
        disp_w = min(disp_w, 0.45)
        top_margin_fig = 0.03 * PAGE_W / PAGE_H   # ≈ 0.0212 — physically equal to left margin
        ax_lg = fig.add_axes([0.03, 1.0 - top_margin_fig - disp_h, disp_w, disp_h])
        ax_lg.set_zorder(20)
        ax_lg.imshow(logo, aspect='equal')
        ax_lg.set_facecolor(C['primary'])
        ax_lg.axis('off')

    # Band header text — use fig.text so it always sits above all axes
    fig.text(0.96, 1 - band_h / 2, 'SCADA ANALYSIS REPORT',
             ha='right', va='center', fontsize=13, fontweight='bold',
             color='white', transform=fig.transFigure, zorder=20)

    # ── Main title block — use fig.text to guarantee rendering above photo ──
    # (ax_img is added after ax, so ax.text() would be hidden by the photo layer)
    title_y = img_y0 + img_h * 0.42   # ≈ 0.606 in figure fraction
    # Line 1 — report type
    fig.text(0.50, title_y + 0.12,
             'Comprehensive SCADA Based\nPerformance Analysis',
             ha='center', va='center', fontsize=26, fontweight='bold',
             color='white', transform=fig.transFigure, zorder=20, linespacing=1.3,
             bbox=dict(boxstyle='round,pad=0.5', facecolor=C['primary'],
                       alpha=0.75, edgecolor='none'))
    # Line 2 — site name subtitle
    fig.text(0.50, title_y + 0.01, 'Solar PV Plant  —  La Brede',
             ha='center', va='center', fontsize=17, fontweight='bold',
             color=C['orange'], transform=fig.transFigure, zorder=20,
             bbox=dict(boxstyle='round,pad=0.35', facecolor='#0A1A2A',
                       alpha=0.60, edgecolor='none'))
    # Analysis period and report date
    fig.text(0.50, title_y - 0.08,
             'Analysis Period:  January 2023  –  December 2024',
             ha='center', va='center', fontsize=11, color='white',
             transform=fig.transFigure, zorder=20)
    fig.text(0.50, title_y - 0.13,
             f'Report Date:  {datetime.now().strftime("%d %B %Y")}',
             ha='center', va='center', fontsize=10, color='#D0E8F8',
             transform=fig.transFigure, zorder=20)

    # ── White lower section (below photo) ─────────────────────────
    ax.add_patch(plt.Rectangle((0, 0), 1, img_y0,
                                facecolor='white', edgecolor='none', zorder=8))

    # Orange accent divider between photo and white section
    ax.add_patch(plt.Rectangle((0, img_y0), 1, 0.004,
                                facecolor=C['orange'], edgecolor='none', zorder=9))

    # Tagline and credit in white section
    ax.text(0.50, img_y0 - 0.07,
            'Comprehensive SCADA-based performance & reliability assessment',
            ha='center', va='center', fontsize=10.5, color=C['primary'],
            style='italic', zorder=9)
    ax.text(0.50, img_y0 - 0.14,
            'Prepared by:  8.2 Advisory  |  A Dolfines Company',
            ha='center', va='center', fontsize=9, color='#555555', zorder=9)

    # ── Footer ────────────────────────────────────────────────────
    ax.add_patch(plt.Rectangle((0, 0), 1, 0.07,
                                facecolor='#F2F2F2', edgecolor='none', zorder=9))
    ax.add_patch(plt.Rectangle((0, 0.068), 1, 0.003,
                                facecolor=C['orange'], edgecolor='none', zorder=9))
    ax.text(0.04, 0.034, 'PVPAT / 8.2 Advisory | A Dolfines Company',
            ha='left', va='center', fontsize=8, color='#555555',
            style='italic', zorder=10)
    ax.text(0.96, 0.034,
            f'Confidential  |  {datetime.now().strftime("%B %Y")}',
            ha='right', va='center', fontsize=8, color='#555555', zorder=10)

    pdf.savefig(fig, dpi=150)
    plt.close(fig)


def page_contents(pdf):
    """Standalone table of contents (page 2)."""
    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    _header_bar(fig, 'TABLE OF CONTENTS')
    _footer(fig, 2)

    ax = fig.add_axes([0.08, 0.09, 0.84, 0.82])
    ax.axis('off')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    sections = [
        ('3',  'Site Overview & Technical Datasheet',
               'Site configuration, equipment specifications and analysis parameters'),
        ('4',  'Executive Summary & KPI Dashboard',
               'Key performance indicators, headline findings and site overview'),
        ('5',  'Data Availability Analysis',
               'SCADA data completeness, gaps and quality assessment'),
        ('6',  'Irradiance Data Coherence',
               'Sensor cross-checks, shadow masks and satellite comparison'),
        ('7',  'Site Performance Overview',
               'Monthly and annual PR, energy yield vs. budget'),
        ('8',  'Inverter-level Performance',
               'Per-inverter PR ranking, outlier identification'),
        ('9',  'Availability Analysis',
               'Technical availability per inverter and fleet-level trends'),
        ('10', 'Energy Loss Waterfall',
               'Breakdown of losses from budget to actual generation'),
        ('11–12', 'Reliability Analysis (MTTF)',
               'Mean-time-to-failure, failure frequency by inverter, and detail table'),
        ('13', 'Conclusions & Summary of Findings',
               'Narrative summary of all findings and priority recommendations'),
        ('14', 'Action Punchlist',
               'Prioritised O&M recommendations with recommended actions'),
    ]

    # Section header row
    ax.text(0.058, 0.97, 'PAGE', ha='center', va='center', fontsize=8,
            fontweight='bold', color=C['primary'])
    ax.text(0.14, 0.97, 'SECTION', ha='left', va='center', fontsize=8,
            fontweight='bold', color=C['primary'])
    ax.plot([0, 1], [0.955, 0.955], color=C['orange'], linewidth=1.5,
            transform=ax.transAxes, clip_on=False)

    y = 0.91
    row_h = 0.074
    for idx, (pg_num, title, desc) in enumerate(sections):
        bg = C['light_bg'] if idx % 2 == 0 else 'white'
        ax.add_patch(plt.Rectangle((0, y - row_h + 0.01), 1, row_h - 0.005,
                                    facecolor=bg, edgecolor='none',
                                    transform=ax.transAxes))
        # Orange left accent bar
        ax.add_patch(plt.Rectangle((0, y - row_h + 0.01), 0.006, row_h - 0.005,
                                    facecolor=C['orange'], edgecolor='none',
                                    transform=ax.transAxes))
        mid_y = y - row_h / 2 + 0.005
        ax.text(0.058, mid_y, pg_num, ha='center', va='center',
                fontsize=10, fontweight='bold', color=C['primary'])
        ax.text(0.14, mid_y + 0.015, title, ha='left', va='center',
                fontsize=9.5, fontweight='bold', color=C['primary'])
        ax.text(0.14, mid_y - 0.018, desc, ha='left', va='center',
                fontsize=7.5, color='#555555')
        # Dotted leader line
        ax.plot([0.075, 0.115], [mid_y, mid_y], color='#CCCCCC',
                linewidth=0.5, linestyle=':')
        y -= row_h

    # Bottom note
    ax.text(0.50, 0.01,
            f'Report generated: {datetime.now().strftime("%d %B %Y")}  |  '
            f'8.2 Advisory | A Dolfines Company  |  Confidential',
            ha='center', va='bottom', fontsize=7, color='#888888',
            style='italic')

    pdf.savefig(fig, dpi=150)
    plt.close(fig)


def page_site_intro(pdf, pg):
    """Site overview introduction + technical datasheet (page 3)."""
    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    _header_bar(fig, 'SITE OVERVIEW & TECHNICAL DATASHEET', SITE_NAME)
    _footer(fig, pg)

    # ── Intro paragraph ───────────────────────────────────────────
    ax_intro = fig.add_axes([0.05, 0.76, 0.90, 0.13])
    ax_intro.axis('off')
    intro_text = (
        f"{SITE_NAME} is a utility-scale solar photovoltaic installation with a DC capacity "
        f"of {CAP_DC_KWP:,.0f} kWp ({N_MODULES:,} × {MODULE_WP:.0f} Wp {MODULE_BRAND} modules) "
        f"and an AC export capacity of {CAP_AC_KW:,.0f} kW, served by {N_INVERTERS} "
        f"{INV_MODEL} string inverters rated at {INV_AC_KW:.0f} kW each "
        f"(DC/AC ratio {DC_AC_RATIO:.2f}).\n\n"
        f"This report covers the analysis period January 2023 – December 2024, using "
        f"{INTERVAL_MIN}-minute SCADA data. Performance Ratio is calculated in accordance "
        f"with IEC 61724 on a DC nameplate basis. Irradiance reference data is sourced "
        f"from the SARAH-3 satellite dataset for budget comparisons."
    )
    ax_intro.text(0, 0.95, intro_text, ha='left', va='top', fontsize=8.5,
                  color='#333333', linespacing=1.55, wrap=True,
                  transform=ax_intro.transAxes)

    # Orange divider below intro
    fig.add_artist(FancyBboxPatch((0.05, 0.745), 0.90, 0.002,
                                   boxstyle='square,pad=0',
                                   facecolor=C['orange'], edgecolor='none',
                                   transform=fig.transFigure, zorder=5))

    # ── Technical datasheet table ─────────────────────────────────
    ax = fig.add_axes([0.05, 0.10, 0.90, 0.62])
    ax.axis('off')

    spec_rows = [
        ['Site Name',               SITE_NAME],
        ['Analysis Period',         '2023 – 2024'],
        ['DC Capacity',             f'{CAP_DC_KWP:.2f} kWp'],
        ['AC Capacity',             f'{CAP_AC_KW:.0f} kW'],
        ['DC / AC Ratio',           f'{DC_AC_RATIO:.2f}'],
        ['Number of Modules',       f'{N_MODULES:,}'],
        ['Module Power',            f'{MODULE_WP:.0f} Wp'],
        ['Module Brand',            MODULE_BRAND],
        ['Module Temp. Coefficient',f'{TEMP_COEFF*100:.2f} %/°C'],
        ['Number of Inverters',     f'{N_INVERTERS}'],
        ['Inverter Model',          INV_MODEL],
        ['Inverter AC Power',       f'{INV_AC_KW:.0f} kW each'],
        ['Strings per Inverter',    f'{N_STRINGS_INV}'],
        ['Structure Types',         STRUCT_TYPES],
        ['Transformer Substations', f'{N_PTR}'],
        ['SCADA Data Interval',     f'{INTERVAL_MIN} minutes'],
        ['PR Calculation Method',   'IEC 61724 – AC energy / (G_meas/G_STC × P_DC_kWp)'],
        ['Budget PR Assumption',    f'{DESIGN_PR*100:.0f}%'],
        ['Irradiance Threshold',    f'{IRR_THRESHOLD:.0f} W/m² (daytime cut-off)'],
        ['Reference Irradiance',    'SARAH-3 satellite POA data (Nord & Sud orientations)'],
    ]

    tbl = ax.table(
        cellText=spec_rows,
        colLabels=['Parameter', 'Value'],
        loc='center', cellLoc='left',
        colWidths=[0.45, 0.55],
    )
    _style_table(tbl)   # applies 1.6× row height
    ax.set_title('Technical Configuration & Analysis Parameters',
                 fontweight='bold', color=C['primary'], pad=10, fontsize=10)

    pdf.savefig(fig, dpi=150)
    plt.close(fig)


def page_executive_summary(pdf, pr_res, avail_res, wf, data_avail,
                            cap_kw, punchlist, irr_coh, pg, punchlist_pg=17):
    import textwrap as _tw

    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    _header_bar(fig, 'EXECUTIVE SUMMARY', SITE_NAME)
    _footer(fig, pg)

    # ── Compute KPIs ──────────────────────────────────────────────
    annual   = pr_res['annual']
    last_yr  = int(annual.index[-1])        if len(annual) > 0 else '--'
    last_pr  = float(annual['PR'].iloc[-1]) if len(annual) > 0 else 0
    all_pr   = float(annual['PR'].mean())   if len(annual) > 0 else 0
    total_E  = float(annual['E_act'].sum()) / 1000 if len(annual) > 0 else 0
    n_yrs    = max(len(annual), 1)
    sy_yr    = total_E * 1000 / CAP_DC_KWP / n_yrs if CAP_DC_KWP > 0 else 0
    mean_av  = avail_res['mean']
    da_pwr   = data_avail['overall_power']
    da_irr   = data_avail['irradiance']
    n_high   = sum(1 for i in punchlist if i['priority'] == 'HIGH')
    n_med    = sum(1 for i in punchlist if i['priority'] == 'MEDIUM')
    irr_ok   = all(d['correlation'] > 0.95 and d['suspect_pct'] < 5
                   for d in irr_coh.values()) if irr_coh else True
    total_loss = sum(i.get('mwh_loss', 0) for i in punchlist)
    _e_ref_total = float(annual['E_ref'].sum()) / 1000 if len(annual) > 0 else 0
    _clean_pr    = (total_E + abs(wf.get('avail_loss', 0)) + abs(wf.get('technical_loss', 0))) \
                   / _e_ref_total * 100 if _e_ref_total > 0 else 0

    def _st(ok, bad='▼  BELOW TARGET', good='✔  ON TARGET'):
        """Return (status_text, text_color, bg_color)."""
        return (good, '#1A7A3A', '#E8F5EC') if ok else (bad, '#CC2200', '#FDECEA')

    kpi_rows = [
        ('Site PR  (' + str(last_yr) + ')',       f'{last_pr:.1f}%',        '≥ 75%',     *_st(last_pr >= 75)),
        ('PR Average (all years)',                 f'{all_pr:.1f}%',         '≥ 75%',     *_st(all_pr >= 75)),
        ('Total Energy Produced',                  f'{total_E:.0f} MWh',     '—',         '—', '#444444', '#FFFFFF'),
        ('Specific Yield (annual avg)',             f'{sy_yr:.0f} kWh/kWp/yr','—',         '—', '#444444', '#FFFFFF'),
        ('Mean Inverter Availability',             f'{mean_av:.1f}%',        '≥ 95%',     *_st(mean_av >= 95)),
        ('Power Data Completeness',                f'{da_pwr:.1f}%',         '≥ 95%',     *_st(da_pwr >= 95)),
        ('Irradiance Data Completeness',           f'{da_irr:.1f}%',         '≥ 95%',     *_st(da_irr >= 95)),
        ('Irradiance Sensor Quality',
         'COHERENT' if irr_ok else 'REVIEW', 'COHERENT',
         *_st(irr_ok, '▼  REVIEW REQUIRED', '✔  COHERENT')),
        ('HIGH Priority Action Items',             str(n_high),              '0',
         *_st(n_high == 0, f'▼  {n_high} UNRESOLVED', '✔  NONE')),
        ('Potential PR  (no downtime)',             f'{_clean_pr:.1f}%',      f'≥ {DESIGN_PR*100:.0f}%',
         *_st(_clean_pr >= DESIGN_PR * 100,
              bad=f'▼  BELOW {DESIGN_PR*100:.0f}% DESIGN TARGET',
              good=f'✔  ABOVE {DESIGN_PR*100:.0f}% DESIGN TARGET')),
    ]

    # ── Section 1: KPI table ──────────────────────────────────────
    fig.add_artist(FancyBboxPatch((0.03, 0.830), 0.94, 0.034,
        boxstyle='square,pad=0', facecolor=C['primary'], edgecolor='none',
        transform=fig.transFigure, zorder=5))
    fig.text(0.050, 0.8465, 'PERFORMANCE KPI DASHBOARD',
             ha='left', va='center', fontsize=9, fontweight='bold',
             color='white', transform=fig.transFigure, zorder=6)
    fig.text(0.970, 0.8465, f'{N_INVERTERS} inverters  |  2023–2024',
             ha='right', va='center', fontsize=7.5, color='#C8E0F8',
             transform=fig.transFigure, zorder=6)

    ax_kpi = fig.add_axes([0.03, 0.630, 0.94, 0.200])
    ax_kpi.axis('off')
    kpi_cell_text = [[r[0], r[1], r[2], r[3]] for r in kpi_rows]
    tbl_kpi = ax_kpi.table(
        cellText=kpi_cell_text,
        colLabels=['Metric', 'Value', 'Target', 'Status'],
        loc='upper center', cellLoc='left',
        colWidths=[0.42, 0.16, 0.12, 0.30],
    )
    tbl_kpi.auto_set_font_size(False)
    for col in range(4):
        cell = tbl_kpi[(0, col)]
        cell.set_facecolor(C['secondary'])
        cell.get_text().set_color('white')
        cell.get_text().set_fontweight('bold')
        cell.get_text().set_fontsize(8)
    for ri, kpi in enumerate(kpi_rows):
        r = ri + 1
        _, _, _, _, t_col, bg_col = kpi
        row_bg = '#F7F7F7' if ri % 2 == 0 else 'white'
        for col in range(3):
            cell = tbl_kpi[(r, col)]
            cell.set_facecolor(row_bg)
            cell.get_text().set_fontsize(8)
        sc = tbl_kpi[(r, 3)]
        sc.set_facecolor(bg_col)
        sc.get_text().set_color(t_col)
        sc.get_text().set_fontweight('bold')
        sc.get_text().set_fontsize(8)
    tbl_kpi.scale(1, 0.92)

    # ── Section 2: Overall Assessment ────────────────────────────
    _sum_yr_strs = "  |  ".join(
        f"{yr}: PR={float(annual.loc[yr,'PR']):.1f}%" for yr in annual.index)
    _sum_da_pwr  = data_avail['overall_power']
    _sum_da_irr  = data_avail['irradiance']

    fig.add_artist(FancyBboxPatch((0.03, 0.594), 0.94, 0.030,
        boxstyle='square,pad=0', facecolor=C['primary'], edgecolor='none',
        transform=fig.transFigure, zorder=5))
    fig.text(0.050, 0.609, 'OVERALL ASSESSMENT',
             ha='left', va='center', fontsize=9, fontweight='bold',
             color='white', transform=fig.transFigure, zorder=6)

    fig.add_artist(FancyBboxPatch((0.03, 0.400), 0.94, 0.194,
        boxstyle='square,pad=0', facecolor='#EEF3FA', edgecolor='#B0C4DE', linewidth=0.5,
        transform=fig.transFigure, zorder=4))

    _sum_bullets = [
        (f"UNDERPERFORMANCE ({_sum_yr_strs})",
         "Site PR is below the 75% target in both years; the sharp 2024 decline is driven "
         "by grid tripping events causing fleet-wide unplanned shutdowns — the dominant loss mechanism on site."),
        ("INVERTER-LEVEL ISSUES — OND1.12 & OND2.15",
         "Both units show below-average specific yield from tripping events plus systematic late "
         "start / early stop relative to the fleet — likely caused by Vdc_min startup voltage set too high."),
        (f"DATA GAPS — power: {_sum_da_pwr:.1f}%  |  irradiance: {_sum_da_irr:.1f}%",
         f"Power ({_sum_da_pwr:.1f}%) and irradiance ({_sum_da_irr:.1f}%) completeness are below 95%, "
         "limiting fault attribution depth and preventing direct contractual energy reporting."),
    ]

    _BFS   = 7.5
    _BLH   = _BFS / (PAGE_H * 72) * 1.4    # figure-fraction per line
    _y_bul = 0.587
    for _btitle, _bbody in _sum_bullets:
        fig.text(0.042, _y_bul, f'■  {_btitle}',
                 ha='left', va='top', fontsize=_BFS, fontweight='bold',
                 color=C['primary'], transform=fig.transFigure, zorder=5)
        _y_bul -= _BLH * 1.35
        _blines = _tw.wrap(_bbody, width=158)
        fig.text(0.050, _y_bul, '\n'.join(_blines),
                 ha='left', va='top', fontsize=_BFS - 0.5,
                 color='#333333', transform=fig.transFigure, zorder=5,
                 linespacing=1.30)
        _y_bul -= len(_blines) * _BLH * 1.30 + 0.011

    # ── Section 3: Top 5 actions ──────────────────────────────────
    top5 = sorted(punchlist, key=lambda x: x.get('mwh_loss', 0), reverse=True)[:5]
    top5_mwh = sum(i.get('mwh_loss', 0) for i in top5)

    fig.add_artist(FancyBboxPatch((0.03, 0.356), 0.94, 0.034,
        boxstyle='square,pad=0', facecolor=C['orange'], edgecolor='none',
        transform=fig.transFigure, zorder=5))
    fig.text(0.050, 0.373, 'TOP 5 RECOMMENDED ACTIONS  —  ranked by estimated MWh impact',
             ha='left', va='center', fontsize=9, fontweight='bold',
             color='white', transform=fig.transFigure, zorder=6)
    fig.text(0.970, 0.373,
             f'Top-5 combined: {top5_mwh:.0f} MWh  |  '
             f'{n_high} HIGH / {n_med} MEDIUM items total',
             ha='right', va='center', fontsize=7.5, color='white',
             transform=fig.transFigure, zorder=6)

    ax_act = fig.add_axes([0.03, 0.065, 0.94, 0.287])
    ax_act.axis('off')
    act_rows = []
    for idx, item in enumerate(top5, 1):
        mwh = item.get('mwh_loss', 0)
        mwh_str = f'{mwh:.0f} MWh' if mwh >= 1 else '< 1 MWh'
        finding = _tw.fill(item['issue'],  width=52)
        action  = _tw.fill(item['action'], width=68)
        act_rows.append([str(idx), item['priority'], item['category'],
                         mwh_str, finding, action])
    tbl_act = ax_act.table(
        cellText=act_rows,
        colLabels=['#', 'Priority', 'Category', 'Est. Loss', 'Finding', 'Recommended Action'],
        loc='upper center', cellLoc='left',
        colWidths=[0.025, 0.070, 0.095, 0.075, 0.310, 0.425],
    )
    tbl_act.auto_set_font_size(False)
    for col in range(6):
        cell = tbl_act[(0, col)]
        cell.set_facecolor(C['primary'])
        cell.get_text().set_color('white')
        cell.get_text().set_fontweight('bold')
        cell.get_text().set_fontsize(8)
    for ri, item in enumerate(top5):
        r = ri + 1
        pri   = item['priority']
        p_col = '#CC2200' if pri == 'HIGH' else C['orange'] if pri == 'MEDIUM' else C['green']
        p_bg  = '#FDECEA' if pri == 'HIGH' else '#FFF3E0' if pri == 'MEDIUM' else '#E8F5EC'
        row_bg = '#F7F7F7' if ri % 2 == 0 else 'white'
        for col in range(6):
            cell = tbl_act[(r, col)]
            cell.set_facecolor(p_bg if col == 1 else row_bg)
            cell.get_text().set_fontsize(7.0)
        tbl_act[(r, 1)].get_text().set_color(p_col)
        tbl_act[(r, 1)].get_text().set_fontweight('bold')
        mwh = item.get('mwh_loss', 0)
        tbl_act[(r, 3)].get_text().set_color(
            C['red'] if mwh > 100 else C['orange'] if mwh > 20 else '#444444')
        tbl_act[(r, 3)].get_text().set_fontweight('bold')

    # Dynamic per-row heights so multi-line cells don't overflow into the next row
    _LINE_H_FRAC = 0.042   # axes fraction per text line at 7pt
    _PAD_H_FRAC  = 0.012   # top+bottom padding inside each row
    for col in range(6):
        tbl_act[(0, col)].set_height(0.060)   # fixed header height
    for ri, row in enumerate(act_rows):
        max_ln = max(row[4].count('\n') + 1, row[5].count('\n') + 1, 1)
        row_h  = max_ln * _LINE_H_FRAC + _PAD_H_FRAC
        for col in range(6):
            tbl_act[(ri + 1, col)].set_height(row_h)
        tbl_act[(ri + 1, 4)]._text.set_va('top')
        tbl_act[(ri + 1, 5)]._text.set_va('top')

    # Punchlist reference note
    fig.text(0.50, 0.058,
             f'\u2192  Full descriptions and all {len(punchlist)} action items are in the Action Punchlist on page {punchlist_pg} of this report.',
             ha='center', va='bottom', fontsize=7, color=C['primary'], style='italic',
             transform=fig.transFigure)

    pdf.savefig(fig, dpi=150)
    plt.close(fig)


def page_data_availability(pdf, data_avail, piv, punchlist, pg):
    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    _header_bar(fig, 'DATA AVAILABILITY ANALYSIS')
    _footer(fig, pg)

    gs = GridSpec(3, 1, figure=fig, hspace=0.65,
                  top=0.90, bottom=0.18, left=0.18, right=0.93)

    # 1 - Summary bar chart
    ax1 = fig.add_subplot(gs[0])
    cats = ['Power Data (Overall)', 'Irradiance Data']
    vals = [data_avail['overall_power'], data_avail['irradiance']]
    cols = [C['green'] if v >= 95 else C['orange'] if v >= 90 else C['red'] for v in vals]
    bars = ax1.barh(cats, vals, color=cols, height=0.4, edgecolor='white')
    ax1.axvline(95, color='red', ls='--', lw=1.2, label='95% target')
    ax1.set_xlim(0, 108)
    ax1.set_xlabel('Availability (%)')
    ax1.set_title('Overall Data Availability', fontweight='bold', color=C['primary'])
    for b, v in zip(bars, vals):
        ax1.text(v + 0.5, b.get_y() + b.get_height()/2,
                 f'{v:.1f}%', va='center', fontsize=10, fontweight='bold')
    ax1.legend(fontsize=8); ax1.grid(axis='x', alpha=0.3)

    # 2 - Per-inverter data availability (natural sort by inverter name)
    ax2 = fig.add_subplot(gs[1])
    inv_items = sorted(data_avail['per_inverter'].items(), key=lambda x: _nat(x[0]))
    inv_n = [x[0] for x in inv_items]
    inv_v = [x[1] for x in inv_items]
    cols2 = [C['green'] if v >= 95 else C['orange'] if v >= 90 else C['red'] for v in inv_v]
    ax2.bar(range(len(inv_n)), inv_v, facecolor='white', edgecolor=cols2, linewidth=1.5, width=0.8)
    ax2.axhline(95, color='red', ls='--', lw=1, label='95% target')
    ax2.set_xticks(range(len(inv_n)))
    ax2.set_xticklabels(inv_n, rotation=55, ha='right', fontsize=6.5)
    _da_ymin = min(80, min(inv_v) - 2) if inv_v else 0
    ax2.set_ylim(_da_ymin, 103); ax2.set_ylabel('Data Availability (%)')
    ax2.set_title('Per-Inverter Data Availability', fontweight='bold', color=C['primary'])
    ax2.legend(fontsize=8); ax2.grid(axis='y', alpha=0.3)

    # 3 - Monthly completeness heatmap
    ax3 = fig.add_subplot(gs[2])
    mc = pd.DataFrame(data_avail['monthly'])
    if len(mc) > 0:
        mc.index = mc.index.strftime('%Y-%m')
        _mc_cols = sorted(mc.columns, key=_nat)   # natural sort: OND1.1, OND1.2 … not 1.1, 1.10
        mc = mc[_mc_cols]
        im = ax3.imshow(mc.T.values, aspect='auto', cmap='RdYlGn', vmin=60, vmax=100)
        ax3.set_xticks(range(len(mc.index)))
        ax3.set_xticklabels(mc.index, rotation=55, ha='right', fontsize=6)
        ax3.set_yticks(range(len(_mc_cols)))
        ax3.set_yticklabels(_mc_cols, fontsize=5.5)
        plt.colorbar(im, ax=ax3, label='Completeness (%)', fraction=0.025, shrink=0.8, pad=0.01)
        ax3.set_title('Monthly Data Completeness Heatmap (%)',
                      fontweight='bold', color=C['primary'])

    # ── KEY OBSERVATIONS — driven by punchlist ───────────────────
    _da_rows = [{'sev': r['priority'], 'finding': r['issue'], 'action': r['action']}
                for r in punchlist if r['category'] == 'Data Quality']
    _da_rows.append({
        'sev': 'INFO',
        'finding': "Vertical red columns in heatmap = site-wide gap (NTP, network, script). "
                   "Horizontal streaks = single-inverter comms fault.",
        'action': 'Configure SCADA alert for >30 min gaps during daylight to enable same-day detection.',
    })
    _da_below95 = sum(1 for v in data_avail['per_inverter'].values() if v < 95)
    _da_below90 = sum(1 for v in data_avail['per_inverter'].values() if v < 90)
    _da_worst_inv = min(data_avail['per_inverter'], key=data_avail['per_inverter'].get) if data_avail['per_inverter'] else ''
    _da_worst_v   = data_avail['per_inverter'].get(_da_worst_inv, 100)
    _da_both_bad  = data_avail['overall_power'] < 95 and data_avail['irradiance'] < 95
    _da_caption = (
        f"Analysis: Power data completeness is {data_avail['overall_power']:.1f}% and irradiance completeness is "
        f"{data_avail['irradiance']:.1f}% — {'both below' if _da_both_bad else 'one or both below'} the 95% reliability threshold, "
        f"so all PR and energy KPIs for gap periods carry elevated uncertainty and cannot be used for contractual reporting without correction. "
        f"{_da_below95} of {len(data_avail['per_inverter'])} inverters individually fall below 95% data completeness"
        + (f", with {_da_below90} below 90% (worst: {_da_worst_inv} at {_da_worst_v:.1f}%)" if _da_below90 > 0 else "")
        + ". Dark vertical columns in the heatmap are site-wide communication outages — they compress monthly totals and must be "
        "recovered from the SCADA buffer before any annual performance assessment is issued. "
        "Horizontal gaps are single-inverter SCADA losses and disproportionately skew MTTF and availability figures for those units."
    )
    _page_insight(fig, _da_rows, gs=gs, has_rotated_labels=True, caption=_da_caption)

    pdf.savefig(fig, dpi=150)
    plt.close(fig)


def page_irradiance_coherence(pdf, irr_coh, irr, test_df, punchlist, pg):
    if not irr_coh:
        return

    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    _header_bar(fig, 'IRRADIANCE DATA COHERENCE ANALYSIS')
    _footer(fig, pg)

    n = len(irr_coh)
    gs = GridSpec(n * 2 + 1, 1, figure=fig, hspace=0.65,
                  top=0.90, bottom=0.18, left=0.10, right=0.85)

    row = 0
    for name, d in irr_coh.items():
        ax_d = fig.add_subplot(gs[row:row+2, 0])
        dd = d['daily_df'].dropna()
        if len(dd) > 0:
            # Convert date index to DatetimeIndex for resampling
            dd_dt = dd.copy()
            dd_dt.index = pd.to_datetime(dd_dt.index)
            mo_m = dd_dt['measured'].resample('ME').sum()   # kWh/m²/month
            mo_r = dd_dt['reference'].resample('ME').sum()

            x = np.arange(len(mo_m))
            w = 0.35
            ax_d.bar(x - w/2, mo_m.values, w,
                     color=C['secondary'], alpha=0.85, label='Measured (pyranometer)')
            ax_d.bar(x + w/2, mo_r.values, w,
                     color=C['yellow'], alpha=0.85, label=f'SARAH_{name} (satellite)')
            ax_d.set_xticks(x)
            ax_d.set_xticklabels([m.strftime('%b\n%Y') for m in mo_m.index], fontsize=6)
            ax_d.set_ylabel('Irradiation (kWh/m²/month)', fontsize=8)
            ax_d.set_title(
                f'Monthly GHI Totals: Measured vs SARAH_{name}  '
                f'(R={d["correlation"]:.3f}  |  Mean ratio={d["mean_ratio"]:.2f}±{d["std_ratio"]:.2f}  '
                f'|  Suspect={d["suspect_pct"]:.1f}%)',
                fontsize=8, fontweight='bold', color=C['primary'])
            ax_d.legend(fontsize=6, ncol=2, loc='upper left')
            ax_d.grid(axis='y', alpha=0.3)

            # Right axis: monthly bias % (measured vs satellite)
            ax_b = ax_d.twinx()
            bias = (mo_m - mo_r) / mo_r.replace(0, np.nan) * 100
            ax_b.plot(x, bias.values, color=C['red'], lw=1.2,
                      marker='o', ms=3.5, label='Monthly bias (%)', zorder=5)
            ax_b.set_ylabel('Monthly bias\n(+= over-reading, −= under)', fontsize=6.5,
                            color=C['red'])
            ax_b.tick_params(axis='y', colors=C['red'], labelsize=7)
            ax_b.spines['right'].set_color(C['red'])
            # Annotate each bias point with its value
            for xi, bv in zip(x, bias.values):
                if not np.isnan(bv):
                    ax_b.text(xi, bv + 0.3, f'{bv:+.1f}%',
                              ha='center', va='bottom', fontsize=5.5, color=C['red'])
        row += 2

    # Summary table
    ax_t = fig.add_subplot(gs[row, 0])
    ax_t.axis('off')
    rows_t = []
    for name, d in irr_coh.items():
        status = '✔ OK' if d['correlation'] > 0.95 and d['suspect_pct'] < 5 else '⚠ Review'
        rows_t.append([
            f'SARAH_{name}',
            f'{d["correlation"]:.3f}',
            f'{d["mean_ratio"]:.2f} ± {d["std_ratio"]:.2f}',
            f'{d["daily_diff_mean"]:.1f}%',
            f'{d["suspect_pct"]:.1f}%',
            f'{d["days_with_gaps"]}',
            status,
        ])
    cols_t = ['Reference', 'R (corr.)', 'Ratio ± σ', 'Daily Δ',
              'Suspect %', 'Gap days', 'Status']
    tbl = ax_t.table(cellText=rows_t, colLabels=cols_t, loc='center', cellLoc='center')
    _style_table(tbl)
    ax_t.set_title('Coherence Summary', fontweight='bold', color=C['primary'], pad=6)

    # ── KEY OBSERVATIONS — driven by punchlist ───────────────────
    _ic_rows = [{'sev': r['priority'], 'finding': r['issue'], 'action': r['action']}
                for r in punchlist if r['category'] == 'Irradiance Sensor']
    _ic_rows.append({
        'sev': 'INFO',
        'finding': "Ratio = sensor / satellite. Ratio > 1.0 = sensor reads MORE irradiance than satellite (over-reading). "
                   "Ratio < 1.0 = sensor reads LESS (under-reading). "
                   "Dirty dome causes under-reading; reflective surfaces near the sensor cause over-reading. "
                   "Suspect % = intervals deviating >30% in either direction. "
                   "High suspect rates make the PR denominator unreliable — all historical PR figures require recalculation.",
        'action': 'Clean dome monthly; shield from nearby reflective surfaces; request factory calibration every 2 years.',
    })
    _ic_all_bad   = all(d['correlation'] < 0.95 or d['suspect_pct'] > 5 for d in irr_coh.values())
    _ic_summary   = "; ".join(
        f"SARAH_{n}: R={d['correlation']:.3f}, suspect={d['suspect_pct']:.1f}%, "
        f"mean ratio={d['mean_ratio']:.2f} ({'over-reading' if d['mean_ratio'] > 1 else 'under-reading'})"
        for n, d in irr_coh.items()
    )
    _ic_worst_s   = max(d['suspect_pct'] for d in irr_coh.values()) if irr_coh else 0
    _ic_mean_rat  = np.mean([d['mean_ratio'] for d in irr_coh.values()]) if irr_coh else 1.0
    _ic_dir       = "OVER" if _ic_mean_rat > 1.0 else "UNDER"
    _ic_dir_cause = (
        "reflective surfaces near the sensor or a calibration offset — NOT consistent with dome soiling (which causes under-reading)"
        if _ic_mean_rat > 1.0 else
        "dome soiling, partial shading of the sensor, or dome degradation — clean the dome and recalibrate"
    )
    _ic_pr_effect = (
        f"Since the sensor reads {abs(_ic_mean_rat - 1)*100:.1f}% MORE irradiance than the satellite reference, "
        "the PR denominator is over-inflated — actual site performance is marginally BETTER than the reported PR figure "
        "(over-reading makes PR appear slightly lower than reality, not higher). "
        f"However, a {abs(_ic_mean_rat - 1)*100:.1f}% sensor offset can account for at most ~{abs(_ic_mean_rat - 1)*100:.1f} percentage points of PR — "
        "it cannot explain the large observed PR shortfall. The dominant causes of low PR are operational: availability losses and equipment underperformance."
        if _ic_mean_rat > 1.0 else
        f"Since the sensor reads {abs(_ic_mean_rat - 1)*100:.1f}% LESS irradiance than the satellite reference, "
        "the PR denominator is deflated — reported PR is artificially inflated relative to true performance. "
        "The actual energy deficit is therefore larger than the PR figure suggests."
    )
    _ic_caption = (
        f"Chart reading guide: each pair of bars shows the pyranometer monthly total (blue) against the SARAH satellite reference (yellow) in kWh/m²/month. "
        f"The red line (right axis) shows the monthly bias — positive values mean the sensor is reading MORE irradiance than the satellite that month, "
        f"negative values mean it is reading LESS. A flat bias line near 0% would indicate a reliable sensor; a consistently positive or negative bias reveals a systematic offset. "
        f"Stats: {_ic_summary}. "
        + ("Both sensors show poor coherence with the satellite reference — results must be treated with caution. "
           if _ic_all_bad else "Overall sensor coherence is acceptable but the systematic bias must be accounted for. ")
        + f"The mean ratio {'> 1.0' if _ic_mean_rat > 1.0 else '< 1.0'} confirms the pyranometer is on average {_ic_dir}-reading. "
        f"The most likely cause is {_ic_dir_cause}. {_ic_pr_effect} "
        + f"The {_ic_worst_s:.1f}% suspect rate (sub-interval readings deviating >30% from satellite) means roughly 1 in {100/max(_ic_worst_s,1):.0f} daytime intervals is severely anomalous — "
        "these corrupt energy yield and PR calculations and must be removed before any contractual KPI figures are issued."
    )
    _page_insight(fig, _ic_rows, gs=gs, caption=_ic_caption)

    # Shift coherence summary table down 1.5 cm so title doesn't bleed into chart above
    _p = ax_t.get_position()
    _shift = (1.5 / 2.54) / PAGE_H   # 1.5 cm → figure fraction ≈ 0.050
    ax_t.set_position([_p.x0, _p.y0 - _shift, _p.width, _p.height])

    pdf.savefig(fig, dpi=150)
    plt.close(fig)


def page_performance_overview(pdf, pr_res, piv, cap_kw, punchlist, pg):
    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    _header_bar(fig, 'SITE PERFORMANCE OVERVIEW - PR & ENERGY')
    _footer(fig, pg)

    gs = GridSpec(4, 2, figure=fig, hspace=0.40, wspace=0.35,
                  top=0.90, bottom=0.18, left=0.10, right=0.97)

    monthly = pr_res['monthly']
    annual  = pr_res['annual']

    # 1 - Monthly energy
    ax1 = fig.add_subplot(gs[0, :])
    if len(monthly) > 0:
        x    = range(len(monthly))
        emwh = monthly['E_act'] / 1000
        cols = [C['secondary'] if m.month < 7 else C['accent']
                for m in monthly.index]
        ax1.bar(x, emwh, color=cols, width=0.75, edgecolor='white')
        ax1.set_xticks(x)
        ax1.set_xticklabels([m.strftime('%b\n%Y') for m in monthly.index],
                             fontsize=6.5)
        ax1.set_ylabel('Energy (MWh)')
        ax1.set_title('Monthly Energy Production (Site)', fontweight='bold', color=C['primary'])
        ax1.grid(axis='y', alpha=0.3)
        for i, v in enumerate(emwh):
            if v > 0:
                ax1.text(i, v + emwh.max()*0.01, f'{v:.0f}',
                         ha='center', va='bottom', fontsize=6)

    # 2 - Monthly PR
    ax2 = fig.add_subplot(gs[1, :])
    if len(monthly) > 0:
        pr_v = monthly['PR'].values
        cprs = [C['green'] if v >= 75 else C['orange'] if v >= 65 else C['red']
                for v in pr_v]
        ax2.bar(range(len(monthly)), pr_v, color=cprs, width=0.75, edgecolor='white')
        ax2.axhline(75, color='green', ls='--', lw=1, label='75% target')
        ax2.axhline(65, color='orange', ls=':', lw=1, label='65% alert')
        ax2.axhline(100, color='purple', ls=':', lw=0.8, alpha=0.5, label='100% (physical max)')
        ax2.set_xticks(range(len(monthly)))
        ax2.set_xticklabels([m.strftime('%b\n%Y') for m in monthly.index], fontsize=6.5)
        ax2.set_ylim(0, 115); ax2.set_ylabel('PR (%)')
        ax2.set_title('Monthly Performance Ratio', fontweight='bold', color=C['primary'])
        ax2.legend(fontsize=7); ax2.grid(axis='y', alpha=0.3)
        for i, v in enumerate(pr_v):
            label = f'{v:.1f}' if v <= 100 else f'{v:.1f}*'
            ax2.text(i, v + 1, label, ha='center', va='bottom', fontsize=6,
                     color='purple' if v > 100 else 'black')
        # Annotate suspect months (PR > 100 %)
        suspect_i = [i for i, v in enumerate(pr_v) if v > 100]
        if suspect_i:
            ax2.annotate(
                '* PR > 100%: likely caused by irradiance sensor gaps\n'
                '  making the GHI reference artificially low that month.',
                xy=(suspect_i[0], pr_v[suspect_i[0]]),
                xytext=(suspect_i[0] + 0.5, 108),
                fontsize=5.5, color='purple', style='italic',
                arrowprops=dict(arrowstyle='->', color='purple', lw=0.7))

    # 3 - Annual table (note partial years)
    ax3 = fig.add_subplot(gs[2, :])
    ax3.axis('off')
    rows = []
    # Determine month counts per year to flag partial years
    monthly_yr = monthly.groupby(monthly.index.year).size()
    for yr, row in annual.iterrows():
        n_mon = monthly_yr.get(yr, 12)
        yr_label = f'{yr}' if n_mon >= 12 else f'{yr} ({n_mon} mo.)*'
        rows.append([
            yr_label,
            f'{row["E_act"]/1e6:.3f} GWh',
            f'{row["irrad"]:.0f} kWh/m²',
            f'{row["PR"]:.1f}%',
            f'{row["E_act"]/cap_kw:.0f} h' if cap_kw > 0 else '--',
        ])
    cols_a = ['Year', 'Energy', 'Irradiation', 'PR', 'Full-load hrs']
    tbl = ax3.table(cellText=rows, colLabels=cols_a, loc='center', cellLoc='center')
    _style_table(tbl)
    tbl.scale(1, 2)
    has_partial = any(monthly_yr.get(yr, 12) < 12 for yr in annual.index)
    title_note = '  (* partial year — not directly comparable)' if has_partial else ''
    ax3.text(0.5, 1.02, f'Annual Performance Summary{title_note}',
             ha='center', va='bottom', transform=ax3.transAxes,
             fontweight='bold', color=C['primary'],
             fontsize=plt.rcParams['axes.titlesize'])

    # 4 - Daily specific yield time-series (uses DC kWp for IEC-standard specific yield)
    ax4 = fig.add_subplot(gs[3, :])
    site_pwr = piv.sum(axis=1, min_count=1)
    daily_sy = site_pwr.resample('D').sum() * INTERVAL_H / max(CAP_DC_KWP, 1)  # kWh/kWp/day
    ax4.fill_between(daily_sy.index, daily_sy.values, alpha=0.4, color=C['secondary'])
    ax4.plot(daily_sy.index, daily_sy.values, color=C['primary'], lw=0.7)
    # Rolling 30-day mean
    roll = daily_sy.rolling(30, center=True).mean()
    ax4.plot(roll.index, roll.values, color=C['red'], lw=1.5,
             label='30-day rolling mean')
    ax4.set_ylabel('Specific Yield (kWh/kWp/day)')
    ax4.set_title('Daily Specific Yield & 30-day Rolling Mean',
                  fontweight='bold', color=C['primary'])
    ax4.legend(fontsize=7); ax4.grid(alpha=0.3)
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))

    # ── KEY OBSERVATIONS — driven by punchlist ───────────────────
    _po_rows = [{'sev': r['priority'], 'finding': r['issue'], 'action': r['action']}
                for r in punchlist if r['category'] == 'Performance']
    _po_rows.append({
        'sev': 'INFO',
        'finding': "Industry benchmark for CdTe PV in SW France: PR 78–83%. "
                   "Fleet σ > 3% across inverters indicates significant variability requiring investigation.",
        'action': '(1) Soiling removal; (2) MPPT optimisation; (3) string repairs; (4) clipping review.',
    })
    _po_annual   = pr_res['annual']
    _po_yrs      = list(_po_annual.index)
    _po_prs      = {yr: float(_po_annual.loc[yr, 'PR']) for yr in _po_yrs}
    _po_irrs     = {yr: float(_po_annual.loc[yr, 'irrad']) for yr in _po_yrs}
    _po_monthly  = pr_res.get('monthly')
    _po_n_b65    = sum(1 for v in _po_monthly['PR'].values if v < 65)  if _po_monthly is not None else 0
    _po_n_b75    = sum(1 for v in _po_monthly['PR'].values if 65 <= v < 75) if _po_monthly is not None else 0
    _po_pr_drop  = (_po_prs[_po_yrs[0]] - _po_prs[_po_yrs[-1]]) if len(_po_yrs) >= 2 else 0
    _po_irr_drop = (_po_irrs[_po_yrs[0]] - _po_irrs[_po_yrs[-1]]) if len(_po_yrs) >= 2 else 0
    _po_caption = (
        "Analysis: "
        + " | ".join(
            f"{yr}: PR={_po_prs[yr]:.1f}%, irrad.={_po_irrs[yr]:.0f} kWh/m² "
            f"({'meets' if _po_prs[yr] >= 75 else 'BELOW'} 75% target)"
            for yr in _po_yrs
        ) + ". "
        + (f"The {_po_pr_drop:.1f} pp year-on-year PR decline accompanies only a {_po_irr_drop:.0f} kWh/m² irradiation reduction — "
           f"confirming the performance gap is not solely weather-driven and has an O&M component. "
           if len(_po_yrs) >= 2 and _po_pr_drop > 5 else "")
        + (f"{_po_n_b65} month(s) fell below the 65% critical threshold and "
           f"{_po_n_b75} between 65–75%. " if _po_n_b65 + _po_n_b75 > 0 else "")
        + "The 30-day rolling mean (bottom chart) shows sustained flat or declining yield during summer months when irradiation peaks, "
        "which is inconsistent with weather alone and points to active loss mechanisms — soiling accumulation and undetected downtime are the primary candidates."
    )
    _page_insight(fig, _po_rows, gs=gs, caption=_po_caption)

    pdf.savefig(fig, dpi=150)
    plt.close(fig)


def page_inverter_performance(pdf, pr_res, avail_res, inv_caps, punchlist, pg):
    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    _header_bar(fig, 'INVERTER-LEVEL PERFORMANCE ANALYSIS')
    _footer(fig, pg)

    gs = GridSpec(3, 1, figure=fig, hspace=0.35,
                  top=0.90, bottom=0.18, left=0.11, right=0.97)

    inv_list = sorted(pr_res['per_inverter'].keys(), key=_nat)
    pr_vals  = [pr_res['per_inverter'].get(i, 0) for i in inv_list]
    av_vals  = [avail_res['per_inverter'].get(i, 0) for i in inv_list]

    valid_pr = [v for v in pr_vals if v > 0]
    fleet_mean = np.mean(valid_pr) if valid_pr else 0
    fleet_std  = np.std(valid_pr)  if valid_pr else 0

    x = range(len(inv_list))

    # 1 - PR bar chart (white bars with coloured outlines)
    ax1 = fig.add_subplot(gs[0])
    cprs = []
    for v in pr_vals:
        if v <= 0:            cprs.append('#AAAAAA')
        elif v < fleet_mean - 2*fleet_std: cprs.append(C['red'])
        elif v < fleet_mean - fleet_std:   cprs.append(C['orange'])
        else:                              cprs.append(C['green'])
    ax1.bar(x, pr_vals, facecolor='white', edgecolor=cprs, linewidth=1.5, width=0.8)
    ax1.axhline(fleet_mean, color='blue', ls='--', lw=1.2,
                label=f'Fleet mean {fleet_mean:.1f}%')
    ax1.axhline(fleet_mean - fleet_std, color='orange', ls=':',
                lw=1, label=f'−1σ ({fleet_mean-fleet_std:.1f}%)')
    ax1.axhline(fleet_mean - 2*fleet_std, color='red', ls=':',
                lw=1, label=f'−2σ ({fleet_mean-2*fleet_std:.1f}%)')
    ax1.set_xticks(x); ax1.set_xticklabels(inv_list, rotation=50, ha='right', fontsize=6.5)
    ax1.set_ylabel('PR (%)'); ax1.set_ylim(0, min(fleet_mean * 1.3, 110))
    ax1.set_title('Performance Ratio by Inverter', fontweight='bold', color=C['primary'])
    ax1.legend(fontsize=7, ncol=2); ax1.grid(axis='y', alpha=0.3)

    # 2 - Availability bar chart (white bars with coloured outlines)
    ax2 = fig.add_subplot(gs[1])
    cav = [C['green'] if v >= 95 else C['orange'] if v >= 90 else C['red'] for v in av_vals]
    ax2.bar(x, av_vals, facecolor='white', edgecolor=cav, linewidth=1.5, width=0.8)
    ax2.axhline(95, color='red', ls='--', lw=1.2, label='95% target')
    ax2.set_xticks(x); ax2.set_xticklabels(inv_list, rotation=50, ha='right', fontsize=6.5)
    _av_ymin = min(80, min(av_vals) - 2) if av_vals else 0
    ax2.set_ylim(_av_ymin, 103); ax2.set_ylabel('Availability (%)')
    ax2.set_title('Technical Availability by Inverter', fontweight='bold', color=C['primary'])
    ax2.legend(fontsize=7); ax2.grid(axis='y', alpha=0.3)

    # 3 - PR vs Availability scatter
    ax3 = fig.add_subplot(gs[2])
    sc = ax3.scatter(av_vals, pr_vals, c=pr_vals, cmap='RdYlGn',
                     vmin=max(fleet_mean - 3*fleet_std, 0), vmax=fleet_mean + fleet_std,
                     s=60, zorder=5, edgecolors='k', lw=0.4)
    for i, inv in enumerate(inv_list):
        ax3.annotate(inv, (av_vals[i], pr_vals[i]),
                     textcoords='offset points', xytext=(4, 2), fontsize=5.5)
    ax3.axvline(95, color='red', ls='--', lw=1, alpha=0.6, label='95% avail target')
    ax3.axhline(fleet_mean, color='blue', ls='--', lw=1, alpha=0.6, label='Fleet PR mean')
    plt.colorbar(sc, ax=ax3, label='', shrink=0.7, fraction=0.025, pad=0.01)
    ax3.set_xlabel('Availability (%)'); ax3.set_ylabel('PR (%)')
    ax3.set_title('PR vs Availability -- Inverter Comparison',
                  fontweight='bold', color=C['primary'])
    ax3.legend(fontsize=7); ax3.grid(alpha=0.3)

    # ── KEY OBSERVATIONS — driven by punchlist ───────────────────
    _ip_rows = [{'sev': r['priority'], 'finding': r['issue'], 'action': r['action']}
                for r in punchlist if r['category'] == 'Inverter PR']
    _ip_rows.append({
        'sev': 'INFO',
        'finding': "Inverters low across both 2023 and 2024 have persistent structural issues. "
                   "One-year outliers may reflect a fault since corrected.",
        'action': 'Cross-check with O&M maintenance records before scheduling field work.',
    })
    _ip_below2s  = [(inv_list[i], pr_vals[i]) for i in range(len(inv_list))
                    if pr_vals[i] > 0 and pr_vals[i] < fleet_mean - 2 * fleet_std]
    _ip_below95a = sum(1 for v in av_vals if v < 95)
    _ip_low_both = [(inv_list[i], pr_vals[i], av_vals[i]) for i in range(len(inv_list))
                    if pr_vals[i] > 0 and pr_vals[i] < fleet_mean - fleet_std and av_vals[i] < 95]
    _ip_caption = (
        f"Analysis: Fleet PR mean = {fleet_mean:.1f}%, \u03c3 = {fleet_std:.1f}%. "
        + (f"{len(_ip_below2s)} inverter(s) fall below the 2\u03c3 boundary ({fleet_mean - 2*fleet_std:.1f}%): "
           + ", ".join(f"{inv} ({pr:.1f}%)" for inv, pr in _ip_below2s[:5])
           + (" + more" if len(_ip_below2s) > 5 else "")
           + " — these are the highest-priority performance investigation targets. "
           if _ip_below2s else "No inverters fall below the 2\u03c3 boundary. ")
        + f"{_ip_below95a} inverter(s) are individually below the 95% availability target. "
        + (f"{len(_ip_low_both)} inverter(s) have both low PR and low availability (scatter lower-left quadrant) — "
           "for these units, improving uptime alone will recover most of the production gap before investigating quality losses separately. "
           if _ip_low_both else
           "Inverters with low PR but good availability are running but underproducing — investigate soiling, string faults, and MPPT settings.")
    )
    _page_insight(fig, _ip_rows, gs=gs, has_rotated_labels=True, caption=_ip_caption)

    pdf.savefig(fig, dpi=150)
    plt.close(fig)


def page_availability(pdf, avail_res, piv, irr, punchlist, pg):
    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    _header_bar(fig, 'AVAILABILITY ANALYSIS')
    _footer(fig, pg)

    gs = GridSpec(3, 2, figure=fig, hspace=0.38, wspace=0.35,
                  top=0.90, bottom=0.18, left=0.10, right=0.92)

    site_monthly = avail_res['site_monthly'].dropna()

    # 1 - Site monthly availability
    ax1 = fig.add_subplot(gs[0, :])
    if len(site_monthly) > 0:
        cols = [C['green'] if v >= 95 else C['orange'] if v >= 90 else C['red']
                for v in site_monthly.values]
        ax1.bar(range(len(site_monthly)), site_monthly.values,
                facecolor='white', edgecolor=cols, linewidth=1.5, width=0.75)
        ax1.axhline(95, color='red', ls='--', lw=1, label='95% target')
        ax1.set_xticks(range(len(site_monthly)))
        ax1.set_xticklabels([str(d.strftime('%b\n%Y'))
                              if hasattr(d, 'strftime') else str(d)
                              for d in site_monthly.index], fontsize=6.5)
        ax1.set_ylim(0, 105); ax1.set_ylabel('Availability (%)')
        ax1.set_title('Site Monthly Availability (Fleet Average)',
                      fontweight='bold', color=C['primary'])
        ax1.legend(fontsize=7); ax1.grid(axis='y', alpha=0.3)
        for i, v in enumerate(site_monthly.values):
            ax1.text(i, v + 0.4, f'{v:.1f}', ha='center', va='bottom', fontsize=6)

    # 2 - Per-inverter monthly availability heatmap
    ax2 = fig.add_subplot(gs[1, :])
    pim_df = avail_res.get('per_inverter_monthly')
    if pim_df is not None and not pim_df.empty:
        cols_sorted_av = sorted(pim_df.columns, key=_nat)
        pim_mat = pim_df[cols_sorted_av].T.values  # shape: n_inv × n_months
        im2 = ax2.imshow(pim_mat, aspect='auto', cmap='RdYlGn', vmin=70, vmax=100,
                         interpolation='nearest')
        ax2.set_yticks(range(len(cols_sorted_av)))
        ax2.set_yticklabels(cols_sorted_av, fontsize=5.5)
        m_labels = [d.strftime('%b\n%y') for d in pim_df.index]
        ax2.set_xticks(range(len(pim_df.index)))
        ax2.set_xticklabels(m_labels, fontsize=6)
        plt.colorbar(im2, ax=ax2, label='Availability (%)', fraction=0.025, pad=0.01, shrink=0.8)
        ax2.set_title('Per-Inverter Monthly Availability Heatmap — Red = Low, Green = High',
                      fontweight='bold', color=C['primary'])

    # 3 - Daily site energy production heatmap-style
    ax3 = fig.add_subplot(gs[2, :])
    ghi_s = irr.set_index('ts')['GHI'].reindex(piv.index) if len(irr) else None
    site_pwr = piv.sum(axis=1, min_count=1)
    daily_e = site_pwr.resample('D').sum() * INTERVAL_H / 1000  # MWh/day
    if ghi_s is not None:
        daily_irr = ghi_s.resample('D').sum() * INTERVAL_H / 1000  # kWh/m²/day
        ax3b = ax3.twinx()
        ax3b.fill_between(daily_irr.index, daily_irr.values,
                          alpha=0.25, color=C['yellow'], label='Irradiation (kWh/m²)')
        ax3b.set_ylabel('Irradiation (kWh/m²/day)', color=C['yellow'], fontsize=8)
        ax3b.tick_params(axis='y', colors=C['yellow'])
    ax3.fill_between(daily_e.index, daily_e.values, alpha=0.5, color=C['secondary'])
    ax3.plot(daily_e.index, daily_e.values, color=C['primary'], lw=0.7, label='Site energy')
    ax3.set_ylabel('Daily Energy (MWh)'); ax3.grid(alpha=0.3)
    ax3.set_title('Daily Site Energy Production', fontweight='bold', color=C['primary'])
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
    ax3.legend(fontsize=7, loc='upper left')

    # Stats box
    n_below = sum(1 for v in avail_res['per_inverter'].values() if v < 95)
    txt = (f"Fleet mean availability: {avail_res['mean']:.1f}%\n"
           f"Inverters < 95%: {n_below}/{len(avail_res['per_inverter'])}\n"
           f"Grid-level simultaneous outages: {avail_res['whole_site_events']}\n"
           f"(all inverters offline at once — likely MV grid events)")
    ax1.text(0.98, 0.04, txt, transform=ax1.transAxes, fontsize=7.5,
             ha='right', va='bottom', bbox=dict(facecolor='white', alpha=0.8,
             edgecolor=C['secondary'], boxstyle='round,pad=0.3'))

    # ── KEY OBSERVATIONS — driven by punchlist ───────────────────
    _av_rows = [{'sev': r['priority'], 'finding': r['issue'], 'action': r['action']}
                for r in punchlist if r['category'] in ('Availability', 'Grid / Site')]
    _av_rows.append({
        'sev': 'INFO',
        'finding': "Common Sungrow SG250HX trip causes: grid over/under-voltage, DC insulation alarm (earth fault), "
                   "AC contactor wear, MPPT low-irradiance startup failure.",
        'action': 'Fault codes from Sungrow SolarInfo monitor required to classify each event — SCADA only captures on/off state.',
    })
    _av_n_b95    = sum(1 for v in avail_res['per_inverter'].values() if v < 95)
    _av_n_b90    = sum(1 for v in avail_res['per_inverter'].values() if v < 90)
    _av_worst3   = sorted(avail_res['per_inverter'].items(), key=lambda x: x[1])[:3]
    _av_gap      = abs(avail_res['mean'] - 95)
    _av_caption  = (
        f"Analysis: Fleet mean availability is {avail_res['mean']:.1f}% — "
        + ("below" if avail_res['mean'] < 95 else "meeting")
        + f" the 95% contractual target by {_av_gap:.1f} pp. "
        f"{_av_n_b95} of {len(avail_res['per_inverter'])} inverters individually fall below 95%"
        + (f", with {_av_n_b90} below 90%" if _av_n_b90 > 0 else "")
        + f". Worst three: {', '.join(f'{inv} ({v:.1f}%)' for inv, v in _av_worst3)}. "
        + (f"{avail_res['whole_site_events']} periods where all {N_INVERTERS} inverters went offline simultaneously appear as uniform dark columns spanning every row of the heatmap — "
           "these are grid-level events (MV protection trips, frequency excursions) and require DSO disturbance records, not inverter servicing, to resolve. "
           if avail_res['whole_site_events'] > 0 else "")
        + "Isolated dark cells in the heatmap are single-inverter faults that should be cross-referenced with the fault code export for root-cause classification."
    )
    _page_insight(fig, _av_rows, gs=gs, has_rotated_labels=True, caption=_av_caption)

    pdf.savefig(fig, dpi=150)
    plt.close(fig)


def page_waterfall(pdf, wf, pr_res, avail_res, punchlist, pg):
    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    _header_bar(fig, 'ENERGY LOSS WATERFALL ANALYSIS')
    _footer(fig, pg)

    gs = GridSpec(2, 2, figure=fig, hspace=0.38, wspace=0.40,
                  top=0.90, bottom=0.18, left=0.10, right=0.97)

    # ── Build waterfall series ───────────────────────────────────
    cats       = []
    bar_bot    = []
    bar_ht     = []
    bar_col    = []
    bar_style  = []   # 'solid' for anchor bars, 'outline' for adjustment bars
    run_total  = 0.0

    def add_bar(label, delta, col, is_abs=False):
        nonlocal run_total
        if is_abs:
            cats.append(label);  bar_bot.append(0)
            bar_ht.append(delta); bar_col.append(col)
            bar_style.append('solid')
            run_total = delta
        else:
            bot = run_total if delta >= 0 else run_total + delta
            cats.append(label); bar_bot.append(bot)
            bar_ht.append(abs(delta)); bar_col.append(col)
            bar_style.append('outline')
            run_total += delta

    add_bar('Budget\n(Theoretical)', wf['budget'],            C['budget'],    is_abs=True)
    if abs(wf['weather_corr']) > 0.1:
        col_w = C['green'] if wf['weather_corr'] >= 0 else C['red']
        add_bar('Weather\nCorrection', wf['weather_corr'], col_w)
    add_bar('Weather-\nCorrected',    wf['weather_corrected'], C['secondary'], is_abs=True)
    if abs(wf['avail_loss']) > 0.1:
        add_bar('Availability\nLoss',    wf['avail_loss'],     C['red'])
    if abs(wf['technical_loss']) > 0.1:
        add_bar('Technical\nLoss',       wf['technical_loss'], C['orange'])
    if abs(wf['residual']) > 0.1:
        col_r = C['green'] if wf['residual'] >= 0 else C['red']
        add_bar('Residual\n(Over/Under)', wf['residual'],      col_r)
    add_bar('Actual\nProduction',     wf['actual'],            C['actual'],    is_abs=True)

    # Main waterfall chart
    ax1 = fig.add_subplot(gs[0, :])
    x = range(len(cats))
    for i, (bot, ht, col, sty) in enumerate(zip(bar_bot, bar_ht, bar_col, bar_style)):
        if sty == 'outline':
            ax1.bar(i, ht, bottom=bot, facecolor='white', edgecolor=col,
                    linewidth=2.0, width=0.6, zorder=3)
        else:
            ax1.bar(i, ht, bottom=bot, color=col, width=0.6,
                    edgecolor='white', lw=1.2, alpha=0.88, zorder=3)
        mid = bot + ht / 2
        ax1.text(i, mid, f'{ht:.0f}\nMWh', ha='center', va='center',
                 fontsize=7.5, fontweight='bold', color='#1A2A3A', zorder=5)
        # Connector
        if i > 0:
            prev_top = bar_bot[i-1] + bar_ht[i-1]
            ax1.plot([i-0.3, i-0.7], [prev_top, prev_top],
                     'k-', alpha=0.25, lw=0.8)

    ax1.set_xticks(x); ax1.set_xticklabels(cats, fontsize=8)
    ax1.set_ylabel('Energy (MWh)'); ax1.grid(axis='y', alpha=0.3, zorder=0)
    ax1.set_title('Energy Waterfall -- Full Analysis Period',
                  fontweight='bold', color=C['primary'])
    ymax = max(wf['budget'], wf['weather_corrected']) * 1.15
    ax1.set_ylim(0, ymax)

    # Legend — simplified: green outline = Gain, red outline = Loss
    lp = [
        mpatches.Patch(facecolor='white', edgecolor=C['green'], linewidth=2, label='Gain'),
        mpatches.Patch(facecolor='white', edgecolor=C['red'],   linewidth=2, label='Loss'),
    ]
    ax1.legend(handles=lp, fontsize=8, loc='upper right')

    # ── Monthly availability loss breakdown ──────────────────────
    ax2 = fig.add_subplot(gs[1, 0])
    monthly_pr_df = pr_res.get('monthly')
    site_monthly  = avail_res.get('site_monthly', pd.Series(dtype=float))
    if monthly_pr_df is not None and len(monthly_pr_df) > 0 and len(site_monthly) > 0:
        # Monthly budget energy (MWh): E_ref (kWh) × DESIGN_PR / 1000
        m_budget_mwh = monthly_pr_df['E_ref'] * DESIGN_PR / 1000
        m_avail_pct  = site_monthly.reindex(monthly_pr_df.index).fillna(
                            avail_res['mean'])
        m_avail_loss = (m_budget_mwh * (1.0 - m_avail_pct / 100)).clip(lower=0)
        # Colour by monthly availability
        m_cols = [C['red'] if av < 90 else C['orange'] if av < 95 else C['green']
                  for av in m_avail_pct.values]
        xm = range(len(m_avail_loss))
        ax2.bar(xm, m_avail_loss.values, facecolor='white', edgecolor=m_cols,
                linewidth=1.5, width=0.75)
        mean_ml = float(m_avail_loss.mean())
        ax2.axhline(mean_ml, color='grey', ls='--', lw=0.9, alpha=0.7,
                    label=f'Monthly mean {mean_ml:.0f} MWh')
        ax2.set_xticks(list(xm))
        ax2.set_xticklabels(
            [d.strftime('%b\n%y') for d in m_avail_loss.index], fontsize=6)
        ax2.set_ylabel('Est. avail. loss (MWh)', fontsize=7)
        ax2.set_title('Monthly Availability Loss Breakdown\n'
                      '(shows which months drove the total availability deficit)',
                      fontweight='bold', color=C['primary'], fontsize=7.5)
        ax2.legend(fontsize=6); ax2.grid(axis='y', alpha=0.3)
        # Annotate each bar with monthly availability %
        for i, (av, v) in enumerate(zip(m_avail_pct.values, m_avail_loss.values)):
            ax2.text(i, v + float(m_avail_loss.max()) * 0.02 + 0.01,
                     f'{av:.0f}%', ha='center', va='bottom', fontsize=5.5,
                     color='#333333')

    # ── Summary metrics table ────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.axis('off')
    rows = [
        ['Budget\nproduction',        f'{wf["budget"]:.0f} MWh', '100%'],
        ['Weather\ncorrection',        f'{wf["weather_corr"]:+.0f} MWh',
         f'{wf["weather_corr"]/wf["budget"]*100:+.1f}%'],
        ['Weather-\ncorrected',        f'{wf["weather_corrected"]:.0f} MWh',
         f'{wf["weather_corrected"]/wf["budget"]*100:.1f}%'],
        ['Availability\nloss',         f'{wf["avail_loss"]:.0f} MWh',
         f'{wf["avail_loss"]/wf["budget"]*100:.1f}%'],
        ['Technical\nloss',            f'{wf["technical_loss"]:.0f} MWh',
         f'{wf["technical_loss"]/wf["budget"]*100:.1f}%'],
        ['Residual\n(over/under)',      f'{wf["residual"]:+.0f} MWh',
         f'{wf["residual"]/wf["budget"]*100:+.1f}%'],
        ['Actual\nproduction',         f'{wf["actual"]:.0f} MWh',
         f'{wf["actual"]/wf["budget"]*100:.1f}%'],
    ]
    tbl = ax3.table(cellText=rows,
                    colLabels=['Category', 'Energy', '% Budget'],
                    loc='center', cellLoc='center')
    _style_table(tbl); tbl.scale(1, 1.9)
    ax3.set_title('Waterfall Summary', fontweight='bold', color=C['primary'], pad=28)

    # ── KEY OBSERVATIONS — driven by punchlist ───────────────────
    _wf_actual_pct = wf['actual'] / wf['budget'] * 100 if wf['budget'] > 0 else 0
    _wf_rows = [{'sev': 'INFO',
                 'finding': f"Actual = {wf['actual']:.0f} MWh ({_wf_actual_pct:.1f}% of budget). "
                            f"Avail. loss {abs(wf['avail_loss']):.0f} MWh + Tech. loss {abs(wf['technical_loss']):.0f} MWh. "
                            f"Weather correction {wf['weather_corr']:+.0f} MWh (non-actionable).",
                 'action': ''}]
    # Show all HIGH punchlist items sorted by MWh impact (already sorted)
    _wf_rows += [{'sev': r['priority'], 'finding': r['issue'], 'action': r['action']}
                 for r in punchlist if r['priority'] == 'HIGH']
    _wf_av_pct   = abs(wf['avail_loss']) / wf['budget'] * 100 if wf['budget'] > 0 else 0
    _wf_te_pct   = abs(wf['technical_loss']) / wf['budget'] * 100 if wf['budget'] > 0 else 0
    _wf_ac_pct   = wf['actual'] / wf['budget'] * 100 if wf['budget'] > 0 else 0
    _wf_dom      = "availability (downtime)" if abs(wf['avail_loss']) >= abs(wf['technical_loss']) else "technical underperformance"
    _wf_recovery = abs(wf['avail_loss']) * 0.40
    # Split availability loss into grid-level (whole-site) vs individual inverter losses
    _wf_grid_mwh = min(
        avail_res.get('whole_site_outage_intervals', 0) * CAP_AC_KW * INTERVAL_H / 1000,
        abs(wf['avail_loss'])
    )
    _wf_inv_mwh  = max(0, abs(wf['avail_loss']) - _wf_grid_mwh)
    _wf_grid_pct = _wf_grid_mwh / abs(wf['avail_loss']) * 100 if wf['avail_loss'] != 0 else 0
    _wf_inv_pct  = 100 - _wf_grid_pct
    _wf_res_pct  = wf['residual'] / wf['budget'] * 100 if wf['budget'] > 0 else 0
    _wf_caption  = (
        f"Budget methodology: theoretical production is calculated as Reference GHI (SARAH-3 satellite, "
        f"or measured GHI where satellite data is unavailable) × DC capacity ({CAP_DC_KWP:.0f} kWp) × "
        f"{DESIGN_PR*100:.0f}% design PR (IEC 61724). Weather correction adjusts for deviation of measured "
        f"irradiance from the satellite reference; it is non-actionable. "
        f"Actual production = {wf['actual']:.0f} MWh ({_wf_ac_pct:.1f}% of weather-corrected budget). "
        f"Availability loss = {abs(wf['avail_loss']):.0f} MWh ({_wf_av_pct:.1f}% of budget), of which "
        f"~{_wf_grid_pct:.0f}% ({_wf_grid_mwh:.0f} MWh) is grid-level (all inverters simultaneously offline) "
        f"and ~{_wf_inv_pct:.0f}% ({_wf_inv_mwh:.0f} MWh) is individual inverter trips. "
        f"Technical underperformance = {abs(wf['technical_loss']):.0f} MWh ({_wf_te_pct:.1f}%). "
        f"{_wf_dom.capitalize()} is the dominant production gap driver. "
        + ("Availability loss is O&M-recoverable: a realistic 40% improvement in maintenance response time "
           f"would recover approximately {_wf_recovery:.0f} MWh per period. "
           if abs(wf['avail_loss']) > 0 else "")
        + (f"Note: the residual shows a marginal apparent overperformance of {wf['residual']:.0f} MWh "
           f"({_wf_res_pct:+.1f}%). This does not contradict the low site PR: the {DESIGN_PR*100:.0f}% design PR "
           f"used in the budget is a contractual assumption; when availability and technical losses are modelled "
           f"separately, the residual captures only the unexplained variance. The overall site underperformance "
           f"is confirmed by the PR analysis and the identified fault mechanisms. "
           if wf['residual'] > 1.0 else "")
        + "The right chart identifies the months where the availability deficit was most acute — "
        "cross-reference with O&M records to confirm documented response times meet contractual SLAs."
    )
    _page_insight(fig, _wf_rows, gs=gs, has_rotated_labels=True, caption=_wf_caption)

    pdf.savefig(fig, dpi=150)
    plt.close(fig)


def page_mttf(pdf, mttf_res, punchlist, pg):
    """Two pages: pg=charts, pg+1=detail table."""
    inv_list = sorted(mttf_res.keys(), key=_nat)  # natural sort (module-level helper)
    n_fail   = [mttf_res[i]['n_failures'] for i in inv_list]
    mttf_d   = [min(mttf_res[i]['mttf_days'], 365)
                if np.isfinite(mttf_res[i]['mttf_days']) else 365
                for i in inv_list]
    x = range(len(inv_list))

    # ── Page 1: two bar charts ────────────────────────────────────
    fig1 = plt.figure(figsize=(PAGE_W, PAGE_H))
    _header_bar(fig1, 'RELIABILITY ANALYSIS -- MTTF', SITE_NAME)
    _footer(fig1, pg)

    gs1 = GridSpec(2, 1, figure=fig1, hspace=0.35,
                   top=0.90, bottom=0.18, left=0.11, right=0.97)

    ax1 = fig1.add_subplot(gs1[0])
    cn = [C['red'] if n > 100 else C['orange'] if n > 30 else C['green']
          for n in n_fail]
    ax1.bar(x, n_fail, facecolor='white', edgecolor=cn, linewidth=1.5, width=0.8)
    mn = np.mean(n_fail)
    ax1.axhline(mn, color='blue', ls='--', lw=1.2, label=f'Mean: {mn:.0f}')
    ax1.set_xticks(x)
    ax1.set_xticklabels(inv_list, rotation=50, ha='right', fontsize=6.5)
    ax1.set_ylabel('Number of fault events')
    ax1.set_title('Fault Event Count by Inverter (Analysis Period)',
                  fontweight='bold', color=C['primary'])
    ax1.legend(fontsize=7); ax1.grid(axis='y', alpha=0.3)

    ax2 = fig1.add_subplot(gs1[1])
    # Literature target: IEA PVPS Task 13 / NREL O&M guidelines suggest MTTF ≥ 90 days
    # Green ≥ 90 d, Yellow 30–90 d, Red < 30 d
    cm = [C['green'] if v >= 90 else C['orange'] if v >= 30 else C['red']
          for v in mttf_d]
    ax2.bar(x, mttf_d, facecolor='white', edgecolor=cm, linewidth=1.5, width=0.8)
    ax2.axhline(90, color='green', ls='--', lw=1,
                label='90-day target (IEA PVPS / NREL O&M benchmark)')
    ax2.set_xticks(x)
    ax2.set_xticklabels(inv_list, rotation=50, ha='right', fontsize=6.5)
    ax2.set_ylabel('MTTF (days, capped at 365)')
    ax2.set_title('Mean Time to Failure by Inverter',
                  fontweight='bold', color=C['primary'])
    ax2.legend(fontsize=7); ax2.grid(axis='y', alpha=0.3)
    for i, (inv, n) in enumerate(zip(inv_list, n_fail)):
        if n == 0:
            ax2.text(i, 5, 'No faults', ha='center', va='bottom',
                     fontsize=5.5, color=C['green'])

    # ── KEY OBSERVATIONS insight table ──────────────────────────
    _total_faults  = sum(n_fail)
    _n_high_fault  = sum(1 for n in n_fail if n > 100)
    _n_med_fault   = sum(1 for n in n_fail if 30 < n <= 100)
    _fin_mttf      = [v for v in mttf_d if v < 365]
    _fleet_mttf    = np.mean(_fin_mttf) if _fin_mttf else float('nan')
    _worst3_mttf   = sorted(
        [(inv, m['mttf_days']) for inv, m in mttf_res.items()
         if np.isfinite(m['mttf_days']) and m['n_failures'] > 0],
        key=lambda x: x[1])[:3]
    # ── KEY OBSERVATIONS — driven by punchlist ───────────────────
    _mttf_rows = [{'sev': r['priority'], 'finding': r['issue'], 'action': r['action']}
                  for r in punchlist if r['category'] == 'Reliability']
    _mttf_rows.append({
        'sev': 'INFO',
        'finding': "Sungrow SG250HX common trip causes: grid over/under-voltage, DC insulation alarm, "
                   "AC contactor wear, MPPT startup failure. SCADA only captures on/off — alarm codes needed to classify.",
        'action': 'Download full fault log from Sungrow SolarInfo platform; check firmware vs latest service bulletin.',
    })
    _mttf_n_high  = sum(1 for n in n_fail if n > 100)
    _mttf_n_med   = sum(1 for n in n_fail if 30 < n <= 100)
    _mttf_fin     = [v for v in mttf_d if v < 365]
    _mttf_fmean   = np.mean(_mttf_fin) if _mttf_fin else 0
    _mttf_worst3  = sorted(
        [(inv_list[i], n_fail[i], mttf_d[i]) for i in range(len(inv_list)) if n_fail[i] > 0],
        key=lambda x: x[1], reverse=True
    )[:3]
    _mttf_caption = (
        f"Analysis: {_mttf_n_high} inverter(s) recorded >100 fault events and {_mttf_n_med} recorded 30–100 over the analysis period. "
        + (f"Three highest fault counts: {', '.join(f'{inv} ({n}f, MTTF={d:.1f}d)' for inv, n, d in _mttf_worst3)}. "
           if _mttf_worst3 else "")
        + f"Fleet mean MTTF is {_mttf_fmean:.1f} days against the 90-day industry benchmark (IEA PVPS Task 13 / NREL O&M guidelines). "
        + ("This is significantly below benchmark, indicating a systemic reliability problem that reactive maintenance alone cannot resolve — "
           "the root failure mode must be identified from fault codes before any hardware decisions are made. "
           if _mttf_fmean < 60 else
           "This is within the acceptable benchmark range, though individual red inverters still require fault code review. ")
        + "Near-daily cycling places cumulative thermal and mechanical stress on IGBT modules and AC contactors — "
        "without root-cause diagnosis, replacement hardware will fail at the same rate."
    )
    _page_insight(fig1, _mttf_rows, gs=gs1, has_rotated_labels=True, caption=_mttf_caption)

    pdf.savefig(fig1, dpi=150)
    plt.close(fig1)

    # ── Page 2: detail table ──────────────────────────────────────
    fig2 = plt.figure(figsize=(PAGE_W, PAGE_H))
    _header_bar(fig2, 'RELIABILITY ANALYSIS -- MTTF DETAIL TABLE', SITE_NAME)
    _footer(fig2, pg + 1)

    ax3 = fig2.add_axes([0.05, 0.09, 0.90, 0.80])
    ax3.axis('off')

    rows = []
    for inv in inv_list:
        m  = mttf_res[inv]
        md = m['mttf_days']
        rows.append([
            inv,
            str(m['n_failures']),
            f'{m["running_hours"]:.0f} h',
            f'{md:.1f} d' if np.isfinite(md) else 'inf',
            f'{m["mttf_hours"]:.0f} h' if np.isfinite(m["mttf_hours"]) else 'inf',
            '✔' if m['n_failures'] == 0 else (
                '!!' if m['n_failures'] > 100 else
                '!'  if m['n_failures'] > 30  else '✔'),
        ])
    tbl = ax3.table(cellText=rows,
                    colLabels=['Inverter', 'Faults', 'Run hrs',
                               'MTTF (d)', 'MTTF (h)', 'Status'],
                    loc='upper center', cellLoc='center',
                    colWidths=[0.18, 0.12, 0.16, 0.16, 0.16, 0.12])
    _style_table(tbl)
    # _style_table already applies scale(1, 1.6).  Calling scale again multiplies,
    # so use 0.58 here → effective 1.6 × 0.58 ≈ 0.93 (tight rows, 31 inv. fit).
    tbl.scale(1, 0.58)
    for cell in tbl.get_celld().values():
        cell.set_fontsize(7.5)
    # Conditional row colouring: !! = critical (light red), ! = warning (light yellow)
    for (r, c), cell in tbl.get_celld().items():
        if r == 0:
            continue   # header already styled
        status_val = rows[r - 1][-1]   # last column = Status
        if status_val == '!!':
            cell.set_facecolor('#FFDDDD')
        elif status_val == '!':
            cell.set_facecolor('#FFF5CC')
    ax3.set_title('MTTF Detail — All Inverters',
                  fontweight='bold', color=C['primary'], pad=8, fontsize=10)

    pdf.savefig(fig2, dpi=150)
    plt.close(fig2)


def fetch_weather_data(cache_path):
    """Fetch or load cached daily weather for La Brede, France (44.69°N, -0.51°E).

    Returns dict with keys 'time', 'temperature_2m_max', 'precipitation_sum'
    (lists of strings/floats aligned by date).  Returns None on failure.
    """
    import urllib.request
    import json
    try:
        if cache_path.exists():
            with open(cache_path, encoding='utf-8') as f:
                return json.load(f)
        url = (
            "https://archive-api.open-meteo.com/v1/archive"
            "?latitude=44.69&longitude=-0.51"
            "&start_date=2023-01-01&end_date=2024-12-31"
            "&daily=temperature_2m_max,precipitation_sum"
            "&timezone=Europe%2FParis"
        )
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        return data
    except Exception as exc:
        print(f"  [Weather] Could not fetch data: {exc} — weather page will be skipped.")
        return None


def page_weather_correlation(pdf, pr_res, weather_data, pg):
    """PR vs weather events page — correlates rain/temperature with performance."""
    if weather_data is None:
        return

    import datetime as _dt
    try:
        w_dates = pd.to_datetime(weather_data['daily']['time'])
        w_tmax  = pd.Series(weather_data['daily']['temperature_2m_max'], index=w_dates,
                            dtype=float)
        w_rain  = pd.Series(weather_data['daily']['precipitation_sum'],  index=w_dates,
                            dtype=float)
    except (KeyError, TypeError):
        return

    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    _header_bar(fig, 'WEATHER CORRELATION — PR vs TEMPERATURE & RAINFALL')
    _footer(fig, pg)

    gs = GridSpec(2, 1, figure=fig, hspace=0.42,
                  top=0.90, bottom=0.18, left=0.12, right=0.78)

    monthly_pr_df = pr_res.get('monthly')
    if monthly_pr_df is None or len(monthly_pr_df) == 0:
        plt.close(fig)
        return

    # ── Chart 1: Monthly PR + monthly precipitation + temperature ────
    ax1 = fig.add_subplot(gs[0])
    months = monthly_pr_df.index
    pr_vals = monthly_pr_df['PR'].values
    pr_cols = [C['green'] if v >= 75 else C['orange'] if v >= 65 else C['red']
               for v in pr_vals]
    ax1.bar(range(len(months)), pr_vals, facecolor='white', edgecolor=pr_cols,
            linewidth=1.5, width=0.65, label='Monthly PR')
    ax1.axhline(75, color='green', ls='--', lw=0.9, label='75% target', alpha=0.7)
    ax1.axhline(65, color='red',   ls='--', lw=0.9, label='65% alert',  alpha=0.7)
    ax1.set_xticks(range(len(months)))
    ax1.set_xticklabels([d.strftime('%b\n%y') for d in months], fontsize=6.5)
    ax1.set_ylabel('PR (%)')
    ax1.set_ylim(max(0, min(pr_vals) * 0.9), min(105, max(pr_vals) * 1.1))

    # Overlay: monthly total precipitation (secondary axis)
    ax1b = ax1.twinx()
    m_rain = w_rain.resample('ME').sum().reindex(months)
    ax1b.bar(range(len(months)), m_rain.values,
             color='steelblue', alpha=0.3, width=0.65, label='Monthly rain (mm)')
    ax1b.set_ylabel('Monthly precipitation (mm)', color='steelblue', fontsize=8)
    ax1b.tick_params(axis='y', colors='steelblue')

    # Overlay: monthly mean max temperature
    ax1c = ax1.twinx()
    ax1c.spines['right'].set_position(('outward', 55))
    m_temp = w_tmax.resample('ME').mean().reindex(months)
    ax1c.plot(range(len(months)), m_temp.values, 'r-o', ms=4, lw=1.2,
              label='Mean max T (°C)')
    ax1c.set_ylabel('Mean max temperature (°C)', color='red', fontsize=8)
    ax1c.tick_params(axis='y', colors='red')

    # Combined legend
    lines1, lbs1 = ax1.get_legend_handles_labels()
    lines2, lbs2 = ax1b.get_legend_handles_labels()
    lines3, lbs3 = ax1c.get_legend_handles_labels()
    ax1.legend(lines1 + lines2 + lines3, lbs1 + lbs2 + lbs3, fontsize=6, ncol=3,
               loc='lower left')
    ax1.set_title('Monthly PR vs Precipitation and Temperature\n'
                  'High rain → PR may rise (soiling washoff); High temperature → PR may dip (thermal derating)',
                  fontweight='bold', color=C['primary'])

    # ── Chart 2: Daily production scatter coloured by temperature ────
    ax2 = fig.add_subplot(gs[1])
    daily_pr = pr_res.get('df_day')
    if daily_pr is not None and len(daily_pr) > 0:
        dp = daily_pr.copy()
        dp['date'] = dp.index.normalize()
        dp_agg = dp.resample('D').agg(PR=('E_act', 'sum'))
        dp_agg['PR'] = (dp['E_act'].resample('D').sum() /
                        dp['E_ref'].resample('D').sum().replace(0, np.nan) * 100).clip(0, 110)
        dp_agg = dp_agg.join(w_tmax.rename('tmax'), how='left')
        dp_agg = dp_agg.join(w_rain.rename('rain'), how='left')
        dp_agg = dp_agg.dropna(subset=['PR'])
        valid = dp_agg[dp_agg['PR'] > 0]
        if len(valid) > 0:
            scatter_c = valid['tmax'].fillna(20)
            sc = ax2.scatter(valid.index, valid['PR'], c=scatter_c,
                             cmap='RdYlGn_r', vmin=10, vmax=40, s=4, alpha=0.6)
            plt.colorbar(sc, ax=ax2, label='Max temperature (°C)',
                         fraction=0.02, pad=0.01, shrink=0.8)
            # Mark heavy rain days (≥10mm)
            rain_days = dp_agg[dp_agg['rain'] >= 10]
            if len(rain_days) > 0:
                ax2.scatter(rain_days.index, rain_days['PR'].clip(0, 110),
                            marker='v', color='steelblue', s=18, alpha=0.7,
                            zorder=5, label='Rain ≥10mm')
                ax2.legend(fontsize=7)
            ax2.axhline(75, color='green', ls='--', lw=0.9, alpha=0.7)
            ax2.set_ylabel('Daily PR (%)'); ax2.grid(alpha=0.2)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
            ax2.set_title('Daily PR coloured by max temperature — red = hot day (thermal derating risk)',
                          fontweight='bold', color=C['primary'])

    # Insight rows
    _wx_rows = [
        {'sev': 'INFO',
         'finding': 'Hot months (Jul–Aug): PR dips due to thermal derating (CdTe Tc coeff −0.26%/°C). '
                    'This is expected — not an O&M fault.',
         'action': 'Verify by plotting PR vs daily max temperature. If R² < 0.3, thermal effect is weak — investigate other causes.'},
        {'sev': 'INFO',
         'finding': 'After significant rain (≥10mm): look for yield step-change (soiling washoff). '
                    'If visible, compare to dry-period PR to quantify soiling loss.',
         'action': 'Overlay rain events on rolling 7-day specific yield to estimate soiling accumulation rate and cleaning ROI.'},
    ]
    _wx_annual   = pr_res.get('annual')
    _wx_yrs      = list(_wx_annual.index) if _wx_annual is not None else []
    _wx_pr_d     = {yr: float(_wx_annual.loc[yr, 'PR'])    for yr in _wx_yrs} if _wx_annual is not None else {}
    _wx_irr_d    = {yr: float(_wx_annual.loc[yr, 'irrad']) for yr in _wx_yrs} if _wx_annual is not None else {}
    _wx_pr_drop  = (_wx_pr_d[_wx_yrs[0]] - _wx_pr_d[_wx_yrs[-1]])   if len(_wx_yrs) >= 2 else 0
    _wx_irr_drop = (_wx_irr_d[_wx_yrs[0]] - _wx_irr_d[_wx_yrs[-1]]) if len(_wx_yrs) >= 2 else 0
    _wx_caption  = (
        "Analysis: Monthly PR bars overlaid with weather data allow separation of weather-driven PR variation from O&M-related loss. "
        + (f"Year-on-year PR declined {_wx_pr_drop:.1f} pp while irradiation fell only {_wx_irr_drop:.0f} kWh/m² ({_wx_irr_drop / max(_wx_irr_d.get(_wx_yrs[0], 1), 1) * 100:.0f}%) — "
           "the disproportionate PR drop confirms a non-weather performance component requiring field investigation. "
           if len(_wx_yrs) >= 2 and _wx_pr_drop > 5 else "")
        + "If the bottom scatter shows a clear downward slope with temperature (cool = green dots at higher PR, red dots lower), "
        "thermal derating accounts for some summer PR reduction — this is normal for CdTe at \u22120.26\u2009%/\u00b0C and should not trigger O&M actions. "
        "Rain spikes in the bar chart followed by a PR step-change upward identify soiling washoff events; "
        "the magnitude of that step is the soiling loss rate and determines the cleaning programme ROI."
    )
    _page_insight(fig, _wx_rows, gs=gs, caption=_wx_caption)

    pdf.savefig(fig, dpi=150)
    plt.close(fig)


def page_start_stop(pdf, start_stop_df, pg):
    """Inverter start/stop time deviation chart — detects voltage threshold anomalies."""
    if start_stop_df is None or start_stop_df.empty:
        return

    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    _header_bar(fig, 'INVERTER START / STOP TIME ANALYSIS')
    _footer(fig, pg)

    gs = GridSpec(2, 1, figure=fig, hspace=0.42,
                  top=0.90, bottom=0.18, left=0.11, right=0.97)

    inv_list = sorted(start_stop_df.index, key=_nat)
    x = range(len(inv_list))
    start_dev = [start_stop_df.loc[i, 'start_dev'] for i in inv_list]
    stop_dev  = [start_stop_df.loc[i, 'stop_dev']  for i in inv_list]

    # Fleet mean start/stop in HH:MM for title
    fs_min = start_stop_df['start_min'].mean()
    fe_min = start_stop_df['stop_min'].mean()
    fs_hm  = f'{int(fs_min//60):02d}:{int(fs_min%60):02d}'
    fe_hm  = f'{int(fe_min//60):02d}:{int(fe_min%60):02d}'

    threshold = 15.0   # minutes — flag as potentially anomalous

    # ── Start time deviation ─────────────────────────────────────
    ax1 = fig.add_subplot(gs[0])
    cs = [C['red'] if abs(v) > threshold else C['orange'] if abs(v) > 8 else C['green']
          for v in start_dev]
    ax1.bar(x, start_dev, facecolor='white', edgecolor=cs, linewidth=1.5, width=0.8)
    ax1.axhline(0,  color='black', lw=0.8)
    ax1.axhline( threshold, color=C['red'],    ls='--', lw=1,
                 label=f'+{threshold:.0f} min threshold (late start)')
    ax1.axhline(-threshold, color=C['red'],    ls='--', lw=1)
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(inv_list, rotation=50, ha='right', fontsize=6.5)
    ax1.set_ylabel('Start time deviation (min)')
    ax1.set_title(f'Inverter Start Time Deviation from Fleet Mean (fleet mean: {fs_hm})\n'
                  'Positive = starts later than fleet mean; negative = starts earlier',
                  fontweight='bold', color=C['primary'])
    ax1.legend(fontsize=7); ax1.grid(axis='y', alpha=0.3)

    # ── Stop time deviation ──────────────────────────────────────
    ax2 = fig.add_subplot(gs[1])
    ce = [C['red'] if abs(v) > threshold else C['orange'] if abs(v) > 8 else C['green']
          for v in stop_dev]
    ax2.bar(x, stop_dev, facecolor='white', edgecolor=ce, linewidth=1.5, width=0.8)
    ax2.axhline(0,  color='black', lw=0.8)
    ax2.axhline( threshold, color=C['red'],    ls='--', lw=1)
    ax2.axhline(-threshold, color=C['red'],    ls='--', lw=1,
                label=f'−{threshold:.0f} min threshold (early stop)')
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(inv_list, rotation=50, ha='right', fontsize=6.5)
    ax2.set_ylabel('Stop time deviation (min)')
    ax2.set_title(f'Inverter Stop Time Deviation from Fleet Mean (fleet mean: {fe_hm})\n'
                  'Negative = stops earlier than fleet mean (possible low-voltage cutoff)',
                  fontweight='bold', color=C['primary'])
    ax2.legend(fontsize=7); ax2.grid(axis='y', alpha=0.3)

    # Insight rows
    n_late_start = sum(1 for v in start_dev if v > threshold)
    n_early_stop = sum(1 for v in stop_dev  if v < -threshold)
    _ss_rows = []
    if n_late_start > 0:
        late_list = ', '.join(inv_list[i] for i, v in enumerate(start_dev) if v > threshold)
        _ss_rows.append({
            'sev': 'MEDIUM',
            'finding': f'{n_late_start} inverter(s) start >{threshold:.0f} min later than fleet mean: {late_list}',
            'action': 'Check Sungrow minimum start irradiance and Vdc_min settings; compare firmware config across inverters.',
        })
    if n_early_stop > 0:
        early_list = ', '.join(inv_list[i] for i, v in enumerate(stop_dev) if v < -threshold)
        _ss_rows.append({
            'sev': 'MEDIUM',
            'finding': f'{n_early_stop} inverter(s) stop >{threshold:.0f} min earlier than fleet mean: {early_list}',
            'action': 'Check DC under-voltage protection threshold; inspect string fuses and DC cabling for voltage drop.',
        })
    _ss_rows.append({
        'sev': 'INFO',
        'finding': f'Fleet mean start: {fs_hm}  |  Fleet mean stop: {fe_hm}. '
                   'Deviations >15 min indicate non-uniform MPPT start/stop threshold settings or DC side issues.',
        'action': 'Only days with >2 kWh/m² daily irradiation are included in the average to exclude overcast days.',
    })
    _ss_max_late  = max((abs(v) for v in start_dev if v > threshold), default=0)
    _ss_max_early = max((abs(v) for v in stop_dev  if v < -threshold), default=0)
    _ss_caption   = (
        f"Analysis: Fleet mean start {fs_hm}, mean stop {fe_hm}. "
        + (f"{n_late_start} inverter(s) start >{threshold:.0f} min late (max deviation: {_ss_max_late:.0f} min). "
           "A 15-min late start on a 250 kW inverter during peak summer irradiance costs approximately 60 kWh/day — "
           "multiplied across all late starters and all days, this is a material recoverable loss. "
           "Root cause is typically a high minimum-irradiance startup threshold or elevated Vdc_min setting in the inverter configuration. "
           if n_late_start > 0 else "No inverters start systematically late. ")
        + (f"{n_early_stop} inverter(s) stop >{threshold:.0f} min early (max: {_ss_max_early:.0f} min). "
           "Early stops often indicate a low DC under-voltage cutoff triggering before string voltage stabilises at dusk — "
           "inspect Vdc_min settings and measure string open-circuit voltage at end-of-day to rule out DC wiring voltage drop. "
           if n_early_stop > 0 else "No inverters stop systematically early. ")
        + ("Non-uniform start/stop behaviour across the fleet suggests different firmware configurations — "
           "a configuration audit comparing each inverter\u2019s startup parameters against the OEM-recommended values is warranted."
           if n_late_start > 0 or n_early_stop > 0 else "")
    )
    _page_insight(fig, _ss_rows, gs=gs, has_rotated_labels=True, caption=_ss_caption)

    pdf.savefig(fig, dpi=150)
    plt.close(fig)


def page_conclusion(pdf, pr_res, avail_res, wf, data_avail,
                    mttf_res, punchlist, irr_coh, pg):
    """Single-page narrative conclusion summarising all findings."""
    import textwrap as _tw

    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    _header_bar(fig, 'CONCLUSIONS & SUMMARY OF FINDINGS', SITE_NAME)
    _footer(fig, pg)

    ax = fig.add_axes([0.03, 0.09, 0.94, 0.82])
    ax.axis('off')
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)

    annual     = pr_res['annual']
    n_years    = max(len(annual), 1)
    spec_yield = annual['E_act'].sum() / CAP_DC_KWP / n_years if CAP_DC_KWP > 0 else 0
    total_mwh  = annual['E_act'].sum() / 1000

    hi_count   = sum(1 for i in punchlist if i['priority'] == 'HIGH')
    me_count   = sum(1 for i in punchlist if i['priority'] == 'MEDIUM')
    total_loss_mwh = sum(i.get('mwh_loss', 0) for i in punchlist)

    irr_ok = all(d['correlation'] > 0.95 and d['suspect_pct'] < 5
                 for d in irr_coh.values()) if irr_coh else True
    sorted_av  = sorted(avail_res['per_inverter'].items(), key=lambda x: x[1])
    n_below95  = sum(1 for _, v in sorted_av if v < 95)
    worst3_av  = ', '.join(f'{i} ({v:.1f}%)' for i, v in sorted_av[:3])
    high_mttf  = [(i, m) for i, m in mttf_res.items() if m['n_failures'] > 100]
    med_mttf   = [(i, m) for i, m in mttf_res.items() if 30 < m['n_failures'] <= 100]

    # ── Helper: draw a section block ──────────────────────────────
    def section(y_top, heading, paras, heading_col=None, indent=0.01):
        heading_col = heading_col or C['primary']
        ax.text(0, y_top, heading, fontsize=9.0, fontweight='bold',
                color=heading_col, va='top', transform=ax.transAxes)
        ax.plot([0, 1], [y_top - 0.017, y_top - 0.017],
                color=C['orange'], lw=0.8, transform=ax.transAxes)
        y = y_top - 0.028
        for para in paras:
            wrapped = _tw.fill(para, width=145)
            n_lines = wrapped.count('\n') + 1
            ax.text(indent, y, wrapped, fontsize=7.0, va='top', color='#1A1A1A',
                    transform=ax.transAxes, linespacing=1.28)
            y -= 0.023 * n_lines + 0.005
        return y - 0.006

    y = 0.99

    # ── 1. SCOPE ────────────────────────────────────────────────
    scope_para = (
        f"This report presents a comprehensive SCADA-based performance and reliability "
        f"analysis of {SITE_NAME} (La Brede) covering January 2023 – December 2024. "
        f"Data from {N_INVERTERS} Sungrow SG250HX inverters ({CAP_DC_KWP:,.0f} kWp DC / "
        f"{CAP_AC_KW:,.0f} kW AC) was processed at {INTERVAL_MIN}-min resolution against "
        f"SARAH-3 satellite irradiance references, following IEC 61724."
    )
    y = section(y, '1.  SCOPE', [scope_para])

    # ── 2. SITE PERFORMANCE ──────────────────────────────────────
    perf_paras = []
    for yr, row in annual.iterrows():
        gap_pct = max(0, 75 - row['PR'])
        gap_mwh = row['E_ref'] / 1e3 * gap_pct / 100 if row['PR'] < 75 else 0
        status_str = ('✔ meets the 75% design target.'
                      if row['PR'] >= 75
                      else f'▲ BELOW the 75% design target by {gap_pct:.1f} pp — '
                           f'equivalent to approximately {gap_mwh:.0f} MWh of recoverable annual production.')
        perf_paras.append(
            f"\u2022  {yr}: Site PR = {row['PR']:.1f}% on {row['irrad']:.0f} kWh/m² irradiation "
            f"→ {row['E_act']/1e6:.2f} GWh generated.  {status_str}"
        )
    perf_paras.append(
        f"\u2022  Average specific yield: {spec_yield:.0f} kWh/kWp/yr. "
        f"For First Solar CdTe modules in SW France the industry benchmark is 1,300–1,550 kWh/kWp/yr depending on irradiation. "
        f"{'✔ Within expected range.' if 1300 <= spec_yield <= 1550 else '▲ Outside expected range — investigate primary loss drivers.'}"
    )
    monthly = pr_res.get('monthly')
    if monthly is not None and len(monthly) > 0:
        n_below65 = sum(1 for v in monthly['PR'].values if v < 65)
        n_below75 = sum(1 for v in monthly['PR'].values if 65 <= v < 75)
        if n_below65 > 0 or n_below75 > 0:
            perf_paras.append(
                f"\u2022  Monthly breakdown: {n_below65} month(s) below the 65% alert threshold (severe underperformance) "
                f"and {n_below75} month(s) between 65–75%. "
                f"Months at <65% require detailed root-cause analysis — cross-reference with availability "
                f"and irradiance records to determine whether the primary driver is downtime, soiling, or a sensor artefact."
            )
    y = section(y, '2.  SITE PERFORMANCE', perf_paras)

    # ── 3. DATA & IRRADIANCE QUALITY ────────────────────────────
    dq_paras = []
    pwr_ok = data_avail['overall_power'] >= 95
    irr_da_ok = data_avail['irradiance'] >= 95
    dq_paras.append(
        f"\u2022  Power data completeness: {data_avail['overall_power']:.1f}%  |  "
        f"Irradiance completeness: {data_avail['irradiance']:.1f}%.  "
        + ('Both meet the 95% target.' if pwr_ok and irr_da_ok
           else 'One or both are below 95% — KPI figures for gap periods carry elevated uncertainty. '
                'Investigate SCADA logger connectivity, buffer size, and data export schedule.')
    )
    for name, d in irr_coh.items():
        _ok_coh = d['correlation'] > 0.95 and d['suspect_pct'] < 5
        ratio_note = (
            f"Ratio {d['mean_ratio']:.2f} > 1.10 — sensor reads systematically HIGH; "
            "verify mounting tilt and check for nearby reflective surfaces." if d['mean_ratio'] > 1.10
            else f"Ratio {d['mean_ratio']:.2f} < 0.90 — sensor reads LOW; likely dome soiling or partial shading; "
                 "clean and recalibrate immediately." if d['mean_ratio'] < 0.90
            else f"Ratio {d['mean_ratio']:.2f} — no systematic offset detected."
        )
        dq_paras.append(
            f"\u2022  Irradiance sensor vs SARAH_{name}: R = {d['correlation']:.3f}, "
            f"suspect readings = {d['suspect_pct']:.1f}%, gap days = {d['days_with_gaps']}. "
            + ('✔ Sensor coherent.  ' if _ok_coh else '▲ Sensor requires attention.  ')
            + ratio_note
        )
    y = section(y, '3.  DATA & IRRADIANCE QUALITY', dq_paras)

    # ── 4. AVAILABILITY & RELIABILITY ───────────────────────────
    ar_paras = [
        f"\u2022  Fleet mean availability: {avail_res['mean']:.1f}%  "
        f"({'✔ meets' if avail_res['mean'] >= 95 else '▲ below'} the 95% contractual threshold).  "
        f"{n_below95} of {len(avail_res['per_inverter'])} inverter(s) individually below 95%.  "
        f"Worst three: {worst3_av}.",
    ]
    if avail_res['whole_site_events'] > 0:
        ar_paras.append(
            f"\u2022  {avail_res['whole_site_events']} recorded period(s) where ALL {N_INVERTERS} inverters went offline simultaneously — "
            f"a pattern that cannot originate from individual inverter faults and is diagnostic of grid-level causes "
            f"(MV protection trip, frequency excursion, transformer fault). "
            f"Obtain MV protection relay trip logs and correlate with DSO (grid operator) disturbance records for each event date. "
            f"If the DSO confirms poor grid quality, request a power quality measurement campaign at the connection point."
        )
    if high_mttf:
        worst_mttf_inv = ', '.join(f'{i} ({m["n_failures"]} faults, MTTF={m["mttf_days"]:.1f}d)'
                                   for i, m in high_mttf[:4])
        ar_paras.append(
            f"\u2022  {len(high_mttf)} inverter(s) recorded >100 fault events (MTTF < 3 days): {worst_mttf_inv}. "
            f"Near-daily cycling places thermal and mechanical stress on power electronics and AC contactors. "
            f"Root cause must be determined — export Sungrow fault code log and engage Sungrow technical support. "
            f"Do NOT replace hardware until fault codes confirm the failure mode."
        )
    if med_mttf:
        ar_paras.append(
            f"\u2022  {len(med_mttf)} additional inverter(s) with 30–100 fault events (ORANGE — elevated trip frequency). "
            f"Schedule preventive inspection; review protection threshold settings (under-voltage, earth fault sensitivity) "
            f"against current grid connection agreement."
        )
    y = section(y, '4.  AVAILABILITY & RELIABILITY', ar_paras)

    # ── 5. ENERGY LOSS ANALYSIS ──────────────────────────────────
    wf_avail_pct = abs(wf['avail_loss']) / wf['budget'] * 100 if wf['budget'] > 0 else 0
    wf_tech_pct  = abs(wf['technical_loss']) / wf['budget'] * 100 if wf['budget'] > 0 else 0
    wf_actual_pct = wf['actual'] / wf['budget'] * 100 if wf['budget'] > 0 else 0
    recovery_mwh = abs(wf['avail_loss']) * 0.40

    el_paras = [
        f"\u2022  Actual production = {wf['actual']:.0f} MWh ({wf_actual_pct:.1f}% of weather-corrected budget). "
        f"Availability loss: {abs(wf['avail_loss']):.0f} MWh ({wf_avail_pct:.1f}% of budget). "
        f"Technical loss (underperformance while running): {abs(wf['technical_loss']):.0f} MWh ({wf_tech_pct:.1f}% of budget).",
        f"\u2022  Availability loss is O&M-recoverable. Improving maintenance response time and "
        f"implementing a preventive maintenance programme can typically recover 30–50% of this loss, "
        f"representing approximately {recovery_mwh:.0f} MWh/period at conservative estimates.",
        f"\u2022  Technical loss requires field investigation to decompose. The primary candidates are: "
        f"(1) module soiling — detectable by comparing pre/post-rain specific yield; "
        f"(2) string-level faults — identifiable through IV-curve measurement; "
        f"(3) MPPT detuning — visible as low specific yield with normal availability; "
        f"(4) DC wiring resistance — requires thermal imaging of junction boxes.",
    ]
    y = section(y, '5.  ENERGY LOSS ANALYSIS', el_paras)

    # ── 6. PRIORITY RECOMMENDATIONS ──────────────────────────────
    hi_items = [i for i in punchlist if i['priority'] == 'HIGH']
    rec_paras = [
        f"A total of {len(punchlist)} corrective actions identified ({hi_count} HIGH, {me_count} MEDIUM), "
        f"with combined estimated energy impact of {total_loss_mwh:.0f} MWh. "
        f"Addressing all HIGH-priority items is the recommended first phase of corrective action."
    ]
    for item in hi_items[:5]:
        mwh_str = f'  [{item.get("mwh_loss", 0):.0f} MWh est.]' if item.get('mwh_loss', 0) >= 1 else ''
        rec_paras.append(
            f"\u2022  [{item['category']}]{mwh_str}  {item['issue'][:100]}"
            + (f'  →  {item["action"][:80]}' if len(item.get('action', '')) > 0 else '')
        )
    if len(hi_items) > 5:
        rec_paras.append(f"\u2022  … and {len(hi_items)-5} further HIGH priority items — see Action Punchlist.")
    section(y, '6.  PRIORITY RECOMMENDATIONS', rec_paras, heading_col='#CC2200')

    pdf.savefig(fig, dpi=150)
    plt.close(fig)


def page_inv_specific_yield(pdf, inv_sy_df, punchlist, pg, piv=None, irr_data=None):
    """Per-inverter monthly performance — deviation heatmap (top) and PR heatmap (bottom).

    inv_sy_df  : DataFrame (index=month-end dates, columns=inverter names)
                 values in kWh/kWp (producing-hours normalised).
    piv        : full power pivot (needed to compute PR including downtime).
    irr_data   : irradiance DataFrame with 'ts' and 'GHI' columns.
    """
    if inv_sy_df is None or inv_sy_df.empty:
        return
    import textwrap as _tw

    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    _header_bar(fig, 'PER-INVERTER SPECIFIC YIELD BY MONTH')
    _footer(fig, pg)

    gs = GridSpec(2, 1, figure=fig, hspace=0.65,
                  top=0.90, bottom=0.18, left=0.11, right=0.93)

    # Sort columns in natural order
    cols_sorted = sorted(inv_sy_df.columns, key=_nat)
    df = inv_sy_df[cols_sorted].copy()

    # ── 1. Heatmap: % deviation from fleet mean (seasonality removed) ──
    ax1 = fig.add_subplot(gs[0])
    fleet_monthly = df.mean(axis=1)
    dev_pct = (df.subtract(fleet_monthly, axis=0)
               .divide(fleet_monthly.clip(lower=1), axis=0) * 100)
    mat = dev_pct.T.values   # shape: n_inv × n_months
    im = ax1.imshow(mat, aspect='auto', cmap='RdYlGn', vmin=-20, vmax=20,
                    interpolation='nearest')
    ax1.set_yticks(range(len(cols_sorted)))
    ax1.set_yticklabels(cols_sorted, fontsize=5.5)
    month_labels = [d.strftime('%b\n%y') for d in df.index]
    ax1.set_xticks(range(len(df.index)))
    ax1.set_xticklabels(month_labels, fontsize=6)
    plt.colorbar(im, ax=ax1, label='% vs fleet mean',
                 fraction=0.025, pad=0.01, shrink=0.8)
    ax1.set_title('Per-Inverter Yield Quality: Monthly Deviation from Fleet Mean (%)',
                  fontweight='bold', color=C['primary'])

    # ── 2. PR heatmap per inverter per month (includes downtime) ──────
    ax2 = fig.add_subplot(gs[1])
    pr_df = None
    if piv is not None and irr_data is not None and len(irr_data):
        inv_dc_kwp = CAP_DC_KWP / max(piv.shape[1], 1)
        ghi_s = irr_data.set_index('ts')['GHI'].reindex(piv.index)
        ghi_monthly = ghi_s.resample('ME').sum() * INTERVAL_H / 1000  # kWh/m²
        e_monthly_kwh = (piv * INTERVAL_H).resample('ME').sum()        # kWh
        denom = ghi_monthly * inv_dc_kwp
        pr_df = e_monthly_kwh.divide(denom, axis=0) * 100              # PR %
        pr_df = pr_df.clip(lower=0, upper=100)
        pr_df = pr_df[cols_sorted]

    if pr_df is not None and not pr_df.empty:
        pr_mat = pr_df.T.values   # shape: n_inv × n_months
        im2 = ax2.imshow(pr_mat, aspect='auto', cmap='RdYlGn', vmin=40, vmax=90,
                         interpolation='nearest')
        ax2.set_yticks(range(len(cols_sorted)))
        ax2.set_yticklabels(cols_sorted, fontsize=5.5)
        ax2.set_xticks(range(len(pr_df.index)))
        ax2.set_xticklabels([d.strftime('%b\n%y') for d in pr_df.index], fontsize=6)
        plt.colorbar(im2, ax=ax2, label='PR (%)', fraction=0.025, pad=0.01, shrink=0.8)
        ax2.set_title('Monthly PR per Inverter (%) — includes availability losses',
                      fontweight='bold', color=C['primary'])
    else:
        ax2.axis('off')
        ax2.text(0.5, 0.5, 'PR data unavailable', ha='center', va='center',
                 transform=ax2.transAxes, fontsize=9, color='grey')

    # ── KEY OBSERVATIONS — driven by punchlist ───────────────────
    _sy_rows = [{'sev': 'INFO',
                 'finding': "Top heatmap: YIELD QUALITY only — downtime excluded (running but underproducing). "
                            "Bottom heatmap: FULL PR including downtime — red = low PR from any cause (fault, trip, degradation).",
                 'action': 'Cross-reference both charts: red top + green bottom = quality loss; green top + red bottom = availability loss.'}]
    _sy_rows += [{'sev': r['priority'], 'finding': r['issue'], 'action': r['action']}
                 for r in punchlist if r['category'] == 'Inverter PR']
    _sy_rows.append({
        'sev': 'INFO',
        'finding': "If PR worsens Apr–Sep and recovers after autumn rain, soiling is the primary driver — "
                   "a structured cleaning programme (e.g. May and August) would recover production.",
        'action': 'Compare pre/post-rain PR to quantify soiling loss rate and ROI of cleaning.',
    })

    # Caption driven by PR heatmap
    if pr_df is not None and not pr_df.empty:
        pr_mean_per_inv  = pr_df.mean(axis=0)
        _sy_fleet_pr     = float(pr_df.stack().mean())
        _sy_worst3_pr    = [(inv, float(pr_mean_per_inv[inv]))
                            for inv in pr_mean_per_inv.nsmallest(3).index]
        _sy_n_low        = int((pr_mean_per_inv < _sy_fleet_pr - 5).sum())
        _sy_caption = (
            f"Analysis: Fleet mean PR across all inverters and months = {_sy_fleet_pr:.1f}%. "
            f"{_sy_n_low} inverter(s) average more than 5 pp below fleet mean. "
            + (f"Lowest average PR: {', '.join(f'{inv} ({pr:.1f}%)' for inv, pr in _sy_worst3_pr)}. "
               if _sy_worst3_pr else "")
            + "Bottom heatmap shows PR including downtime — a red month for an inverter means its total output "
            "(losses from both trips and quality degradation combined) was low relative to available irradiance. "
            "Top heatmap isolates quality loss by excluding downtime intervals: a red cell in the top heatmap "
            "means the inverter was running but underperforming its peers — likely soiling, string faults, or MPPT issues. "
            "Persistent red in summer months across both charts simultaneously indicates a structural problem, not a recoverable trip."
        )
    else:
        # Fallback to deviation-based caption when PR data unavailable
        worst_dev_pct = dev_pct.abs().max(axis=0)
        wdp_sorted = worst_dev_pct[cols_sorted]
        _sy_n_red    = int((wdp_sorted.values > 20).sum())
        _sy_n_orange = int(((wdp_sorted.values > 10) & (wdp_sorted.values <= 20)).sum())
        _sy_worst3   = [(cols_sorted[i], float(wdp_sorted.values[i]))
                        for i in np.argsort(wdp_sorted.values)[::-1][:3]]
        _sy_caption = (
            f"Analysis: {_sy_n_red} inverter(s) exceed the 20% worst-month deviation threshold and "
            f"{_sy_n_orange} exceed 10%. "
            + (f"Most impaired: {', '.join(f'{inv} ({dev:.1f}%)' for inv, dev in _sy_worst3)}. "
               if _sy_worst3 else "")
            + "Seasonality is removed — a red cell means that inverter underperformed its peers that month."
        )
    _page_insight(fig, _sy_rows, gs=gs, has_rotated_labels=False, caption=_sy_caption)

    pdf.savefig(fig, dpi=150)
    plt.close(fig)


def page_data_limitations(pdf, pg):
    """Annex: what analyses cannot be performed with the available SCADA data."""
    import textwrap as _tw

    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    _header_bar(fig, 'ANNEX — DATA LIMITATIONS & ANALYSIS CONSTRAINTS')
    _footer(fig, pg)

    ax = fig.add_axes([0.04, 0.09, 0.92, 0.82])
    ax.axis('off')
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)

    # Intro
    ax.text(0, 0.99,
            'The analyses presented in this report are limited by the data available in the SCADA export.\n'
            'The table below summarises what additional analyses would be possible if additional data channels\n'
            'or higher-resolution data were available.  Items marked ✗ cannot be performed with current data.',
            fontsize=7.5, va='top', color='#333333', transform=ax.transAxes, linespacing=1.5)

    rows = [
        # (Analysis, Status, Data Required / Reason)
        ('Inverter AC/DC efficiency',            '✗ Not possible',
         'Only AC power (PAC) logged; DC power, DC voltage & DC current channels not exported.'),
        ('String-level fault detection',         '✗ Not possible',
         'Only inverter-level AC power available; MPPT string-level data not in SCADA export.'),
        ('Inverter tripping events < 10 min',    '✗ Not possible',
         '10-min data resolution; requires ≤1-min SCADA or event-log file from inverter.'),
        ('Downtime root-cause classification',   '✗ Not possible',
         'No alarm / fault codes exported; only running/stopped state inferred from PAC.'),
        ('Soiling rate quantification',          '✗ Approximate only',
         'Requires regular IV-curve scans or bifacial soiling sensors; heatmap is indicative only.'),
        ('Transformer / MV losses',              '✗ Not possible',
         'No metering at PTR1/PTR2 secondary side; only inverter AC output is measured.'),
        ('Grid code compliance (PF, V, f)',      '✗ Not possible',
         'Reactive power (Q), grid voltage (V) and frequency (f) channels not in export.'),
        ('Module degradation rate (LID/PID)',    '✗ Insufficient data',
         'Less than 3 full calendar years of consistent data; degradation requires 3+ years.'),
        ('Weather-corrected PR (POA-based)',     '⚠ Satellite proxy only',
         'GHI measured on-site but no in-plane (POA) sensor; SARAH-3 satellite used as reference.'),
        ('Night-time consumption / standby',     '✗ Not possible',
         'AC metering only captures inverter output; no import/export meter data available.'),
        ('Clipping losses',                      '⚠ Indicative only',
         'Can be estimated from DC/AC ratio and irradiance, but requires DC power data for accuracy.'),
        ('Inter-inverter thermal variation',     '✗ Not possible',
         'No per-inverter module temperature; only one site-wide ambient/panel sensor.'),
    ]

    # Column x-positions: Analysis | Status | Reason
    # Status column widened to 0.17 (was 0.10) so longest label fits on one line
    COL_X   = [0.00, 0.28, 0.45]
    WRAP_AN = 38   # analysis column wrap (chars)
    WRAP_RE = 76   # reason column wrap (chars) — tuned to 0.55-wide column at 6pt

    # Dynamic row height: sized to the tallest wrapped cell in that row
    # LINE_H in axes-fraction units: 6.5pt × 1.25 linespacing / (axes_h × page_h_pt)
    LINE_H  = 6.5 * 1.25 / (0.82 * PAGE_H * 72)   # ≈ 0.01196 axes units per line
    ROW_PAD = 0.005                                  # top + bottom padding

    def _rh(analysis, reason):
        al = _tw.wrap(analysis, width=WRAP_AN) or ['']
        rl = _tw.wrap(reason,   width=WRAP_RE) or ['']
        return max(len(al), 1, len(rl)) * LINE_H + ROW_PAD

    # Table header
    hy = 0.84
    hdrs = ['Analysis / KPI', 'Status', 'Reason / Data Needed']
    for x, h in zip(COL_X, hdrs):
        ax.text(x, hy, h, fontsize=8, fontweight='bold', color='white',
                va='top', transform=ax.transAxes,
                bbox=dict(boxstyle='square,pad=0.1', facecolor=C['primary'],
                          edgecolor='none'))
    ax.plot([0.0, 1.0], [hy - 0.022, hy - 0.022],
            color=C['primary'], lw=1.5, transform=ax.transAxes)

    y = hy - 0.028
    for idx, (analysis, status, reason) in enumerate(rows):
        rh = _rh(analysis, reason)
        bg = '#F5F5F5' if idx % 2 == 0 else 'white'
        ax.add_patch(plt.Rectangle((0, y - rh), 1, rh,
                                   facecolor=bg, edgecolor='#E0E0E0', lw=0.4,
                                   transform=ax.transAxes))
        ok_col = C['green'] if '⚠' in status else C['red']
        cy = y - rh / 2   # vertical centre of this row

        al_text = '\n'.join(_tw.wrap(analysis, width=WRAP_AN) or [''])
        rl_text = '\n'.join(_tw.wrap(reason,   width=WRAP_RE) or [''])

        ax.text(COL_X[0], cy, al_text,
                fontsize=6.5, va='center', transform=ax.transAxes,
                linespacing=1.25)
        ax.text(COL_X[1], cy, status,
                fontsize=6.5, va='center', transform=ax.transAxes,
                color=ok_col, fontweight='bold')
        ax.text(COL_X[2], cy, rl_text,
                fontsize=6.0, va='center', transform=ax.transAxes,
                color='#444444', linespacing=1.25)
        y -= rh

    # Footer note
    ax.text(0.0, y - 0.015,
            'Note: Fault alarm codes (Sungrow SG250HX event log) would significantly improve '
            'root-cause classification of the downtime events identified in this report.\n'
            'Recommendation: configure SCADA export to include all alarm channels, DC power '
            '(PDC), and string-level MPPT data.',
            fontsize=7, va='top', color=C['primary'], transform=ax.transAxes,
            linespacing=1.4, style='italic')

    pdf.savefig(fig, dpi=150)
    plt.close(fig)


def page_punchlist(pdf, punchlist, pg):
    import textwrap
    priority_c = {'HIGH': C['red'], 'MEDIUM': '#FF8C00', 'LOW': C['green']}

    # Column x-positions (axes fraction):
    #   #=0.02  Priority=0.06  MWh=0.14  Category=0.22  Finding=0.39  Action=0.67
    # Wrap widths tuned to column widths (A4 @7pt Open Sans)
    # Finding col: 0.43–0.71 = 0.28 × 7.30" ≈ 2.0" → ~34 chars
    # Action col:  0.71–0.99 = 0.28 × 7.30" ≈ 2.0" → ~34 chars
    WRAP_I = 42   # finding/issue column  (+1 cm wider than before)
    WRAP_A = 42   # action column        (+1 cm wider than before)
    LINE_H = 0.014   # height per wrapped line (tight — fits 14 items on one page)
    PAD    = 0.002   # top/bottom padding inside each row

    def row_lines(issue, action):
        """Return (issue_lines, action_lines, total_row_height)."""
        il = textwrap.wrap(issue,  width=WRAP_I) or ['']
        al = textwrap.wrap(action, width=WRAP_A) or ['']
        n  = max(len(il), len(al))
        return il, al, n * LINE_H + PAD * 2

    # Pre-calculate row heights and page breaks
    chunks = []
    current, current_h = [], 0.0
    AVAILABLE = 0.88   # axes height fraction available for rows
    HEADER_H  = 0.055  # height consumed by column headers

    for item in punchlist or []:
        il, al, rh = row_lines(item['issue'], item['action'])
        if current and current_h + rh > AVAILABLE - HEADER_H:
            chunks.append(current)
            current, current_h = [], 0.0
        current.append((item, il, al, rh))
        current_h += rh
    if current:
        chunks.append(current)
    if not chunks:
        chunks = [[]]   # empty page for the "no actions" case

    for page_idx, chunk in enumerate(chunks):
        fig = plt.figure(figsize=(PAGE_W, PAGE_H))
        sub = f'Page {page_idx + 1}' if len(chunks) > 1 else ''
        _header_bar(fig, 'ACTION PUNCHLIST', sub)
        _footer(fig, pg)

        ax = fig.add_axes([0.03, 0.07, 0.94, 0.85])
        ax.axis('off'); ax.set_xlim(0, 1); ax.set_ylim(0, 1)

        if not punchlist:
            ax.text(0.5, 0.5, 'No critical actions identified.\n'
                    'Site operating within expected parameters.',
                    ha='center', va='center', fontsize=13, color=C['green'])
            pdf.savefig(fig, dpi=150)
            plt.close(fig)
            return

        # Column headers
        # Layout: #=0.01  Priority=0.05  MWh=0.11  €Loss=0.17  Category=0.23  Finding=0.33  Action=0.66
        # Finding and Action each +1 cm vs previous layout (space reclaimed from meta columns)
        hdr_y = 0.97
        for cx, lbl in [(0.01, '#'), (0.05, 'Priority'), (0.11, 'MWh'), (0.17, '€ Loss'),
                        (0.23, 'Category'), (0.33, 'Finding / Issue'),
                        (0.66, 'Recommended Action')]:
            ax.text(cx, hdr_y, lbl, fontsize=7, fontweight='bold',
                    color=C['primary'], va='top', transform=ax.transAxes)
        ax.plot([0.01, 0.99], [hdr_y - 0.020, hdr_y - 0.020],
                color=C['primary'], lw=1.5, transform=ax.transAxes, clip_on=False)

        y = hdr_y - HEADER_H

        for row_idx, (item, il, al, rh) in enumerate(chunk):
            if y - rh < 0.04:
                break
            num = (sum(len(c) for c in chunks[:page_idx]) + row_idx + 1)
            pri = item['priority']
            col = priority_c.get(pri, 'black')
            bg  = '#FFEAEA' if pri == 'HIGH' else ('#FFFBE6' if pri == 'MEDIUM' else 'white')

            # Row background
            ax.add_patch(plt.Rectangle((0.01, y - rh), 0.98, rh,
                                       facecolor=bg, edgecolor='#DDDDDD',
                                       lw=0.5, transform=ax.transAxes))
            # Meta fields – vertically centred on the row
            meta_y = y - rh / 2
            ax.text(0.01, meta_y, str(num), fontsize=6.5, fontweight='bold',
                    color=C['primary'], va='center', transform=ax.transAxes)
            ax.text(0.05, meta_y, pri, fontsize=6.5, fontweight='bold',
                    color=col, va='center', transform=ax.transAxes)
            # MWh loss column
            mwh = item.get('mwh_loss', 0.0)
            mwh_str = f'{mwh:.0f}' if mwh >= 1 else ('~0' if mwh == 0 else f'{mwh:.1f}')
            ax.text(0.11, meta_y, mwh_str, fontsize=6.5, fontweight='bold',
                    color=C['red'] if mwh > 50 else C['orange'] if mwh > 0 else '#888888',
                    va='center', transform=ax.transAxes)
            # Euro loss column (€0.10/kWh = €100/MWh)
            eur = mwh * 100.0
            eur_str = f'€{eur:,.0f}' if eur >= 100 else ('~€0' if eur == 0 else f'€{eur:.0f}')
            ax.text(0.17, meta_y, eur_str, fontsize=6.5, fontweight='bold',
                    color=C['red'] if eur > 5000 else C['orange'] if eur > 0 else '#888888',
                    va='center', transform=ax.transAxes)
            ax.text(0.23, meta_y, item['category'][:16], fontsize=6.5,
                    va='center', transform=ax.transAxes, clip_on=True)

            # Wrapped text lines – top-aligned within the row
            n_lines = max(len(il), len(al))
            for k in range(n_lines):
                line_y = y - PAD - k * LINE_H - LINE_H * 0.5
                if k < len(il):
                    ax.text(0.33, line_y, il[k], fontsize=6.5, va='center',
                            transform=ax.transAxes, clip_on=True)
                if k < len(al):
                    ax.text(0.66, line_y, al[k], fontsize=6.5, va='center',
                            transform=ax.transAxes, clip_on=True)

            y -= rh

        # Summary footer + tariff assumption note
        hi = sum(1 for i in punchlist if i['priority'] == 'HIGH')
        me = sum(1 for i in punchlist if i['priority'] == 'MEDIUM')
        lo = sum(1 for i in punchlist if i['priority'] == 'LOW')
        total_mwh_loss = sum(i.get('mwh_loss', 0) for i in punchlist)
        ax.text(0.5, 0.025,
                f'Total: {len(punchlist)} actions  |  HIGH: {hi}  |  MEDIUM: {me}  |  LOW: {lo}'
                f'  |  Est. total loss: {total_mwh_loss:.0f} MWh',
                ha='center', va='bottom', fontsize=7.5, fontweight='bold',
                color=C['primary'], transform=ax.transAxes)
        ax.text(0.5, 0.005,
                'Tariff assumption: €0.10/kWh (€100/MWh). '
                'MWh losses are independently estimated per category — availability and technical losses should not be summed directly.',
                ha='center', va='bottom', fontsize=6, color='#555555',
                style='italic', transform=ax.transAxes)

        pdf.savefig(fig, dpi=150)
        plt.close(fig)
        pg += 1


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  PVPAT SCADA Analysis Tool  -  Solar PV Performance Report")
    print("=" * 65)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / REPORT

    # ── Phase 1: Load data ───────────────────────────────────────
    print("\n[1/4] Loading data …")
    inv_data  = load_inverter_data()
    irr_data  = load_irradiance_data()
    sarah     = load_sarah_data()
    test_df   = load_test_csv()

    # ── Phase 2: Process ─────────────────────────────────────────
    print("\n[2/4] Processing …")
    piv_raw           = pivot_power(inv_data)
    cap_kw, inv_caps  = estimate_site_capacity(piv_raw, irr_data)
    # Clean stuck/frozen SCADA readings (e.g. OND1.6 stuck at 206.59 kW Oct-Nov 2023)
    piv, stuck_report = clean_stuck_values(piv_raw)
    if stuck_report:
        print(f"  NOTE: {len(stuck_report)} inverter(s) had stuck readings removed.")

    # ── Phase 3: Analyse ─────────────────────────────────────────
    print("\n[3/4] Analysing …")
    data_avail   = analyse_data_availability(piv, irr_data)
    pr_res       = analyse_pr(piv, irr_data, cap_kw)
    avail_res    = analyse_availability(piv, irr_data)
    irr_coh      = analyse_irradiance_coherence(irr_data, sarah)
    mttf_res     = analyse_mttf(piv, irr_data)
    inv_sy_df    = analyse_inv_specific_yield(piv, irr_data)
    start_stop_df = analyse_start_stop(piv, irr_data)
    wf           = build_waterfall(pr_res, irr_data, sarah, avail_res, cap_kw)
    punchlist    = generate_punchlist(avail_res, pr_res, irr_coh,
                                     mttf_res, data_avail, cap_kw, wf=wf,
                                     start_stop_df=start_stop_df)
    # Weather data (cached; skips gracefully if network unavailable)
    _wx_cache = OUT_DIR / 'weather_cache.json'
    weather_data = fetch_weather_data(_wx_cache)

    # ── Phase 4: Report ──────────────────────────────────────────
    print(f"\n[4/4] Generating PDF report -> {out_path}")

    with PdfPages(out_path) as pdf:
        pg = 1
        print(f"  Page {pg}: Cover …");
        page_cover(pdf);                                                             pg += 1
        print(f"  Page {pg}: Table of Contents …");
        page_contents(pdf);                                                          pg += 1
        print(f"  Page {pg}: Site Overview …");
        page_site_intro(pdf, pg);                                                    pg += 1
        print(f"  Page {pg}: Executive Summary …");
        _punchlist_pg = pg + 12 + (1 if weather_data else 0)   # DA+IC+PO+[wx]+IP+SY+AV+WF+MTTF(2)+SS+Conc+PL
        page_executive_summary(pdf, pr_res, avail_res, wf, data_avail,
                               cap_kw, punchlist, irr_coh, pg,
                               punchlist_pg=_punchlist_pg);                          pg += 1
        print(f"  Page {pg}: Data Availability …");
        page_data_availability(pdf, data_avail, piv, punchlist, pg);                pg += 1
        print(f"  Page {pg}: Irradiance Coherence …");
        page_irradiance_coherence(pdf, irr_coh, irr_data, test_df, punchlist, pg); pg += 1
        print(f"  Page {pg}: Performance Overview …");
        page_performance_overview(pdf, pr_res, piv, cap_kw, punchlist, pg);        pg += 1
        if weather_data:
            print(f"  Page {pg}: Weather Correlation …");
            page_weather_correlation(pdf, pr_res, weather_data, pg);               pg += 1
        print(f"  Page {pg}: Inverter Performance …");
        page_inverter_performance(pdf, pr_res, avail_res, inv_caps, punchlist, pg); pg += 1
        print(f"  Page {pg}: Per-Inverter Specific Yield …");
        page_inv_specific_yield(pdf, inv_sy_df, punchlist, pg,
                                piv=piv, irr_data=irr_data);                      pg += 1
        print(f"  Page {pg}: Availability …");
        page_availability(pdf, avail_res, piv, irr_data, punchlist, pg);            pg += 1
        print(f"  Page {pg}: Waterfall …");
        page_waterfall(pdf, wf, pr_res, avail_res, punchlist, pg);                  pg += 1
        print(f"  Page {pg}: MTTF charts …");
        page_mttf(pdf, mttf_res, punchlist, pg);                                    pg += 2
        print(f"  Page {pg}: Start/Stop Analysis …");
        page_start_stop(pdf, start_stop_df, pg);                                    pg += 1
        print(f"  Page {pg}: Conclusions …");
        page_conclusion(pdf, pr_res, avail_res, wf, data_avail,
                        mttf_res, punchlist, irr_coh, pg);                           pg += 1
        print(f"  Page {pg}: Punchlist …");
        page_punchlist(pdf, punchlist, pg);                                          pg += 1
        print(f"  Page {pg}: Data Limitations Annex …");
        page_data_limitations(pdf, pg)

        d = pdf.infodict()
        d['Title']        = f'{SITE_NAME} - SCADA Performance Analysis'
        d['Author']       = 'PVPAT Analysis Tool | Dolfines'
        d['Subject']      = 'Solar PV SCADA Analysis'
        d['CreationDate'] = datetime.now()

    # ── Summary ──────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print(f"  REPORT COMPLETE: {out_path}")
    print("=" * 65)
    annual = pr_res['annual']
    for yr, row in annual.iterrows():
        print(f"  {yr}: PR={row['PR']:.1f}%  Energy={row['E_act']/1e6:.3f} GWh  "
              f"Irrad={row['irrad']:.0f} kWh/m²")
    print(f"  Mean availability  : {avail_res['mean']:.1f}%")
    print(f"  Data availability  : {data_avail['overall_power']:.1f}%")
    print(f"  AC capacity        : {CAP_AC_KW:.0f} kW  |  DC: {CAP_DC_KWP:.0f} kWp")
    hi = sum(1 for i in punchlist if i['priority']=='HIGH')
    me = sum(1 for i in punchlist if i['priority']=='MEDIUM')
    print(f"  Punchlist          : {len(punchlist)} items  ({hi} HIGH, {me} MEDIUM)")
    print("=" * 65)


if __name__ == '__main__':
    main()
