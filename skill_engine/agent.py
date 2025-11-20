# skill_engine/agent.py

from __future__ import annotations

import logging
import time
import uuid
from copy import deepcopy
from typing import Any, Dict, List, Optional

from config import AgentConfig, AppConfig, load_config
from skill_engine.domain import AgentPlan, AgentResult, PlanStep, SkillInput, StepResult, SkillOutput
from skill_engine.engine import SkillEngine
from skill_engine.memory.manager import get_memory_manager
from skill_engine.registry import get_global_registry, SkillRegistry
from skill_engine.skill_base import RunContext
from skill_engine.memory.facade import MemoryFacade
from core.router import Router
from core.logging import get_logger as get_structured_logger
from skill_engine.skill_base import safe_invoke
from skill_engine.resilience import create_registry
from core.continuous_learning import ContinuousLearner
from core.feedback_logger import FeedbackLogger
import os

logger = logging.getLogger(__name__)


class Agent:
    def __init__(
        self,
        config: AgentConfig,
        registry: SkillRegistry | None = None,
        memory_facade: MemoryFacade | None = None,
        app_config: AppConfig | None = None,
    ) -> None:
        """
        Initialize Agent with explicit dependency injection.

        Args:
            config: AgentConfig with execution parameters and routing mode.
            registry: SkillRegistry for skill lookup (uses global if None).
            memory_facade: MemoryFacade for memory operations (creates new if None).
        """
        self.config = config
        self.app_config = app_config
        self.registry = registry or get_global_registry()

        memory_cfg = app_config.memory if app_config else None
        # get_memory_manager() returns MemoryFacade directly
        self.memory_facade = memory_facade or get_memory_manager(memory_config=memory_cfg)

        self.continuous_learner: ContinuousLearner | None = None
        if self.config.continuous_learning_enabled:
            try:
                min_events = max(1, self.config.continuous_learning_min_events)
                self.continuous_learner = ContinuousLearner(min_events=min_events)
            except Exception as exc:
                logger.warning("Continuous learning disabled due to initialization error: %s", exc)

        # Create a circuit-breaker registry for this Agent instance.
        # Uses SKILLOS_CIRCUIT_REDIS_URL if provided; avoids globals.
        redis_url = os.environ.get("SKILLOS_CIRCUIT_REDIS_URL")
        try:
            self.circuit_registry = create_registry(redis_url)
        except Exception:
            self.circuit_registry = create_registry(None)

        # Initialize engine and router
        self.engine = SkillEngine()
        self.feedback_logger = FeedbackLogger()

        # Create router with config's routing settings
        # Note: config.routing is already a RoutingConfig from config module
        try:
            self.router = Router(config.routing)
        except Exception as e:
            logger.warning(f"Failed to initialize router with config: {e}, using default")
            self.router = Router()

        # Event hooks: observer registry
        self._observers = {}

    def subscribe(self, event_name: str, callback):
        """Subscribe a callback to an event."""
        if event_name not in self._observers:
            self._observers[event_name] = []
        self._observers[event_name].append(callback)

    def publish(self, event_name: str, **kwargs):
        """Publish an event to all observers."""
        for cb in self._observers.get(event_name, []):
            try:
                cb(**kwargs)
            except Exception as e:
                logger.warning(f"Observer callback error for event '{event_name}': {e}")

    @staticmethod
    def from_env(
        config_path: str | None = None,
        env_prefix: str = "SKILLOS_",
    ) -> Agent:
        """
        Create Agent from environment configuration.

        Loads configuration from layered sources and returns a ready-to-use Agent.

        Args:
            config_path: Optional path to config file (TOML/YAML).
            env_prefix: Prefix for environment variables (default: SKILLOS_).

        Returns:
            Agent instance with configuration loaded from environment.

        Example:
            # Uses ultimateskillos.toml + environment variables
            agent = Agent.from_env()

            # Custom config path
            agent = Agent.from_env(config_path="production.toml")

            # Custom environment prefix
            agent = Agent.from_env(env_prefix="MYAPP_")
        """
        app_config = load_config(config_path, env_prefix)

        # Configure logging if file specified
        if app_config.logging.file:
            logging.basicConfig(
                level=app_config.logging.level,
                format=app_config.logging.format,
                filename=app_config.logging.file,
            )
        else:
            logging.basicConfig(
                level=app_config.logging.level,
                format=app_config.logging.format,
            )

        return Agent(config=app_config.agent, app_config=app_config)

    @staticmethod
    def default(max_steps: int = 6) -> Agent:
        """
        Create Agent with default configuration (convenience method).

        Args:
            max_steps: Override default maximum steps.

        Returns:
            Agent with default AppConfig.
        """
        agent_config = AgentConfig(max_steps=max_steps)
        app_config = AppConfig()
        app_config.agent = agent_config
        return Agent(config=agent_config, app_config=app_config)

    def run(
        self, task: str, *, max_steps: int | None = None, verbose: bool = False
    ) -> AgentResult:
        """
        Execute a task using the skill engine with structured result tracking.

        Args:
            task: The task/query to execute.
            max_steps: Maximum steps to take (overrides config default).
            verbose: Whether to print intermediate steps (overrides config).

        Returns:
            AgentResult with complete execution trace and structured data.
        """
        # Setup
        plan_id = str(uuid.uuid4())
        trace_id = str(uuid.uuid4())
        max_steps = max_steps or self.config.max_steps
        verbose = verbose or self.config.verbose
        start_time = time.time()

        # Create plan from task (planner populates plan.steps when available)
        plan = AgentPlan(plan_id=plan_id, goal=task)
        planner_steps = self._generate_plan(plan, trace_id)
        plan_used = bool(plan.steps)

        result = AgentResult(plan_id=plan_id, status="failed")
        if planner_steps:
            result.metadata["planner_plan"] = planner_steps
        if plan_used:
            result.metadata["plan"] = plan.to_dict()
        result.metadata["plan_used"] = plan_used

        query: str = task
        step_results: List[StepResult] = []
        plan_index = 0
        last_result_text: Optional[str] = None
        final_answer_candidate: Optional[str] = None
        failure_occurred = False
        skills_invoked: List[str] = []
        reflection_snapshot: Optional[Dict[str, Any]] = None

        try:
            for step_num in range(1, max_steps + 1):
                step_id = f"{plan_id}:step_{step_num}"
                step_start = time.time()

                if verbose:
                    logger.info(f"Step {step_num}: Query: {query}")

                # Determine step source (planner vs router)
                is_plan_step = plan_index < len(plan.steps)
                plan_step = plan.steps[plan_index] if is_plan_step else None
                if is_plan_step:
                    plan_index += 1
                    skill_name = plan_step.skill_name
                    raw_params = plan_step.input_data or {}
                    params = self._prepare_plan_inputs(raw_params, last_result_text)
                    if not isinstance(params, dict):
                        params = {"text": query}
                else:
                    try:
                        route_result = self.router.route(query)
                        skill_name = route_result["use_skill"]
                        params = route_result.get("params", {"text": query})
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
                        failure_occurred = True
                        break

                # Create execution context with memory facade and structured logger
                step_logger = get_structured_logger(
                    f"skill.{skill_name}", trace_id=trace_id, step_id=step_id, correlation_id=plan_id
                )
                context = RunContext(
                    trace_id=trace_id,
                    correlation_id=plan_id,
                    memory_facade=self.memory_facade,
                    logger=step_logger,
                    circuit_registry=self.circuit_registry,
                )

                # Execute skill (using safe_invoke to provide timeout/retries)
                try:
                    skill_input = SkillInput(
                        payload=params, trace_id=trace_id, correlation_id=plan_id
                    )

                    skill_obj = self.engine.skills.get(skill_name)
                    if skill_obj is None:
                        logger.warning(
                            f"Skill '{skill_name}' not found, trying question_answering fallback"
                        )
                        skill_obj = self.engine.skills.get("question_answering")
                        if skill_obj is not None:
                            skill_name = "question_answering"
                            params = {"query": query, "text": query}
                            skill_input = SkillInput(
                                payload=params, trace_id=trace_id, correlation_id=plan_id
                            )
                        else:
                            raise RuntimeError(
                                f"Skill '{skill_name}' not found and no fallback available"
                            )

                    skill_output = safe_invoke(skill_obj, skill_input, context)
                    normalized_output = self._normalize_output(skill_output)
                    step_output_obj = self._coerce_skill_output(skill_output, normalized_output)

                    if verbose:
                        logger.info(f"Skill '{skill_name}' completed")

                    step_result = StepResult(
                        step_id=step_id,
                        success=True,
                        output=step_output_obj,
                        execution_time_ms=(time.time() - step_start) * 1000,
                        attempt=1,
                    )

                    step_results.append(step_result)
                    result.add_step_result(step_result)
                    skills_invoked.append(skill_name)

                    self.publish(
                        "skill_executed",
                        skill_name=skill_name,
                        step_id=step_id,
                        output=skill_output,
                        params=params,
                    )

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
                    failure_occurred = True
                    self.publish(
                        "skill_failed",
                        skill_name=skill_name,
                        step_id=step_id,
                        error=str(e),
                        params=params,
                    )
                    # Continue to next step instead of breaking if we're following a plan
                    if is_plan_step and plan_index < len(plan.steps):
                        continue
                    else:
                        break

                structured_obs = normalized_output
                extracted_answer = self._extract_answer_text(structured_obs)
                if extracted_answer:
                    final_answer_candidate = str(extracted_answer)
                    last_result_text = final_answer_candidate
                elif structured_obs is None and isinstance(skill_output, str):
                    last_result_text = skill_output

                if skill_name == "reflection" and isinstance(structured_obs, dict):
                    reflection_snapshot = structured_obs

                if self.config.enable_memory and structured_obs is not None:
                    try:
                        memory_text = extracted_answer
                        if memory_text:
                            self.memory_facade.add(
                                str(memory_text),
                                tier="long_term",
                                metadata={"trace_id": trace_id, "step_id": step_id},
                            )
                        else:
                            text_val = params.get("text")
                            if isinstance(text_val, str):
                                self.memory_facade.add(
                                    text_val,
                                    tier="long_term",
                                    metadata={"trace_id": trace_id, "step_id": step_id},
                                )
                    except Exception as e:
                        logger.warning(f"Failed to write to memory: {e}")

                plan_remaining = plan_index < len(plan.steps)

                if (
                    extracted_answer
                    and (not is_plan_step or not plan_remaining)
                ):
                    result.status = "success"
                    result.final_answer = str(extracted_answer)
                    if self.config.enable_memory:
                        result.memory_used = self.memory_facade.recall_context(task)
                    self.publish(
                        "step_completed",
                        step_id=step_id,
                        final_answer=extracted_answer,
                        result=result,
                    )
                    break

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
                            if isinstance(top, dict) and isinstance(top.get("text"), str):
                                answer_text = top["text"]  # type: ignore[index]

                    if answer_text:
                        last_result_text = answer_text
                        final_answer_candidate = answer_text
                        if not (is_plan_step and plan_remaining):
                            if self.config.enable_memory:
                                self.memory_facade.add(
                                    answer_text,
                                    tier="long_term",
                                    metadata={"trace_id": trace_id, "step_id": step_id},
                                )
                            result.status = "success"
                            result.final_answer = answer_text
                            if self.config.enable_memory:
                                result.memory_used = self.memory_facade.recall_context(task)
                            self.publish(
                                "step_completed",
                                step_id=step_id,
                                final_answer=answer_text,
                                result=result,
                            )
                            break
                    elif not (is_plan_step and plan_remaining):
                        no_match_answer = (
                            "I could not find anything in memory that answers that."
                        )
                        if self.config.enable_memory:
                            self.memory_facade.add(
                                no_match_answer,
                                tier="long_term",
                                metadata={"trace_id": trace_id, "step_id": step_id},
                            )
                        result.status = "partial"
                        result.final_answer = no_match_answer
                        if self.config.enable_memory:
                            result.memory_used = self.memory_facade.recall_context(task)
                        self.publish(
                            "step_completed",
                            step_id=step_id,
                            final_answer=no_match_answer,
                            result=result,
                        )
                        break

                if (
                    plan_used
                    and not plan_remaining
                    and final_answer_candidate
                    and not result.final_answer
                ):
                    result.status = "success"
                    result.final_answer = final_answer_candidate
                    if self.config.enable_memory:
                        result.memory_used = self.memory_facade.recall_context(task)
                    self.publish(
                        "step_completed",
                        step_id=step_id,
                        final_answer=final_answer_candidate,
                        result=result,
                    )
                    break

                query = str(skill_output)

            if result.status == "failed":
                if final_answer_candidate:
                    result.status = "success" if not failure_occurred else "partial"
                    result.final_answer = final_answer_candidate
                    if self.config.enable_memory:
                        result.memory_used = self.memory_facade.recall_context(task)
                else:
                    result.status = "partial"
                    result.final_answer = None  # Don't echo the query
                    if self.config.enable_memory:
                        result.memory_used = self.memory_facade.recall_context(task)

            self.publish("task_finished", plan_id=plan_id, result=result)

        except Exception as e:
            logger.exception(f"Unexpected error during agent execution: {e}")
            result.status = "failed"
            result.final_answer = None
            result.metadata["error"] = str(e)
            # Publish event: task_failed
            self.publish("task_failed", plan_id=plan_id, error=str(e), result=result)

        finally:
            # Finalize result
            result.total_time_ms = (time.time() - start_time) * 1000
            result.metadata["steps_taken"] = len(step_results)
            result.metadata["plan_id"] = plan_id
            result.metadata["trace_id"] = trace_id

            self._log_feedback(task, result, skills_invoked, reflection_snapshot)
            self._maybe_run_continuous_learning()

        return result

    def _generate_plan(self, plan: AgentPlan, trace_id: str) -> List[Dict[str, Any]]:
        """Invoke the planner skill to populate the AgentPlan."""
        planner_skill = self.engine.skills.get("planner")
        if planner_skill is None:
            return []

        plan_logger = get_structured_logger(
            "skill.planner", trace_id=trace_id, step_id=f"{plan.plan_id}:plan", correlation_id=plan.plan_id
        )
        context = RunContext(
            trace_id=trace_id,
            correlation_id=plan.plan_id,
            memory_facade=self.memory_facade,
            logger=plan_logger,
            circuit_registry=self.circuit_registry,
        )
        if self.app_config and getattr(self.app_config, "memory", None):
            setattr(context, "memory_top_k", self.app_config.memory.top_k)

        planner_input = SkillInput(
            payload={"goal": plan.goal},
            trace_id=trace_id,
            correlation_id=plan.plan_id,
        )

        try:
            planner_output = safe_invoke(planner_skill, planner_input, context)
        except Exception as exc:
            logger.warning("Planner invocation failed: %s", exc)
            return []

        normalized = self._normalize_output(planner_output)
        if not isinstance(normalized, dict):
            return []

        raw_steps = normalized.get("plan") or normalized.get("results") or []
        if not isinstance(raw_steps, list):
            return []

        plan.version = getattr(planner_skill, "version", plan.version)

        for idx, raw_step in enumerate(raw_steps, start=1):
            if not isinstance(raw_step, dict):
                continue
            skill_name = raw_step.get("skill")
            if not skill_name:
                continue
            raw_input = raw_step.get("input") or raw_step.get("params") or {}
            if not isinstance(raw_input, dict):
                raw_input = {"text": str(raw_input)}
            plan.add_step(
                PlanStep(
                    step_id=f"{plan.plan_id}:plan_{idx}",
                    skill_name=skill_name,
                    input_data=deepcopy(raw_input),
                    description=raw_step.get("description", ""),
                )
            )

        return raw_steps

    def _prepare_plan_inputs(self, payload: Dict[str, Any], last_result: Optional[str]) -> Dict[str, Any]:
        """Clone plan payload and replace <LAST_RESULT> placeholders."""
        return self._replace_placeholders(deepcopy(payload), last_result)

    def _replace_placeholders(self, value: Any, last_result: Optional[str]) -> Any:
        if isinstance(value, dict):
            return {k: self._replace_placeholders(v, last_result) for k, v in value.items()}
        if isinstance(value, list):
            return [self._replace_placeholders(item, last_result) for item in value]
        if isinstance(value, str) and value == "<LAST_RESULT>":
            return last_result or ""
        return value

    def _coerce_skill_output(self, skill_output: Any, normalized: Optional[Dict[str, Any]]) -> SkillOutput | None:
        if isinstance(skill_output, SkillOutput):
            return skill_output
        if isinstance(skill_output, dict):
            return SkillOutput(payload=skill_output)
        if normalized is not None:
            return SkillOutput(payload=normalized)
        return None

    def _normalize_output(self, skill_output: Any) -> Optional[Dict[str, Any]]:
        if isinstance(skill_output, dict):
            return skill_output
        payload = getattr(skill_output, "payload", None)
        if isinstance(payload, dict):
            return payload
        if hasattr(skill_output, "to_dict"):
            try:
                maybe = skill_output.to_dict()
            except Exception:
                maybe = None
            if isinstance(maybe, dict):
                return maybe
        return None

    def _extract_answer_text(self, structured_obs: Optional[Dict[str, Any]]) -> Optional[str]:
        if not structured_obs:
            return None
        for key in ("final_answer", "summary", "answer", "output"):
            val = structured_obs.get(key)
            if isinstance(val, (str, int, float)):
                return str(val)
        return None

    def _log_feedback(
        self,
        query: str,
        result: AgentResult,
        skills_invoked: List[str],
        reflection_snapshot: Optional[Dict[str, Any]],
    ) -> None:
        logger_instance = getattr(self, "feedback_logger", None)
        if not logger_instance:
            return

        try:
            metrics: Dict[str, Any] = {
                "total_time_ms": result.total_time_ms,
                "steps_completed": result.steps_completed,
            }
            if reflection_snapshot:
                score = reflection_snapshot.get("reflection_score") or reflection_snapshot.get("score")
                if score is not None:
                    metrics["reflection_score"] = score

            metadata: Dict[str, Any] = {
                "plan_id": result.plan_id,
                "status": result.status,
                "plan_used": result.metadata.get("plan_used"),
                "plan": result.metadata.get("plan"),
                "planner_plan": result.metadata.get("planner_plan"),
                "step_results": [sr.to_dict() for sr in result.step_results],
                "final_answer": result.final_answer,
            }
            if reflection_snapshot:
                metadata["reflection_output"] = reflection_snapshot

            logger_instance.log(
                query=query,
                skills=skills_invoked,
                outcome=result.status,
                metrics=metrics,
                metadata=metadata,
            )
        except Exception as exc:
            logger.warning("Failed to log feedback: %s", exc)

    def _maybe_run_continuous_learning(self) -> None:
        """Trigger background learning when enough feedback logs exist."""
        if not self.continuous_learner:
            return

        threshold = max(1, self.config.continuous_learning_min_events)
        try:
            updated = self.continuous_learner.update(threshold)
            if updated:
                self.publish(
                    "continuous_learning_updated",
                    version=self.continuous_learner.get_version(),
                    threshold=threshold,
                )
        except Exception as exc:
            logger.warning("Continuous learning update failed: %s", exc)
