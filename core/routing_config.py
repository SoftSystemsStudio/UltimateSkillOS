"""
Configuration for routing, planning, and skill execution.

Centralizes all configurable parameters for the agent system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class RoutingConfig:
    """Configuration for the routing system."""

    mode: str = "hybrid"
    """Routing mode: 'keyword' (fallback) | 'hybrid' (default) | 'llm_only'."""

    use_llm_for_intent: bool = False
    """Whether to use LLM for intent classification."""

    use_embeddings: bool = True
    """Whether to use embedding-based semantic matching."""

    embedding_model_name: str = "all-MiniLM-L6-v2"
    """Name of the embedding model to use."""

    intent_classifier_confidence_threshold: float = 0.5
    """Minimum confidence for intent classification."""

    skill_selector_confidence_threshold: float = 0.3
    """Minimum confidence for skill selection."""

    enable_skill_chaining: bool = True
    """Whether to allow selecting multiple skills in sequence."""

    max_chain_length: int = 3
    """Maximum number of skills to chain in one execution."""


@dataclass
class PlanningConfig:
    """Configuration for the planning system."""

    use_explicit_planner: bool = True
    """Whether to use the Planner skill to decompose complex goals."""

    planner_max_steps: int = 10
    """Maximum number of steps the planner can suggest."""

    allow_dynamic_replanning: bool = True
    """Whether to replan if execution diverges from plan."""

    plan_optimization: str = "greedy"
    """Plan optimization strategy: 'greedy' | 'cost_aware' | 'parallel'."""


@dataclass
class ExecutionConfig:
    """Configuration for skill execution."""

    max_retries: int = 2
    """Maximum retries for failed skills."""

    retry_backoff_ms: int = 500
    """Milliseconds to wait before retry (multiplied by attempt number)."""

    timeout_ms: int = 30000
    """Timeout for individual skill execution."""

    record_all_outputs: bool = True
    """Whether to record all intermediate outputs."""

    memory_context_size: int = 5
    """Number of memory entries to include in context."""


@dataclass
class AgentConfig:
    """Complete configuration for the Agent."""

    routing: RoutingConfig = None
    planning: PlanningConfig = None
    execution: ExecutionConfig = None
    verbose: bool = False
    log_level: str = "INFO"

    def __post_init__(self):
        if self.routing is None:
            self.routing = RoutingConfig()
        if self.planning is None:
            self.planning = PlanningConfig()
        if self.execution is None:
            self.execution = ExecutionConfig()

    @classmethod
    def default(cls) -> AgentConfig:
        """Create a default configuration."""
        return cls()

    @classmethod
    def keyword_only(cls) -> AgentConfig:
        """Create a configuration using only keyword routing."""
        return cls(routing=RoutingConfig(mode="keyword"))

    @classmethod
    def llm_focused(cls) -> AgentConfig:
        """Create a configuration using LLM-based routing."""
        return cls(
            routing=RoutingConfig(
                mode="llm_only",
                use_llm_for_intent=True,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "routing": {
                "mode": self.routing.mode,
                "use_llm_for_intent": self.routing.use_llm_for_intent,
                "use_embeddings": self.routing.use_embeddings,
            },
            "planning": {
                "use_explicit_planner": self.planning.use_explicit_planner,
                "allow_dynamic_replanning": self.planning.allow_dynamic_replanning,
            },
            "execution": {
                "max_retries": self.execution.max_retries,
                "timeout_ms": self.execution.timeout_ms,
            },
        }
