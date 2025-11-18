from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from skill_engine.agent import Agent


class RunRequest(BaseModel):
    task: str
    options: Optional[Dict[str, Any]] = {}


app = FastAPI(title="UltimateSkillOS API")


@app.on_event("startup")
async def create_agent() -> None:
    # Lazily construct an Agent on startup. This avoids side-effects at import time.
    try:
        agent = Agent.from_env()
    except Exception as e:
        # If the Agent cannot be constructed, keep app running but record the error.
        # The endpoint will return 503 if agent is not available.
        app.state._agent_error = str(e)
        app.state.agent = None
        return
    app.state.agent = agent
    app.state._agent_error = None


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
