"""M12-03: MCP server skill-execution bridge tests.

Proves one real deterministic skill (voss-lint-as-skill) runs end-to-end
through the bridge, unknown ids raise KeyError, the handler runs off the
event loop (asyncio.to_thread), and stdout capture is per-call.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import time
import types
from pathlib import Path

import pytest

from voss.harness.mcp.server_skills import make_skill_dispatch
from voss.harness.permissions import PermissionGate
from voss.harness.render import PlainRenderer
from voss.harness.skill_registry import default_skill_registry
from voss.harness.tools import make_toolset

FIXTURES = Path(__file__).resolve().parents[2] / "skills" / "fixtures"


def _real_dispatch(tmp_path: Path):
    tools = make_toolset(tmp_path)
    reg = default_skill_registry()
    return make_skill_dispatch(
        cwd=tmp_path,
        provider=None,
        history=None,
        record=types.SimpleNamespace(model="fake", id="t"),
        renderer=PlainRenderer(),
        tools=tools,
        gate=PermissionGate(auto_yes=True),
        skill_registry=reg,
    )


@pytest.mark.asyncio
async def test_voss_lint_as_skill_runs_through_bridge(tmp_path: Path) -> None:
    shutil.copy(FIXTURES / "voss-lint" / "bad.voss", tmp_path / "bad.voss")
    disp = _real_dispatch(tmp_path)

    text = await disp("voss-lint-as-skill", [str(tmp_path)])

    schema = json.loads(text)
    assert schema["version"] == 1
    assert schema["findings"], "expected the seeded bad.voss violation"
    assert any(f["rule"] == "ANLY001" for f in schema["findings"]), schema["findings"]


@pytest.mark.asyncio
async def test_unknown_skill_raises_key_error(tmp_path: Path) -> None:
    disp = _real_dispatch(tmp_path)
    with pytest.raises(KeyError, match="unknown skill: nope"):
        await disp("nope", [])


def _fake_registry(handler):
    entry = types.SimpleNamespace(id="x", mutating=False, handler=handler)
    return types.SimpleNamespace(get=lambda name: entry if name == "x" else None)


@pytest.mark.asyncio
async def test_dispatch_runs_in_thread_not_blocking_loop(tmp_path: Path) -> None:
    def _handler(ctx, args):
        time.sleep(0.05)
        print("done")

    disp = make_skill_dispatch(
        cwd=tmp_path,
        provider=None,
        history=None,
        record=types.SimpleNamespace(model="fake", id="t"),
        renderer=PlainRenderer(),
        tools=None,
        gate=PermissionGate(auto_yes=True),
        skill_registry=_fake_registry(_handler),
    )

    ticks = 0

    async def _tick() -> None:
        nonlocal ticks
        # If the bridge blocked the loop these would not advance during the
        # 50ms sleep inside the handler.
        for _ in range(5):
            await asyncio.sleep(0.001)
            ticks += 1

    out, _ = await asyncio.gather(disp("x", []), _tick())
    assert out == "done\n"
    assert ticks == 5


@pytest.mark.asyncio
async def test_per_call_stdout_isolation(tmp_path: Path) -> None:
    def _handler(ctx, args):
        print(args[0])

    disp = make_skill_dispatch(
        cwd=tmp_path,
        provider=None,
        history=None,
        record=types.SimpleNamespace(model="fake", id="t"),
        renderer=PlainRenderer(),
        tools=None,
        gate=PermissionGate(auto_yes=True),
        skill_registry=_fake_registry(_handler),
    )

    r1 = await disp("x", ["alpha"])
    r2 = await disp("x", ["beta"])
    assert r1 == "alpha\n"
    assert r2 == "beta\n"
