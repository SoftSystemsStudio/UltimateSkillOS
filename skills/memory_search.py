# skills/memory_search.py

from __future__ import annotations

from typing import Any, Dict, List

from skill_engine.base import BaseSkill
from skill_engine.memory.manager import get_memory_manager


class MemorySearchSkill(BaseSkill):
    """
    Skill that queries the shared MemoryManager for relevant entries.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "memory_search"
        self.description = "Searches the agent's memory for items relevant to the query."

    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        mm = get_memory_manager()

        # Normalize query
        query_raw: Any = params.get("query") or params.get("text") or ""
        query = str(query_raw).strip()

        if not query:
            return {
                "error": "No query provided for memory_search.",
                "query": query,
                "matches": [],
                "confidence": 0.0,
            }

        k = int(params.get("k", 5))

        results: List[Dict[str, Any]] = mm.search(query, k=k)

        # Shape results for the Agent:
        #   matches: [{"text": ..., "score": ...}, ...]
        return {
            "query": query,
            "matches": results,
            "confidence": 0.7 if results else 0.3,
        }
