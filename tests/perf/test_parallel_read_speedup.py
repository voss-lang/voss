"""T2-06 / PAR-05: partition scheduler speedup gate.

Self-contained, deterministic benchmark proving the T2-03 partition
scheduler achieves ≥40% wall-clock drop on a 6-step read batch vs.
serial baseline. Uses STUB tools with asyncio.sleep (no live disk or
network — SPEC PAR-05 line 62) so timing stays stable across CI.

Two acceptance tests:
1. test_parallel_read_speedup_default_cap — cap=8 vs cap=1, ratio ≤ 0.6
2. test_parallel_read_speedup_cap_1_sanity — cap=1 wall-clock ≥ 250ms
   (forced-serial proof; safety net for any parallelism leak regression)

Tests do NOT use a recorder; scheduler timing is isolated from recorder
overhead.
"""
from __future__ import annotations

import asyncio
import time

import pytest

from voss.harness.agent import Plan, ToolCall, _run_step_loop
from voss.harness.tools import ToolEntry
from voss_runtime import configure, tool
from voss_runtime._config import reset_config


SLEEP_S = 0.05  # 50ms per stub read; 6 × 50ms = 300ms serial baseline
N_READS = 6


@tool(name="slow_read", description="Stub read that sleeps to model IO latency.")
async def _slow_read(path: str) -> str:
    await asyncio.sleep(SLEEP_S)
    return f"contents of {path}"


SLOW_TOOLS: dict[str, ToolEntry] = {
    "slow_read": ToolEntry(descriptor=_slow_read, is_mutating=False),
}


class _NullRenderer:
    """Minimal Renderer stub. Scheduler only calls show_tool_call per step."""

    def show_tool_call(self, *a, **kw) -> None: pass
    def stream_delta(self, *a, **kw) -> None: pass
    def finalize_stream(self, *a, **kw) -> None: pass


def _make_plan(n: int) -> Plan:
    return Plan(
        rationale="benchmark",
        steps=[ToolCall(name="slow_read", args={"path": f"f{i}.txt"}) for i in range(n)],
        confidence=1.0,
        final_when_done="ok",
    )


@pytest.fixture(autouse=True)
def _reset_runtime():
    reset_config()
    yield
    reset_config()


async def test_parallel_read_speedup_default_cap() -> None:
    """SPEC PAR-05 Success Criteria #1: parallel ≤ 60% × serial (≥40% drop)."""
    plan = _make_plan(N_READS)

    configure(max_parallel_reads=8)
    t0 = time.perf_counter()
    await _run_step_loop(
        plan.steps, SLOW_TOOLS, None, _NullRenderer(), recorder=None
    )
    parallel_ms = (time.perf_counter() - t0) * 1000

    configure(max_parallel_reads=1)
    t0 = time.perf_counter()
    await _run_step_loop(
        plan.steps, SLOW_TOOLS, None, _NullRenderer(), recorder=None
    )
    serial_ms = (time.perf_counter() - t0) * 1000

    print(
        f"\n[T2-06] parallel={parallel_ms:.1f}ms serial={serial_ms:.1f}ms "
        f"ratio={parallel_ms / serial_ms:.3f}"
    )
    assert parallel_ms <= serial_ms * 0.6, (
        f"parallel {parallel_ms:.1f}ms not <= 60% of serial {serial_ms:.1f}ms"
    )


async def test_parallel_read_speedup_cap_1_sanity() -> None:
    """Cap=1 forces serial: 6 × 50ms = 300ms ± slop; ≥250ms floor catches leaks."""
    configure(max_parallel_reads=1)
    plan = _make_plan(N_READS)
    t0 = time.perf_counter()
    await _run_step_loop(
        plan.steps, SLOW_TOOLS, None, _NullRenderer(), recorder=None
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    print(f"\n[T2-06] cap=1 elapsed={elapsed_ms:.1f}ms (expected ~300ms)")
    assert elapsed_ms >= 250, (
        f"cap=1 ran too fast ({elapsed_ms:.1f}ms) — parallelism leaked"
    )
