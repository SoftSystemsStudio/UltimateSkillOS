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
    mf = facade.MemoryFacade()
    # ensure add works
    mf.add("hello world", tier="long_term")
    results = mf.search("hello")
    assert isinstance(results, list)
