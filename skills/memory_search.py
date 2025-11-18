# skills/memory_search.py

from __future__ import annotations

from typing import Any, Dict, List

from skill_engine.base import BaseSkill
from skill_engine.memory.manager import get_memory_manager


from pydantic import BaseModel
from skill_engine.domain import SkillInput, SkillOutput

class MemorySearchInput(BaseModel):
    query: str = ""
    k: int = 5

class MemorySearchOutput(BaseModel):
    query: str
    matches: list
    confidence: float
    error: str = ""

class MemorySearchSkill(BaseSkill):
    name = "memory_search"
    version = "1.0.0"
    description = "Searches the agent's memory for items relevant to the query."
    input_schema = MemorySearchInput
    output_schema = MemorySearchOutput
    sla = None

    def invoke(self, input_data: SkillInput, context) -> SkillOutput:
        mm = get_memory_manager()
        query = input_data.payload.get("query", "")
        k = int(input_data.payload.get("k", 5))
        if not query:
            return {
                "error": "No query provided for memory_search.",
                "query": query,
                "matches": [],
                "confidence": 0.0,
            }
        results: list = mm.search(query, k=k)
        return {
            "query": query,
            "matches": results,
            "confidence": 0.7 if results else 0.3,
        }
