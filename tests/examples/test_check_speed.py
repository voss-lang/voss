"""D-03 + D-13 check-time invariants. Sentinel + per-sample wall-clock gate."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

from tests.examples.helpers import copy_example, run_voss


CHECK_CEILING_SECONDS = 2.0
REPO_ROOT = Path(__file__).resolve().parents[2]


def test_check_does_not_load_hf_encoder() -> None:
    from voss import analyze, parse

    src = (REPO_ROOT / "samples" / "support.voss").read_text()
    program = parse(src, file="samples/support.voss")
    result = analyze(program, source_path="samples/support.voss", emit_indexes=False)
    assert result.ok, [d.message for d in result.diagnostics]
    offenders = sorted(k for k in sys.modules if "sentence_transformers" in k)
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
