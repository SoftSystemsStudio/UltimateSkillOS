"""Continuous learning utilities for routing and skills."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Callable, Dict, Optional

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

    def stats(self) -> Dict[str, int]:
        """Return basic counters for monitoring."""

        logs = self.logger.get_logs()
        total_events = len(logs)
        new_events = total_events - self._last_update_count
        return {
            "version": self.version,
            "min_events": self.min_events,
            "total_events": total_events,
            "events_since_update": max(0, new_events),
        }


class ContinuousLearningRunner:
    """Async helper that periodically triggers continuous learning updates."""

    def __init__(
        self,
        tick: Callable[[], None],
        interval_seconds: float,
        *,
        run_immediately: bool = True,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")

        self._tick = tick
        self._interval = float(interval_seconds)
        self._run_immediately = run_immediately
        self._task: Optional[asyncio.Task] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._stats: Dict[str, Optional[float | int | str]] = {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "last_started_at": None,
            "last_completed_at": None,
            "last_error": None,
        }

    def start(self) -> None:
        """Start the background loop if not already running."""

        if self._task is not None:
            return

        loop = asyncio.get_running_loop()
        self._stop_event = asyncio.Event()
        self._task = loop.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the background loop and wait for cleanup."""

        if self._task is None or self._stop_event is None:
            return

        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None
            self._stop_event = None

    async def trigger_once(self) -> None:
        """Run a single learning tick immediately in a worker thread."""

        await self._invoke_tick()

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def snapshot(self) -> Dict[str, Optional[float | int | str | bool]]:
        """Expose internal counters for status endpoints."""

        return {
            **self._stats,
            "interval_seconds": self._interval,
            "run_immediately": self._run_immediately,
            "running": self.is_running(),
        }

    async def _run_loop(self) -> None:
        logger.info(
            "Continuous learning loop started (interval=%ss, immediate=%s)",
            self._interval,
            self._run_immediately,
        )
        try:
            if self._run_immediately:
                await self._invoke_tick()

            assert self._stop_event is not None
            while not self._stop_event.is_set():
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=self._interval)
                    break
                except asyncio.TimeoutError:
                    await self._invoke_tick()
        except asyncio.CancelledError:
            logger.debug("Continuous learning loop cancelled")
            raise
        finally:
            logger.info("Continuous learning loop stopped")

    async def _invoke_tick(self) -> None:
        self._stats["last_started_at"] = time.time()
        try:
            await asyncio.to_thread(self._tick)
            self._stats["successful_runs"] = int(self._stats["successful_runs"]) + 1
            self._stats["last_error"] = None
        except Exception as exc:  # pragma: no cover - defensive logging
            self._stats["failed_runs"] = int(self._stats["failed_runs"]) + 1
            self._stats["last_error"] = str(exc)
            logger.warning("Continuous learning tick failed: %s", exc)
        finally:
            self._stats["total_runs"] = int(self._stats["total_runs"]) + 1
            self._stats["last_completed_at"] = time.time()
