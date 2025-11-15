from skill_engine.base import BaseSkill

class PlannerSkill(BaseSkill):
    name = "planner"

    def run(self, params: dict):
        plan = params.get("plan", [])
        results = []

        for step in plan:
            results.append({"step": step, "status": "ok"})

        return {
            "executed_steps": len(results),
            "results": results
        }
