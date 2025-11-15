from skill_engine.base import SkillTool
import re

class AutoFixTool(SkillTool):
    name = "autofix"
    description = "Attempts to repair errors, improve clarity, or fix broken code/text."

    def run(self, params):
        text = params.get("text", "").strip()
        if not text:
            return {"error": "Missing 'text' parameter"}

        fixes = []

        # Fix common issues
        fixed = text

        # Remove double spaces
        if "  " in fixed:
            fixed = re.sub(r" {2,}", " ", fixed)
            fixes.append("Removed excessive spacing.")

        # Fix missing final punctuation
        if not fixed.endswith((".", "!", "?")):
            fixed += "."
            fixes.append("Added ending punctuation.")

        # Fix common misspellings
        corrections = {
            "teh": "the",
            "recieve": "receive",
            "beleive": "believe",
            "enviroment": "environment"
        }

        for wrong, right in corrections.items():
            if wrong in fixed.lower():
                fixed = re.sub(wrong, right, fixed, flags=re.IGNORECASE)
                fixes.append(f"Corrected spelling: {wrong} → {right}")

        return {
            "original": text,
            "fixed": fixed,
            "fixes_applied": fixes or ["No fixes needed."],
            "confidence": 0.9 if fixes else 0.99
        }

tool = AutoFixTool()
