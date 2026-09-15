import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request

from app.core.config import settings

_requests: dict[str, deque[float]] = defaultdict(deque)
_daily: deque[float] = deque()
_lock = Lock()


def enforce_rate_limit(request: Request) -> None:
    now = time.time()
    key = request.client.host if request.client else "unknown"
    with _lock:
        while _requests[key] and _requests[key][0] < now - 60:
            _requests[key].popleft()
        while _daily and _daily[0] < now - 86400:
            _daily.popleft()
        if len(_requests[key]) >= settings.rate_limit_per_minute:
            raise HTTPException(429, "Too many requests. Please wait one minute.")
        if len(_daily) >= settings.daily_request_limit:
            raise HTTPException(503, "Daily live-analysis budget reached.")
        _requests[key].append(now)
        _daily.append(now)
