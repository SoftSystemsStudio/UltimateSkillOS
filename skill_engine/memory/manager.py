"""
MemoryManager – high-level API for memory management.

Initializes and configures all memory tiers and backends.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from skill_engine.memory.base import MemoryBackend
from skill_engine.memory.facade import MemoryFacade
from skill_engine.memory.faiss_backend import FAISSBackend
from skill_engine.memory.in_memory import InMemoryBackend
from skill_engine.memory.tiers import LongTermMemory, Scratchpad, ShortTermMemory

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    High-level memory management API.

    Initializes and coordinates all memory tiers and backends.
    """

    def __init__(
        self,
        long_term_backend: Optional[MemoryBackend] = None,
        index_path: str | Path = ".cache/memory_index",
        db_path: str | Path = ".cache/memory.db",
        embedding_model=None,
    ):
        """
        Initialize the memory manager.

        Args:
            long_term_backend: Backend for long-term memory. If None, uses FAISS.
            index_path: Path for FAISS index storage.
            db_path: Path for SQLite database.
            embedding_model: Embedding model for semantic search.
        """
        logger.info("Initializing MemoryManager")

        # Initialize short-term memory
        self.short_term = ShortTermMemory()
        logger.debug("Initialized short-term memory")

        # Initialize long-term memory with backend
        if long_term_backend is None:
            try:
                long_term_backend = FAISSBackend(
                    index_path=index_path,
                    db_path=db_path,
                    embedding_model=embedding_model,
                )
                logger.debug("Initialized FAISS backend for long-term memory")
            except ImportError:
                logger.warning("FAISS not available, falling back to in-memory")
                long_term_backend = InMemoryBackend()

        self.long_term = LongTermMemory(long_term_backend)
        logger.debug("Initialized long-term memory")

        # Initialize scratchpad
        self.scratchpad = Scratchpad()
        logger.debug("Initialized scratchpad")

        # Create unified facade
        self.facade = MemoryFacade(self.short_term, self.long_term, self.scratchpad)
        logger.info("MemoryManager initialized successfully")

    def get_facade(self) -> MemoryFacade:
        """Get the unified memory facade."""
        return self.facade

    def stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        return self.facade.stats()


# Global singleton instance
_global_memory_manager: Optional[MemoryManager] = None


def get_memory_manager(
    long_term_backend: Optional[MemoryBackend] = None,
    **kwargs,
) -> MemoryFacade:
    """
    Get or create the global memory manager.

    Args:
        long_term_backend: Optional backend for long-term memory.
        **kwargs: Additional arguments for MemoryManager initialization.

    Returns:
        MemoryFacade for memory access.
    """
    global _global_memory_manager

    if _global_memory_manager is None:
        _global_memory_manager = MemoryManager(
            long_term_backend=long_term_backend,
            **kwargs,
        )

    return _global_memory_manager.get_facade()


def reset_memory_manager() -> None:
    """Reset the global memory manager (useful for testing)."""
    global _global_memory_manager
    _global_memory_manager = None
    logger.info("Reset global memory manager")
