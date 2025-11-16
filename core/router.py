# core/router.py

from __future__ import annotations

from typing import Any, Dict


class Router:
    """
    Lightweight natural-language router that decides which skill to invoke.

    Contract:
        route(text: str) -> {
            "use_skill": <skill_name>,
            "confidence": float,
            "params": dict
        }
    """

    def route(self, text: str) -> Dict[str, Any]:
        query = text.strip()
        lowered = query.lower()

        # Default routing: summarize the input text
        default_skill = "summarize"
        default_confidence = 0.5
        default_params: Dict[str, Any] = {"text": query}

        # ------------------------------------------------------------------
        # Memory recall / personal context
        # ------------------------------------------------------------------
        # Heuristics: "what is my", "what's my", "do you remember", "recall", etc.
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
            # Route to memory_search.
            # Provide both "query" and "text" to keep it compatible with
            # varying skill implementations.
            return {
                "use_skill": "memory_search",
                "confidence": 0.9,
                "params": {
                    "query": query,
                    "text": query,
                },
            }

        # Explicit memory write phrases can still leverage summarize,
        # since your summarize skill is already writing to memory.
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
            }

        # ------------------------------------------------------------------
        # Research / web search
        # ------------------------------------------------------------------
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
                "params": {
                    "query": query,
                    "text": query,
                },
            }

        # ------------------------------------------------------------------
        # File operations
        # ------------------------------------------------------------------
        # Skill name is "file" (as per your registered skills),
        # even though the module is file_tool.py.
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
                "params": {
                    "command": query,
                    "text": query,
                },
            }

        # ------------------------------------------------------------------
        # Planning / decomposition
        # ------------------------------------------------------------------
        if any(
            kw in lowered
            for kw in [
                "plan",
                "roadmap",
                "steps",
                "strategy",
                "break this down",
            ]
        ):
            return {
                "use_skill": "planner",
                "confidence": 0.8,
                "params": {"goal": query},
            }

        # ------------------------------------------------------------------
        # Explicit summarization
        # ------------------------------------------------------------------
        if any(
            kw in lowered
            for kw in [
                "summarize",
                "shorten",
                "tl;dr",
            ]
        ):
            return {
                "use_skill": "summarize",
                "confidence": 0.9,
                "params": {"text": query},
            }

        # ------------------------------------------------------------------
        # Fallback: summarize
        # ------------------------------------------------------------------
        return {
            "use_skill": default_skill,
            "confidence": default_confidence,
            "params": default_params,
        }
