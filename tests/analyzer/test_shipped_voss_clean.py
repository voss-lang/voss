from __future__ import annotations

import subprocess
from pathlib import Path

from voss import analyze, parse

REPO_ROOT = Path(__file__).resolve().parents[2]
SKIPPED_PREFIX = "tests/skills/fixtures/"


def test_no_shipped_voss_file_gates_on_unmeasured_confidence():
    listed = subprocess.run(
        ["git", "ls-files", "*.voss"], cwd=REPO_ROOT, text=True, capture_output=True, check=True
    ).stdout.split()
    shipped = [rel for rel in listed if not rel.startswith(SKIPPED_PREFIX)]
    assert "samples/classify.voss" in shipped
    assert "voss/harness/agent/loop.voss" in shipped

    flagged = []
    for rel in shipped:
        program = parse((REPO_ROOT / rel).read_text(), file=rel)
        result = analyze(program, source_path=rel, emit_indexes=False)
        if any(d.code == "ANLY004" for d in result.diagnostics):
            flagged.append(rel)
    assert flagged == []
