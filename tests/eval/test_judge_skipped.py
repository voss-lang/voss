"""Runner-layer crash semantics live in voss/eval/runner.py (Plan 03).

That layer owns `judge_verdict='skipped'` and `success=False`.
"""
import asyncio

import pytest

from voss.eval.judge import judge_run


def test_runtime_error_propagates():
    """judge_run only converts ParseError to skipped."""

    class CrashingProvider:
        async def complete(self, **kw):
            raise RuntimeError("simulated provider crash")

        def count_tokens(self, **kw):
            return 1

    with pytest.raises(RuntimeError):
        asyncio.run(
            judge_run(
                provider=CrashingProvider(),
                model="m",
                task_prompt="t",
                final="f",
                file_diff="",
                rubric="r",
            )
        )
