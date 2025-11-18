# UltimateSkillOS

Agent-based skill execution framework with autonomous routing, persistent memory, and tool integration.

## Features

- **Modular Skills**: Pluggable skill system with base abstractions
- **Intelligent Routing**: Keyword-based intent matching with fallbacks
- **Persistent Memory**: FAISS-backed vector storage + JSON metadata
- **Agent Loop**: Multi-step reasoning with memory context injection
- **Type Safety**: Full type hints and validation
- **Zero Dependencies**: Minimal core + optional external integrations

## Quick Start

```python
from skill_engine.agent import Agent

agent = Agent(max_steps=6)
result = agent.run("summarize this text", verbose=True)
print(result["final_answer"])
```

## Architecture

- **core/**: Router, loaders, evaluation
- **skill_engine/**: Agent, skills engine, memory management
- **skills/**: Individual skill implementations
- **memory/**: Long-term and short-term memory systems

See [STRUCTURE.md](./STRUCTURE.md) for detailed documentation.

## Skills Included

- **Summarize**: Extract concise summaries
- **Research**: Web search (Tavily integration)
- **File Tool**: Read/write operations
- **Meta Interpreter**: Plan generation from markdown
- **Reflection**: Criticism and improvement suggestions
- **Autofix**: Typo correction
- **Memory Search**: Query persistent memory
- **Planner**: Task decomposition

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Python API

```python
from skill_engine.agent import Agent

# Create agent with default configuration
agent = Agent.default(max_steps=6)

# Run a task
result = agent.run("How does photosynthesis work?", verbose=True)
print(result.final_answer)
```

### Web Interface

Start the FastAPI server:

```bash
uvicorn api:app --host 0.0.0.0 --port 8002
```

Then open your browser to `http://localhost:8002` to access the interactive chat interface.

### API Endpoint

Send POST requests to `/chat`:

```bash
curl -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain machine learning in simple terms"}'
```

Response format:

```json
{
  "response": {
    "plan_id": "...",
    "status": "success",
    "final_answer": "...",
    "step_results": [...],
    "total_time_ms": 123.45,
    "steps_completed": 2,
    "metadata": {...}
  }
}
```

### CLI

```bash
python -m skill_engine.cli summarize '{"text": "Your text here"}'
```

## Configuration

Vector model: `all-MiniLM-L6-v2` (384 dims)
Search top-k: 5 results
Max agent steps: 6 (configurable)

Configuration file: `ultimateskillos.toml` or environment variables with `SKILLOS_` prefix.