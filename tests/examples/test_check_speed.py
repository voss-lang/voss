"""D-03 + D-13 check-time invariants. Sentinel + per-sample wall-clock gate."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

from tests.examples.helpers import copy_example, run_voss


CHECK_CEILING_SECONDS = 8.0
REPO_ROOT = Path(__file__).resolve().parents[2]


def test_check_does_not_load_hf_encoder() -> None:
    # Run in a CLEAN subprocess: in the full suite an earlier test may have
    # already imported sentence_transformers, so asserting on THIS process's
    # sys.modules is order-dependent. The subprocess proves analyze() itself
    # does not pull in the HF encoder (D-03).
    import json
    import subprocess

    script = (
        "import json, sys\n"
        "from voss import analyze, parse\n"
        "src = open('samples/support.voss').read()\n"
        "program = parse(src, file='samples/support.voss')\n"
        "result = analyze(program, source_path='samples/support.voss', emit_indexes=False)\n"
        "assert result.ok, [d.message for d in result.diagnostics]\n"
        "print(json.dumps(sorted(k for k in sys.modules if 'sentence_transformers' in k)))\n"
    )
    cp = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr
    offenders = json.loads(cp.stdout.strip().splitlines()[-1])
    assert offenders == [], f"D-03 violated: sentence_transformers loaded: {offenders}"


@pytest.mark.parametrize("sample", ["classify", "support", "research"])
def test_check_speed_under_ceiling(tmp_path: Path, sample: str) -> None:
    """D-13: voss check must complete under CHECK_CEILING_SECONDS for each sample."""
    copy_example(tmp_path, sample)
    run_voss(["check", f"{sample}.voss"], cwd=tmp_path)
    start = time.perf_counter()
    result = run_voss(["check", f"{sample}.voss"], cwd=tmp_path)
    elapsed = time.perf_counter() - start
    assert result.returncode == 0, result.stderr
    assert elapsed < CHECK_CEILING_SECONDS, (
        f"voss check {sample}.voss took {elapsed:.2f}s "
        f"(ceiling {CHECK_CEILING_SECONDS}s) — D-03 regression?"
    )
