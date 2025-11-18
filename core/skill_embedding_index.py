"""
Skill Embedding Index – semantic search over skills via embeddings.

Uses sentence-transformers to build and query a skill index.
"""

from __future__ import annotations

import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)


class SkillEmbeddingIndex:
    """
    Semantic index of skills for similarity-based matching.

    Supports:
    - Building index at startup from skill manifests
    - Querying skills by semantic similarity
    - Fast cosine similarity matching
    """

    def __init__(self, embedding_model=None):
        """
        Initialize the embedding index.

        Args:
            embedding_model: Embedding model (e.g., from sentence-transformers).
                           If None, attempts to load 'all-MiniLM-L6-v2'.
        """
        self.embedding_model = embedding_model
        self._skill_embeddings: dict[str, np.ndarray] = {}
        self._skill_texts: dict[str, str] = {}

    def build_index(self, manifests: list) -> None:
        """
        Build embedding index from skill manifests.

        Args:
            manifests: List of SkillManifest objects.
        """
        if not self.embedding_model:
            logger.warning(
                "No embedding model available, skipping semantic index build"
            )
            return

        logger.info(f"Building embedding index for {len(manifests)} skills...")

        for manifest in manifests:
            # Combine description and examples into single text
            text_parts = [
                manifest.description,
                " ".join(manifest.examples),
                " ".join(manifest.tags),
            ]
            combined_text = " ".join(text_parts)

            self._skill_texts[manifest.name] = combined_text

            try:
                embedding = self.embedding_model.encode(combined_text)
                self._skill_embeddings[manifest.name] = embedding
            except Exception as e:
                logger.warning(
                    f"Failed to embed skill '{manifest.name}': {e}"
                )

        logger.info(f"Built index with {len(self._skill_embeddings)} embeddings")

    def search(
        self, query: str, top_k: int = 5, threshold: float = 0.3
    ) -> list[tuple[str, float]]:
        """
        Search for skills semantically similar to a query.

        Args:
            query: Search query text.
            top_k: Number of results to return.
            threshold: Minimum similarity score [0.0, 1.0].

        Returns:
            List of (skill_name, similarity_score) tuples.
        """
        if not self.embedding_model:
            logger.debug("No embedding model, returning empty search results")
            return []

        if not self._skill_embeddings:
            logger.warning("No skills in index, search returns empty")
            return []

        try:
            query_embedding = self.embedding_model.encode(query)
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            return []

        scores = []
        for skill_name, skill_embedding in self._skill_embeddings.items():
            # Cosine similarity
            similarity = self._cosine_similarity(query_embedding, skill_embedding)

            if similarity >= threshold:
                scores.append((skill_name, similarity))

        # Sort by similarity (descending)
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores[:top_k]

    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors.

        Args:
            vec1: First vector.
            vec2: Second vector.

        Returns:
            Cosine similarity in range [0.0, 1.0].
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def get_skill_text(self, skill_name: str) -> Optional[str]:
        """Get the indexed text for a skill."""
        return self._skill_texts.get(skill_name)
