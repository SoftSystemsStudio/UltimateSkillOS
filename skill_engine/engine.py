# engine.py
class SkillEngine:
    def __init__(self, loader, router):
        self.loader = loader
        self.router = router

    def run(self, skill_name, query):
        return self.router.route(skill_name, query)
