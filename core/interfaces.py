from abc import ABC, abstractmethod
from typing import Any, Dict

class Planner(ABC):
    """
    Abstract base class for planning modules.
    Implementations should provide a plan method that returns a sequence of steps or actions.
    """
    @abstractmethod
    def plan(self, goal: str, context: Dict[str, Any]) -> Any:
        pass

class Evaluator(ABC):
    """
    Abstract base class for self-evaluation components.
    Implementations should provide an evaluate method that returns a score or feedback.
    """
    @abstractmethod
    def evaluate(self, result: Any, context: Dict[str, Any]) -> Any:
        pass
