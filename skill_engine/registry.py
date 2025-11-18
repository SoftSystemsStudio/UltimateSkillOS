"""
Central Skill Registry – manages skill discovery, versioning, and metadata.

Provides:
- Skill registration with manifests
- Discovery-based loading from modules
- Semantic versioning and stability levels
- Capability tagging and filtering
- Version override support
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Any, Callable, Dict, Literal, Optional

from skill_engine.domain import SkillName, SkillVersion
from skills.skill_manifest import SkillManifest

logger = logging.getLogger(__name__)

# Type aliases
StabilityLevel = Literal["experimental", "beta", "stable"]


class SkillRegistry:
    """
    Central registry for all available skills.

    Manages:
    - Skill instances and their metadata
    - Versioning and stability levels
    - Capability tags for filtering
    - Version overrides for compatibility
    """

    def __init__(self, prefer_stable: bool = True):
        """
        Initialize the registry.

        Args:
            prefer_stable: If True, prefer stable skills in routing.
        """
        self.prefer_stable = prefer_stable
        self._skills: Dict[SkillName, Any] = {}
        """Map of skill_name → skill_instance."""

        self._manifests: Dict[SkillName, SkillManifest] = {}
        """Map of skill_name → SkillManifest."""

        self._stability: Dict[SkillName, StabilityLevel] = {}
        """Stability level for each skill."""

        self._versions: Dict[SkillName, str] = {}
        """Version string for each skill."""

        self._tags: Dict[SkillName, set[str]] = {}
        """Capability tags for each skill."""

        self._version_overrides: Dict[str, str] = {}
        """Override version selection: {skill_name: version}."""

    def register(
        self,
        skill: Any,
        manifest: SkillManifest,
        stability: StabilityLevel = "beta",
        tags: list[str] | None = None,
    ) -> None:
        """
        Register a skill with its manifest.

        Args:
            skill: Skill instance or class.
            manifest: SkillManifest describing the skill.
            stability: Stability level (experimental, beta, stable).
            tags: Capability tags for filtering.

        Raises:
            ValueError: If skill name conflicts with registered skill.
        """
        skill_name = manifest.name

        if skill_name in self._skills:
            # Allow re-registration for updates, but warn
            logger.warning(
                f"Re-registering skill '{skill_name}' "
                f"(was version {self._versions.get(skill_name)})"
            )

        self._skills[skill_name] = skill
        self._manifests[skill_name] = manifest
        self._stability[skill_name] = stability
        self._versions[skill_name] = manifest.version
        self._tags[skill_name] = set(tags or [])

        logger.info(
            f"Registered skill '{skill_name}' v{manifest.version} "
            f"({stability})"
        )

    def get(self, name: SkillName) -> Any:
        """
        Retrieve a skill by name.

        Args:
            name: Skill name.

        Returns:
            Skill instance.

        Raises:
            KeyError: If skill not found.
        """
        if name not in self._skills:
            raise KeyError(f"Skill '{name}' not registered")
        return self._skills[name]

    def get_optional(self, name: SkillName) -> Any | None:
        """
        Retrieve a skill by name, returning None if not found.

        Args:
            name: Skill name.

        Returns:
            Skill instance or None.
        """
        return self._skills.get(name)

    def manifest(self, name: SkillName) -> SkillManifest:
        """
        Retrieve manifest for a skill.

        Args:
            name: Skill name.

        Returns:
            SkillManifest.

        Raises:
            KeyError: If skill not found.
        """
        if name not in self._manifests:
            raise KeyError(f"Manifest for skill '{name}' not found")
        return self._manifests[name]

    def all(self) -> list[SkillManifest]:
        """
        List all registered skill manifests.

        Returns:
            List of SkillManifest objects.
        """
        return list(self._manifests.values())

    def all_names(self) -> list[SkillName]:
        """List all registered skill names."""
        return list(self._skills.keys())

    def stability_of(self, name: SkillName) -> StabilityLevel:
        """Get stability level of a skill."""
        return self._stability.get(name, "beta")

    def version_of(self, name: SkillName) -> str:
        """Get version of a registered skill."""
        return self._versions.get(name, "0.0.0")

    def is_stable(self, name: SkillName) -> bool:
        """Check if a skill is marked stable."""
        return self.stability_of(name) == "stable"

    def is_experimental(self, name: SkillName) -> bool:
        """Check if a skill is marked experimental."""
        return self.stability_of(name) == "experimental"

    def add_tags(self, name: SkillName, tags: list[str]) -> None:
        """Add capability tags to a skill."""
        if name not in self._tags:
            self._tags[name] = set()
        self._tags[name].update(tags)

    def has_tag(self, name: SkillName, tag: str) -> bool:
        """Check if a skill has a specific tag."""
        return tag in self._tags.get(name, set())

    def tags_of(self, name: SkillName) -> set[str]:
        """Get all tags for a skill."""
        return self._tags.get(name, set())

    def filter_by_tag(self, tag: str) -> list[SkillName]:
        """
        Find all skills with a specific tag.

        Args:
            tag: Capability tag.

        Returns:
            List of skill names.
        """
        return [name for name, tags in self._tags.items() if tag in tags]

    def filter_by_stability(self, stability: StabilityLevel) -> list[SkillName]:
        """
        Find all skills with a specific stability level.

        Args:
            stability: Stability level.

        Returns:
            List of skill names.
        """
        return [name for name, stab in self._stability.items() if stab == stability]

    def filter_by_tags(self, tags: list[str], match_all: bool = False) -> list[SkillName]:
        """
        Find skills matching tag criteria.

        Args:
            tags: List of tags to filter by.
            match_all: If True, skill must have ALL tags. If False, any tag.

        Returns:
            List of skill names.
        """
        results = []
        for name, skill_tags in self._tags.items():
            if match_all:
                if all(tag in skill_tags for tag in tags):
                    results.append(name)
            else:
                if any(tag in skill_tags for tag in tags):
                    results.append(name)
        return results

    def set_version_override(self, skill_name: SkillName, version: str) -> None:
        """
        Override version selection for a skill.

        Args:
            skill_name: Skill name.
            version: Version to select.
        """
        self._version_overrides[skill_name] = version
        logger.info(f"Version override for '{skill_name}' set to {version}")

    def get_version_override(self, skill_name: SkillName) -> str | None:
        """Get version override for a skill."""
        return self._version_overrides.get(skill_name)

    def clear_version_overrides(self) -> None:
        """Clear all version overrides."""
        self._version_overrides.clear()

    def to_dict(self) -> dict[str, Any]:
        """Export registry state as dictionary."""
        return {
            "skills": list(self._skills.keys()),
            "manifests": {name: m.to_dict() for name, m in self._manifests.items()},
            "stability": dict(self._stability),
            "versions": dict(self._versions),
            "tags": {name: list(tags) for name, tags in self._tags.items()},
        }


# Global singleton instance
_global_registry: Optional[SkillRegistry] = None


def get_global_registry() -> SkillRegistry:
    """Get or create the global skill registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = SkillRegistry()
    return _global_registry


def set_global_registry(registry: SkillRegistry) -> None:
    """Set the global skill registry."""
    global _global_registry
    _global_registry = registry
