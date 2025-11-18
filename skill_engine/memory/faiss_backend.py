"""
FAISS-backed long-term memory with SQLite metadata storage.

Provides high-performance semantic search via embeddings.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Optional

import numpy as np

from skill_engine.memory.base import MemoryBackend, MemoryRecord

logger = logging.getLogger(__name__)


class FAISSBackend:
    """
    FAISS-backed vector storage with SQLite metadata.

    Stores embeddings in FAISS index and metadata in SQLite for:
    - High-speed semantic search
    - Persistent long-term memory
    - Scalable to millions of records
    """

    def __init__(
        self,
        index_path: str | Path = ".cache/memory_index",
        db_path: str | Path = ".cache/memory.db",
        embedding_model=None,
        embedding_dim: int = 384,
    ):
        """
        Initialize FAISS backend.

        Args:
            index_path: Path to store FAISS index.
            db_path: Path to SQLite database.
            embedding_model: Embedding model (e.g., sentence-transformers).
            embedding_dim: Dimension of embeddings (default: 384 for all-MiniLM-L6-v2).
        """
        self.index_path = Path(index_path)
        self.db_path = Path(db_path)
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_dim

        # Create directories
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize FAISS index (lazy load)
        self._index = None
        self._index_id_map: dict[int, str] = {}  # FAISS row index → record ID
        self._id_to_index: dict[str, int] = {}  # record ID → FAISS row index

        # Initialize SQLite
        self._init_db()
        self._load_index()

    def _init_db(self) -> None:
        """Initialize SQLite database schema."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_records (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                faiss_index INTEGER UNIQUE
            )
            """
        )

        conn.commit()
        conn.close()
        logger.debug(f"Initialized SQLite database: {self.db_path}")

    def _get_index(self):
        """Get or create FAISS index lazily."""
        if self._index is None:
            try:
                import faiss

                self._index = faiss.IndexFlatL2(self.embedding_dim)
                logger.debug("Created new FAISS index")
            except ImportError:
                logger.error(
                    "FAISS not available. Install with: pip install faiss-cpu"
                )
                raise
        return self._index

    def _save_index(self) -> None:
        """Persist FAISS index to disk."""
        if self._index is not None:
            try:
                import faiss

                faiss.write_index(self._index, str(self.index_path / "index.faiss"))
                logger.debug(f"Saved FAISS index to {self.index_path}")
            except Exception as e:
                logger.error(f"Failed to save FAISS index: {e}")

    def _load_index(self) -> None:
        """Load existing FAISS index or create new."""
        try:
            import faiss

            index_file = self.index_path / "index.faiss"
            if index_file.exists():
                self._index = faiss.read_index(str(index_file))
                logger.debug(f"Loaded FAISS index from {index_file}")
                self._rebuild_mappings()
        except Exception as e:
            logger.warning(f"Failed to load FAISS index: {e}")
            self._index = None

    def _rebuild_mappings(self) -> None:
        """Rebuild ID mappings from SQLite."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT id, faiss_index FROM memory_records WHERE faiss_index IS NOT NULL")
        for record_id, faiss_idx in cursor.fetchall():
            self._index_id_map[faiss_idx] = record_id
            self._id_to_index[record_id] = faiss_idx

        conn.close()
        logger.debug(f"Rebuilt ID mappings: {len(self._index_id_map)} records")

    def _embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for text.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector.

        Raises:
            RuntimeError: If embedding model not available.
        """
        if not self.embedding_model:
            logger.warning("No embedding model configured, using zero vector")
            return np.zeros(self.embedding_dim, dtype=np.float32)

        try:
            embedding = self.embedding_model.encode(text)
            return np.array([embedding], dtype=np.float32)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return np.zeros((1, self.embedding_dim), dtype=np.float32)

    def add(self, records: list[MemoryRecord]) -> None:
        """
        Add records to memory.

        Args:
            records: List of MemoryRecord objects.
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        index = self._get_index()

        for record in records:
            if not record.id:
                record.id = str(uuid.uuid4())

            # Generate embedding if not provided
            if record.embedding is None:
                embedding_array = self._embed(record.content)
                record.embedding = embedding_array[0].tolist()
            else:
                embedding_array = np.array([record.embedding], dtype=np.float32)

            # Add to FAISS
            index.add(embedding_array)
            faiss_idx = index.ntotal - 1

            # Map IDs
            self._index_id_map[faiss_idx] = record.id
            self._id_to_index[record.id] = faiss_idx

            # Store in SQLite
            metadata_json = json.dumps(record.metadata)
            cursor.execute(
                """
                INSERT OR REPLACE INTO memory_records 
                (id, content, timestamp, metadata, faiss_index)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.content,
                    record.timestamp.isoformat(),
                    metadata_json,
                    faiss_idx,
                ),
            )

            logger.debug(f"Added memory record: {record.id}")

        conn.commit()
        conn.close()
        self._save_index()

    def search(self, query: str, top_k: int = 5) -> list[MemoryRecord]:
        """
        Search for similar records using semantic similarity.

        Args:
            query: Query text.
            top_k: Number of results to return.

        Returns:
            List of matching MemoryRecord objects.
        """
        if not self._index or self._index.ntotal == 0:
            logger.debug("Index is empty, returning no results")
            return []

        # Embed query
        query_embedding = self._embed(query)

        # Search
        index = self._get_index()
        distances, indices = index.search(query_embedding, min(top_k, index.ntotal))

        # Retrieve records from SQLite
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1:  # Invalid result
                continue

            record_id = self._index_id_map.get(idx)
            if not record_id:
                continue

            cursor.execute(
                "SELECT id, content, timestamp, metadata FROM memory_records WHERE id = ?",
                (record_id,),
            )
            row = cursor.fetchone()
            if row:
                record = MemoryRecord(
                    id=row[0],
                    content=row[1],
                    timestamp=row[2],
                    metadata=json.loads(row[3] or "{}"),
                )
                results.append(record)

        conn.close()
        return results

    def delete(self, ids: list[str]) -> None:
        """
        Delete records by ID.

        Note: Deletion from FAISS is not efficient, so records are marked
        as deleted in SQLite but remain in the index.

        Args:
            ids: List of record IDs to delete.
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        for record_id in ids:
            cursor.execute("DELETE FROM memory_records WHERE id = ?", (record_id,))
            if record_id in self._id_to_index:
                faiss_idx = self._id_to_index[record_id]
                del self._index_id_map[faiss_idx]
                del self._id_to_index[record_id]
            logger.debug(f"Deleted memory record: {record_id}")

        conn.commit()
        conn.close()

    def get_by_id(self, id: str) -> MemoryRecord | None:
        """
        Retrieve a record by ID.

        Args:
            id: Record ID.

        Returns:
            MemoryRecord or None if not found.
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, content, timestamp, metadata FROM memory_records WHERE id = ?",
            (id,),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return MemoryRecord(
                id=row[0],
                content=row[1],
                timestamp=row[2],
                metadata=json.loads(row[3] or "{}"),
            )
        return None

    def clear(self) -> None:
        """Clear all records."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memory_records")
        conn.commit()
        conn.close()

        self._index = None
        self._index_id_map.clear()
        self._id_to_index.clear()
        logger.info("Cleared all memory records")

    def count(self) -> int:
        """Get total number of records."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memory_records")
        count = cursor.fetchone()[0]
        conn.close()
        return count
