"""M8-05 /recall slash command tests."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from voss.harness.cli import _build_slash_registry, _recall
from voss.harness.memory_store import MemoryStore


def _ctx(repo: Path) -> SimpleNamespace:
    return SimpleNamespace(
        memory_store=MemoryStore(repo).bind(session_id="test-sess"),
        record=SimpleNamespace(id="test-sess", name="original-name", runs=[]),
        cwd=repo,
    )


def test_recall_command_registered() -> None:
    registry = _build_slash_registry()
    cmd = registry.lookup("/recall")
    assert cmd is not None
    assert cmd.help
    assert cmd.mutating is False


def test_recall_returns_top_n_with_source_filter(
    tmp_voss_repo: Path,
    fake_session_corpus: dict,
    capsys: pytest.CaptureFixture,
) -> None:
    ctx = _ctx(tmp_voss_repo)
    _recall(
        ctx,
        ["snake_case", "--top", "3", "--source", "turn"],
        "/recall snake_case --top 3 --source turn",
    )
    out = capsys.readouterr().out
    assert "[turn]" in out
    assert "[decision]" not in out
    header_lines = [ln for ln in out.splitlines() if ln.startswith("[")]
    assert len(header_lines) <= 3


def test_recall_no_args_prints_usage(
    tmp_voss_repo: Path,
    capsys: pytest.CaptureFixture,
) -> None:
    ctx = _ctx(tmp_voss_repo)
    _recall(ctx, [], "/recall")
    err = capsys.readouterr().err
    assert "usage" in err.lower()
