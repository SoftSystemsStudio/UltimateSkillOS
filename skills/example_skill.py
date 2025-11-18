from skill_engine.base import BaseSkill

class ExampleSkill(BaseSkill):
    name = "ExampleSkill"

    def _run(self, params: dict) -> dict:
        # Always return a very brief answer for testing
        return {
            "final_answer": "AI thinks."
        }
