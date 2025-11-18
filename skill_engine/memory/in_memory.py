"""
In-memory backend for short-term and ephemeral memory.

Used for scratchpad and session-scoped memory.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from skill_engine.memory.base import MemoryBackend, MemoryRecord

logger = logging.getLogger(__name__)


class InMemoryBackend:
    """
    Simple in-memory storage for memory records.

    Suitable for:
    - Short-term memory during a session
    - Scratchpad for temporary notes
    - Testing and development
    """

    def __init__(self):
        """Initialize the in-memory backend."""
        self._records: dict[str, MemoryRecord] = {}
        self._order: list[str] = []  # Maintain insertion order

    def add(self, records: list[MemoryRecord]) -> None:
        """
        Add records to memory.

        Args:
            records: List of MemoryRecord objects.
        """
        for record in records:
            if not record.id:
                record.id = str(uuid.uuid4())
            
            if record.id not in self._records:
                self._order.append(record.id)
            
            self._records[record.id] = record
            logger.debug(f"Added memory record: {record.id}")

    def search(self, query: str, top_k: int = 5) -> list[MemoryRecord]:
        """
        Search for similar records (keyword-based fallback).

        Since in-memory doesn't have embeddings, uses simple keyword matching.

        Args:
            query: Query text.
            top_k: Number of results to return.

        Returns:
            List of matching MemoryRecord objects.
        """
        query_lower = query.lower()
        matches = []

        for record in self._records.values():
            content_lower = record.content.lower()
            # Simple keyword matching
            if query_lower in content_lower or any(
                word in content_lower for word in query_lower.split()
            ):
                matches.append(record)

        # Return top_k most recent matches
        matches.sort(key=lambda r: r.timestamp, reverse=True)
        return matches[:top_k]

    def delete(self, ids: list[str]) -> None:
        """
        Delete records by ID.

        Args:
            ids: List of record IDs to delete.
        """
        for id_ in ids:
            if id_ in self._records:
                del self._records[id_]
                self._order.remove(id_)
                logger.debug(f"Deleted memory record: {id_}")

    def get_by_id(self, id: str) -> MemoryRecord | None:
        """
        Retrieve a record by ID.

        Args:
            id: Record ID.

        Returns:
            MemoryRecord or None if not found.
        """
        return self._records.get(id)

    def clear(self) -> None:
        """Clear all records."""
        self._records.clear()
        self._order.clear()
        logger.info("Cleared all memory records")

    def count(self) -> int:
        """Get total number of records."""
        return len(self._records)

    def to_list(self) -> list[MemoryRecord]:
        """Get all records in insertion order."""
        return [self._records[id_] for id_ in self._order if id_ in self._records]
