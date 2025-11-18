# skills/summarize.py
from skill_engine.base import BaseSkill
import re

from pydantic import BaseModel
from skill_engine.domain import SkillInput, SkillOutput

class SummarizeInput(BaseModel):
    text: str = ""

class SummarizeOutput(BaseModel):
    summary: str
    length: int
    confidence: float
    error: str = ""

class SummarizeSkill(BaseSkill):
    name = "summarize"
    version = "1.0.0"
    description = "Summarizes text into a short extractive summary."
    keywords = ["summarize", "summary", "tl;dr", "shorten"]
    input_schema = SummarizeInput
    output_schema = SummarizeOutput
    sla = None

    def invoke(self, input_data: SkillInput, context) -> SkillOutput:
        text = input_data.payload.get("text", "")
        if not text:
            return {"error": "Missing 'text' parameter"}
        sentences = re.split(r'(?<=[.!?]) +', text.strip())
        top = sentences[:3]
        summary = " ".join(top).strip()
        return {"summary": summary, "length": len(summary.split()), "confidence": 0.9}
