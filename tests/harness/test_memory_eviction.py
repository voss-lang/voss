"""M8-06 inline eviction tests (Req 6 cap + D-14/D-16 quota)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from voss.harness.memory_store import MemoryStore


@pytest.fixture(autouse=True)
def _no_chroma(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip chroma init so disk accounting reflects user-content only.

    Chroma's persist_dir holds an opaque SQLite DB + embedding model files
    (several MB); eviction is a user-content policy, not a chroma reclaim
    policy. Tests focus on the source-dir size invariant.
    """
    monkeypatch.setattr(MemoryStore, "_maybe_chroma", lambda self: None)


def _turns_dir(repo: Path) -> Path:
    return repo / ".voss" / "memory" / "turns"


def _seed_turns_bytes(repo: Path, total_bytes: int, *, session_prefix: str = "old") -> None:
    """Drop fake jsonl files in turns/ to inflate dir size."""
    d = _turns_dir(repo)
    d.mkdir(parents=True, exist_ok=True)
    chunk = "x" * 256
    written = 0
    i = 0
    while written < total_bytes:
        path = d / f"{session_prefix}-{i:04d}.jsonl"
        path.write_text(chunk + "\n")
        written += len(chunk) + 1
        i += 1
    # Backdate so they evict first
    for p in d.glob(f"{session_prefix}-*.jsonl"):
        os.utime(p, (1000, 1000))


def test_inline_evict_when_source_over_quota(tmp_voss_repo: Path) -> None:
    cap = 4096
    store = MemoryStore(tmp_voss_repo, cap_bytes=cap).bind(session_id="s1")
    turns_quota = int(cap * 0.60)
    _seed_turns_bytes(tmp_voss_repo, turns_quota + 2048)

    files_before = list(_turns_dir(tmp_voss_repo).glob("*.jsonl"))
    assert sum(p.stat().st_size for p in files_before) > turns_quota

    store.write_turn(role="user", content="new turn body", session_id="s1", turn_idx=0)

    after = sum(p.stat().st_size for p in _turns_dir(tmp_voss_repo).glob("*.jsonl"))
    assert after <= turns_quota, f"post-write turns dir {after} > quota {turns_quota}"


def test_post_write_size_under_cap(tmp_voss_repo: Path) -> None:
    cap = 10_240
    store = MemoryStore(tmp_voss_repo, cap_bytes=cap).bind(session_id="s1")
    _seed_turns_bytes(tmp_voss_repo, int(cap * 1.10))

    store.write_turn(role="user", content="new turn", session_id="s1", turn_idx=0)

    total = 0
    for src in ("turns", "ledgers", "decisions", "conventions", "notes"):
        src_dir = tmp_voss_repo / ".voss" / "memory" / src
        if not src_dir.exists():
            continue
        total += sum(p.stat().st_size for p in src_dir.rglob("*") if p.is_file())
    assert total <= cap, f"post-write user-content total {total} > cap {cap}"


def test_oldest_evicted_first_within_source(tmp_voss_repo: Path) -> None:
    cap = 2048
    store = MemoryStore(tmp_voss_repo, cap_bytes=cap).bind(session_id="s1")
    turns_dir = _turns_dir(tmp_voss_repo)
    turns_dir.mkdir(parents=True, exist_ok=True)

    body = "y" * 700
    paths = []
    for i, ts in enumerate((1000, 2000, 3000)):
        p = turns_dir / f"seed-{i}.jsonl"
        p.write_text(body + "\n")
        os.utime(p, (ts, ts))
        paths.append(p)

    store.write_turn(role="user", content="incoming", session_id="s1", turn_idx=0)

    assert not paths[0].exists(), "oldest seed-0 should be evicted first"
    assert paths[2].exists(), "newest seed-2 should survive"
