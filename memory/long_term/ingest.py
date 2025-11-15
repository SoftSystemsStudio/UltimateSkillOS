"""
Ingest files (md, txt) into the VectorStore.
This will:
 - read files
 - chunk them (simple sliding window)
 - embed chunks via EmbeddingClient
 - write embeddings + metadata into VectorStore
"""
from pathlib import Path
import re
from .embeddings import EmbeddingClient
from .vector_store import VectorStore

CHUNK_SIZE = 400  # characters
CHUNK_OVERLAP = 100

def _chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    text = re.sub(r"\s+", " ", text).strip()
    chunks = []
    i = 0
    n = len(text)
    while i < n:
        chunk = text[i:i+chunk_size]
        chunks.append(chunk.strip())
        i += chunk_size - overlap
    return chunks

def ingest_files(paths, model_name="all-MiniLM-L6-v2", dim=384, verbose=True):
    """
    paths: list of file paths (strings or Path)
    """
    emb_client = EmbeddingClient(model_name=model_name)
    store = VectorStore(dim=dim)
    files = [Path(p) for p in paths]
    metadatas = []
    all_texts = []
    for f in files:
        if not f.exists():
            if verbose:
                print("skipping (not found):", f)
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        chunks = _chunk_text(text)
        for i, c in enumerate(chunks):
            meta = {
                "source": str(f),
                "chunk_index": i,
                "chunk_text_preview": c[:200]
            }
            metadatas.append(meta)
            all_texts.append(c)
    if not all_texts:
        if verbose:
            print("No texts to ingest.")
        return 0
    # get embeddings (may be large)
    embeddings = emb_client.embed_texts(all_texts)
    # add to store (vector store will pad/truncate embeddings if necessary)
    store.add(embeddings, metadatas)
    if verbose:
        print(f"Ingested {len(all_texts)} chunks into vector store. Total vectors: {store.count()}")
    return len(all_texts)
