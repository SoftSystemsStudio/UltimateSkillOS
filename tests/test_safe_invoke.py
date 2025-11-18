import time

import pytest

from skill_engine.skill_base import safe_invoke, RunContext, SLA
from skill_engine.domain import SkillInput, SkillOutput
from skill_engine.resilience import CircuitOpen


class FastSkill:
    name = "fast"
    version = "0.0.1"
    description = "Quick success skill"
    input_schema = dict
    output_schema = dict

    def invoke(self, input_data: SkillInput, context: RunContext) -> SkillOutput:
        return SkillOutput(payload={"ok": True})


class SlowSkill:
    name = "slow"
    version = "0.0.1"
    description = "Slow skill that sleeps"
    input_schema = dict
    output_schema = dict

    def invoke(self, input_data: SkillInput, context: RunContext) -> SkillOutput:
        time.sleep(0.2)
        return SkillOutput(payload={"ok": True})


class FailingSkill:
    name = "fail"
    version = "0.0.1"
    description = "Always fails"
    input_schema = dict
    output_schema = dict

    def invoke(self, input_data: SkillInput, context: RunContext) -> SkillOutput:
        raise RuntimeError("skill failed")


def make_ctx(trace_id: str = "t"):  # helper
    return RunContext(trace_id=trace_id)


def test_safe_invoke_success():
    ctx = make_ctx("trace-success")
    inp = SkillInput(payload={}, trace_id=ctx.trace_id)
    res = safe_invoke(FastSkill(), inp, ctx)
    assert isinstance(res, SkillOutput)
    assert res.payload.get("ok") is True


def test_safe_invoke_timeout_raises():
    ctx = make_ctx("trace-timeout")
    inp = SkillInput(payload={}, trace_id=ctx.trace_id)

    slow = SlowSkill()
    slow.sla = SLA(timeout_seconds=0, retries=1, circuit_breaker=False)

    with pytest.raises(TimeoutError):
        safe_invoke(slow, inp, ctx)


def test_circuit_breaker_opens_and_recovers():
    ctx = make_ctx("trace-circuit")
    inp = SkillInput(payload={}, trace_id=ctx.trace_id)

    failing = FailingSkill()
    # configure low threshold and short timeout for test
    failing.sla = SLA(timeout_seconds=1, retries=1, circuit_breaker={"failure_threshold": 2, "recovery_timeout_seconds": 1, "half_open_trial_requests": 1})

    # two failing calls should open the circuit
    with pytest.raises(RuntimeError):
        safe_invoke(failing, inp, ctx)

    with pytest.raises(RuntimeError):
        safe_invoke(failing, inp, ctx)

    # now circuit should be open and subsequent calls raise CircuitOpen
    with pytest.raises(CircuitOpen):
        safe_invoke(failing, inp, ctx)

    # wait for recovery timeout to allow half-open trial
    time.sleep(1.1)

    # now a succeeding skill should reset the breaker
    fast = FastSkill()
    # use same skill key name to fetch same breaker
    fast.name = failing.name
    res = safe_invoke(fast, inp, ctx)
    assert isinstance(res, SkillOutput)

    # subsequent calls should continue to succeed
    res2 = safe_invoke(fast, inp, ctx)
    assert isinstance(res2, SkillOutput)
