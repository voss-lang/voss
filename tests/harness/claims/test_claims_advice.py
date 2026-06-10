"""VBUS-06 advice arrays on conflict.

GREEN as of V17-03. `claims check --json` on conflict emits a dict with a
non-empty "advice" list containing a runnable `voss bus send` command
naming the conflicting owner (D-07).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from voss.harness.claims import claims_group


@pytest.mark.acceptance
def test_check_conflict_json_emits_advice(tmp_path: Path) -> None:
    runner = CliRunner()
    cwd = ["--cwd", str(tmp_path)]

    staked = runner.invoke(
        claims_group, ["stake", "src/api/**", *cwd], env={"VOSS_AGENT_ID": "agent-a"}
    )
    assert staked.exit_code == 0, staked.output

    conflict = runner.invoke(
        claims_group,
        ["check", "src/api/handlers.py", "--json", *cwd],
        env={"VOSS_AGENT_ID": "agent-b"},
    )
    assert conflict.exit_code == 1

    records = [
        json.loads(line) for line in conflict.output.splitlines() if line.strip()
    ]
    advised = [r for r in records if isinstance(r, dict) and r.get("advice")]
    assert advised, f"no advice array in conflict output: {conflict.output!r}"

    advice = advised[0]["advice"]
    assert isinstance(advice, list) and advice
    assert all(isinstance(a, str) for a in advice)

    bus_hints = [a for a in advice if a.startswith("voss bus send")]
    assert bus_hints, f"no runnable `voss bus send` hint in advice: {advice!r}"
    assert any("agent-a" in a for a in bus_hints), (
        f"advice does not name the conflicting owner agent-a: {bus_hints!r}"
    )
