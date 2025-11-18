from skill_engine.domain import AgentPlan, PlanStep


def test_plan_add_and_get():
    plan = AgentPlan(plan_id="p1", goal="Test goal")
    step = PlanStep(step_id="s1", skill_name="fast", input_data={})
    plan.add_step(step)
    assert plan.get_step("s1") is step
