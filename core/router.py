from skills.research import ResearchSkill

class SkillRouter:
    def __init__(self):
        self.skills = {
            "research": ResearchSkill(),
        }

    def get(self, name: str):
        return self.skills.get(name)
