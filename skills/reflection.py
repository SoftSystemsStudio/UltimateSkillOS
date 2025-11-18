from skill_engine.base import BaseSkill
from core.interfaces import Evaluator
from pydantic import BaseModel
from skill_engine.domain import SkillInput, SkillOutput

class ReflectionInput(BaseModel):
    text: str

class ReflectionOutput(BaseModel):
    text_evaluated: str
    issues_found: list[str]
    confidence: float
    reflection_score: float
    suggested_action: str

class ReflectionSkill(BaseSkill, Evaluator):
    name = "reflection"
    version = "1.0.0"
    description = "Analyzes outcomes and generates insights for improvement."
    input_schema = ReflectionInput
    output_schema = ReflectionOutput
    sla = None

    def evaluate(self, result, context):
        issues = []
        text = result.get("text", "")
        reflection_score = 100  # Start with a perfect score

        if len(text) < 10:
            issues.append("Text is very short.")
            reflection_score -= 30
        if text.endswith("?"):
            issues.append("Ends with uncertainty.")
            reflection_score -= 20

        suggested_action = "None"
        if reflection_score < 50:
            suggested_action = "Consider rephrasing or adding more detail."

        return {
            "text_evaluated": text,
            "issues_found": issues,
            "confidence": 0.8,
            "reflection_score": reflection_score,
            "suggested_action": suggested_action
        }

    def invoke(self, input_data: SkillInput, context) -> SkillOutput:
        text = input_data.payload.get("text", "")
        return self.evaluate({"text": text}, context)
