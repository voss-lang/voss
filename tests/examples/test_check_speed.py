"""D-03 + D-13 check-time invariants. Sentinel here; per-sample wall-clock gate lands in M3-06."""
from __future__ import annotations

import sys
from pathlib import Path


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
