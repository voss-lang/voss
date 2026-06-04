"""Harness-specific providers.

These wrap the same `ModelProvider` protocol as `voss_runtime.providers` but
add OAuth bearer auth (Claude Code subscription) and direct httpx transport.

For simple API-key flows we still use voss_runtime's LiteLLMProvider.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional, Protocol, Union, runtime_checkable

import httpx
from pydantic import BaseModel

from voss_runtime.providers.base import ProviderResponse

from . import auth


# ---------------------------------------------------------------------------
# T1-02: Streaming event contract — typed union consumed by the agent loop
# (T1-05/T1-06) and the iteration loop's terminating-Plan parse. Bodies of
# stream() land in T1-03; this module ships only shapes + Protocol so
# downstream waves can pin against a stable surface.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TextDelta:
    text: str


@dataclass(frozen=True, slots=True)
class ToolUseStart:
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class ToolUseDelta:
    id: str
    partial_json: str


@dataclass(frozen=True, slots=True)
class ToolUseEnd:
    id: str


@dataclass(frozen=True, slots=True)
class Usage:
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    # T4 CACHE-02 (D-01): streaming half — symmetric with ProviderResponse
    # on the non-streaming path; OAuth-path emission sites pass through
    # defaults (Pitfall 3 deferral).
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass(frozen=True, slots=True)
class Done:
    stop_reason: str


@dataclass(frozen=True, slots=True)
class ParsedPlan:
    """Terminal event carrying the structured Plan parse.

    Locked mechanism (CONTEXT.md "Claude's Discretion") for surfacing the
    Plan instance: providers emit a synthetic terminal ParsedPlan event
    rather than returning the Plan from the stream() coroutine. Keeps the
    agent-loop consumer branching on a single shape.

    `plan` is typed Any to avoid importing `voss.harness.agent.Plan` here
    and creating a circular import; T1-03 / T1-05 pin the concrete type
    at the call site.
    """

    plan: Any


ProviderStreamEvent = Union[
    TextDelta,
    ToolUseStart,
    ToolUseDelta,
    ToolUseEnd,
    Usage,
    Done,
    ParsedPlan,
]


@runtime_checkable
class StreamingProvider(Protocol):
    """Structural protocol both AnthropicOAuthProvider and OpenAIOAuthProvider satisfy.

    T1-03 fills the stream() bodies; T1-05 consumes the events in the
    agent iteration loop. Signature mirrors complete() arg-for-arg so
    callers can swap call sites without re-threading kwargs.
    """

    async def stream(
        self,
        *,
        messages: list[dict],
        model: str,
        response_format: Optional[type] = None,
        tools: Optional[list[dict]] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> AsyncIterator[ProviderStreamEvent]:
        ...


# ---------------------------------------------------------------------------
# Anthropic OAuth provider — Claude Pro/Max subscription via Claude Code creds
# ---------------------------------------------------------------------------


# Conservative model alias map. LiteLLM-style names → Anthropic API IDs.
_MODEL_ALIASES = {
    "claude-sonnet-4-5": "claude-sonnet-4-5",
    "claude-sonnet-4-7": "claude-sonnet-4-5",  # placeholder until 4.7 alias settles
    "claude-haiku-4-5": "claude-haiku-4-5",
    "claude-opus-4-7": "claude-opus-4-5",
}

# Anthropic's OAuth tokens are scoped to Claude Code. The API rejects requests
# whose system prompt does not begin with the Claude Code identity line.
# Including this preamble keeps the harness compatible with the subscription
# auth path (it sits in front of any harness-provided system prompts).
CLAUDE_CODE_PREAMBLE = "You are Claude Code, Anthropic's official CLI for Claude."


def _resolve_model(model: str) -> str:
    return _MODEL_ALIASES.get(model, model)


class AnthropicOAuthProvider:
    """Anthropic Messages API client using Claude Code OAuth tokens.

    Notes:
    - Adds `anthropic-beta: oauth-2025-04-20` header.
    - Translates `response_format=PydanticModel` into a single forced tool call,
      then validates the tool input against the model.
    - Refreshes access token automatically on 401.
    """

    def __init__(
        self,
        creds: auth.AnthropicOAuthCreds,
        *,
        client: Optional[httpx.AsyncClient] = None,
        base_url: str = auth.ANTHROPIC_API_BASE,
        max_output_tokens: int = 4096,
    ):
        self.creds = creds
        self._client = client
        self.base_url = base_url
        self.max_output_tokens = max_output_tokens

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _headers(self) -> dict[str, str]:
        return {
            "authorization": f"Bearer {self.creds.access_token}",
            "anthropic-beta": auth.ANTHROPIC_OAUTH_BETA,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "user-agent": "voss-harness/0.1",
        }

    def _maybe_refresh(self) -> None:
        if self.creds.expired:
            self.creds = auth.refresh_anthropic(self.creds)

    def _payload(
        self,
        *,
        messages: list[dict],
        model: str,
        response_format: Optional[type],
        tools: Optional[list[dict]],
        temperature: float,
        max_tokens: Optional[int],
    ) -> dict[str, Any]:
        # Split out system messages — Anthropic API takes them separately.
        system_chunks: list[Any] = []
        chat: list[dict] = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system_chunks.append(content)
            else:
                chat.append({"role": role, "content": content})

        # Anthropic API accepts `system` as either a string or a list of
        # content blocks. Use the block form so we can prepend the Claude Code
        # preamble required by OAuth-scoped tokens without polluting the
        # harness's own system message.
        system_blocks = [{"type": "text", "text": CLAUDE_CODE_PREAMBLE}]
        for chunk in system_chunks:
            if isinstance(chunk, list):
                system_blocks.extend(
                    block
                    for block in chunk
                    if isinstance(block, dict) and block.get("type") == "text"
                )
            elif chunk:
                system_blocks.append({"type": "text", "text": chunk})

        body: dict[str, Any] = {
            "model": _resolve_model(model),
            "max_tokens": max_tokens or self.max_output_tokens,
            "temperature": temperature,
            "messages": chat,
            "system": system_blocks,
        }

        if response_format is not None and issubclass(response_format, BaseModel):
            schema = response_format.model_json_schema()
            body["tools"] = (tools or []) + [
                {
                    "name": "submit_response",
                    "description": "Return the final structured response.",
                    "input_schema": schema,
                }
            ]
            body["tool_choice"] = {"type": "tool", "name": "submit_response"}
        elif tools:
            body["tools"] = tools

        return body

    async def complete(
        self,
        *,
        messages: list[dict],
        model: str,
        response_format: Optional[type] = None,
        tools: Optional[list[dict]] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> ProviderResponse:
        self._maybe_refresh()
        body = self._payload(
            messages=messages,
            model=model,
            response_format=response_format,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        url = f"{self.base_url}/v1/messages"

        async def _post() -> httpx.Response:
            return await self._http().post(
                url, json=body, headers=self._headers(), timeout=timeout
            )

        resp = await _post()
        if resp.status_code == 401:
            self.creds = auth.refresh_anthropic(self.creds)
            resp = await _post()
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Anthropic OAuth call failed [{resp.status_code}]: {resp.text[:500]}"
            )

        data = resp.json()
        usage = data.get("usage", {})
        prompt_tokens = int(usage.get("input_tokens", 0))
        completion_tokens = int(usage.get("output_tokens", 0))

        text = ""
        parsed: Any = None
        for block in data.get("content", []):
            btype = block.get("type")
            if btype == "text":
                text += block.get("text", "")
            elif btype == "tool_use" and response_format is not None:
                inp = block.get("input", {})
                parsed = response_format.model_validate(inp)
                if not text:
                    text = json.dumps(inp)

        return ProviderResponse(
            text=text,
            model=data.get("model", model),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=0.0,  # subscription billing — no per-call cost
            raw=data,
            parsed=parsed,
        )

    async def stream(
        self,
        *,
        messages: list[dict],
        model: str,
        response_format: Optional[type] = None,
        tools: Optional[list[dict]] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> AsyncIterator[ProviderStreamEvent]:
        """Stream Anthropic Messages API SSE → ProviderStreamEvent (T1-03).

        Preserves OAuth refresh-on-401, structured-output Plan extraction
        (forced submit_response tool), and graceful httpx connection close
        via async-context exit on CancelledError.
        """
        self._maybe_refresh()
        body = self._payload(
            messages=messages,
            model=model,
            response_format=response_format,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        body["stream"] = True
        url = f"{self.base_url}/v1/messages"

        # Try once with current creds; on 401 refresh + reopen in a second
        # async-with. Cannot reopen inside the same context manager.
        refreshed = False
        while True:
            client = self._http()
            async with client.stream(
                "POST", url, json=body, headers=self._headers(), timeout=timeout
            ) as resp:
                if resp.status_code == 401 and not refreshed:
                    self.creds = auth.refresh_anthropic(self.creds)
                    refreshed = True
                    continue
                if resp.status_code >= 400:
                    body_text = await resp.aread()
                    raise RuntimeError(
                        f"Anthropic OAuth stream failed [{resp.status_code}]: "
                        f"{body_text[:500]!r}"
                    )

                # SSE decode state.
                current_tool_use_id: Optional[str] = None
                tool_use_json: dict[str, list[str]] = {}
                captured_stop_reason: str = "end_turn"
                captured_usage: Optional[Usage] = None
                message_start_input_tokens = 0
                message_start_cache_creation = 0
                message_start_cache_read = 0

                async for line in resp.aiter_lines():
                    if not line or line.startswith(":"):
                        continue
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if not payload:
                        continue
                    try:
                        data = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    ev_type = data.get("type", "")

                    if ev_type == "message_start":
                        msg = data.get("message", {}) or {}
                        usage = msg.get("usage", {}) or {}
                        message_start_input_tokens = int(
                            usage.get("input_tokens", 0)
                        )
                        message_start_cache_creation = int(
                            usage.get("cache_creation_input_tokens", 0)
                        )
                        message_start_cache_read = int(
                            usage.get("cache_read_input_tokens", 0)
                        )

                    elif ev_type == "content_block_start":
                        cb = data.get("content_block", {}) or {}
                        if cb.get("type") == "tool_use":
                            tu_id = cb.get("id", "")
                            tu_name = cb.get("name", "")
                            current_tool_use_id = tu_id
                            tool_use_json[tu_id] = []
                            yield ToolUseStart(id=tu_id, name=tu_name)

                    elif ev_type == "content_block_delta":
                        d = data.get("delta", {}) or {}
                        dtype = d.get("type", "")
                        if dtype == "text_delta":
                            yield TextDelta(text=d.get("text", ""))
                        elif dtype == "input_json_delta" and current_tool_use_id:
                            chunk = d.get("partial_json", "")
                            tool_use_json[current_tool_use_id].append(chunk)
                            yield ToolUseDelta(
                                id=current_tool_use_id, partial_json=chunk
                            )

                    elif ev_type == "content_block_stop":
                        if current_tool_use_id is not None:
                            yield ToolUseEnd(id=current_tool_use_id)

                    elif ev_type == "message_delta":
                        d = data.get("delta", {}) or {}
                        if d.get("stop_reason"):
                            captured_stop_reason = d["stop_reason"]
                        usage = data.get("usage")
                        if usage:
                            captured_usage = Usage(
                                prompt_tokens=message_start_input_tokens
                                or int(usage.get("input_tokens", 0)),
                                completion_tokens=int(usage.get("output_tokens", 0)),
                                cost_usd=0.0,
                                cache_creation_input_tokens=message_start_cache_creation,
                                cache_read_input_tokens=message_start_cache_read,
                            )

                    elif ev_type == "message_stop":
                        if captured_usage is not None:
                            yield captured_usage
                        if (
                            response_format is not None
                            and current_tool_use_id is not None
                        ):
                            full_json = "".join(
                                tool_use_json.get(current_tool_use_id, [])
                            )
                            try:
                                plan_obj = response_format.model_validate_json(
                                    full_json
                                )
                                yield ParsedPlan(plan=plan_obj)
                            except Exception:
                                pass
                        yield Done(stop_reason=captured_stop_reason)
                        return

                # Server hangup without message_stop.
                yield Done(stop_reason="incomplete")
                return

    def count_tokens(self, *, text: str, model: str) -> int:
        # Quick estimate. Anthropic's counter requires an extra API call;
        # for harness budgeting a 4-chars-per-token heuristic is fine.
        return max(len(text) // 4, 1)


# ---------------------------------------------------------------------------
# OpenAI OAuth provider — ChatGPT subscription via Codex CLI tokens
# ---------------------------------------------------------------------------


_OPENAI_MODEL_DEFAULT = "gpt-5"


class OpenAIOAuthProvider:
    """OpenAI Responses API client using Codex CLI ChatGPT-mode tokens.

    These tokens are issued by ChatGPT login (not API keys) and are scoped to
    the Responses API. Account id is sent in the `chatgpt-account-id` header.
    """

    def __init__(
        self,
        creds: auth.CodexCreds,
        *,
        client: Optional[httpx.AsyncClient] = None,
        base_url: Optional[str] = None,
    ):
        self.creds = creds
        self._client = client
        # ChatGPT-mode tokens go to chatgpt.com; api-key mode goes to api.openai.com.
        if base_url is None:
            base_url = (
                auth.CHATGPT_BACKEND_BASE
                if creds.auth_mode.lower() == "chatgpt"
                else auth.OPENAI_API_BASE
            )
        self.base_url = base_url

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _headers(self) -> dict[str, str]:
        h = {
            "authorization": f"Bearer {self.creds.access_token}",
            "content-type": "application/json",
            "user-agent": "voss-harness/0.1",
            "originator": "codex_cli_rs",
            "OpenAI-Beta": "responses=v1",
        }
        if self.creds.account_id:
            h["chatgpt-account-id"] = self.creds.account_id
        return h

    def _maybe_refresh(self) -> None:
        # Codex tokens lack expiry metadata in the local file; rely on 401.
        return

    @staticmethod
    def _to_responses_input(messages: list[dict]) -> tuple[list[str], list[dict]]:
        """Split messages into (system_chunks, responses-API input list)."""
        system_chunks: list[str] = []
        items: list[dict] = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system_chunks.append(content)
                continue
            api_role = "assistant" if role == "assistant" else "user"
            items.append(
                {
                    "type": "message",
                    "role": api_role,
                    "content": [{"type": "input_text", "text": content}],
                }
            )
        return system_chunks, items

    def _payload(
        self,
        *,
        messages: list[dict],
        model: str,
        response_format: Optional[type],
        temperature: float,
        max_tokens: Optional[int],
    ) -> dict[str, Any]:
        system_chunks, items = self._to_responses_input(messages)
        body: dict[str, Any] = {
            "model": model or _OPENAI_MODEL_DEFAULT,
            "input": items,
            "store": False,
            "stream": False,
        }
        if temperature is not None:
            body["temperature"] = temperature
        if max_tokens is not None:
            body["max_output_tokens"] = max_tokens
        if system_chunks:
            body["instructions"] = "\n\n".join(system_chunks)
        if response_format is not None and issubclass(response_format, BaseModel):
            # NON-strict json_schema. strict=True forces additionalProperties:false
            # on every nested object and rejects open fields (Plan.args is an open
            # dict) → the endpoint 400s. Non-strict still supplies the schema as
            # guidance; we validate the returned JSON against the model ourselves.
            body["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": response_format.__name__,
                    "strict": False,
                    "schema": response_format.model_json_schema(),
                }
            }
        return body

    async def complete(
        self,
        *,
        messages: list[dict],
        model: str,
        response_format: Optional[type] = None,
        tools: Optional[list[dict]] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> ProviderResponse:
        self._maybe_refresh()
        body = self._payload(
            messages=messages,
            model=model,
            response_format=response_format,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        # api.openai.com uses /v1/responses; chatgpt.com/backend-api/codex uses /responses.
        url = (
            f"{self.base_url}/responses"
            if self.base_url.endswith("/codex")
            else f"{self.base_url}/v1/responses"
        )

        async def _post() -> httpx.Response:
            return await self._http().post(
                url, json=body, headers=self._headers(), timeout=timeout
            )

        resp = await _post()
        if resp.status_code == 401 and self.creds.refresh_token:
            self.creds = auth.refresh_codex(self.creds)
            resp = await _post()
        if resp.status_code >= 400:
            raise RuntimeError(
                f"OpenAI OAuth call failed [{resp.status_code}]: {resp.text[:500]}"
            )

        data = resp.json()
        usage = data.get("usage", {})
        prompt_tokens = int(usage.get("input_tokens", 0))
        completion_tokens = int(usage.get("output_tokens", 0))

        text = ""
        for block in data.get("output", []):
            if block.get("type") == "message":
                for c in block.get("content", []):
                    if c.get("type") in ("output_text", "text"):
                        text += c.get("text", "")
        # Some response shapes flatten to top-level "output_text".
        if not text and isinstance(data.get("output_text"), str):
            text = data["output_text"]

        parsed: Any = None
        if response_format is not None and text:
            try:
                parsed = response_format.model_validate_json(text)
            except Exception:
                parsed = None

        return ProviderResponse(
            text=text,
            model=data.get("model", model),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=0.0,
            raw=data,
            parsed=parsed,
        )

    async def stream(
        self,
        *,
        messages: list[dict],
        model: str,
        response_format: Optional[type] = None,
        tools: Optional[list[dict]] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> AsyncIterator[ProviderStreamEvent]:
        """Stream OpenAI Responses API SSE → ProviderStreamEvent (T1-03).

        Preserves structured-output Plan extraction via `text.format`
        json_schema, ChatGPT-mode 401 refresh, and graceful httpx close via
        async-context exit on CancelledError. `tools` is accepted for
        signature symmetry with Anthropic but unused — Plan comes from
        accumulated output_text deltas, not tool-use streaming.
        """
        self._maybe_refresh()
        body = self._payload(
            messages=messages,
            model=model,
            response_format=response_format,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        body["stream"] = True
        url = (
            f"{self.base_url}/responses"
            if self.base_url.endswith("/codex")
            else f"{self.base_url}/v1/responses"
        )

        refreshed = False
        while True:
            client = self._http()
            async with client.stream(
                "POST", url, json=body, headers=self._headers(), timeout=timeout
            ) as resp:
                if (
                    resp.status_code == 401
                    and not refreshed
                    and self.creds.refresh_token
                ):
                    self.creds = auth.refresh_codex(self.creds)
                    refreshed = True
                    continue
                if resp.status_code >= 400:
                    body_text = await resp.aread()
                    raise RuntimeError(
                        f"OpenAI OAuth stream failed [{resp.status_code}]: "
                        f"{body_text[:500]!r}"
                    )

                text_acc: list[str] = []
                async for line in resp.aiter_lines():
                    if not line or line.startswith(":"):
                        continue
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if not payload:
                        continue
                    try:
                        data = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    ev_type = data.get("type", "")

                    if ev_type == "response.output_text.delta":
                        chunk = data.get("delta", "")
                        text_acc.append(chunk)
                        yield TextDelta(text=chunk)

                    elif ev_type == "response.completed":
                        response_obj = data.get("response", {}) or {}
                        usage = response_obj.get("usage", {}) or {}
                        yield Usage(
                            prompt_tokens=int(usage.get("input_tokens", 0)),
                            completion_tokens=int(usage.get("output_tokens", 0)),
                            cost_usd=0.0,
                        )
                        if response_format is not None:
                            full_text = (
                                response_obj.get("output_text") or "".join(text_acc)
                            )
                            try:
                                plan_obj = response_format.model_validate_json(
                                    full_text
                                )
                                yield ParsedPlan(plan=plan_obj)
                            except Exception:
                                pass
                        stop = response_obj.get("status", "completed")
                        yield Done(stop_reason=stop)
                        return
                    # response.created / response.in_progress / output_item.*
                    # / etc. are ignored — not load-bearing for the loop.

                yield Done(stop_reason="incomplete")
                return

    def count_tokens(self, *, text: str, model: str) -> int:
        return max(len(text) // 4, 1)
