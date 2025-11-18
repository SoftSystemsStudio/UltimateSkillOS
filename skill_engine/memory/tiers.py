"""
Memory tiers: short-term, long-term, and scratchpad.

Each tier provides a specific memory management strategy.
"""

from __future__ import annotations

import logging
from typing import Any

from skill_engine.memory.base import MemoryBackend, MemoryRecord
from skill_engine.memory.in_memory import InMemoryBackend

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """
    Ephemeral, session-scoped memory.

    Used for:
    - Current execution context
    - Per-run state and observations
    - Temporary working memory

    Backed by in-memory storage.
    """

    def __init__(self):
        """Initialize short-term memory."""
        self.backend: MemoryBackend = InMemoryBackend()

    def add(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        """
        Add a memory entry.

        Args:
            content: Memory content.
            metadata: Optional metadata.

        Returns:
            Record ID.
        """
        import uuid

        record = MemoryRecord(
            id=str(uuid.uuid4()),
            content=content,
            metadata=metadata or {},
        )
        self.backend.add([record])
        return record.id

    def search(self, query: str, top_k: int = 5) -> list[MemoryRecord]:
        """Search short-term memory."""
        return self.backend.search(query, top_k)

    def clear(self) -> None:
        """Clear all short-term memory."""
        self.backend.clear()

    def count(self) -> int:
        """Get number of entries."""
        return self.backend.count()


class LongTermMemory:
    """
    Persistent, cross-session memory.

    Used for:
    - Long-term facts and learnings
    - Persistent knowledge base
    - Query history and patterns

    Backed by FAISS + SQLite for scalability.
    """

    def __init__(self, backend: MemoryBackend):
        """
        Initialize long-term memory.

        Args:
            backend: Storage backend (e.g., FAISSBackend).
        """
        self.backend = backend

    def add(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        """
        Add a memory entry.

        Args:
            content: Memory content.
            metadata: Optional metadata.

        Returns:
            Record ID.
        """
        import uuid

        record = MemoryRecord(
            id=str(uuid.uuid4()),
            content=content,
            metadata=metadata or {},
        )
        self.backend.add([record])
        return record.id

    def search(self, query: str, top_k: int = 5) -> list[MemoryRecord]:
        """Search long-term memory."""
        return self.backend.search(query, top_k)

    def delete(self, ids: list[str]) -> None:
        """Delete specific entries."""
        self.backend.delete(ids)

    def clear(self) -> None:
        """Clear all long-term memory."""
        self.backend.clear()

    def count(self) -> int:
        """Get number of entries."""
        return self.backend.count()


class Scratchpad:
    """
    Temporary structured notes for Planner and Reflection.

    Used for:
    - Plan steps and reasoning
    - Intermediate computation results
    - Temporary analysis notes
    - Per-step working memory

    Backed by in-memory storage, cleared at step boundaries.
    """

    def __init__(self):
        """Initialize scratchpad."""
        self.backend: MemoryBackend = InMemoryBackend()
        self.notes: dict[str, Any] = {}  # Structured key-value storage

    def add_note(self, key: str, value: Any) -> None:
        """
        Add a structured note.

        Args:
            key: Note key.
            value: Note value (any type).
        """
        self.notes[key] = value
        logger.debug(f"Added scratchpad note: {key}")

    def get_note(self, key: str) -> Any | None:
        """Get a note by key."""
        return self.notes.get(key)

    def add_memory(self, content: str, tag: str = "") -> str:
        """
        Add an unstructured memory entry (for logging work).

        Args:
            content: Memory content.
            tag: Optional tag for categorization.

        Returns:
            Record ID.
        """
        import uuid

        record = MemoryRecord(
            id=str(uuid.uuid4()),
            content=content,
            metadata={"tag": tag, "type": "scratchpad"},
        )
        self.backend.add([record])
        return record.id

    def search_memory(self, query: str, top_k: int = 5) -> list[MemoryRecord]:
        """Search scratchpad memory entries."""
        return self.backend.search(query, top_k)

    def clear(self) -> None:
        """Clear all scratchpad entries."""
        self.notes.clear()
        self.backend.clear()
        logger.debug("Cleared scratchpad")

    def to_dict(self) -> dict[str, Any]:
        """Export scratchpad as dictionary."""
        return {
            "notes": self.notes,
            "memory_count": self.backend.count(),
        }
