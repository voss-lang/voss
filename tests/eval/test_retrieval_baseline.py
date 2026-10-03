from __future__ import annotations

import json
from pathlib import Path

import pytest

from voss.eval import retrieval
from voss.eval.retrieval import PINNED_COMMIT, build_pools, materialize

DATASET = Path(__file__).resolve().parents[2] / "evals" / "retrieval"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


@pytest.mark.slow
def test_materialize_pinned_commit_is_cached_without_git_metadata(monkeypatch):
    corpus = materialize(PINNED_COMMIT)
    assert (corpus / "voss" / "harness" / "code" / "semantic_index.py").is_file()
    assert not (corpus / ".git").exists()

    popen = retrieval.subprocess.Popen

    def no_archive(argv, *args, **kwargs):
        assert "archive" not in argv, "cache hit must not re-archive"
        return popen(argv, *args, **kwargs)

    monkeypatch.setattr(retrieval.subprocess, "Popen", no_archive)
    assert materialize(PINNED_COMMIT) == corpus


@pytest.mark.slow
def test_stored_pools_reproduce_at_pinned_commit():
    stored_files = sorted((DATASET / "baseline").glob("*.jsonl"))
    if not stored_files:
        pytest.skip("no stored baseline pools yet")
    stored = {row["query_id"]: row for path in stored_files for row in read_jsonl(path)}
    queries = [
        row for path in sorted((DATASET / "queries").glob("*.jsonl")) for row in read_jsonl(path)
        if row["id"] in stored
    ]
    rebuilt = {row["query_id"]: row for row in build_pools(materialize(PINNED_COMMIT), queries)}
    bm25_drift = [qid for qid in stored if rebuilt[qid]["bm25"] != stored[qid]["bm25"]]
    assert not bm25_drift, f"bm25 rankings drifted for {bm25_drift}"
    pool_drift = [
        f"{qid}: stored {[e['chunk_id'] for e in stored[qid]['pool']]} "
        f"rebuilt {[e['chunk_id'] for e in rebuilt[qid]['pool']]}"
        for qid in stored
        if [(e["chunk_id"], e["text_sha"]) for e in rebuilt[qid]["pool"]]
        != [(e["chunk_id"], e["text_sha"]) for e in stored[qid]["pool"]]
    ]
    assert not pool_drift, "pool drift:\n" + "\n".join(pool_drift)
