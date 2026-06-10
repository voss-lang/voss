"""Matrix runner toolchain + skip scaffolds (EVGLD-02, EVGLD-03, EVGLD-05)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import click
import pytest

from voss.eval import runner

_XFAIL = pytest.mark.xfail(
    reason="plan E2-08: runner toolchain extension not yet implemented",
    strict=True,
)


def _write_task(root: Path, task_id: str, task_toml: str) -> None:
    task_dir = root / "tests" / "eval" / "matrix" / task_id
    fixture = task_dir / "fixture"
    fixture.mkdir(parents=True)
    (fixture / "README.md").write_text("# Fixture\n")
    (task_dir / "task.toml").write_text(task_toml)


def _read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


_MINIMAL_TASK = "\n".join(
    [
        'prompt = "Smoke task."',
        'mode = "plan"',
        'rubric = "Pass if the run completes."',
        "",
    ]
)


@_XFAIL
def test_preflight_prints_toolchain_availability(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """EVGLD-02: preflight prints toolchain availability for py/rust/ts."""
    _write_task(tmp_path, "py-99-stub", _MINIMAL_TASK)
    out = tmp_path / "out"
    monkeypatch.chdir(tmp_path)

    real_which = runner.shutil.which

    def _which(cmd: str, path: str | None = None) -> str | None:
        if cmd == "cargo":
            return None
        return real_which(cmd, path)

    with patch.object(runner.shutil, "which", side_effect=_which):
        runner.run_suite(
            stub=True,
            auth_pref="none",
            suite="matrix",
            task="py-99-stub",
            out=out,
            max_turns=3,
        )

    captured = capsys.readouterr()
    stdout = captured.out
    assert "toolchains:" in stdout
    assert "py" in stdout
    assert "rust" in stdout
    assert "ts" in stdout


@_XFAIL
def test_toolchain_absent_records_skip_row(tmp_path: Path, monkeypatch) -> None:
    """EVGLD-03: absent toolchain records skip row, not gate fail."""
    _write_task(tmp_path, "rust-99-stub", _MINIMAL_TASK)
    out = tmp_path / "out"
    monkeypatch.chdir(tmp_path)

    real_which = runner.shutil.which

    def _which(cmd: str, path: str | None = None) -> str | None:
        if cmd == "cargo":
            return None
        return real_which(cmd, path)

    with patch.object(runner.shutil, "which", side_effect=_which):
        runner.run_suite(
            stub=True,
            auth_pref="none",
            suite="matrix",
            task="rust-99-stub",
            out=out,
            max_turns=3,
        )

    row = _read_rows(out / "runs.jsonl")[0]
    assert row["skipped"] is True
    assert row["skip_reason"] == "toolchain-absent"
    assert row["gate_pass"] is None
    assert row["success"] is None
    assert row.get("gate_pass") is not False


@_XFAIL
def test_require_all_toolchains_fails_when_absent(tmp_path: Path, monkeypatch) -> None:
    """EVGLD-05: --require-all-toolchains fails fast when a toolchain is missing."""
    _write_task(tmp_path, "py-99-stub", _MINIMAL_TASK)
    out = tmp_path / "out"
    monkeypatch.chdir(tmp_path)

    real_which = runner.shutil.which

    def _which(cmd: str, path: str | None = None) -> str | None:
        if cmd == "cargo":
            return None
        return real_which(cmd, path)

    with patch.object(runner.shutil, "which", side_effect=_which):
        with pytest.raises(click.UsageError, match="cargo"):
            runner.run_suite(
                stub=True,
                auth_pref="none",
                suite="matrix",
                task="py-99-stub",
                out=out,
                require_all_toolchains=True,
            )
