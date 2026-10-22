import pytest

from app.services import rate_limit
from app.services.provider_guard import provider_auth, provider_circuit


@pytest.fixture(autouse=True)
def reset_operational_state() -> None:
    """Keep request-budget and provider-circuit state isolated across tests."""
    rate_limit._requests.clear()
    rate_limit._daily.clear()
    rate_limit._client_daily.clear()
    provider_circuit.reset()
    provider_auth.reset()
    yield
    rate_limit._requests.clear()
    rate_limit._daily.clear()
    rate_limit._client_daily.clear()
    provider_circuit.reset()
    provider_auth.reset()
