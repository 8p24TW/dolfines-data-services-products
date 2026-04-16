import json
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services.charting import build_chart_data, detect_chart_time_range, fetch_chart_reference_irradiance

router = APIRouter()


@router.post("/charting")
async def charting_endpoint(
    file: Annotated[UploadFile, File()],
    time_column: Annotated[str, Form()],
    series: Annotated[str, Form()],
    worksheet: Annotated[str | None, Form()] = None,
    start_date: Annotated[str | None, Form()] = None,
    end_date: Annotated[str | None, Form()] = None,
    aggregation: Annotated[str, Form()] = "hourly",
    site_timezone: Annotated[str, Form()] = "UTC",
):
    try:
        payload = json.loads(series)
        file_bytes = await file.read()
        return build_chart_data(
            file_bytes=file_bytes,
            filename=file.filename or "uploaded-file",
            time_column=time_column,
            series=payload,
            worksheet=worksheet,
            start_date=start_date,
            end_date=end_date,
            aggregation=aggregation,
            site_timezone=site_timezone,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/charting/date-range")
async def charting_date_range_endpoint(
    file: Annotated[UploadFile, File()],
    time_column: Annotated[str, Form()],
    worksheet: Annotated[str | None, Form()] = None,
):
    try:
        file_bytes = await file.read()
        return detect_chart_time_range(
            file_bytes=file_bytes,
            filename=file.filename or "uploaded-file",
            time_column=time_column,
            worksheet=worksheet,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/charting/reference-irradiance")
async def charting_reference_irradiance_endpoint(
    source: Annotated[str, Form()] = "era5-land",
    latitude: Annotated[float, Form()] = 0.0,
    longitude: Annotated[float, Form()] = 0.0,
    start_date: Annotated[str, Form()] = "2023-01-01",
    end_date: Annotated[str, Form()] = "2024-12-31",
    aggregation: Annotated[str, Form()] = "hourly",
    site_timezone: Annotated[str, Form()] = "UTC",
    irradiance_basis: Annotated[str, Form()] = "poa",
    tracker_mode: Annotated[str, Form()] = "fixed-tilt",
    irradiance_tilt_deg: Annotated[float, Form()] = 0.0,
):
    try:
        return fetch_chart_reference_irradiance(
            source=source,
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            end_date=end_date,
            aggregation=aggregation,
            site_timezone=site_timezone,
            irradiance_basis=irradiance_basis,
            tracker_mode=tracker_mode,
            irradiance_tilt_deg=irradiance_tilt_deg,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
