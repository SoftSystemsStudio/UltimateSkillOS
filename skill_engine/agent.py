# skill_engine/agent.py

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from skill_engine.domain import AgentPlan, AgentResult, PlanStep, SkillInput, StepResult
from skill_engine.engine import SkillEngine
from skill_engine.memory.memory_manager import get_memory_manager
from skill_engine.skill_base import RunContext
from core.router import Router  # Using the existing Router implementation

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, max_steps: int = 6) -> None:
        self.engine = SkillEngine()
        # Shared, process-wide memory manager (SQLite-backed by default)
        self.memory = get_memory_manager()
        self.router = Router()
        self.max_steps = max_steps

    def run(
        self, task: str, *, max_steps: int | None = None, verbose: bool = False
    ) -> AgentResult:
        """
        Execute a task using the skill engine with structured result tracking.

        Args:
            task: The task/query to execute.
            max_steps: Maximum steps to take (overrides instance default).
            verbose: Whether to print intermediate steps.

        Returns:
            AgentResult with complete execution trace and structured data.
        """
        # Setup
        plan_id = str(uuid.uuid4())
        trace_id = str(uuid.uuid4())
        max_steps = max_steps or self.max_steps
        start_time = time.time()

        # Create plan from task
        plan = AgentPlan(plan_id=plan_id, goal=task)
        result = AgentResult(plan_id=plan_id, status="failed")

        query: str = task
        step_results: List[StepResult] = []

        try:
            for step_num in range(1, max_steps + 1):
                step_id = f"{plan_id}:step_{step_num}"
                step_start = time.time()

                if verbose:
                    logger.info(f"Step {step_num}: Query: {query}")

                # Route to best skill
                try:
                    route_result = self.router.route(query)
                    skill_name = route_result["use_skill"]
                    params: Dict[str, Any] = route_result.get(
                        "params", {"text": query}
                    )
                except Exception as e:
                    logger.error(f"Routing failed at step {step_num}: {e}")
                    step_result = StepResult(
                        step_id=step_id,
                        success=False,
                        error=f"Routing failed: {str(e)}",
                        execution_time_ms=(time.time() - step_start) * 1000,
                        attempt=1,
                    )
                    step_results.append(step_result)
                    result.add_step_result(step_result)
                    break

                # Create execution context
                context = RunContext(
                    trace_id=trace_id,
                    correlation_id=plan_id,
                    memory_context=self.memory.search(query),
                )

                # Execute skill
                try:
                    skill_input = SkillInput(
                        payload=params, trace_id=trace_id, correlation_id=plan_id
                    )

                    skill_output = self.engine.run(skill_name, dict(params))

                    if verbose:
                        logger.info(
                            f"Skill '{skill_name}' completed: {skill_output}"
                        )

                    step_result = StepResult(
                        step_id=step_id,
                        success=True,
                        output=skill_output if hasattr(skill_output, "to_dict") else None,
                        execution_time_ms=(time.time() - step_start) * 1000,
                        attempt=1,
                    )

                    step_results.append(step_result)
                    result.add_step_result(step_result)

                except Exception as e:
                    logger.error(f"Skill execution failed at step {step_num}: {e}")
                    step_result = StepResult(
                        step_id=step_id,
                        success=False,
                        error=f"Skill '{skill_name}' failed: {str(e)}",
                        execution_time_ms=(time.time() - step_start) * 1000,
                        attempt=1,
                    )
                    step_results.append(step_result)
                    result.add_step_result(step_result)
                    break

                # Extract observation
                structured_obs: Optional[Dict[str, Any]] = (
                    skill_output if isinstance(skill_output, dict) else None
                )

                # Memory write: store useful outcomes
                if structured_obs is not None:
                    if "summary" in structured_obs:
                        self.memory.add(str(structured_obs["summary"]))
                    elif "answer" in structured_obs:
                        self.memory.add(str(structured_obs["answer"]))
                    else:
                        text_val = params.get("text")
                        if isinstance(text_val, str):
                            self.memory.add(text_val)

                # Termination: explicit summary/answer
                if (
                    structured_obs is not None
                    and ("summary" in structured_obs or "answer" in structured_obs)
                ):
                    final_answer = structured_obs.get("summary") or structured_obs.get(
                        "answer"
                    )
                    result.status = "success"
                    result.final_answer = final_answer
                    result.memory_used = self.memory.search(task)
                    break

                # Termination: memory_search skill
                if (
                    skill_name == "memory_search"
                    and structured_obs is not None
                    and "matches" in structured_obs
                ):
                    matches = structured_obs.get("matches") or []
                    query_for_search = (
                        params.get("query") or params.get("text") or query
                    )
                    query_clean = str(query_for_search).strip()

                    answer_text: Optional[str] = None

                    if matches:
                        for m in matches:
                            if not isinstance(m, dict):
                                continue
                            txt = m.get("text")
                            if not isinstance(txt, str):
                                continue

                            clean = txt.strip()
                            if clean == query_clean:
                                continue
                            if clean.startswith("{") and "summary" in clean:
                                continue

                            answer_text = clean
                            break

                        if answer_text is None:
                            top = matches[0]
                            if isinstance(top, dict) and isinstance(
                                top.get("text"), str
                            ):
                                answer_text = top["text"]  # type: ignore[index]

                    if answer_text:
                        self.memory.add(answer_text)
                        result.status = "success"
                        result.final_answer = answer_text
                        result.memory_used = self.memory.search(task)
                        break

                    no_match_answer = (
                        "I could not find anything in memory that answers that."
                    )
                    self.memory.add(no_match_answer)
                    result.status = "partial"
                    result.final_answer = no_match_answer
                    result.memory_used = self.memory.search(task)
                    break

                # Default: propagate observation into next query
                query = str(skill_output)

            # If we completed all steps without terminating
            if result.status == "failed":
                result.status = "partial"
                result.final_answer = query
                result.memory_used = self.memory.search(task)

        except Exception as e:
            logger.exception(f"Unexpected error during agent execution: {e}")
            result.status = "failed"
            result.final_answer = None
            result.metadata["error"] = str(e)

        finally:
            # Finalize result
            result.total_time_ms = (time.time() - start_time) * 1000
            result.metadata["steps_taken"] = len(step_results)
            result.metadata["plan_id"] = plan_id
            result.metadata["trace_id"] = trace_id

        return result
