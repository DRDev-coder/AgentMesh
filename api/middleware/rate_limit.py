from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    """Bounded per-process demo limiter for the expensive chat endpoint."""

    def __init__(self, app):
        super().__init__(app)
        self.limit = max(0, int(os.getenv("RATE_LIMIT_REQUESTS", "30")))
        self.window = max(1, int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")))
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    async def dispatch(self, request, call_next):
        if self.limit and request.url.path.endswith("/api/v1/chat"):
            client = request.client.host if request.client else "unknown"
            now = time.monotonic()
            with self._lock:
                bucket = self._requests[client]
                cutoff = now - self.window
                while bucket and bucket[0] <= cutoff:
                    bucket.popleft()
                if len(bucket) >= self.limit:
                    retry_after = max(1, int(self.window - (now - bucket[0])))
                    return JSONResponse(
                        {"detail": "Rate limit exceeded. Try again later."},
                        status_code=429,
                        headers={"Retry-After": str(retry_after)},
                    )
                bucket.append(now)
        return await call_next(request)
