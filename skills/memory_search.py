from skill_engine.base import BaseSkill

class MemorySearchSkill(BaseSkill):
    name = "memory_search"

    def run(self, params: dict):
        query = params.get("query", "")
        memory = params.get("memory", [])

        matches = [m for m in memory if query.lower() in m.lower()]

        return {
            "query": query,
            "matches": matches,
            "confidence": 0.7
        }
