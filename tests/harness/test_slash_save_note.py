"""M8-05 /save (memory note) slash command tests; regression for Pitfall 1 collision."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from voss.harness.cli import _save_note
from voss.harness.memory_store import MemoryStore


def _ctx(repo: Path) -> SimpleNamespace:
    return SimpleNamespace(
        memory_store=MemoryStore(repo).bind(session_id="test-sess"),
        record=SimpleNamespace(id="test-sess", name="original-name", runs=[]),
        cwd=repo,
    )


def test_save_note_writes_to_memory_notes_dir(tmp_voss_repo: Path) -> None:
    ctx = _ctx(tmp_voss_repo)
    _save_note(ctx, ["my", "rate-limiter", "idea"], "/save my rate-limiter idea")
    notes_dir = tmp_voss_repo / ".voss" / "memory" / "notes"
    files = list(notes_dir.glob("*.md"))
    assert len(files) == 1
    body = files[0].read_text()
    assert "my rate-limiter idea" in body
    assert "related_session: test-sess" in body


def test_save_note_does_not_rename_session(tmp_voss_repo: Path) -> None:
    ctx = _ctx(tmp_voss_repo)
    _save_note(ctx, ["a", "new", "note"], "/save a new note")
    assert ctx.record.name == "original-name"


def test_save_with_no_args_errors(
    tmp_voss_repo: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    ctx = _ctx(tmp_voss_repo)
    _save_note(ctx, [], "/save")
    err = capsys.readouterr().err
    assert "usage:" in err
    notes_dir = tmp_voss_repo / ".voss" / "memory" / "notes"
    assert not notes_dir.exists() or not list(notes_dir.glob("*.md"))
