"""
First-class domain model for the Skill Engine.

Provides strongly-typed data structures for:
- Skill identification and versioning
- Skill input/output contracts
- Agent planning and execution results
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime

# ============================================================================
# Skill Identification & Versioning
# ============================================================================

SkillName = str
"""Type alias for a skill's unique identifier."""


@dataclass(frozen=True)
class SkillVersion:
    """
    Semantic version string for skills (MAJOR.MINOR.PATCH).
    
    Example:
        SkillVersion.parse("1.2.3")
    """
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def parse(cls, version_str: str) -> SkillVersion:
        """Parse a semantic version string."""
        try:
            parts = version_str.split(".")
            if len(parts) != 3:
                raise ValueError(f"Invalid version format: {version_str}")
            major, minor, patch = map(int, parts)
            return cls(major, minor, patch)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Cannot parse version '{version_str}': {e}")


# ============================================================================
# Skill Input/Output Contracts
# ============================================================================

@dataclass
class SkillInput:
    """
    Standardized input contract for skill execution.
    
    Attributes:
        payload: The actual input data as a dictionary.
        trace_id: Unique identifier for tracing execution chains.
        correlation_id: Optional ID for correlating related requests.
        timestamp: When the input was created.
    """
    payload: dict[str, Any]
    trace_id: str
    correlation_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "payload": self.payload,
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SkillOutput:
    """
    Standardized output contract for skill execution.
    
    Attributes:
        payload: The actual result data as a dictionary.
        warnings: List of non-fatal warnings during execution.
        metrics: Performance metrics (execution time, tokens, etc.).
        timestamp: When the output was produced.
    """
    payload: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "payload": self.payload,
            "warnings": self.warnings,
            "metrics": self.metrics,
            "timestamp": self.timestamp.isoformat(),
        }

    def add_warning(self, warning: str) -> None:
        """Add a warning to the output."""
        self.warnings.append(warning)

    def set_metric(self, name: str, value: float) -> None:
        """Record a performance metric."""
        self.metrics[name] = value


# ============================================================================
# Agent Planning & Execution
# ============================================================================

@dataclass
class PlanStep:
    """
    A single step in an agent plan.
    
    Attributes:
        step_id: Unique identifier within the plan.
        skill_name: The skill to execute.
        input_data: Input parameters for the skill.
        description: Human-readable description of the step.
        depends_on: Step IDs that must complete before this one.
        retry_count: Number of retries if execution fails (default: 0).
    """
    step_id: str
    skill_name: SkillName
    input_data: dict[str, Any]
    description: str = ""
    depends_on: list[str] = field(default_factory=list)
    retry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "step_id": self.step_id,
            "skill_name": self.skill_name,
            "input_data": self.input_data,
            "description": self.description,
            "depends_on": self.depends_on,
            "retry_count": self.retry_count,
        }


@dataclass
class AgentPlan:
    """
    A complete execution plan for an agent.
    
    Attributes:
        plan_id: Unique identifier for the plan.
        goal: The high-level goal the plan is meant to achieve.
        steps: Ordered list of steps to execute.
        created_at: When the plan was generated.
        version: Version of the planning logic used.
    """
    plan_id: str
    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0.0"

    def add_step(self, step: PlanStep) -> None:
        """Add a step to the plan."""
        self.steps.append(step)

    def get_step(self, step_id: str) -> PlanStep | None:
        """Retrieve a step by ID."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "steps": [step.to_dict() for step in self.steps],
            "created_at": self.created_at.isoformat(),
            "version": self.version,
        }


@dataclass
class StepResult:
    """
    Result of executing a single plan step.
    
    Attributes:
        step_id: The step that was executed.
        success: Whether the step succeeded.
        output: The skill output (if successful).
        error: Error message (if failed).
        execution_time_ms: How long the step took to execute.
        attempt: Which attempt this result is from.
    """
    step_id: str
    success: bool
    output: SkillOutput | None = None
    error: str | None = None
    execution_time_ms: float = 0.0
    attempt: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "step_id": self.step_id,
            "success": self.success,
            "output": self.output.to_dict() if self.output else None,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "attempt": self.attempt,
        }


@dataclass
class AgentResult:
    """
    Complete result of an agent's execution of a plan.
    
    Attributes:
        plan_id: The plan that was executed.
        status: 'success', 'partial', or 'failed'.
        final_answer: The agent's final answer or conclusion.
        step_results: Results of individual steps.
        total_time_ms: Total execution time.
        steps_completed: Number of steps that completed successfully.
        memory_used: Relevant memory entries that influenced the result.
        metadata: Additional execution metadata.
    """
    plan_id: str
    status: str  # 'success', 'partial', 'failed'
    final_answer: str | None = None
    step_results: list[StepResult] = field(default_factory=list)
    total_time_ms: float = 0.0
    steps_completed: int = 0
    memory_used: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    completed_at: datetime = field(default_factory=datetime.utcnow)

    def add_step_result(self, result: StepResult) -> None:
        """Record the result of a step."""
        self.step_results.append(result)
        if result.success:
            self.steps_completed += 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "plan_id": self.plan_id,
            "status": self.status,
            "final_answer": self.final_answer,
            "step_results": [sr.to_dict() for sr in self.step_results],
            "total_time_ms": self.total_time_ms,
            "steps_completed": self.steps_completed,
            "memory_used": self.memory_used,
            "metadata": self.metadata,
            "completed_at": self.completed_at.isoformat(),
        }

    @property
    def is_successful(self) -> bool:
        """Check if the result indicates overall success."""
        return self.status == "success" and self.final_answer is not None

    def get_failed_steps(self) -> list[StepResult]:
        """Get all steps that failed."""
        return [sr for sr in self.step_results if not sr.success]
