from __future__ import annotations

import litellm

from ..exceptions import ParseError, ProviderError
from .base import ProviderResponse


class LiteLLMProvider:
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
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if timeout is not None:
            kwargs["timeout"] = timeout
        if tools is not None:
            kwargs["tools"] = tools
        if response_format is not None:
            kwargs["response_format"] = response_format

        try:
            resp = await litellm.acompletion(**kwargs)
        except Exception as e:
            raise ProviderError(f"{model}: {e}") from e

        choice = resp.choices[0].message
        text = choice.content or ""
        usage = resp.usage
        cost = float(getattr(resp, "_hidden_params", {}).get("response_cost", 0.0) or 0.0)

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
            raw=resp.model_dump() if hasattr(resp, "model_dump") else dict(resp),
            parsed=parsed,
        )

    def count_tokens(self, *, text, model) -> int:
        return litellm.token_counter(model=model, text=text)
