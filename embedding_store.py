class EmbeddingStore:
    def __init__(self):
        self.data = []
    def add(self, text):
        self.data.append(text)
    def get(self, idx):
        if 0 <= idx < len(self.data):
            return self.data[idx]
        return None
    def search(self, query):
        # Dummy search: return all stored texts
        return self.data
