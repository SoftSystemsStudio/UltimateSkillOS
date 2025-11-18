# core/router.py

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from core.intent_classifier import IntentClassifier
from core.skill_selector import SkillSelector
from core.skill_embedding_index import SkillEmbeddingIndex
from core.routing_config import RoutingConfig
from skills.skill_manifest import list_manifests

logger = logging.getLogger(__name__)


class RouterStrategy:
    """
    Abstract base class for router strategies.
    """
    def route(self, text: str) -> Dict[str, Any]:
        raise NotImplementedError()

class KeywordRouter(RouterStrategy):
    def __init__(self, router: Router):
        self.router = router
    def route(self, text: str) -> Dict[str, Any]:
        return self.router._route_keyword(text)

class HybridRouter(RouterStrategy):
    def __init__(self, router: Router):
        self.router = router
    def route(self, text: str) -> Dict[str, Any]:
        return self.router._route_hybrid(text)

class MLRouter(RouterStrategy):
    def __init__(self, model, router: Router):
        self.model = model
        self.router = router
    def route(self, text: str) -> Dict[str, Any]:
        # Placeholder: use model to predict skill sequence
        # If model is not confident, fallback to hybrid
        prediction = self.model.predict([text]) if self.model else None
        if prediction:
            return {
                "use_skill": prediction[0],
                "confidence": 0.95,
                "params": {"text": text},
                "reasoning": "MLRouter prediction"
            }
        else:
            return self.router._route_hybrid(text)

class Router:
    """
    Intelligent router that routes user queries to skills.

    Strategy (configurable):
    1. hybrid (default): Intent classification + skill selection + embeddings
    2. llm_only: Pure LLM-based routing
    3. keyword: Legacy keyword-based fallback

    Components:
    - IntentClassifier: Determines user intent
    - SkillSelector: Maps intent → skill with rules
    - SkillEmbeddingIndex: Semantic skill matching
    """

    def __init__(
        self,
        config: RoutingConfig | None = None,
        embedding_model=None,
    ):
        """
        Initialize the router with configuration.

        Args:
            config: RoutingConfig object. If None, uses default.
            embedding_model: Embedding model for semantic matching.
        """
        self.config = config or RoutingConfig()
        self.embedding_model = embedding_model
        self.prior_skill: Optional[str] = None

        # Initialize components
        self.intent_classifier = IntentClassifier(
            use_llm=self.config.use_llm_for_intent
        )
        self.skill_selector = SkillSelector(embedding_model=embedding_model)
        self.skill_embedding_index = SkillEmbeddingIndex(
            embedding_model=embedding_model
        )

        # Build embedding index if available
        if (
            self.embedding_model
            and self.config.use_embeddings
            and self.config.mode in ("hybrid", "llm_only")
        ):
            try:
                manifests = list_manifests()
                self.skill_embedding_index.build_index(manifests)
            except Exception as e:
                logger.warning(f"Failed to build skill embedding index: {e}")

    def set_strategy(self, strategy: str, model=None):
        if strategy == "keyword":
            self.strategy = KeywordRouter(self)
        elif strategy == "hybrid":
            self.strategy = HybridRouter(self)
        elif strategy == "ml":
            self.strategy = MLRouter(model, self)
        else:
            raise ValueError(f"Unknown router strategy: {strategy}")
        logger.info(f"Router strategy set to: {strategy}")

    def route(self, text: str) -> Dict[str, Any]:
        if hasattr(self, "strategy"):
            result = self.strategy.route(text)
            # Fallback to keyword router if ML confidence is low
            if result.get("confidence", 1.0) < 0.6 and not isinstance(self.strategy, KeywordRouter):
                logger.info("Low confidence, falling back to keyword router.")
                return KeywordRouter(self).route(text)
            return result

        """
        Route a query to the best skill.

        Args:
            text: User query text.

        Returns:
            Dict with keys:
            - use_skill: Selected skill name
            - confidence: Confidence score
            - params: Skill parameters
            - reasoning: Explanation
        """
        query = text.strip()

        if self.config.mode == "keyword":
            return self._route_keyword(query)
        elif self.config.mode == "llm_only":
            return self._route_llm_only(query)
        else:  # hybrid
            return self._route_hybrid(query)

    def _route_keyword(self, query: str) -> Dict[str, Any]:
        """
        Legacy keyword-based routing (fallback).

        Args:
            query: User query.

        Returns:
            Routing decision.
        """
        lowered = query.lower()

        # Memory recall
        if any(
            phrase in lowered
            for phrase in [
                "what is my",
                "what's my",
                "do you remember",
                "remember when",
                "remember that",
                "recall",
                "remind me",
            ]
        ):
            return {
                "use_skill": "memory_search",
                "confidence": 0.9,
                "params": {"query": query, "text": query},
                "reasoning": "Keyword match: memory recall",
            }

        # Memory store
        if any(
            phrase in lowered
            for phrase in [
                "remember this",
                "store this",
                "save this in memory",
                "note this down",
            ]
        ):
            return {
                "use_skill": "summarize",
                "confidence": 0.8,
                "params": {"text": query},
                "reasoning": "Keyword match: memory store",
            }

        # Research
        if any(
            kw in lowered
            for kw in [
                "search for",
                "look up",
                "google",
                "research",
                "find out about",
            ]
        ):
            return {
                "use_skill": "research",
                "confidence": 0.9,
                "params": {"query": query, "text": query},
                "reasoning": "Keyword match: research",
            }

        # File operations
        if any(
            kw in lowered
            for kw in [
                "file",
                "read file",
                "write file",
                "open file",
                "save file",
            ]
        ):
            return {
                "use_skill": "file",
                "confidence": 0.9,
                "params": {"command": query, "text": query},
                "reasoning": "Keyword match: file operation",
            }

        # Planning
        if any(
            kw in lowered
            for kw in ["plan", "roadmap", "steps", "strategy", "break this down"]
        ):
            return {
                "use_skill": "planner",
                "confidence": 0.8,
                "params": {"goal": query},
                "reasoning": "Keyword match: planning",
            }

        # Summarization
        if any(
            kw in lowered for kw in ["summarize", "shorten", "tl;dr"]
        ):
            return {
                "use_skill": "summarize",
                "confidence": 0.9,
                "params": {"text": query},
                "reasoning": "Keyword match: summarization",
            }

        # Default fallback
        return {
            "use_skill": "summarize",
            "confidence": 0.5,
            "params": {"text": query},
            "reasoning": "Keyword fallback: no clear match",
        }

    def _route_hybrid(self, query: str) -> Dict[str, Any]:
        """
        Hybrid routing: intent classification + skill selection + embeddings.

        Args:
            query: User query.

        Returns:
            Routing decision.
        """
        # Step 1: Classify intent
        intent = self.intent_classifier.classify(query)
        logger.debug(f"Classified intent: {intent.primary} ({intent.confidence:.2f})")

        # Step 2: Select skill for intent
        selection = self.skill_selector.select(
            intent.primary,
            intent.constraints,
            prior_skill=self.prior_skill,
        )
        logger.debug(
            f"Selected skill: {selection.primary_skill} ({selection.confidence:.2f})"
        )

        # Step 3: Optionally refine with semantic search
        semantic_matches = self.skill_embedding_index.search(
            query, top_k=3, threshold=0.3
        )
        if semantic_matches:
            semantic_top, semantic_score = semantic_matches[0]
            logger.debug(
                f"Semantic top match: {semantic_top} ({semantic_score:.2f})"
            )

            # Blend semantic score with selected skill
            if semantic_top == selection.primary_skill:
                selection.confidence = min(
                    1.0,
                    (selection.confidence + semantic_score) / 2
                )

        # Build parameters for the skill
        params = self._build_params(selection.primary_skill, query)

        self.prior_skill = selection.primary_skill

        return {
            "use_skill": selection.primary_skill,
            "confidence": selection.confidence,
            "params": params,
            "reasoning": f"{selection.reasoning} (intent: {intent.primary})",
            "intent": intent.primary,
        }

    def _route_llm_only(self, query: str) -> Dict[str, Any]:
        """
        LLM-only routing (future implementation).

        For now, falls back to hybrid.

        Args:
            query: User query.

        Returns:
            Routing decision.
        """
        logger.debug("LLM-only routing not yet implemented, using hybrid")
        return self._route_hybrid(query)

    def _build_params(self, skill_name: str, query: str) -> Dict[str, Any]:
        """
        Build input parameters for a skill.

        Args:
            skill_name: Name of the skill to build params for.
            query: User query.

        Returns:
            Dictionary of parameters.
        """
        # Default: include the query text
        params = {"text": query}

        # Skill-specific parameter sets
        if skill_name == "memory_search":
            params = {"query": query, "text": query}
        elif skill_name == "research":
            params = {"query": query, "text": query}
        elif skill_name == "file":
            params = {"command": query, "text": query}
        elif skill_name == "planner":
            params = {"goal": query}
        elif skill_name in ("summarize", "reflection"):
            params = {"text": query}

        return params

    def set_routing_mode(self, mode: str) -> None:
        """Change routing mode at runtime."""
        if mode not in ("keyword", "hybrid", "llm_only"):
            raise ValueError(f"Unknown routing mode: {mode}")
        self.config.mode = mode
        logger.info(f"Router mode changed to: {mode}")
