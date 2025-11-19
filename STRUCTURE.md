# UltimateSkillOS Structure Guide

UltimateSkillOS is an agent-first runtime where deterministic heuristics decide which skills to run, the router decides *who* should execute them, and the memory stack keeps every step grounded in past work. This file explains where the moving pieces live today.

## Directory Highlights

- `core/` – Routing, embeddings, logging, and experimentation primitives.
    - `router.py`, `ml_router.py`, `skill_selector.py`: keyword + embedding routing logic.
    - `embedding_provider.py`, `skill_embedding_index.py`: pluggable embedding backends and FAISS index helpers.
    - `continuous_learning.py`, `feedback_logger.py`, `optimizer.py`: feedback collection and router tuning.
    - `interfaces.py`, `routing_config.py`: shared dataclasses and contracts.
- `skill_engine/` – Agent runtime.
    - `agent.py`: main loop orchestrating planning → execution → memory updates.
    - `engine.py`, `executor.py`, `registry.py`: discovery and safe execution of skills.
    - `base.py`, `skill_base.py`: BaseSkill contracts + safety wrappers.
    - `memory/`: facade for FAISS, in-memory, or dummy backends (`manager.py`, `facade.py`, `faiss_backend.py`, etc.).
    - `resilience.py`, `utils.py`: retries, timeouts, and helper utilities.
- `skills/` – First-party skills.
    - `planner.py`: heuristic task planner that sequences memory, research/meta, QA, summary, and reflection steps.
    - `memory_search.py`, `research.py`, `meta_interpreter.py`, `summarize.py`, `reflection.py`, `qa_skill.py`, etc.
    - `skill_manifest.py`, `skill_examples.py`: registry helpers and human-readable docs.
- `api/` – FastAPI entrypoint (`api/app.py`) exposing `/chat` and `/run` endpoints.
- `config/` – Loader helpers that stitch together defaults, `ultimateskillos.toml`, and env vars.
- `memory_store/` – Default JSON + FAISS storage for persisted experiences.
- `examples/` – Minimal integration examples for tests and demos.
- `tests/` – Full pytest layout (`unit/`, `integration/`, `skills/`, `golden/`, etc.) with fixtures in `tests/conftest.py`.
- `docs/`, `CONFIG_GUIDE.md`, `ARCHITECTURE_SUMMARY.md`: supplemental guides referenced from README.
- Root files (`README.md`, `Dockerfile`, `ultimateskillos.toml`, `requirements.txt`) support packaging, container builds, and configuration.

## Architecture Snapshot

1. **Planning** – `skills/planner.py` runs first. It analyzes the goal, guarantees a memory step, adds research/meta/summarize steps when keywords demand them, and always ends with `reflection`. Output is a structured list of `{description, skill, input, rationale, success_criteria}` items.
2. **Routing** – `core/router.py` and `core/ml_router.py` score skills using keyword intents, embeddings, and optional LLM intent classification. `skill_embedding_index.py` keeps per-skill vectors fresh.
3. **Execution** – `skill_engine/agent.py` asks the planner for a plan, resolves each step through `skill_engine/engine.py`, executes via `executor.py`, and records results + telemetry.
4. **Memory** – `skill_engine/memory/manager.py` decides whether to use FAISS, in-memory, or dummy backends. `memory_store/` provides the default persisted state that backs `skills/memory_search.py`.
5. **Learning + Feedback** – `core/continuous_learning.py` monitors feedback logs, while `core/optimizer.py` can refresh routing weights once enough traces accumulate.

## Execution Flow

```
User Query
    ↓
PlannerSkill.plan(goal)
    ↓ (structured steps)
Agent.run(...) iterates steps
    ↓
Router selects concrete skill implementation + params
    ↓
Skill executes via SkillEngine executor
    ↓
Results + reflections stored in MemoryManager
    ↓
Final answer returned (with plan + per-step outputs)
```

## Development Notes

- New skills inherit from `skill_engine.base.BaseSkill` or `skill_engine.skill_base.SkillBase`. Put them in `skills/` and register keywords so the router can discover them.
- The planner favors deterministic heuristics over on-the-fly LLM planning. If you add a new capability that should be in every plan, add a helper in `skills/planner.py` and cover it in `tests/unit/test_planner_skill.py`.
- Embedding backends are configured via `ultimateskillos.toml` (`memory.provider=auto|sentence_transformer|openai|dummy`). `core/embedding_provider.py` is the single source of truth.
- Tests live under `tests/` with clear scopes: `unit/`, `integration/`, `skills/`, `memory/`, etc. Run `pytest tests/unit` for fast feedback before the full suite.
