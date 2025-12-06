from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config.settings import get_settings
from app.core.event_bus import get_event_bus


class BackpressureMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/telemetry"):
            event_bus = get_event_bus()
            settings = get_settings()
            queue_size = event_bus.get_queue_size()

            if queue_size >= settings.backpressure_reject_threshold:
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "Service unavailable due to high load",
                        "retry_after": 5,
                    },
                    headers={"Retry-After": "5"},
                )

            if queue_size >= settings.backpressure_queue_threshold:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too many requests, please slow down",
                        "queue_depth": queue_size,
                    },
                )

        response = await call_next(request)
        return response
