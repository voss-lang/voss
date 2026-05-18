"""SKL-02 `add-test`: agentic, mutating pytest-test generator.

Agentic (D-07) — drives a model turn via `run_turn`. Mutating (D-09,
`mutating=True`): the agent locates a public function and writes a pytest
test through the gated `fs_write` tool. The skill performs NO direct write
itself — every mutation flows through `run_turn`'s tool dispatch, so the
standard permission gate + mode rules apply with NO skill-level escalation
or bypass (D-09/D-11). In `plan` mode the gated write is refused cleanly and
nothing is mutated. pytest is the confirmed project test framework.

The `.voss` companion at voss/harness/skills/voss/add-test.voss is a dogfood
demonstration (D-05), NOT the runtime exec path.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from ..agent import run_turn

_PROMPT = (
    "Generate a unit test for this project.\n\n"
    "1. Locate one public (non-underscore) function in a source module under "
    "the project root.\n"
    "2. Write a pytest test module to `tests/test_<module>.py` (where "
    "<module> is the source module's name) that imports the function and "
    "exercises it.\n"
    "3. The test MUST contain a DELIBERATELY FAILING assertion (assert the "
    "function returns a value it does not) so the planted test is RED by "
    "design.\n"
    "4. Create the file using the `fs_write` tool. Do NOT use any shell "
    "command. Do NOT write anywhere except the `tests/` directory under the "
    "project root.\n\n"
    "When the test file is written, you are done."
)


def run(
    *,
    cwd: Path,
    provider,
    history,
    record,
    renderer,
    tools,
    gate,
) -> None:
    asyncio.run(
        run_turn(
            _PROMPT,
            tools=tools,
            cwd=cwd,
            renderer=renderer,
            model=record.model,
            provider=provider,
            history=history,
            permissions=gate,
            cognition=None,
            session_id=record.id,
        )
    )
