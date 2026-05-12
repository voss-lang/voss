"""DOG-07 / D-12 (c): compiled harness CLI smoke exits 0 with output."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_dog07_voss_do_through_compiled_harness(precompiled_harness: Path) -> None:
    precompiled_harness.joinpath("fixture.md").write_text("noop fixture body\n")

    env = os.environ.copy()
    env["VOSS_HARNESS"] = "compiled"
    env["VOSS_HERMETIC"] = "1"

    result = subprocess.run(
        [sys.executable, "-m", "voss.cli", "do", "noop summary of fixture.md"],
        cwd=str(precompiled_harness),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()
