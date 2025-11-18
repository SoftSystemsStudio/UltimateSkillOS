"""
MemoryFacade – unified interface for all memory tiers.

Provides a single access point for skills to interact with memory.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from skill_engine.memory.base import MemoryRecord
from skill_engine.memory.tiers import LongTermMemory, Scratchpad, ShortTermMemory

logger = logging.getLogger(__name__)


class MemoryFacade:
    """
    Unified interface for accessing all memory tiers.

    Provides:
    - Tier selection (short-term, long-term, scratchpad)
    - Unified search across tiers
    - Context-aware memory management
    """

    def __init__(
        self,
        short_term: ShortTermMemory,
        long_term: LongTermMemory,
        scratchpad: Scratchpad,
    ):
        """
        Initialize the memory facade.

        Args:
            short_term: ShortTermMemory instance.
            long_term: LongTermMemory instance.
            scratchpad: Scratchpad instance.
        """
        self.short_term = short_term
        self.long_term = long_term
        self.scratchpad = scratchpad

    def add(
        self,
        content: str,
        tier: Literal["short_term", "long_term", "scratchpad"] = "short_term",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Add a memory entry to a specific tier.

        Args:
            content: Memory content.
            tier: Memory tier to use.
            metadata: Optional metadata.

        Returns:
            Record ID.

        Raises:
            ValueError: If tier is invalid.
        """
        if tier == "short_term":
            return self.short_term.add(content, metadata)
        elif tier == "long_term":
            return self.long_term.add(content, metadata)
        elif tier == "scratchpad":
            return self.scratchpad.add_memory(content, metadata.get("tag", "") if metadata else "")
        else:
            raise ValueError(f"Unknown memory tier: {tier}")

    def search(
        self,
        query: str,
        tier: Literal["short_term", "long_term", "scratchpad", "all"] = "long_term",
        top_k: int = 5,
    ) -> list[MemoryRecord]:
        """
        Search for records in memory.

        Args:
            query: Search query.
            tier: Memory tier(s) to search.
            top_k: Number of results to return.

        Returns:
            List of matching MemoryRecord objects.

        Raises:
            ValueError: If tier is invalid.
        """
        if tier == "short_term":
            return self.short_term.search(query, top_k)
        elif tier == "long_term":
            return self.long_term.search(query, top_k)
        elif tier == "scratchpad":
            return self.scratchpad.search_memory(query, top_k)
        elif tier == "all":
            # Search all tiers and merge results
            all_results = []
            all_results.extend(self.short_term.search(query, top_k))
            all_results.extend(self.long_term.search(query, top_k))
            all_results.extend(self.scratchpad.search_memory(query, top_k))

            # Sort by timestamp (most recent first) and deduplicate
            seen = set()
            unique_results = []
            for record in sorted(all_results, key=lambda r: r.timestamp, reverse=True):
                if record.id not in seen:
                    seen.add(record.id)
                    unique_results.append(record)

            return unique_results[:top_k]
        else:
            raise ValueError(f"Unknown memory tier: {tier}")

    def recall_context(self, query: str, top_k: int = 3) -> str:
        """
        Get formatted context string from memory for injection into skills.

        Args:
            query: Query for memory context.
            top_k: Number of results to include.

        Returns:
            Formatted string suitable for prompt injection.
        """
        results = self.search(query, tier="long_term", top_k=top_k)

        if not results:
            return "No relevant memory found."

        lines = ["Recent relevant memories:"]
        for i, record in enumerate(results, 1):
            lines.append(f"{i}. {record.content}")
            if record.metadata:
                lines.append(f"   (Tags: {', '.join(str(v) for v in record.metadata.values())})")

        return "\n".join(lines)

    def clear_tier(
        self, tier: Literal["short_term", "long_term", "scratchpad"] = "short_term"
    ) -> None:
        """
        Clear a specific memory tier.

        Args:
            tier: Tier to clear.

        Raises:
            ValueError: If tier is invalid.
        """
        if tier == "short_term":
            self.short_term.clear()
        elif tier == "long_term":
            self.long_term.clear()
        elif tier == "scratchpad":
            self.scratchpad.clear()
        else:
            raise ValueError(f"Unknown memory tier: {tier}")

        logger.info(f"Cleared {tier} memory")

    def stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        return {
            "short_term": self.short_term.count(),
            "long_term": self.long_term.count(),
            "scratchpad": self.scratchpad.count(),
        }

    def to_dict(self) -> dict[str, Any]:
        """Export memory facade state."""
        return {
            "short_term_count": self.short_term.count(),
            "long_term_count": self.long_term.count(),
            "scratchpad": self.scratchpad.to_dict(),
        }

    def retrieve_context(self, goal: str, top_k: int = 3) -> dict[str, Any]:
        """
        Retrieve relevant memory context for a specific goal.

        Args:
            goal: The goal or query to retrieve context for.
            top_k: Number of top relevant memory entries to retrieve.

        Returns:
            A dictionary of relevant memory entries.
        """
        relevant_memories = self.search(goal, tier="all", top_k=top_k)
        context = {}
        for i, memory in enumerate(relevant_memories):
            context[f"memory_{i+1}"] = memory.content
        return context
