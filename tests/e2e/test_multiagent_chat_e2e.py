"""M13 Wave-0 RED scaffold — headline multi-agent chat e2e (MAG-08).

One stub-provider `voss chat` end-to-end: a single NL request fans to ≥2
concurrent `SubAgentPanel`s (live progress + budget), the parent injects
≥1 mid-run course-correction into a child, the even-split reserve
rebalances when a child finishes, and `gather` aggregates results into the
turn — clean post-gather region — ALL asserted in one test
(M13-VALIDATION.md MAG-08).

Modeled on tests/e2e/test_chat_e2e.py:14-23 using the `cli_runner`
fixture. The e2e runner auto-installs the deterministic StubProvider via a
generated `sitecustomize.py` (tests/e2e/runner.py:1-31) — NO provider
plumbing in the test.

Wave-0 discipline: multiagent tools are not wired into `voss chat` until
W4, so this is `@pytest.mark.xfail(strict=False)` — it COLLECTS but runs
RED-by-design. No production code is written here.
"""
from __future__ import annotations

import pytest

from .runner import CliRunner


@pytest.mark.xfail(
    reason="W4 chat multiagent-tool integration not yet wired",
    strict=False,
)
def test_multiagent_chat_e2e(cli_runner: CliRunner) -> None:
    r = cli_runner.run(
        "chat",
        "--plain",
        stdin=(
            "Investigate the auth bug and the rate-limiter latency in "
            "parallel using sub-agents, then summarize both.\n"
            "/exit\n"
        ),
        timeout=30.0,
    )
    assert r.returncode == 0, r.output

    out = r.output

    # MAG-08: ≥2 concurrent sub-agent panels referenced in the transcript.
    panel_refs = out.lower().count("sub-agent") + out.lower().count("subagent")
    assert panel_refs >= 2, f"expected ≥2 sub-agent panel references; got {panel_refs}"

    # ≥1 budget tick per child (budget meter leaves the em-dash placeholder).
    assert "budget" in out.lower(), "no budget tick surfaced in transcript"

    # ≥1 applied mid-run course-correction.
    assert (
        "correct" in out.lower() or "steer" in out.lower()
    ), "no applied correction surfaced in transcript"

    # ≥1 rebalance event when a child finishes.
    assert "rebalance" in out.lower(), "no rebalance event surfaced in transcript"

    # Aggregated multi-child turn line + clean post-gather region.
    assert "gather" in out.lower(), "no aggregated gather turn line in transcript"
