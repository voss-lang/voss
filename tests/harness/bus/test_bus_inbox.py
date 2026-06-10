"""VBUS-04 `voss bus inbox` cursor semantics — xfail until V15 ships.

Contract: inbox returns messages mentioning the caller since its last read;
a second call returns nothing (cursor advanced server-side, D-10).
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


def test_inbox_returns_unread_once_then_empty(tmp_path: Path) -> None:
    _require_bus()
    runner = CliRunner()
    with bus_server_env(tmp_path) as env:
        env_a = {**env, "VOSS_AGENT_ID": "agent-a"}
        env_b = {**env, "VOSS_AGENT_ID": "agent-b"}

        for body in ("@agent-a first-msg", "@agent-a second-msg"):
            sent = runner.invoke(bus_group, ["send", body], env=env_b)
            assert sent.exit_code == 0, sent.output

        first_read = runner.invoke(bus_group, ["inbox"], env=env_a)
        assert first_read.exit_code == 0, first_read.output
        assert "first-msg" in first_read.output
        assert "second-msg" in first_read.output

        second_read = runner.invoke(bus_group, ["inbox"], env=env_a)
        assert second_read.exit_code == 0, second_read.output
        assert "first-msg" not in second_read.output
        assert "second-msg" not in second_read.output
