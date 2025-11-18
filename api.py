from fastapi import FastAPI
from pydantic import BaseModel
from skill_engine.domain import Agent  # your custom agent module
from core.router import Router
from skill_engine.memory.in_memory import InMemoryBackend
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Initialize required dependencies
router = Router()
memory = InMemoryBackend()
agent = Agent(router=router, memory=memory)

# Serve static files from the webui directory
app.mount("/", StaticFiles(directory="webui", html=True), name="web")

class QueryInput(BaseModel):
    query: str

@app.post("/chat")
async def chat(input: QueryInput):
    response = agent.run(input.query)
    return {"response": response}