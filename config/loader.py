"""
Configuration file loading and environment variable merging.

Supports:
- TOML files (pyproject.toml, ultimateskillos.toml)
- YAML files (config.yml)
- Environment variable overrides
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


def load_from_file(
    file_path: str | Path, base_config: Any = None
) -> Any:
    """
    Load configuration from TOML or YAML file.

    Args:
        file_path: Path to config file (.toml, .yaml, .yml).
        base_config: Base configuration to merge into (if None, starts from empty dict).

    Returns:
        Merged configuration (as dict or updated config object).
    """
    from config import AppConfig

    file_path = Path(file_path)

    # File doesn't exist - return base config unchanged
    if not file_path.exists():
        logger.debug(f"Config file not found: {file_path}")
        return base_config or AppConfig.default()

    try:
        if file_path.suffix.lower() in [".toml"]:
            return _load_toml(file_path, base_config)
        elif file_path.suffix.lower() in [".yaml", ".yml"]:
            return _load_yaml(file_path, base_config)
        else:
            logger.warning(f"Unsupported config file format: {file_path.suffix}")
            return base_config or AppConfig.default()
    except Exception as e:
        logger.error(f"Failed to load config from {file_path}: {e}")
        return base_config or AppConfig.default()


def _load_toml(file_path: Path, base_config: Any = None) -> Any:
    """Load configuration from TOML file."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # Fallback for older Python
        except ImportError:
            logger.warning(
                "TOML support requires 'tomli' package. Install with: pip install tomli"
            )
            return base_config

    from config import AppConfig

    base_config = base_config or AppConfig.default()

    try:
        with open(file_path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        logger.error(f"Failed to parse TOML file {file_path}: {e}")
        return base_config

    # Extract [tool.skillos] section if loading from pyproject.toml
    if file_path.name == "pyproject.toml":
        data = data.get("tool", {}).get("skillos", {})

    return _merge_dict_into_config(data, base_config)


def _load_yaml(file_path: Path, base_config: Any = None) -> Any:
    """Load configuration from YAML file."""
    try:
        import yaml
    except ImportError:
        logger.warning("YAML support requires 'pyyaml' package. Install with: pip install pyyaml")
        return base_config

    from config import AppConfig

    base_config = base_config or AppConfig.default()

    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Failed to parse YAML file {file_path}: {e}")
        return base_config

    return _merge_dict_into_config(data, base_config)


def _merge_dict_into_config(data: Dict[str, Any], config: Any) -> Any:
    """
    Merge dictionary data into config object.

    Handles nested dictionaries for memory, agent, routing, logging sections.
    """
    if not data:
        return config

    # Handle memory config
    if "memory" in data:
        for key, value in data["memory"].items():
            if hasattr(config.memory, key):
                setattr(config.memory, key, value)

    # Handle agent config
    if "agent" in data:
        agent_data = data["agent"]
        for key, value in agent_data.items():
            if key == "routing" and isinstance(value, dict):
                # Handle nested routing config
                for rkey, rvalue in value.items():
                    if hasattr(config.agent.routing, rkey):
                        setattr(config.agent.routing, rkey, rvalue)
            elif hasattr(config.agent, key):
                setattr(config.agent, key, value)

    # Handle logging config
    if "logging" in data:
        for key, value in data["logging"].items():
            if hasattr(config.logging, key):
                setattr(config.logging, key, value)

    return config


def merge_from_env(config: Any, env_prefix: str = "SKILLOS_") -> Any:
    """
    Override config with environment variables.

    Environment variable format:
    - SKILLOS_AGENT_MAX_STEPS=10
    - SKILLOS_MEMORY_TOP_K=5
    - SKILLOS_AGENT_ROUTING_MODE=hybrid
    - SKILLOS_LOGGING_LEVEL=DEBUG

    Args:
        config: Configuration object to update.
        env_prefix: Prefix for environment variables (default: SKILLOS_).

    Returns:
        Updated configuration object.
    """
    for env_var, value in os.environ.items():
        if not env_var.startswith(env_prefix):
            continue

        # Parse environment variable name
        parts = env_var[len(env_prefix) :].lower().split("_")

        if len(parts) < 2:
            continue

        section = parts[0]
        key_parts = parts[1:]

        try:
            if section == "agent" and len(key_parts) >= 1:
                if key_parts[0] == "routing" and len(key_parts) >= 2:
                    # Handle SKILLOS_AGENT_ROUTING_*
                    routing_key = "_".join(key_parts[1:])
                    routing_key = _coerce_value(routing_key, value, config.agent.routing)
                    setattr(config.agent.routing, routing_key, _parse_value(value))
                else:
                    # Handle SKILLOS_AGENT_*
                    agent_key = "_".join(key_parts)
                    if hasattr(config.agent, agent_key):
                        setattr(config.agent, agent_key, _parse_value(value))

            elif section == "memory" and len(key_parts) >= 1:
                memory_key = "_".join(key_parts)
                if hasattr(config.memory, memory_key):
                    setattr(config.memory, memory_key, _parse_value(value))

            elif section == "logging" and len(key_parts) >= 1:
                logging_key = "_".join(key_parts)
                if hasattr(config.logging, logging_key):
                    setattr(config.logging, logging_key, _parse_value(value))

        except Exception as e:
            logger.warning(f"Failed to set {env_var}: {e}")

    return config


def _coerce_value(key: str, value: str, config_obj: Any) -> str:
    """Coerce snake_case key to match config object attribute name."""
    # Try exact match first
    if hasattr(config_obj, key):
        return key

    # Try with underscores already in place
    for attr in dir(config_obj):
        if attr.lower() == key.lower() and not attr.startswith("_"):
            return attr

    return key


def _parse_value(value: str) -> Any:
    """
    Parse environment variable value to appropriate type.

    Handles: bool, int, float, str
    """
    value_lower = value.lower()

    if value_lower in ("true", "yes", "1"):
        return True
    if value_lower in ("false", "no", "0"):
        return False

    # Try int
    try:
        return int(value)
    except ValueError:
        pass

    # Try float
    try:
        return float(value)
    except ValueError:
        pass

    # Return as string
    return value
