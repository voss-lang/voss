"""CACHE-05 + CACHE-07 cassette proof for Anthropic OAuth prompt caching.

Replay-only in CI. Set VOSS_RECORD=1 to record through Claude Code OAuth.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

vcr = pytest.importorskip("vcr")

from voss.harness import auth
from voss.harness.agent import run_turn
from voss.harness.permissions import PermissionGate
from voss.harness.providers import AnthropicOAuthProvider
from voss.harness.render import PlainRenderer
from voss_runtime.providers.base import ProviderResponse


_CASSETTE_DIR = Path(__file__).parent / "fixtures" / "cassettes"
_MODEL = "claude-sonnet-4-5"


def _cassette(name: str):
    record_mode = "new_episodes" if os.environ.get("VOSS_RECORD") == "1" else "none"
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
        before_record_response=_redact_response_headers,
    )


def _redact_response_headers(response):
    headers = response.get("headers", {})
    for key in list(headers):
        if key.lower() in {"cookie", "set-cookie"}:
            headers.pop(key, None)
    return response


def _cacheable_voss_md() -> str:
    # Anthropic requires a cache breakpoint to cover at least 1024 tokens.
    return "\n".join(
        f"OAuth cache integration v2 stable prefix line {idx}: Voss caches this context."
        for idx in range(1300)
    )


def _oauth_creds() -> auth.AnthropicOAuthCreds:
    if os.environ.get("VOSS_RECORD") == "1":
        resolved = auth.resolve("claude")
        if resolved.anthropic_oauth is None:
            pytest.skip(f"Claude OAuth unavailable for recording: {resolved.detail}")
        return resolved.anthropic_oauth

    return auth.AnthropicOAuthCreds(
        access_token="vcr-replay-token",
        refresh_token="vcr-replay-refresh",
        expires_at_ms=int((time.time() + 3600) * 1000),
        subscription_type="replay",
    )


class CassetteOAuthProvider(AnthropicOAuthProvider):
    """OAuth provider with local record_run close-out to keep cassette focused."""

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
        return await super().complete(
            messages=messages,
            model=model,
            response_format=response_format,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )


async def _run_one_turn(
    *, cwd: Path, provider: CassetteOAuthProvider, prompt: str
):
    result = await run_turn(
        prompt,
        tools={},
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
    provider = CassetteOAuthProvider(_oauth_creds())
    try:
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
    finally:
        await provider.aclose()


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
