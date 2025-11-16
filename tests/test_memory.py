from embedding_store import EmbeddingStore

mem = EmbeddingStore()

mem.add("Agents help automate repetitive workflows.")
mem.add("Vector databases store embeddings for semantic search.")
mem.add("Python is great for building AI automation systems.")

print("Search for 'automation':")
print(mem.search("automation"))
