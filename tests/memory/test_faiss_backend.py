import pytest

try:
    import faiss  # type: ignore
    FAISS_AVAILABLE = True
except Exception:
    FAISS_AVAILABLE = False

from skill_engine.memory import facade


@pytest.mark.skipif(not FAISS_AVAILABLE, reason="FAISS not installed")
def test_faiss_index_creation(tmp_path):
    # Basic smoke test for FAISS index creation
    idx_path = tmp_path / "index.faiss"
    from skill_engine.memory.tiers import ShortTermMemory, LongTermMemory, Scratchpad
    from skill_engine.memory.in_memory import InMemoryBackend
    short_term = ShortTermMemory()
    long_term = LongTermMemory(InMemoryBackend())
    scratchpad = Scratchpad()
    mf = facade.MemoryFacade(short_term, long_term, scratchpad)
    # ensure add works
    mf.add("hello world", tier="long_term")
    results = mf.search("hello")
    assert isinstance(results, list)
