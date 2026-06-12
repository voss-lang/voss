"""VSEM-04 RED tests: code_recall tool registration, BM25 degradation, p95 perf."""
from __future__ import annotations

import time

import pytest

from .conftest import write_fixture_repo


def test_registration(tmp_path):
    """code_recall lands in the tools dict via attach_code_recall_tool:
    group=="code", non-mutating, schema present."""
    from voss.harness.code.semantic_index import CodeIndexService
    from voss.harness.tools import ToolEntry, attach_code_recall_tool

    svc = CodeIndexService(tmp_path, session_id="test-session")
    tools: dict[str, ToolEntry] = {}
    attach_code_recall_tool(tools, code_index_service=svc)

    assert "code_recall" in tools
    entry = tools["code_recall"]
    assert isinstance(entry, ToolEntry)
    assert entry.group == "code"
    assert entry.is_mutating is False
    assert entry.descriptor.parameters, "tool schema must be present"


def test_degradation(tmp_path, chroma_disabled_env):
    """Chroma-absent install: query returns BM25-only hits, never raises."""
    write_fixture_repo(tmp_path)

    from voss.harness.code.index import build_index

    build_index(tmp_path)

    from voss.harness.code.semantic_index import CodeIndex

    index = CodeIndex(tmp_path)
    index.build(session_id="test-session")
    hits = index.query("retry backoff delay", top_k=5)

    assert isinstance(hits, list), "degraded query must return hits, not raise"
    assert hits, "BM25 fallback must still find the retry/backoff chunk"
    assert any("alpha" in h.locator for h in hits)


@pytest.mark.slow
def test_perf_p95(tmp_path, fake_embed_fn):
    """Recall p95 < 500ms on an indexed ~10K LoC fixture."""
    # ~40 files x ~260 lines ≈ 10K LoC with varied symbol vocab.
    for f in range(40):
        body = "\n\n".join(
            f"def func_{f}_{s}(value):\n"
            f'    """Handler {f}.{s} for topic_{(f + s) % 17}."""\n'
            "    total = 0\n"
            "    for item in range(value):\n"
            "        total += item\n"
            "    return total"
            for s in range(40)
        )
        (tmp_path / f"module_{f}.py").write_text(body + "\n")

    from voss.harness.code.index import build_index

    build_index(tmp_path)

    from voss.harness.code.semantic_index import CodeIndex

    index = CodeIndex(tmp_path)
    index.build(session_id="test-session")

    timings = []
    for i in range(20):
        started = time.perf_counter()
        index.query(f"handler for topic_{i % 17} accumulate total", top_k=5)
        timings.append(time.perf_counter() - started)

    timings.sort()
    p95 = timings[int(len(timings) * 0.95) - 1]
    assert p95 < 0.5, f"p95 recall latency {p95:.3f}s exceeds 500ms"
