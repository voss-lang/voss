from __future__ import annotations

import ast as _ast
from pathlib import Path

import pytest
from click.testing import CliRunner

from voss.ast_nodes import Span
from voss.cli import main
from voss.codegen import CodegenResult
from voss.diagnostics import AnalysisResult, Diagnostic


_SOURCE = "let x = 1\n"
_V10_TEAM_SOURCE = '''team Eng {
  ceiling { budget: 1000 tokens, scope: "src/**" }
  principles {
    diff: "Make the smallest diff."
  }
  gate done {
    require tests_passed
  }
  memory {
    decisions: ".voss/decisions"
  }
  roster e {
    backend { scope: "src/**" }
  }
}
'''
_V10_STANDALONE_COORDINATION_SOURCE = '''principles { diff: "Make the smallest diff." }
gate done { require tests_passed }
memory { decisions: ".voss/decisions" }
'''


def _write_source(name: str = "app.voss") -> Path:
    path = Path(name)
    path.write_text(_SOURCE)
    return path


def _ok_analysis(*diagnostics: Diagnostic) -> AnalysisResult:
    return AnalysisResult(diagnostics=tuple(diagnostics), indexes=())


def _fake_codegen(source: str = 'print("ok")\n') -> CodegenResult:
    return CodegenResult(
        source=source,
        imports=(),
        requires_async_main=False,
        analysis=None,
    )


def _patch_pipeline(monkeypatch, *, analysis: AnalysisResult, code: CodegenResult, captured: dict):
    def fake_analyze(program, **kwargs):
        captured.setdefault("analyze_kwargs", []).append(kwargs)
        return analysis

    def fake_generate(program, **kwargs):
        captured.setdefault("generate_kwargs", []).append(kwargs)
        return code

    monkeypatch.setattr("voss.cli.analyze", fake_analyze)
    monkeypatch.setattr("voss.cli.generate_python", fake_generate)


def test_compile_writes_default_source_py(monkeypatch):
    captured: dict = {}
    _patch_pipeline(
        monkeypatch,
        analysis=_ok_analysis(),
        code=_fake_codegen(),
        captured=captured,
    )
    runner = CliRunner()
    with runner.isolated_filesystem():
        path = _write_source()
        result = runner.invoke(main, ["compile", str(path)])
        assert result.exit_code == 0, result.output
        out = Path("app.py")
        assert out.exists()
        _ast.parse(out.read_text())


def test_compile_writes_explicit_output_atomically(monkeypatch):
    captured: dict = {}
    _patch_pipeline(
        monkeypatch,
        analysis=_ok_analysis(),
        code=_fake_codegen(),
        captured=captured,
    )
    runner = CliRunner()
    with runner.isolated_filesystem():
        path = _write_source()
        result = runner.invoke(
            main, ["compile", str(path), "--output", "build/out.py"]
        )
        assert result.exit_code == 0, result.output
        out = Path("build/out.py")
        assert out.exists()
        _ast.parse(out.read_text())


def test_compile_prints_warnings_but_writes_when_no_errors(monkeypatch):
    warning = Diagnostic(
        severity="warning",
        code="ANLY001",
        message="probable unguarded",
        span=Span(file="app.voss", line_start=1, col_start=1, line_end=1, col_end=1),
    )
    captured: dict = {}
    _patch_pipeline(
        monkeypatch,
        analysis=_ok_analysis(warning),
        code=_fake_codegen(),
        captured=captured,
    )
    runner = CliRunner()
    with runner.isolated_filesystem():
        path = _write_source()
        result = runner.invoke(main, ["compile", str(path)])
        assert result.exit_code == 0, result.output
        assert "ANLY001" in result.output
        assert Path("app.py").exists()


def test_compile_blocks_on_analyzer_errors_without_write(monkeypatch):
    err = Diagnostic(
        severity="error",
        code="ANLY999",
        message="boom",
        span=Span(file="app.voss", line_start=1, col_start=1, line_end=1, col_end=1),
    )
    captured: dict = {}

    def fake_generate(program, **kwargs):
        captured["generate_called"] = True
        return _fake_codegen()

    monkeypatch.setattr("voss.cli.analyze", lambda program, **kw: _ok_analysis(err))
    monkeypatch.setattr("voss.cli.generate_python", fake_generate)

    runner = CliRunner()
    with runner.isolated_filesystem():
        path = _write_source()
        result = runner.invoke(main, ["compile", str(path)])
        assert result.exit_code != 0
        assert "ANLY999" in result.output
        assert not Path("app.py").exists()
        assert "generate_called" not in captured


@pytest.mark.parametrize(
    "body",
    [_V10_TEAM_SOURCE, _V10_STANDALONE_COORDINATION_SOURCE],
)
def test_compile_accepts_v10_coordination_declarations(body: str) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        path = Path("coord.voss")
        path.write_text(body, encoding="utf-8")
        result = runner.invoke(main, ["compile", str(path)])
        assert result.exit_code == 0, result.output
        out = Path("coord.py")
        assert out.exists()
        _ast.parse(out.read_text())


def test_compile_passes_emit_indexes_true(monkeypatch):
    captured: dict = {}
    _patch_pipeline(
        monkeypatch,
        analysis=_ok_analysis(),
        code=_fake_codegen(),
        captured=captured,
    )
    runner = CliRunner()
    with runner.isolated_filesystem():
        path = _write_source()
        result = runner.invoke(main, ["compile", str(path)])
        assert result.exit_code == 0, result.output
        assert captured["analyze_kwargs"][0].get("emit_indexes") is True


def test_compile_uses_public_generate_python_with_analysis(monkeypatch):
    analysis = _ok_analysis()
    captured: dict = {}
    _patch_pipeline(
        monkeypatch,
        analysis=analysis,
        code=_fake_codegen(),
        captured=captured,
    )
    runner = CliRunner()
    with runner.isolated_filesystem():
        path = _write_source()
        result = runner.invoke(main, ["compile", str(path)])
        assert result.exit_code == 0, result.output
        gen_kwargs = captured["generate_kwargs"][0]
        assert gen_kwargs.get("analysis") is analysis
        assert "source_path" in gen_kwargs
        assert "cache_dir" in gen_kwargs
