"""
Memory system for the Skill Engine.

Provides:
- Abstract MemoryBackend protocol
- Multiple storage backends (in-memory, FAISS+SQLite)
- Memory tiers (short-term, long-term, scratchpad)
- Unified MemoryFacade for skill access
"""

from __future__ import annotations

from skill_engine.memory.base import MemoryBackend, MemoryRecord
from skill_engine.memory.facade import MemoryFacade
from skill_engine.memory.faiss_backend import FAISSBackend
from skill_engine.memory.in_memory import InMemoryBackend
from skill_engine.memory.manager import MemoryManager, get_memory_manager, reset_memory_manager
from skill_engine.memory.tiers import LongTermMemory, Scratchpad, ShortTermMemory

__all__ = [
    # Base
    "MemoryBackend",
    "MemoryRecord",
    # Backends
    "InMemoryBackend",
    "FAISSBackend",
    # Tiers
    "ShortTermMemory",
    "LongTermMemory",
    "Scratchpad",
    # Facade
    "MemoryFacade",
    # Manager
    "MemoryManager",
    "get_memory_manager",
    "reset_memory_manager",
]
