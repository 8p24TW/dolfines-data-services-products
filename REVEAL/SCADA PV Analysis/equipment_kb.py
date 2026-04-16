"""
equipment_kb.py — Equipment knowledge base for PVPAT Platform
=============================================================
Wind turbine, solar module, and solar inverter metadata used to
auto-fill technical fields in the platform editor.
"""

WIND_TURBINE_SPECS: dict[str, dict[str, dict[str, float]]] = {
    "Vestas": {
        "V80-2.0": {"rated_mw": 2.0, "rotor_diameter_m": 80},
        "V90-2.0": {"rated_mw": 2.0, "rotor_diameter_m": 90},
        "V100-2.0": {"rated_mw": 2.0, "rotor_diameter_m": 100},
        "V110-2.0": {"rated_mw": 2.0, "rotor_diameter_m": 110},
        "V112-3.45": {"rated_mw": 3.45, "rotor_diameter_m": 112},
        "V136-3.45": {"rated_mw": 3.45, "rotor_diameter_m": 136},
        "V136-4.5": {"rated_mw": 4.5, "rotor_diameter_m": 136},
        "V150-4.5": {"rated_mw": 4.5, "rotor_diameter_m": 150},
        "V162-5.6": {"rated_mw": 5.6, "rotor_diameter_m": 162},
        "V172-7.2": {"rated_mw": 7.2, "rotor_diameter_m": 172},
        "V236-15.0": {"rated_mw": 15.0, "rotor_diameter_m": 236},
    },
    "Siemens Gamesa": {
        "SG 2.1-114": {"rated_mw": 2.1, "rotor_diameter_m": 114},
        "SG 2.6-114": {"rated_mw": 2.6, "rotor_diameter_m": 114},
        "SG 3.4-132": {"rated_mw": 3.4, "rotor_diameter_m": 132},
        "SG 4.5-145": {"rated_mw": 4.5, "rotor_diameter_m": 145},
        "SG 5.0-145": {"rated_mw": 5.0, "rotor_diameter_m": 145},
        "SG 6.0-170": {"rated_mw": 6.0, "rotor_diameter_m": 170},
        "SG 11.0-193 DD": {"rated_mw": 11.0, "rotor_diameter_m": 193},
        "SG 14-236 DD": {"rated_mw": 14.0, "rotor_diameter_m": 236},
    },
    "GE Vernova": {
        "GE 1.5sl": {"rated_mw": 1.5, "rotor_diameter_m": 77},
        "GE 2.75-120": {"rated_mw": 2.75, "rotor_diameter_m": 120},
        "GE 3.6-130": {"rated_mw": 3.6, "rotor_diameter_m": 130},
        "GE 4.8-158": {"rated_mw": 4.8, "rotor_diameter_m": 158},
        "GE 5.5-158": {"rated_mw": 5.5, "rotor_diameter_m": 158},
        "Haliade-X 12MW": {"rated_mw": 12.0, "rotor_diameter_m": 220},
        "Haliade-X 13MW": {"rated_mw": 13.0, "rotor_diameter_m": 220},
        "Haliade-X 14MW": {"rated_mw": 14.0, "rotor_diameter_m": 220},
        "Haliade-X 15MW": {"rated_mw": 15.0, "rotor_diameter_m": 220},
    },
    "Enercon": {
        "E-44": {"rated_mw": 0.9, "rotor_diameter_m": 44},
        "E-53": {"rated_mw": 0.8, "rotor_diameter_m": 53},
        "E-70": {"rated_mw": 2.3, "rotor_diameter_m": 71},
        "E-82": {"rated_mw": 2.3, "rotor_diameter_m": 82},
        "E-92": {"rated_mw": 2.35, "rotor_diameter_m": 92},
        "E-101": {"rated_mw": 3.05, "rotor_diameter_m": 101},
        "E-115": {"rated_mw": 3.0, "rotor_diameter_m": 115},
        "E-126 EP3": {"rated_mw": 4.2, "rotor_diameter_m": 127},
        "E-126 EP4": {"rated_mw": 4.2, "rotor_diameter_m": 127},
        "E-138 EP3": {"rated_mw": 4.26, "rotor_diameter_m": 138},
        "E-160 EP5": {"rated_mw": 5.56, "rotor_diameter_m": 160},
    },
    "Nordex": {
        "N90/2500": {"rated_mw": 2.5, "rotor_diameter_m": 90},
        "N100/3300": {"rated_mw": 3.3, "rotor_diameter_m": 100},
        "N117/3000": {"rated_mw": 3.0, "rotor_diameter_m": 117},
        "N131/3000": {"rated_mw": 3.0, "rotor_diameter_m": 131},
        "N131/3600": {"rated_mw": 3.6, "rotor_diameter_m": 131},
        "N149/4.0": {"rated_mw": 4.0, "rotor_diameter_m": 149},
        "N149/4.5": {"rated_mw": 4.5, "rotor_diameter_m": 149},
        "N163/5.X": {"rated_mw": 5.7, "rotor_diameter_m": 163},
        "N175/6.X": {"rated_mw": 6.0, "rotor_diameter_m": 175},
    },
    "Goldwind": {
        "GW87/1500": {"rated_mw": 1.5, "rotor_diameter_m": 87},
        "GW93/2000": {"rated_mw": 2.0, "rotor_diameter_m": 93},
        "GW121/2500": {"rated_mw": 2.5, "rotor_diameter_m": 121},
        "GW136/3000": {"rated_mw": 3.0, "rotor_diameter_m": 136},
        "GW155/4500": {"rated_mw": 4.5, "rotor_diameter_m": 155},
        "GW171/6250": {"rated_mw": 6.25, "rotor_diameter_m": 171},
        "GW175-6.0": {"rated_mw": 6.0, "rotor_diameter_m": 175},
    },
    "Ming Yang": {
        "MySE 3.0-135": {"rated_mw": 3.0, "rotor_diameter_m": 135},
        "MySE 3.5-155": {"rated_mw": 3.5, "rotor_diameter_m": 155},
        "MySE 4.0-155": {"rated_mw": 4.0, "rotor_diameter_m": 155},
        "MySE 6.25-173": {"rated_mw": 6.25, "rotor_diameter_m": 173},
        "MySE 7.25-158": {"rated_mw": 7.25, "rotor_diameter_m": 158},
        "MySE 16.0-242": {"rated_mw": 16.0, "rotor_diameter_m": 242},
    },
    "Envision": {
        "EN-136/4000": {"rated_mw": 4.0, "rotor_diameter_m": 136},
        "EN-156/4200": {"rated_mw": 4.2, "rotor_diameter_m": 156},
        "EN-185/6800": {"rated_mw": 6.8, "rotor_diameter_m": 185},
    },
    "Senvion": {
        "MM92/2050": {"rated_mw": 2.05, "rotor_diameter_m": 92},
        "3.2M114": {"rated_mw": 3.2, "rotor_diameter_m": 114},
        "3.4M140": {"rated_mw": 3.4, "rotor_diameter_m": 140},
    },
    "Suzlon": {
        "S88/2100": {"rated_mw": 2.1, "rotor_diameter_m": 88},
        "S111/2100": {"rated_mw": 2.1, "rotor_diameter_m": 111},
        "S128/2800": {"rated_mw": 2.8, "rotor_diameter_m": 128},
    },
    "CSSC Haizhuang": {
        "H116-2000": {"rated_mw": 2.0, "rotor_diameter_m": 116},
        "H146-4000": {"rated_mw": 4.0, "rotor_diameter_m": 146},
        "H210-10000": {"rated_mw": 10.0, "rotor_diameter_m": 210},
    },
    "Windey": {
        "WD3000D-121": {"rated_mw": 3.0, "rotor_diameter_m": 121},
        "WD5000D-155": {"rated_mw": 5.0, "rotor_diameter_m": 155},
    },
    "Other": {},
}

WIND_TURBINES: dict[str, list[str]] = {
    manufacturer: list(models.keys())
    for manufacturer, models in WIND_TURBINE_SPECS.items()
}

SOLAR_MODULE_SPECS: dict[str, dict[str, dict[str, float | str]]] = {
    "First Solar": {
        "Series 6 Plus": {"power_wp": 460.0, "technology": "CdTe thin-film"},
        "Series 6 CuRe": {"power_wp": 445.0, "technology": "CdTe thin-film"},
        "Series 7": {"power_wp": 535.0, "technology": "CdTe thin-film"},
    },
    "Jinko Solar": {
        "Tiger Pro 72HC": {"power_wp": 540.0, "technology": "Mono PERC"},
        "Tiger Neo 72HL4-BDV": {"power_wp": 585.0, "technology": "N-type TOPCon bifacial"},
        "Tiger Neo 78HL4-BDV": {"power_wp": 620.0, "technology": "N-type TOPCon bifacial"},
    },
    "LONGi": {
        "Hi-MO 5 LR5-72HPH": {"power_wp": 545.0, "technology": "Mono PERC"},
        "Hi-MO 6 LR5-72HTH": {"power_wp": 585.0, "technology": "HPBC mono"},
        "Hi-MO 7 LR7-72HGD": {"power_wp": 615.0, "technology": "HPDC bifacial"},
    },
    "JA Solar": {
        "JAM72S30": {"power_wp": 545.0, "technology": "Mono PERC"},
        "DeepBlue 4.0 Pro JAM72D40": {"power_wp": 585.0, "technology": "N-type bifacial"},
        "DeepBlue 4.0 X JAM66D45": {"power_wp": 635.0, "technology": "N-type bifacial"},
    },
    "Canadian Solar": {
        "HiKu7 CS7L": {"power_wp": 600.0, "technology": "Mono PERC"},
        "BiHiKu7 CS7N": {"power_wp": 665.0, "technology": "Bifacial mono PERC"},
        "TOPBiHiKu6 CS6W": {"power_wp": 620.0, "technology": "TOPCon bifacial"},
    },
    "Trina Solar": {
        "Vertex TSM-DE18M": {"power_wp": 540.0, "technology": "Mono PERC"},
        "Vertex N TSM-NEG19RC": {"power_wp": 615.0, "technology": "N-type i-TOPCon bifacial"},
        "Vertex N TSM-NEG21C": {"power_wp": 695.0, "technology": "N-type i-TOPCon bifacial"},
    },
    "SunPower / Maxeon": {
        "Maxeon 3": {"power_wp": 400.0, "technology": "IBC mono"},
        "Maxeon 6": {"power_wp": 440.0, "technology": "IBC mono"},
        "Performance 7": {"power_wp": 615.0, "technology": "Shingled PERC"},
    },
    "Hanwha Q CELLS": {
        "Q.PEAK DUO XL-G11.3": {"power_wp": 590.0, "technology": "Mono PERC"},
        "Q.TRON XL-G2.4": {"power_wp": 605.0, "technology": "N-type"},
    },
    "REC Group": {
        "REC Alpha Pure-R": {"power_wp": 430.0, "technology": "HJT mono"},
        "REC TwinPeak 5": {"power_wp": 400.0, "technology": "Mono PERC"},
    },
    "Risen Energy": {
        "Titan RSM110-8-550M": {"power_wp": 550.0, "technology": "Mono PERC"},
        "Hyper-ion RSM132-8-700BHDG": {"power_wp": 700.0, "technology": "HJT bifacial"},
    },
    "BYD": {
        "P6C-36 Series 4": {"power_wp": 365.0, "technology": "Poly/mono PERC"},
        "P7 Series": {"power_wp": 540.0, "technology": "Mono PERC"},
    },
    "Astronergy": {
        "ASTRO 5 CHSM72M": {"power_wp": 550.0, "technology": "Mono PERC"},
        "ASTRO N7 CHSM72N": {"power_wp": 620.0, "technology": "TOPCon bifacial"},
    },
    "Seraphim": {
        "SIV N-TOPCon 210": {"power_wp": 605.0, "technology": "TOPCon bifacial"},
        "Blade SRP-550-BMD": {"power_wp": 550.0, "technology": "Mono PERC"},
    },
    "Other": {},
}

SOLAR_MODULES: dict[str, list[str]] = {
    manufacturer: list(models.keys())
    for manufacturer, models in SOLAR_MODULE_SPECS.items()
}

SOLAR_MODULE_MANUFACTURERS: list[str] = list(SOLAR_MODULE_SPECS.keys())
SOLAR_MODULE_SERIES: dict[str, list[str]] = {
    manufacturer: list(models.keys())
    for manufacturer, models in SOLAR_MODULE_SPECS.items()
    if models
}

SOLAR_INVERTER_SPECS: dict[str, dict[str, dict[str, float]]] = {
    "Sungrow": {
        "SG110CX-P2": {"ac_kw": 110.0},
        "SG250HX": {"ac_kw": 250.0},
        "SG320HX": {"ac_kw": 320.0},
        "SG350HX": {"ac_kw": 352.0},
        "SG3125HV-MV": {"ac_kw": 3125.0},
        "SG5000UD-MV": {"ac_kw": 5000.0},
    },
    "Huawei": {
        "SUN2000-100KTL-M1": {"ac_kw": 100.0},
        "SUN2000-185KTL-H1": {"ac_kw": 185.0},
        "SUN2000-200KTL-H0": {"ac_kw": 200.0},
        "SUN2000-215KTL-H3": {"ac_kw": 215.0},
        "SUN2000-330KTL-H1": {"ac_kw": 330.0},
    },
    "SMA": {
        "Sunny Tripower CORE2 110": {"ac_kw": 110.0},
        "Sunny Tripower CORE2 150": {"ac_kw": 150.0},
        "Sunny Highpower PEAK3": {"ac_kw": 150.0},
        "Sunny Central 2200": {"ac_kw": 2200.0},
        "Sunny Central 2475-EV": {"ac_kw": 2475.0},
    },
    "ABB / FIMER": {
        "PVS-10/33/100 TRIO": {"ac_kw": 100.0},
        "PVS-175-TL": {"ac_kw": 175.0},
        "PVS-250-TL": {"ac_kw": 250.0},
        "PVS-980-TL": {"ac_kw": 980.0},
        "PVS-100/120-TL": {"ac_kw": 120.0},
    },
    "Fronius": {
        "Symo GEN24 Plus 3.0": {"ac_kw": 3.0},
        "Symo GEN24 Plus 10.0": {"ac_kw": 10.0},
        "Tauro ECO 50-3-P": {"ac_kw": 50.0},
        "Tauro ECO 100-3-P": {"ac_kw": 100.0},
    },
    "Schneider Electric": {
        "Conext Core XC 1000": {"ac_kw": 1000.0},
        "Conext Core XC 1500": {"ac_kw": 1500.0},
    },
    "Delta": {
        "M50A": {"ac_kw": 50.0},
        "M88A": {"ac_kw": 88.0},
        "M125HV": {"ac_kw": 125.0},
        "MH250HV": {"ac_kw": 250.0},
        "RPI H5A": {"ac_kw": 550.0},
    },
    "KACO": {
        "blueplanet 60 TL3": {"ac_kw": 60.0},
        "blueplanet 125 TL3": {"ac_kw": 125.0},
        "XP500U-TL": {"ac_kw": 500.0},
    },
    "Power Electronics": {
        "FS1250CU": {"ac_kw": 1250.0},
        "FS3000CU": {"ac_kw": 3000.0},
        "SC500K": {"ac_kw": 500.0},
    },
    "Ingeteam": {
        "INGECON SUN 1Play 33TL M": {"ac_kw": 33.0},
        "INGECON SUN 3Play 150TL": {"ac_kw": 150.0},
        "INGECON SUN 3Play 330TL": {"ac_kw": 330.0},
    },
    "Solaredge": {
        "SE50K": {"ac_kw": 50.0},
        "SE100K": {"ac_kw": 100.0},
        "SE166K": {"ac_kw": 166.0},
        "SE250K": {"ac_kw": 250.0},
    },
    "Enphase": {
        "IQ8A": {"ac_kw": 0.37},
        "IQ8H": {"ac_kw": 0.38},
        "IQ8X": {"ac_kw": 0.384},
    },
    "Other": {},
}

SOLAR_INVERTERS: dict[str, list[str]] = {
    manufacturer: list(models.keys())
    for manufacturer, models in SOLAR_INVERTER_SPECS.items()
}


def get_wind_turbine_spec(manufacturer: str, model: str) -> dict[str, float]:
    return dict(WIND_TURBINE_SPECS.get(manufacturer, {}).get(model, {}))


def get_solar_module_spec(manufacturer: str, model: str) -> dict[str, float | str]:
    return dict(SOLAR_MODULE_SPECS.get(manufacturer, {}).get(model, {}))


def get_inverter_spec(manufacturer: str, model: str) -> dict[str, float]:
    return dict(SOLAR_INVERTER_SPECS.get(manufacturer, {}).get(model, {}))


def detect_wind_manufacturer(technology: str) -> str:
    """Return the manufacturer key that best matches the technology string."""
    if not technology:
        return ""
    t = technology.lower()
    for manufacturer, models in WIND_TURBINES.items():
        if manufacturer.lower() in t or any(model.lower() in t for model in models):
            return manufacturer
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
    for alias, manufacturer in aliases.items():
        if alias in t:
            return manufacturer
    return ""


def detect_module_manufacturer(module_model: str) -> str:
    """Return the module manufacturer that best matches a model/technology string."""
    if not module_model:
        return ""
    text = module_model.lower()
    for manufacturer, models in SOLAR_MODULES.items():
        short_name = manufacturer.lower().split("/")[0].strip()
        if short_name in text or any(model.lower() in text for model in models):
            return manufacturer
    aliases = {
        "first solar": "First Solar",
        "jinko": "Jinko Solar",
        "longi": "LONGi",
        "ja solar": "JA Solar",
        "canadian": "Canadian Solar",
        "trina": "Trina Solar",
        "maxeon": "SunPower / Maxeon",
        "sunpower": "SunPower / Maxeon",
        "q cells": "Hanwha Q CELLS",
        "qcells": "Hanwha Q CELLS",
        "rec": "REC Group",
        "risen": "Risen Energy",
        "astronergy": "Astronergy",
        "seraphim": "Seraphim",
    }
    for alias, manufacturer in aliases.items():
        if alias in text:
            return manufacturer
    return ""


def detect_inverter_manufacturer(inverter_model: str) -> str:
    """Return the manufacturer key that best matches the inverter model string."""
    if not inverter_model:
        return ""
    model_text = inverter_model.lower()
    for manufacturer, models in SOLAR_INVERTERS.items():
        short_name = manufacturer.lower().split("/")[0].strip()
        if short_name in model_text or any(model.lower() in model_text for model in models):
            return manufacturer
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
    for alias, manufacturer in aliases.items():
        if alias in model_text:
            return manufacturer
    return ""
