from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from voss import analyze
from voss.diagnostics import AnalysisResult, Diagnostic, EmittedIndex

from tests.analyzer.conftest import program, span


def test_diagnostic_string_includes_location_severity_code_and_message():
    diag = Diagnostic(
        severity="warning",
        code="ANLY001",
        message="unguarded probable<string> used where string is expected",
        span=span("sample.voss", 12, 16),
        hint="Add a confidence gate such as if intent @ p >= 0.80 { ... }.",
    )
    text = str(diag)
    first_line, _, hint_line = text.partition("\n")
    assert first_line == (
        "sample.voss:12:16: warning ANLY001: "
        "unguarded probable<string> used where string is expected"
    )
    assert hint_line.strip().startswith("hint:")
    assert "confidence gate" in hint_line


def test_diagnostic_string_without_hint_has_no_trailing_newline():
    diag = Diagnostic(
        severity="error",
        code="ANLY999",
        message="boom",
        span=span("a.voss", 3, 4),
    )
    assert str(diag) == "a.voss:3:4: error ANLY999: boom"


def test_analysis_result_helpers_split_warnings_and_errors():
    warn = Diagnostic(
        severity="warning",
        code="ANLY001",
        message="w",
        span=span("a.voss", 1, 1),
    )
    err = Diagnostic(
        severity="error",
        code="ANLY050",
        message="e",
        span=span("a.voss", 2, 1),
    )
    result = AnalysisResult(diagnostics=(warn, err))
    assert result.warnings == (warn,)
    assert result.errors == (err,)
    assert result.ok is False

    clean = AnalysisResult(diagnostics=(warn,))
    assert clean.errors == ()
    assert clean.ok is True


def test_emitted_index_metadata_is_frozen():
    idx = EmittedIndex(
        match_id="m1",
        path=Path(".voss-cache/indexes/m1.json"),
        case_count=3,
        threshold=0.8,
        model="text-embedding-3-small",
    )
    assert idx.match_id == "m1"
    assert idx.case_count == 3
    with pytest.raises((FrozenInstanceError, AttributeError)):
        idx.case_count = 5  # type: ignore[misc]


def test_analyze_empty_program_returns_ok_result():
    result = analyze(program(), emit_indexes=False)
    assert isinstance(result, AnalysisResult)
    assert result.diagnostics == ()
    assert result.indexes == ()
    assert result.ok is True
