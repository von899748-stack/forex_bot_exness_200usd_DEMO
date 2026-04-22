"""Rate limiter for API/orders"""
import time
from typing import Dict, Optional
from dataclasses import dataclass
from threading import Lock


@dataclass
class RateLimit:
    """Rate limit configuration"""
    max_calls: int
    period: float  # seconds
    burst: int = 0


class RateLimiter:
    """Simple token bucket rate limiter"""

    def __init__(self):
        self.limits: Dict[str, RateLimit] = {}
        self._tokens: Dict[str, float] = {}
        self._last_update: Dict[str, float] = {}
        self._lock = Lock()

    def add_limit(self, key: str, max_calls: int, period: float):
        """Add a rate limit for a key"""
        self.limits[key] = RateLimit(max_calls=max_calls, period=period)
        self._tokens[key] = float(max_calls)
        self._last_update[key] = time.time()

    async def acquire(self, key: str = "default") -> bool:
        """
        Acquire a token for operation. Returns False if rate limit exceeded.
        """
        with self._lock:
            if key not in self.limits:
                self.add_limit(key, max_calls=10, period=1.0)

            limit = self.limits[key]
            now = time.time()
            elapsed = now - self._last_update[key]

            # Add tokens based on elapsed time
            refill_rate = limit.max_calls / limit.period
            new_tokens = elapsed * refill_rate
            self._tokens[key] = min(limit.max_calls, self._tokens[key] + new_tokens)
            self._last_update[key] = now

            if self._tokens[key] >= 1:
                self._tokens[key] -= 1
                return True
            return False
