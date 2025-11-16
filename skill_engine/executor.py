"""
Task executor - coordinates routing, skills, and memory for agent tasks.
"""
from core.router import Router
from skill_engine.engine import SkillEngine
from skill_engine.memory.memory_manager import MemoryManager

class TaskExecutor:
    """
    Main agent – uses router, skills, and persistent memory.
    """

    def __init__(self):
        self.engine = SkillEngine()
        self.router = Router()
        self.memory = MemoryManager()

    def run(self, text: str):
        # Store input
        self.memory.add(text)

        # Retrieve memory
        related = self.memory.search(text)
        memory_context = [m["text"] for m in related]

        # Route
        route = self.router.route(text)
        skill = route["use_skill"]
        params = route["params"]

        # Inject memory into params
        params["memory_context"] = memory_context

        # Execute skill
        result = self.engine.run(skill, params)

        # Store result
        if isinstance(result, dict):
            self.memory.add(str(result))

        return {
            "input": text,
            "selected_skill": skill,
            "context_used": memory_context,
            "result": result
        }
