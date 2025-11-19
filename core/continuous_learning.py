"""Continuous learning utilities for routing and skills."""

from __future__ import annotations

import logging
from pathlib import Path

from core.feedback_logger import FeedbackLogger
from core.ml_router import MLRouterModel
from core.optimizer import ParameterOptimizer

logger = logging.getLogger(__name__)


class ContinuousLearner:
    """Coordinates periodic router/model retraining from feedback logs."""

    def __init__(self, model_path: str = "data/router_model.pkl", min_events: int = 25):
        self.model = MLRouterModel(model_path)
        self.logger = FeedbackLogger()
        self.version = 1
        self.min_events = max(1, min_events)
        self._last_update_count = 0
        self._version_file = Path("data/model_version.txt")
        self._version_file.parent.mkdir(parents=True, exist_ok=True)

    def update(self, min_events: int | None = None) -> bool:
        """Retrain router model if enough new feedback entries accumulated."""

        threshold = max(1, min_events or self.min_events)
        logs = self.logger.get_logs()
        new_events = len(logs) - self._last_update_count
        if new_events < threshold:
            logger.debug(
                "Skipping continuous learning update (need %s more events)",
                threshold - new_events,
            )
            return False

        try:
            self.model.train(logs)
            optimizer = ParameterOptimizer()
            optimizer.optimize(logs)
        except Exception as exc:
            logger.warning("Continuous learning update failed: %s", exc)
            return False

        self.version += 1
        self._last_update_count = len(logs)
        self._version_file.write_text(f"Router_v{self.version}")
        logger.info("Continuous learner updated router model to version %s", self.version)
        return True

    def get_model(self):
        return self.model.model

    def get_version(self) -> int:
        return self.version
