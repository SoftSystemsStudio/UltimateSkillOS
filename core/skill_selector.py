"""
Skill Selector – maps intents to executable skills.

Uses embeddings, rules, and semantic matching to select optimal skills.
"""

from __future__ import annotations

import logging
import numpy as np
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SkillSelection:
    """Result of skill selection for a given intent."""

    def __init__(
        self,
        primary_skill: str,
        confidence: float,
        alternatives: list[tuple[str, float]] | None = None,
        reasoning: str = "",
    ):
        self.primary_skill = primary_skill
        self.confidence = confidence
        self.alternatives = alternatives or []
        self.reasoning = reasoning

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "primary_skill": self.primary_skill,
            "confidence": self.confidence,
            "alternatives": self.alternatives,
            "reasoning": self.reasoning,
        }


class SkillSelector:
    """
    Maps intents to skills using embeddings, rules, and semantic matching.

    Strategy: LLM + embeddings + priority rules
    """

    # Intent → skills mapping with priority ordering
    INTENT_SKILL_MAPPING = {
        "memory_recall": ["memory_search", "summarize"],
        "memory_store": ["summarize", "memory_search"],
        "research": ["research", "memory_search"],
        "file_operation": ["file", "research"],
        "planning": ["planner", "reflection"],
        "summarization": ["summarize", "reflection"],
        "reflection": ["reflection", "summarize"],
    }

    # Skill compatibility rules
    SKILL_RULES = {
        "memory_search": {
            "cannot_follow": ["memory_search"],  # Don't chain memory_search after itself
            "priority": 10,
            "cost": 0.6,
        },
        "research": {
            "cannot_follow": ["research"],
            "priority": 9,
            "cost": 2.5,
        },
        "summarize": {
            "cannot_follow": [],
            "priority": 5,
            "cost": 0.8,
        },
        "file": {
            "cannot_follow": [],
            "priority": 8,
            "cost": 0.7,
        },
        "planner": {
            "cannot_follow": ["planner"],
            "priority": 10,
            "cost": 1.2,
        },
        "reflection": {
            "cannot_follow": ["reflection"],
            "priority": 6,
            "cost": 1.5,
        },
    }

    def __init__(self, embedding_model=None):
        """
        Initialize the skill selector.

        Args:
            embedding_model: Optional embedding model for semantic matching.
                           Uses sentence-transformers if available.
        """
        self.embedding_model = embedding_model
        self._embedding_cache: dict[str, np.ndarray] = {}

    def select(
        self,
        intent_primary: str,
        intent_constraints: dict[str, Any] | None = None,
        prior_skill: str | None = None,
        available_skills: list[str] | None = None,
    ) -> SkillSelection:
        """
        Select the best skill(s) for an intent.

        Args:
            intent_primary: Primary intent classification.
            intent_constraints: Constraints extracted from user input.
            prior_skill: Previously selected skill (to avoid repeats).
            available_skills: List of available skills (if None, use all).

        Returns:
            SkillSelection with primary skill and alternatives.
        """
        intent_constraints = intent_constraints or {}

        # Step 1: Get candidate skills for this intent
        candidates = self.INTENT_SKILL_MAPPING.get(
            intent_primary, ["summarize"]
        ).copy()

        if available_skills:
            candidates = [s for s in candidates if s in available_skills]

        if not candidates:
            return SkillSelection(
                primary_skill="summarize",
                confidence=0.3,
                reasoning=f"No skills available for intent '{intent_primary}', defaulting",
            )

        # Step 2: Filter out skills that violate rules
        if prior_skill:
            candidates = self._apply_compatibility_rules(prior_skill, candidates)

        if not candidates:
            # Fall back to the full mapping
            candidates = self.INTENT_SKILL_MAPPING.get(
                intent_primary, ["summarize"]
            ).copy()

        # Step 3: Rank candidates
        ranked = self._rank_candidates(candidates, intent_constraints)

        if not ranked:
            return SkillSelection(
                primary_skill="summarize",
                confidence=0.3,
                reasoning="Could not rank candidates, defaulting",
            )

        primary, confidence = ranked[0]
        alternatives = ranked[1:5]

        return SkillSelection(
            primary_skill=primary,
            confidence=confidence,
            alternatives=alternatives,
            reasoning=f"Selected '{primary}' for intent '{intent_primary}' (confidence: {confidence:.2f})",
        )

    def _apply_compatibility_rules(
        self, prior_skill: str, candidates: list[str]
    ) -> list[str]:
        """
        Filter candidates based on compatibility rules.

        Args:
            prior_skill: The skill that was just executed.
            candidates: List of candidate skills.

        Returns:
            Filtered list of compatible candidates.
        """
        if prior_skill not in self.SKILL_RULES:
            return candidates

        rules = self.SKILL_RULES[prior_skill]
        cannot_follow = rules.get("cannot_follow", [])

        # Remove skills that cannot follow the prior skill
        return [s for s in candidates if s not in cannot_follow]

    def _rank_candidates(
        self, candidates: list[str], constraints: dict[str, Any]
    ) -> list[tuple[str, float]]:
        """
        Rank candidate skills by relevance and cost.

        Args:
            candidates: List of candidate skill names.
            constraints: Extracted constraints from user input.

        Returns:
            Sorted list of (skill_name, confidence) tuples.
        """
        ranked = []

        for i, skill in enumerate(candidates):
            # Base score: earlier in the list gets higher score
            position_score = 1.0 - (i * 0.15)

            # Apply rules-based adjustments
            if skill in self.SKILL_RULES:
                rule = self.SKILL_RULES[skill]
                priority = rule.get("priority", 5)
                cost = rule.get("cost", 1.0)

                # Higher priority = higher score, higher cost = lower score
                priority_bonus = priority * 0.05
                cost_penalty = max(0, cost - 1.0) * 0.05
            else:
                priority_bonus = 0.5
                cost_penalty = 0.0

            # Constraint-based adjustments
            detail_adjustment = 0.0
            if constraints.get("detail_level") == "high" and skill in [
                "research",
                "reflection",
            ]:
                detail_adjustment = 0.1
            elif constraints.get("detail_level") == "low" and skill in [
                "summarize",
            ]:
                detail_adjustment = 0.1

            confidence = min(
                1.0,
                position_score + priority_bonus - cost_penalty + detail_adjustment,
            )
            ranked.append((skill, confidence))

        # Sort by confidence (descending)
        ranked.sort(key=lambda x: x[1], reverse=True)

        return ranked

    def select_multiple(
        self,
        intent_primary: str,
        intent_constraints: dict[str, Any] | None = None,
        count: int = 3,
    ) -> list[str]:
        """
        Select multiple skills for an intent (e.g., for pipeline execution).

        Args:
            intent_primary: Primary intent classification.
            intent_constraints: Constraints extracted from user input.
            count: Number of skills to select.

        Returns:
            List of skill names.
        """
        selection = self.select(intent_primary, intent_constraints)
        skills = [selection.primary_skill]

        for skill, _ in selection.alternatives[:count - 1]:
            if skill not in skills:
                skills.append(skill)

        return skills
