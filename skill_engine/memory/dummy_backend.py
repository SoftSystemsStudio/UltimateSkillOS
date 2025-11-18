from skill_engine.memory.base import MemoryBackend

class DummyMemoryBackend(MemoryBackend):
    def add(self, text: str, **kwargs):
        pass
    def search(self, query: str, **kwargs):
        return [{"text": "dummy result"}]
    def stats(self):
        return {"dummy": True}
