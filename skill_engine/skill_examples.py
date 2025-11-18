"""
Reference implementation of the Skill Protocol with Pydantic validation.

This demonstrates how to properly implement a skill with:
- Pydantic input/output schemas
- Proper invoke() signature
- Full validation at boundaries
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from skill_engine.domain import SkillInput, SkillName, SkillOutput
from skill_engine.skill_base import RunContext, Skill


# ============================================================================
# Example: Simple Echo Skill
# ============================================================================


class EchoInputSchema(BaseModel):
    """Validated input for the echo skill."""

    text: str = Field(..., description="Text to echo back")
    uppercase: bool = Field(
        default=False, description="Convert to uppercase if true"
    )


class EchoOutputSchema(BaseModel):
    """Validated output for the echo skill."""

    result: str = Field(..., description="The echoed text")
    original_length: int = Field(..., description="Length of original text")


class EchoSkill:
    """
    Simple echo skill that demonstrates proper Skill implementation.

    Implements the Skill Protocol:
    - name, version, description attributes
    - input_schema and output_schema as Pydantic models
    - invoke() method with proper signature
    """

    name: SkillName = "echo"
    version: str = "1.0.0"
    description: str = "Simple echo skill for demonstration"
    input_schema: type[BaseModel] = EchoInputSchema
    output_schema: type[BaseModel] = EchoOutputSchema

    def invoke(self, input_data: SkillInput, context: RunContext) -> SkillOutput:
        """
        Execute the echo skill with full validation.

        Args:
            input_data: Validated SkillInput with payload to process.
            context: RunContext with trace_id, memory, etc.

        Returns:
            SkillOutput with validated payload.

        Raises:
            pydantic.ValidationError: If input or output fails schema validation.
        """
        from skill_engine.skill_base import SkillValidator

        # Validate input against schema
        try:
            validated_input = SkillValidator.validate_input(
                input_data.payload, self.input_schema
            )
        except Exception as e:
            return SkillOutput(
                payload={"error": f"Input validation failed: {str(e)}"},
                warnings=[str(e)],
            )

        # Process
        text = validated_input.text
        result_text = text.upper() if validated_input.uppercase else text

        output_payload = {
            "result": result_text,
            "original_length": len(text),
        }

        # Validate output against schema
        try:
            validated_output = SkillValidator.validate_output(
                output_payload, self.output_schema
            )
        except Exception as e:
            return SkillOutput(
                payload={"error": f"Output validation failed: {str(e)}"},
                warnings=[str(e)],
            )

        # Return validated output
        return SkillOutput(
            payload=validated_output.model_dump(),
            warnings=[],
            metrics={"execution_ms": 0.1},
        )


# ============================================================================
# Example: Research Skill (more complex)
# ============================================================================


class ResearchInputSchema(BaseModel):
    """Validated input for research skill."""

    query: str = Field(..., description="Research query")
    max_results: int = Field(default=5, ge=1, le=50, description="Max results")
    search_type: str = Field(
        default="web", pattern="^(web|academic|news)$", description="Type of search"
    )


class ResearchOutputSchema(BaseModel):
    """Validated output for research skill."""

    summary: str = Field(..., description="Summary of findings")
    num_results: int = Field(..., description="Number of results found")
    sources: list[str] = Field(default_factory=list, description="Source URLs")


class ResearchSkill:
    """Research skill implementation."""

    name: SkillName = "research"
    version: str = "1.1.0"
    description: str = "Search and research skill"
    input_schema: type[BaseModel] = ResearchInputSchema
    output_schema: type[BaseModel] = ResearchOutputSchema

    def invoke(self, input_data: SkillInput, context: RunContext) -> SkillOutput:
        """Execute research with validation at all boundaries."""
        from skill_engine.skill_base import SkillValidator

        # Validate input
        try:
            validated_input = SkillValidator.validate_input(
                input_data.payload, self.input_schema
            )
        except Exception as e:
            return SkillOutput(
                payload={"error": f"Input validation failed: {str(e)}"},
                warnings=[str(e)],
            )

        # Simulate research
        output_payload = {
            "summary": f"Results for '{validated_input.query}'",
            "num_results": 3,
            "sources": [
                "https://example.com/1",
                "https://example.com/2",
                "https://example.com/3",
            ],
        }

        # Validate output
        try:
            validated_output = SkillValidator.validate_output(
                output_payload, self.output_schema
            )
        except Exception as e:
            return SkillOutput(
                payload={"error": f"Output validation failed: {str(e)}"},
                warnings=[str(e)],
            )

        return SkillOutput(
            payload=validated_output.model_dump(),
            warnings=[],
            metrics={
                "query_length": len(validated_input.query),
                "results_found": output_payload["num_results"],
            },
        )
