# core/router.py

class Router:
    """
    Decides which skill to use based on the text.
    """

    def __init__(self):
        self.rules = [
            ("research", ["research", "find", "look up", "search"]),
            ("summarize", ["summarize", "shorten", "explain simply"]),
            ("reflection", ["improve", "fix", "rewrite", "review"]),
            ("autofix", ["typo", "correct", "fix spelling"]),
        ]

    def route(self, text: str):
        t = text.lower()

        for skill, keywords in self.rules:
            if any(k in t for k in keywords):
                params = {}

                if skill == "research":
                    params = {"query": text.replace("research", "").strip()}

                elif skill == "summarize":
                    params = {"text": text}

                elif skill == "reflection":
                    params = {"text": text}

                elif skill == "autofix":
                    params = {"text": text}

                return {
                    "use_skill": skill,
                    "params": params,
                    "confidence": 0.9,
                }

        return {
            "use_skill": "summarize",
            "params": {"text": text},
            "confidence": 0.5,
        }
