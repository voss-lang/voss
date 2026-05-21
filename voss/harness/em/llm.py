"""EM LLM call wrapper — mirrors voss/eval/judge.py:judge_run (O5-03, OEM-03).

Async `em_plan(...)` calls provider.complete with response_format=EMPlanResponse
and temperature=0.0. On ParseError or parsed=None, returns a Noop fallback
(never raises for parse failures — only other exceptions bubble).
"""
from __future__ import annotations

from voss_runtime.exceptions import ParseError
from voss_runtime.providers.base import ModelProvider

from .schema import EMPlanResponse, NoopOp


EM_SYSTEM = """\
You are the Engineering Manager (EM) in a caged autonomous engineering team.

Your authority:
  - Create tickets from the original human idea
  - Dispatch cards to roster roles (backend, frontend, ui, ai)
  - Kill or rescope cards that are off-track
  - Set acceptance criteria and definition of done

Cage rules (immutable — you CANNOT override these):
  - You cannot change the ceiling or risk thresholds
  - You cannot invent new agents or register roles outside the declared roster
  - You cannot extend or reallocate budget
  - The audit bar is the original idea, not your AC/DoD

If nothing needs to happen this iteration, emit a noop op with a reason.

Return a JSON object matching the EMPlanResponse schema:
{
  "ops": [{"op": "create_ticket", ...}, {"op": "dispatch_card", ...}, ...],
  "reasoning": "<your scratchpad>"
}
"""


async def em_plan(
    *,
    provider: ModelProvider,
    model: str,
    idea: str,
    snapshot: str,
    roster_descriptions: dict[str, str] | None = None,
) -> EMPlanResponse:
    """Call the EM LLM and parse the structured response.

    On ParseError or parsed=None, returns EMPlanResponse(ops=[NoopOp(reason="parse_failure")]).
    On other exceptions, re-raises (the loop's responsibility to handle).
    """
    roster_text = ""
    if roster_descriptions:
        lines = [f"  - {role}: {desc}" for role, desc in roster_descriptions.items()]
        roster_text = "\n## Available Roster Roles\n" + "\n".join(lines) + "\n"

    user_msg = (
        f"## Original Idea\n{idea}\n\n"
        f"## Current Board Snapshot\n{snapshot}\n"
        f"{roster_text}"
    )

    try:
        resp = await provider.complete(
            messages=[
                {"role": "system", "content": EM_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            model=model,
            response_format=EMPlanResponse,
            temperature=0.0,
        )
    except ParseError:
        return EMPlanResponse(ops=[NoopOp(op="noop", reason="parse_failure")])

    if resp.parsed is None:
        return EMPlanResponse(ops=[NoopOp(op="noop", reason="parse_failure")])

    return resp.parsed
