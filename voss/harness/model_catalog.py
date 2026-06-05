"""models.dev catalog — the source for the `/models` picker.

Fetches the public catalog at https://models.dev/api.json (the same source
OpenCode uses), filters it to the provider families Voss can route, and
normalizes each model into a flat `ModelEntry`. Cached to disk with a TTL so
the picker opens instantly and works offline.

Shape pinned from the live API (2026-06):

    {provider_id: {
        id, name, env:[KEY,...], api: base_url|null, npm, doc,
        models: {model_id: {
            id, name, family, cost:{input,output,...}|null,
            limit:{context,output}, modalities, tool_call, reasoning, ...
        }}
    }}

Every target provider is OpenAI-compatible (`@ai-sdk/openai-compatible`), so a
single LiteLLM route (api_base + env key) serves Ollama Cloud and OpenCode Zen;
`anthropic`/`openai` use their native LiteLLM prefixes. `cost.input == 0 and
cost.output == 0` marks a Free model; `cost is None` (Ollama Cloud) is a
subscription model with no price tag.

Pure parsing (`parse_catalog`) is isolated from network/disk (`fetch_raw`) so
it is unit-testable without hitting models.dev.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

CATALOG_URL = "https://models.dev/api.json"
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24h
_USER_AGENT = "voss-harness/0.1 (+models.dev catalog)"

# Provider families Voss routes, in display order. Keys are models.dev provider
# ids; the value is the order rank (lower = higher in the picker).
TARGET_PROVIDERS: tuple[str, ...] = (
    "anthropic",
    "openai",
    "opencode",      # OpenCode Zen
    "opencode-go",   # OpenCode Go
    "ollama-cloud",
)


def cache_path() -> Path:
    """Catalog cache location (XDG_CACHE_HOME-aware)."""
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "voss" / "models.json"


@dataclass(frozen=True)
class ModelEntry:
    """One selectable model, flattened from a models.dev provider+model pair."""

    id: str                       # models.dev model id (e.g. "gemma3:27b")
    name: str                     # display name (e.g. "Gemma 3 27B")
    provider_id: str              # models.dev provider id (e.g. "ollama-cloud")
    provider_label: str           # display group (e.g. "Ollama Cloud")
    api_base: str | None          # OpenAI-compatible base URL, or None for native
    env_key: str | None           # API-key env var (e.g. "OLLAMA_API_KEY")
    free: bool                    # cost is explicitly $0 in + $0 out
    subscription: bool            # cost is unpriced (Ollama Cloud) — no tag
    context: int | None           # context-window tokens
    tool_call: bool               # supports tool/function calling


@dataclass(frozen=True)
class ProviderGroup:
    """A picker section: one provider and its models, in catalog order."""

    id: str
    label: str
    api_base: str | None
    env_key: str | None
    models: tuple[ModelEntry, ...]


def _is_free(model: dict) -> bool:
    cost = model.get("cost")
    return (
        isinstance(cost, dict)
        and cost.get("input", 1) == 0
        and cost.get("output", 1) == 0
    )


def _model_entry(provider_id: str, provider_label: str, api_base: str | None,
                 env_key: str | None, model: dict) -> ModelEntry:
    cost = model.get("cost")
    limit = model.get("limit") or {}
    context = limit.get("context") if isinstance(limit, dict) else None
    return ModelEntry(
        id=str(model.get("id", "")),
        name=str(model.get("name") or model.get("id", "")),
        provider_id=provider_id,
        provider_label=provider_label,
        api_base=api_base,
        env_key=env_key,
        free=_is_free(model),
        subscription=cost is None,
        context=context if isinstance(context, int) else None,
        tool_call=bool(model.get("tool_call", False)),
    )


def parse_catalog(
    raw: dict, *, providers: Iterable[str] = TARGET_PROVIDERS
) -> list[ProviderGroup]:
    """Filter the raw models.dev dict to `providers` and normalize to groups.

    Pure — no network/disk. Provider order follows `providers`; model order
    follows the catalog's own ordering. Unknown/absent providers are skipped.
    """
    order = list(providers)
    groups: list[ProviderGroup] = []
    for pid in order:
        prov = raw.get(pid)
        if not isinstance(prov, dict):
            continue
        models_raw = prov.get("models")
        if not isinstance(models_raw, dict) or not models_raw:
            continue
        label = str(prov.get("name") or pid)
        api_base = prov.get("api") or None
        env_list = prov.get("env")
        env_key = env_list[0] if isinstance(env_list, list) and env_list else None
        entries = tuple(
            _model_entry(pid, label, api_base, env_key, m)
            for m in models_raw.values()
            if isinstance(m, dict) and m.get("id")
        )
        if entries:
            groups.append(
                ProviderGroup(
                    id=pid,
                    label=label,
                    api_base=api_base,
                    env_key=env_key,
                    models=entries,
                )
            )
    return groups


def _read_cache(path: Path) -> tuple[dict | None, float]:
    """Return (data, fetched_at) from cache, or (None, 0.0) if absent/corrupt."""
    try:
        blob = json.loads(path.read_text())
        data = blob.get("data")
        fetched_at = float(blob.get("fetched_at", 0.0))
        if isinstance(data, dict):
            return data, fetched_at
    except (OSError, ValueError, TypeError):
        pass
    return None, 0.0


def _write_cache(path: Path, data: dict, *, now: float) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"fetched_at": now, "data": data}))
    except OSError:
        pass  # cache is best-effort; a write failure must not break the picker


def _http_get_json(url: str, *, timeout: float) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (trusted URL)
        return json.loads(resp.read().decode("utf-8"))


def fetch_raw(
    *,
    force: bool = False,
    ttl: float = CACHE_TTL_SECONDS,
    timeout: float = 15.0,
    url: str = CATALOG_URL,
    path: Path | None = None,
    now: Callable[[], float] = time.time,
    http_get: Callable[[str], dict] | None = None,
) -> dict:
    """Return the raw models.dev catalog dict, network + disk-cache aware.

    Fresh cache (within `ttl`) is returned without a network call. Otherwise a
    fetch is attempted; on success the cache is refreshed, on failure a stale
    cache (any age) is used as a fallback. Raises RuntimeError only when there
    is neither a usable fetch nor any cache. `now`/`http_get`/`path` are
    injectable for deterministic tests.
    """
    path = path or cache_path()
    fetch = http_get or (lambda u: _http_get_json(u, timeout=timeout))
    cached, fetched_at = _read_cache(path)
    current = now()

    if not force and cached is not None and (current - fetched_at) < ttl:
        return cached

    try:
        data = fetch(url)
        if not isinstance(data, dict) or not data:
            raise ValueError("empty or malformed catalog")
        _write_cache(path, data, now=current)
        return data
    except Exception as exc:  # noqa: BLE001 — network/parse; fall back to cache
        if cached is not None:
            return cached
        raise RuntimeError(f"models.dev catalog unavailable and no cache: {exc}") from exc


def load_catalog(
    *,
    providers: Iterable[str] = TARGET_PROVIDERS,
    force: bool = False,
    **fetch_kwargs,
) -> list[ProviderGroup]:
    """Fetch (cached) + parse into provider groups for the picker."""
    raw = fetch_raw(force=force, **fetch_kwargs)
    return parse_catalog(raw, providers=providers)
