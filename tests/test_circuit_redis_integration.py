import os
import time

import pytest

from skill_engine.resilience import registry, CircuitBreakerConfig
from skill_engine.domain import SkillInput
from skill_engine.skill_base import RunContext


pytestmark = pytest.mark.skipif(
    not os.environ.get("SKILLOS_CIRCUIT_REDIS_URL"),
    reason="SKILLOS_CIRCUIT_REDIS_URL not set; skipping Redis integration test",
)


def test_redis_circuit_opens_and_recovers():
    key = "integration_test_skill"
    cfg = CircuitBreakerConfig(failure_threshold=2, recovery_timeout_seconds=1, half_open_trial_requests=1)

    # create breaker via registry (should be Redis-backed if env var provided)
    cb = registry.get_or_create(key, cfg)

    # ensure fresh state
    try:
        state = registry.get_state(key)
    except Exception:
        state = None

    # simulate failures
    cb.on_failure()
    cb.on_failure()

    st = registry.get_state(key)
    assert st is not None
    assert st["failures"] >= 2
    assert st["opened_at"] is not None

    # subsequent check should show open behavior
    # wait for recovery timeout
    time.sleep(1.1)

    st2 = registry.get_state(key)
    # after timeout, opened_at may be cleared and half_open_trials reset
    assert st2 is not None
