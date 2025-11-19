# UltimateSkillOS

Agent-based skill execution framework with autonomous routing, persistent memory, and tool integration.

## Features

- **Modular Skills**: Pluggable skill system with base abstractions
- **Routing + Planning**: Hybrid keyword/embedding intent routing backed by a deterministic heuristic planner
- **Persistent Memory**: FAISS-backed vector storage + JSON metadata
- **Pluggable Embeddings**: Sentence-transformers, OpenAI, or dummy providers via config
- **Continuous Learning (optional)**: Feedback-driven router updates once enough traces accrue
- **Agent Loop**: Multi-step reasoning with memory context injection
- **Type Safety**: Full type hints and validation
- **Zero Dependencies**: Minimal core + optional external integrations

## Quick Start

```python
from skill_engine.agent import Agent

agent = Agent.from_env()  # honors ultimateskillos.toml + SKILLOS_* overrides
result = agent.run("summarize this text", verbose=True)
print(result.final_answer)
```

## Architecture

- **core/**: Router, loaders, evaluation
- **skill_engine/**: Agent, skills engine, memory management
- **skills/**: Individual skill implementations
- **memory/**: Long-term and short-term memory systems

See [STRUCTURE.md](./STRUCTURE.md) for detailed documentation.

### Planner & Execution Flow

- Goals are analyzed for intent (question, research, summary, planning cues, memory hints).
- Planner always kicks off with `memory_search` to ground the task in prior context.
- Research/plan/summarize steps are conditionally inserted based on keyword heuristics.
- Core answers are produced via `question_answering` with QA vs reasoning modes.
- Every plan ends with `reflection` so downstream skills can critique their own output.

## Skills Included

- **Summarize**: Extract concise summaries
- **Research**: Web search (Tavily integration)
- **File Tool**: Read/write operations
- **Meta Interpreter**: Plan generation from markdown
- **Reflection**: Criticism and improvement suggestions
- **Autofix**: Typo correction
- **Memory Search**: Query persistent memory
- **Planner**: Heuristic task decomposer that sequences memory, research, reasoning, summary, and reflection skills

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Python API

```python
from skill_engine.agent import Agent

# Create agent with layered configuration (defaults + ultimateskillos.toml + env)
agent = Agent.from_env()

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

- **Embeddings**: Configure `memory.provider` to `auto`, `sentence_transformer`, `openai`, or `dummy`. When using OpenAI, set `OPENAI_API_KEY` and optionally `memory.openai_embedding_model`.
- **Vector Model Defaults**: `all-MiniLM-L6-v2` (384 dims) with FAISS persisted to `.cache/ultimate_skillos/`.
- **Search Top-K**: `memory.top_k` (default 3) controls recall size.
- **Agent Steps**: `agent.max_steps` (default 6) plus `agent.verbose`, `agent.enable_memory` toggles.
- **Continuous Learning**: Toggle `agent.continuous_learning_enabled` and set `agent.continuous_learning_min_events` to control when router retraining kicks in based on feedback logs.

Manage configuration in `ultimateskillos.toml` or override with environment variables prefixed by `SKILLOS_` (see `CONFIG_GUIDE.md` for exhaustive reference).