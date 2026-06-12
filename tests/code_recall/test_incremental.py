"""VSEM-02 RED tests: hash-manifest incremental re-embedding + D-13 trigger #2.

Embed-call counting: a DefaultEmbeddingFunction subclass records every input
batch, monkeypatched onto SemanticMemory — only re-embedded chunks appear.
"""
from __future__ import annotations

import time

import pytest

from .conftest import write_fixture_repo


@pytest.fixture
def counting_embed(monkeypatch):
    """fake_embed_fn variant that records every embedded input text."""
    try:
        from chromadb.utils import embedding_functions
    except Exception:
        pytest.skip("chromadb DefaultEmbeddingFunction unavailable")

    # NOT a DefaultEmbeddingFunction subclass: chroma 1.5.9 _embed() bypasses
    # any instance of DefaultEmbeddingFunction (uses the persisted config EF
    # natively), so a counting subclass never fires. Wrap instead.
    class CountingEmbed(embedding_functions.EmbeddingFunction):
        def __init__(self) -> None:
            self._inner = embedding_functions.DefaultEmbeddingFunction()
            self.embedded_texts: list[str] = []

        def __call__(self, input):  # noqa: A002 — chroma's param name
            self.embedded_texts.extend(str(t) for t in input)
            return self._inner(input)

    fn = CountingEmbed()

    from voss_runtime.memory.semantic import SemanticMemory

    monkeypatch.setattr(SemanticMemory, "_embedding_function", lambda self: fn)
    return fn


def _built_repo(tmp_path):
    write_fixture_repo(tmp_path)

    from voss.harness.code.index import build_index

    build_index(tmp_path)

    from voss.harness.code.semantic_index import CodeIndex

    index = CodeIndex(tmp_path)
    index.build(session_id="test-session")
    return index


def test_only_changed_file_reembeds(tmp_path, counting_embed):
    """Touch one file → exactly that file's chunks re-embed."""
    index = _built_repo(tmp_path)
    counting_embed.embedded_texts.clear()

    (tmp_path / "alpha.py").write_text(
        "def alpha_retry_backoff_v2(attempt: int) -> float:\n"
        "    return min(3.0 ** attempt, 60.0)\n"
    )
    index.build(session_id="test-session")

    assert counting_embed.embedded_texts, "changed file must re-embed"
    assert any("alpha_retry_backoff_v2" in t for t in counting_embed.embedded_texts)
    for text in counting_embed.embedded_texts:
        assert "beta_serialize" not in text, "unchanged beta.py must not re-embed"
        assert "gamma_evict_cache" not in text, "unchanged gamma.py must not re-embed"


def test_no_reembed_on_unchanged(tmp_path, counting_embed):
    """Unchanged-repo reindex → zero embed calls."""
    index = _built_repo(tmp_path)
    counting_embed.embedded_texts.clear()

    index.build(session_id="test-session")

    assert counting_embed.embedded_texts == []


def test_targeted_rehash_on_fs_write(tmp_path, counting_embed):
    """D-13 trigger #2 contract (implemented in V19-03): an agent file
    mutation fires CodeIndexService.queue_rehash(path) → EXACTLY that file's
    chunks re-embed, off-thread, without blocking the caller."""
    write_fixture_repo(tmp_path)

    from voss.harness.code.index import build_index

    build_index(tmp_path)

    from voss.harness.code.semantic_index import CodeIndexService

    # Not-ready service: queue_rehash must be a non-blocking no-op, not an error.
    cold = CodeIndexService(tmp_path, session_id="test-session")
    cold.queue_rehash(tmp_path / "alpha.py")

    svc = CodeIndexService(tmp_path, session_id="test-session")
    svc.ensure_background_build()
    deadline = time.monotonic() + 30.0
    while not svc.is_ready() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert svc.is_ready(), "background build must finish on tiny fixture repo"
    counting_embed.embedded_texts.clear()

    target = tmp_path / "gamma.py"
    target.write_text(
        "def gamma_evict_cache_rewritten(root) -> int:\n"
        "    return 0\n"
    )
    started = time.monotonic()
    svc.queue_rehash(target)
    assert time.monotonic() - started < 1.0, "queue_rehash must not block"

    deadline = time.monotonic() + 30.0
    while not counting_embed.embedded_texts and time.monotonic() < deadline:
        time.sleep(0.05)

    assert counting_embed.embedded_texts, "targeted re-hash must re-embed the written file"
    assert any(
        "gamma_evict_cache_rewritten" in t for t in counting_embed.embedded_texts
    )
    for text in counting_embed.embedded_texts:
        assert "alpha_retry_backoff" not in text, "alpha.py must not re-embed"
        assert "beta_serialize" not in text, "beta.py must not re-embed"
