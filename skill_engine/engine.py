# skill_engine/engine.py

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Any, Dict, Mapping

import skills
from skill_engine.base import BaseSkill

logger = logging.getLogger(__name__)


class SkillEngine:
    """
    Dynamic skill loader and dispatcher.

    - Discovers all modules under the `skills` package.
    - Registers all subclasses of BaseSkill with a non-empty `name`.
    """

    def __init__(self) -> None:
        self.skills: Dict[str, BaseSkill] = self.load_all_skills()

    def load_all_skills(self) -> Dict[str, BaseSkill]:
        loaded: Dict[str, BaseSkill] = {}

        for module_info in pkgutil.iter_modules(skills.__path__):
            module_name = f"skills.{module_info.name}"
            try:
                module = importlib.import_module(module_name)
            except Exception as e:
                logger.exception("[Engine] Failed to import %s: %s", module_name, e)
                continue

            for attr in dir(module):
                obj = getattr(module, attr)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BaseSkill)
                    and obj is not BaseSkill
                ):
                    try:
                        inst: BaseSkill = obj()
                        if inst.name:
                            loaded[inst.name] = inst
                    except Exception as e:
                        logger.exception(
                            "[Engine] Failed to instantiate skill %s.%s: %s",
                            module_name,
                            attr,
                            e,
                        )
                        continue

        logger.info("[Engine] Registered skills: %s", list(loaded.keys()))
        return loaded

    def run(self, skill_name: str, params: Mapping[str, Any]) -> Any:
        """
        Execute a skill by name with the given parameter mapping.
        """
        skill = self.skills.get(skill_name)
        if skill is None:
            return {"error": f"Skill '{skill_name}' not found"}

        # Ensure we pass a plain dict to the skill implementation.
        return skill.run(dict(params))
