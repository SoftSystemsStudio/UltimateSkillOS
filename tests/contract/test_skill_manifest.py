from skill_engine import engine
from skill_engine.skill_base import SkillValidator


def test_skill_manifest_consistency():
    eng = engine.SkillEngine()
    for name, skill in eng.skills.items():
        # Validate structural compliance
        SkillValidator.validate_skill(skill)
        # Ensure declared name matches registry key
        assert getattr(skill, "name", name) == name
