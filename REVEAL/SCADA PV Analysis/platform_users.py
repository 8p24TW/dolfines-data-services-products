"""
platform_users.py — Demo user & site configuration for PVPAT Platform
======================================================================
Replace / extend with a proper DB or Secrets store before production.
"""

from pathlib import Path


def _find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    return current.parents[2]


REPO_ROOT = _find_repo_root()
SCADA_PV_ROOT = REPO_ROOT / "REVEAL" / "SCADA PV Analysis"

# ── Demo credentials ──────────────────────────────────────────────────────
USERS = {
    "demo@dolfines.com": {
        "password": "pvpat2024",
        "display_name": "Demo User",
        "company": "Dolfines / 8p2 Advisory",
        "plan": "unlimited",          # "one_shot" | "unlimited"
        "sites": ["SOHMEX", "VENTOUX_PV", "LIMOUSIN_WIND", "NORMANDIE_PV"],
    },
    "client@solar-co.com": {
        "password": "solar2024",
        "display_name": "Solar Co. Manager",
        "company": "Solar Co.",
        "plan": "unlimited",
        "sites": ["SOHMEX"],
    },
}

# ── Site definitions ──────────────────────────────────────────────────────
SITES = {
    "SOHMEX": {
        "display_name": "SOHMEX Solar Farm",
        "country": "France",
        "region": "Grand Est",
        "cod": "01/06/2022",
        "technology": "CdTe (First Solar Series 6)",
        "inverter_model": "Sungrow SG250HX",
        "n_inverters": 21,
        "inv_ac_kw": 250.0,
        "cap_ac_kw": 5250.0,
        "cap_dc_kwp": 4977.0,
        "n_modules": 10_815,
        "module_wp": 460.0,
        "dc_ac_ratio": 0.948,
        "design_pr": 0.80,
        "operating_pr_target": 0.79,
        "interval_min": 10,
        "irr_threshold": 50.0,
        "power_threshold": 5.0,
        # Paths to the SCADA data files (absolute, on local machine)
        "data_dir": str(SCADA_PV_ROOT / "00orig"),
        "site_type": "solar",
        "status": "operational",       # operational | maintenance | offline
        "lat": 48.8,
        "lon": 6.1,
    },
    "VENTOUX_PV": {
        "display_name": "Ventoux Solaire",
        "country": "France",
        "region": "Provence-Alpes-Côte d'Azur",
        "cod": "15/03/2021",
        "technology": "Mono PERC (Jinko Tiger)",
        "inverter_model": "Huawei SUN2000-100KTL",
        "n_inverters": 120,
        "inv_ac_kw": 100.0,
        "cap_ac_kw": 12_000.0,
        "cap_dc_kwp": 12_480.0,
        "n_modules": 27_200,
        "module_wp": 459.0,
        "dc_ac_ratio": 1.04,
        "design_pr": 0.81,
        "operating_pr_target": 0.80,
        "interval_min": 15,
        "irr_threshold": 50.0,
        "power_threshold": 5.0,
        "data_dir": "",
        "site_type": "solar",
        "status": "operational",
        "lat": 44.1,
        "lon": 5.3,
    },
    "LIMOUSIN_WIND": {
        "display_name": "Parc Éolien du Limousin",
        "country": "France",
        "region": "Nouvelle-Aquitaine",
        "cod": "01/11/2019",
        "technology": "Vestas V136-4.5 MW",
        "inverter_model": "—",
        "n_inverters": 4,
        "inv_ac_kw": 4_500.0,      # kW per turbine
        "cap_ac_kw": 18_000.0,
        "cap_dc_kwp": 18_000.0,    # reused field — kW for wind
        "n_modules": 0,
        "module_wp": 0.0,
        "dc_ac_ratio": 1.0,
        "design_pr": 0.94,
        "operating_pr_target": 0.92,
        "interval_min": 10,
        "irr_threshold": 0.0,
        "power_threshold": 10.0,
        "data_dir": "",
        "site_type": "wind",
        "status": "maintenance",
        "lat": 45.8,
        "lon": 1.9,
        # Wind-specific technical data
        "hub_height_m": 112,
        "tip_height_m": 180,       # hub + rotor_radius (136/2 = 68 m)
        "rotor_diameter_m": 136,
        "expected_aep_gwh": 52.4,  # Annual Energy Production
    },
    "NORMANDIE_PV": {
        "display_name": "Normandie Agri-PV",
        "country": "France",
        "region": "Normandie",
        "cod": "20/07/2023",
        "technology": "Bifacial (LONGi Hi-MO 6)",
        "inverter_model": "SMA Sunny Tripower CORE2",
        "n_inverters": 50,
        "inv_ac_kw": 150.0,
        "cap_ac_kw": 7_500.0,
        "cap_dc_kwp": 7_560.0,
        "n_modules": 16_000,
        "module_wp": 472.5,
        "dc_ac_ratio": 1.01,
        "design_pr": 0.79,
        "operating_pr_target": 0.78,
        "interval_min": 15,
        "irr_threshold": 50.0,
        "power_threshold": 5.0,
        "data_dir": "",
        "site_type": "solar",
        "status": "operational",
        "lat": 49.2,
        "lon": 0.4,
    },
}

# ── Pricing ───────────────────────────────────────────────────────────────
PRICING = {
    "one_shot": {
        "label": "One-Shot Report",
        "price_eur": 3_500,
        "description": "Single comprehensive analysis report for one site.",
    },
    "unlimited": {
        "label": "Platform Access — Unlimited Reports",
        "price_eur_month": 1_000,
        "description": "Unlimited daily & comprehensive reports for all your sites.",
    },
}
