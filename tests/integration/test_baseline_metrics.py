import sys
import os

# Ensure the workspace root is in the Python path
workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.insert(0, workspace_root)

import pytest
from core.self_eval_harness import run_meta_learning_simulation, aggregate
from skill_engine.engine import SkillEngine
from skill_engine.domain import AgentPlan, PlanStep

@pytest.fixture
def skill_engine():
    return SkillEngine()

def test_baseline_metrics():
    """
    Test baseline performance metrics for the agent.
    """
    # Run the simulation
    runs = run_meta_learning_simulation()
    metrics = aggregate(runs)

    # Assertions for baseline metrics
    assert metrics["time_to_threshold"] < 50, "Time to threshold is too high."
    assert metrics["sample_efficiency"] > 10, "Sample efficiency is too low."

    print("Baseline metrics:", metrics)

def test_reflection_improves_quality(skill_engine):
    """
    Test that reflection and self-correction improve the quality of answers.
    """
    # Define a sample plan with a skill that produces a suboptimal answer
    plan = AgentPlan(
        plan_id="test_plan_1",
        goal="Test the reflection and autofix capabilities",
        steps=[
            PlanStep(step_id="1", skill_name="ExampleSkill", input_data={"query": "What is AI?"})
        ]
    )

    # Execute the plan
    result = skill_engine.execute_plan(plan)

    # Ensure the reflection feedback and autofix were applied
    assert "reflection_feedback" in result.final_answer
    assert "autofix_output" in result.final_answer

    # Validate that the final answer is improved
    reflection_feedback = result.final_answer["reflection_feedback"]
    autofix_output = result.final_answer["autofix_output"]

    assert reflection_feedback["notes"] != ""
    assert autofix_output["fixed_context"] != result.final_answer["final_answer"]