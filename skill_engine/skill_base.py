"""
Formal Skill interface using Protocol for structural typing.

Enforces:
- Pydantic validation at all boundaries
- Structured error handling
- Clear skill contracts (input/output schemas)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, ValidationError

from skill_engine.domain import SkillInput, SkillName, SkillOutput, SkillVersion

logger = logging.getLogger(__name__)

# resilience primitives (circuit breaker)
from skill_engine.resilience import CircuitOpen, CircuitBreakerConfig, CircuitBreaker


class RunContext:
    """
    Execution context passed to skill invocations.
    
    Provides:
    - Trace and correlation IDs for observability
    - Memory context from prior steps
    - Configuration and runtime parameters
    - Unified memory access via facade
    """

    def __init__(
        self,
        trace_id: str,
        correlation_id: str | None = None,
        memory_context: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        memory_facade: Optional[Any] = None,
        logger: Optional[logging.Logger] = None,
        circuit_registry: Optional[Any] = None,
    ):
        self.trace_id = trace_id
        self.correlation_id = correlation_id
        self.memory_context = memory_context or []
        self.metadata = metadata or {}
        self.memory = memory_facade  # MemoryFacade for skills to interact with memory
        # Logger (structured) available to skills; falls back to module logger
        self.logger = logger or logging.getLogger(__name__)
        # Optional circuit breaker registry injected by caller
        self.circuit_registry = circuit_registry

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for serialization."""
        return {
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "memory_context": self.memory_context,
            "metadata": self.metadata,
        }


@runtime_checkable
class Skill(Protocol):
    """
    Formal interface that all skills must implement.
    
    Uses Protocol for structural typing - any class with these attributes
    and methods will satisfy the interface without explicit inheritance.
    
    All data crossing boundaries is validated with Pydantic models.
    """

    name: SkillName
    """Unique skill identifier."""

    version: str
    """Semantic version string (MAJOR.MINOR.PATCH)."""

    description: str
    """Human-readable skill description."""

    input_schema: type[BaseModel]
    """Pydantic model for validating input payload."""

    output_schema: type[BaseModel]
    """Pydantic model for validating output payload."""

    # Optional SLA configuration for this skill (timeout, retries, circuit_breaker)
    sla: Any | None

    def invoke(
        self, input_data: SkillInput, context: RunContext
    ) -> SkillOutput:
        """
        Execute the skill with validated input.

        Args:
            input_data: Validated skill input with trace/correlation IDs.
            context: Execution context with memory and metadata.

        Returns:
            Validated skill output with metrics and warnings.

        Raises:
            ValidationError: If input or output fails schema validation.
            RuntimeError: If skill execution fails.
        """
        ...


@dataclass
class SLA:
    """Simple per-skill SLA configuration.

    `circuit_breaker` may be either a boolean (enable default breaker) or
    a mapping/dict that will be used to construct `CircuitBreakerConfig`.
    """

    timeout_seconds: int = 30
    retries: int = 1
    circuit_breaker: Any = False


def safe_invoke(skill: Any, input_data: SkillInput, context: RunContext) -> SkillOutput:
    """
    Safely invoke a skill with timeout and retry semantics.

    Supports both the new Skill Protocol (invoke) and legacy BaseSkill (run).
    Logs `skill_started`, `skill_succeeded`, and `skill_failed` events to
    `context.logger` when available.
    """
    import concurrent.futures
    import time

    # Determine SLA
    sla_cfg = getattr(skill, "sla", None)
    if sla_cfg is None:
        sla = SLA()
    elif isinstance(sla_cfg, SLA):
        sla = sla_cfg
    else:
        # try to map dict-like objects
        try:
            sla = SLA(**(sla_cfg or {}))
        except Exception:
            sla = SLA()

    logger = getattr(context, "logger", logging.getLogger(__name__))

    attempt = 0
    last_exc: Exception | None = None
    # Prepare circuit breaker if configured. Prefer registry supplied in context.
    breaker = None
    try:
        cb_conf_raw = sla.circuit_breaker
        if cb_conf_raw:
            # If bool True, use defaults. If mapping, construct config.
            if isinstance(cb_conf_raw, bool):
                cb_cfg = CircuitBreakerConfig()
            elif isinstance(cb_conf_raw, dict):
                try:
                    cb_cfg = CircuitBreakerConfig(**cb_conf_raw)
                except Exception:
                    cb_cfg = CircuitBreakerConfig()
            else:
                cb_cfg = CircuitBreakerConfig()

            skill_key = getattr(skill, "name", None) or getattr(skill, "__class__", type(skill)).__name__
            # If caller provided a registry in the context, use it. Otherwise create a local in-memory breaker.
            reg = getattr(context, "circuit_registry", None)
            if reg is not None:
                try:
                    breaker = reg.get_or_create(str(skill_key), cb_cfg)
                except Exception:
                    breaker = CircuitBreaker(str(skill_key), cb_cfg)
            else:
                breaker = CircuitBreaker(str(skill_key), cb_cfg)
    except Exception:
        breaker = None

    def _call():
        # Support Protocol-based invoke(input, context) or legacy run(params)
        if hasattr(skill, "invoke"):
            return skill.invoke(input_data, context)
        # legacy BaseSkill
        if hasattr(skill, "run"):
            # pass plain dict for legacy run
            return skill.run(input_data.payload)
        raise RuntimeError("Skill does not expose invoke() or run()")

    # emit started
    try:
        logger.info("skill_started", extra={"event": "skill_started", "skill": getattr(skill, "name", None)})
    except Exception:
        pass

    while attempt < max(1, sla.retries):
        attempt += 1
        try:
            # check circuit before each attempt
            if breaker is not None:
                try:
                    breaker.before_call()
                except CircuitOpen as co:
                    last_exc = co
                    logger.warning("circuit_open", extra={"event": "circuit_open", "skill": getattr(skill, "name", None)})
                    break

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                fut = ex.submit(_call)
                result = fut.result(timeout=sla.timeout_seconds)

            # on success, record to circuit breaker
            if breaker is not None:
                try:
                    breaker.on_success()
                except Exception:
                    pass

            # emit succeeded
            try:
                logger.info("skill_succeeded", extra={"event": "skill_succeeded", "skill": getattr(skill, "name", None), "attempt": attempt})
            except Exception:
                pass

            return result

        except concurrent.futures.TimeoutError as te:
            last_exc = TimeoutError(f"Skill timed out after {sla.timeout_seconds}s")
            logger.warning("skill_timeout", extra={"event": "skill_timeout", "skill": getattr(skill, "name", None), "attempt": attempt})
            if breaker is not None:
                try:
                    breaker.on_failure()
                except Exception:
                    pass
                break
            # else retry if attempts remain
        except Exception as ex:
            last_exc = ex
            logger.exception("skill_exception", extra={"event": "skill_failed", "skill": getattr(skill, "name", None), "attempt": attempt})
            if breaker is not None:
                try:
                    breaker.on_failure()
                except Exception:
                    pass
                break
            # retry loop continues

    # If we reach here, all attempts failed
    try:
        logger.error("skill_failed", extra={"event": "skill_failed", "skill": getattr(skill, "name", None), "error": str(last_exc)})
    except Exception:
        pass

    # Raise last exception for caller to handle
    if last_exc:
        raise last_exc
    raise RuntimeError("Skill invocation failed without exception")


class SkillValidator:
    """
    Validates skill compliance and enforces Pydantic boundary validation.
    """

    @staticmethod
    def validate_skill(obj: Any) -> None:
        """
        Verify that an object implements the Skill protocol.

        Args:
            obj: Object to validate.

        Raises:
            TypeError: If obj does not implement the Skill protocol.
        """
        if not isinstance(obj, Skill):
            raise TypeError(
                f"Object {obj} does not implement Skill protocol. "
                f"Required: name, version, description, input_schema, output_schema, invoke()"
            )

    @staticmethod
    def validate_input(
        input_data: dict[str, Any], schema: type[BaseModel]
    ) -> BaseModel:
        """
        Validate input payload against Pydantic schema.

        Args:
            input_data: Raw input dictionary.
            schema: Pydantic model class to validate against.

        Returns:
            Validated Pydantic model instance.

        Raises:
            ValidationError: If input does not match schema.
        """
        try:
            return schema.model_validate(input_data)
        except ValidationError as e:
            logger.error(f"Input validation failed: {e}")
            raise

    @staticmethod
    def validate_output(
        output_data: dict[str, Any], schema: type[BaseModel]
    ) -> BaseModel:
        """
        Validate output payload against Pydantic schema.

        Args:
            output_data: Raw output dictionary.
            schema: Pydantic model class to validate against.

        Returns:
            Validated Pydantic model instance.

        Raises:
            ValidationError: If output does not match schema.
        """
        try:
            return schema.model_validate(output_data)
        except ValidationError as e:
            logger.error(f"Output validation failed: {e}")
            raise


class ValidationError(Exception):
    """
    Structured error for validation failures.

    Enables fast-fail at boundaries instead of silent data drift.
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        schema: type[BaseModel] | None = None,
    ):
        self.message = message
        self.field = field
        self.value = value
        self.schema = schema
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with context."""
        parts = [self.message]
        if self.field:
            parts.append(f"field='{self.field}'")
        if self.value is not None:
            parts.append(f"value={repr(self.value)}")
        if self.schema:
            parts.append(f"schema={self.schema.__name__}")
        return " | ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "message": self.message,
            "field": self.field,
            "value": self.value,
            "schema": self.schema.__name__ if self.schema else None,
        }
