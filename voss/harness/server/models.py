"""Server-owned model choices and credential-safe provider construction."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from .. import auth, model_catalog, model_router
from ..subscription_models import SUBSCRIPTION_MODELS


class ModelSelectionBody(BaseModel):
    model: str = Field(default="", max_length=256)
    auth: Literal["claude", "codex", "api"] | None = None
    provider: str | None = Field(default=None, max_length=128)


class ModelChoice(BaseModel):
    id: str
    name: str
    provider: str
    provider_label: str
    auth: Literal["claude", "codex", "api"]
    connected: bool
    recommended: bool


class ModelCatalog(BaseModel):
    v: int = 1
    models: list[ModelChoice]
    warning: str


@dataclass
class Selection:
    choice: ModelChoice
    provider: Any
    model: str
    source: str


def subscription_choices() -> list[ModelChoice]:
    return [
        ModelChoice(
            id=m.id, name=m.label, auth=mode,
            provider="anthropic" if mode == "claude" else "openai",
            provider_label="Claude subscription" if mode == "claude" else "Codex subscription",
            recommended=m.recommended, connected=False,
        )
        for mode, models in SUBSCRIPTION_MODELS.items()
        for m in models
    ]


def subscription_resolution(mode: str):
    try:
        res = auth.resolve(mode)
        expected = "claude-agent" if mode == "claude" else "codex-oauth"
        if res.source == expected:
            if mode == "codex" and (
                not res.codex_oauth or not res.codex_oauth.has_oauth
                or not isinstance(res.codex_oauth.auth_mode, str)
                or res.codex_oauth.auth_mode.lower() != "chatgpt"
            ):
                raise ValueError("Codex subscription requires ChatGPT OAuth")
            return res
    except Exception:
        pass
    login = "claude /login" if mode == "claude" else "codex login"
    raise ValueError(f"No usable {mode} subscription login. Run `{login}`, then retry.")


def api_entries() -> list[model_catalog.ModelEntry]:
    return [m for g in model_catalog.load_catalog() for m in g.models if m.tool_call]


def api_choice(entry: model_catalog.ModelEntry, *, connected: bool = False) -> ModelChoice:
    return ModelChoice(
        id=entry.id, name=entry.name, provider=entry.provider_id,
        provider_label=entry.provider_label + " API", auth="api", connected=connected,
        recommended=False,
    )


def catalog() -> ModelCatalog:
    choices = subscription_choices()
    for mode in SUBSCRIPTION_MODELS:
        try:
            subscription_resolution(mode)
            connected = True
        except ValueError:
            connected = False
        for choice in choices:
            if choice.auth == mode:
                choice.connected = connected
    warning = ""
    try:
        connected_api: dict[str, bool] = {}
        for entry in api_entries():
            if entry.provider_id not in connected_api:
                connected_api[entry.provider_id] = (
                    entry.env_key is None or bool(model_router.resolve_key(entry))
                )
            choices.append(api_choice(entry, connected=connected_api[entry.provider_id]))
    except Exception:
        warning = "API catalog unavailable; subscription models are still available."
    return ModelCatalog(models=choices, warning=warning)


def _match(choices: list[ModelChoice], query: str) -> list[ModelChoice]:
    query = query.strip().lower()
    exact = [m for m in choices if m.id.lower() == query]
    return exact or [m for m in choices if query in m.id.lower() or query in m.name.lower()]


def prepare(body: ModelSelectionBody, current_model: str) -> Selection:
    choices = [m for m in subscription_choices() if body.auth in (None, m.auth)]
    if body.provider:
        choices = [m for m in choices if m.provider == body.provider]
    query = body.model.strip()
    if not query and body.auth in SUBSCRIPTION_MODELS:
        if not choices:
            raise ValueError("Provider does not match the requested authentication route.")
        query = next((m.id for m in choices if m.id == current_model), "")
        query = query or next(m.id for m in choices if m.recommended)
    matches = _match(choices, query) if query else []
    entries = []
    if not matches and body.auth in (None, "api"):
        try:
            entries = api_entries()
        except Exception:
            raise ValueError("API catalog unavailable. Retry /models when connected.") from None
        if body.provider:
            entries = [m for m in entries if m.provider_id == body.provider]
        if not query:
            entries = [m for m in entries if m.env_key is None or model_router.resolve_key(m)]
            current = [m for m in entries if model_router.model_string(m) == current_model]
            entries = current or entries[:1]
        choices = [api_choice(m) for m in entries]
        if query.startswith("openai/") and not any(m.id == query for m in choices):
            query = query.removeprefix("openai/")
        matches = _match(choices, query) if query else choices
    if len(matches) != 1:
        reason = "Ambiguous model" if matches else "No matching model"
        raise ValueError(f"{reason}. Use /models to select a model and authentication route.")
    choice = matches[0]
    if choice.auth == "api":
        entry = next(m for m in entries if (m.id, m.provider_id) == (choice.id, choice.provider))
        key = model_router.resolve_key(entry)
        if entry.env_key and not key:
            raise ValueError(f"No API key for {choice.provider_label}. Run `voss login` first.")
        try:
            provider, model = model_router.build_provider_for_model(entry, api_key=key)
        except Exception:
            raise ValueError("Could not initialize the API provider. Selection unchanged.") from None
        return Selection(choice, provider, model, "api")
    return _subscription_selection(choice)


def restore(model: str, mode: str, provider: str | None) -> Selection:
    if provider:
        mode = "api"
    if mode not in SUBSCRIPTION_MODELS:
        return prepare(ModelSelectionBody(model=model, auth=mode, provider=provider), "")
    compatible = model.startswith("claude-") if mode == "claude" else auth.is_codex_backend_model(model)
    if not compatible:
        raise ValueError("Saved model does not match its authentication route.")
    choice = next(m for m in subscription_choices() if m.auth == mode)
    return _subscription_selection(choice.model_copy(update={"id": model, "name": model}))


def _subscription_selection(choice: ModelChoice) -> Selection:
    res = subscription_resolution(choice.auth)
    try:
        if choice.auth == "claude":
            from ..claude_agent_provider import ClaudeAgentProvider

            provider = ClaudeAgentProvider(model_default=choice.id, cli_path=res.cli_path)
        else:
            from ..providers import OpenAIOAuthProvider

            provider = OpenAIOAuthProvider(res.codex_oauth)
    except Exception:
        raise ValueError("Could not initialize the subscription provider. Check your local login; selection unchanged.") from None
    return Selection(choice, provider, choice.id, res.source)


def provider_label(provider: Any, source: str) -> str:
    label = getattr(provider, "voss_provider_label", "")
    if label:
        return label
    if source in ("codex", "codex-oauth"):
        return "Codex"
    if source in ("claude-agent", "env-anthropic", "voss-anthropic"):
        return "Anthropic"
    if source in ("env-openai", "voss-openai"):
        return "OpenAI"
    return source
