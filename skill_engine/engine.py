# skill_engine/engine.py

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Any, Callable, Dict, List, Mapping

import skills
from skill_engine.base import BaseSkill

logger = logging.getLogger(__name__)


class SkillEngine:
    """
    Dynamic skill loader and dispatcher.

    - Discovers all modules under the `skills` package.
    - Registers all subclasses of BaseSkill with a non-empty `name`.
    - Supports dynamic factory loading for planners and memory backends.
    """

    def __init__(self, planner_factory=None, memory_factory=None) -> None:
        self.skills: Dict[str, BaseSkill] = self.load_all_skills()
        self.planner_factory = planner_factory
        self.memory_factory = memory_factory
        self.task_finished_observer = TaskFinishedObserver()

    def load_all_skills(self) -> Dict[str, BaseSkill]:
        loaded: Dict[str, BaseSkill] = {}

        for module_info in pkgutil.iter_modules(skills.__path__):
            module_name = f"skills.{module_info.name}"
            try:
                module = importlib.import_module(module_name)
            except Exception as e:
                logger.exception("[Engine] Failed to import %s: %s", module_name, e)
                continue

            for attr in dir(module):
                obj = getattr(module, attr)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BaseSkill)
                    and obj is not BaseSkill
                ):
                    try:
                        inst: BaseSkill = obj()
                        if inst.name:
                            loaded[inst.name] = inst
                    except Exception as e:
                        logger.exception(
                            "[Engine] Failed to instantiate skill %s.%s: %s",
                            module_name,
                            attr,
                            e,
                        )
                        continue

        logger.info("[Engine] Registered skills: %s", list(loaded.keys()))
        return loaded

    def run(self, skill_name: str, params: Mapping[str, Any]) -> Any:
        """
        Execute a skill by name with the given parameter mapping.
        """
        skill = self.skills.get(skill_name)
        if skill is None:
            return {"error": f"Skill '{skill_name}' not found"}

        # Ensure we pass a plain dict to the skill implementation.
        return skill.run(dict(params))

    def get_planner(self, planner_type: str = "default"):
        """Get a planner instance from the factory."""
        if self.planner_factory:
            return self.planner_factory(planner_type)
        return None

    def get_memory_backend(self, backend_type: str = "default"):
        """Get a memory backend instance from the factory."""
        if self.memory_factory:
            return self.memory_factory(backend_type)
        return None

    def execute_plan(self, plan: AgentPlan) -> AgentResult:
        """
        Execute a plan by invoking skills sequentially.

        Args:
            plan (AgentPlan): The plan to execute.

        Returns:
            AgentResult: The result of the plan execution.
        """
        step_results = []
        total_time = 0.0

        for step in plan.steps:
            start_time = datetime.utcnow()
            try:
                # Execute the skill
                skill_output = self.run(step.skill_name, step.input_data)

                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                step_results.append(StepResult(
                    step_id=step.step_id,
                    success=True,
                    output=SkillOutput(payload=skill_output),
                    execution_time_ms=execution_time
                ))
                total_time += execution_time

                # Check for early termination
                if "final_answer" in skill_output:
                    return AgentResult(
                        plan_id=plan.plan_id,
                        status="success",
                        final_answer=skill_output["final_answer"],
                        step_results=step_results,
                        total_time_ms=total_time,
                        steps_completed=len(step_results)
                    )

            except Exception as e:
                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                step_results.append(StepResult(
                    step_id=step.step_id,
                    success=False,
                    error=str(e),
                    execution_time_ms=execution_time
                ))
                total_time += execution_time

        # Check if max_steps is reached without a final answer
        if not any(sr.success for sr in step_results):
            return AgentResult(
                plan_id=plan.plan_id,
                status="failed",
                final_answer="Unable to complete the task within the given steps.",
                step_results=step_results,
                total_time_ms=total_time,
                steps_completed=sum(1 for sr in step_results if sr.success)
            )

        # Determine overall status
        status = "success" if all(sr.success for sr in step_results) else "partial"
        return AgentResult(
            plan_id=plan.plan_id,
            status=status,
            final_answer=None,
            step_results=step_results,
            total_time_ms=total_time,
            steps_completed=sum(1 for sr in step_results if sr.success)
        )

    def set_planning_strategy(self, strategy: str, strategy_impl: Any) -> None:
        """
        Set a planning strategy dynamically.

        Args:
            strategy (str): The name of the strategy.
            strategy_impl (Any): The implementation of the strategy.
        """
        if not hasattr(self, "planning_strategies"):
            self.planning_strategies = {}
        self.planning_strategies[strategy] = strategy_impl

    def get_planning_strategy(self, strategy: str) -> Any:
        """
        Retrieve a planning strategy by name.

        Args:
            strategy (str): The name of the strategy.

        Returns:
            Any: The implementation of the strategy.
        """
        if hasattr(self, "planning_strategies") and strategy in self.planning_strategies:
            return self.planning_strategies[strategy]
        raise ValueError(f"Planning strategy '{strategy}' not found.")

class TaskFinishedObserver:
    """
    Observer for task_finished events to trigger evaluation.
    """
    def __init__(self):
        self.subscribers: List[Callable[[AgentResult], None]] = []

    def subscribe(self, callback: Callable[[AgentResult], None]) -> None:
        """Subscribe to the task_finished event."""
        self.subscribers.append(callback)

    def notify(self, result: AgentResult) -> None:
        """Notify all subscribers with the task result."""
        for subscriber in self.subscribers:
            subscriber(result)

# Example usage in the Agent loop
class Agent:
    def __init__(self):
        self.task_finished_observer = TaskFinishedObserver()

    def execute_plan(self, plan: AgentPlan) -> AgentResult:
        result = super().execute_plan(plan)
        self.task_finished_observer.notify(result)
        return result
