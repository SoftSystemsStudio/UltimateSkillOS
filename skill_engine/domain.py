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
from skill_engine.router import Router
from skill_engine.memory.facade import MemoryFacade

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

    def compute_confidence(self) -> float:
        """
        Compute the overall confidence score based on step results.

        Returns:
            float: The average confidence score across all steps.
        """
        confidences = [sr.output.metrics.get("confidence", 0) for sr in self.step_results if sr.success]
        return sum(confidences) / len(confidences) if confidences else 0.0

    def flag_low_confidence_steps(self, threshold: float = 0.5) -> list[StepResult]:
        """
        Identify steps with low confidence scores.

        Args:
            threshold (float): The confidence threshold below which steps are flagged.

        Returns:
            list[StepResult]: Steps with confidence below the threshold.
        """
        return [sr for sr in self.step_results if sr.output.metrics.get("confidence", 1) < threshold]

    def to_trace(self) -> str:
        """
        Generate a traceable reasoning chain for the agent's execution.

        Returns:
            str: A formatted string showing the reasoning chain.
        """
        trace_lines = [f"Plan ID: {self.plan_id}", f"Status: {self.status}"]
        for step_result in self.step_results:
            trace_lines.append(f"Step ID: {step_result.step_id}")
            trace_lines.append(f"  Success: {step_result.success}")
            if step_result.success:
                trace_lines.append(f"  Output: {step_result.output.payload}")
            else:
                trace_lines.append(f"  Error: {step_result.error}")
            trace_lines.append(f"  Execution Time: {step_result.execution_time_ms} ms")
        trace_lines.append(f"Final Answer: {self.final_answer}")
        return "\n".join(trace_lines)


@dataclass
class Agent:
    """
    The Agent class orchestrates the execution of plans by invoking skills
    or using the Router for sub-tasks.
    """
    router: Router
    memory: MemoryFacade

    def execute_plan(self, plan: AgentPlan) -> AgentResult:
        """
        Execute a given plan step-by-step.

        Args:
            plan (AgentPlan): The plan to execute.

        Returns:
            AgentResult: The result of the plan execution.
        """
        step_results = []
        memory_context = self.memory.retrieve_context(plan.goal)
        total_time = 0.0

        for step in plan.steps:
            start_time = datetime.utcnow()
            try:
                # Inject memory context into the step input
                step.input_data.update(memory_context)

                # Use the Router to invoke the skill
                skill_output = self.router.route(
                    skill_name=step.skill_name,
                    input_data=SkillInput(
                        payload=step.input_data,
                        trace_id=plan.plan_id
                    )
                )

                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                step_results.append(StepResult(
                    step_id=step.step_id,
                    success=True,
                    output=skill_output,
                    execution_time_ms=execution_time
                ))
                total_time += execution_time

            except Exception as e:
                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                step_results.append(StepResult(
                    step_id=step.step_id,
                    success=False,
                    error=str(e),
                    execution_time_ms=execution_time
                ))
                total_time += execution_time

        # Determine overall status
        status = "success" if all(sr.success for sr in step_results) else "partial"
        final_answer = step_results[-1].output.payload if step_results and step_results[-1].success else None

        return AgentResult(
            plan_id=plan.plan_id,
            status=status,
            final_answer=final_answer,
            step_results=step_results,
            total_time_ms=total_time,
            steps_completed=sum(1 for sr in step_results if sr.success),
            memory_used=memory_context
        )
