"""
Intent Classifier – determines what the user is trying to accomplish.

Uses LLM prompting to classify intents and extract constraints.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class Intent:
    """Represents a classified user intent."""

    primary: str
    """Primary intent category (e.g., 'search', 'memory_recall', 'planning')."""

    confidence: float
    """Confidence score [0.0, 1.0]."""

    constraints: dict[str, Any]
    """Extracted constraints or parameters."""

    alternatives: list[tuple[str, float]] = None
    """Alternative intents ranked by confidence."""

    reasoning: str = ""
    """Explanation of the classification."""

    def __post_init__(self):
        if self.alternatives is None:
            self.alternatives = []


class IntentClassifier:
    """
    Classifies user prompts into structured intents.

    Strategy: LLM-based with fallback to keyword patterns.
    """

    # Fallback keyword-based patterns for when LLM is unavailable
    KEYWORD_PATTERNS = {
        "memory_recall": {
            "keywords": [
                "remember",
                "recall",
                "what do you know",
                "do you remember",
                "remind me",
                "what's my",
                "what is my",
            ],
            "confidence": 0.85,
        },
        "memory_store": {
            "keywords": [
                "remember this",
                "store this",
                "save this",
                "note this",
                "write this down",
            ],
            "confidence": 0.80,
        },
        "research": {
            "keywords": [
                "research",
                "search for",
                "find out",
                "look up",
                "investigate",
                "find information",
                "what's new",
            ],
            "confidence": 0.85,
        },
        "file_operation": {
            "keywords": [
                "file",
                "read",
                "write",
                "save",
                "open",
                "directory",
                "folder",
            ],
            "confidence": 0.80,
        },
        "planning": {
            "keywords": [
                "plan",
                "steps",
                "break down",
                "roadmap",
                "strategy",
                "how do i",
                "how do you",
            ],
            "confidence": 0.80,
        },
        "summarization": {
            "keywords": [
                "summarize",
                "summary",
                "tl;dr",
                "give me the gist",
                "in short",
            ],
            "confidence": 0.85,
        },
        "reflection": {
            "keywords": [
                "reflect",
                "what went wrong",
                "what went right",
                "lessons learned",
                "improve",
            ],
            "confidence": 0.75,
        },
    }

    def __init__(self, use_llm: bool = True):
        """
        Initialize the classifier.

        Args:
            use_llm: If True, attempt LLM-based classification (not implemented yet).
        """
        self.use_llm = use_llm

    def classify(self, prompt: str) -> Intent:
        """
        Classify a user prompt into an intent.

        Args:
            prompt: User's input text.

        Returns:
            Intent object with classification and confidence.
        """
        if self.use_llm:
            return self._classify_with_llm(prompt)
        else:
            return self._classify_with_keywords(prompt)

    def _classify_with_llm(self, prompt: str) -> Intent:
        """
        Classify using LLM (stub for future implementation).

        Args:
            prompt: User's input text.

        Returns:
            Intent from LLM classification.
        """
        # TODO: Integrate with LLM for intent classification
        # For now, fall back to keyword-based classification
        logger.debug("LLM classification not yet implemented, using keywords")
        return self._classify_with_keywords(prompt)

    def _classify_with_keywords(self, prompt: str) -> Intent:
        """
        Classify using keyword patterns (fallback).

        Args:
            prompt: User's input text.

        Returns:
            Intent from keyword matching.
        """
        lowered = prompt.lower()
        matches = []

        for intent_name, pattern_data in self.KEYWORD_PATTERNS.items():
            keywords = pattern_data["keywords"]
            base_confidence = pattern_data["confidence"]

            # Count keyword matches
            match_count = sum(1 for kw in keywords if kw in lowered)

            if match_count > 0:
                # Confidence increases with more keyword matches
                confidence = min(base_confidence + (match_count * 0.05), 1.0)
                matches.append((intent_name, confidence))

        if not matches:
            # Default to summarization
            return Intent(
                primary="summarization",
                confidence=0.5,
                constraints={},
                reasoning="No clear intent detected, defaulting to summarization",
            )

        # Sort by confidence and return top match
        matches.sort(key=lambda x: x[1], reverse=True)
        primary, confidence = matches[0]

        return Intent(
            primary=primary,
            confidence=confidence,
            constraints=self._extract_constraints(prompt),
            alternatives=matches[1:5],
            reasoning=f"Keyword-based classification: {primary}",
        )

    def _extract_constraints(self, prompt: str) -> dict[str, Any]:
        """
        Extract parameters/constraints from the prompt.

        Args:
            prompt: User's input text.

        Returns:
            Dictionary of extracted constraints.
        """
        constraints = {}

        # Look for common constraint patterns
        if any(kw in prompt.lower() for kw in ["limit", "max", "top"]):
            constraints["has_limit"] = True

        if any(kw in prompt.lower() for kw in ["recent", "latest", "new"]):
            constraints["temporal_preference"] = "recent"

        if any(kw in prompt.lower() for kw in ["detailed", "comprehensive", "full"]):
            constraints["detail_level"] = "high"
        elif any(kw in prompt.lower() for kw in ["brief", "short", "quick"]):
            constraints["detail_level"] = "low"

        return constraints
