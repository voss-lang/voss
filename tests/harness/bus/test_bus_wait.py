"""VBUS-04 `voss bus wait` scaffold — xfail until V15 ships.

Contract: `wait --mention <me> --timeout <s>` blocks on the SSE stream,
unblocks within 2s of a matching `bus send`, prints the message, exit 0;
no match by the deadline → exit 124.
"""
from __future__ import annotations

import threading
import time
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


def test_wait_unblocks_on_matching_send(tmp_path: Path) -> None:
    _require_bus()
    with bus_server_env(tmp_path) as env:
        env_a = {**env, "VOSS_AGENT_ID": "agent-a"}
        env_b = {**env, "VOSS_AGENT_ID": "agent-b"}
        box: dict = {}

        def waiter() -> None:
            box["result"] = CliRunner().invoke(
                bus_group,
                ["wait", "--mention", "agent-a", "--timeout", "60"],
                env=env_a,
            )

        thread = threading.Thread(target=waiter)
        thread.start()
        time.sleep(0.5)  # let wait attach to the SSE stream

        sent = CliRunner().invoke(
            bus_group, ["send", "@agent-a done", "--label", "task-done"], env=env_b
        )
        assert sent.exit_code == 0, sent.output

        thread.join(timeout=2.5)  # VBUS-04: unblock within 2s of the send
        assert not thread.is_alive(), "bus wait did not unblock within 2s"
        result = box["result"]
        assert result.exit_code == 0, result.output
        assert "done" in result.output


def test_timeout(tmp_path: Path) -> None:
    _require_bus()
    with bus_server_env(tmp_path) as env:
        result = CliRunner().invoke(
            bus_group,
            ["wait", "--mention", "agent-a", "--timeout", "1"],
            env={**env, "VOSS_AGENT_ID": "agent-a"},
        )
        assert result.exit_code == 124
