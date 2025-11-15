import importlib
import pkgutil
import skills


class SkillEngine:
    def __init__(self):
        self.skills = self.load_all_skills()

    def load_all_skills(self):
        """Dynamically load all skills inside /skills."""
        loaded = {}
        package = skills

        for _, module_name, _ in pkgutil.walk_packages(package.__path__):
            module = importlib.import_module(f"skills.{module_name}")

            # Look for a variable named `tool` inside the module
            if hasattr(module, "tool"):
                tool = getattr(module, "tool")
                loaded[tool.name.lower()] = tool

        return loaded

    def run(self, skill_name, params):
        """Run a skill by name."""
        key = skill_name.lower()

        if key not in self.skills:
            return {"error": f"Skill '{skill_name}' not found"}

        skill = self.skills[key]
        return skill.run(params)
