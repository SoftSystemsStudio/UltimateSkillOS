"""
Configuration System Documentation for UltimateSkillOS

This document explains how to configure UltimateSkillOS using the layered
configuration system.
"""

# Configuration System Overview

UltimateSkillOS uses a **layered configuration** approach with clear precedence:

1. **Defaults** (built-in dataclass defaults)
2. **ultimateskillos.toml** (project-level config in repo root)
3. **Environment Variables** (highest priority, e.g., `SKILLOS_AGENT_MAX_STEPS=10`)

## Quick Start

### Option 1: Use Environment Variables (Simplest)

```python
from skill_engine.agent import Agent

# Creates Agent with defaults, overridable via environment variables
agent = Agent.from_env()

# Execute a task
result = agent.run("Summarize the latest research on AI safety")
```

Override specific settings:

```bash
export SKILLOS_AGENT_MAX_STEPS=10
export SKILLOS_MEMORY_TOP_K=5
export SKILLOS_AGENT_ROUTING_MODE=hybrid

python my_script.py
```

### Option 2: Use ultimateskillos.toml (Recommended for Projects)

Create `ultimateskillos.toml` in your project root:

```toml
[memory]
model_name = "sentence-transformers/all-MiniLM-L6-v2"
embedding_dim = 384
top_k = 3

[agent]
max_steps = 6
timeout_seconds = 300
verbose = true

[agent.routing]
mode = "hybrid"
use_embeddings = true
```

Then use:

```python
from skill_engine.agent import Agent

agent = Agent.from_env()  # Loads ultimateskillos.toml automatically
```

### Option 3: Use Custom Config File

```python
from skill_engine.agent import Agent

agent = Agent.from_env(config_path="config/production.toml")
```

### Option 4: Explicit Configuration (Full Control)

```python
from config import AgentConfig, RoutingConfig
from skill_engine.agent import Agent

routing = RoutingConfig(
    mode="hybrid",
    use_embeddings=True,
    embedding_threshold=0.5,
)

config = AgentConfig(
    max_steps=10,
    timeout_seconds=300,
    verbose=True,
    routing=routing,
)

agent = Agent(config=config)
```

## Configuration Reference

### Memory Configuration

```toml
[memory]
# Embedding model for semantic search
model_name = "sentence-transformers/all-MiniLM-L6-v2"

# Embedding dimension (384 for all-MiniLM-L6-v2)
embedding_dim = 384

# Determine which embedding backend to load
provider = "auto"  # auto | sentence_transformer | openai | dummy

# Override OpenAI embedding model when provider="openai"
openai_embedding_model = "text-embedding-3-small"

# Top-K results for memory searches
top_k = 3

# Short-term memory capacity (number of records)
short_term_capacity = 100

# Database path for long-term memory
long_term_db_path = ".cache/ultimate_skillos/memory.db"

# FAISS index path for semantic search
faiss_index_path = ".cache/ultimate_skillos/memory_index.faiss"

# Enable FAISS (disables if False or FAISS not installed)
enable_faiss = true
```

**Environment Variables:**
- `SKILLOS_MEMORY_MODEL_NAME`
- `SKILLOS_MEMORY_EMBEDDING_DIM`
- `SKILLOS_MEMORY_TOP_K`
- `SKILLOS_MEMORY_SHORT_TERM_CAPACITY`
- `SKILLOS_MEMORY_LONG_TERM_DB_PATH`
- `SKILLOS_MEMORY_FAISS_INDEX_PATH`
- `SKILLOS_MEMORY_ENABLE_FAISS` (true/false)
- `SKILLOS_MEMORY_PROVIDER`
- `SKILLOS_MEMORY_OPENAI_EMBEDDING_MODEL`

**Embedding Provider Options:**
- `auto` (default): Use sentence-transformers if installed, otherwise fall back to OpenAI, then dummy zeros.
- `sentence_transformer`: Force local `sentence-transformers` models; install `sentence-transformers` beforehand.
- `openai`: Use OpenAI embeddings via `OPENAI_API_KEY`; configure `memory.openai_embedding_model`.
- `dummy`: Return zero vectors (useful for tests when embeddings are not required).

### Agent Configuration

```toml
[agent]
# Maximum steps in agent execution loop
max_steps = 6

# Timeout for agent execution (seconds)
timeout_seconds = 300

# Verbose logging during execution
verbose = false

# Enable memory system integration
enable_memory = true

# Toggle self-improving router updates
continuous_learning_enabled = false

# Minimum new feedback entries before retraining
continuous_learning_min_events = 25

[agent.routing]
# Routing mode: "keyword", "hybrid", "llm_only"
mode = "hybrid"

# Use embedding-based skill selection
use_embeddings = true

# Use LLM for intent classification
use_llm_for_intent = false

# Fall back to keyword routing if hybrid fails
keyword_fallback = true

# Minimum confidence threshold for embeddings
embedding_threshold = 0.5
```

**Environment Variables:**
- `SKILLOS_AGENT_MAX_STEPS`
- `SKILLOS_AGENT_TIMEOUT_SECONDS`
- `SKILLOS_AGENT_VERBOSE` (true/false)
- `SKILLOS_AGENT_ENABLE_MEMORY` (true/false)
- `SKILLOS_AGENT_CONTINUOUS_LEARNING_ENABLED` (true/false)
- `SKILLOS_AGENT_CONTINUOUS_LEARNING_MIN_EVENTS`
- `SKILLOS_AGENT_ROUTING_MODE`
- `SKILLOS_AGENT_ROUTING_USE_EMBEDDINGS` (true/false)
- `SKILLOS_AGENT_ROUTING_USE_LLM_FOR_INTENT` (true/false)
- `SKILLOS_AGENT_ROUTING_KEYWORD_FALLBACK` (true/false)
- `SKILLOS_AGENT_ROUTING_EMBEDDING_THRESHOLD`

### Continuous Learning Workflow

1. Enable the feature:
   ```toml
   [agent]
   continuous_learning_enabled = true
   continuous_learning_min_events = 50
   ```
2. Ensure skills emit feedback via the built-in `FeedbackLogger` (already wired through `SkillEngine`). Each skill execution appends to `data/feedback_log.json`.
3. Once the configured number of new events accumulates, the agent triggers `core.continuous_learning.ContinuousLearner`, which retrains the ML router (`core/ml_router.py`) and updates model metadata under `data/`.
4. Monitor logs for `continuous_learning_updated` events to verify retraining progress.

### Logging Configuration

```toml
[logging]
# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
level = "INFO"

# Log format string
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Optional log file path (null for console only)
file = null
```

**Environment Variables:**
- `SKILLOS_LOGGING_LEVEL`
- `SKILLOS_LOGGING_FORMAT`
- `SKILLOS_LOGGING_FILE`

## Advanced Usage

### Custom Environment Prefix

```python
from skill_engine.agent import Agent

# Use custom prefix instead of SKILLOS_
agent = Agent.from_env(env_prefix="MYAPP_")
```

Now override using:

```bash
export MYAPP_AGENT_MAX_STEPS=20
```

### Loading from pyproject.toml

The config system automatically looks for `[tool.skillos]` in `pyproject.toml`:

```toml
# pyproject.toml
[project]
name = "my-project"

[tool.skillos.agent]
max_steps = 8
verbose = true

[tool.skillos.memory]
top_k = 5
```

### Merging Configurations

Configurations merge in this order (later overrides earlier):

1. Built-in defaults
2. `pyproject.toml` `[tool.skillos]` section
3. `ultimateskillos.toml` in current directory
4. Custom config file (if `config_path` provided)
5. Environment variables

Example:

```python
# Start with defaults
# Override from ultimateskillos.toml
# Override from config/staging.toml
agent = Agent.from_env(config_path="config/staging.toml")
# Final override from SKILLOS_* environment variables
```

## Best Practices

1. **Development**: Use environment variables
   ```bash
   export SKILLOS_AGENT_VERBOSE=true
   export SKILLOS_LOGGING_LEVEL=DEBUG
   ```

2. **Projects**: Commit `ultimateskillos.toml` to version control
   ```toml
   # ultimateskillos.toml
   [agent]
   max_steps = 6
   ```

3. **Secrets**: Use environment variables for API keys and secrets
   ```bash
   # Never commit secrets!
   export SKILLOS_AGENT_API_KEY=sk-...
   ```

4. **Environments**: Use separate config files per environment
   ```bash
   python main.py  # Uses ultimateskillos.toml
   SKILLOS_CONFIG_PATH=config/prod.toml python main.py  # Uses prod.toml
   ```

5. **Testing**: Isolate configuration
   ```python
   from config import AgentConfig
   
   # Don't inherit from environment in tests
   test_config = AgentConfig(max_steps=1, timeout_seconds=10)
   agent = Agent(config=test_config)
   ```

## Migration from Old Agent(max_steps=6)

**Old Way (Still Supported):**
```python
agent = Agent.default(max_steps=6)
result = agent.run(task)
```

**New Way (Recommended):**
```python
from config import AgentConfig
from skill_engine.agent import Agent

config = AgentConfig(max_steps=6)
agent = Agent(config=config)
result = agent.run(task)
```

**Or Using Environment Variables:**
```python
agent = Agent.from_env()  # Loads from ultimateskillos.toml + env vars
result = agent.run(task)
```

## Troubleshooting

### "Config file not found"
The loader silently skips missing files. Check that:
1. Path is correct relative to current working directory
2. File permissions allow reading

### "TOML support requires 'tomli' package"
Install with: `pip install tomli` (or `pip install -r requirements.txt`)

### Environment variables not being picked up
Check the prefix:
- Default: `SKILLOS_*`
- Custom: Whatever you passed to `env_prefix`

Example:
```bash
export SKILLOS_AGENT_MAX_STEPS=10  # ✓ Correct
export SKILLOS_MAX_STEPS=10        # ✗ Wrong (missing AGENT_)
export SKILLOS_AGENT_MAXSTEPS=10   # ✗ Wrong (should be MAX_STEPS)
```

### Configuration precedence unclear
Remember: **Latest source wins**

1. Defaults loaded first
2. TOML files merged in order
3. Environment variables applied last (highest priority)

To debug, check the config:
```python
from skill_engine.agent import Agent

agent = Agent.from_env()
print(agent.config.to_dict())  # View merged configuration
```

---

For complete examples, see `config/__init__.py` and `skill_engine/agent.py`.
