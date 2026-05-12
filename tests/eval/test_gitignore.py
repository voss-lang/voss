"""M5 D-03 / M2 D-09: .voss/.gitignore does NOT add eval/; .voss/eval/<ts>/ stays git-tracked."""
from __future__ import annotations

from pathlib import Path

from voss.harness.cognition import write_voss_gitignore


def test_eval_tracked_voss_gitignore_does_not_ignore_eval(tmp_path: Path) -> None:
    write_voss_gitignore(tmp_path)
    content = (tmp_path / ".voss" / ".gitignore").read_text()

    assert "eval/" not in content
    patterns = [line.strip() for line in content.splitlines() if not line.startswith("#")]
    assert "eval" not in patterns


def test_voss_gitignore_still_ignores_sessions(tmp_path: Path) -> None:
    write_voss_gitignore(tmp_path)
    content = (tmp_path / ".voss" / ".gitignore").read_text()

    assert "sessions/" in content
