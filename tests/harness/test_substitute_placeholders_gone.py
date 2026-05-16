"""T1 ITER-02 grep gate: _substitute_placeholders must stay deleted.

SPEC acceptance criterion 3: `grep -r _substitute_placeholders voss/`
returns zero matches. CI also runs this grep as an explicit workflow
step (.github/workflows/ci.yml); the pytest copy is a developer-local
safety net so the regression fails fast before push.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def test_substitute_placeholders_fully_removed() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    voss_dir = repo_root / "voss"
    result = subprocess.run(
        [
            "grep",
            "-rn",
            "--include=*.py",
            "--include=*.voss",
            "_substitute_placeholders",
            str(voss_dir),
        ],
        capture_output=True,
        text=True,
    )
    # grep returns 0 on match, 1 on no match. We want NO match.
    assert result.returncode != 0, (
        "_substitute_placeholders is forbidden (T1 ITER-02). "
        f"Matches found:\n{result.stdout}"
    )
