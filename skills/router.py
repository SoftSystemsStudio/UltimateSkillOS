# core/router.py
import importlib
import pkgutil
import skills
from skill_engine.base import BaseSkill
from typing import Dict

class Router:
    """
    Auto-discover skills in the `skills` package and perform simple keyword-based routing.
    """

    def __init__(self):
        self.skills: Dict[str, BaseSkill] = {}
        self._load_skills()

    def _load_skills(self):
        for module_info in pkgutil.iter_modules(skills.__path__):
            module_name = f"skills.{module_info.name}"
            try:
                module = importlib.import_module(module_name)
            except Exception as e:
                # keep going even if a skill import fails
                print(f"[Router] Failed importing {module_name}: {e}")
                continue

            for attr in dir(module):
                obj = getattr(module, attr)
                if isinstance(obj, type) and issubclass(obj, BaseSkill) and obj is not BaseSkill:
                    instance = obj()
                    if getattr(instance, "name", None):
                        self.skills[instance.name] = instance

        print(f"[Router] Loaded skills: {list(self.skills.keys())}")

    def route(self, text: str):
        text_lower = (text or "").lower()

        # 1) simple keyword match
        for skill in self.skills.values():
            for kw in getattr(skill, "keywords", []):
                if kw in text_lower:
                    return {"use_skill": skill.name, "params": {"text": text}}

        # 2) heuristic prefixes
        if text_lower.startswith("research"):
            return {"use_skill": "research", "params": {"query": text_lower.replace("research", "").strip()}}

        if text_lower.startswith("summarize"):
            return {"use_skill": "summarize", "params": {"text": text}}

        # fallback to summarize if available
        fallback = "summarize" if "summarize" in self.skills else next(iter(self.skills.keys()), None)
        return {"use_skill": fallback, "params": {"text": text}}
