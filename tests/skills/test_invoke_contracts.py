import pytest

from skill_engine.engine import SkillEngine
from skill_engine.skill_base import SkillValidator


def test_registered_skills_implement_protocol():
    engine = SkillEngine()
    for name, skill in engine.skills.items():
        # Each skill should pass validation
        SkillValidator.validate_skill(skill)
