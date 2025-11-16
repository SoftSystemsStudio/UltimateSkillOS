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
python -m skill_engine.cli summarize '{"text": "Your text here"}'
```

## Configuration

Vector model: `all-MiniLM-L6-v2` (384 dims)
Search top-k: 5 results
Max agent steps: 6 (configurable)