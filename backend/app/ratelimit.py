"""A light per-token rate limit, so one runaway `useEffect` can't take the API
down for a whole stream."""

import threading
import time
from collections.abc import Callable


class RateLimiter:
    """A token bucket per key. It refills `rate` tokens per second and holds at most `burst`."""

    MAX_KEYS = 10_000

    def __init__(self, rate: float, burst: int, clock: Callable[[], float] = time.monotonic) -> None:
        self.rate = rate
        self.burst = burst
        self.clock = clock
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str) -> float | None:
        """Spend one request. Returns None if it is allowed, else the seconds to wait."""
        now = self.clock()
        with self._lock:
            tokens, updated = self._buckets.get(key, (float(self.burst), now))
            tokens = min(float(self.burst), tokens + (now - updated) * self.rate)
            if tokens < 1:
                self._buckets[key] = (tokens, now)
                return (1 - tokens) / self.rate
            if key not in self._buckets and len(self._buckets) >= self.MAX_KEYS:
                self._prune(now)
            self._buckets[key] = (tokens - 1, now)
            return None

    def _prune(self, now: float) -> None:
        # A bucket that has had time to refill completely carries no information.
        refill_time = self.burst / self.rate
        self._buckets = {k: v for k, v in self._buckets.items() if now - v[1] < refill_time}
