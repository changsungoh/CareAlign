import pytest

from app.services.provider_guard import CircuitOpenError, ProviderCircuitBreaker


def test_circuit_opens_after_consecutive_failures() -> None:
    circuit = ProviderCircuitBreaker(failure_threshold=2, recovery_seconds=30)
    circuit.before_call()
    circuit.record_failure()
    circuit.before_call()
    circuit.record_failure()
    assert circuit.snapshot().state == "open"
    with pytest.raises(CircuitOpenError):
        circuit.before_call()


def test_success_resets_failure_count() -> None:
    circuit = ProviderCircuitBreaker(failure_threshold=2, recovery_seconds=30)
    circuit.record_failure()
    circuit.record_success()
    snapshot = circuit.snapshot()
    assert snapshot.state == "closed"
    assert snapshot.consecutive_failures == 0


def test_circuit_recovers_after_cooldown(monkeypatch) -> None:
    now = 100.0
    monkeypatch.setattr("app.services.provider_guard.time.monotonic", lambda: now)
    circuit = ProviderCircuitBreaker(failure_threshold=1, recovery_seconds=5)
    circuit.record_failure()
    assert circuit.snapshot().state == "open"
    now = 106.0
    circuit.before_call()
    assert circuit.snapshot().state == "closed"
