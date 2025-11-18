# UltimateSkillOS: 3-Month Enhancement Roadmap

**Target:** Close feedback loops for self-evolving workflows; transition from foundational → production-ready autonomy.

---

## Phase 1: Reflection-to-Action Loop (Weeks 1–4)

**Goal:** Enable agent to self-correct by auto-invoking reflection and acting on feedback.

### 1.1 Enhanced ReflectionSkill

**File:** `skills/reflection.py`

**Changes:**
- Add structured output: `{"critique": "...", "severity": "error|warning|info", "suggested_action": "retry|replan|skip"}`
- Classify outcomes (success, partial, failure) instead of just checking text length.
- Return a `reflection_score` (0–100) indicating confidence in the outcome.

**Example Output:**
```json
{
  "critique": "Research returned too few results; may need broader query.",
  "severity": "warning",
  "reflection_score": 45,
  "suggested_action": "retry"
}
```

### 1.2 Integrate Reflection into Agent Loop

**File:** `skill_engine/agent.py`

**Changes:**
```python
# After each step execution, optionally invoke reflection
if step_result.success and should_reflect(skill_name, step_num):
    reflection = safe_invoke(reflection_skill, skill_output, context)
    reflection_score = reflection.get("reflection_score", 100)
    step_result.metrics["reflection_score"] = reflection_score
    
    # If score is low, trigger re-execution or re-plan
    if reflection_score < 50:
        # Mark for retry or defer to re-planning phase
        step_result.metadata["requires_rework"] = True
        context.logger.warning(f"Step {step_num} flagged for rework: {reflection['suggested_action']}")
```

**Acceptance Criteria:**
- Reflection is invoked after ~50% of steps (configurable).
- reflection_score is captured in metrics.
- Agent logs and acts on "requires_rework" flag.
- Test: `tests/integration/test_reflection_loop.py` verifies reflection triggers and scores are captured.

**Effort:** 1–2 days | **Testing:** 1 day

---

## Phase 2: Adaptive Planning & Dynamic Re-planning (Weeks 5–8)

**Goal:** Enable agent to decompose goals dynamically and re-plan if initial plan fails.

### 2.1 Implement PlannerSkill

**File:** `skills/planner.py`

**Current State:** Stub that just iterates through pre-defined steps.

**Changes:**
- Add a `decompose(goal: str, context: dict) → List[PlanStep]` method.
- For each step, invoke the appropriate skill (e.g., if "research" step, invoke research skill).
- Return execution results with timing and outcomes.

**Example:**
```python
def invoke(self, input_data: SkillInput, context: RunContext) -> SkillOutput:
    plan = input_data.payload.get("plan")
    results = []
    for step in plan.steps:
        # Invoke the skill for this step
        skill_obj = self.engine.skills[step.skill_name]
        step_input = SkillInput(payload=step.input_data, trace_id=context.trace_id)
        step_output = safe_invoke(skill_obj, step_input, context)
        results.append({
            "step_id": step.step_id,
            "output": step_output.to_dict()
        })
    return SkillOutput(payload={"results": results})
```

**Acceptance Criteria:**
- PlannerSkill can execute a plan and return results for each step.
- Test: `tests/skills/test_planner_execution.py` verifies multi-step execution.

**Effort:** 2–3 days | **Testing:** 1–2 days

### 2.2 Agent Re-planning Logic

**File:** `skill_engine/agent.py`

**Changes:**
```python
# If reflection indicates plan needs rework and attempts < max_replans:
if plan_requires_rework and replan_attempts < MAX_REPLANS:
    context.logger.info(f"Generating alternative plan (attempt {replan_attempts + 1})")
    
    # Invoke MetaInterpreter to generate a new plan
    meta_input = SkillInput(
        payload={"goal": task, "previous_attempt": result.to_dict()},
        trace_id=trace_id
    )
    new_plan_output = safe_invoke(meta_interpreter_skill, meta_input, context)
    new_plan = new_plan_output.payload.get("plan")
    
    # Execute new plan via PlannerSkill
    planner_input = SkillInput(payload={"plan": new_plan}, trace_id=trace_id)
    replan_result = safe_invoke(planner_skill, planner_input, context)
    
    result = replan_result  # Overwrite with new attempt
    replan_attempts += 1
```

**Acceptance Criteria:**
- If reflection score is low, agent auto-generates alternative plan.
- Agent executes new plan and compares results.
- Metrics track number of re-planning attempts.
- Test: `tests/integration/test_replanning.py` verifies re-plan trigger and execution.

**Effort:** 2 days | **Testing:** 1–2 days

---

## Phase 3: Learning from History (Weeks 9–12)

**Goal:** Agent learns from past executions and improves future decisions.

### 3.1 Memory Summarization

**File:** `skill_engine/memory/summarizer.py` (new)

**Changes:**
- Implement `summarize_executions(time_window="7d") → dict`.
- Query memory for all executed steps in the window.
- Cluster by skill and outcome; generate statistics.

**Example Output:**
```json
{
  "period": "2025-11-18 to 2025-11-25",
  "summary": {
    "research": {
      "invocations": 42,
      "success_rate": 0.88,
      "avg_latency_ms": 1250,
      "common_queries": ["AI safety", "ML benchmarks"]
    },
    "summarize": {
      "invocations": 38,
      "success_rate": 0.95,
      "avg_latency_ms": 320
    }
  },
  "learned_heuristics": [
    "If query contains 'recent', prefer research_skill (89% success)",
    "Summarize skill consistently succeeds; no retries needed"
  ]
}
```

**Acceptance Criteria:**
- Summarizer generates reports with skill statistics.
- Test: `tests/unit/test_summarizer.py` verifies statistics calculation.

**Effort:** 1–2 days | **Testing:** 1 day

### 3.2 Dynamic Heuristic Generation & Storage

**File:** `skill_engine/memory/heuristics.py` (new)

**Changes:**
- Store learned heuristics in a JSON file (e.g., `.cache/learned_heuristics.json`).
- At startup, Agent loads heuristics and passes them to Router.
- Router uses heuristics to adjust skill scores (e.g., boost research_skill score by +10 if query contains "recent").

**Example Heuristic File:**
```json
{
  "last_updated": "2025-11-25T10:00:00Z",
  "heuristics": [
    {
      "condition": "query_contains('recent')",
      "skill": "research",
      "boost": 15,
      "confidence": 0.89,
      "evidence_count": 42
    },
    {
      "condition": "query_contains('summarize')",
      "skill": "summarize",
      "boost": 20,
      "confidence": 0.95,
      "evidence_count": 38
    }
  ]
}
```

**Acceptance Criteria:**
- Router consults heuristics and adjusts scores.
- Heuristics are periodically regenerated (e.g., daily).
- Test: `tests/unit/test_router_with_heuristics.py` verifies score adjustment.

**Effort:** 2 days | **Testing:** 1–2 days

### 3.3 Performance Dashboard (Optional)

**File:** `api/dashboard.py` (new)

**Changes:**
- Add `/metrics` endpoint that returns aggregated performance stats.
- Include skill health, query success rates, and learned heuristics.

**Example Response:**
```json
{
  "agent_health": "operational",
  "uptime_hours": 120,
  "total_queries": 485,
  "success_rate": 0.82,
  "avg_latency_ms": 1450,
  "skills": {
    "research": {"success_rate": 0.88, "invocations": 42},
    "summarize": {"success_rate": 0.95, "invocations": 38}
  },
  "learned_heuristics_count": 8
}
```

**Acceptance Criteria:**
- Dashboard endpoint returns comprehensive metrics.
- Test: `tests/api/test_metrics_endpoint.py` verifies response schema.

**Effort:** 1 day | **Testing:** 0.5 days

---

## Implementation Schedule

| Week | Phase | Components | Effort |
|---|---|---|---|
| 1–4 | Reflection-to-Action | ReflectionSkill + agent loop integration | 4–5 days |
| 5–8 | Adaptive Planning | PlannerSkill + re-planning logic | 6–7 days |
| 9–12 | Learning from History | Summarizer + heuristic generation + dashboard | 5–6 days |

**Total:** ~15–18 development days + 4–5 days testing/documentation.

---

## Testing Strategy

### Unit Tests (Per Phase)
- `test_reflection_skill.py` — ReflectionSkill output format and scoring.
- `test_planner_skill.py` — PlannerSkill multi-step execution.
- `test_summarizer.py` — Memory summarization logic.
- `test_heuristic_generation.py` — Heuristic creation and storage.

### Integration Tests (Per Phase)
- `test_reflection_loop.py` — Agent invokes reflection and acts on feedback.
- `test_replanning.py` — Agent re-plans and re-executes on low reflection score.
- `test_learning_loop.py` — Memory summarization and heuristic application improve future queries.

### Contract Tests
- Verify ReflectionSkill implements Skill protocol.
- Verify PlannerSkill input/output schemas.

### Golden Tests
- Store golden traces for canonical queries (e.g., "Summarize recent AI safety research").
- Verify reflection scores and re-planning attempts are logged.
- Use golden traces to detect regressions in reflection quality or learning behavior.

---

## Success Criteria

By end of Q4 2025:
- ✅ Agent auto-invokes reflection and acts on feedback.
- ✅ Agent dynamically re-plans if initial attempt scores low.
- ✅ Memory summarization generates performance statistics.
- ✅ Router uses learned heuristics to adjust skill selection.
- ✅ All new features covered by unit + integration tests.
- ✅ Golden traces demonstrate improved query outcomes over time.
- ✅ Overall agent autonomy score: 8/10 (from current 7.5/10).

---

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| Reflection invocations slow down agent | Make reflection sampling configurable; default to 50% of steps. |
| Re-planning creates infinite loops | Cap re-planning attempts; abort if max_replans exceeded. |
| Heuristics become outdated | Regenerate daily; include confidence scores; deprecate old heuristics. |
| Learning curve for operators | Document via examples; add CLI command `skillos metrics --summary`. |

---

## Future Enhancements (Q1+ 2026)

- **Multi-agent coordination:** Spawn sub-agents for parallel sub-goal execution.
- **Continual learning with LLM:** Use LLM to critique traces and suggest new skills.
- **Skill generation:** Auto-create new skills based on unmet goals detected in reflection.
- **Hierarchical planning:** Support deep task trees with dependency management.

---

## Appendix: Example Execution Flow (End-State)

```
User: "Summarize recent breakthroughs in AI safety research."

Initial Query
  ↓
MetaInterpreter generates plan:
  Step 1: Research("recent AI safety breakthroughs") 
  Step 2: Summarize(research_result)
  ↓
Agent executes plan:
  Step 1: safe_invoke(Research, ...)
    → Output: [5 papers on AI alignment]
    → Reflection invoked: "Found relevant papers; good start." (score: 75)
  Step 2: safe_invoke(Summarize, ...)
    → Output: "AI safety research focuses on alignment, interpretability, and robustness..."
    → Reflection invoked: "Summary is comprehensive but long." (score: 60)
  ↓
Agent detects low reflection score on step 2
  → Triggers re-plan:
    "Summarize results more concisely."
  ↓
MetaInterpreter generates new plan:
  Step 1: Research (with tighter focus)
  Step 2: Summarize (with max_length constraint)
  ↓
Agent re-executes new plan
  → Step 1: [3 most impactful papers]
  → Step 2: "AI safety: alignment (how to ensure AI follows human intent), 
              interpretability (understanding AI decision-making), 
              robustness (ensuring AI behaves correctly under adversarial conditions)."
  → Reflection: "Concise, covers key areas." (score: 90)
  ↓
Agent returns result with metadata:
  {
    "answer": "...",
    "status": "success",
    "replanning_attempts": 1,
    "total_time_ms": 2500,
    "reflection_scores": [75, 60, 90],
    "learned_heuristics_applied": ["Recent queries prefer research_skill"]
  }
  ↓
Memory writes outcome + learned heuristic update
  ↓
On next similar query, Router uses learned heuristics
  → Improves skill selection confidence
```

---

## Questions & Discussion

1. **Reflection sampling:** Should reflection be invoked for every step, sampled randomly, or triggered only after failures?
   - Recommendation: Sample 50% by default; always reflect on failures.

2. **Re-planning cap:** How many re-planning attempts before giving up?
   - Recommendation: 2–3 max; log and return partial result.

3. **Heuristic staleness:** How often should heuristics be regenerated?
   - Recommendation: Daily at minimum; on-demand if explicitly requested.

4. **Memory growth:** Will summarization and heuristic storage cause memory bloat?
   - Recommendation: Archive old summaries (e.g., keep last 30 days); compress heuristics.

---

**Prepared by:** AI Assistant  
**Date:** November 18, 2025  
**Status:** Ready for stakeholder review and prioritization.
