"""M8-03 MemoryStore orchestration tests."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from voss.harness.memory_store import Hit, MemoryStore, make_id


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
    decisions_dir = tmp_voss_repo / ".voss" / "memory" / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    (decisions_dir / "jwt-policy.md").write_text(
        "---\nid: jwt-policy\n---\n\n# Decision\n\njwt token policy\n"
    )

    hits = store.recall("jwt", top_k=10, source="turns")
    assert hits, "expected at least one turn hit"
    assert all(h.source == "turn" for h in hits)


def test_composite_id_format() -> None:
    assert make_id("turn", "abc-123", seq=42) == "turn:abc-123:042"
    assert make_id("decision", ".voss/decisions/2026-05-14-foo.md") == (
        "decision:.voss/decisions/2026-05-14-foo.md"
    )
    assert make_id("convention", "2026-05-14-naming") == "convention:2026-05-14-naming"
