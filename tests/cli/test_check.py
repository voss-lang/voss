from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from voss.ast_nodes import Span
from voss.cli import main
from voss.diagnostics import AnalysisResult, Diagnostic


_PROBABLE_WARNING_SOURCE = (
    "fn doIt(x: string) -> string {\n"
    "    let intent: probable<string> = ask(\"classify\")\n"
    "    return intent.value\n"
    "}\n"
)

_CLEAN_SOURCE = "let x = 1\n"


def _write(name: str, body: str) -> Path:
    path = Path(name)
    path.write_text(body)
    return path


def test_check_prints_analyzer_warning_and_exits_zero_by_default():
    runner = CliRunner()
    with runner.isolated_filesystem():
        path = _write("warn.voss", _PROBABLE_WARNING_SOURCE)
        result = runner.invoke(main, ["check", str(path)])
        assert result.exit_code == 0, result.output
        assert "ANLY001" in result.output
        assert "warning" in result.output
        assert "warn.voss" in result.output


def test_check_warnings_as_errors_exits_nonzero():
    runner = CliRunner()
    with runner.isolated_filesystem():
        path = _write("warn.voss", _PROBABLE_WARNING_SOURCE)
        result = runner.invoke(main, ["check", "--warnings-as-errors", str(path)])
        assert result.exit_code != 0
        assert "ANLY001" in result.output


def test_check_errors_exit_nonzero(monkeypatch):
    err_diag = Diagnostic(
        severity="error",
        code="ANLY999",
        message="forced error for test",
        span=Span(file="boom.voss", line_start=1, col_start=1, line_end=1, col_end=1),
    )

    def fake_analyze(program, **kwargs):
        return AnalysisResult(diagnostics=(err_diag,), indexes=())

    monkeypatch.setattr("voss.cli.analyze", fake_analyze)
    runner = CliRunner()
    with runner.isolated_filesystem():
        path = _write("boom.voss", _CLEAN_SOURCE)
        result = runner.invoke(main, ["check", str(path)])
        assert result.exit_code != 0
        assert "ANLY999" in result.output
        assert "forced error for test" in result.output


def test_check_does_not_emit_indexes_or_cache_files():
    runner = CliRunner()
    with runner.isolated_filesystem() as fs:
        path = _write("clean.voss", _CLEAN_SOURCE)
        result = runner.invoke(
            main, ["check", "--cache-dir", ".voss-cache", str(path)]
        )
        assert result.exit_code == 0, result.output
        fs_path = Path(fs)
        assert not (fs_path / ".voss-cache").exists()
        assert not list(fs_path.glob("**/*.idx"))


def test_check_passes_emit_indexes_false_to_analyzer(monkeypatch):
    captured: dict = {}

    def fake_analyze(program, **kwargs):
        captured.update(kwargs)
        return AnalysisResult(diagnostics=(), indexes=())

    monkeypatch.setattr("voss.cli.analyze", fake_analyze)
    runner = CliRunner()
    with runner.isolated_filesystem():
        path = _write("clean.voss", _CLEAN_SOURCE)
        result = runner.invoke(main, ["check", str(path)])
        assert result.exit_code == 0, result.output
        assert captured.get("emit_indexes") is False
