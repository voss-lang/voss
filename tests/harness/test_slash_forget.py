"""M8-05 /forget slash command tests."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from voss.harness.cli import _forget
from voss.harness.memory_store import MemoryStore


def _ctx(repo: Path) -> SimpleNamespace:
    store = MemoryStore(repo).bind(session_id="test-sess")
    store.write_turn(role="user", content="seed turn", session_id="test-sess", turn_idx=0)
    return SimpleNamespace(
        memory_store=store,
        record=SimpleNamespace(id="test-sess", name="original-name", runs=[]),
        cwd=repo,
    )


def test_forget_tombstones_matching_ids(
    tmp_voss_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    ctx = _ctx(tmp_voss_repo)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    _forget(ctx, ["turn:test-sess:*", "--yes"], "/forget turn:test-sess:* --yes")
    out = capsys.readouterr().out
    assert "tombstoned" in out
    tomb = tmp_voss_repo / ".voss" / "memory" / ".tombstones.jsonl"
    assert tomb.exists()
    body = tomb.read_text()
    assert "turn:test-sess:000" in body


def test_forget_requires_yes_noninteractive(
    tmp_voss_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    ctx = _ctx(tmp_voss_repo)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    _forget(ctx, ["turn:test-sess:*"], "/forget turn:test-sess:*")
    err = capsys.readouterr().err
    assert "requires --yes" in err
    tomb = tmp_voss_repo / ".voss" / "memory" / ".tombstones.jsonl"
    assert not tomb.exists() or tomb.read_text().strip() == ""
