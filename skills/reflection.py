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
    notes: str

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

        # Check for logical errors
        if "error" in text.lower():
            issues.append("Logical error detected in the answer.")
            reflection_score -= 30

        # Check for missing information
        if "missing" in text.lower():
            issues.append("The answer is missing critical information.")
            reflection_score -= 25

        # Check for suboptimal phrasing
        if len(text.split()) < 5:
            issues.append("The answer is too brief and lacks detail.")
            reflection_score -= 20

        suggested_action = "None"
        if reflection_score < 50:
            suggested_action = "Revise the answer to address missing details and improve clarity."

        return {
            "text_evaluated": text,
            "issues_found": issues,
            "confidence": 0.8,
            "reflection_score": reflection_score,
            "suggested_action": suggested_action,
            "notes": "Reflection completed. Issues: " + ", ".join(issues) if issues else "No issues found."
        }

    def invoke(self, input_data: SkillInput, context) -> SkillOutput:
        text = input_data.payload.get("text", "")
        return self.evaluate({"text": text}, context)

class ReflectionSkill(BaseSkill):
    name = "ReflectionSkill"

    def _run(self, params: dict) -> dict:
        text = params.get("answer", "")
        issues = []
        reflection_score = 100
        adjustments = []
        # Check for logical errors
        if "error" in text.lower():
            issues.append("Logical error detected in the answer.")
            reflection_score -= 30
        # Check for missing information
        if "missing" in text.lower():
            issues.append("The answer is missing critical information.")
            reflection_score -= 25
        # Check for suboptimal phrasing
        if len(text.split()) < 5:
            issues.append("The answer is too brief and lacks detail.")
            reflection_score -= 20
            adjustments.append({
                "skill_name": "AutofixSkill",
                "params": {
                    "target": text,
                    "replacement": text + " (expanded)"
                }
            })
        suggested_action = "None"
        if reflection_score < 50:
            suggested_action = "Revise the answer to address missing details and improve clarity."
        return {
            "text_evaluated": text,
            "issues_found": issues,
            "confidence": 0.8,
            "reflection_score": reflection_score,
            "suggested_action": suggested_action,
            "adjustments": adjustments,
            "notes": "Reflection completed. Issues: " + ", ".join(issues) if issues else "No issues found."
        }
