"""
Formal Skill interface using Protocol for structural typing.

Enforces:
- Pydantic validation at all boundaries
- Structured error handling
- Clear skill contracts (input/output schemas)
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, ValidationError

from skill_engine.domain import SkillInput, SkillName, SkillOutput, SkillVersion

logger = logging.getLogger(__name__)


class RunContext:
    """
    Execution context passed to skill invocations.
    
    Provides:
    - Trace and correlation IDs for observability
    - Memory context from prior steps
    - Configuration and runtime parameters
    """

    def __init__(
        self,
        trace_id: str,
        correlation_id: str | None = None,
        memory_context: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.trace_id = trace_id
        self.correlation_id = correlation_id
        self.memory_context = memory_context or []
        self.metadata = metadata or {}

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
