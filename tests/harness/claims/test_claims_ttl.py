"""VBUS-02 TTL behavior.

GREEN as of V17-03. `--ttl <seconds>` on stake (default 1800); expired
claims stop blocking `check` and are ignored by `stake`.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from voss.harness.claims import claims_group

AGENT_A = {"VOSS_AGENT_ID": "agent-a"}
AGENT_B = {"VOSS_AGENT_ID": "agent-b"}


@pytest.mark.slow
def test_ttl_expiry_unblocks_check(tmp_path: Path) -> None:
    runner = CliRunner()
    cwd = ["--cwd", str(tmp_path)]

    staked = runner.invoke(
        claims_group, ["stake", "src/api/**", "--ttl", "1", *cwd], env=AGENT_A
    )
    assert staked.exit_code == 0, staked.output

    blocked = runner.invoke(
        claims_group, ["check", "src/api/handlers.py", *cwd], env=AGENT_B
    )
    assert blocked.exit_code == 1

    time.sleep(1.2)  # past the 1s TTL

    clear = runner.invoke(
        claims_group, ["check", "src/api/handlers.py", *cwd], env=AGENT_B
    )
    assert clear.exit_code == 0, clear.output


def test_default_ttl_applied_when_flag_absent(tmp_path: Path) -> None:
    runner = CliRunner()
    before = time.time()

    staked = runner.invoke(
        claims_group, ["stake", "src/api/**", "--cwd", str(tmp_path)], env=AGENT_A
    )
    assert staked.exit_code == 0, staked.output

    listed = runner.invoke(
        claims_group,
        ["list", "--json", "--cwd", str(tmp_path)],
        env=AGENT_A,
    )
    assert listed.exit_code == 0, listed.output
    records = [
        json.loads(line) for line in listed.output.splitlines() if line.strip()
    ]
    expiries = [r["expires_at"] for r in records if "expires_at" in r]
    assert expiries, f"no expires_at in list --json output: {listed.output!r}"
    # Default TTL is 1800s — expiry must land ~30 min out, not seconds.
    assert all(e >= before + 1700 for e in expiries), expiries
