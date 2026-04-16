import json
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services.long_term import correlate_long_term_solar, fetch_reference_weather

router = APIRouter()


@router.post("/long-term/reference")
async def fetch_reference_endpoint(
    source: Annotated[str, Form()] = "era5-land",
    site_type: Annotated[str, Form()] = "solar",
    latitude: Annotated[float, Form()] = 0.0,
    longitude: Annotated[float, Form()] = 0.0,
    start_date: Annotated[str, Form()] = "2023-01-01",
    end_date: Annotated[str, Form()] = "2024-12-31",
):
    try:
        return fetch_reference_weather(
            source=source,
            site_type=site_type,
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/long-term/correlate")
async def correlate_long_term_endpoint(
    file: UploadFile = File(...),
    site_type: Annotated[str, Form()] = "solar",
    source: Annotated[str, Form()] = "era5-land",
    latitude: Annotated[float, Form()] = 0.0,
    longitude: Annotated[float, Form()] = 0.0,
    start_date: Annotated[str, Form()] = "2023-01-01",
    end_date: Annotated[str, Form()] = "2024-12-31",
    correlation_years: Annotated[int, Form()] = 20,
    dc_capacity_kwp: Annotated[float, Form()] = 0.0,
    ac_capacity_kw: Annotated[float, Form()] = 0.0,
    specific_yield_kwh_kwp: Annotated[float, Form()] = 0.0,
    yield_scenario: Annotated[str, Form()] = "measured",
    run_mode: Annotated[str, Form()] = "preview",
    site_timezone: Annotated[str, Form()] = "UTC",
    irradiance_basis: Annotated[str, Form()] = "poa",
    tracker_mode: Annotated[str, Form()] = "fixed-tilt",
    irradiance_tilt_deg: Annotated[float, Form()] = 0.0,
    column_mappings: Annotated[str, Form()] = "{}",
):
    try:
        if site_type != "solar":
            raise HTTPException(status_code=400, detail="Long-term correlation is currently implemented for solar sites only.")

        try:
            mappings = json.loads(column_mappings or "{}")
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid column_mappings payload.") from exc

        return correlate_long_term_solar(
            file_bytes=await file.read(),
            filename=file.filename or "uploaded.csv",
            column_mappings=mappings,
            source=source,
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            end_date=end_date,
            correlation_years=correlation_years,
            dc_capacity_kwp=dc_capacity_kwp,
            ac_capacity_kw=ac_capacity_kw,
            specific_yield_kwh_kwp=specific_yield_kwh_kwp,
            yield_scenario=yield_scenario,
            run_mode=run_mode,
            site_timezone=site_timezone,
            irradiance_basis=irradiance_basis,
            tracker_mode=tracker_mode,
            irradiance_tilt_deg=irradiance_tilt_deg,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
