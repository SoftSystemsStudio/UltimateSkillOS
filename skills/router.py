from skill_engine.base import SkillTool

class RouterTool(SkillTool):
    name = "router"
    description = "Automatically selects the correct skill based on the input text."

    def run(self, params):
        text = params.get("text", "").lower().strip()
        if not text:
            return {"error": "Missing 'text' parameter"}

        # Routing rules
        if any(k in text for k in ["summarize", "summary", "condense"]):
            return {"use_skill": "summarize", "params": {"text": text}}

        if any(k in text for k in ["research", "look up", "find info", "search for"]):
            # remove tool trigger words for cleaner queries
            cleaned = (
                text.replace("research", "")
                    .replace("look up", "")
                    .replace("find info", "")
                    .replace("search for", "")
                    .strip()
            )
            return {"use_skill": "research", "params": {"query": cleaned}}

        if any(k in text for k in ["fix", "correct", "repair", "cleanup"]):
            return {"use_skill": "autofix", "params": {"text": text}}

        if any(k in text for k in ["reflect", "why", "how can", "improve"]):
            return {"use_skill": "reflection", "params": {"text": text}}

        # Default fallback
        return {
            "use_skill": "summarize",
            "params": {"text": text},
            "note": "No rule matched; defaulted to summarize"
        }

tool = RouterTool()
