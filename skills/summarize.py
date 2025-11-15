# skills/summarize.py
from skill_engine.base import BaseSkill
import re

class SummarizeSkill(BaseSkill):
    name = "summarize"
    description = "Summarizes text into a short extractive summary."
    keywords = ["summarize", "summary", "tl;dr", "shorten"]

    def run(self, params: dict):
        text = params.get("text", "")
        if not text:
            return {"error": "Missing 'text' parameter"}

        # Very small extractive: pick up to 3 sentences
        sentences = re.split(r'(?<=[.!?]) +', text.strip())
        top = sentences[:3]
        summary = " ".join(top).strip()
        return {"summary": summary, "length": len(summary.split()), "confidence": 0.9}
