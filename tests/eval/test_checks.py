"""Unit tests for eval check executor (_run_checks)."""
from __future__ import annotations

import time
from pathlib import Path

from voss.eval.runner import _run_checks
from voss.eval.suite import CmdCheck, FileContainsCheck, FileExistsCheck


def test_empty_checks(tmp_path: Path) -> None:
    gate_pass, results = _run_checks([], tmp_path)

    assert gate_pass is True
    assert results == []


def test_cmd_true_false(tmp_path: Path) -> None:
    gate_pass, results = _run_checks([CmdCheck(type="cmd", run="true")], tmp_path)
    assert gate_pass is True
    assert results[0]["pass"] is True

    gate_pass, results = _run_checks([CmdCheck(type="cmd", run="false")], tmp_path)
    assert gate_pass is False
    assert results[0]["pass"] is False


def test_cmd_exit_codes(tmp_path: Path) -> None:
    gate_pass, results = _run_checks([CmdCheck(type="cmd", run="exit 1")], tmp_path)
    assert gate_pass is False
    assert results[0]["pass"] is False

    gate_pass, results = _run_checks([CmdCheck(type="cmd", run="exit 0")], tmp_path)
    assert gate_pass is True
    assert results[0]["pass"] is True


def test_cmd_timeout(tmp_path: Path) -> None:
    start = time.monotonic()

    gate_pass, results = _run_checks(
        [CmdCheck(type="cmd", run="sleep 5", timeout=1)],
        tmp_path,
    )

    elapsed = time.monotonic() - start
    assert elapsed < 2.0
    assert gate_pass is False
    assert results[0]["pass"] is False
    assert results[0]["detail"] == "timeout"


def test_file_exists(tmp_path: Path) -> None:
    (tmp_path / "present.txt").write_text("ok")

    gate_pass, results = _run_checks(
        [FileExistsCheck(type="file_exists", path="present.txt")],
        tmp_path,
    )
    assert gate_pass is True
    assert results[0]["pass"] is True

    gate_pass, results = _run_checks(
        [FileExistsCheck(type="file_exists", path="missing.txt")],
        tmp_path,
    )
    assert gate_pass is False
    assert results[0]["pass"] is False


def test_file_contains(tmp_path: Path) -> None:
    (tmp_path / "data.txt").write_text("hello world")

    gate_pass, results = _run_checks(
        [FileContainsCheck(type="file_contains", path="data.txt", text="world")],
        tmp_path,
    )
    assert gate_pass is True
    assert results[0]["pass"] is True

    gate_pass, results = _run_checks(
        [FileContainsCheck(type="file_contains", path="data.txt", text="absent")],
        tmp_path,
    )
    assert gate_pass is False
    assert results[0]["pass"] is False


def test_mixed_no_short_circuit(tmp_path: Path) -> None:
    gate_pass, results = _run_checks(
        [
            CmdCheck(type="cmd", run="true"),
            CmdCheck(type="cmd", run="false"),
        ],
        tmp_path,
    )

    assert gate_pass is False
    assert len(results) == 2
    assert results[0]["pass"] is True
    assert results[1]["pass"] is False
