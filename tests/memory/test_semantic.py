import pytest


def _default_embed_fn():
    try:
        from chromadb.utils import embedding_functions

        return embedding_functions.DefaultEmbeddingFunction()
    except Exception:
        return None


def test_semantic_memory_round_trip(tmp_path, monkeypatch):
    """Non-live: uses Chroma's bundled DefaultEmbeddingFunction (ONNX, no download)."""
    embed_fn = _default_embed_fn()
    if embed_fn is None:
        pytest.skip("chromadb DefaultEmbeddingFunction unavailable")

    from voss_runtime.memory.semantic import SemanticMemory

    monkeypatch.setattr(
        SemanticMemory, "_embedding_function", lambda self: embed_fn
    )

    try:
        mem = SemanticMemory(persist_dir=str(tmp_path / "chroma"))
    except Exception as e:
        pytest.skip(f"SemanticMemory init failed (likely needs network): {e}")

    mem.add("python is a programming language used by developers")
    mem.add("paris is the capital of france")
    results = mem.retrieve("what language do programmers use?", top_k=2)
    assert results, "expected at least one result"
    assert "python" in results[0].lower()


@pytest.mark.live
def test_semantic_memory_live_local_fallback(tmp_path):
    from voss_runtime.memory.semantic import SemanticMemory

    mem = SemanticMemory(
        persist_dir=str(tmp_path / "chroma"),
        model="sentence-transformers/all-MiniLM-L6-v2",
    )
    mem.add("python is a programming language")
    mem.add("paris is the capital of france")
    results = mem.retrieve("what language do programmers use?", top_k=2)
    assert results
    assert "python" in results[0].lower()
