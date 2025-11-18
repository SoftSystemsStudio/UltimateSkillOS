from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from skill_engine.agent import Agent


class RunRequest(BaseModel):
    task: str
    options: Optional[Dict[str, Any]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: lazily construct an Agent. This avoids side-effects at import time.
    try:
        agent = Agent.from_env()
        app.state._agent_error = None
    except Exception as e:
        # If the Agent cannot be constructed, keep app running but record the error.
        # The endpoint will return 503 if agent is not available.
        app.state.agent = None
        app.state._agent_error = str(e)
        yield
        return
    app.state.agent = agent
    yield
    # Cleanup: no shutdown logic needed


app = FastAPI(title="UltimateSkillOS API", lifespan=lifespan)


@app.post("/run")
async def run_task(req: RunRequest, request: Request):
    """Run a task through the Agent and return a structured AgentResult (JSON).

    Request schema:
    {
      "task": "string",
      "options": { "max_steps": 4, "trace": true }
    }
    """
    agent: Agent | None = getattr(request.app.state, "agent", None)
    err = getattr(request.app.state, "_agent_error", None)
    if agent is None:
        raise HTTPException(status_code=503, detail={"error": "Agent not available", "reason": err})

    task = req.task
    options = req.options or {}
    max_steps = options.get("max_steps")
    trace = options.get("trace", False)

    try:
        result = agent.run(task, max_steps=max_steps, verbose=bool(trace))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})

    # AgentResult.to_dict() returns JSON-serializable structure
    return result.to_dict()
