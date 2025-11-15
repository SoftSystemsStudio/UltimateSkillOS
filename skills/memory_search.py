from skill_engine.base import SkillTool
from memory.long_term.vector_store import VectorStore
from memory.long_term.embeddings import EmbeddingClient

class MemorySearchTool(SkillTool):
    name = "memory_search"
    description = "Search long-term memory for semantically relevant chunks."

    def __init__(self):
        # dimension must match embedding model; default 384
        self.dim = 384
        self.store = VectorStore(dim=self.dim)
        self.emb = EmbeddingClient()

    def run(self, params):
        query = params.get("query") or params.get("text") or ""
        top_k = int(params.get("top_k", 5))
        if not query:
            return {"error": "Missing 'query' parameter"}

        q_emb = self.emb.embed_texts([query])[0]
        results = self.store.search(q_emb, top_k=top_k)
        return {"query": query, "results": results, "count": self.store.count()}
        
tool = MemorySearchTool()
