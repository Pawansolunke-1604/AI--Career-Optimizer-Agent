"""In-memory sliding-window rate limiter. Protects the shared free Gemini quota."""
import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.exceptions import RateLimitError


class SlidingWindowLimiter:
    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_s: int, now: float | None = None) -> int:
        """Return 0 if allowed (and record the hit), else seconds to wait."""
        now = time.monotonic() if now is None else now
        with self._lock:
            q = self._hits[key]
            while q and q[0] <= now - window_s:
                q.popleft()
            if len(q) >= limit:
                return int(q[0] + window_s - now) + 1
            q.append(now)
            if len(self._hits) > 10_000:  # keep memory bounded
                for k in [k for k, v in self._hits.items() if not v]:
                    del self._hits[k]
            return 0


limiter = SlidingWindowLimiter()


def rate_limit(name: str, per_ip: int, window_s: int, global_limit: int | None = None,
               global_window_s: int = 60):
    """FastAPI dependency. global_limit caps ALL users together (your one Gemini key is shared)."""
    def dependency(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        wait = limiter.check(f"{name}:ip:{ip}", per_ip, window_s)
        if not wait and global_limit:
            wait = limiter.check(f"{name}:global", global_limit, global_window_s)
        if wait:
            raise RateLimitError(f"Too many requests right now. Please try again in {wait} seconds.")
    return dependency