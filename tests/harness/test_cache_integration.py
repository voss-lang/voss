"""CACHE-05 + CACHE-07 cassette proof for Anthropic prompt caching.

Replay-only in CI. Set VOSS_RECORD=1 with ANTHROPIC_API_KEY for the one-time
recording run.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

vcr = pytest.importorskip("vcr")

from voss.harness.agent import Plan, run_turn
from voss.harness.permissions import PermissionGate
from voss.harness.providers import Done, ParsedPlan, Usage
from voss.harness.render import PlainRenderer
from voss.harness.tools import make_toolset
from voss_runtime.providers.base import ProviderResponse
from voss_runtime.providers.litellm_provider import LiteLLMProvider


_CASSETTE_DIR = Path(__file__).parent / "fixtures" / "cassettes"
_MODEL = "claude-sonnet-4-5"


def _cassette(name: str):
    record_mode = "new_episodes" if os.environ.get("VOSS_RECORD") == "1" else "none"
    if record_mode == "none":
        os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-vcr-replay-placeholder")
    return vcr.use_cassette(
        str(_CASSETTE_DIR / f"{name}.yaml"),
        record_mode=record_mode,
        filter_headers=[
            "x-api-key",
            "authorization",
            "anthropic-api-key",
            "cookie",
            "set-cookie",
        ],
    )


def _cacheable_voss_md() -> str:
    # Anthropic requires a cache breakpoint to cover at least 1024 tokens.
    return "\n".join(
        f"Cache integration stable prefix line {idx}: Voss caches this context."
        for idx in range(1300)
    )


class CassetteLiteLLMProvider:
    """Streaming shim for run_turn that keeps the API hop on LiteLLM."""

    def __init__(self) -> None:
        self._delegate = LiteLLMProvider()

    async def complete(
        self,
        *,
        messages,
        model,
        response_format=None,
        tools=None,
        temperature=1.0,
        max_tokens=None,
        timeout=None,
    ) -> ProviderResponse:
        if response_format is not None and response_format.__name__ == "RunSemantics":
            parsed = response_format(goal="cache integration cassette")
            return ProviderResponse(
                text=parsed.model_dump_json(),
                model=model,
                prompt_tokens=1,
                completion_tokens=1,
                cost_usd=0.0,
                raw={"test_stub": "record_run"},
                parsed=parsed,
            )
        return await self._delegate.complete(
            messages=messages,
            model=model,
            response_format=response_format,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    async def stream(self, **kwargs):
        response = await self._delegate.complete(
            messages=kwargs["messages"],
            model=kwargs["model"],
            response_format=None,
            tools=kwargs.get("tools"),
            temperature=0.0,
            max_tokens=64,
            timeout=kwargs.get("timeout"),
        )
        yield ParsedPlan(
            Plan(
                rationale="cache integration cassette",
                steps=[],
                confidence=0.95,
                final_when_done=(response.text or "cache probe complete")[:200],
            )
        )
        yield Usage(
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            cost_usd=response.cost_usd,
            cache_creation_input_tokens=response.cache_creation_input_tokens,
            cache_read_input_tokens=response.cache_read_input_tokens,
        )
        yield Done(stop_reason="end_turn")

    def count_tokens(self, *, text: str, model: str) -> int:
        return self._delegate.count_tokens(text=text, model=model)


async def _run_one_turn(
    *, cwd: Path, provider: CassetteLiteLLMProvider, prompt: str
):
    result = await run_turn(
        prompt,
        tools=make_toolset(cwd),
        cwd=cwd,
        renderer=PlainRenderer(),
        model=_MODEL,
        provider=provider,
        permissions=PermissionGate(auto_yes=True),
        session_id="cache-two-turn-session",
        voss_md_text=_cacheable_voss_md(),
    )
    assert result.run is not None
    assert result.run.iterations
    return result.run.iterations[-1]


async def _run_two_turns(tmp_path: Path):
    provider = CassetteLiteLLMProvider()
    turn1 = await _run_one_turn(
        cwd=tmp_path,
        provider=provider,
        prompt="Hello, identify yourself and the model you are.",
    )
    turn2 = await _run_one_turn(
        cwd=tmp_path,
        provider=provider,
        prompt="Now describe one project you've helped with.",
    )
    return turn1, turn2


@pytest.mark.asyncio
async def test_first_turn_writes_cache(tmp_path: Path) -> None:
    with _cassette("cache_two_turn_session"):
        turn1, _turn2 = await _run_two_turns(tmp_path)

    assert turn1.cache_creation_input_tokens > 0
    assert turn1.cache_read_input_tokens == 0


@pytest.mark.asyncio
async def test_second_turn_reads_cache(tmp_path: Path) -> None:
    with _cassette("cache_two_turn_session"):
        _turn1, turn2 = await _run_two_turns(tmp_path)

    assert turn2.cache_read_input_tokens > 0
