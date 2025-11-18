"""
Skill manifest registry for dynamic skill discovery and routing.

Each skill registers its metadata to enable:
- Semantic skill discovery via embeddings
- Intent classification mapping
- Execution planning
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillManifest:
    """
    Metadata describing a skill and its capabilities.
    
    Used by routing, planning, and discovery systems.
    """

    name: str
    """Unique skill identifier."""

    version: str
    """Semantic version (MAJOR.MINOR.PATCH)."""

    description: str
    """Detailed description of what the skill does."""

    examples: list[str] = field(default_factory=list)
    """Example inputs or use cases."""

    tags: list[str] = field(default_factory=list)
    """Semantic tags for categorization (e.g., 'search', 'memory', 'planning')."""

    input_required: list[str] = field(default_factory=list)
    """Required input parameters."""

    input_optional: list[str] = field(default_factory=list)
    """Optional input parameters."""

    output_fields: list[str] = field(default_factory=list)
    """Fields available in output."""

    cost: float = field(default=1.0)
    """Relative execution cost for prioritization."""

    mutually_exclusive_with: list[str] = field(default_factory=list)
    """Skill names that should not be chained after this one."""

    requires_context: list[str] = field(default_factory=list)
    """Required context (e.g., 'memory', 'file_system')."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional arbitrary metadata."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "examples": self.examples,
            "tags": self.tags,
            "input_required": self.input_required,
            "input_optional": self.input_optional,
            "output_fields": self.output_fields,
            "cost": self.cost,
            "mutually_exclusive_with": self.mutually_exclusive_with,
            "requires_context": self.requires_context,
            "metadata": self.metadata,
        }


# ============================================================================
# Skill Registry: Manifests for all available skills
# ============================================================================

SKILL_MANIFESTS = {
    "summarize": SkillManifest(
        name="summarize",
        version="1.0.0",
        description="Summarizes text into a short extractive summary using sentence extraction.",
        examples=[
            "Summarize this article",
            "Give me the key points",
            "What's the tl;dr?",
        ],
        tags=["text_processing", "summarization", "extraction"],
        input_required=["text"],
        input_optional=["max_length", "style"],
        output_fields=["summary", "length", "confidence"],
        cost=0.8,
        metadata={"model": "extractive", "supports_memory": True},
    ),
    "memory_search": SkillManifest(
        name="memory_search",
        version="1.0.0",
        description="Searches persistent memory for relevant entries based on semantic or keyword search.",
        examples=[
            "What do you remember about...",
            "Did I tell you about...",
            "Recall when I said...",
        ],
        tags=["memory", "retrieval", "search"],
        input_required=["query"],
        input_optional=["limit", "filter_type"],
        output_fields=["matches", "total_count", "query_time_ms"],
        cost=0.6,
        metadata={"supports_memory": False},
    ),
    "research": SkillManifest(
        name="research",
        version="1.1.0",
        description="Performs web research and information retrieval using semantic search and knowledge bases.",
        examples=[
            "Research recent advances in AI",
            "Find information about...",
            "What's new with...",
        ],
        tags=["research", "web_search", "knowledge"],
        input_required=["query"],
        input_optional=["search_type", "max_results", "source_filter"],
        output_fields=["results", "summary", "sources", "num_results"],
        cost=2.5,
        requires_context=["internet"],
        metadata={"external_api": True},
    ),
    "file": SkillManifest(
        name="file",
        version="1.0.0",
        description="Reads, writes, and manages files on the filesystem.",
        examples=[
            "Read the file at /path/to/file.txt",
            "Write data to a file",
            "List files in a directory",
        ],
        tags=["file_operations", "io", "filesystem"],
        input_required=["command"],
        input_optional=["path", "content", "mode"],
        output_fields=["result", "content", "status"],
        cost=0.7,
        requires_context=["file_system"],
        metadata={"side_effects": True},
    ),
    "planner": SkillManifest(
        name="planner",
        version="1.0.0",
        description="Decomposes complex goals into executable step-by-step plans.",
        examples=[
            "Create a plan to accomplish...",
            "Break this down into steps",
            "What's the roadmap for...",
        ],
        tags=["planning", "decomposition", "strategy"],
        input_required=["goal"],
        input_optional=["constraints", "max_steps"],
        output_fields=["plan", "steps", "rationale"],
        cost=1.2,
        metadata={"returns_structured_plan": True},
    ),
    "reflection": SkillManifest(
        name="reflection",
        version="1.0.0",
        description="Analyzes outcomes and generates insights for improvement.",
        examples=[
            "Reflect on what just happened",
            "What went wrong?",
            "How could we improve?",
        ],
        tags=["reflection", "analysis", "improvement"],
        input_required=["context"],
        input_optional=["focus_area"],
        output_fields=["insights", "improvements", "next_steps"],
        cost=1.5,
        metadata={"requires_prior_context": True},
    ),
    "meta_interpreter": SkillManifest(
        name="meta_interpreter",
        version="1.0.0",
        description="Interprets and executes meta-level instructions for self-modification.",
        examples=[
            "Interpret and execute this program",
            "Run this logic",
            "Execute this instruction",
        ],
        tags=["meta", "interpretation", "execution"],
        input_required=["instruction"],
        input_optional=["context", "parameters"],
        output_fields=["result", "trace", "modifications"],
        cost=2.0,
        metadata={"advanced": True, "potentially_unsafe": True},
    ),
    "autofix": SkillManifest(
        name="autofix",
        version="1.0.0",
        description="Automatically detects and fixes common issues in code or data.",
        examples=[
            "Fix this code",
            "Correct the errors",
            "Auto-repair this",
        ],
        tags=["debugging", "repair", "fixing"],
        input_required=["content"],
        input_optional=["language", "fix_type"],
        output_fields=["fixed_content", "changes", "issues_found"],
        cost=1.8,
        metadata={"side_effects": True},
    ),
}


def get_manifest(skill_name: str) -> SkillManifest | None:
    """Retrieve manifest for a skill by name."""
    return SKILL_MANIFESTS.get(skill_name)


def list_manifests() -> list[SkillManifest]:
    """List all registered skill manifests."""
    return list(SKILL_MANIFESTS.values())


def get_manifests_by_tag(tag: str) -> list[SkillManifest]:
    """Find all skills with a specific tag."""
    return [m for m in SKILL_MANIFESTS.values() if tag in m.tags]
