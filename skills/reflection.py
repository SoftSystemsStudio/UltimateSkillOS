
from skill_engine.base import BaseSkill
from core.interfaces import Evaluator

class ReflectionSkill(BaseSkill, Evaluator):
    name = "reflection"

    def run(self, params: dict):
        text = params.get("text", "")

        issues = []
        if len(text) < 10:
            issues.append("Text is very short.")
        if text.endswith("?"):
            issues.append("Ends with uncertainty.")

        return {
            "text_evaluated": text,
            "issues_found": issues,
            "confidence": 0.8
        }
