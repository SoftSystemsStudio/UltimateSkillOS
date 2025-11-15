from skill_engine.base import SkillTool
import re

class ReflectionTool(SkillTool):
    name = "reflection"
    description = "Evaluates text for clarity, correctness, structure, and completeness."

    def run(self, params):
        text = params.get("text", "").strip()
        if not text:
            return {"error": "Missing 'text' parameter"}

        issues = []

        # Heuristic checks
        if len(text) < 40:
            issues.append("Text is very short.")
        if "error" in text.lower():
            issues.append("Contains the word 'error'.")
        if re.search(r"\bTODO\b", text):
            issues.append("Contains TODO markers.")
        if "  " in text:
            issues.append("Double spacing detected.")
        if text.endswith("?"):
            issues.append("Ends with uncertainty.")

        # Build improved rewrite
        if issues:
            rewrite = (
                "IMPROVED VERSION:\n"
                f"{text}\n\n"
                "SUGGESTED FIXES:\n- " + "\n- ".join(issues)
            )
        else:
            rewrite = text

        return {
            "text_evaluated": text,
            "issues_found": issues or ["No issues found."],
            "rewrite": rewrite,
            "confidence": 0.95 if not issues else 0.80
        }

tool = ReflectionTool()
