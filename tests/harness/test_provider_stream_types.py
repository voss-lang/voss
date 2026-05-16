"""T1-02: ProviderStreamEvent union + StreamingProvider Protocol.

Locks the typed-event contract for the iteration loop's streaming path.
T1-03 fills the stream() bodies on both providers against these shapes.
"""
from __future__ import annotations

import inspect
import time
import typing

from voss.harness import auth as A
from voss.harness.providers import (
    AnthropicOAuthProvider,
    Done,
    OpenAIOAuthProvider,
    ParsedPlan,
    ProviderStreamEvent,
    StreamingProvider,
    TextDelta,
    ToolUseDelta,
    ToolUseEnd,
    ToolUseStart,
    Usage,
)


def _anthropic_creds() -> A.AnthropicOAuthCreds:
    return A.AnthropicOAuthCreds(
        access_token="sk-ant-oat01-A",
        refresh_token="sk-ant-ort01-R",
        expires_at_ms=int((time.time() + 3600) * 1000),
        subscription_type="max",
    )


def _openai_creds() -> A.CodexCreds:
    return A.CodexCreds(
        api_key=None,
        access_token="acc",
        refresh_token="ref",
        account_id="acct_42",
        auth_mode="chatgpt",
    )


class TestEventShapes:
    def test_text_delta(self) -> None:
        assert TextDelta(text="hello").text == "hello"

    def test_tool_use_start(self) -> None:
        ev = ToolUseStart(id="tu_1", name="submit_response")
        assert ev.id == "tu_1"
        assert ev.name == "submit_response"

    def test_tool_use_delta(self) -> None:
        ev = ToolUseDelta(id="tu_1", partial_json='{"rationale":"')
        assert ev.partial_json == '{"rationale":"'

    def test_tool_use_end(self) -> None:
        assert ToolUseEnd(id="tu_1").id == "tu_1"

    def test_usage(self) -> None:
        ev = Usage(prompt_tokens=120, completion_tokens=50, cost_usd=0.0)
        assert ev.cost_usd == 0.0
        assert ev.prompt_tokens == 120
        assert ev.completion_tokens == 50

    def test_done(self) -> None:
        assert Done(stop_reason="end_turn").stop_reason == "end_turn"

    def test_parsed_plan_holds_instance_identity(self) -> None:
        sentinel = object()
        ev = ParsedPlan(plan=sentinel)
        assert ev.plan is sentinel


class TestUnionShape:
    def test_union_has_exactly_seven_variants(self) -> None:
        names = {t.__name__ for t in typing.get_args(ProviderStreamEvent)}
        assert names == {
            "TextDelta",
            "ToolUseStart",
            "ToolUseDelta",
            "ToolUseEnd",
            "Usage",
            "Done",
            "ParsedPlan",
        }

    def test_each_variant_is_member_of_union(self) -> None:
        # Construct one of each and check isinstance against the runtime
        # tuple form of the Union.
        variants = (
            TextDelta(text="x"),
            ToolUseStart(id="i", name="n"),
            ToolUseDelta(id="i", partial_json=""),
            ToolUseEnd(id="i"),
            Usage(prompt_tokens=0, completion_tokens=0, cost_usd=0.0),
            Done(stop_reason="end_turn"),
            ParsedPlan(plan=None),
        )
        union_types = typing.get_args(ProviderStreamEvent)
        for v in variants:
            assert isinstance(v, union_types)


class TestStreamingProviderProtocol:
    def test_anthropic_satisfies_streaming_protocol(self) -> None:
        p = AnthropicOAuthProvider(_anthropic_creds())
        assert isinstance(p, StreamingProvider)

    def test_openai_satisfies_streaming_protocol(self) -> None:
        p = OpenAIOAuthProvider(_openai_creds())
        assert isinstance(p, StreamingProvider)

    def test_stream_signature_matches_locked_kwargs(self) -> None:
        # Both providers expose stream() with the exact CONTEXT.md kwargs.
        expected = {
            "messages",
            "model",
            "response_format",
            "tools",
            "temperature",
            "max_tokens",
            "timeout",
        }
        for cls in (AnthropicOAuthProvider, OpenAIOAuthProvider):
            sig = inspect.signature(cls.stream)
            params = set(sig.parameters) - {"self"}
            assert params == expected, f"{cls.__name__} stream() params: {params}"


# T1-03 removed the placeholder-body tests from T1-02: both stream() methods
# are now concrete SSE/streaming implementations. End-to-end coverage lives
# in test_anthropic_stream.py, test_openai_stream.py, and
# test_provider_stream_parity.py.
