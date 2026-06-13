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

from . import auth
from .model_catalog import ModelEntry, ProviderGroup

KeyGetter = Callable[[str], str | None]


def resolve_key(
    entry: ModelEntry,
    *,
    getter: KeyGetter = os.environ.get,
    keyring_get: KeyGetter = auth.load_provider_key,
) -> str | None:
    """Return the API key for `entry`'s provider: env var first, keyring second.

    Both lookups are injectable for hermetic tests; live callers get the real
    env + keyring by default.
    """
    if not entry.env_key:
        return None
    return getter(entry.env_key) or keyring_get(entry.env_key)


def _default_oauth_check(provider_id: str) -> bool:
    """Native families are also 'connected' via existing OAuth/Codex creds."""
    if provider_id == "anthropic":
        return auth.load_anthropic_oauth() is not None
    if provider_id == "openai":
        codex = auth.load_codex()
        return bool(codex and (codex.api_key or codex.has_oauth))
    return False


def provider_connected(
    provider_id: str,
    env_key: str | None,
    *,
    getter: KeyGetter = os.environ.get,
    keyring_get: KeyGetter = auth.load_provider_key,
    oauth_check: Callable[[str], bool] = _default_oauth_check,
) -> bool:
    """True if Voss can authenticate to `provider_id` right now.

    Keyless providers (env_key None, e.g. local Ollama) are always connected;
    otherwise an env var or stored key suffices, with an OAuth fallback for the
    native Anthropic/OpenAI families.
    """
    if env_key is None:
        return True
    if getter(env_key) or keyring_get(env_key):
        return True
    return oauth_check(provider_id)


def connected_providers(
    groups: list[ProviderGroup],
    *,
    getter: KeyGetter = os.environ.get,
    keyring_get: KeyGetter = auth.load_provider_key,
    oauth_check: Callable[[str], bool] = _default_oauth_check,
) -> dict[str, bool]:
    """Map each group's provider_id -> connected? (for picker grey-out)."""
    return {
        g.id: provider_connected(
            g.id, g.env_key, getter=getter, keyring_get=keyring_get, oauth_check=oauth_check
        )
        for g in groups
    }


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
    setattr(provider, "voss_provider_id", entry.provider_id)
    setattr(provider, "voss_provider_label", entry.provider_label)
    setattr(provider, "voss_model_id", entry.id)
    return provider, model_string(entry)


def flatten(groups: list[ProviderGroup]) -> list[ModelEntry]:
    """All entries across groups, in display order."""
    return [m for g in groups for m in g.models]


def match_models(groups: list[ProviderGroup], query: str) -> list[ModelEntry]:
    """Substring match (case-insensitive) on model id or display name."""
    q = query.strip().lower()
    if not q:
        return flatten(groups)
    return [
        m
        for m in flatten(groups)
        if q in m.id.lower() or q in m.name.lower()
    ]


def find_by_id(
    groups: list[ProviderGroup], model_id: str, *, provider_id: str | None = None
) -> list[ModelEntry]:
    """Exact model-id matches, optionally scoped to one provider.

    Returns a list because the same model id can appear under multiple
    providers (e.g. claude-opus-4-5 under both anthropic and opencode).
    """
    return [
        m
        for m in flatten(groups)
        if m.id == model_id and (provider_id is None or m.provider_id == provider_id)
    ]


def find_entry(
    groups: list[ProviderGroup], provider_id: str, model_id: str
) -> ModelEntry | None:
    """The single entry for (provider_id, model_id), or None."""
    hits = find_by_id(groups, model_id, provider_id=provider_id)
    return hits[0] if hits else None


def boot_routed_provider(
    *,
    getter: KeyGetter = os.environ.get,
    keyring_get: KeyGetter = auth.load_provider_key,
    catalog_loader: Callable[[], list[ProviderGroup]] | None = None,
    harness: dict | None = None,
) -> tuple[ModelProvider, str] | None:
    """Rebuild the live provider+model from a persisted routed selection.

    Reads `[harness] preferred_provider/preferred_model`; if both are set and
    the model is found in the (cached) catalog, returns (provider, model_string)
    to override the auth-resolved default at boot. Returns None when there is no
    routed selection or the catalog/entry is unavailable (caller keeps its
    default). Never raises.
    """
    from . import config as _config
    from . import model_catalog as _catalog

    h = harness if harness is not None else _config.load_harness_config()
    provider_id = h.get("preferred_provider")
    model_id = h.get("preferred_model")
    if not provider_id or not model_id:
        return None

    loader = catalog_loader or _catalog.load_catalog
    try:
        groups = loader()
    except Exception:  # noqa: BLE001 — offline/parse: keep the default provider
        return None

    entry = find_entry(groups, provider_id, model_id)
    if entry is None:
        return None
    key = resolve_key(entry, getter=getter, keyring_get=keyring_get)
    return build_provider_for_model(entry, api_key=key)


def prepare_model(
    entry: ModelEntry,
    *,
    getter: KeyGetter = os.environ.get,
    keyring_get: KeyGetter = auth.load_provider_key,
) -> tuple[ModelProvider, str, bool]:
    """Convenience: resolve the key then build the provider.

    Returns (provider, model_string, key_present). `key_present` is False when
    the provider needs a key (env_key set) but none is configured — the picker
    surfaces this as "needs connect" (P5) rather than failing a turn later.
    """
    key = resolve_key(entry, getter=getter, keyring_get=keyring_get)
    provider, model = build_provider_for_model(entry, api_key=key)
    needs_key = entry.env_key is not None
    key_present = (key is not None) if needs_key else True
    return provider, model, key_present
