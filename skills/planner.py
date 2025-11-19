from __future__ import annotations

import os
import re
from typing import Any, Dict, List

from skill_engine.base import BaseSkill
from core.interfaces import Planner
from pydantic import BaseModel
from skill_engine.domain import SkillInput, SkillOutput


class PlannerInput(BaseModel):
    goal: str
    plan: list[dict] = []


class PlannerOutput(BaseModel):
    executed_steps: int
    results: list[dict]
    plan: list[dict]


class PlannerSkill(BaseSkill, Planner):
    name = "planner"
    version = "2.0.0"
    description = "Decomposes complex goals into a sequenced plan using heuristics and available skills."
    input_schema = PlannerInput
    output_schema = PlannerOutput
    sla = None

    QUESTION_PREFIXES = ("what", "why", "how", "when", "who", "where", "which")
    RESEARCH_KEYWORDS = {"research", "investigate", "study", "latest", "trend", "analysis", "compare"}
    SUMMARY_KEYWORDS = {"summarize", "summary", "synthesize", "condense", "tl;dr"}
    PLAN_KEYWORDS = {"plan", "roadmap", "strategy", "steps", "outline", "framework", "approach"}
    MEMORY_KEYWORDS = {"remember", "previous", "prior", "history", "context"}

    def __init__(self) -> None:
        super().__init__()
        self.memory_top_k = int(os.getenv("PLANNER_MEMORY_TOP_K", "5"))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def plan(self, goal: str, context: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        goal = (goal or "").strip()
        if not goal:
            goal = "Provide a helpful answer"

        context = context or {}
        analysis = self._analyze_goal(goal)
        plan: List[Dict[str, Any]] = []

        if analysis["needs_memory"]:
            plan.append(self._memory_step(goal, context))

        if analysis["needs_research"]:
            plan.append(self._research_step(goal))

        if analysis["needs_plan"]:
            plan.append(self._meta_plan_step(goal))

        plan.append(self._answer_step(goal, analysis))

        if analysis["needs_summary"]:
            plan.append(self._summary_step(goal))

        plan.append(self._reflection_step(goal))

        if not plan:
            plan = self._default_plan(goal)

        return plan

    def invoke(self, input_data: SkillInput, context) -> SkillOutput:
        goal = (
            input_data.payload.get("goal")
            or input_data.payload.get("query")
            or input_data.payload.get("text")
            or ""
        )
        provided_plan = input_data.payload.get("plan")
        plan = provided_plan or self.plan(goal, context)

        return {
            "executed_steps": 0,  # Planning does not execute downstream skills directly
            "results": plan,
            "plan": plan,
        }

    # ------------------------------------------------------------------
    # Heuristic helpers
    # ------------------------------------------------------------------
    def _analyze_goal(self, goal: str) -> Dict[str, bool]:
        text = goal.lower()
        tokens = set(re.findall(r"\w+", text))

        first_word = text.split()[:1]
        is_question = text.endswith("?") or (
            first_word and first_word[0] in self.QUESTION_PREFIXES
        )
        needs_research = bool(tokens & self.RESEARCH_KEYWORDS)
        needs_summary = bool(tokens & self.SUMMARY_KEYWORDS)
        needs_plan = bool(tokens & self.PLAN_KEYWORDS)
        needs_memory = (
            needs_research
            or bool(tokens & self.MEMORY_KEYWORDS)
            or "remember" in text
            or is_question
        )
        if not needs_memory:
            needs_memory = True  # Default to checking memory so context is available

        return {
            "is_question": is_question,
            "needs_research": needs_research,
            "needs_summary": needs_summary,
            "needs_plan": needs_plan,
            "needs_memory": needs_memory,
        }

    def _memory_step(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        top_k = getattr(context, "memory_top_k", self.memory_top_k)
        return self._step(
            description="Gather prior knowledge",
            skill="memory_search",
            payload={"query": goal, "k": top_k},
            reason="Use stored experiences or notes before reaching out to external tools.",
            success="Relevant memory snippets identified or explicit acknowledgement that none exist.",
        )

    def _research_step(self, goal: str) -> Dict[str, Any]:
        return self._step(
            description="Perform targeted research",
            skill="research",
            payload={"query": goal},
            reason="The request references investigation/analysis that benefits from external data.",
            success="Fresh findings or citations captured for the goal.",
        )

    def _meta_plan_step(self, goal: str) -> Dict[str, Any]:
        return self._step(
            description="Decompose goal into milestones",
            skill="meta_interpreter",
            payload={"task": goal},
            reason="User explicitly asked for a plan/strategy/roadmap.",
            success="Structured outline or actionable checklist produced.",
        )

    def _answer_step(self, goal: str, analysis: Dict[str, bool]) -> Dict[str, Any]:
        mode = "qa" if analysis["is_question"] else "reason"
        return self._step(
            description="Produce core answer or reasoning",
            skill="question_answering",
            payload={"query": goal, "mode": mode},
            reason="Synthesize information gathered so far into a direct response.",
            success="Clear answer or rationale aligned with the goal.",
        )

    def _summary_step(self, goal: str) -> Dict[str, Any]:
        return self._step(
            description="Summarize findings",
            skill="summarize",
            payload={"text": "<LAST_RESULT>"},
            reason="User asked for a summary-style deliverable.",
            success="Concise summary highlighting the key points.",
        )

    def _reflection_step(self, goal: str) -> Dict[str, Any]:
        return self._step(
            description="Check for gaps or improvements",
            skill="reflection",
            payload={"text": "<LAST_RESULT>"},
            reason="Ensure the final answer meets quality expectations.",
            success="List of issues (if any) and suggested adjustments.",
        )

    def _default_plan(self, goal: str) -> List[Dict[str, Any]]:
        return [
            self._memory_step(goal, {}),
            self._answer_step(goal, {"is_question": True}),
            self._reflection_step(goal),
        ]

    def _step(self, *, description: str, skill: str, payload: Dict[str, Any], reason: str, success: str) -> Dict[str, Any]:
        return {
            "description": description,
            "skill": skill,
            "input": payload,
            "rationale": reason,
            "success_criteria": success,
        }
