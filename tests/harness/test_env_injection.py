"""VBUS-03 agent identity — automatable CLI side.

GREEN as of V17-03 (claims verbs) + V17-04 (spawn injection). The full
end-to-end (live Tauri pane env contains VOSS_AGENT_ID) is manual-only —
see V17 VALIDATION. Automatable portion: claims verbs resolve identity
from VOSS_AGENT_ID (recorded as owner), and a bare invocation without the
var exits 2 with an actionable message.
"""
from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from voss.harness.claims import claims_group


def test_stake_records_env_agent_id_as_owner(tmp_path: Path) -> None:
    runner = CliRunner()
    env = {"VOSS_AGENT_ID": "claude-1"}

    staked = runner.invoke(
        claims_group, ["stake", "src/api/**", "--cwd", str(tmp_path)], env=env
    )
    assert staked.exit_code == 0, staked.output

    listed = runner.invoke(
        claims_group, ["list", "--json", "--cwd", str(tmp_path)], env=env
    )
    assert listed.exit_code == 0, listed.output
    records = [
        json.loads(line) for line in listed.output.splitlines() if line.strip()
    ]
    assert records, f"list --json returned nothing: {listed.output!r}"
    owners = {r.get("agent_id") or r.get("owner") for r in records}
    assert "claude-1" in owners, f"env identity not recorded as owner: {records!r}"


def test_bare_shell_without_var_exits_2(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        claims_group,
        ["stake", "src/api/**", "--cwd", str(tmp_path)],
        env={"VOSS_AGENT_ID": None},
    )
    assert result.exit_code == 2
    assert "VOSS_AGENT_ID" in result.stderr  # actionable: names the var to set
