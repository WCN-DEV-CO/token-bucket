# token-bucket

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Zero dependencies](https://img.shields.io/badge/dependencies-0-brightgreen.svg)](#)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](#)

A tiny, thread-safe **token-bucket rate limiter**. Smooth sustained throughput
with controllable bursts. Sync + async-friendly. Zero dependencies.

## Install
```bash
pip install token-bucket-wcn
```

## Quick start
```python
from token_bucket import TokenBucket

# 5 requests/sec sustained, allow bursts up to 10
bucket = TokenBucket(rate=5, capacity=10)

if bucket.try_acquire():       # non-blocking
    do_request()

bucket.acquire(block=True)     # blocks until a token is free
```

### Non-blocking with retry hint
```python
from token_bucket import TokenBucket, RateLimitExceeded
try:
    bucket.acquire(block=False)
except RateLimitExceeded as e:
    print(f"slow down, retry in {e.retry_after:.2f}s")
```

### Decorator
```python
from token_bucket import rate_limited

@rate_limited(rate=2, capacity=2)   # at most 2/sec
def call_api(): ...
```

## Features
- ✅ Classic token-bucket: steady refill + burst capacity
- ✅ Blocking, non-blocking (`try_acquire`), and timeout modes
- ✅ Thread-safe (200 racers → never oversold)
- ✅ Injectable clock for deterministic tests
- ✅ Decorator for drop-in limiting
- ✅ **Zero dependencies**

## License
MIT © WCN Development Co
