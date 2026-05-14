"""M8-05 /memory slash command tests."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from voss.harness.cli import _memory
from voss.harness.memory_store import MemoryStore


def test_memory_summary_renders_counts_per_source(
    tmp_voss_repo: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    store = MemoryStore(tmp_voss_repo).bind(session_id="test-sess")
    store.write_turn(role="user", content="turn body", session_id="test-sess", turn_idx=0)
    store.write_note("a note body", session_id="test-sess")
    candidate = SimpleNamespace(
        statement="use type hints",
        confidence=0.9,
        evidence_quote="always use type hints",
        evidence_turn_idx=0,
    )
    store.write_convention(candidate, session_id="test-sess")

    ctx = SimpleNamespace(
        memory_store=store,
        record=SimpleNamespace(id="test-sess", name="orig", runs=[]),
        cwd=tmp_voss_repo,
    )
    _memory(ctx, [], "/memory")
    out = capsys.readouterr().out
    assert "turns" in out
    assert "conventions" in out
    assert "notes" in out
