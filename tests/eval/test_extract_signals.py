from __future__ import annotations

from pathlib import Path

import pytest

from voss.eval.runner import _extract_signals
from voss.harness.session import SessionRecord


@pytest.mark.parametrize("confidence,expected", [(None, None), (0.7, 0.7)])
def test_extract_signals_drops_unknown_confidence(tmp_path: Path, confidence, expected) -> None:
    record = SessionRecord.new(cwd=tmp_path, model="stub")
    record.runs.append({"cost_usd": 0.01, "plan": {"confidence": confidence}})
    assert _extract_signals(record) == (0.01, expected)
