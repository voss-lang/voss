"""Claude subscription provider via the official `claude-agent-sdk` package.

Replaces the retired raw-OAuth path (AnthropicOAuthProvider): Anthropic blocks
subscription OAuth tokens in third-party tools server-side (2026-01-09) and
prohibits them by ToS. The sanctioned route is the Agent SDK / `claude -p`,
which since 2026-06-15 bills against a dedicated monthly subscription credit
separate from interactive Claude Code limits.

Design (provider mode): Voss keeps its own agent loop, tools, and permission
gate. The spawned Claude Code runs with `max_turns=1`, all built-in tools
disabled, no settings sources, and no cwd — it acts as a pure model. Each
`stream()` call is a stateless one-shot `query()`: the harness rebuilds the
full message list every iteration (repacking, steering injections), so a
persistent SDK session would hold a divergent transcript.

Known tradeoffs:
- History is flattened into a single prompt with <<<USER>>>/<<<ASSISTANT>>>
  markers; hostile content containing a marker could confuse turn attribution
  (same class of risk as the Responses-API flattening in OpenAIOAuthProvider).
- No cross-iteration prompt caching: every call re-sends the transcript.
  $0 under subscription, but burns the metered Agent SDK credit faster.
  Follow-up if painful: ClaudeSDKClient session mode behind a flag.
- If ANTHROPIC_API_KEY is exported, the spawned CLI may bill the API key
  instead of the subscription. Unreachable under --auth=auto (the key wins
  earlier in resolve()); possible under explicit --auth=claude with a key
  exported.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Optional

from pydantic import BaseModel

from voss_runtime.providers.base import ProviderResponse

from . import telemetry
from .providers import Done, ParsedPlan, ProviderStreamEvent, TextDelta, Usage

_INSTALL_HINT = "claude-agent-sdk not installed — pip install 'voss[claude]'"
_CLI_HINT = "claude CLI not found — npm install -g @anthropic-ai/claude-code"
_LOGIN_HINT = "run `claude /login` in a terminal to connect your subscription"

_JSON_TAIL = (
    "Respond as the assistant. Output only the JSON object matching the "
    "required schema."
)


def _content_to_text(content: Any) -> str:
    """Flatten message content (string or Anthropic-style block list) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text", "")))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


def _flatten_messages(
    messages: list[dict], *, want_json: bool = False
) -> tuple[str, str]:
    """Split messages into (system_prompt, one-shot prompt).

    System contents join with blank lines; the rest become sentinel-delimited
    turns. The trailing JSON instruction is defensive glue — the SDK's
    `output_format` json_schema does the heavy lifting.
    """
    system_chunks: list[str] = []
    turns: list[str] = []
    for m in messages:
        role = m.get("role", "user")
        text = _content_to_text(m.get("content", ""))
        if role == "system":
            system_chunks.append(text)
            continue
        marker = "<<<ASSISTANT>>>" if role == "assistant" else "<<<USER>>>"
        turns.append(f"{marker}\n{text}")
    prompt = "\n\n".join(turns)
    if want_json:
        prompt = f"{prompt}\n\n{_JSON_TAIL}" if prompt else _JSON_TAIL
    return "\n\n".join(system_chunks), prompt


class ClaudeAgentProvider:
    """Drives the Claude Code CLI through `claude_agent_sdk.query()`.

    Satisfies the same StreamingProvider/ModelProvider protocols as the OAuth
    providers. `temperature`, `max_tokens`, and harness `tools` are accepted
    for signature symmetry but unused — the SDK exposes none of them, and
    Claude Code's own tools are disabled (Voss owns tool execution).

    `query_fn` is a test seam: inject an async-generator factory with the
    `query(prompt=..., options=...)` signature to run without the SDK.
    """

    def __init__(
        self,
        *,
        model_default: str = "claude-sonnet-4-5",
        cli_path: str | Path | None = None,
        query_fn: Optional[Callable[..., AsyncIterator[Any]]] = None,
    ):
        self.model_default = model_default
        self.cli_path = str(cli_path) if cli_path is not None else None
        self._query_fn = query_fn

    # ------------------------------------------------------------------
    # SDK plumbing
    # ------------------------------------------------------------------

    def _resolve_query(self) -> Callable[..., AsyncIterator[Any]]:
        if self._query_fn is not None:
            return self._query_fn
        try:
            from claude_agent_sdk import query  # type: ignore[import-not-found]
        except ImportError as e:
            raise RuntimeError(_INSTALL_HINT) from e
        return query

    def _make_options(self, *, system_prompt: str, model: str, schema: Optional[dict]):
        kwargs: dict[str, Any] = {
            "system_prompt": system_prompt or None,
            "model": model,
            # Structured output rides an internal StructuredOutput tool
            # round-trip, and the model may spend text-only turns before
            # calling it (observed live with large harness system prompts).
            # Tools are disabled, so extra turns are cheap; 8 is a runaway
            # cap, not a target. Plain text fits in one.
            "max_turns": 8 if schema else 1,
            "tools": [],
            "allowed_tools": [],
            "setting_sources": [],
            "permission_mode": "default",
            "cwd": None,
            "cli_path": self.cli_path,
            "include_partial_messages": False,
            "output_format": (
                {"type": "json_schema", "schema": schema} if schema else None
            ),
        }
        try:
            from claude_agent_sdk import (  # type: ignore[import-not-found]
                ClaudeAgentOptions,
            )

            return ClaudeAgentOptions(**kwargs)
        except ImportError:
            if self._query_fn is None:
                raise RuntimeError(_INSTALL_HINT) from None
            # Test seam active: a plain attribute bag is enough for fakes.
            from types import SimpleNamespace

            return SimpleNamespace(**kwargs)

    @staticmethod
    def _wrap_error(e: Exception) -> RuntimeError:
        name = type(e).__name__
        if name == "CLINotFoundError":
            return RuntimeError(f"{_CLI_HINT} ({e})")
        if name == "ProcessError":
            exit_code = getattr(e, "exit_code", "?")
            return RuntimeError(
                f"claude-agent process failed (exit {exit_code}): {e}; "
                f"if this is an auth error, {_LOGIN_HINT}"
            )
        return RuntimeError(f"claude-agent call failed ({name}): {e}")

    # ------------------------------------------------------------------
    # Protocol surface
    # ------------------------------------------------------------------

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
        query = self._resolve_query()
        want_schema = response_format is not None and issubclass(
            response_format, BaseModel
        )
        system_prompt, prompt = _flatten_messages(messages, want_json=want_schema)
        options = self._make_options(
            system_prompt=system_prompt,
            model=model or self.model_default,
            schema=response_format.model_json_schema() if want_schema else None,
        )

        text_acc: list[str] = []
        result_msg: Any = None
        it = aiter(query(prompt=prompt, options=options))
        try:
            while True:
                try:
                    if timeout:
                        msg = await asyncio.wait_for(anext(it), timeout)
                    else:
                        msg = await anext(it)
                except StopAsyncIteration:
                    break
                except asyncio.TimeoutError:
                    raise RuntimeError(
                        f"claude-agent call timed out after {timeout}s"
                    ) from None
                except (RuntimeError, asyncio.CancelledError):
                    raise
                except Exception as e:  # noqa: BLE001 — SDK error types stay contained
                    raise self._wrap_error(e) from e

                # ResultMessage: terminal accounting + structured output.
                if hasattr(msg, "total_cost_usd"):
                    if getattr(msg, "is_error", False):
                        subtype = getattr(msg, "subtype", "error")
                        status = getattr(msg, "api_error_status", None)
                        detail = (
                            getattr(msg, "errors", None)
                            or getattr(msg, "result", None)
                            or ""
                        )
                        tag = f"{subtype}/{status}" if status else f"{subtype}"
                        raise RuntimeError(
                            f"claude-agent call failed [{tag}]: {detail}"
                        )
                    result_msg = msg
                    break

                # AssistantMessage: text blocks → deltas; thinking / stray
                # tool-use blocks are ignored (tools are disabled).
                content = getattr(msg, "content", None)
                if isinstance(content, list):
                    for block in content:
                        if hasattr(block, "text") and not hasattr(block, "input"):
                            text_acc.append(block.text)
                            yield TextDelta(text=block.text)
                        elif hasattr(block, "input"):
                            # StructuredOutput is the SDK's own json_schema
                            # delivery mechanism, not a stray tool call.
                            name = getattr(block, "name", "?")
                            if name != "StructuredOutput":
                                telemetry.emit(
                                    "provider.claude_agent.stray_tool_use",
                                    "warn",
                                    data={"name": name},
                                )
                # SystemMessage(init) and anything else: not load-bearing.

            if result_msg is None:
                yield Done(stop_reason="incomplete")
                return

            # Drain to natural exhaustion so the SDK generator finishes its
            # own subprocess cleanup — closing it mid-stream via GeneratorExit
            # leaves the SDK's internal tasks pending ("Task was destroyed but
            # it is pending" on interpreter exit). Bounded: post-result the
            # stream ends immediately; 5s is a hang guard, not a wait target.
            try:
                while True:
                    await asyncio.wait_for(anext(it), 5)
            except (StopAsyncIteration, asyncio.TimeoutError):
                pass

            usage = getattr(result_msg, "usage", None) or {}
            # Subscription turns must not count as harness spend; the SDK's
            # advisory total_cost_usd goes to telemetry only.
            telemetry.emit(
                "provider.claude_agent.result",
                "debug",
                data={"total_cost_usd": getattr(result_msg, "total_cost_usd", None)},
            )
            yield Usage(
                prompt_tokens=int(usage.get("input_tokens", 0)),
                completion_tokens=int(usage.get("output_tokens", 0)),
                cost_usd=0.0,
                cache_creation_input_tokens=int(
                    usage.get("cache_creation_input_tokens", 0)
                ),
                cache_read_input_tokens=int(
                    usage.get("cache_read_input_tokens", 0)
                ),
            )
            if want_schema:
                plan_obj = self._extract_plan(
                    response_format, result_msg, "".join(text_acc)
                )
                if plan_obj is not None:
                    yield ParsedPlan(plan=plan_obj)
            yield Done(
                stop_reason=getattr(result_msg, "stop_reason", None) or "end_turn"
            )
        finally:
            # Closing the SDK iterator terminates the subprocess on cancel,
            # timeout, or error paths.
            aclose = getattr(it, "aclose", None)
            if aclose is not None:
                try:
                    await aclose()
                except Exception:  # noqa: BLE001 — close is best-effort
                    pass

    @staticmethod
    def _extract_plan(
        response_format: type, result_msg: Any, accumulated_text: str
    ) -> Optional[Any]:
        structured = getattr(result_msg, "structured_output", None)
        if structured:
            try:
                return response_format.model_validate(structured)
            except Exception:  # noqa: BLE001 — fall through to text parse
                pass
        full_text = getattr(result_msg, "result", None) or accumulated_text
        try:
            return response_format.model_validate_json(full_text)
        except Exception:  # noqa: BLE001 — loop's unparsed fallback handles it
            return None

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
        text_acc: list[str] = []
        usage: Optional[Usage] = None
        parsed: Optional[Any] = None
        async for ev in self.stream(
            messages=messages,
            model=model,
            response_format=response_format,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        ):
            if isinstance(ev, TextDelta):
                text_acc.append(ev.text)
            elif isinstance(ev, Usage):
                usage = ev
            elif isinstance(ev, ParsedPlan):
                parsed = ev.plan
        return ProviderResponse(
            text="".join(text_acc),
            model=model or self.model_default,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            cost_usd=0.0,
            cache_creation_input_tokens=(
                usage.cache_creation_input_tokens if usage else 0
            ),
            cache_read_input_tokens=usage.cache_read_input_tokens if usage else 0,
            raw={},
            parsed=parsed,
        )

    def count_tokens(self, *, text: str, model: str) -> int:
        # Same 4-chars-per-token heuristic as the OAuth providers.
        return max(len(text) // 4, 1)
