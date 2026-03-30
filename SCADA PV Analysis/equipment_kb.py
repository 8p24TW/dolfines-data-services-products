"""
equipment_kb.py — Equipment knowledge base for PVPAT Platform
=============================================================
Wind turbine manufacturers & models, solar module manufacturers,
and solar inverter manufacturers & models.
"""

# ── Wind turbines ─────────────────────────────────────────────────────────────
# Structure: { "Manufacturer": ["Model1", "Model2", ...] }
# Rated capacity (MW) is part of the model name for reference.

WIND_TURBINES: dict[str, list[str]] = {
    "Vestas": [
        "V80-2.0",
        "V90-2.0",
        "V100-2.0",
        "V110-2.0",
        "V112-3.45",
        "V136-3.45",
        "V136-4.5",
        "V150-4.5",
        "V162-5.6",
        "V172-7.2",
        "V236-15.0",
    ],
    "Siemens Gamesa": [
        "SG 2.1-114",
        "SG 2.6-114",
        "SG 3.4-132",
        "SG 4.5-145",
        "SG 5.0-145",
        "SG 6.0-170",
        "SG 11.0-193 DD",
        "SG 14-236 DD",
    ],
    "GE Vernova": [
        "GE 1.5sl",
        "GE 2.75-120",
        "GE 3.6-130",
        "GE 4.8-158",
        "GE 5.5-158",
        "Haliade-X 12MW",
        "Haliade-X 13MW",
        "Haliade-X 14MW",
        "Haliade-X 15MW",
    ],
    "Enercon": [
        "E-44",
        "E-53",
        "E-70",
        "E-82",
        "E-92",
        "E-101",
        "E-115",
        "E-126 EP3",
        "E-126 EP4",
        "E-138 EP3",
        "E-160 EP5",
    ],
    "Nordex": [
        "N90/2500",
        "N100/3300",
        "N117/3000",
        "N131/3000",
        "N131/3600",
        "N149/4.0",
        "N149/4.5",
        "N163/5.X",
        "N175/6.X",
    ],
    "Goldwind": [
        "GW87/1500",
        "GW93/2000",
        "GW121/2500",
        "GW136/3000",
        "GW155/4500",
        "GW171/6250",
        "GW175-6.0",
    ],
    "Ming Yang": [
        "MySE 3.0-135",
        "MySE 3.5-155",
        "MySE 4.0-155",
        "MySE 6.25-173",
        "MySE 7.25-158",
        "MySE 16.0-242",
    ],
    "Envision": [
        "EN-136/4000",
        "EN-156/4200",
        "EN-185/6800",
    ],
    "Senvion": [
        "MM92/2050",
        "3.2M114",
        "3.4M140",
    ],
    "Suzlon": [
        "S88/2100",
        "S111/2100",
        "S128/2800",
    ],
    "CSSC Haizhuang": [
        "H116-2000",
        "H146-4000",
        "H210-10000",
    ],
    "Windey": [
        "WD3000D-121",
        "WD5000D-155",
    ],
    "Other": [],
}

# ── Solar module manufacturers ────────────────────────────────────────────────
SOLAR_MODULE_MANUFACTURERS: list[str] = [
    "First Solar",
    "Jinko Solar",
    "LONGi",
    "JA Solar",
    "Canadian Solar",
    "Trina Solar",
    "SunPower / Maxeon",
    "Hanwha Q CELLS",
    "REC Group",
    "Risen Energy",
    "BYD",
    "Astronergy",
    "Seraphim",
    "Other",
]

# Popular module series per manufacturer (informational — not used in dropdowns yet)
SOLAR_MODULE_SERIES: dict[str, list[str]] = {
    "First Solar": ["Series 6 CdTe", "Series 6 Plus", "Series 7 CdTe"],
    "Jinko Solar": ["Tiger Pro (72HC)", "Tiger Neo (54HL4-B)", "Eagle G2"],
    "LONGi": ["Hi-MO 5m", "Hi-MO 6 (LR5-72HTH)", "Hi-MO X6 (LR5-72HIBD)"],
    "JA Solar": ["JAM60S20", "JAM72S30", "DeepBlue 4.0 Pro"],
    "Canadian Solar": ["HiKu7 CS7L", "BiHiKu7 CS7N", "TOPBiHiKu6"],
    "Trina Solar": ["Vertex S (TSM-DE09)", "Vertex DEG (TSM-DEG19C)", "Vertex N (TDM-NEG21C)"],
    "SunPower / Maxeon": ["Maxeon 3 (BLK-R)", "Maxeon 5 (AC)", "Maxeon 6 (AC)"],
    "Hanwha Q CELLS": ["Q.PEAK DUO BLK ML-G10+", "Q.TRON BLK M-G2+"],
    "REC Group": ["REC Alpha Pure-R", "REC TwinPeak 5"],
}

# ── Solar inverters ───────────────────────────────────────────────────────────
SOLAR_INVERTERS: dict[str, list[str]] = {
    "Sungrow": [
        "SG110CX-P2",
        "SG250HX",
        "SG320HX",
        "SG350HX",
        "SG3125HV-MV",
        "SG5000UD-MV",
    ],
    "Huawei": [
        "SUN2000-100KTL-M1",
        "SUN2000-185KTL-H1",
        "SUN2000-200KTL-H0",
        "SUN2000-215KTL-H3",
        "SUN2000-330KTL-H1",
    ],
    "SMA": [
        "Sunny Tripower CORE2 110",
        "Sunny Tripower CORE2 150",
        "Sunny Highpower PEAK3",
        "Sunny Central 2200",
        "Sunny Central 2475-EV",
    ],
    "ABB / FIMER": [
        "PVS-10/33/100 TRIO",
        "PVS-175-TL",
        "PVS-250-TL",
        "PVS-980-TL",
        "PVS-100/120-TL",
    ],
    "Fronius": [
        "Symo GEN24 Plus 3.0",
        "Symo GEN24 Plus 10.0",
        "Tauro ECO 50-3-P",
        "Tauro ECO 100-3-P",
    ],
    "Schneider Electric": [
        "Conext Core XC 1000",
        "Conext Core XC 1500",
    ],
    "Delta": [
        "M50A",
        "M88A",
        "M125HV",
        "MH250HV",
        "RPI H5A",
    ],
    "KACO": [
        "blueplanet 60 TL3",
        "blueplanet 125 TL3",
        "XP500U-TL",
    ],
    "Power Electronics": [
        "FS1250CU",
        "FS3000CU",
        "SC500K",
    ],
    "Ingeteam": [
        "INGECON SUN 1Play 33TL M",
        "INGECON SUN 3Play 150TL",
        "INGECON SUN 3Play 330TL",
    ],
    "Solaredge": [
        "SE50K",
        "SE100K",
        "SE166K",
        "SE250K",
    ],
    "Enphase": [
        "IQ8A",
        "IQ8H",
        "IQ8X",
    ],
    "Other": [],
}


# ── Helper: detect manufacturer from a technology/model string ────────────────

def detect_wind_manufacturer(technology: str) -> str:
    """Return the manufacturer key that best matches the technology string."""
    if not technology:
        return ""
    t = technology.lower()
    for mfr in WIND_TURBINES:
        if mfr.lower() in t or t.startswith(mfr.split()[0].lower()):
            return mfr
    # short-name aliases
    aliases = {
        "vestas": "Vestas",
        "siemens": "Siemens Gamesa",
        "gamesa": "Siemens Gamesa",
        "ge ": "GE Vernova",
        "haliade": "GE Vernova",
        "enercon": "Enercon",
        "nordex": "Nordex",
        "goldwind": "Goldwind",
        "ming yang": "Ming Yang",
        "myse": "Ming Yang",
        "envision": "Envision",
        "senvion": "Senvion",
        "suzlon": "Suzlon",
    }
    for alias, mfr in aliases.items():
        if alias in t:
            return mfr
    return ""


def detect_inverter_manufacturer(inverter_model: str) -> str:
    """Return the manufacturer key that best matches the inverter model string."""
    if not inverter_model:
        return ""
    m = inverter_model.lower()
    for mfr in SOLAR_INVERTERS:
        if mfr.lower().split("/")[0].strip() in m:
            return mfr
    aliases = {
        "sungrow": "Sungrow",
        "sg": "Sungrow",
        "huawei": "Huawei",
        "sun2000": "Huawei",
        "sma": "SMA",
        "abb": "ABB / FIMER",
        "fimer": "ABB / FIMER",
        "fronius": "Fronius",
        "schneider": "Schneider Electric",
        "delta": "Delta",
        "kaco": "KACO",
        "power electronics": "Power Electronics",
        "ingeteam": "Ingeteam",
        "solaredge": "Solaredge",
        "enphase": "Enphase",
    }
    for alias, mfr in aliases.items():
        if alias in m:
            return mfr
    return ""
