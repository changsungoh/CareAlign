import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request

from app.core.config import settings

_requests: dict[str, deque[float]] = defaultdict(deque)
_daily: deque[float] = deque()
_lock = Lock()


def client_key(request: Request) -> str:
    """Identify the caller; behind N trusted proxies use the entry the last proxy appended.

    The left-most X-Forwarded-For value is client-controlled and therefore spoofable, so it
    is only read from the right and only when ``trusted_proxy_hops`` is configured.
    """
    hops = settings.trusted_proxy_hops
    if hops > 0:
        forwarded = [
            part.strip()
            for part in request.headers.get("x-forwarded-for", "").split(",")
            if part.strip()
        ]
        if len(forwarded) >= hops:
            return forwarded[-hops]
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(request: Request) -> None:
    now = time.time()
    key = client_key(request)
    with _lock:
        for stale in [k for k, q in _requests.items() if k != key and (not q or q[-1] < now - 60)]:
            del _requests[stale]
        while _requests[key] and _requests[key][0] < now - 60:
            _requests[key].popleft()
        if len(_requests[key]) >= settings.rate_limit_per_minute:
            raise HTTPException(429, "Too many requests. Please wait one minute.")
        _requests[key].append(now)


def enforce_analysis_budget(request: Request) -> None:
    enforce_rate_limit(request)
    if settings.demo_mode:
        return
    now = time.time()
    with _lock:
        while _daily and _daily[0] < now - 86400:
            _daily.popleft()
        if len(_daily) >= settings.daily_request_limit:
            raise HTTPException(503, "Daily live-analysis budget reached.")
        _daily.append(now)
