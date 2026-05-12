"""Doctor-row sentinel tests."""
from __future__ import annotations

from pathlib import Path

from voss.harness.diagnostics import CheckResult, run_all_checks


def test_doctor_reports_harness_cache_row(tmp_path: Path) -> None:
    results = run_all_checks(tmp_path)
    names = [check.name for check in results]

    assert "harness cache" in names
    check = results[names.index("harness cache")]
    assert check.result is CheckResult.OK
    assert check.detail == "no harness sources"
