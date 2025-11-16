# skills/research.py
from skill_engine.base import BaseSkill
import os

# Optional: import Tavily only when used to avoid import errors on machines without it
try:
    from tavily import TavilyClient  # type: ignore
    TAVILY_AVAILABLE = True
except Exception:
    TAVILY_AVAILABLE = False

class ResearchSkill(BaseSkill):
    name = "research"
    description = "Performs web-style research using Tavily (if configured)."
    keywords = ["research", "find", "look up", "what is", "who is", "why is"]

    def run(self, params: dict):
        query = params.get("query") or params.get("text") or ""
        if not query:
            return {"error": "Missing 'query' parameter"}

        # Use Tavily if available
        if TAVILY_AVAILABLE:
            api_key = os.getenv("TAVILY_API_KEY")
            if not api_key:
                return {"error": "TAVILY_API_KEY not set in environment"}
            client = TavilyClient(api_key=api_key)
            # call a safe simple search path; adapt if your client API differs
            try:
                resp = client.search(query=query)
                return {"answer": resp, "sources": getattr(resp, "sources", []), "confidence": 0.75}
            except Exception as e:
                return {"error": f"Tavily error: {e}"}
        else:
            # Offline fallback stub
            return {"answer": f"Offline-mode research fallback for: {query}", "sources": [], "confidence": 0.4}
