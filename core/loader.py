# loader.py
class SkillLoader:
    def __init__(self):
        self.skills = {}

    def load_skill(self, name, cls):
        self.skills[name] = cls()

    def get_skill(self, name):
        return self.skills.get(name)
