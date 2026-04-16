from fastapi import APIRouter
from pydantic import BaseModel

from fastapi import Query
from app.services.market import evaluate_retrofit_bess, generate_price_forecast, get_hourly_profile

router = APIRouter()


class PriceForecastRequest(BaseModel):
    site_id: str | None = None
    site_name: str | None = None
    scenario: str = "base"
    start_year: int = 2027
    end_year: int = 2046
    baseload_start_eur_mwh: float = 70.0
    annual_production_mwh: float | None = None
    site_profile_basis: str | None = None
    site_profile_weights: list[dict[str, float | int | str]] | None = None


class RetrofitBessRequest(BaseModel):
    site_id: str | None = None
    site_name: str = "Site"
    annual_production_mwh: float | None = None
    annual_negative_price_energy_mwh: float = 0.0
    battery_power_kw: float = 0.0
    battery_energy_kwh: float = 0.0
    battery_cost_eur_kwh: float = 200.0
    battery_roundtrip_efficiency_pct: float = 88.0
    site_tariff_eur_mwh: float = 0.0
    estimated_land_area_m2: float | None = None


@router.post("/market/price-forecast")
async def market_price_forecast_endpoint(payload: PriceForecastRequest):
    return generate_price_forecast(
        scenario=payload.scenario,
        start_year=payload.start_year,
        end_year=payload.end_year,
        baseload_start_eur_mwh=payload.baseload_start_eur_mwh,
        annual_production_mwh=payload.annual_production_mwh,
        site_profile_basis=payload.site_profile_basis,
        site_profile_weights=payload.site_profile_weights,
    )


@router.get("/market/hourly-profile")
async def market_hourly_profile_endpoint(
    year: int = Query(2027, ge=2027, le=2046),
    month: int = Query(6, ge=1, le=12),
    day_type: str = Query("ouvre"),
    scenario: str = Query("base"),
):
    return get_hourly_profile(year=year, month=month, day_type=day_type, scenario=scenario)


@router.post("/market/retrofit-bess")
async def market_retrofit_bess_endpoint(payload: RetrofitBessRequest):
    return evaluate_retrofit_bess(
        site_name=payload.site_name,
        annual_negative_price_energy_mwh=payload.annual_negative_price_energy_mwh,
        battery_power_kw=payload.battery_power_kw,
        battery_energy_kwh=payload.battery_energy_kwh,
        battery_cost_eur_kwh=payload.battery_cost_eur_kwh,
        battery_roundtrip_efficiency_pct=payload.battery_roundtrip_efficiency_pct,
        site_tariff_eur_mwh=payload.site_tariff_eur_mwh,
        estimated_land_area_m2=payload.estimated_land_area_m2,
    )
