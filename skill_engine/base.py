"""
BaseSkill (Professional Version)
Provides:
- BaseSkill abstract class
- lightweight schema validation
- safe_run wrapper with logging
- standardized run() method
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger("BaseSkill")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(ch)


class BaseSkill:
    name: str = "base"
    description: str = "Base skill"
    keywords: List[str] = []
    input_schema: Optional[Dict[str, Any]] = None

    def __init__(self) -> None:
        self.log = logging.getLogger(f"Skill.{self.name}")
        self.log.setLevel(logging.INFO)

    def validate(self, params: Dict[str, Any]) -> None:
        if not self.input_schema:
            return
        required = self.input_schema.get("required", [])
        for r in required:
            if r not in params:
                raise ValueError(f"Missing required parameter: {r}")

    def safe_run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            self.log.info("Running skill '%s' with params: %s", self.name, params)
            self.validate(params)
            out = self._run(params)
            if not isinstance(out, dict):
                out = {"result": out}
            return out
        except Exception as e:
            self.log.exception("Skill '%s' failed: %s", self.name, e)
            return {"error": str(e)}

    def _run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement _run()")

    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.safe_run(params)
