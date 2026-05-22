"""M8-03 MemoryStore orchestration tests."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from voss.harness.memory_store import Hit, MemoryStore, make_id


def test_bm25_tokenize_splits_symbols_and_punctuation() -> None:
    from voss.harness.memory_store import _bm25_tokenize

    assert {"get", "user", "by", "id"} <= set(_bm25_tokenize("getUserById"))
    assert {"parse", "config", "file"} <= set(_bm25_tokenize("parse_config_file"))
    assert {"voss", "harness", "memory", "store"} <= set(
        _bm25_tokenize("voss.harness.memory_store")
    )
    assert _bm25_tokenize("!@#$%^&*()") == []


def test_recall_hits_tagged_with_source(tmp_voss_repo: Path) -> None:
    from types import SimpleNamespace

    store = MemoryStore(tmp_voss_repo).bind(session_id="s1")
    store.write_turn(
        role="user",
        content="rotating jwt tokens every 24h is the new policy",
        session_id="s1",
        turn_idx=0,
    )
    store.write_note("jwt rotation runbook tip", session_id="s1")
    store.write_convention(
        SimpleNamespace(
            statement="rotate jwt tokens every 24h",
            confidence=0.9,
            evidence_quote="rotate jwt tokens every 24h",
            evidence_turn_idx=0,
        ),
        session_id="s1",
    )
    decisions_dir = tmp_voss_repo / ".voss" / "memory" / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    (decisions_dir / "jwt-decision.md").write_text(
        "---\nid: jwt-decision\nrelated_session: s1\n---\n\n# Decision\n\njwt rotation policy\n"
    )

    hits = store.recall("jwt rotation", top_k=10)
    assert hits, "recall returned no hits"
    sources = {h.source for h in hits}
    assert all(h.source for h in hits), "every Hit must have a non-empty source"
    assert len(sources) >= 2


def test_no_chroma_no_import_error(
    chroma_disabled_env, tmp_voss_repo: Path
) -> None:
    store = MemoryStore(tmp_voss_repo).bind(session_id="s1")
    for idx in range(3):
        store.write_turn(
            role="user",
            content=f"sample {idx} jwt content",
            session_id="s1",
            turn_idx=idx,
        )
    hits = store.recall("jwt", top_k=3)
    assert isinstance(hits, list)
    for h in hits:
        assert isinstance(h, Hit)


def test_lazy_chroma_init_no_eager_import(tmp_path: Path) -> None:
    """Verify chromadb stays unimported until first recall/add (Pitfall 4)."""
    script = (
        "import sys\n"
        "from pathlib import Path\n"
        "from voss.harness.memory_store import MemoryStore\n"
        f"s = MemoryStore(Path({str(tmp_path)!r})).bind(session_id='x')\n"
        "assert 'chromadb' not in sys.modules, 'chromadb imported eagerly'\n"
        "print('ok')\n"
    )
    env = os.environ.copy()
    repo_root = Path(__file__).resolve().parents[2]
    env["PYTHONPATH"] = (
        str(repo_root)
        if not env.get("PYTHONPATH")
        else f"{repo_root}{os.pathsep}{env['PYTHONPATH']}"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"subprocess failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert result.stdout.strip() == "ok"


def test_recall_source_filter(tmp_voss_repo: Path) -> None:
    store = MemoryStore(tmp_voss_repo).bind(session_id="s1")
    store.write_turn(
        role="user",
        content="jwt token refresh handler bug",
        session_id="s1",
        turn_idx=0,
    )
    store.write_turn(
        role="assistant",
        content="unrelated deployment checklist",
        session_id="s1",
        turn_idx=1,
    )
    decisions_dir = tmp_voss_repo / ".voss" / "memory" / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    (decisions_dir / "jwt-policy.md").write_text(
        "---\nid: jwt-policy\n---\n\n# Decision\n\njwt token policy\n"
    )

    hits = store.recall("jwt", top_k=10, source="turns")
    assert hits, "expected at least one turn hit"
    assert all(h.source == "turn" for h in hits)


def test_bm25_fallback_source_filter_returns_turn_hits(
    monkeypatch: pytest.MonkeyPatch, tmp_voss_repo: Path
) -> None:
    monkeypatch.setattr(MemoryStore, "_maybe_chroma", lambda self: None)
    store = MemoryStore(tmp_voss_repo).bind(session_id="s1")
    store.write_turn(
        role="user",
        content="semantic fallback source filter target",
        session_id="s1",
        turn_idx=0,
    )
    store.write_turn(
        role="assistant",
        content="unrelated deployment checklist",
        session_id="s1",
        turn_idx=1,
    )
    decisions_dir = tmp_voss_repo / ".voss" / "memory" / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    (decisions_dir / "fallback-source.md").write_text(
        "---\nid: fallback-source\n---\n\n# Decision\n\nsemantic fallback source filter target\n"
    )

    hits = store.recall("semantic fallback source filter", top_k=10, source="turns")

    assert hits, "expected at least one BM25 turn hit"
    assert all(h.source == "turn" for h in hits)


def test_bm25_fallback_omits_tombstoned_turn_locator(
    monkeypatch: pytest.MonkeyPatch, tmp_voss_repo: Path
) -> None:
    monkeypatch.setattr(MemoryStore, "_maybe_chroma", lambda self: None)
    store = MemoryStore(tmp_voss_repo).bind(session_id="s1")
    store.write_turn(
        role="user",
        content="tombstone bm25 fallback should hide this locator",
        session_id="s1",
        turn_idx=0,
    )
    locator = make_id("turn", "s1", seq=0)
    assert store.forget(locator) == 1

    hits = store.recall("tombstone bm25 fallback locator", top_k=10)

    assert all(h.locator != locator for h in hits)


def test_bm25_fallback_no_match_returns_empty_list(
    monkeypatch: pytest.MonkeyPatch, tmp_voss_repo: Path
) -> None:
    monkeypatch.setattr(MemoryStore, "_maybe_chroma", lambda self: None)
    store = MemoryStore(tmp_voss_repo).bind(session_id="s1")
    store.write_turn(
        role="user",
        content="alpha beta gamma",
        session_id="s1",
        turn_idx=0,
    )

    assert store.recall("zzzz-not-present", top_k=10) == []


def test_rrf_merge_deduplicates_and_preserves_first_hit_metadata() -> None:
    duplicate_bm25 = Hit(
        source="turn",
        locator="turn:s1:000",
        score=9.0,
        excerpt="bm25 duplicate excerpt",
        session_id="s1",
        ts="2026-05-21T10:00:00+00:00",
    )
    bm25_only = Hit(source="note", locator="note:alpha", score=8.0, excerpt="bm25 only")
    chroma_only = Hit(source="decision", locator="decision:beta", score=7.0, excerpt="chroma only")
    duplicate_chroma = Hit(
        source="ledger",
        locator="turn:s1:000",
        score=6.0,
        excerpt="chroma duplicate excerpt",
        session_id="other",
        ts="2026-05-21T11:00:00+00:00",
    )

    results = MemoryStore._rrf_merge(
        [[duplicate_bm25, bm25_only], [chroma_only, duplicate_chroma]],
        top_k=2,
    )

    assert len(results) == 2
    assert results[0].locator == "turn:s1:000"
    assert results[0].score > results[1].score
    assert results[0].source == duplicate_bm25.source
    assert results[0].excerpt == duplicate_bm25.excerpt
    assert results[0].session_id == duplicate_bm25.session_id
    assert results[0].ts == duplicate_bm25.ts


def test_recall_uses_rrf_hybrid_path(
    monkeypatch: pytest.MonkeyPatch, tmp_voss_repo: Path
) -> None:
    store = MemoryStore(tmp_voss_repo).bind(session_id="s1")
    chroma = object()
    calls: list[str] = []
    duplicate_bm25 = Hit(source="turn", locator="turn:s1:000", score=1.0, excerpt="bm25")
    bm25_only = Hit(source="note", locator="note:alpha", score=1.0, excerpt="bm25 only")
    chroma_only = Hit(source="decision", locator="decision:beta", score=1.0, excerpt="chroma only")
    duplicate_chroma = Hit(source="turn", locator="turn:s1:000", score=1.0, excerpt="chroma")

    def fake_bm25(self, query, *, top_k, source):
        calls.append(f"bm25:{top_k}:{source}")
        return [duplicate_bm25, bm25_only]

    def fake_maybe_chroma(self):
        calls.append("maybe_chroma")
        return chroma

    def fake_chroma(self, received_chroma, query, *, top_k, source):
        calls.append(f"chroma:{top_k}:{source}:{received_chroma is chroma}")
        return [chroma_only, duplicate_chroma]

    monkeypatch.setattr(MemoryStore, "_bm25_recall", fake_bm25)
    monkeypatch.setattr(MemoryStore, "_maybe_chroma", fake_maybe_chroma)
    monkeypatch.setattr(MemoryStore, "_chroma_recall", fake_chroma)

    hits = store.recall("jwt", top_k=2, source="turns")

    assert calls == ["bm25:6:turns", "maybe_chroma", "chroma:6:turns:True"]
    assert [hit.locator for hit in hits] == ["turn:s1:000", "decision:beta"]
    assert hits[0].score > hits[1].score


def test_recall_returns_bm25_when_chroma_recall_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_voss_repo: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = MemoryStore(tmp_voss_repo).bind(session_id="s1")
    bm25_hits = [
        Hit(source="turn", locator="turn:s1:000", score=3.0, excerpt="first"),
        Hit(source="turn", locator="turn:s1:001", score=2.0, excerpt="second"),
        Hit(source="turn", locator="turn:s1:002", score=1.0, excerpt="third"),
    ]

    monkeypatch.setattr(MemoryStore, "_bm25_recall", lambda self, query, *, top_k, source: bm25_hits)
    monkeypatch.setattr(MemoryStore, "_maybe_chroma", lambda self: object())

    def fail_chroma(self, chroma, query, *, top_k, source):
        raise RuntimeError("boom")

    monkeypatch.setattr(MemoryStore, "_chroma_recall", fail_chroma)

    hits = store.recall("jwt", top_k=2)

    assert hits == bm25_hits[:2]
    assert "falling back to BM25" in capsys.readouterr().err


def test_composite_id_format() -> None:
    assert make_id("turn", "abc-123", seq=42) == "turn:abc-123:042"
    assert make_id("decision", ".voss/decisions/2026-05-14-foo.md") == (
        "decision:.voss/decisions/2026-05-14-foo.md"
    )
    assert make_id("convention", "2026-05-14-naming") == "convention:2026-05-14-naming"
