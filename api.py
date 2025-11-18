from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

# Use the higher-level Agent implementation (skill_engine.agent)
from skill_engine.agent import Agent as RuntimeAgent

from fastapi.staticfiles import StaticFiles

app = FastAPI()


@app.on_event("startup")
async def startup_event():
    """Initialize agent on startup to avoid side effects at import time."""
    try:
        app.state.agent = RuntimeAgent.default()
    except Exception:
        # Fallback to from_env if default() fails for some setups
        app.state.agent = RuntimeAgent.from_env()


# Serve static files from the webui directory
app.mount("/", StaticFiles(directory="webui", html=True), name="web")


class QueryInput(BaseModel):
    query: str


@app.post("/chat")
async def chat(input: QueryInput, request: Request):
    agent: Optional[RuntimeAgent] = getattr(request.app.state, "agent", None)
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    try:
        result = agent.run(input.query)
        # Agent.run returns an AgentResult dataclass; convert to dict for JSON
        if hasattr(result, "to_dict"):
            return {"response": result.to_dict()}
        return {"response": str(result)}
    except Exception as e:
        # Return an HTTP 500 with the error message
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}