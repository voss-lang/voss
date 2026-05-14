"""M8-03 recall hit-rate evaluation (chroma 80% / keyword 60% top-3 gates).

`fake_session_corpus` (conftest.py) seeds a 5-session corpus across all four
source types plus a ledger; this test exercises `MemoryStore.recall` against
that fixture under both chroma and keyword-fallback configurations.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from voss.harness.memory_store import MemoryStore


def _hit_rate(store: MemoryStore, corpus: dict) -> float:
    hits = 0
    for query, expected in corpus.items():
        result = store.recall(query, top_k=3)
        locators = [h.locator for h in result]
        if expected in locators:
            hits += 1
    return hits / len(corpus)


@pytest.mark.parametrize("chroma_enabled", [True, False], ids=["chroma", "keyword"])
def test_recall_top3_hit_rate(
    chroma_enabled: bool,
    tmp_voss_repo: Path,
    fake_session_corpus: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not chroma_enabled:
        # Force MemoryStore.recall to take the keyword fallback regardless of env.
        from voss.harness import memory_store as ms_mod

        monkeypatch.setattr(
            ms_mod.MemoryStore,
            "_maybe_chroma",
            lambda self: None,
        )
    else:
        try:
            from voss_runtime.memory import SemanticMemory  # noqa: F401
        except ModuleNotFoundError:
            pytest.skip("voss[search] not installed; chroma path unavailable")

    store = MemoryStore(tmp_voss_repo).bind(session_id="eval")
    rate = _hit_rate(store, fake_session_corpus)
    floor = 0.80 if chroma_enabled else 0.60
    assert rate >= floor, (
        f"recall@top-3 hit rate {rate:.2%} below floor {floor:.0%} "
        f"({'chroma' if chroma_enabled else 'keyword'} path)"
    )
