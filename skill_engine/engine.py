# skill_engine/engine.py
import importlib
import pkgutil
import skills
from skill_engine.base import BaseSkill

class SkillEngine:
    def __init__(self):
        self.skills = self.load_all_skills()

    def load_all_skills(self):
        loaded = {}
        for module_info in pkgutil.iter_modules(skills.__path__):
            module_name = f"skills.{module_info.name}"
            try:
                module = importlib.import_module(module_name)
            except Exception as e:
                print(f"[Engine] Failed to import {module_name}: {e}")
                continue

            for attr in dir(module):
                obj = getattr(module, attr)
                if isinstance(obj, type) and issubclass(obj, BaseSkill) and obj is not BaseSkill:
                    inst = obj()
                    if inst.name:
                        loaded[inst.name] = inst
        print(f"[Engine] Registered skills: {list(loaded.keys())}")
        return loaded

    def run(self, skill_name: str, params: dict):
        key = skill_name
        if key not in self.skills:
            return {"error": f"Skill '{skill_name}' not found"}
        skill = self.skills[key]
        return skill.run(params)
