"""DeterministicEMStub — scripted EM planner for tests (O5-03, OEM-04).

Production callers MUST NOT import this module. The stub yields scripted
EMPlanResponses with zero live LLM calls, mirroring the O3
DeterministicReviewerStub pattern.
"""
from __future__ import annotations

from .schema import EMPlanResponse, NoopOp


class DeterministicEMStub:
    """Yields scripted EMPlanResponses in order; zero LLM calls.

    On exhaustion, returns EMPlanResponse(ops=[NoopOp(reason="stub_exhausted")]).
    Records every call's kwargs in `self.calls` for test introspection.
    """

    def __init__(self, scripted: list[EMPlanResponse] | None = None) -> None:
        self._queue = list(scripted) if scripted else []
        self.calls: list[dict] = []

    async def plan(
        self,
        *,
        idea: str = "",
        snapshot: str = "",
        **kwargs,
    ) -> EMPlanResponse:
        self.calls.append({"idea": idea, "snapshot": snapshot, **kwargs})
        if self._queue:
            return self._queue.pop(0)
        return EMPlanResponse(ops=[NoopOp(op="noop", reason="stub_exhausted")])
