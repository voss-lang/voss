"""M5 D-09: judge_run returns Verdict on valid JSON; ParseError -> skipped."""
import asyncio

from voss.eval.judge import Verdict, judge_run
from voss_runtime.providers.base import ProviderResponse
from voss_runtime.providers.litellm_provider import ParseError


class FakeJudgeProvider:
    def __init__(self, verdict: Verdict | None):
        self.verdict = verdict

    async def complete(self, *, messages, model, response_format=None, **kw):
        text = self.verdict.model_dump_json() if self.verdict else "{}"
        return ProviderResponse(
            text=text,
            model=model,
            prompt_tokens=1,
            completion_tokens=1,
            cost_usd=0.0,
            raw={},
            parsed=self.verdict,
        )

    def count_tokens(self, *, text, model):
        return 1


def test_judge_returns_verdict():
    fp = FakeJudgeProvider(Verdict(verdict="pass", confidence=0.9, rationale="ok"))
    verdict, verdict_str = asyncio.run(
        judge_run(
            provider=fp,
            model="m",
            task_prompt="t",
            final="f",
            file_diff="",
            rubric="r",
        )
    )
    assert verdict_str == "pass"
    assert verdict is not None
    assert verdict.confidence == 0.9


def test_judge_parse_error_returns_skipped():
    """RESEARCH Pattern 2 fallback: ParseError -> skipped."""

    class RaisingProvider:
        async def complete(self, **kw):
            raise ParseError("bad json")

        def count_tokens(self, **kw):
            return 1

    verdict, verdict_str = asyncio.run(
        judge_run(
            provider=RaisingProvider(),
            model="m",
            task_prompt="t",
            final="f",
            file_diff="",
            rubric="r",
        )
    )
    assert verdict is None
    assert verdict_str == "skipped"
