from skill_engine.base import SkillTool
from skill_engine.engine import SkillEngine


class PlannerTool(SkillTool):
    name = "planner"
    description = "Executes multi-step plans created by the meta interpreter with auto-parameter extraction."

    def __init__(self):
        self.engine = SkillEngine()  # Load all skills dynamically

    def extract_parameters(self, skill_name, step_text):
        """
        Auto-build correct parameters for each skill based on the step.
        """

        if skill_name == "summarize":
            return {"text": step_text}

        if skill_name == "research":
            # Extract query by removing the word 'research'
            query = step_text.replace("research", "").strip()
            if not query:
                query = step_text
            return {"query": query}

        # Default fallback: pass step text as generic input
        return {"text": step_text}

    def run(self, params):
        plan = params.get("plan")
        if not plan:
            return {"error": "Missing 'plan' parameter"}

        results = []
        logs = []

        for step in plan:
            logs.append(f"Processing step: '{step}'")

            # Auto-match skill
            chosen_skill = None
            for skill_name in self.engine.skills.keys():
                if skill_name in step.lower():
                    chosen_skill = skill_name
                    break

            if not chosen_skill:
                logs.append(f"No matching skill found for step: '{step}'")
                results.append({"step": step, "result": None})
                continue

            logs.append(f"Using skill: {chosen_skill}")

            # Auto-parameter extraction
            params = self.extract_parameters(chosen_skill, step)
            logs.append(f"Built parameters: {params}")

            # Execute skill
            result = self.engine.run(chosen_skill, params)
            results.append({"step": step, "result": result})

        return {
            "executed_steps": len(results),
            "results": results,
            "logs": logs,
            "confidence": 0.82
        }


tool = PlannerTool()
