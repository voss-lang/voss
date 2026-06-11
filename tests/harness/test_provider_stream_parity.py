"""T1-03 Task 2: cross-provider parity — same logical Plan via both stream() paths.

SPEC ITER-03: "both providers pass a parity test against a recorded fixture
stream". Asymmetry tolerated — Anthropic emits ToolUseStart/Delta/End,
OpenAI does not (Plan parse goes through accumulated output_text chunks
in `text.format` json_schema mode).
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx
import pytest

from voss.harness import auth as A
from voss.harness.agent import Plan
from voss.harness.providers import (
    AnthropicOAuthProvider,
    Done,
    OpenAIOAuthProvider,
    ParsedPlan,
    TextDelta,
    ToolUseDelta,
    ToolUseEnd,
    ToolUseStart,
)


FIXTURES = Path(__file__).parent / "fixtures"


def _anth_creds() -> A.AnthropicOAuthCreds:
    return A.AnthropicOAuthCreds(
        access_token="sk-ant-oat01-A",
        refresh_token="sk-ant-ort01-R",
        expires_at_ms=int((time.time() + 3600) * 1000),
        subscription_type="max",
    )


def _oa_creds() -> A.CodexCreds:
    return A.CodexCreds(
        api_key=None,
        access_token="acc",
        refresh_token="ref",
        account_id="acct_42",
        auth_mode="chatgpt",
    )


def _client_for(fixture_path: Path) -> httpx.AsyncClient:
    body = fixture_path.read_bytes()

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=body, headers={"content-type": "text/event-stream"}
        )

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_both_providers_yield_same_logical_plan() -> None:
    anth = AnthropicOAuthProvider(
        _anth_creds(), client=_client_for(FIXTURES / "anthropic_stream_parity.sse")
    )
    oa = OpenAIOAuthProvider(
        _oa_creds(), client=_client_for(FIXTURES / "openai_stream_parity.sse")
    )

    async def drain(p, **kwargs):
        out = []
        async for ev in p.stream(**kwargs):
            out.append(ev)
        return out

    anth_events = await drain(
        anth,
        messages=[{"role": "user", "content": "hi"}],
        model="claude-sonnet-4-5",
        response_format=Plan,
    )
    oa_events = await drain(
        oa,
        messages=[{"role": "user", "content": "hi"}],
        model="gpt-5",
        response_format=Plan,
    )

    # Both streams produce >=1 TextDelta.
    assert sum(1 for e in anth_events if isinstance(e, TextDelta)) >= 1
    assert sum(1 for e in oa_events if isinstance(e, TextDelta)) >= 1

    # Each stream emits exactly one ParsedPlan with the same locked fields.
    anth_parsed = [e for e in anth_events if isinstance(e, ParsedPlan)]
    oa_parsed = [e for e in oa_events if isinstance(e, ParsedPlan)]
    assert len(anth_parsed) == 1
    assert len(oa_parsed) == 1

    for parsed in (anth_parsed[0], oa_parsed[0]):
        assert isinstance(parsed.plan, Plan)
        assert parsed.plan.rationale == "parity rationale"
        assert parsed.plan.confidence == pytest.approx(0.85)
        assert parsed.plan.final_when_done == "parity"

    # Each stream ends with exactly one Done.
    assert sum(1 for e in anth_events if isinstance(e, Done)) == 1
    assert sum(1 for e in oa_events if isinstance(e, Done)) == 1
    assert isinstance(anth_events[-1], Done)
    assert isinstance(oa_events[-1], Done)

    # Anthropic-only asymmetry: exactly one ToolUseStart(submit_response),
    # >=1 ToolUseDelta, exactly one ToolUseEnd.
    tu_starts = [e for e in anth_events if isinstance(e, ToolUseStart)]
    tu_deltas = [e for e in anth_events if isinstance(e, ToolUseDelta)]
    tu_ends = [e for e in anth_events if isinstance(e, ToolUseEnd)]
    assert len(tu_starts) == 1 and tu_starts[0].name == "submit_response"
    assert len(tu_deltas) >= 1
    assert len(tu_ends) == 1

    # OpenAI has none of those.
    assert not any(isinstance(e, ToolUseStart) for e in oa_events)
    assert not any(isinstance(e, ToolUseDelta) for e in oa_events)
    assert not any(isinstance(e, ToolUseEnd) for e in oa_events)


@pytest.mark.asyncio
async def test_claude_agent_provider_matches_parity_contract() -> None:
    """ClaudeAgentProvider joins the OpenAI side of the documented asymmetry:
    Plan comes from accumulated text / structured_output, never ToolUse* events.
    Fake SDK messages stand in for the recorded SSE fixtures (the SDK speaks
    NDJSON over a subprocess, not SSE)."""
    import json as _json

    from voss.harness.claude_agent_provider import ClaudeAgentProvider

    plan_json = _json.dumps(
        {
            "rationale": "parity rationale",
            "steps": [],
            "confidence": 0.85,
            "open_question": None,
            "final_when_done": "parity",
        }
    )

    class _Text:
        def __init__(self, text: str) -> None:
            self.text = text

    class _Assistant:
        def __init__(self, blocks: list) -> None:
            self.content = blocks

    class _Result:
        total_cost_usd = 0.0
        is_error = False
        subtype = "success"
        structured_output = None
        result = None
        stop_reason = "end_turn"
        usage = {"input_tokens": 120, "output_tokens": 60}

    async def fake_query(*, prompt, options):
        yield _Assistant([_Text(plan_json)])
        yield _Result()

    p = ClaudeAgentProvider(query_fn=fake_query)
    events = []
    async for ev in p.stream(
        messages=[{"role": "user", "content": "hi"}],
        model="claude-sonnet-4-5",
        response_format=Plan,
    ):
        events.append(ev)

    assert sum(1 for e in events if isinstance(e, TextDelta)) >= 1

    parsed = [e for e in events if isinstance(e, ParsedPlan)]
    assert len(parsed) == 1
    assert isinstance(parsed[0].plan, Plan)
    assert parsed[0].plan.rationale == "parity rationale"
    assert parsed[0].plan.confidence == pytest.approx(0.85)
    assert parsed[0].plan.final_when_done == "parity"

    assert sum(1 for e in events if isinstance(e, Done)) == 1
    assert isinstance(events[-1], Done)

    # Joins the OpenAI side: zero ToolUse* events.
    assert not any(
        isinstance(e, (ToolUseStart, ToolUseDelta, ToolUseEnd)) for e in events
    )
