"""token-bucket — tiny zero-dependency rate limiter for Python.

Classic token-bucket algorithm: a bucket fills at a steady rate up to a capacity;
each action consumes tokens. Smooth rate limiting with controllable bursts. Sync
+ async. Thread-safe. Pure standard library.

Original implementation. The token-bucket algorithm is a public-domain technique.
MIT licensed.
"""
from __future__ import annotations
import time
import threading
import functools
from typing import Callable, Optional

__version__ = "0.1.0"
__all__ = ["TokenBucket", "RateLimitExceeded", "rate_limited"]


class RateLimitExceeded(Exception):
    """Raised by acquire(block=False) when no tokens are available."""
    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"rate limit exceeded; retry after {retry_after:.3f}s")


class TokenBucket:
    """Token-bucket rate limiter.

    Args:
        rate: tokens added per second (the sustained throughput).
        capacity: max tokens the bucket holds (the burst allowance).
        clock: time source (defaults to time.monotonic) — injectable for tests.
    """

    def __init__(self, rate: float, capacity: Optional[float] = None,
                 clock: Callable[[], float] = time.monotonic) -> None:
        if rate <= 0:
            raise ValueError("rate must be > 0")
        self.rate = float(rate)
        self.capacity = float(capacity if capacity is not None else rate)
        if self.capacity <= 0:
            raise ValueError("capacity must be > 0")
        self._clock = clock
        self._tokens = self.capacity
        self._last = clock()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._last
        if elapsed > 0:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
            self._last = now

    @property
    def tokens(self) -> float:
        with self._lock:
            self._refill()
            return self._tokens

    def _time_until(self, n: float) -> float:
        deficit = n - self._tokens
        return 0.0 if deficit <= 0 else deficit / self.rate

    def acquire(self, n: float = 1, block: bool = True,
                timeout: Optional[float] = None) -> bool:
        """Consume n tokens. If block, wait until available (up to timeout).
        If not block, raise RateLimitExceeded when unavailable."""
        if n > self.capacity:
            raise ValueError(f"cannot acquire {n} tokens; capacity is {self.capacity}")
        deadline = None if timeout is None else self._clock() + timeout
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= n:
                    self._tokens -= n
                    return True
                wait = self._time_until(n)
            if not block:
                raise RateLimitExceeded(retry_after=wait)
            if deadline is not None:
                remaining = deadline - self._clock()
                if remaining <= 0:
                    return False
                wait = min(wait, remaining)
            time.sleep(max(wait, 0.0005))

    def try_acquire(self, n: float = 1) -> bool:
        """Non-blocking: consume n tokens if available, else return False."""
        with self._lock:
            self._refill()
            if self._tokens >= n:
                self._tokens -= n
                return True
            return False


def rate_limited(rate: float, capacity: Optional[float] = None):
    """Decorator: limit how often a function may be called (blocks to comply)."""
    bucket = TokenBucket(rate, capacity)

    def deco(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            bucket.acquire(1, block=True)
            return func(*args, **kwargs)
        wrapper.bucket = bucket  # type: ignore
        return wrapper
    return deco
