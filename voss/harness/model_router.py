"""Route a catalog ModelEntry to a live provider + litellm model string.

The picker (P3/P4) hands a `ModelEntry` here; this module turns it into a
ready-to-use `(provider, model_string)` pair. Two routes:

  * native       — Anthropic / OpenAI models litellm knows by id
                   (api_base is None) → model = entry.id
  * openai-compat — Ollama Cloud / OpenCode Zen / Go (api_base set, all
                   `@ai-sdk/openai-compatible`) → model = "openai/<id>" with
                   the provider's api_base + api key.

Key resolution reads the provider's env var today; P2 layers a keyring lookup
in front via the injectable `getter`. The actual swap of the *live* session
provider (ctx.provider / app provider) is wired in P6 — this module stays a
pure, testable factory.
"""
from __future__ import annotations

import os
from typing import Callable

from voss_runtime.providers import LiteLLMProvider
from voss_runtime.providers.base import ModelProvider

from .model_catalog import ModelEntry


def resolve_key(
    entry: ModelEntry, *, getter: Callable[[str], str | None] = os.environ.get
) -> str | None:
    """Return the API key for `entry`'s provider, or None if unset.

    `getter` defaults to env lookup; P2 passes a keyring-then-env resolver.
    """
    if not entry.env_key:
        return None
    return getter(entry.env_key)


def model_string(entry: ModelEntry) -> str:
    """The litellm model id for `entry` (adds the `openai/` route prefix for
    OpenAI-compatible custom endpoints; native ids pass through)."""
    if entry.api_base:
        return f"openai/{entry.id}"
    return entry.id


def build_provider_for_model(
    entry: ModelEntry, *, api_key: str | None = None
) -> tuple[ModelProvider, str]:
    """Build a provider + model string for `entry`.

    For OpenAI-compatible endpoints the api_base + key are bound to the
    provider instance so the one LiteLLMProvider class serves every endpoint.
    For native providers a bare LiteLLMProvider is returned (key passed through
    when known, else litellm reads it from the env).
    """
    if entry.api_base:
        provider = LiteLLMProvider(api_base=entry.api_base, api_key=api_key)
    else:
        provider = LiteLLMProvider(api_key=api_key)
    return provider, model_string(entry)


def prepare_model(
    entry: ModelEntry, *, getter: Callable[[str], str | None] = os.environ.get
) -> tuple[ModelProvider, str, bool]:
    """Convenience: resolve the key then build the provider.

    Returns (provider, model_string, key_present). `key_present` is False when
    the provider needs a key (env_key set) but none is configured — the picker
    surfaces this as "needs connect" (P5) rather than failing a turn later.
    """
    key = resolve_key(entry, getter=getter)
    provider, model = build_provider_for_model(entry, api_key=key)
    needs_key = entry.env_key is not None
    key_present = (key is not None) if needs_key else True
    return provider, model, key_present
