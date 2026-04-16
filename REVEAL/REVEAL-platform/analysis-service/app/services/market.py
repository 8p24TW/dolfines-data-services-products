"""
Market and retrofit services for REVEAL.

This first integration is adapted from the external day-ahead and long-term
revenue tooling provided for the Retrofit BESS consultancy workflow. It keeps
the same strategic logic:
  - gradual PV cannibalization pressure on market prices
  - delayed BESS relief as storage deployment grows
  - retrofit screening driven by negative-price energy recovery and simple payback

The next integration step is to replace the manual negative-energy bridge with
hourly production and curtailment curves from the REVEAL Performance workflow.
"""

from __future__ import annotations

import calendar
import csv
import datetime as dt
import math
import statistics
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_PROJECTIONS_CSV = _DATA_DIR / "projections_day-ahead.csv"
_HISTORICAL_DAY_AHEAD_CSV = _DATA_DIR / "base_donnees_day-ahead.csv"


SCENARIO_ESCALATION = {
    "base": 0.005,
    "high": 0.015,
    "low": -0.015,
}

GAMMA_0 = 0.40
LAMBDA_ = 0.10
BETA_0 = 0.15
MU = 0.07
D_BESS = 4
SOLAR_EXPOSURE_FACTOR = 1.8

MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}

MONTH_RADIATION = {
    1: 0.28,
    2: 0.42,
    3: 0.62,
    4: 0.80,
    5: 0.94,
    6: 1.00,
    7: 1.00,
    8: 0.90,
    9: 0.70,
    10: 0.50,
    11: 0.30,
    12: 0.24,
}

TYPE_PROFIL_MAP = {
    "ouvre": "Jour ouvré",
    "weekend": "Week-end / J. Férié",
}

SCENARIO_SUFFIX_MAP = {
    "base": "base",
    "high": "haut",
    "low": "bas",
    "haut": "haut",
    "bas": "bas",
}


@lru_cache(maxsize=1)
def _load_projection_rows() -> dict[tuple[int, int, str], list[dict[str, Any]]]:
    rows_by_key: dict[tuple[int, int, str], list[dict[str, Any]]] = {}
    if not _PROJECTIONS_CSV.exists():
        return rows_by_key

    with open(_PROJECTIONS_CSV, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            key = (int(raw["annee"]), int(raw["mois"]), raw["type_profil"])
            row = {
                "hour": int(raw["heure"]),
                "price_base_eur_mwh": round(float(raw["prix_base_eur_mwh"]), 2),
                "price_high_eur_mwh": round(float(raw["prix_haut_eur_mwh"]), 2),
                "price_low_eur_mwh": round(float(raw["prix_bas_eur_mwh"]), 2),
                "baseload_base_eur_mwh": round(float(raw["bl_base_eur_mwh"]), 2),
                "baseload_high_eur_mwh": round(float(raw["bl_haut_eur_mwh"]), 2),
                "baseload_low_eur_mwh": round(float(raw["bl_bas_eur_mwh"]), 2),
                "price_base_p10_eur_mwh": round(float(raw["prix_base_p10_eur_mwh"]), 2),
                "price_base_p25_eur_mwh": round(float(raw["prix_base_p25_eur_mwh"]), 2),
                "price_base_p50_eur_mwh": round(float(raw["prix_base_p50_eur_mwh"]), 2),
                "price_base_p75_eur_mwh": round(float(raw["prix_base_p75_eur_mwh"]), 2),
                "price_base_p90_eur_mwh": round(float(raw["prix_base_p90_eur_mwh"]), 2),
                "price_high_p10_eur_mwh": round(float(raw["prix_haut_p10_eur_mwh"]), 2),
                "price_high_p25_eur_mwh": round(float(raw["prix_haut_p25_eur_mwh"]), 2),
                "price_high_p50_eur_mwh": round(float(raw["prix_haut_p50_eur_mwh"]), 2),
                "price_high_p75_eur_mwh": round(float(raw["prix_haut_p75_eur_mwh"]), 2),
                "price_high_p90_eur_mwh": round(float(raw["prix_haut_p90_eur_mwh"]), 2),
                "price_low_p10_eur_mwh": round(float(raw["prix_bas_p10_eur_mwh"]), 2),
                "price_low_p25_eur_mwh": round(float(raw["prix_bas_p25_eur_mwh"]), 2),
                "price_low_p50_eur_mwh": round(float(raw["prix_bas_p50_eur_mwh"]), 2),
                "price_low_p75_eur_mwh": round(float(raw["prix_bas_p75_eur_mwh"]), 2),
                "price_low_p90_eur_mwh": round(float(raw["prix_bas_p90_eur_mwh"]), 2),
                "freq_neg_base": round(float(raw["freq_neg_base"]), 4),
                "freq_neg_high": round(float(raw["freq_neg_haut"]), 4),
                "freq_neg_low": round(float(raw["freq_neg_bas"]), 4),
            }
            rows_by_key.setdefault(key, []).append(row)

    for values in rows_by_key.values():
        values.sort(key=lambda item: item["hour"])
    return rows_by_key


def _classify_day_type(date_value: dt.date) -> str:
    if date_value.weekday() >= 5:
        return "Week-end / J. Férié"
    return "Jour ouvré"


@lru_cache(maxsize=1)
def _load_historical_profiles() -> dict[tuple[int, str], dict[int, float]]:
    grouped: dict[tuple[int, str, int], list[float]] = {}
    if not _HISTORICAL_DAY_AHEAD_CSV.exists():
        return {}

    with open(_HISTORICAL_DAY_AHEAD_CSV, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            timestamp = raw.get("datetime_start")
            price_text = raw.get("prix_da_eur_mwh")
            if not timestamp or not price_text:
                continue

            try:
                parsed_dt = dt.datetime.fromisoformat(timestamp)
                price = float(price_text)
            except ValueError:
                continue

            date_key = parsed_dt.date()
            day_type = raw.get("type_jour")
            if day_type in {"Week-end", "Férié"}:
                type_profil = "Week-end / J. Férié"
            elif day_type == "Jour ouvré":
                type_profil = "Jour ouvré"
            else:
                type_profil = _classify_day_type(date_key)

            grouped.setdefault((parsed_dt.month, type_profil, parsed_dt.hour), []).append(price)

    result: dict[tuple[int, str], dict[int, float]] = {}
    for (month, type_profil, hour), values in grouped.items():
        result.setdefault((month, type_profil), {})[hour] = round(statistics.median(values), 2)
    return result


def _pv_cannibalization_index(year: int) -> float:
    if year <= 2030:
        return 0.0
    return 1.0 - math.exp(-LAMBDA_ * (year - 2030))


def _bess_relief_index(year: int, start_year: int) -> float:
    deployment_year = start_year + D_BESS
    if year <= deployment_year:
        return 0.0
    return 1.0 - math.exp(-MU * (year - deployment_year))


def _market_price_key(scenario_key: str) -> str:
    if scenario_key == "high":
        return "price_high_eur_mwh"
    if scenario_key == "low":
        return "price_low_eur_mwh"
    return "price_base_eur_mwh"


def _market_negative_key(scenario_key: str) -> str:
    if scenario_key == "high":
        return "freq_neg_high"
    if scenario_key == "low":
        return "freq_neg_low"
    return "freq_neg_base"


@lru_cache(maxsize=64)
def _calendar_daytype_counts(year: int) -> dict[tuple[int, str], int]:
    counts: dict[tuple[int, str], int] = {}
    for month in range(1, 13):
        month_weeks = calendar.monthcalendar(year, month)
        weekend_days = sum(1 for week in month_weeks for day in (week[calendar.SATURDAY], week[calendar.SUNDAY]) if day)
        total_days = calendar.monthrange(year, month)[1]
        workdays = total_days - weekend_days
        counts[(month, "Jour ouvré")] = workdays
        counts[(month, "Week-end / J. Férié")] = weekend_days
    return counts


def _build_hour_lookup(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {int(row["hour"]): row for row in rows}


def _generic_solar_profile_weights(year: int) -> list[dict[str, Any]]:
    weights: list[dict[str, Any]] = []
    calendar_counts = _calendar_daytype_counts(year)
    total = 0.0
    for month in range(1, 13):
        seasonal = MONTH_RADIATION.get(month, 0.5)
        for day_type, type_profil in TYPE_PROFIL_MAP.items():
            day_count = calendar_counts.get((month, type_profil), 0)
            if day_count <= 0:
                continue
            for hour in range(24):
                daylight = max(0.0, math.cos((hour - 13.0) * math.pi / 12.0))
                share = daylight * seasonal * day_count
                if share <= 0:
                    continue
                total += share
                weights.append(
                    {
                        "month": month,
                        "day_type": day_type,
                        "hour": hour,
                        "share": share,
                    }
                )
    if total <= 0:
        return []
    return [{**item, "share": item["share"] / total} for item in weights]


def _compute_market_profile_stats(
    *,
    year: int,
    scenario_key: str,
    site_profile_weights: list[dict[str, Any]] | None,
) -> dict[str, float | None]:
    projection_rows = _load_projection_rows()
    price_key = _market_price_key(scenario_key)
    negative_key = _market_negative_key(scenario_key)
    calendar_counts = _calendar_daytype_counts(year)

    market_price_sum = 0.0
    market_negative_sum = 0.0
    market_hours = 0.0

    for month in range(1, 13):
        for day_type, type_profil in TYPE_PROFIL_MAP.items():
            day_count = calendar_counts.get((month, type_profil), 0)
            if day_count <= 0:
                continue
            rows = projection_rows.get((year, month, type_profil), [])
            if not rows:
                continue
            for row in rows:
                hour_weight = float(day_count)
                market_price_sum += float(row[price_key]) * hour_weight
                market_negative_sum += float(row[negative_key]) * hour_weight
                market_hours += hour_weight

    market_avg_price = market_price_sum / market_hours if market_hours > 0 else None
    market_negative_share = market_negative_sum / market_hours if market_hours > 0 else None

    if not site_profile_weights:
        return {
            "market_avg_price": market_avg_price,
            "market_negative_share": market_negative_share,
            "site_capture_ratio": None,
            "site_negative_energy_share": None,
        }

    weighted_price = 0.0
    weighted_negative = 0.0
    total_share = 0.0

    for weight in site_profile_weights:
        try:
            month = int(weight["month"])
            hour = int(weight["hour"])
            day_type = str(weight["day_type"])
            share = float(weight["share"])
        except (KeyError, TypeError, ValueError):
            continue
        if share <= 0:
            continue
        type_profil = TYPE_PROFIL_MAP.get(day_type, "Jour ouvré")
        rows = projection_rows.get((year, month, type_profil), [])
        if not rows:
            continue
        hour_row = _build_hour_lookup(rows).get(hour)
        if not hour_row:
            continue
        weighted_price += float(hour_row[price_key]) * share
        weighted_negative += float(hour_row[negative_key]) * share
        total_share += share

    if total_share <= 0:
        return {
            "market_avg_price": market_avg_price,
            "market_negative_share": market_negative_share,
            "site_capture_ratio": None,
            "site_negative_energy_share": None,
        }

    normalized_capture_price = weighted_price / total_share
    normalized_negative_share = weighted_negative / total_share
    capture_ratio = (
        max(0.1, min(normalized_capture_price / market_avg_price, 1.2))
        if market_avg_price and market_avg_price != 0
        else None
    )

    return {
        "market_avg_price": market_avg_price,
        "market_negative_share": market_negative_share,
        "site_capture_ratio": capture_ratio,
        "site_negative_energy_share": max(0.0, min(normalized_negative_share, 1.0)),
    }


def generate_price_forecast(
    *,
    scenario: str,
    start_year: int,
    end_year: int,
    baseload_start_eur_mwh: float,
    annual_production_mwh: float | None = None,
    site_profile_basis: str | None = None,
    site_profile_weights: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    scenario_key = scenario.lower().strip()
    rows: list[dict[str, Any]] = []
    effective_profile_weights = site_profile_weights
    profile_basis = site_profile_basis or "portfolio"
    peak_negative_hours_pct = 0.0
    annual_market_stats: dict[int, dict[str, float | None]] = {}

    for year in range(start_year, end_year + 1):
        stats = _compute_market_profile_stats(
            year=year,
            scenario_key=scenario_key,
            site_profile_weights=effective_profile_weights if effective_profile_weights else _generic_solar_profile_weights(year),
        )
        annual_market_stats[year] = stats
        peak_negative_hours_pct = max(peak_negative_hours_pct, float(stats.get("market_negative_share") or 0.0))

    source_start_avg = float(annual_market_stats.get(start_year, {}).get("market_avg_price") or 0.0)
    scaling_factor = baseload_start_eur_mwh / source_start_avg if source_start_avg > 0 else 1.0

    for year in range(start_year, end_year + 1):
        market_stats = annual_market_stats[year]
        avg_price = float(market_stats.get("market_avg_price") or 0.0) * scaling_factor
        negative_hours_pct = max(0.0, min(float(market_stats.get("market_negative_share") or 0.0), 0.95))
        capture_ratio = market_stats.get("site_capture_ratio")
        solar_capture_price = avg_price * float(capture_ratio) if capture_ratio is not None else avg_price
        site_negative_energy_share = market_stats.get("site_negative_energy_share")
        if site_negative_energy_share is None and annual_production_mwh is not None:
            site_negative_energy_share = max(0.0, min(negative_hours_pct * SOLAR_EXPOSURE_FACTOR, 1.0))
        negative_price_energy_mwh = annual_production_mwh * float(site_negative_energy_share) if annual_production_mwh is not None and site_negative_energy_share is not None else None

        if avg_price > 0:
            pv_cannibalization_index = max(0.0, min((avg_price - solar_capture_price) / avg_price, 1.0))
        else:
            pv_cannibalization_index = 0.0
        bess_relief_index = (
            max(0.0, min((peak_negative_hours_pct - negative_hours_pct) / peak_negative_hours_pct, 1.0))
            if peak_negative_hours_pct > 0
            else 0.0
        )

        rows.append(
            {
                "year": year,
                "avg_price_eur_mwh": round(avg_price, 2),
                "solar_capture_price_eur_mwh": round(solar_capture_price, 2),
                "negative_hours_pct": round(negative_hours_pct, 4),
                "negative_hours_estimate": int(round(negative_hours_pct * 8760)),
                "pv_cannibalization_index": round(pv_cannibalization_index, 4),
                "bess_relief_index": round(bess_relief_index, 4),
                "negative_price_capture_share": round(float(site_negative_energy_share), 4) if site_negative_energy_share is not None else None,
                "negative_price_energy_mwh": round(negative_price_energy_mwh, 1) if negative_price_energy_mwh is not None else None,
                "site_profile_basis": profile_basis,
            }
        )

    return {
        "scenario": scenario_key,
        "start_year": start_year,
        "end_year": end_year,
        "baseload_start_eur_mwh": baseload_start_eur_mwh,
        "annual_production_mwh": round(annual_production_mwh, 1) if annual_production_mwh is not None else None,
        "site_profile_basis": profile_basis,
        "rows": rows,
        "notes": [
            "Forecast adapted from the external day-ahead methodology already prepared for the Retrofit BESS consultancy workflow.",
            "Annual market price and negative-hour trends are aggregated directly from the consultancy day-ahead projection CSV.",
            "When long-term correlation exists, REVEAL injects the site-specific hourly production shape into capture-price and negative-energy estimates.",
        ],
    }


def get_hourly_profile(
    *,
    year: int,
    month: int,
    day_type: str,
    scenario: str,
) -> dict[str, Any]:
    """Return the 24-hour projected price profile bundle from the pre-computed CSV."""
    type_profil = TYPE_PROFIL_MAP.get(day_type, "Jour ouvré")
    scenario_key = scenario.lower().strip()

    projection_rows = _load_projection_rows()
    historical_profiles = _load_historical_profiles()
    rows = projection_rows.get((year, month, type_profil), [])

    if not rows:
        return {
            "year": year,
            "month": month,
            "day_type": day_type,
            "scenario": scenario_key,
            "rows": [],
            "available": False,
            "available_scenarios": ["base", "high", "low"],
            "historical_available": False,
            "type_label": type_profil,
            "month_label": MONTH_NAMES.get(month, str(month)),
            "error": "Projected hourly price data is not available for this combination.",
        }

    historical_lookup = historical_profiles.get((month, type_profil), {})
    enriched_rows = []
    for row in rows:
        enriched_rows.append(
            {
                **row,
                "historical_price_eur_mwh": historical_lookup.get(row["hour"]),
            }
        )

    return {
        "year": year,
        "month": month,
        "day_type": day_type,
        "scenario": scenario_key,
        "rows": enriched_rows,
        "available": len(enriched_rows) == 24,
        "available_scenarios": ["base", "high", "low"],
        "historical_available": bool(historical_lookup),
        "type_label": type_profil,
        "month_label": MONTH_NAMES.get(month, str(month)),
    }


def evaluate_retrofit_bess(
    *,
    site_name: str,
    annual_negative_price_energy_mwh: float,
    battery_power_kw: float,
    battery_energy_kwh: float,
    battery_cost_eur_kwh: float,
    battery_roundtrip_efficiency_pct: float,
    site_tariff_eur_mwh: float,
    estimated_land_area_m2: float | None = None,
) -> dict[str, Any]:
    battery_energy_mwh = max(battery_energy_kwh, 0.0) / 1000.0
    battery_power_mw = max(battery_power_kw, 0.0) / 1000.0
    duration_hours = battery_energy_mwh / battery_power_mw if battery_power_mw > 0 else 0.0
    roundtrip_efficiency = max(min(battery_roundtrip_efficiency_pct, 100.0), 0.0) / 100.0
    annual_negative_price_energy_mwh = max(annual_negative_price_energy_mwh, 0.0)
    site_tariff_eur_mwh = max(site_tariff_eur_mwh, 0.0)

    implied_cycles = min(330.0, max(0.0, annual_negative_price_energy_mwh / battery_energy_mwh)) if battery_energy_mwh > 0 else 0.0
    annual_shifted_energy_mwh = min(annual_negative_price_energy_mwh, battery_energy_mwh * implied_cycles * roundtrip_efficiency)
    annual_revenue_uplift_eur = annual_shifted_energy_mwh * site_tariff_eur_mwh
    placeholder_capex_eur = max(battery_energy_kwh, 0.0) * max(battery_cost_eur_kwh, 0.0)
    simple_payback_years = placeholder_capex_eur / annual_revenue_uplift_eur if annual_revenue_uplift_eur > 0 else None
    land_area = estimated_land_area_m2 if estimated_land_area_m2 is not None and estimated_land_area_m2 > 0 else battery_energy_mwh * 30.0

    if simple_payback_years is None:
        recommendation = "Insufficient recoverable negative-price value to justify a first-pass retrofit case yet."
    elif simple_payback_years <= 6:
        recommendation = "The first-pass screen looks promising. Move to hourly dispatch modelling and interconnection review."
    elif simple_payback_years <= 10:
        recommendation = "The case may work if curtailment intensity, capture spread, or EPC pricing improve. Refine the dispatch model next."
    else:
        recommendation = "At placeholder assumptions, the retrofit case looks weak. Focus next on verifying curtailed energy, grid constraints, and site-specific capex before progressing."

    return {
        "site_name": site_name,
        "battery_power_kw": round(battery_power_kw, 1),
        "battery_energy_kwh": round(battery_energy_kwh, 1),
        "battery_duration_hours": round(duration_hours, 2),
        "estimated_land_area_m2": round(land_area, 1),
        "placeholder_capex_eur": round(placeholder_capex_eur, 2),
        "annual_negative_price_energy_mwh": round(annual_negative_price_energy_mwh, 2),
        "annual_shifted_energy_mwh": round(annual_shifted_energy_mwh, 2),
        "site_tariff_eur_mwh": round(site_tariff_eur_mwh, 2),
        "annual_revenue_uplift_eur": round(annual_revenue_uplift_eur, 2),
        "implied_cycles_per_year": round(implied_cycles, 1),
        "simple_payback_years": round(simple_payback_years, 2) if simple_payback_years is not None else None,
        "recommendation": recommendation,
        "notes": [
            "Simple payback = placeholder CAPEX / annual uplift, where annual uplift = annual shifted energy x site tariff.",
            "Retrofit BESS screening assumes a one-directional battery that only stores curtailed on-site renewable energy and re-injects it at the site's saved tariff.",
            "This methodology does not assume grid charging or standalone merchant arbitrage spread capture.",
            "Annual shifted energy is capped by the negative-price energy input, battery energy capacity, implied cycles/year, and round-trip efficiency.",
            "Negative-price energy should come from the REVEAL Performance analysis rather than a manual estimate wherever possible.",
            "Land-use is currently an indicative planning check and should be refined against OEM layout drawings, PCS, transformer, and fire-separation requirements.",
        ],
    }
