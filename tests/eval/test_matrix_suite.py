"""Matrix suite load + cognition-token scaffolds (EVGLD-01, EVGLD-04)."""
from __future__ import annotations

from pathlib import Path

import pytest

from voss.eval.suite import FileContainsCheck, load_suite

MATRIX_DIR = Path("tests/eval/matrix")

EXPECTED_CELL_IDS = frozenset(
    {
        "py-01-analyze",
        "py-02-plan-only",
        "py-03-approved-edit",
        "py-04-validation",
        "py-05-resume",
        "py-06-fetch-summarize",
        "rust-01-analyze",
        "rust-03-approved-edit",
        "rust-04-validation",
        "ts-01-analyze",
        "ts-03-approved-edit",
        "ts-04-validation",
    }
)

ANALYZE_COGNITION_TOKENS = {
    "py-01-analyze": "pyproject",
    "rust-01-analyze": "Cargo.toml",
    "ts-01-analyze": "package.json",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _matrix_present() -> bool:
    return (_repo_root() / MATRIX_DIR).is_dir()


pytestmark = pytest.mark.skipif(
    not _matrix_present(),
    reason="matrix suite not built yet",
)


def test_matrix_suite_loads() -> None:
    """EVGLD-01: matrix suite loads exactly 12 cells."""
    tasks = load_suite(MATRIX_DIR, suite="matrix")
    assert len(tasks) == 12


def test_matrix_all_cells_have_checks() -> None:
    """EVGLD-01: every matrix cell has at least one deterministic check."""
    tasks = load_suite(MATRIX_DIR, suite="matrix")
    assert all(len(spec.checks) >= 1 for _, spec in tasks), (
        "every matrix task must have at least one deterministic check"
    )


def test_matrix_cell_ids() -> None:
    """EVGLD-01: curated 12-cell matrix ids are present."""
    tasks = load_suite(MATRIX_DIR, suite="matrix")
    assert {task_id for task_id, _ in tasks} == EXPECTED_CELL_IDS


def test_matrix_cognition_token() -> None:
    """EVGLD-04: analyze cells gate on lang-correct manifest token in architecture.md."""
    tasks = dict(load_suite(MATRIX_DIR, suite="matrix"))
    for task_id, token in ANALYZE_COGNITION_TOKENS.items():
        checks = tasks[task_id].checks
        assert any(
            isinstance(c, FileContainsCheck)
            and c.path == ".voss/architecture.md"
            and token in c.text
            for c in checks
        ), f"{task_id} missing cognition FileContainsCheck for {token!r}"
