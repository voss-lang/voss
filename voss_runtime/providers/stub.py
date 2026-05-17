from __future__ import annotations

import hashlib
import json
from typing import Any, AsyncIterator, Callable, Optional

from .base import ProviderResponse


def _fallback_payload_for_schema(response_format: type, value: Any) -> dict[str, Any] | None:
    fields = getattr(response_format, "model_fields", {})
    required = {"rationale", "steps", "confidence", "final_when_done"}
    if not required.issubset(set(fields)):
        return None
    return {
        "rationale": "stub plan",
        "steps": [],
        "confidence": 0.95,
        "final_when_done": str(value),
    }


class StubProvider:
    """Deterministic in-memory provider for tests.

    Responses are looked up by prompt fingerprint; falls back to a default response.
    """

    def __init__(
        self,
        *,
        responses: Optional[dict[str, Any]] = None,
        default_response: str = "stub-response",
        summarizer: Optional[Callable[[str, int], str]] = None,
    ):
        self.responses = responses or {}
        self.default_response = default_response
        self.summarizer = summarizer or (lambda text, target: text[: max(target * 4, 16)])
        self.calls: list[dict] = []

    @staticmethod
    def fingerprint(messages: list[dict]) -> str:
        return hashlib.sha256(json.dumps(messages, sort_keys=True).encode()).hexdigest()[:16]

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
        self.calls.append(
            {
                "model": model,
                "messages": messages,
                "tools": tools,
                "response_format": response_format,
                "max_tokens": max_tokens,
            }
        )
        fp = self.fingerprint(messages)
        entry = self.responses.get(fp, self.default_response)
        text = entry if isinstance(entry, str) else json.dumps(entry)
        parsed = None
        if response_format is not None:
            payload = entry if isinstance(entry, dict) else {"value": entry}
            try:
                parsed = response_format.model_validate(payload)
            except Exception:  # noqa: BLE001 - deterministic fallback for Plan-like schemas
                fallback = _fallback_payload_for_schema(response_format, entry)
                if fallback is None:
                    raise
                parsed = response_format.model_validate(fallback)
            text = parsed.model_dump_json()
        prompt_tokens = sum(len(m["content"]) for m in messages) // 4 or 1
        completion_tokens = max(len(text) // 4, 1)
        return ProviderResponse(
            text=text,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=0.0,
            raw={"stub": True},
            parsed=parsed,
        )

    async def stream(
        self,
        *,
        messages,
        model,
        response_format=None,
        tools=None,
        temperature=1.0,
        max_tokens=None,
        timeout=None,
    ) -> AsyncIterator[object]:
        from voss.harness.providers import Done, ParsedPlan, TextDelta, Usage

        response = await self.complete(
            messages=messages,
            model=model,
            response_format=response_format,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        yield TextDelta(response.text)
        if response.parsed is not None:
            yield ParsedPlan(response.parsed)
        yield Usage(
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            cost_usd=response.cost_usd,
        )
        yield Done("end_turn")

    def count_tokens(self, *, text, model) -> int:
        return max(len(text) // 4, 1)
