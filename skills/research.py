# skills/research.py
from skill_engine.base import BaseSkill
import os

# Optional: import Tavily only when used to avoid import errors on machines without it
try:
    from tavily import TavilyClient  # type: ignore
    TAVILY_AVAILABLE = True
except Exception:
    TAVILY_AVAILABLE = False

from pydantic import BaseModel
from skill_engine.domain import SkillInput, SkillOutput

class ResearchInput(BaseModel):
    query: str = ""
    text: str = ""

class ResearchOutput(BaseModel):
    answer: str = ""
    sources: list = []
    confidence: float = 0.0
    error: str = ""

class ResearchSkill(BaseSkill):
    name = "research"
    version = "1.1.0"
    description = "Performs web-style research using Tavily (if configured)."
    keywords = ["research", "find", "look up", "what is", "who is", "why is"]
    input_schema = ResearchInput
    output_schema = ResearchOutput
    sla = None

    def invoke(self, input_data: SkillInput, context) -> SkillOutput:
        query = input_data.payload.get("query") or input_data.payload.get("text") or ""
        if not query:
            return {"error": "Missing 'query' parameter"}
        if TAVILY_AVAILABLE:
            api_key = os.getenv("TAVILY_API_KEY")
            if not api_key:
                return {"error": "TAVILY_API_KEY not set in environment"}
            client = TavilyClient(api_key=api_key)
            try:
                resp = client.search(query=query)
                return {"answer": str(resp), "sources": getattr(resp, "sources", []), "confidence": 0.75}
            except Exception as e:
                return {"error": f"Tavily error: {e}"}
        else:
            return {"answer": f"Offline-mode research fallback for: {query}", "sources": [], "confidence": 0.4}
