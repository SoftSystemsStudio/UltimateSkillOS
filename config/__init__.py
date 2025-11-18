"""
Configuration module for UltimateSkillOS.

Provides layered configuration management:
- Defaults from dataclasses
- Environment variables for secrets/overrides
- TOML/YAML file overrides
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Literal

__all__ = [
    "LoggingConfig",
    "MemoryConfig",
    "AgentConfig",
    "RoutingConfig",
    "AppConfig",
    "load_config",
]


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str | None = None  # Optional log file path


@dataclass
class MemoryConfig:
    """Memory system configuration."""

    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    top_k: int = 3
    short_term_capacity: int = 100
    long_term_db_path: str = ".cache/ultimate_skillos/memory.db"
    faiss_index_path: str = ".cache/ultimate_skillos/memory_index.faiss"
    enable_faiss: bool = True  # Fall back to in-memory if FAISS unavailable


@dataclass
class RoutingConfig:
    """Routing configuration."""

    mode: Literal["keyword", "hybrid", "llm_only"] = "hybrid"
    use_embeddings: bool = True
    use_llm_for_intent: bool = False  # Set to True for LLM-based intent classification
    keyword_fallback: bool = True
    embedding_threshold: float = 0.5


@dataclass
class AgentConfig:
    """Agent execution configuration."""

    max_steps: int = 6
    timeout_seconds: int = 300
    verbose: bool = False
    enable_memory: bool = True
    routing: RoutingConfig = field(default_factory=RoutingConfig)


@dataclass
class AppConfig:
    """Complete application configuration."""

    memory: MemoryConfig = field(default_factory=MemoryConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "memory": {
                "model_name": self.memory.model_name,
                "embedding_dim": self.memory.embedding_dim,
                "top_k": self.memory.top_k,
                "short_term_capacity": self.memory.short_term_capacity,
                "long_term_db_path": self.memory.long_term_db_path,
                "faiss_index_path": self.memory.faiss_index_path,
                "enable_faiss": self.memory.enable_faiss,
            },
            "agent": {
                "max_steps": self.agent.max_steps,
                "timeout_seconds": self.agent.timeout_seconds,
                "verbose": self.agent.verbose,
                "enable_memory": self.agent.enable_memory,
                "routing": {
                    "mode": self.agent.routing.mode,
                    "use_embeddings": self.agent.routing.use_embeddings,
                    "use_llm_for_intent": self.agent.routing.use_llm_for_intent,
                    "keyword_fallback": self.agent.routing.keyword_fallback,
                    "embedding_threshold": self.agent.routing.embedding_threshold,
                },
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "file": self.logging.file,
            },
        }

    @staticmethod
    def default() -> AppConfig:
        """Create default configuration."""
        return AppConfig()


# Lazy import to avoid circular dependencies
def load_config(
    config_path: str | None = None,
    env_prefix: str = "SKILLOS_",
) -> AppConfig:
    """
    Load configuration from layered sources.

    Args:
        config_path: Optional path to config file (TOML/YAML).
        env_prefix: Prefix for environment variables (e.g., SKILLOS_AGENT_MAX_STEPS).

    Returns:
        Merged AppConfig from all sources.

    Priority (highest to lowest):
    1. Environment variables
    2. config_path file (if provided)
    3. ultimateskillos.toml in current directory
    4. Defaults from AppConfig dataclass
    """
    from config.loader import load_from_file, merge_from_env

    # Start with defaults
    config = AppConfig.default()

    # Load from ultimateskillos.toml if it exists
    config = load_from_file("ultimateskillos.toml", config)

    # Load from provided config path
    if config_path:
        config = load_from_file(config_path, config)

    # Override with environment variables (highest priority)
    config = merge_from_env(config, env_prefix)

    return config
