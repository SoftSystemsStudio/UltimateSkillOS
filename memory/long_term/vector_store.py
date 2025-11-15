"""
Lightweight FAISS-backed vector store with JSON metadata.
Stores embeddings in an index and metadata in a JSON list.
"""
import os
import json
import faiss
import numpy as np
from pathlib import Path

DEFAULT_DIR = Path("memory/long_term_store")
DEFAULT_DIR.mkdir(parents=True, exist_ok=True)

class VectorStore:
    def __init__(self, dim=384, index_path=DEFAULT_DIR / "faiss.index", meta_path=DEFAULT_DIR / "meta.json"):
        self.dim = dim
        self.index_path = Path(index_path)
        self.meta_path = Path(meta_path)
        self._init_index()

    def _init_index(self):
        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            # load metadata
            self.meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
        else:
            # use IndexFlatIP on normalized vectors for simple similarity
            self.index = faiss.IndexFlatIP(self.dim)
            self.meta = []
            self._save()

    def _save(self):
        faiss.write_index(self.index, str(self.index_path))
        self.meta_path.write_text(json.dumps(self.meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def _ensure_dim(self, emb):
        arr = np.array(emb, dtype="float32")
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        if arr.shape[1] != self.dim:
            # if smaller, pad with zeros; if larger, truncate
            new = np.zeros((arr.shape[0], self.dim), dtype="float32")
            new[:, :min(self.dim, arr.shape[1])] = arr[:, :self.dim]
            arr = new
        return arr

    def add(self, embeddings, metadatas):
        """
        embeddings: list[list[float]]
        metadatas: list[dict]  (same length)
        """
        if len(embeddings) != len(metadatas):
            raise ValueError("embeddings and metadatas length mismatch")
        arr = self._ensure_dim(embeddings)
        # normalize for cosine using inner product search
        faiss.normalize_L2(arr)
        self.index.add(arr)
        start_id = len(self.meta)
        # append metadata with assigned id
        for i, m in enumerate(metadatas):
            m_copy = dict(m)
            m_copy["_id"] = start_id + i
            self.meta.append(m_copy)
        self._save()

    def search(self, query_embedding, top_k=5):
        q = self._ensure_dim(query_embedding)
        faiss.normalize_L2(q)
        D, I = self.index.search(q, top_k)
        results = []
        for dist, idx in zip(D[0], I[0]):
            if idx < 0 or idx >= len(self.meta):
                continue
            meta = dict(self.meta[idx])
            results.append({"score": float(dist), "meta": meta})
        return results

    def count(self):
        return len(self.meta)
