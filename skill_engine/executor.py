"""
Task executor - coordinates routing, skills, and memory for agent tasks.
"""

from skill_engine.agent import Agent
from config import AgentConfig, AppConfig, load_config

class TaskExecutor:
    """
    Unified agent executor – uses Agent loop for both single-step and multi-step tasks.
    """

    def __init__(self, config: AgentConfig = None):
        if config is None:
            app_config = load_config()
            config = app_config.agent
        else:
            app_config = AppConfig()
            app_config.agent = config
        self.agent = Agent(config=config, app_config=app_config)

    def run(self, text: str, max_steps: int = 1):
        """
        Run a task using the unified Agent loop.
        """
        result = self.agent.run(text, max_steps=max_steps)
        return {
            "input": text,
            "result": result.final_answer,
            "status": result.status,
            "steps_taken": result.metadata.get("steps_taken"),
            "trace_id": result.metadata.get("trace_id"),
            "plan_id": result.metadata.get("plan_id"),
            "memory_used": getattr(result, "memory_used", None)
        }
