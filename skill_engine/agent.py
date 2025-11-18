# skill_engine/agent.py

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from config import AgentConfig, AppConfig, load_config
from skill_engine.domain import AgentPlan, AgentResult, PlanStep, SkillInput, StepResult
from skill_engine.engine import SkillEngine
from skill_engine.memory.manager import get_memory_manager
from skill_engine.registry import get_global_registry, SkillRegistry
from skill_engine.skill_base import RunContext
from skill_engine.memory.facade import MemoryFacade
from core.router import Router
from core.logging import get_logger as get_structured_logger
from skill_engine.skill_base import safe_invoke
from skill_engine.resilience import create_registry
import os

logger = logging.getLogger(__name__)


class Agent:
    def __init__(
        self,
        config: AgentConfig,
        registry: SkillRegistry | None = None,
        memory_facade: MemoryFacade | None = None,
    ) -> None:
        """
        Initialize Agent with explicit dependency injection.

        Args:
            config: AgentConfig with execution parameters and routing mode.
            registry: SkillRegistry for skill lookup (uses global if None).
            memory_facade: MemoryFacade for memory operations (creates new if None).
        """
        self.config = config
        self.registry = registry or get_global_registry()
        # get_memory_manager() returns MemoryFacade directly
        self.memory_facade = memory_facade or get_memory_manager()

        # Create a circuit-breaker registry for this Agent instance.
        # Uses SKILLOS_CIRCUIT_REDIS_URL if provided; avoids globals.
        redis_url = os.environ.get("SKILLOS_CIRCUIT_REDIS_URL")
        try:
            self.circuit_registry = create_registry(redis_url)
        except Exception:
            self.circuit_registry = create_registry(None)

        # Initialize engine and router
        self.engine = SkillEngine()

        # Create router with config's routing settings
        # Note: config.routing is already a RoutingConfig from config module
        try:
            self.router = Router(config.routing)
        except Exception as e:
            logger.warning(f"Failed to initialize router with config: {e}, using default")
            self.router = Router()

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

        return Agent(config=app_config.agent)

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
        return Agent(config=agent_config)

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

                # Create execution context with memory facade and structured logger
                step_logger = get_structured_logger(f"skill.{skill_name}", trace_id=trace_id, step_id=step_id, correlation_id=plan_id)
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

                    # Lookup concrete skill object from engine
                    skill_obj = self.engine.skills.get(skill_name)
                    if skill_obj is None:
                        raise RuntimeError(f"Skill '{skill_name}' not found in engine")

                    skill_output = safe_invoke(skill_obj, skill_input, context)

                    if verbose:
                        logger.info(f"Skill '{skill_name}' completed")

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

                # Memory write: store useful outcomes (if enabled)
                if self.config.enable_memory and structured_obs is not None:
                    try:
                        if "summary" in structured_obs:
                            self.memory_facade.add(
                                str(structured_obs["summary"]), tier="long_term", metadata={"trace_id": trace_id, "step_id": step_id}
                            )
                        elif "answer" in structured_obs:
                            self.memory_facade.add(
                                str(structured_obs["answer"]), tier="long_term", metadata={"trace_id": trace_id, "step_id": step_id}
                            )
                        else:
                            text_val = params.get("text")
                            if isinstance(text_val, str):
                                self.memory_facade.add(text_val, tier="long_term", metadata={"trace_id": trace_id, "step_id": step_id})
                    except Exception as e:
                        logger.warning(f"Failed to write to memory: {e}")

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
                    if self.config.enable_memory:
                        result.memory_used = self.memory_facade.recall_context(task)
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
                        if self.config.enable_memory:
                            self.memory_facade.add(answer_text, tier="long_term", metadata={"trace_id": trace_id, "step_id": step_id})
                        result.status = "success"
                        result.final_answer = answer_text
                        if self.config.enable_memory:
                            result.memory_used = self.memory_facade.recall_context(task)
                        break

                    no_match_answer = (
                        "I could not find anything in memory that answers that."
                    )
                    if self.config.enable_memory:
                        self.memory_facade.add(no_match_answer, tier="long_term", metadata={"trace_id": trace_id, "step_id": step_id})
                    result.status = "partial"
                    result.final_answer = no_match_answer
                    if self.config.enable_memory:
                        result.memory_used = self.memory_facade.recall_context(task)
                    break

                # Default: propagate observation into next query
                query = str(skill_output)

            # If we completed all steps without terminating
            if result.status == "failed":
                result.status = "partial"
                result.final_answer = query
                if self.config.enable_memory:
                    result.memory_used = self.memory_facade.recall_context(task)

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
