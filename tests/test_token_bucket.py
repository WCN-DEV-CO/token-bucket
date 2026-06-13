import threading, time
import pytest
from token_bucket import TokenBucket, RateLimitExceeded, rate_limited

class FakeClock:
    def __init__(self): self.t=0.0
    def __call__(self): return self.t
    def advance(self,dt): self.t+=dt

def test_starts_full():
    tb=TokenBucket(rate=10, capacity=10); assert tb.tokens==10

def test_consume_and_refill():
    c=FakeClock(); tb=TokenBucket(rate=10, capacity=10, clock=c)
    assert tb.try_acquire(10)
    assert not tb.try_acquire(1)
    c.advance(0.5)
    assert tb.try_acquire(5)
    assert not tb.try_acquire(1)

def test_capacity_caps_refill():
    c=FakeClock(); tb=TokenBucket(rate=10, capacity=10, clock=c)
    tb.try_acquire(10); c.advance(100)
    assert tb.tokens==10

def test_nonblocking_raises_with_retry_after():
    c=FakeClock(); tb=TokenBucket(rate=2, capacity=2, clock=c)
    tb.try_acquire(2)
    with pytest.raises(RateLimitExceeded) as ei:
        tb.acquire(1, block=False)
    assert ei.value.retry_after == pytest.approx(0.5, abs=1e-6)

def test_acquire_more_than_capacity_errors():
    tb=TokenBucket(rate=5, capacity=5)
    with pytest.raises(ValueError): tb.acquire(6)

def test_invalid_params():
    with pytest.raises(ValueError): TokenBucket(rate=0)
    with pytest.raises(ValueError): TokenBucket(rate=5, capacity=0)

def test_blocking_with_timeout_returns_false():
    tb=TokenBucket(rate=1, capacity=1)
    assert tb.try_acquire(1)
    t0=time.monotonic()
    assert tb.acquire(1, block=True, timeout=0.05) is False
    assert time.monotonic()-t0 >= 0.05

def test_burst_then_sustained():
    c=FakeClock(); tb=TokenBucket(rate=10, capacity=20, clock=c)
    assert tb.try_acquire(20)
    assert not tb.try_acquire(1)
    c.advance(1.0)
    assert tb.try_acquire(10)

def test_decorator_limits_calls():
    calls=[]
    @rate_limited(rate=1000, capacity=2)
    def f(): calls.append(1)
    f(); f()
    assert len(calls)==2
    assert hasattr(f,"bucket")

def test_thread_safe_no_oversell():
    c_tokens=50
    tb=TokenBucket(rate=1, capacity=c_tokens)
    grabbed=[]; lock=threading.Lock()
    def worker():
        if tb.try_acquire(1):
            with lock: grabbed.append(1)
    threads=[threading.Thread(target=worker) for _ in range(200)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert len(grabbed)==c_tokens
