"""J3-01 S3.1: candidate shortlist with full chunk text and freshness."""
from __future__ import annotations

import pytest

from .conftest import write_fixture_repo

QUERIES = ["where is retry backoff handled", "json serialization", "evict stale cache"]


def _index(root):
    from voss.harness.code.semantic_index import CodeIndex

    return CodeIndex(root)


@pytest.mark.parametrize("query", QUERIES)
def test_candidates_reproduce_the_eval_pool_order(indexed_fixture_repo, query):
    idx = _index(indexed_fixture_repo)
    pool = idx.query(query, top_k=15)
    candidates = idx.candidates(query)

    assert pool
    assert [c.hit.locator for c in candidates] == [h.locator for h in pool]
    assert [c.hit.score for c in candidates] == [h.score for h in pool]


@pytest.mark.parametrize("query", QUERIES)
def test_candidates_carry_full_indexed_chunk_text_and_location(indexed_fixture_repo, query):
    idx = _index(indexed_fixture_repo)
    candidates = idx.candidates(query)
    chunks = {cid: (rel, start, end, text) for cid, text, rel, start, end in idx._bm25_chunks}

    assert candidates
    for c in candidates:
        rel, start, end, text = chunks[c.hit.locator]
        assert (c.path, c.line_start, c.line_end, c.text) == (rel, start, end, text)
        assert c.fresh is True


def test_changed_file_marks_its_candidates_stale(indexed_fixture_repo):
    idx = _index(indexed_fixture_repo)
    query = "where is retry backoff handled"
    assert all(c.fresh for c in idx.candidates(query))

    alpha = indexed_fixture_repo / "alpha.py"
    alpha.write_text(
        alpha.read_text().replace(
            '"""Alpha module: retry backoff helpers."""\n',
            '"""Alpha module: changed."""\nimport os\n',
        )
    )
    candidates = idx.candidates(query)

    assert any(c.path == "alpha.py" for c in candidates)
    assert any(c.path != "alpha.py" for c in candidates)
    for c in candidates:
        assert c.fresh is (c.path != "alpha.py")


def test_chunk_missing_from_the_index_is_not_fresh(indexed_fixture_repo):
    idx = _index(indexed_fixture_repo)
    query = "json serialization"
    first = idx.candidates(query)[0].hit.locator
    idx._chunk_by_id.pop(first)

    missing = idx.candidates(query)[0]

    assert missing.hit.locator == first
    assert missing.text == ""
    assert missing.fresh is False
    assert missing.path == first.removeprefix("code:").rsplit(":", 1)[0]


def test_no_candidates_without_the_vector_side(tmp_path, chroma_disabled_env):
    write_fixture_repo(tmp_path)
    from voss.harness.code.index import build_index

    build_index(tmp_path)
    idx = _index(tmp_path)
    assert idx.query("json serialization")[0].source == "code[degraded]"

    assert idx.candidates("json serialization") is None


def test_no_candidates_when_the_chroma_query_fails(indexed_fixture_repo, monkeypatch):
    from voss.harness.code.semantic_index import CodeIndex

    def _boom(self, sem, query, top_k):
        raise RuntimeError("chroma down")

    monkeypatch.setattr(CodeIndex, "_chroma_query", _boom)

    assert _index(indexed_fixture_repo).candidates("json serialization") is None


def test_service_returns_no_candidates_until_ready(tmp_path):
    from voss.harness.code.semantic_index import CodeIndexService

    svc = CodeIndexService(tmp_path, session_id="test-session")

    assert svc.is_ready() is False
    assert svc.candidates("json serialization") is None


def test_ready_service_delegates_to_the_index(indexed_fixture_repo):
    from voss.harness.code.semantic_index import CodeIndexService

    svc = CodeIndexService(indexed_fixture_repo, session_id="test-session")
    svc._ready.set()

    assert [c.hit.locator for c in svc.candidates("json serialization")] == [
        h.locator for h in svc._code_index.query("json serialization", top_k=15)
    ]


def test_pool_is_capped_at_fifteen(indexed_fixture_repo):
    from voss.harness.code.semantic_index import CANDIDATE_POOL

    for name in range(12):
        (indexed_fixture_repo / f"extra_{name}.py").write_text(
            f"def json_serialization_{name}(payload):\n    return payload\n"
        )
    from voss.harness.code.index import build_index

    build_index(indexed_fixture_repo)
    idx = _index(indexed_fixture_repo)
    idx.build(session_id="test-session")

    assert CANDIDATE_POOL == 15
    assert len(idx.candidates("json serialization")) == 15
