from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.models.telemetry import TelemetryBatch, TelemetryPoint, TelemetryQuery
from app.services.telemetry_service import get_telemetry_service

router = APIRouter()


@router.post("/point", status_code=202)
async def ingest_point(point: TelemetryPoint):
    service = get_telemetry_service()
    try:
        await service.ingest_point(point)
        return {"status": "accepted"}
    except ValueError as e:
        if "Rate limit exceeded" in str(e):
            raise HTTPException(status_code=429, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch", status_code=202)
async def ingest_batch(batch: TelemetryBatch):
    service = get_telemetry_service()
    try:
        await service.ingest_batch(batch)
        return {"status": "accepted", "count": len(batch.points)}
    except ValueError as e:
        if "Rate limit exceeded" in str(e):
            raise HTTPException(status_code=429, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{device_id}", response_model=list[TelemetryPoint])
async def query_telemetry(
    device_id: str,
    metric: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100,
):
    service = get_telemetry_service()
    query = TelemetryQuery(
        device_id=device_id,
        metric=metric,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
    return await service.query_telemetry(query)


@router.get("/{device_id}/{metric}/latest", response_model=TelemetryPoint)
async def get_latest(device_id: str, metric: str):
    service = get_telemetry_service()
    point = await service.get_latest(device_id, metric)
    if not point:
        raise HTTPException(
            status_code=404, detail=f"No telemetry for {device_id}/{metric}"
        )
    return point
