from __future__ import annotations

import json
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from voss.eval import retrieval
from voss.eval.retrieval import PINNED_COMMIT, build_pools, materialize

DATASET = Path(__file__).resolve().parents[2] / "evals" / "retrieval"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_concurrent_materialization_reuses_the_first_complete_archive(tmp_path, monkeypatch):
    repo = Path(__file__).resolve().parents[2]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    monkeypatch.setattr(retrieval.tempfile, "gettempdir", lambda: str(tmp_path))
    dest = tmp_path / f"voss-retrieval-{commit[:12]}"
    ready = threading.Barrier(2)
    rename = Path.rename

    def publish(path, target):
        if target == dest:
            ready.wait(timeout=30)
        return rename(path, target)

    monkeypatch.setattr(Path, "rename", publish)
    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(materialize, commit) for _ in range(2)]
        assert [future.result(timeout=60) for future in futures] == [dest, dest]
    assert (dest / ".complete").is_file()
    assert (dest / "README.md").is_file()
    assert list(tmp_path.iterdir()) == [dest]


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
def test_materialize_rebuilds_cache_when_files_were_deleted(monkeypatch, tmp_path):
    monkeypatch.setattr(retrieval.tempfile, "gettempdir", lambda: str(tmp_path))
    corpus = materialize(PINNED_COMMIT)
    source = corpus / "voss" / "harness" / "code" / "semantic_index.py"
    source.unlink()

    assert materialize(PINNED_COMMIT) == corpus
    assert source.is_file()


@pytest.mark.slow
def test_materialize_keeps_a_tree_another_run_published_after_the_stale_check(monkeypatch, tmp_path):
    monkeypatch.setattr(retrieval.tempfile, "gettempdir", lambda: str(tmp_path))
    corpus = materialize(PINNED_COMMIT)
    published = corpus.stat().st_ino
    complete = retrieval._complete
    calls = []

    def stale_on_first_check(dest):
        calls.append(dest)
        return len(calls) > 1 and complete(dest)

    monkeypatch.setattr(retrieval, "_complete", stale_on_first_check)

    assert materialize(PINNED_COMMIT) == corpus
    assert corpus.stat().st_ino == published


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
