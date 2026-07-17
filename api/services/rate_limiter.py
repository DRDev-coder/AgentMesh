from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

import redis

from api.config import Settings
from api.errors import APIError


class DistributedRateLimiter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = redis.Redis.from_url(
            settings.redis_url, decode_responses=True, socket_timeout=0.5
        )
        self._fallback: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._redis_retry_after = 0.0

    def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        bucket = int(time.time()) // window_seconds
        redis_key = f"agentmesh:rate:{key}:{bucket}"
        if time.monotonic() >= self._redis_retry_after:
            try:
                pipeline = self.client.pipeline(transaction=True)
                pipeline.incr(redis_key)
                pipeline.expire(redis_key, window_seconds + 5)
                count, _ = pipeline.execute()
                if int(count) > limit:
                    raise APIError(
                        429,
                        "rate_limit_exceeded",
                        "Rate limit exceeded. Try again later.",
                        headers={"Retry-After": str(window_seconds)},
                    )
                return
            except APIError:
                raise
            except Exception as exc:
                if self.settings.environment not in {"development", "test"}:
                    raise APIError(
                        503,
                        "rate_limit_unavailable",
                        "Request protection is temporarily unavailable.",
                    ) from exc
                self._redis_retry_after = time.monotonic() + 5.0
        now = time.monotonic()
        with self._lock:
            values = self._fallback[key]
            while values and values[0] <= now - window_seconds:
                values.popleft()
            if len(values) >= limit:
                raise APIError(
                    429,
                    "rate_limit_exceeded",
                    "Rate limit exceeded. Try again later.",
                    headers={"Retry-After": str(window_seconds)},
                )
            values.append(now)
