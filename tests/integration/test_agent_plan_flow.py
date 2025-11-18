import os
import pytest

from skill_engine.agent import Agent


pytestmark = pytest.mark.skipif(not os.environ.get("RUN_INTEGRATION"), reason="Integration tests disabled by default")


def test_agent_multi_step_plan():
    agent = Agent.from_env()
    result = agent.run("Summarize recent advances in AI safety", max_steps=4)
    assert hasattr(result, "step_results")
    assert isinstance(result.step_results, list)
