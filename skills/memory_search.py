# skills/memory_search.py

from __future__ import annotations

from typing import Any, Dict, List

from skill_engine.base import BaseSkill
from skill_engine.memory.manager import get_memory_manager


from pydantic import BaseModel
from skill_engine.domain import SkillInput, SkillOutput
from config import load_config

try:
    DEFAULT_TOP_K = int(load_config().memory.top_k)
except Exception:  # pragma: no cover - defensive fallback
    DEFAULT_TOP_K = 5

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
        facade = getattr(context, "memory_facade", None) or get_memory_manager()
        query = input_data.payload.get("query", "")
        k = int(input_data.payload.get("k", DEFAULT_TOP_K) or DEFAULT_TOP_K)
        if not query:
            return {
                "error": "No query provided for memory_search.",
                "query": query,
                "matches": [],
                "confidence": 0.0,
            }
        results = facade.search(query, top_k=k, tier="long_term")
        serialized = [r.to_dict() if hasattr(r, "to_dict") else r for r in results]
        return {
            "query": query,
            "matches": serialized,
            "confidence": 0.7 if results else 0.3,
        }
