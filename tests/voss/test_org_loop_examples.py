"""V10 RED scaffold — org-loop sample files pass `voss check` (VLANG-08).

Parametrizes the three planned sample files. They do not exist yet AND use the
new V10 grammar, so `voss check` exits non-zero — RED expected. No expected-fail/skip masks
(gsd-scaffold-fictional-api).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from voss.cli import check

_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "sample",
    [
        "samples/team-orchestration.voss",
        "samples/reviewer-split.voss",
        "samples/audit-gates.voss",
    ],
)
def test_org_loop_examples_check_clean(sample: str) -> None:
    path = _REPO_ROOT / sample
    result = CliRunner().invoke(check, [str(path)])
    assert result.exit_code == 0, result.output
