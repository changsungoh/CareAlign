import time
from dataclasses import dataclass
from threading import Lock

from app.core.config import settings


class CircuitOpenError(RuntimeError):
    pass


@dataclass(frozen=True)
class CircuitSnapshot:
    state: str
    consecutive_failures: int
    retry_after_seconds: float


class ProviderCircuitBreaker:
    def __init__(self, failure_threshold: int, recovery_seconds: float) -> None:
        if failure_threshold < 1 or recovery_seconds <= 0:
            raise ValueError("Circuit-breaker thresholds must be positive.")
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self._consecutive_failures = 0
        self._open_until = 0.0
        self._lock = Lock()

    def before_call(self) -> None:
        now = time.monotonic()
        with self._lock:
            if self._open_until and now < self._open_until:
                raise CircuitOpenError("Provider circuit is temporarily open.")
            if self._open_until:
                self._open_until = 0.0
                self._consecutive_failures = 0

    def record_success(self) -> None:
        with self._lock:
            self._consecutive_failures = 0
            self._open_until = 0.0

    def record_failure(self) -> None:
        with self._lock:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self.failure_threshold:
                self._open_until = time.monotonic() + self.recovery_seconds

    def snapshot(self) -> CircuitSnapshot:
        now = time.monotonic()
        with self._lock:
            retry_after = max(0.0, self._open_until - now)
            return CircuitSnapshot(
                state="open" if retry_after else "closed",
                consecutive_failures=self._consecutive_failures,
                retry_after_seconds=round(retry_after, 2),
            )

    def reset(self) -> None:
        self.record_success()


provider_circuit = ProviderCircuitBreaker(
    settings.provider_failure_threshold,
    settings.provider_recovery_seconds,
)
