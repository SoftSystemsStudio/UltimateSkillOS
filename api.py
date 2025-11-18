from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Use the higher-level Agent implementation (skill_engine.agent)
from skill_engine.agent import Agent as RuntimeAgent

from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Create a runtime-ready Agent using defaults (loads config from env/files)
# This ensures correct initialization of router, engine, memory, etc.
try:
    agent = RuntimeAgent.default()
except Exception:
    # Fallback to from_env if default() fails for some setups
    agent = RuntimeAgent.from_env()

# Serve static files from the webui directory
app.mount("/", StaticFiles(directory="webui", html=True), name="web")


class QueryInput(BaseModel):
    query: str


@app.post("/chat")
async def chat(input: QueryInput):
    try:
        result = agent.run(input.query)
        # Agent.run returns an AgentResult dataclass; convert to dict for JSON
        if hasattr(result, "to_dict"):
            return {"response": result.to_dict()}
        return {"response": str(result)}
    except Exception as e:
        # Return an HTTP 500 with the error message
        raise HTTPException(status_code=500, detail=str(e))