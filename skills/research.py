from tavily import TavilyClient

class ResearchSkill:
    name = "research"
    description = "AI-augmented research skill using Tavily search."

    def __init__(self):
        self.client = TavilyClient()

    def run(self, params):
        query = params.get("query", "")
        if not query:
            return {"error": "Missing 'query' parameter"}

        # Perform Tavily search
        response = self.client.search(query=query, include_answer=True)

        # Robust extraction
        results = response.get("results", [])

        key_points = []
        for r in results:
            text = (
                r.get("snippet")
                or r.get("content")
                or r.get("text")
                or ""
            )
            if text:
                key_points.append(text.strip())

        return {
            "answer": response.get("answer", "No answer returned."),
            "sources": [r.get("url") for r in results if r.get("url")],
            "key_points": key_points,
            "confidence": response.get("confidence", 0.75),
        }

tool = ResearchSkill()
