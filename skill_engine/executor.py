from skill_engine.engine import SkillEngine
from memory.short_term import ShortTermMemory

class TaskExecutor:
    """
    High-level agent executor with short-term memory.
    """

    def __init__(self):
        self.engine = SkillEngine()
        self.memory = ShortTermMemory(max_items=20)

    def run(self, text):
        # Log input into memory
        self.memory.add({"input": text})

        # 1. Router chooses skill
        router = self.engine.skills.get("router")
        if router is None:
            return {"error": "router skill not found"}

        routing = router.run({"text": text})
        self.memory.add({"router": routing})

        if "use_skill" not in routing:
            return {"error": "router failed", "details": routing}

        skill_name = routing["use_skill"]
        params = routing["params"]

        # 2. Load the resolved skill
        skill = self.engine.skills.get(skill_name)
        if skill is None:
            return {"error": f"Skill '{skill_name}' not found"}

        # 3. Execute underlying skill
        result = skill.run(params)

        # Store result in memory
        self.memory.add({"result": result})

        return {
            "input": text,
            "selected_skill": skill_name,
            "used_params": params,
            "result": result,
            "memory": self.memory.get(),
            "confidence": result.get("confidence", 0.8),
        }
