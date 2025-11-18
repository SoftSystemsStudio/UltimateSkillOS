"""
Skill Discovery – auto-discovers and registers skills from modules.

Supports:
- Module-based auto-discovery (skills.*)
- Entrypoint-based discovery (for pip packages)
- Registration hook for extensibility
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Any, Callable, Optional

import skills

from skill_engine.registry import SkillRegistry, StabilityLevel
from skills.skill_manifest import SKILL_MANIFESTS, get_manifest

logger = logging.getLogger(__name__)


class SkillDiscovery:
    """
    Discovers and auto-registers skills from various sources.

    Sources:
    - Module-based: loads all classes from skills.* modules
    - Manifest-based: uses SkillManifest registry
    - Entrypoint-based: future support for pip packages
    """

    @staticmethod
    def discover_from_modules(
        registry: SkillRegistry,
        package=skills,
        base_class: type | None = None,
    ) -> int:
        """
        Discover skills by importing all modules and looking for registrable classes.

        Args:
            registry: SkillRegistry to register skills into.
            package: Package to scan (default: skills).
            base_class: Base class to look for (e.g., BaseSkill or Skill protocol).

        Returns:
            Number of skills discovered.
        """
        count = 0
        discovered_skills = {}

        # Import all modules in the package
        for module_info in pkgutil.iter_modules(package.__path__):
            module_name = f"{package.__name__}.{module_info.name}"
            try:
                module = importlib.import_module(module_name)
                logger.debug(f"Imported module: {module_name}")
            except Exception as e:
                logger.warning(f"Failed to import {module_name}: {e}")
                continue

            # Look for skill classes or instances in the module
            for attr_name in dir(module):
                if attr_name.startswith("_"):
                    continue

                attr = getattr(module, attr_name)

                # Check if it's a skill (by checking for required attributes)
                if SkillDiscovery._is_skill_like(attr, base_class):
                    skill_name = None

                    # Extract skill name
                    if hasattr(attr, "name"):
                        skill_name = attr.name
                    elif isinstance(attr, type) and hasattr(attr, "name"):
                        # Class with name attribute
                        try:
                            instance = attr()
                            skill_name = instance.name
                            attr = instance
                        except Exception as e:
                            logger.warning(
                                f"Failed to instantiate {module_name}.{attr_name}: {e}"
                            )
                            continue

                    if skill_name and skill_name not in discovered_skills:
                        discovered_skills[skill_name] = (attr, module_name, attr_name)
                        count += 1

        # Register discovered skills
        for skill_name, (skill_obj, module_name, attr_name) in discovered_skills.items():
            try:
                manifest = get_manifest(skill_name)
                if manifest:
                    # Register with manifest from SkillManifest registry
                    registry.register(skill_obj, manifest, stability="stable")
                else:
                    # Create a minimal manifest from skill attributes
                    manifest = SkillDiscovery._create_default_manifest(skill_obj)
                    registry.register(skill_obj, manifest, stability="beta")
                    logger.info(
                        f"Registered skill '{skill_name}' from {module_name}.{attr_name}"
                    )
            except Exception as e:
                logger.error(
                    f"Failed to register skill '{skill_name}' from {module_name}: {e}"
                )

        logger.info(f"Discovered and registered {count} skills")
        return count

    @staticmethod
    def _is_skill_like(obj: Any, base_class: type | None = None) -> bool:
        """
        Check if an object looks like a skill.

        Args:
            obj: Object to check.
            base_class: Optional base class to check against.

        Returns:
            True if object appears to be a skill.
        """
        # Check for base class inheritance
        if base_class and isinstance(obj, type) and issubclass(obj, base_class):
            return True

        # Check for required skill attributes
        required_attrs = ["name", "run"]
        has_required = all(hasattr(obj, attr) for attr in required_attrs)

        return has_required

    @staticmethod
    def _create_default_manifest(skill_obj: Any) -> Any:
        """
        Create a minimal SkillManifest from a skill object.

        Args:
            skill_obj: Skill instance or class.

        Returns:
            SkillManifest-like object.
        """
        from skills.skill_manifest import SkillManifest

        name = getattr(skill_obj, "name", "unknown")
        version = getattr(skill_obj, "version", "1.0.0")
        description = getattr(skill_obj, "description", f"Skill: {name}")
        keywords = getattr(skill_obj, "keywords", [])

        return SkillManifest(
            name=name,
            version=version,
            description=description,
            tags=keywords or [],
            examples=[],
        )

    @staticmethod
    def discover_from_manifests(
        registry: SkillRegistry,
        manifest_registry: dict | None = None,
    ) -> int:
        """
        Register skills based on the SkillManifest registry.

        This creates stub entries for skills defined in manifests,
        allowing planning and routing even if implementation isn't loaded.

        Args:
            registry: SkillRegistry to register into.
            manifest_registry: Manifest registry (default: SKILL_MANIFESTS).

        Returns:
            Number of manifests registered.
        """
        manifest_registry = manifest_registry or SKILL_MANIFESTS
        count = 0

        for skill_name, manifest in manifest_registry.items():
            # Create a stub skill object
            stub_skill = type(
                "StubSkill",
                (),
                {
                    "name": manifest.name,
                    "version": manifest.version,
                    "description": manifest.description,
                    "run": lambda *a, **kw: {
                        "error": f"Skill '{manifest.name}' not yet implemented"
                    },
                },
            )()

            registry.register(stub_skill, manifest, stability="stable")
            count += 1

        logger.info(f"Registered {count} manifests as skills")
        return count

    @staticmethod
    def discover_from_entrypoints(
        registry: SkillRegistry,
        group: str = "skillengine.skills",
    ) -> int:
        """
        Discover skills from setuptools entrypoints (for pip packages).

        Args:
            registry: SkillRegistry to register into.
            group: Entrypoint group name.

        Returns:
            Number of skills discovered.

        Note:
            Requires python 3.10+ (or importlib_metadata backport).
        """
        try:
            from importlib.metadata import entry_points
        except ImportError:
            logger.warning("importlib.metadata not available, skipping entrypoint discovery")
            return 0

        count = 0
        try:
            eps = entry_points(group=group)
            for ep in eps:
                try:
                    skill_class = ep.load()
                    skill_obj = skill_class() if isinstance(skill_class, type) else skill_class

                    manifest = get_manifest(skill_obj.name)
                    if not manifest:
                        manifest = SkillDiscovery._create_default_manifest(skill_obj)

                    registry.register(skill_obj, manifest, stability="beta")
                    count += 1
                    logger.info(f"Loaded skill from entrypoint: {ep.name}")
                except Exception as e:
                    logger.error(f"Failed to load entrypoint skill {ep.name}: {e}")

            logger.info(f"Discovered {count} skills from entrypoints")
        except Exception as e:
            logger.warning(f"Entrypoint discovery failed: {e}")

        return count
