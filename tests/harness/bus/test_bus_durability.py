"""VBUS-05 durable journal across server restart — xfail until V15 ships.

Contract (D-10): messages append to <cwd>/.voss/bus/messages.jsonl, per-agent
cursors in cursors.json; after a server kill + restart, `inbox` still returns
the pre-restart unread message.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from . import bus_server_env

try:
    from voss.harness.bus_client import bus_group
    _BUS_AVAILABLE = True
except ImportError:
    bus_group = None  # type: ignore[assignment]
    _BUS_AVAILABLE = False

pytestmark = pytest.mark.xfail(
    reason="bus is V15-gated — implemented in V17-05/V17-06 after V15 ships",
    strict=False,
)


def _require_bus() -> None:
    if not _BUS_AVAILABLE:
        pytest.fail("voss.harness.bus_client not importable yet (V17-06, V15-gated)")


def test_unread_message_survives_server_restart(tmp_path: Path) -> None:
    _require_bus()
    runner = CliRunner()

    # Server lifetime 1: send, do NOT read.
    with bus_server_env(tmp_path) as env:
        sent = runner.invoke(
            bus_group,
            ["send", "@agent-a pre-restart-msg"],
            env={**env, "VOSS_AGENT_ID": "agent-b"},
        )
        assert sent.exit_code == 0, sent.output

    # Journal persisted on disk between lifetimes.
    assert (tmp_path / ".voss" / "bus" / "messages.jsonl").exists()

    # Server lifetime 2 (restart): unread message still delivered.
    with bus_server_env(tmp_path) as env:
        inbox = runner.invoke(
            bus_group, ["inbox"], env={**env, "VOSS_AGENT_ID": "agent-a"}
        )
        assert inbox.exit_code == 0, inbox.output
        assert "pre-restart-msg" in inbox.output
