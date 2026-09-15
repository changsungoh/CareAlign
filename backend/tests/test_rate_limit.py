import time

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core.config import settings
from app.services import rate_limit


def request(host: str = "198.51.100.7") -> Request:
    return Request({"type": "http", "client": (host, 1234), "headers": []})


@pytest.fixture(autouse=True)
def clear_limits() -> None:
    rate_limit._requests.clear()
    rate_limit._daily.clear()


def test_minute_limit_blocks_only_after_configured_allowance(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_per_minute", 2)
    monkeypatch.setattr(settings, "daily_request_limit", 10)
    rate_limit.enforce_rate_limit(request())
    rate_limit.enforce_rate_limit(request())
    with pytest.raises(HTTPException) as error:
        rate_limit.enforce_rate_limit(request())
    assert error.value.status_code == 429


def test_daily_budget_blocks_new_live_work(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_per_minute", 10)
    monkeypatch.setattr(settings, "daily_request_limit", 1)
    rate_limit.enforce_rate_limit(request("198.51.100.7"))
    with pytest.raises(HTTPException) as error:
        rate_limit.enforce_rate_limit(request("203.0.113.9"))
    assert error.value.status_code == 503


def test_expired_entries_are_pruned(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_per_minute", 1)
    monkeypatch.setattr(settings, "daily_request_limit", 1)
    expired = time.time() - 90_000
    rate_limit._requests["198.51.100.7"].append(expired)
    rate_limit._daily.append(expired)
    rate_limit.enforce_rate_limit(request())
    assert len(rate_limit._requests["198.51.100.7"]) == 1
    assert len(rate_limit._daily) == 1
