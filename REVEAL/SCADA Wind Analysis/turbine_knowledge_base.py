"""
turbine_knowledge_base.py
─────────────────────────
Structured database of known operational issues, component weaknesses, and
recommended corrective actions for major industrial wind turbines (≥ 800 kW).

Sources: published O&M studies, manufacturer service bulletins (public domain),
industry failure-rate databases (ReliaWind, SPARTA, ECN/TNO reports), and
accumulated field-engineering experience.

Structure
─────────
TURBINE_DB  dict keyed by  "<manufacturer>/<model_id>"
Each entry contains:
  - meta         : commercial and technical specification
  - known_issues : list of documented failure modes with severity + recommendation
  - strengths    : notable design advantages
  - monitoring   : KPIs and channels to prioritise for this model

Severity  HIGH   = failure likely within 2 years if unaddressed; high revenue impact
          MEDIUM = latent degradation; address within next planned service
          LOW    = minor; monitor and log
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def lookup(manufacturer: str, model_id: str) -> dict | None:
    """Return the knowledge-base entry for a specific turbine, or None."""
    return TURBINE_DB.get(f"{manufacturer.lower()}/{model_id.lower()}")


def lookup_by_rated_kw(manufacturer: str, rated_kw: float, tolerance_pct: float = 8.0) -> list[dict]:
    """Return all entries for a manufacturer whose rated power is within tolerance_pct."""
    results = []
    prefix = manufacturer.lower() + "/"
    for key, entry in TURBINE_DB.items():
        if key.startswith(prefix):
            r = entry["meta"]["rated_kw"]
            if abs(r - rated_kw) / max(rated_kw, 1) * 100 <= tolerance_pct:
                results.append(entry)
    return results


def best_match(manufacturer: str, rated_kw: float) -> dict | None:
    """Return the closest-matching entry for a manufacturer by rated power."""
    prefix = manufacturer.lower() + "/"
    candidates = {k: v for k, v in TURBINE_DB.items() if k.startswith(prefix)}
    if not candidates:
        return None
    return min(candidates.values(), key=lambda e: abs(e["meta"]["rated_kw"] - rated_kw))


# ─────────────────────────────────────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────────────────────────────────────

TURBINE_DB: dict[str, dict] = {

    # ══════════════════════════════════════════════════════════════════════════
    # NORDEX
    # ══════════════════════════════════════════════════════════════════════════

    "nordex/n90_2500": {
        "meta": {
            "manufacturer": "Nordex",
            "model": "N90/2500",
            "rated_kw": 2500,
            "rotor_m": 90,
            "iec_class": "IA/IIA",
            "drivetrain": "3-stage gearbox + DFIG",
            "years_produced": "2004–2012",
        },
        "known_issues": [
            {
                "component": "Gearbox – high-speed shaft bearing",
                "issue": "Premature spalling of the HSS cylindrical roller bearing, accelerated by lubricant contamination and axial load excursions in turbulent sites.",
                "severity": "HIGH",
                "frequency": "~25% of units by year 8",
                "recommendation": "Magnetic oil-plug checks every 6 months; vibration-based bearing monitoring; plan gearbox exchange campaign at year 8–10.",
            },
            {
                "component": "Main bearing (rotor)",
                "issue": "Single spherical roller main bearing shows raceway fatigue in high-wind-shear sites due to combined radial and axial loading.",
                "severity": "HIGH",
                "recommendation": "Annual grease analysis; consider CMS accelerometer on main bearing housing; budget for main bearing replacement within 12-year lifecycle.",
            },
            {
                "component": "Blade trailing edge – root section",
                "issue": "Adhesive bond disbonding at trailing edge between 5–15 m from root, driven by rain erosion and thermal cycling.",
                "severity": "MEDIUM",
                "recommendation": "Drone inspection every 2 years; apply leading-edge protection tape; repair bond lines with approved structural adhesive during annual service.",
            },
            {
                "component": "Yaw drive – gear ring",
                "issue": "Lubricant starvation on the yaw gear ring tooth faces at high-yaw-rate sites, leading to pitting.",
                "severity": "MEDIUM",
                "recommendation": "Increase lubrication interval to every 500 hours; inspect ring gear tooth contact pattern annually.",
            },
        ],
        "strengths": [
            "Robust nacelle structure suitable for high-turbulence Class IA sites.",
            "Well-documented service history with widely available spare parts.",
        ],
        "monitoring": [
            "Gearbox oil temperature differential (in vs out)",
            "HSS bearing vibration (RMS and kurtosis)",
            "Main bearing grease sample every 6 months",
            "Yaw motor current vs nacelle position",
        ],
    },

    "nordex/n100_2500": {
        "meta": {
            "manufacturer": "Nordex",
            "model": "N100/2500",
            "rated_kw": 2500,
            "rotor_m": 100,
            "iec_class": "IIA/IIIA",
            "drivetrain": "3-stage gearbox + DFIG",
            "years_produced": "2009–2015",
        },
        "known_issues": [
            {
                "component": "Gearbox – intermediate shaft bearing",
                "issue": "IMS bearing inner race micropitting noted in early production batches, linked to inadequate EP additive concentration.",
                "severity": "HIGH",
                "recommendation": "Oil sample analysis (ferrography) every 500 operating hours; upgrade to OEM-approved oil grade with enhanced EP additives.",
            },
            {
                "component": "Blade – leading edge erosion",
                "issue": "Above-average erosion rate at tip speeds ~80 m/s in sites with annual rainfall > 900 mm.",
                "severity": "MEDIUM",
                "recommendation": "Apply leading-edge erosion protection system (LEAPS) by year 3; inspect annually with drone.",
            },
            {
                "component": "Converter – IGBT module",
                "issue": "Thermal cycling fatigue of IGBT bond wires in converter cabinets, causing intermittent overcurrent trips.",
                "severity": "MEDIUM",
                "recommendation": "Converter thermal imaging during annual service; replace IGBT modules at first sign of bond-wire lift.",
            },
        ],
        "strengths": [
            "Larger rotor improves low-wind-site performance significantly vs N90.",
            "Compatible with N90 nacelle major assemblies reducing spare-parts stock.",
        ],
        "monitoring": [
            "Gearbox vibration (IMS bearing)",
            "IGBT junction temperatures via SCADA",
            "Blade leading-edge condition (annual drone)",
        ],
    },

    "nordex/n131_3900": {
        "meta": {
            "manufacturer": "Nordex",
            "model": "N131/3900 (Delta4000)",
            "rated_kw": 3900,
            "rotor_m": 131,
            "iec_class": "IIA",
            "drivetrain": "3-stage gearbox (medium-speed) + PMSG (AeroTwin drive)",
            "years_produced": "2017–present",
        },
        "known_issues": [
            {
                "component": "Pitch system – inverter PCB",
                "issue": "Early production (2017–2019) batches of the pitch inverter PCBs exhibited capacitor electrolyte drying, causing pitch axis faults and emergency stops. Service bulletin issued.",
                "severity": "HIGH",
                "frequency": "Reported in ~30% of early-batch units by year 3",
                "recommendation": "Verify service bulletin NX-SB-XXXX application status; replace affected PCBs during next planned maintenance if not already done. Check SCADA for frequency of 'Pitch fault' messages per turbine.",
            },
            {
                "component": "Main bearing – front main bearing",
                "issue": "The N131 uses a 3-point suspension with a single large-diameter main bearing. Micro-pitting observed in units operating in elevated turbulence (TI > 14%) sites.",
                "severity": "HIGH",
                "recommendation": "Grease analysis every 6 months; install acoustic emission sensor on main bearing housing; plan inspection at year 5. Turbulence-adaptive pitch scheduling (if available via OEM update) reduces main bearing loads.",
            },
            {
                "component": "Gearbox – planet stage carrier",
                "issue": "Planet carrier pin bore wear observed in a proportion of units at year 4–6, leading to gear contact misalignment and accelerated tooth wear on ring gear.",
                "severity": "HIGH",
                "recommendation": "Borescope inspection of planet stage at 40,000-hour interval; oil ferrography for metallic particles; budget for gearbox exchange at year 8–10.",
            },
            {
                "component": "Blade – trailing edge bond (root 0–20 m)",
                "issue": "Adhesive bond fatigue at the trailing edge panel joint between 5–20 m from root, consistent with high flap-wise bending cycles in turbulent inflow.",
                "severity": "MEDIUM",
                "recommendation": "Annual drone inspection focusing on root section trailing edge; early-stage disbonding is repairable in-situ; late-stage requires factory repair.",
            },
            {
                "component": "Blade – leading edge erosion (tip)",
                "issue": "Polyurethane leading edge coating erosion accelerates above tip speed 85 m/s in sites with high-frequency rain events, causing AEP losses of 0.5–1.5% per year.",
                "severity": "MEDIUM",
                "recommendation": "Apply leading-edge protection (LEP) shells or tape system by year 2–3; annual drone inspection from year 2 onwards.",
            },
            {
                "component": "Converter – water-cooling pump",
                "issue": "The Delta4000 uses a liquid-cooled converter; impeller wear and coolant hose micro-cracks have caused unplanned shutdowns.",
                "severity": "MEDIUM",
                "recommendation": "Coolant system inspection and pressure test annually; replace pump impellers at 30,000-hour interval; check coolant inhibitor concentration.",
            },
            {
                "component": "Nacelle – vibration alarm sensitivity",
                "issue": "Vibration monitoring thresholds set conservatively from factory; nuisance trips from rotor imbalance after blade icing events.",
                "severity": "LOW",
                "recommendation": "Calibrate vibration thresholds to site-specific baseline after first winter season; implement blade heating system if ice accretion expected > 100 h/year.",
            },
        ],
        "strengths": [
            "High annual energy yield at IEC IIA sites due to 131 m rotor and optimised blade profile.",
            "Medium-speed PMSG drivetrain eliminates slip rings and reduces generator maintenance vs DFIG.",
            "Integrated condition monitoring system (CMS) with standard SCADA export.",
            "Service bulletin ecosystem is active with regular OEM updates.",
        ],
        "monitoring": [
            "Pitch fault event rate per turbine per month (target < 1 per turbine/month)",
            "Main bearing temperature trend (flag if rising > 2°C/month)",
            "Gearbox oil particle count (NAS 7 target in service)",
            "Converter coolant system pressure (flag any loss > 0.2 bar/day)",
            "Blade leading-edge condition index (drone annual)",
            "Rotor imbalance indicator (vibration RMS, nacelle accelerometer)",
        ],
    },

    "nordex/n149_4500": {
        "meta": {
            "manufacturer": "Nordex",
            "model": "N149/4500 (Delta4000)",
            "rated_kw": 4500,
            "rotor_m": 149,
            "iec_class": "IIA/IIIA",
            "drivetrain": "3-stage gearbox (medium-speed) + PMSG",
            "years_produced": "2019–present",
        },
        "known_issues": [
            {
                "component": "Pitch system – inverter PCB",
                "issue": "Same early-batch PCB issue as N131; check service bulletin status.",
                "severity": "HIGH",
                "recommendation": "Confirm SB application; schedule PCB replacement if outstanding.",
            },
            {
                "component": "Blade – root trailing edge",
                "issue": "Larger blade chord increases bending moment at root; trailing edge disbond risk elevated vs N131.",
                "severity": "MEDIUM",
                "recommendation": "Annual drone inspection with focus on 0–25 m from root; consider accelerated inspection cycle in high-turbulence sites.",
            },
            {
                "component": "Foundation – dynamic loading",
                "issue": "149 m rotor increases tower base fatigue cycles; earlier 80 m hub-height towers may be under-designed for full AEP life.",
                "severity": "MEDIUM",
                "recommendation": "Commission fatigue analysis if original design assumed smaller rotor; inspect anchor bolts and grout condition at year 5.",
            },
        ],
        "strengths": [
            "Excellent IEC IIIA/low-wind performance with 149 m rotor.",
            "Compatible with N131 nacelle major assemblies.",
        ],
        "monitoring": [
            "Same as N131, plus tower base acceleration monitoring.",
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # VESTAS
    # ══════════════════════════════════════════════════════════════════════════

    "vestas/v80_2000": {
        "meta": {
            "manufacturer": "Vestas",
            "model": "V80-2.0 MW",
            "rated_kw": 2000,
            "rotor_m": 80,
            "iec_class": "IA/IIA",
            "drivetrain": "3-stage gearbox + DFIG (OptiSlip)",
            "years_produced": "2000–2010",
        },
        "known_issues": [
            {
                "component": "Gearbox – planet carrier",
                "issue": "Planet carrier pin fractures in the first planetary stage, particularly in turbulent sites; widespread failure mode documented in multiple markets.",
                "severity": "HIGH",
                "recommendation": "Oil particle count monitoring every 500 hours; plan gearbox exchange campaign if unit age > 12 years; dedicated planetary CMS channel.",
            },
            {
                "component": "Blade – trailing edge split",
                "issue": "Gel-coat cracking and trailing edge panel separation, accelerated in coastal/erosive environments.",
                "severity": "HIGH",
                "recommendation": "Annual visual inspection; repair any open cracks within 3 months to prevent moisture ingress and structural progression.",
            },
            {
                "component": "Main bearing",
                "issue": "Double-row spherical roller main bearing shows early fatigue in Class IA turbulent sites; documented in ReliaWind dataset.",
                "severity": "HIGH",
                "recommendation": "Vibration monitoring of main bearing; grease sample every 6 months; budget replacement by year 10.",
            },
            {
                "component": "Blade – root bushing",
                "issue": "T-bolt root fastener loosening due to composite fatigue, leading to blade wobble and vibration alarms.",
                "severity": "MEDIUM",
                "recommendation": "Root bolt torque check at each annual service; apply thread-locking compound per OEM specification.",
            },
        ],
        "strengths": [
            "Very large fleet size means abundant spare parts availability and well-documented service procedures.",
            "Robust track record in high-wind IA sites.",
        ],
        "monitoring": [
            "Gearbox planet stage vibration",
            "Main bearing temperature and vibration",
            "Blade root bolt torque (physical check annually)",
        ],
    },

    "vestas/v90_3000": {
        "meta": {
            "manufacturer": "Vestas",
            "model": "V90-3.0 MW",
            "rated_kw": 3000,
            "rotor_m": 90,
            "iec_class": "IA/IIA",
            "drivetrain": "3-stage gearbox + DFIG",
            "years_produced": "2004–2013",
        },
        "known_issues": [
            {
                "component": "Main bearing",
                "issue": "Non-drive-end main bearing inner-race spalling, documented in SPARTA database as one of the highest-frequency failure modes for this model.",
                "severity": "HIGH",
                "frequency": "~35% of units by year 10",
                "recommendation": "CMS accelerometer mandatory; grease analysis every 6 months; first replacement typically years 7–9.",
            },
            {
                "component": "Gearbox – oil seal leak",
                "issue": "High-pressure oil seal failures at the gearbox HSS output shaft, causing nacelle contamination and fire risk.",
                "severity": "HIGH",
                "recommendation": "Inspect seal condition at every annual service; replace at first sign of weeping; ensure fire suppression system is functional.",
            },
            {
                "component": "Blade – root crack",
                "issue": "Longitudinal cracks in the blade shell at the root cylinder junction under high fatigue loading.",
                "severity": "HIGH",
                "recommendation": "Annual crack survey with hammer tap-testing from root to 5 m; any crack > 150 mm warrants immediate inspection and repair.",
            },
            {
                "component": "Transformer – winding insulation",
                "issue": "Nacelle transformer winding insulation failure in high-humidity environments; accelerated by frequent start-stop cycles.",
                "severity": "MEDIUM",
                "recommendation": "Insulation resistance test at annual service; DGA if moisture ingress suspected.",
            },
        ],
        "strengths": [
            "Well-proven in high-wind IEC IA sites.",
            "Active OEM service network and available refurbishment packages.",
        ],
        "monitoring": [
            "Main bearing vibration RMS and kurtosis",
            "Gearbox oil temperature and seal inspection",
            "Blade root annual inspection",
        ],
    },

    "vestas/v112_3300": {
        "meta": {
            "manufacturer": "Vestas",
            "model": "V112-3.3/3.45 MW",
            "rated_kw": 3450,
            "rotor_m": 112,
            "iec_class": "IIA/IIIA",
            "drivetrain": "3-stage gearbox + PMSG (ECO)",
            "years_produced": "2010–2018",
        },
        "known_issues": [
            {
                "component": "Main shaft bearing – front",
                "issue": "Tapered roller front main bearing shows inner-race spalling in sites with high yaw misalignment, linked to combined axial-radial overloads.",
                "severity": "HIGH",
                "recommendation": "Nacelle anemometry audit; correct persistent yaw offset > 5°; CMS monitoring; budget main bearing replacement at year 8.",
            },
            {
                "component": "Yaw bearing – raceway",
                "issue": "Yaw bearing raceway surface pitting reported in turbulent sites; insufficient lubrication intervals exacerbate the issue.",
                "severity": "MEDIUM",
                "recommendation": "Yaw bearing grease every 500 hours; inspect raceway and gear teeth at annual service; replace yaw bearing by year 12.",
            },
            {
                "component": "Blade – trailing edge (mid-span)",
                "issue": "Trailing edge bond disbonding between 25–45 m from root under high fatigue loading cycles.",
                "severity": "MEDIUM",
                "recommendation": "Drone inspection bi-annually; trailing edge repair kits available from OEM.",
            },
            {
                "component": "ECO drivetrain – coupling",
                "issue": "Flexible coupling between medium-speed gearbox and PMSG shows wear at higher-than-expected rates in high-turbulence sites.",
                "severity": "MEDIUM",
                "recommendation": "Coupling inspection every 20,000 hours; replace elastomeric elements per OEM interval.",
            },
        ],
        "strengths": [
            "PMSG eliminates slip rings; lower generator maintenance cost vs DFIG.",
            "Good track record in medium-wind IEC IIA/IIIA sites.",
        ],
        "monitoring": [
            "Main bearing front vibration and temperature",
            "Yaw bearing condition (audio/vibration sensor)",
            "Coupling alignment check annually",
        ],
    },

    "vestas/v150_4500": {
        "meta": {
            "manufacturer": "Vestas",
            "model": "V150-4.5 MW",
            "rated_kw": 4500,
            "rotor_m": 150,
            "iec_class": "IIA/IIIA",
            "drivetrain": "3-stage gearbox + PMSG",
            "years_produced": "2018–present",
        },
        "known_issues": [
            {
                "component": "Blade – ice accretion",
                "issue": "Large rotor surface area increases susceptibility to ice accretion in continental sites; IPS (Integrated Protection System) blade heating has shown intermittent failures in early fleet.",
                "severity": "MEDIUM",
                "recommendation": "Verify IPS functionality before each winter season; review loss accounting for icing events.",
            },
            {
                "component": "Blade – trailing edge erosion",
                "issue": "Tip speed ~88 m/s at rated; leading and trailing edge erosion accelerated in sites with high rain intensity.",
                "severity": "MEDIUM",
                "recommendation": "Leading-edge protection by year 2; annual drone inspection.",
            },
            {
                "component": "Foundation – dynamic loading",
                "issue": "150 m rotor on 105 m hub-height towers significantly increases foundation fatigue loads; grout erosion at pedestal in clay-rich soils.",
                "severity": "MEDIUM",
                "recommendation": "Annual foundation visual inspection and monitoring extensometers; grout integrity test every 5 years.",
            },
        ],
        "strengths": [
            "Best-in-class AEP at IEC IIIA low-wind sites.",
            "Advanced control system with sector management capability.",
        ],
        "monitoring": [
            "Blade heating system status (IPS)",
            "Foundation accelerometers or strain gauges",
            "Tower natural frequency trend (detect foundation softening)",
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SIEMENS GAMESA (SG)  — includes legacy Siemens and legacy Gamesa lines
    # ══════════════════════════════════════════════════════════════════════════

    "siemens-gamesa/g80_2000": {
        "meta": {
            "manufacturer": "Gamesa (now SG)",
            "model": "G80-2.0 MW",
            "rated_kw": 2000,
            "rotor_m": 80,
            "iec_class": "IIA",
            "drivetrain": "3-stage gearbox + DFIG",
            "years_produced": "2005–2015",
        },
        "known_issues": [
            {
                "component": "Gearbox – all stages",
                "issue": "The G80 gearbox has one of the highest failure rates documented in European O&M databases; planet carrier pin fatigue, IMS bearing spalling, and HSS seal failures are all common.",
                "severity": "HIGH",
                "frequency": "~40% of units require gearbox exchange by year 8",
                "recommendation": "Implement online oil particle monitoring; plan gearbox refurbishment campaign; negotiate frame agreement with gearbox reconditioner.",
            },
            {
                "component": "Pitch system – hydraulic actuator",
                "issue": "Hydraulic pitch actuator seal degradation leads to pitch axis sluggishness, which increases blade root loads and triggers overspeed events.",
                "severity": "HIGH",
                "recommendation": "Hydraulic fluid sampling every 1,000 hours; seal kit replacement every 3 years; verify pitch response time at annual service.",
            },
            {
                "component": "Main bearing",
                "issue": "Raceway spalling on inner ring under combined loading; exacerbated by shaft deflection from rotor imbalance.",
                "severity": "HIGH",
                "recommendation": "Annual vibration measurement and trending; replace at first sign of noise or particle generation.",
            },
        ],
        "strengths": [
            "Large fleet installed across Southern Europe; good local supply chain.",
        ],
        "monitoring": [
            "Gearbox online particle monitoring (mandatory)",
            "Hydraulic pressure and temperature",
            "Main bearing CMS channel",
        ],
    },

    "siemens-gamesa/g114_2100": {
        "meta": {
            "manufacturer": "Gamesa (now SG)",
            "model": "G114-2.1 MW",
            "rated_kw": 2100,
            "rotor_m": 114,
            "iec_class": "IIA/IIIA",
            "drivetrain": "3-stage gearbox + DFIG",
            "years_produced": "2012–2018",
        },
        "known_issues": [
            {
                "component": "Gearbox – IMS bearing",
                "issue": "IMS cylindrical roller bearing inner race fatigue; same root cause as G80 but somewhat reduced frequency due to redesigned oil circuit.",
                "severity": "HIGH",
                "recommendation": "Oil ferrography every 500 hours; CMS IMS bearing channel.",
            },
            {
                "component": "Blade – leading edge erosion",
                "issue": "High tip speed (~84 m/s) accelerates leading-edge coat erosion, particularly in Atlantic coastal sites.",
                "severity": "MEDIUM",
                "recommendation": "Leading-edge protection by year 3; annual drone inspection.",
            },
            {
                "component": "Converter – grid-fault ride-through",
                "issue": "Intermittent Low Voltage Ride Through (LVRT) failures cause disconnections during grid disturbances.",
                "severity": "MEDIUM",
                "recommendation": "Firmware update per SG service bulletin; test LVRT capability annually with test equipment.",
            },
        ],
        "strengths": [
            "Larger rotor vs G80 significantly improves low-wind performance.",
        ],
        "monitoring": [
            "Gearbox IMS vibration",
            "LVRT event log monitoring",
        ],
    },

    "siemens-gamesa/swt2.3": {
        "meta": {
            "manufacturer": "Siemens (now SG)",
            "model": "SWT-2.3-82/93/101",
            "rated_kw": 2300,
            "rotor_m": 101,
            "iec_class": "IIA/IIIA",
            "drivetrain": "Single-stage gearbox + PMSG (IntegraDrive)",
            "years_produced": "2005–2017",
        },
        "known_issues": [
            {
                "component": "Gearbox – single-stage planet",
                "issue": "Single-stage epicyclic gearbox planet carrier pin wear, more critical than multi-stage designs because there is no secondary mechanical filter.",
                "severity": "HIGH",
                "recommendation": "Online oil monitoring mandatory; vibration-based planetary CMS; plan gearbox inspection at 40,000 h.",
            },
            {
                "component": "Generator – winding insulation",
                "issue": "PMSG winding insulation degradation from moisture ingress through nacelle ventilation, manifesting as phase-to-phase fault.",
                "severity": "HIGH",
                "recommendation": "Annual insulation resistance (IR) test; check nacelle seals and desiccant packs.",
            },
            {
                "component": "Blade – erosion (IntegralBlade)",
                "issue": "Siemens IntegralBlade (cast epoxy) has excellent structural integrity but gel-coat erosion at leading edge in high-rain sites.",
                "severity": "MEDIUM",
                "recommendation": "Apply LEP by year 4; annual drone inspection.",
            },
        ],
        "strengths": [
            "IntegralBlade (one-piece cast) has lowest blade structural failure rate in class.",
            "Direct-to-grid PM generator reduces converter complexity.",
        ],
        "monitoring": [
            "Planet stage online oil monitoring",
            "Generator winding IR test annually",
            "Blade leading-edge drone condition",
        ],
    },

    "siemens-gamesa/sg5_145": {
        "meta": {
            "manufacturer": "Siemens Gamesa",
            "model": "SG 5.0-145",
            "rated_kw": 5000,
            "rotor_m": 145,
            "iec_class": "IIA",
            "drivetrain": "Single-stage gearbox + PMSG",
            "years_produced": "2018–present",
        },
        "known_issues": [
            {
                "component": "Converter – power module",
                "issue": "IGBT power module failures in the full-scale converter under high-cycling operation (frequent start/stop).",
                "severity": "HIGH",
                "recommendation": "Thermal imaging of converter at annual service; IGBT lifetime monitoring via SCADA; stock converter modules as critical spares.",
            },
            {
                "component": "Gearbox – lubrication system",
                "issue": "Oil pump auxiliary pressure loss in cold climates causing start-up delays and occasional bearing brinelling.",
                "severity": "MEDIUM",
                "recommendation": "Verify pre-lube function before winter start; add oil heater if ambient < −10°C expected.",
            },
        ],
        "strengths": [
            "High AEP density on IEC IIA sites.",
            "Advanced load control reduces tower fatigue.",
        ],
        "monitoring": [
            "Converter thermal imaging",
            "Gearbox pre-lube pressure",
            "Tower base acceleration",
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # ENERCON
    # ══════════════════════════════════════════════════════════════════════════

    "enercon/e82_2000": {
        "meta": {
            "manufacturer": "Enercon",
            "model": "E-82/2000",
            "rated_kw": 2000,
            "rotor_m": 82,
            "iec_class": "IIA/IIIA",
            "drivetrain": "Direct drive (annular synchronous generator, no gearbox)",
            "years_produced": "2005–2016",
        },
        "known_issues": [
            {
                "component": "Slip ring assembly",
                "issue": "Carbon brush wear on the rotor slip rings (used for rotor excitation) requires frequent inspection; brush dust contamination of generator internals.",
                "severity": "HIGH",
                "frequency": "Brush replacement every 12–18 months typical",
                "recommendation": "6-monthly slip ring inspection and brush wear measurement; maintain clean-room conditions during brush change; upgrade to brushless excitation if retrofit kit available.",
            },
            {
                "component": "Pitch bearing – inner race",
                "issue": "Pitch bearing raceway fatigue noted at years 10–14, driven by accumulated fatigue cycles in turbulent sites. Unique to Enercon due to high pitch-cycle frequency from direct-drive controller tuning.",
                "severity": "HIGH",
                "recommendation": "Annual grease injection per OEM schedule; visual inspection of raceway via bolt-hole scope at year 8; budget bearing replacement at year 12–15.",
            },
            {
                "component": "Generator winding – insulation",
                "issue": "Multi-pole annular generator has long stator winding with elevated moisture sensitivity; insulation resistance degradation documented in humid coastal sites.",
                "severity": "MEDIUM",
                "recommendation": "Annual IR test on all three phases; maintain generator heaters active during cold/humid standby periods.",
            },
            {
                "component": "Converter – grid-side IGBT",
                "issue": "The Enercon full-scale converter (no gearbox allows full-scale converter) has experienced IGBT failures under high grid-reactive-power demand.",
                "severity": "MEDIUM",
                "recommendation": "Monitor reactive power output vs converter temperature; reduce reactive power setpoint if converter temperature rises above threshold.",
            },
        ],
        "strengths": [
            "No gearbox eliminates the single highest failure-rate component in wind turbines.",
            "Very high reliability in low-wind sites due to direct-drive efficiency at partial load.",
            "Excellent track record in Germany and Northern Europe.",
        ],
        "monitoring": [
            "Slip ring brush wear (6-monthly measurement)",
            "Pitch bearing grease temperature and condition",
            "Generator IR test annually",
            "Converter temperature trending",
        ],
    },

    "enercon/e101_3000": {
        "meta": {
            "manufacturer": "Enercon",
            "model": "E-101/3000",
            "rated_kw": 3000,
            "rotor_m": 101,
            "iec_class": "IIA/IIIA",
            "drivetrain": "Direct drive (annular synchronous generator)",
            "years_produced": "2012–2020",
        },
        "known_issues": [
            {
                "component": "Slip ring assembly",
                "issue": "Same as E-82; brush wear rate slightly higher due to increased generator torque.",
                "severity": "HIGH",
                "recommendation": "Reduce inspection interval to 4-monthly in high-humidity sites.",
            },
            {
                "component": "Blade root – T-bolt fatigue",
                "issue": "T-bolt root attachment fatigue under high flap-wise load reversals, leading to fretting wear in composite root laminate.",
                "severity": "MEDIUM",
                "recommendation": "Root bolt torque verification at each annual service; apply torque audit every 500 operating hours in Year 1–3.",
            },
            {
                "component": "Tower – flange bolt relaxation",
                "issue": "Progressive bolt preload loss at tower flange joints, particularly in warm/humid climates due to galvanic corrosion of zinc-coated nuts.",
                "severity": "MEDIUM",
                "recommendation": "Tower flange bolt torque audit at 3-year intervals; apply anti-corrosion treatment to bolt threads.",
            },
        ],
        "strengths": [
            "No gearbox; excellent long-term availability record.",
            "Variable-speed operation via full-scale converter provides good grid-support capability.",
        ],
        "monitoring": [
            "Slip ring brush wear (4-monthly)",
            "Blade root bolt torque annually",
            "Tower flange bolt torque every 3 years",
        ],
    },

    "enercon/e138_3500": {
        "meta": {
            "manufacturer": "Enercon",
            "model": "E-138/3500 EP3",
            "rated_kw": 3500,
            "rotor_m": 138,
            "iec_class": "IIA/IIIA",
            "drivetrain": "Direct drive (annular synchronous generator)",
            "years_produced": "2017–present",
        },
        "known_issues": [
            {
                "component": "Blade manufacturing – bond quality",
                "issue": "Early E-138 series experienced trailing-edge bond quality variability from the new split-blade manufacturing process; recall and inspection campaign conducted by Enercon.",
                "severity": "HIGH",
                "recommendation": "Verify that Enercon inspection/recall campaign has been completed and signed off for each blade serial number.",
            },
            {
                "component": "Slip ring",
                "issue": "Same as E-82/E-101 platform; larger generator means higher brush current and accelerated wear.",
                "severity": "HIGH",
                "recommendation": "4-monthly inspection; upgrade to silver-alloy brushes if standard carbon brushes wear faster than expected.",
            },
        ],
        "strengths": [
            "Very large rotor (138 m) makes it excellent for IEC IIIA low-wind sites.",
            "Direct-drive architecture continues to offer best-in-class availability potential.",
        ],
        "monitoring": [
            "Blade trailing edge condition (confirm recall completion first)",
            "Slip ring brush wear 4-monthly",
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # GE (General Electric / GE Vernova)
    # ══════════════════════════════════════════════════════════════════════════

    "ge/1.5s": {
        "meta": {
            "manufacturer": "GE",
            "model": "GE 1.5s/1.5sl/1.5se",
            "rated_kw": 1500,
            "rotor_m": 77,
            "iec_class": "IA/IIA",
            "drivetrain": "3-stage gearbox + DFIG",
            "years_produced": "2000–2014",
        },
        "known_issues": [
            {
                "component": "Main bearing",
                "issue": "Double-tapered roller main bearing fatigue; among the most widely reported failure modes in this fleet globally.",
                "severity": "HIGH",
                "recommendation": "CMS mandatory; replace at first CMS alarm; negotiate exchange unit frame agreement given high frequency.",
            },
            {
                "component": "Gearbox – planet stage",
                "issue": "Planet carrier pin bore fretting, leading to pin migration and ring gear damage. Well-documented failure in 1.5s across the US and Europe.",
                "severity": "HIGH",
                "frequency": "Highest documented planetary stage failure rate in its class",
                "recommendation": "Online oil particle monitoring; gearbox exchange at year 8–10; assess repower economics after year 12.",
            },
            {
                "component": "Blade – structural crack (root section)",
                "issue": "Longitudinal shell crack at root-to-airfoil transition, propagating from manufacturing weld line.",
                "severity": "HIGH",
                "recommendation": "Annual root-to-10m crack survey; repair any > 100 mm immediately.",
            },
            {
                "component": "Converter – crowbar resistor",
                "issue": "Crowbar resistor degradation during repeated LVRT events.",
                "severity": "MEDIUM",
                "recommendation": "Test LVRT annually; replace resistor bank at 10-year service.",
            },
        ],
        "strengths": [
            "Single most widely installed multi-MW turbine globally; extremely deep spare-parts market.",
            "Robust nacelle structure proven in high-turbulence Class IA sites.",
        ],
        "monitoring": [
            "Main bearing CMS accelerometer",
            "Planet stage oil particle monitor",
            "Blade root annual crack survey",
        ],
    },

    "ge/2.0_116": {
        "meta": {
            "manufacturer": "GE",
            "model": "GE 2.0-116",
            "rated_kw": 2000,
            "rotor_m": 116,
            "iec_class": "IIA/IIIA",
            "drivetrain": "3-stage gearbox + DFIG",
            "years_produced": "2013–2020",
        },
        "known_issues": [
            {
                "component": "Blade – leading edge erosion",
                "issue": "High tip speed (~85 m/s) coupled with sanded-gelcoat finish leads to early erosion.",
                "severity": "HIGH",
                "recommendation": "LEP application by year 2; annual drone inspection from year 1.",
            },
            {
                "component": "Gearbox – IMS bearing",
                "issue": "IMS bearing fatigue at years 5–7 under high turbulence; similar failure mode to GE 1.5s gearbox.",
                "severity": "HIGH",
                "recommendation": "Oil particle monitoring; CMS channel on IMS; oil change at 2,500 h.",
            },
            {
                "component": "Tower – flange corrosion",
                "issue": "Internal tower flange bolts showing accelerated corrosion in coastal sites.",
                "severity": "MEDIUM",
                "recommendation": "Annual bolt torque and corrosion audit; apply corrosion inhibitor.",
            },
        ],
        "strengths": [
            "Good AEP at IEC IIA/IIIA sites with 116 m rotor.",
        ],
        "monitoring": [
            "Blade LEP condition (drone annual)",
            "Gearbox IMS vibration",
            "Tower bolt annual audit",
        ],
    },

    "ge/cypress_4_8": {
        "meta": {
            "manufacturer": "GE Vernova",
            "model": "Cypress 4.8-158",
            "rated_kw": 4800,
            "rotor_m": 158,
            "iec_class": "IIA/IIIA",
            "drivetrain": "3-stage gearbox + DFIG (two-piece blade design)",
            "years_produced": "2019–present",
        },
        "known_issues": [
            {
                "component": "Blade – jointing interface",
                "issue": "Cypress introduces a two-piece blade with a bolted mid-span joint to enable road transport; joint seal wear has been reported in early fleet.",
                "severity": "HIGH",
                "recommendation": "Annual inspection of joint bolt torques and seal integrity; water ingress into joint is a critical failure path.",
            },
            {
                "component": "Converter – thermal management",
                "issue": "Full-scale converter thermal cycling at partial-load sites with frequent start/stop causes IGBT solder fatigue.",
                "severity": "MEDIUM",
                "recommendation": "IGBT junction temperature monitoring via SCADA; plan IGBT module replacement at year 7.",
            },
        ],
        "strengths": [
            "Two-piece blade enables 158 m rotor on standard road transport network.",
            "Excellent AEP potential at IEC IIIA sites.",
        ],
        "monitoring": [
            "Blade joint bolt torque and seal condition annually",
            "Converter IGBT temperatures",
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SENVION (formerly REpower)
    # ══════════════════════════════════════════════════════════════════════════

    "senvion/mm92_2050": {
        "meta": {
            "manufacturer": "Senvion (formerly REpower)",
            "model": "MM92-2.05 MW",
            "rated_kw": 2050,
            "rotor_m": 92,
            "iec_class": "IIA/IIIA",
            "drivetrain": "3-stage gearbox + DFIG",
            "years_produced": "2006–2016",
        },
        "known_issues": [
            {
                "component": "Gearbox – HSS bearing",
                "issue": "HSS cylindrical roller bearing inner race fatigue, particularly in high-turbulence sites with frequent torque reversals.",
                "severity": "HIGH",
                "recommendation": "CMS HSS channel; oil sample ferrography every 500 hours; exchange programme at year 8.",
            },
            {
                "component": "Blade – root erosion",
                "issue": "Root-section leading-edge erosion from rain impact at ~78 m/s tip speed.",
                "severity": "MEDIUM",
                "recommendation": "LEP by year 3; annual drone inspection.",
            },
            {
                "component": "Main bearing",
                "issue": "Spherical roller main bearing fatigue in Class IIA turbulent sites.",
                "severity": "HIGH",
                "recommendation": "CMS accelerometer; grease analysis 6-monthly.",
            },
        ],
        "strengths": [
            "Well-established in German and Northern European markets.",
            "Large fleet means independent spare-parts ecosystem active.",
        ],
        "monitoring": [
            "Gearbox HSS CMS channel",
            "Main bearing vibration and grease",
            "Blade leading-edge annual drone",
        ],
    },

    "senvion/3.4m104": {
        "meta": {
            "manufacturer": "Senvion",
            "model": "3.4M104 / 3.4M114",
            "rated_kw": 3400,
            "rotor_m": 114,
            "iec_class": "IIA",
            "drivetrain": "3-stage gearbox + DFIG",
            "years_produced": "2011–2019",
        },
        "known_issues": [
            {
                "component": "Main bearing – front",
                "issue": "Front main bearing raceway fatigue accelerated by shaft deflection under rotor imbalance conditions.",
                "severity": "HIGH",
                "recommendation": "CMS; ensure rotor balance within 15 g·m residual imbalance at commissioning and after blade replacement.",
            },
            {
                "component": "Converter",
                "issue": "Full-scale converter failures related to DC bus capacitor degradation.",
                "severity": "MEDIUM",
                "recommendation": "Capacitance test at 5-year service; converter thermal imaging annually.",
            },
        ],
        "strengths": [
            "Competitive AEP at IEC IIA sites.",
        ],
        "monitoring": [
            "Main bearing CMS",
            "Converter capacitor health monitoring",
            "Rotor balance at commissioning",
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # GOLDWIND
    # ══════════════════════════════════════════════════════════════════════════

    "goldwind/gw121_2500": {
        "meta": {
            "manufacturer": "Goldwind",
            "model": "GW121/2500",
            "rated_kw": 2500,
            "rotor_m": 121,
            "iec_class": "IIA/IIIA",
            "drivetrain": "Direct drive PMSG (permanent magnet synchronous generator)",
            "years_produced": "2013–present",
        },
        "known_issues": [
            {
                "component": "Generator – demagnetisation",
                "issue": "Partial demagnetisation of permanent magnet poles observed in units exposed to high vibration and elevated temperature simultaneously.",
                "severity": "HIGH",
                "recommendation": "Generator vibration and temperature monitoring; annual back-EMF test to detect demagnetisation.",
            },
            {
                "component": "Blade – manufacture quality",
                "issue": "Earlier production batches showed void content variability in blade laminate, resulting in reduced fatigue life.",
                "severity": "MEDIUM",
                "recommendation": "Ultrasonic testing of blade shells if manufactured before 2016; repair any detected delamination > 50 cm².",
            },
        ],
        "strengths": [
            "No gearbox; competitive O&M cost in Chinese and Australian markets.",
        ],
        "monitoring": [
            "Generator temperature and vibration",
            "Annual back-EMF measurement",
        ],
    },

}  # end TURBINE_DB
