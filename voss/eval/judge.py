"""LLM-as-judge scorer (M5 D-08, D-09)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from voss_runtime.providers.base import ModelProvider
from voss_runtime.providers.litellm_provider import ParseError


class Verdict(BaseModel):
    """Judge response, pydantic-validated via response_format=Verdict."""

    model_config = ConfigDict(extra="ignore")

    verdict: Literal["pass", "fail"]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


JUDGE_SYSTEM = """You are an evaluator. Given a task prompt, the agent's final
answer, an optional file diff, and a rubric, decide if the run passed or failed.
Return ONLY a JSON object: {"verdict": "pass"|"fail", "confidence": 0.0-1.0,
"rationale": "<one paragraph>"}.
"""


async def judge_run(
    *,
    provider: ModelProvider,
    model: str,
    task_prompt: str,
    final: str,
    file_diff: str,
    rubric: str,
) -> tuple[Verdict | None, str]:
    """Return (Verdict, judge_verdict_str). On ParseError, returns (None, "skipped")."""
    user_msg = (
        f"## Task prompt\n{task_prompt}\n\n"
        f"## Agent final\n{final}\n\n"
        f"## File diff\n{file_diff}\n\n"
        f"## Rubric\n{rubric}\n"
    )
    try:
        resp = await provider.complete(
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            model=model,
            response_format=Verdict,
            temperature=0.0,
        )
    except ParseError:
        return None, "skipped"
    if resp.parsed is None:
        return None, "skipped"
    return resp.parsed, resp.parsed.verdict
