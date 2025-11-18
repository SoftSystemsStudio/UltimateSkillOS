#!/usr/bin/env python3
"""
Example: Using the new configuration system.

This script demonstrates how to use the layered configuration system
with different approaches: environment variables, config files, and explicit.
"""

import logging
from config import AgentConfig, AppConfig, RoutingConfig, load_config
from skill_engine.agent import Agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_1_simple_from_env():
    """Simplest approach: use environment variables."""
    logger.info("\n=== Example 1: Simple with Environment Variables ===")
    logger.info("Usage: SKILLOS_AGENT_MAX_STEPS=10 python this_script.py")

    agent = Agent.from_env()
    logger.info(f"Config: {agent.config.to_dict()}")
    # Now you can use agent.run(task)


def example_2_from_config_file():
    """Load from custom config file."""
    logger.info("\n=== Example 2: Load from Custom Config File ===")

    agent = Agent.from_env(config_path="config/production.toml")
    logger.info(f"Loaded config from production.toml")
    logger.info(f"Routing mode: {agent.config.routing.mode}")
    logger.info(f"Max steps: {agent.config.max_steps}")


def example_3_explicit_config():
    """Explicit configuration (full control)."""
    logger.info("\n=== Example 3: Explicit Configuration ===")

    routing = RoutingConfig(
        mode="hybrid",
        use_embeddings=True,
        embedding_threshold=0.5,
    )

    config = AgentConfig(
        max_steps=10,
        timeout_seconds=600,
        verbose=True,
        routing=routing,
    )

    agent = Agent(config=config)
    logger.info(f"Created agent with explicit config")
    logger.info(f"Config: {agent.config.to_dict()}")


def example_4_load_and_inspect():
    """Load config and inspect all settings."""
    logger.info("\n=== Example 4: Load and Inspect Configuration ===")

    config = load_config()
    logger.info(f"Full configuration:")
    import json

    print(json.dumps(config.to_dict(), indent=2))


def example_5_override_precedence():
    """Demonstrate configuration precedence."""
    logger.info("\n=== Example 5: Configuration Precedence ===")

    logger.info("Precedence (lowest to highest):")
    logger.info("1. Built-in defaults")
    logger.info("2. ultimateskillos.toml (if exists)")
    logger.info("3. Custom config file (if provided)")
    logger.info("4. Environment variables (SKILLOS_*)")

    logger.info("\nTo override max_steps:")
    logger.info('  In ultimateskillos.toml: max_steps = 8')
    logger.info('  In environment: export SKILLOS_AGENT_MAX_STEPS=8')

    config = load_config()
    logger.info(f"\nCurrent max_steps: {config.agent.max_steps}")


def example_6_memory_config():
    """Configure memory system."""
    logger.info("\n=== Example 6: Configure Memory System ===")

    config = load_config()

    logger.info(f"Memory Settings:")
    logger.info(f"  Model: {config.memory.model_name}")
    logger.info(f"  Embedding dimension: {config.memory.embedding_dim}")
    logger.info(f"  Top-K results: {config.memory.top_k}")
    logger.info(f"  FAISS enabled: {config.memory.enable_faiss}")
    logger.info(f"  LongTerm DB: {config.memory.long_term_db_path}")

    logger.info("\nTo override in environment:")
    logger.info('  export SKILLOS_MEMORY_TOP_K=5')
    logger.info('  export SKILLOS_MEMORY_ENABLE_FAISS=false')


def example_7_routing_config():
    """Configure routing behavior."""
    logger.info("\n=== Example 7: Configure Routing ===")

    config = load_config()

    logger.info(f"Routing Settings:")
    logger.info(f"  Mode: {config.agent.routing.mode}")
    logger.info(f"  Use embeddings: {config.agent.routing.use_embeddings}")
    logger.info(f"  Use LLM intent: {config.agent.routing.use_llm_for_intent}")
    logger.info(f"  Embedding threshold: {config.agent.routing.embedding_threshold}")

    logger.info("\nTo switch to keyword-only mode:")
    logger.info('  export SKILLOS_AGENT_ROUTING_MODE=keyword')


def example_8_custom_prefix():
    """Use custom environment variable prefix."""
    logger.info("\n=== Example 8: Custom Environment Prefix ===")

    logger.info('Usage: MYAPP_AGENT_MAX_STEPS=20 python this_script.py')

    agent = Agent.from_env(env_prefix="MYAPP_")
    logger.info(f"Using custom MYAPP_ prefix instead of SKILLOS_")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        example_num = int(sys.argv[1])
        examples = [
            example_1_simple_from_env,
            example_2_from_config_file,
            example_3_explicit_config,
            example_4_load_and_inspect,
            example_5_override_precedence,
            example_6_memory_config,
            example_7_routing_config,
            example_8_custom_prefix,
        ]

        if 1 <= example_num <= len(examples):
            examples[example_num - 1]()
        else:
            logger.error(f"Example {example_num} not found (1-{len(examples)})")
    else:
        logger.info("Configuration System Examples")
        logger.info("==============================\n")
        logger.info("Run individual examples:")
        logger.info("  python examples/config_examples.py 1  # Simple from env")
        logger.info("  python examples/config_examples.py 2  # From config file")
        logger.info("  python examples/config_examples.py 3  # Explicit config")
        logger.info("  python examples/config_examples.py 4  # Load and inspect")
        logger.info("  python examples/config_examples.py 5  # Override precedence")
        logger.info("  python examples/config_examples.py 6  # Memory config")
        logger.info("  python examples/config_examples.py 7  # Routing config")
        logger.info("  python examples/config_examples.py 8  # Custom prefix")

        # Run all examples
        logger.info("\nRunning all examples...\n")
        example_1_simple_from_env()
        example_3_explicit_config()
        example_4_load_and_inspect()
        example_5_override_precedence()
        example_6_memory_config()
        example_7_routing_config()
