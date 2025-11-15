import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

class EmbeddingStore:
    def __init__(self, index_path="memory/faiss.index"):
        self.index_path = index_path
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        # FAISS index (384 dims for MiniLM)
        self.index = faiss.IndexFlatL2(384)

        # Store raw texts alongside vectors
        self.texts = []

        # Load if exists
        if os.path.exists(index_path):
            self.load()

    def embed(self, text: str) -> np.ndarray:
        return self.model.encode([text])[0]

    def add(self, text: str):
        vector = self.embed(text).astype(np.float32).reshape(1, -1)
        self.index.add(vector)
        self.texts.append(text)
        self.save()

    def search(self, query: str, k: int = 5):
        if self.index.ntotal == 0:
            return []

        vector = self.embed(query).astype(np.float32).reshape(1, -1)
        distances, indices = self.index.search(vector, k)

        results = []
        for i in indices[0]:
            if i < len(self.texts):
                results.append(self.texts[i])

        return results

    def save(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.index_path + ".txt", "w") as f:
            for t in self.texts:
                f.write(t + "\n")

    def load(self):
        self.index = faiss.read_index(self.index_path)
        txt_path = self.index_path + ".txt"
        if os.path.exists(txt_path):
            with open(txt_path, "r") as f:
                self.texts = f.read().splitlines()
