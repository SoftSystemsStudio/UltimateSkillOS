"""
Skill Engine - Core agent orchestration and skill execution.

Main components:
  - Agent: Autonomous task executor with memory and routing
  - SkillEngine: Dynamic skill loader and runner
  - BaseSkill: Abstract base for all skill implementations
"""

from skill_engine.agent import Agent
from skill_engine.base import BaseSkill
from skill_engine.engine import SkillEngine

__all__ = ["Agent", "BaseSkill", "SkillEngine"]
