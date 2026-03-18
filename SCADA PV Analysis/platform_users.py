"""
platform_users.py — Demo user & site configuration for PVPAT Platform
======================================================================
Replace / extend with a proper DB or Secrets store before production.
"""

# ── Demo credentials ──────────────────────────────────────────────────────
USERS = {
    "demo@dolfines.com": {
        "password": "pvpat2024",
        "display_name": "Demo User",
        "company": "Dolfines / 8p2 Advisory",
        "plan": "unlimited",          # "one_shot" | "unlimited"
        "sites": ["SOHMEX"],
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
        "n_inverters": 31,
        "inv_ac_kw": 250.0,
        "cap_ac_kw": 7750.0,
        "cap_dc_kwp": 9844.92,
        "n_modules": 21_402,
        "module_wp": 460.0,
        "dc_ac_ratio": 1.27,
        "design_pr": 0.80,
        "operating_pr_target": 0.79,
        "interval_min": 10,
        "irr_threshold": 50.0,
        "power_threshold": 5.0,
        # Paths to the SCADA data files (absolute, on local machine)
        "data_dir": r"C:\Users\RichardMUSI\OneDrive - Dolfines\Bureau\AI\dolfines-data-services-products\SCADA PV Analysis\00orig",
        "status": "operational",       # operational | maintenance | offline
        "lat": 48.8,
        "lon": 6.1,
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
