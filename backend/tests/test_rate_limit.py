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
    rate_limit.enforce_analysis_budget(request("198.51.100.7"))
    with pytest.raises(HTTPException) as error:
        rate_limit.enforce_analysis_budget(request("203.0.113.9"))
    assert error.value.status_code == 503


def test_teachback_rate_limit_does_not_consume_live_analysis_budget(monkeypatch) -> None:
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "rate_limit_per_minute", 10)
    monkeypatch.setattr(settings, "daily_request_limit", 1)
    rate_limit.enforce_rate_limit(request("198.51.100.7"))
    assert len(rate_limit._daily) == 0
    rate_limit.enforce_analysis_budget(request("203.0.113.9"))
    assert len(rate_limit._daily) == 1


def test_demo_analysis_does_not_consume_live_budget(monkeypatch) -> None:
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "rate_limit_per_minute", 10)
    monkeypatch.setattr(settings, "daily_request_limit", 1)
    rate_limit.enforce_analysis_budget(request())
    assert len(rate_limit._daily) == 0


def test_expired_entries_are_pruned(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_per_minute", 1)
    monkeypatch.setattr(settings, "daily_request_limit", 1)
    expired = time.time() - 90_000
    rate_limit._requests["198.51.100.7"].append(expired)
    rate_limit._daily.append(expired)
    rate_limit.enforce_analysis_budget(request())
    assert len(rate_limit._requests["198.51.100.7"]) == 1
    assert len(rate_limit._daily) == 1


def _proxied(forwarded: str, peer: str = "10.0.0.1") -> Request:
    return Request(
        {
            "type": "http",
            "client": (peer, 1234),
            "headers": [(b"x-forwarded-for", forwarded.encode())],
        }
    )


def test_proxy_headers_are_ignored_unless_hops_configured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "trusted_proxy_hops", 0)
    assert rate_limit.client_key(_proxied("1.1.1.1")) == "10.0.0.1"


def test_client_key_reads_from_the_right_so_spoofed_prefix_is_ignored(monkeypatch) -> None:
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    assert rate_limit.client_key(_proxied("6.6.6.6, 203.0.113.9")) == "203.0.113.9"


def test_idle_client_keys_are_dropped(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_per_minute", 5)
    rate_limit._requests["198.51.100.1"].append(time.time() - 120)
    rate_limit.enforce_rate_limit(request("198.51.100.2"))
    assert "198.51.100.1" not in rate_limit._requests
