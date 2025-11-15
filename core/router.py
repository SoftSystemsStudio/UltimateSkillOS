# router.py
class Router:
    def __init__(self, loader):
        self.loader = loader

    def route(self, skill_name, query):
        skill = self.loader.get_skill(skill_name)
        if not skill:
            return f"Skill '{skill_name}' not found."
        return skill.run(query)
