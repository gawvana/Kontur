import time
import os
from collections import defaultdict
from fastapi import Request, HTTPException

_in_memory_limits = defaultdict(list)

class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute

    async def __call__(self, request: Request):
        # Allow disabling in tests if explicitly set
        if os.environ.get("DISABLE_RATE_LIMIT", "0") == "1":
            return
        
        # Use client IP or X-Forwarded-For
        forwarded = request.headers.get("X-Forwarded-For")
        client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "127.0.0.1")
        key = f"{client_ip}:{request.url.path}"
        
        now = time.time()
        window_start = now - 60.0
        
        # Clean up older timestamps
        timestamps = [t for t in _in_memory_limits[key] if t > window_start]
        if len(timestamps) >= self.requests_per_minute:
            retry_after = int(timestamps[0] + 60.0 - now) + 1
            raise HTTPException(
                status_code=429,
                detail="Too Many Requests. Please slow down.",
                headers={"Retry-After": str(max(1, retry_after))}
            )
        
        timestamps.append(now)
        _in_memory_limits[key] = timestamps
