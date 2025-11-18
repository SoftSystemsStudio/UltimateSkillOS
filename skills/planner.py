
from skill_engine.base import BaseSkill
from core.interfaces import Planner
from pydantic import BaseModel
from skill_engine.domain import SkillInput, SkillOutput

class PlannerInput(BaseModel):
    goal: str
    plan: list[str] = []

class PlannerOutput(BaseModel):
    executed_steps: int
    results: list[dict]

class PlannerSkill(BaseSkill, Planner):
    name = "planner"
    version = "1.0.0"
    description = "Decomposes complex goals into executable step-by-step plans."
    input_schema = PlannerInput
    output_schema = PlannerOutput
    sla = None

    def plan(self, goal: str, context: dict) -> list:
        # Dummy planner: break goal into steps by splitting sentences
        return [s.strip() for s in goal.split('.') if s.strip()]

    def invoke(self, input_data: SkillInput, context) -> SkillOutput:
        goal = input_data.payload.get("goal", "")
        plan = input_data.payload.get("plan", [])
        if not plan:
            plan = self.plan(goal, context)
        results = []
        for step in plan:
            results.append({"step": step, "status": "ok"})
        output = {
            "executed_steps": len(results),
            "results": results
        }
        return output
