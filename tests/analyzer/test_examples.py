from __future__ import annotations

import json
from pathlib import Path

import pytest

from voss import analyze, parse

EXAMPLES = Path(__file__).resolve().parent.parent / "parser" / "examples"


class FakeIndexBuilder:
    model = "fake-embedding-model"

    def build_cases(self, cases):
        return [
            {
                "label": label,
                "description": description,
                "embedding": [float(i), 0.0],
            }
            for i, (description, label) in enumerate(cases)
        ]


def _load(name: str):
    path = EXAMPLES / name
    if not path.exists():
        pytest.skip("Phase 2 parser examples not present")
    return parse(path.read_text(), file=name)


def test_classify_example_analyzes_without_probable_warning():
    program = _load("classify.voss")
    result = analyze(
        program,
        emit_indexes=False,
        index_builder=FakeIndexBuilder(),
    )
    assert [d for d in result.diagnostics if d.code == "ANLY001"] == []


def test_support_example_emits_semantic_index(tmp_path):
    program = _load("support.voss")
    result = analyze(
        program,
        source_path="support.voss",
        project_root=tmp_path,
        cache_dir=".voss-cache",
        index_builder=FakeIndexBuilder(),
    )
    target = tmp_path / ".voss-cache" / "support.idx"
    assert target.exists()
    data = json.loads(target.read_text())
    assert data["program"] == "support"
    assert data["model"] == "fake-embedding-model"
    assert len(data["matches"]) >= 1
    entry = data["matches"][0]
    assert len(entry["cases"]) == 3
    assert result.indexes
    assert result.indexes[0].path.name == "support.idx"


def test_research_example_ctx_budgets_do_not_emit_static_warning():
    program = _load("research.voss")
    result = analyze(
        program,
        emit_indexes=False,
        index_builder=FakeIndexBuilder(),
    )
    assert [d for d in result.diagnostics if d.code == "ANLY002"] == []


def test_assistant_example_response_value_warns_until_gated():
    program = _load("assistant.voss")
    result = analyze(
        program,
        emit_indexes=False,
        index_builder=FakeIndexBuilder(),
    )
    warns = [d for d in result.diagnostics if d.code == "ANLY001"]
    assert len(warns) >= 1
    assert any("probable<string>" in d.message for d in warns)


# D-07 coverage: memory.semantic (test-only fixture).
def test_memory_semantic_coverage_analyzes_clean():
    program = _load("coverage/memory_semantic.voss")
    result = analyze(
        program,
        source_path="coverage/memory_semantic.voss",
        emit_indexes=False,
        index_builder=FakeIndexBuilder(),
    )
    assert result.ok, [d.message for d in result.diagnostics]
    errors = [d for d in result.diagnostics if str(getattr(d, "severity", "error")).lower() == "error"]
    assert errors == [], errors


# D-07 coverage: memory.working (test-only fixture).
def test_memory_working_coverage_analyzes_clean():
    program = _load("coverage/memory_working.voss")
    result = analyze(
        program,
        source_path="coverage/memory_working.voss",
        emit_indexes=False,
        index_builder=FakeIndexBuilder(),
    )
    assert result.ok, [d.message for d in result.diagnostics]
    errors = [d for d in result.diagnostics if str(getattr(d, "severity", "error")).lower() == "error"]
    assert errors == [], errors
