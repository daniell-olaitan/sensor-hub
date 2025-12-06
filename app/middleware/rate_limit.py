from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.rate_limiter import get_rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/telemetry"):
            rate_limiter = get_rate_limiter()
            allowed, remaining = await rate_limiter.check_global_rate_limit()

            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"error": "Rate limit exceeded"},
                    headers={"X-RateLimit-Remaining": "0"},
                )

        response = await call_next(request)
        return response
