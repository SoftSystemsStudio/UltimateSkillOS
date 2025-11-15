from skill_engine.base import SkillTool
import re

class SummarizeTool(SkillTool):
    name = "summarize"
    description = "Summarizes text using a lightweight extractive method."

    def run(self, params):
        text = params.get("text", "").strip()
        if not text:
            return {"error": "Missing 'text' parameter"}

        # Split into sentences safely
        sentences = re.split(r'(?<=[.!?]) +', text)
        if len(sentences) == 1:
            return {
                "summary": text,
                "length": 1,
                "confidence": 0.9
            }

        # Word frequency scoring
        words = re.findall(r'\w+', text.lower())
        freq = {w: words.count(w) for w in set(words)}

        # Score sentences
        scores = []
        for sent in sentences:
            sent_words = re.findall(r'\w+', sent.lower())
            score = sum(freq.get(w, 0) for w in sent_words)
            scores.append((score, sent))

        # Sort best sentences
        scores.sort(reverse=True)
        top = [s for _, s in scores[:3]]

        summary = " ".join(top)

        return {
            "summary": summary,
            "length": len(top),
            "confidence": 0.95
        }
tool = SummarizeTool()
