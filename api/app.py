import logging
import os
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env file (for API keys)
load_dotenv()

from skill_engine.agent import Agent as RuntimeAgent

logger = logging.getLogger(__name__)

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
        # Log the full structured result for troubleshooting while keeping the response minimal
        if hasattr(result, "to_dict"):
            logger.info("Agent result: %s", result.to_dict())
        else:
            logger.info("Agent result (unstructured): %s", result)

        final_answer = getattr(result, "final_answer", None)
        if isinstance(final_answer, str) and final_answer.strip():
            return {"response": final_answer.strip()}

        # Fallback to a simple status message if we didn't get a final answer
        return {"response": "I wasn't able to generate an answer. Please try rephrasing your question."}
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
