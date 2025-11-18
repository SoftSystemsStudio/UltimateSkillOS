import pytest
from skill_engine.engine import SkillEngine
from skill_engine.domain import AgentPlan, PlanStep

@pytest.fixture
def skill_engine():
    return SkillEngine()

def test_multi_step_execution(skill_engine):
    """
    Test a multi-step task requiring FileTool, memory search, and summarization.
    """
    # Define the plan
    plan = AgentPlan(
        plan_id="test_plan_001",
        goal="Process a file, search memory, and summarize results",
        steps=[
            PlanStep(
                step_id="step_1",
                skill_name="file_tool",
                input_data={"file_path": "test_file.txt"},
                description="Process the file to extract content."
            ),
            PlanStep(
                step_id="step_2",
                skill_name="memory_search",
                input_data={"query": "Extracted content"},
                description="Search memory for related information."
            ),
            PlanStep(
                step_id="step_3",
                skill_name="summarize",
                input_data={"content": "Memory search results"},
                description="Summarize the findings."
            )
        ]
    )

    # Execute the plan
    result = skill_engine.execute_plan(plan)

    # Assertions
    assert result.status == "success"
    assert len(result.step_results) == 3
    assert all(step.success for step in result.step_results)
    assert result.final_answer is not None