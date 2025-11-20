import asyncio
import logging
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from core.continuous_learning import ContinuousLearningRunner
from skill_engine.agent import Agent as RuntimeAgent

# Load environment variables from .env file (for API keys)
load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(title="UltimateSkillOS API")


class QueryInput(BaseModel):
    query: str


class FeedbackInput(BaseModel):
    plan_id: str
    rating: int = Field(..., ge=-1, le=1, description="-1=bad, 0=neutral, 1=good")
    notes: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    """Initialize the runtime agent and background learning loop."""
    try:
        agent = RuntimeAgent.default()
    except Exception:
        # Fall back to from_env to be robust
        agent = RuntimeAgent.from_env()

    app.state.agent = agent
    app.state.learning_runner = None
    await _maybe_start_learning_loop(app)


@app.on_event("shutdown")
async def shutdown_event():
    await _maybe_stop_learning_loop(app)


@app.post("/chat")
async def chat(input: QueryInput, request: Request):
    agent: Optional[RuntimeAgent] = getattr(request.app.state, "agent", None)
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        result = agent.run(input.query)
        # Log the full structured result for troubleshooting while keeping the response minimal
        if hasattr(result, "to_dict"):
            logger.info("Agent result: %s", result.to_dict())
        else:
            logger.info("Agent result (unstructured): %s", result)

        final_answer = getattr(result, "final_answer", None)

        if isinstance(final_answer, str) and not final_answer.strip():
            final_answer = None

        # Return only the final_answer for clean client-side consumption
        return {"final_answer": final_answer}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/feedback")
async def submit_feedback(input: FeedbackInput, request: Request):
    agent: Optional[RuntimeAgent] = getattr(request.app.state, "agent", None)
    if agent is None or not hasattr(agent, "feedback_logger"):
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        agent.feedback_logger.log(
            query=f"user_feedback:{input.plan_id}",
            skills=[],
            outcome="user_feedback",
            metrics={"rating": input.rating},
            metadata={"plan_id": input.plan_id, "notes": input.notes},
        )
        # Opportunistically trigger continuous learning if enabled
        should_trigger = (
            getattr(agent.config, "continuous_learning_enabled", False)
            and getattr(agent.config, "continuous_learning_trigger_on_feedback", True)
            and getattr(agent, "continuous_learner", None) is not None
        )
        if should_trigger:
            runner: Optional[ContinuousLearningRunner] = getattr(
                request.app.state, "learning_runner", None
            )
            if runner is not None:
                await runner.trigger_once()
            else:
                await asyncio.to_thread(agent._maybe_run_continuous_learning)
        return {"status": "recorded"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    """Serve the main web UI."""
    webui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "webui", "index.html")
    if os.path.exists(webui_path):
        return FileResponse(webui_path)
    raise HTTPException(status_code=404, detail="Web UI not found")


@app.get("/learning/status")
async def learning_status(request: Request):
    agent: Optional[RuntimeAgent] = getattr(request.app.state, "agent", None)
    runner: Optional[ContinuousLearningRunner] = getattr(request.app.state, "learning_runner", None)
    config = getattr(agent, "config", None)
    learner = getattr(agent, "continuous_learner", None) if agent else None

    enabled = bool(config and getattr(config, "continuous_learning_enabled", False))
    interval = int(getattr(config, "continuous_learning_background_interval_seconds", 0)) if config else 0
    trigger_on_feedback = bool(
        config and getattr(config, "continuous_learning_trigger_on_feedback", True)
    )

    return {
        "agent_initialized": agent is not None,
        "continuous_learning_enabled": enabled,
        "learning_available": learner is not None,
        "background_interval_seconds": interval,
        "trigger_on_feedback": trigger_on_feedback,
        "runner": runner.snapshot() if runner else None,
        "learner": learner.stats() if learner else None,
    }


async def _maybe_start_learning_loop(fastapi_app: FastAPI) -> None:
    agent: Optional[RuntimeAgent] = getattr(fastapi_app.state, "agent", None)
    if agent is None:
        return

    if getattr(agent, "continuous_learner", None) is None:
        logger.info("Continuous learning loop not started (learner unavailable)")
        return

    config = getattr(agent, "config", None)
    if not config or not getattr(config, "continuous_learning_enabled", False):
        logger.info("Continuous learning loop not started (feature disabled)")
        return

    interval = getattr(config, "continuous_learning_background_interval_seconds", 0)
    if interval <= 0:
        logger.info("Continuous learning loop not started (interval <= 0)")
        return

    run_immediately = getattr(config, "continuous_learning_background_run_immediately", True)

    runner = ContinuousLearningRunner(
        tick=agent._maybe_run_continuous_learning,
        interval_seconds=interval,
        run_immediately=run_immediately,
    )
    runner.start()
    fastapi_app.state.learning_runner = runner
    logger.info(
        "Continuous learning loop running every %ss (immediate=%s)", interval, run_immediately
    )


async def _maybe_stop_learning_loop(fastapi_app: FastAPI) -> None:
    runner: Optional[ContinuousLearningRunner] = getattr(fastapi_app.state, "learning_runner", None)
    if runner is None:
        return

    await runner.stop()
    fastapi_app.state.learning_runner = None
