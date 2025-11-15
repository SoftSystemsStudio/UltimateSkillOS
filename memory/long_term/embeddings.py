"""
Embedding client wrapper using sentence-transformers with a safe fallback.
"""
import logging

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
except Exception as e:
    SentenceTransformer = None
    np = None
    logging.warn("sentence-transformers not available; embedding fallback will be used.")

class EmbeddingClient:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model_name = model_name
        if SentenceTransformer is not None:
            self.model = SentenceTransformer(model_name)
        else:
            self.model = None

    def embed_texts(self, texts):
        """
        texts: list[str]
        returns: list[list[float]] embeddings
        """
        if self.model is None:
            # cheap fallback: map tokens -> ascii sums (NOT semantic)
            out = []
            for t in texts:
                vec = [float(sum(ord(ch) for ch in t[i:i+4])) for i in range(0, min(64, len(t)), 4)]
                # pad/truncate to fixed dim 16
                vec = (vec + [0.0]*16)[:16]
                out.append(vec)
            return out

        # cast to list
        embs = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        # ensure python list output
        return [e.tolist() for e in embs]
