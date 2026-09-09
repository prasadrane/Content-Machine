"""In-memory per-IP POST rate limit (public demo quota guard)."""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token window: at most `limit_per_min` POST /api/* requests per IP per 60s."""

    def __init__(self, app, limit_per_min: int = 10):
        super().__init__(app)
        self.limit_per_min = limit_per_min
        self._hits: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and request.url.path.startswith("/api/"):
            ip = request.client.host if request.client else "unknown"
            now = time.time()
            window = [t for t in self._hits.get(ip, []) if now - t < 60.0]
            if len(window) >= self.limit_per_min:
                return JSONResponse(
                    {"detail": "demo rate limit reached: try again in a minute"},
                    status_code=429,
                )
            window.append(now)
            self._hits[ip] = window
        return await call_next(request)
