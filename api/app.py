from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables from .env file (for API keys)
load_dotenv()

from skill_engine.agent import Agent as RuntimeAgent

app = FastAPI(title="UltimateSkillOS API")


class QueryInput(BaseModel):
    query: str


@app.on_event("startup")
async def startup_event():
    # Initialize the runtime Agent and store it on app.state
    try:
        app.state.agent = RuntimeAgent.default()
    except Exception:
        # Fall back to from_env to be robust
        app.state.agent = RuntimeAgent.from_env()


@app.post("/chat")
async def chat(input: QueryInput, request: Request):
    agent: Optional[RuntimeAgent] = getattr(request.app.state, "agent", None)
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    try:
        result = agent.run(input.query)
        if hasattr(result, "to_dict"):
            return {"response": result.to_dict()}
        return {"response": str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    """Serve the main web UI"""
    webui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "webui", "index.html")
    if os.path.exists(webui_path):
        return FileResponse(webui_path)
    raise HTTPException(status_code=404, detail="Web UI not found")
