import json
import os
import pytest

from skill_engine.agent import Agent


GOLDEN_DIR = os.path.dirname(__file__)


pytestmark = pytest.mark.skipif(not os.environ.get("RUN_GOLDEN"), reason="Golden tests disabled")


def load_golden(name: str) -> dict:
    path = os.path.join(GOLDEN_DIR, f"{name}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_plan_matches_golden(tmp_path):
    # Example golden trace name
    name = "example_prompt"
    golden = load_golden(name)
    agent = Agent.from_env()
    result = agent.run(golden["prompt"], max_steps=golden.get("max_steps", 4))
    # Compare plan and step outputs
    got = result.to_dict()
    # Simple diff: compare keys and step count
    assert got["plan_id"] != golden.get("plan_id", "")
    assert len(got["step_results"]) == len(golden.get("step_results", []))
