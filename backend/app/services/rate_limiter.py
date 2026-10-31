import math
import time
from typing import Callable, Dict, List
from fastapi import HTTPException, Request

try:
    from app.config import settings
except ImportError:
    from backend.app.config import settings


class SlidingWindowRateLimiter:
    """
    In-memory sliding-window rate limiter for public AI endpoints.
    Tracks timestamps per client IP, enforces memory bounds via pruning,
    and supports clock injection for deterministic testing.
    """

    def __init__(
        self,
        window_seconds: float = 60.0,
        max_tracked_ips: int = 5000,
        clock: Callable[[], float] = time.time,
    ):
        self.window_seconds = window_seconds
        self.max_tracked_ips = max_tracked_ips
        self.clock = clock
        self._requests: Dict[str, List[float]] = {}

    def get_client_ip(self, request: Request) -> str:
        if settings.trust_proxy_headers:
            xff = request.headers.get("x-forwarded-for")
            if xff:
                # Use the client's original IP (first entry in comma-separated header)
                first_ip = xff.split(",")[0].strip()
                if first_ip:
                    return first_ip
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    def _prune_expired(self, now: float):
        cutoff = now - self.window_seconds
        expired_keys = [
            ip for ip, timestamps in self._requests.items()
            if not timestamps or timestamps[-1] < cutoff
        ]
        for ip in expired_keys:
            del self._requests[ip]

    def check(self, request: Request):
        limit = settings.ai_rate_limit_per_minute
        if limit <= 0:
            return  # Rate limiting disabled via configuration

        now = self.clock()
        ip = self.get_client_ip(request)

        # Enforce memory bounds
        if len(self._requests) >= self.max_tracked_ips:
            self._prune_expired(now)

        cutoff = now - self.window_seconds
        timestamps = self._requests.get(ip, [])
        # Retain only timestamps within the sliding window
        timestamps = [t for t in timestamps if t > cutoff]

        if len(timestamps) >= limit:
            oldest = timestamps[0]
            retry_after = max(1, math.ceil(self.window_seconds - (now - oldest)))
            raise HTTPException(
                status_code=429,
                detail=f"Too many AI requests. Please slow down and try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

        timestamps.append(now)
        self._requests[ip] = timestamps

    def reset(self):
        """Resets all tracked request records (for tests)."""
        self._requests.clear()


ai_rate_limiter = SlidingWindowRateLimiter()


def rate_limit_ai_endpoint(request: Request):
    """FastAPI dependency applied to AI generation and reasoning endpoints."""
    ai_rate_limiter.check(request)

