from __future__ import annotations

import litellm

from ..exceptions import ParseError, ProviderError
from ._cache_tokens import extract_cache_tokens
from .base import ProviderResponse


def _as_response_format_param(response_format):
    """Convert a Pydantic response model into a NON-strict json_schema param.

    Passing the raw model class makes litellm request OpenAI strict structured
    outputs (strict=True), which require `additionalProperties: false` on every
    object. Schemas with open/free-form fields (e.g. Plan's `args: dict`) cannot
    satisfy that and OpenAI rejects them outright. Non-strict json_schema still
    supplies the schema as guidance and returns JSON content, which we validate
    ourselves against the original model.
    """
    schema_fn = getattr(response_format, "model_json_schema", None)
    if not callable(schema_fn):
        return response_format
    return {
        "type": "json_schema",
        "json_schema": {
            "name": getattr(response_format, "__name__", "Response"),
            "schema": schema_fn(),
            "strict": False,
        },
    }


class LiteLLMProvider:
    def __init__(
        self,
        *,
        api_base: str | None = None,
        api_key: str | None = None,
        custom_llm_provider: str | None = None,
    ) -> None:
        """Stateless by default; optional per-instance routing overrides.

        `api_base`/`api_key` let one provider class target any OpenAI-compatible
        endpoint (Ollama Cloud, OpenCode Zen, …) without env-var juggling. When
        all are None the behaviour is identical to the historic no-arg provider
        (litellm reads ANTHROPIC_API_KEY/OPENAI_API_KEY/etc. from the env).
        """
        self.api_base = api_base
        self.api_key = api_key
        self.custom_llm_provider = custom_llm_provider

    def _route_kwargs(self) -> dict:
        out: dict = {}
        if self.api_base:
            out["api_base"] = self.api_base
        if self.api_key:
            out["api_key"] = self.api_key
        if self.custom_llm_provider:
            out["custom_llm_provider"] = self.custom_llm_provider
        return out

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
        kwargs: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            **self._route_kwargs(),
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if timeout is not None:
            kwargs["timeout"] = timeout
        if tools is not None:
            kwargs["tools"] = tools
        if response_format is not None:
            # NB: keep `response_format` (the original model) for parsing below;
            # only the wire param is converted to a non-strict json_schema.
            kwargs["response_format"] = _as_response_format_param(response_format)

        try:
            resp = await litellm.acompletion(**kwargs)
        except Exception as e:
            raise ProviderError(f"{model}: {e}") from e

        choice = resp.choices[0].message
        text = choice.content or ""
        usage = resp.usage
        cost = float(getattr(resp, "_hidden_params", {}).get("response_cost", 0.0) or 0.0)
        cache_create, cache_read = extract_cache_tokens(usage)

        parsed = None
        if response_format is not None and text:
            try:
                parsed = response_format.model_validate_json(text)
            except Exception as e:
                raise ParseError(f"Failed to parse {response_format.__name__}: {e}") from e

        return ProviderResponse(
            text=text,
            model=model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            cost_usd=cost,
            cache_creation_input_tokens=cache_create,
            cache_read_input_tokens=cache_read,
            raw=resp.model_dump() if hasattr(resp, "model_dump") else dict(resp),
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
    ):
        """Complete-then-yield streaming facade.

        LiteLLM's native streaming is deferred to a follow-up; this bridges
        the gap so the agent loop's `provider.stream()` call works instead
        of raising AttributeError.
        """
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
        # A structured turn (response_format set) returns the schema JSON as
        # `text`; that is NOT prose and must never surface as an assistant
        # TextDelta (it leaks raw `{"rationale":...}` into the chat). Emit only
        # the ParsedPlan in that case; stream text only for free-form turns.
        if response.text and response_format is None:
            yield TextDelta(response.text)
        if response.parsed is not None:
            yield ParsedPlan(response.parsed)
        yield Usage(
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            cost_usd=response.cost_usd,
            cache_creation_input_tokens=response.cache_creation_input_tokens,
            cache_read_input_tokens=response.cache_read_input_tokens,
        )
        yield Done("end_turn")

    def count_tokens(self, *, text, model) -> int:
        return litellm.token_counter(model=model, text=text)
