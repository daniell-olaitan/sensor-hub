import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import alerts, analytics, devices, firmware, telemetry
from app.core.event_bus import get_event_bus
from app.core.redis_client import get_redis_client
from app.middleware.backpressure import BackpressureMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = await get_redis_client()
    event_bus = get_event_bus()
    await event_bus.start()
    logger.info("SensorHub started")
    yield
    await event_bus.stop()
    await redis_client.close()
    logger.info("SensorHub stopped")


app = FastAPI(title="SensorHub", version="1.0.0", lifespan=lifespan)

app.add_middleware(BackpressureMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(devices.router, prefix="/devices", tags=["devices"])
app.include_router(telemetry.router, prefix="/telemetry", tags=["telemetry"])
app.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
app.include_router(firmware.router, prefix="/firmware", tags=["firmware"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sensorhub"}


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.exception_handler(KeyError)
async def key_error_handler(request: Request, exc: KeyError):
    return JSONResponse(status_code=404, content={"error": str(exc)})
