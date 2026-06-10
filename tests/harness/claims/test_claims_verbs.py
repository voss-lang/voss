"""VBUS-01 two-agent stake/check/release acceptance sequence.

GREEN as of V17-03 (claims_group shipped). Serverless: storage at
<cwd>/.voss-cache/claims.sqlite (D-02), identity from VOSS_AGENT_ID
(exit 2 when absent).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from voss.harness.claims import claims_group

AGENT_A = {"VOSS_AGENT_ID": "agent-a"}
AGENT_B = {"VOSS_AGENT_ID": "agent-b"}


@pytest.mark.acceptance
class TestTwoAgentSequence:
    def test_full_sequence(self, tmp_path: Path) -> None:
        runner = CliRunner()
        cwd = ["--cwd", str(tmp_path)]

        staked = runner.invoke(
            claims_group, ["stake", "src/api/**", *cwd], env=AGENT_A
        )
        assert staked.exit_code == 0, staked.output

        # B checking inside A's claim → conflict, exit 1, names A
        conflict = runner.invoke(
            claims_group, ["check", "src/api/handlers.py", *cwd], env=AGENT_B
        )
        assert conflict.exit_code == 1
        assert "agent-a" in conflict.output

        # B checking a disjoint subtree → clear
        clear = runner.invoke(
            claims_group, ["check", "src/other/**", *cwd], env=AGENT_B
        )
        assert clear.exit_code == 0, clear.output

        # B staking the conflicting pattern → atomically rejected
        rejected = runner.invoke(
            claims_group, ["stake", "src/api/**", *cwd], env=AGENT_B
        )
        assert rejected.exit_code == 1

        # A releases, then B's stake succeeds
        released = runner.invoke(claims_group, ["release", *cwd], env=AGENT_A)
        assert released.exit_code == 0, released.output

        won = runner.invoke(
            claims_group, ["stake", "src/api/**", *cwd], env=AGENT_B
        )
        assert won.exit_code == 0, won.output


def test_missing_agent_id(tmp_path: Path) -> None:
    # VBUS-03 CLI side: no VOSS_AGENT_ID → exit 2, actionable stderr.
    result = CliRunner().invoke(
        claims_group,
        ["stake", "src/api/**", "--cwd", str(tmp_path)],
        env={"VOSS_AGENT_ID": None},
    )
    assert result.exit_code == 2
    assert "VOSS_AGENT_ID" in result.stderr
