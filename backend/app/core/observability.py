import json
import logging
import re
import time
from contextvars import ContextVar
from uuid import uuid4

from fastapi import Request, Response

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_request_id: ContextVar[str] = ContextVar("request_id", default="unavailable")
logger = logging.getLogger("carealign.operations")


def current_request_id() -> str:
    return _request_id.get()


def safe_request_id(value: str | None) -> str:
    if value and REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return uuid4().hex


def log_event(event: str, *, level: int = logging.INFO, **fields: object) -> None:
    """Emit machine-readable operational metadata only; never pass clinical text here."""
    payload = {"event": event, "request_id": current_request_id(), **fields}
    logger.log(level, json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str))


async def observe_request(request: Request, call_next) -> Response:
    request_id = safe_request_id(request.headers.get("X-Request-ID"))
    token = _request_id.set(request_id)
    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        log_event(
            "http_request_completed",
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            duration_ms=duration_ms,
        )
        _request_id.reset(token)
