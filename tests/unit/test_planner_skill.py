from skills.planner import PlannerSkill


def _skill_sequence(plan):
    return [step["skill"] for step in plan]


def test_research_goal_includes_memory_and_research_steps():
    planner = PlannerSkill()
    plan = planner.plan("Research the latest AI safety findings and summarize them", {})
    skills = _skill_sequence(plan)

    assert "memory_search" in skills
    assert "research" in skills
    assert "summarize" in skills
    assert skills[-1] == "reflection"


def test_strategy_goal_triggers_meta_planning():
    planner = PlannerSkill()
    plan = planner.plan("Create a rollout strategy plan for the onboarding program", {})
    skills = _skill_sequence(plan)

    assert "meta_interpreter" in skills
    assert "question_answering" in skills


def test_fallback_plan_still_answers_question():
    planner = PlannerSkill()
    plan = planner.plan("Explain the impact of data drift", {})
    skills = _skill_sequence(plan)

    assert "question_answering" in skills
    assert skills[-1] == "reflection"
    assert len(plan) >= 3
