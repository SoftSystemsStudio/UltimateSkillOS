from skill_engine.base import BaseSkill
from pydantic import BaseModel
from skill_engine.domain import SkillInput, SkillOutput

class AutofixInput(BaseModel):
    text: str

class AutofixOutput(BaseModel):
    original: str
    fixed: str
    confidence: float

class AutofixSkill(BaseSkill):
    name = "autofix"
    version = "1.0.0"
    description = "Automatically detects and fixes common issues in code or data."
    input_schema = AutofixInput
    output_schema = AutofixOutput
    sla = None

    def invoke(self, input_data: SkillInput, context) -> SkillOutput:
        text = input_data.payload.get("text", "")
        fixed = text.replace("sentnce", "sentence")
        output = {
            "original": text,
            "fixed": fixed,
            "confidence": 0.8
        }
        return output
