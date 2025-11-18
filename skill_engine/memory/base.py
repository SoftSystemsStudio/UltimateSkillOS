"""
Memory system for the Skill Engine.

Provides:
- Abstract MemoryBackend protocol
- Memory tiers (short-term, long-term, scratchpad)
- Unified MemoryFacade for skill access
- Integration with RunContext
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@dataclass
class MemoryRecord:
    """
    A single memory record with metadata.

    Attributes:
        id: Unique identifier.
        content: The actual memory content.
        timestamp: When the memory was created.
        metadata: Additional metadata (tags, source, etc.).
        embedding: Optional vector embedding.
    """

    id: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "embedding": self.embedding,
        }


@runtime_checkable
class MemoryBackend(Protocol):
    """
    Abstract protocol for memory backends.

    Implementations provide storage and retrieval of memory records.
    """

    def add(self, records: list[MemoryRecord]) -> None:
        """
        Add records to memory.

        Args:
            records: List of MemoryRecord objects to store.
        """
        ...

    def search(self, query: str, top_k: int = 5) -> list[MemoryRecord]:
        """
        Search for similar records.

        Args:
            query: Query text.
            top_k: Number of top results to return.

        Returns:
            List of MemoryRecord objects, ranked by relevance.
        """
        ...

    def delete(self, ids: list[str]) -> None:
        """
        Delete records by ID.

        Args:
            ids: List of record IDs to delete.
        """
        ...

    def get_by_id(self, id: str) -> MemoryRecord | None:
        """
        Retrieve a record by ID.

        Args:
            id: Record ID.

        Returns:
            MemoryRecord or None if not found.
        """
        ...

    def clear(self) -> None:
        """Clear all records from memory."""
        ...

    def count(self) -> int:
        """Get total number of records."""
        ...
