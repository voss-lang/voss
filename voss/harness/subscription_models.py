"""Curated model lists for subscription auth paths (R8 `/model` picker).

The catalog-driven `/models` picker routes API-key providers; subscription
providers (Claude via the Agent SDK, ChatGPT via the Codex backend) accept
only a narrow, account-billed model set with no listing API. This module is
the ONE place that set lives: `SUBSCRIPTION_MODELS` maps auth mode →
curated entries, `detect_auth_mode` maps the live provider object back to
its auth mode, and `match` implements the `/model <query>` precedence
(exact id → unique prefix → unique substring).

Lists are best-effort: neither backend validates a model id up front, so a
stale/wrong id surfaces as a turn error, same as a hand-typed `/model <id>`.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubscriptionModel:
    """One curated row: id is what the backend accepts, label/description
    are picker copy. `recommended` tags the suggested default."""

    id: str
    label: str
    description: str
    recommended: bool = False


# Auth mode → curated models, in picker order. Claude ids track the ones the
# harness already pins (cli.py boot snap, config.py role aliases); Codex ids
# are the gpt-5.x set the ChatGPT backend serves (providers.py:475 — older
# gpt-5/gpt-5-codex ids 400).
SUBSCRIPTION_MODELS: dict[str, tuple[SubscriptionModel, ...]] = {
    "claude": (
        SubscriptionModel(
            "claude-sonnet-4-5",
            "Sonnet 4.5",
            "Balanced speed and capability · everyday default",
            recommended=True,
        ),
        SubscriptionModel(
            "claude-opus-4-8",
            "Opus 4.8",
            "Most capable · hard, multi-step work",
        ),
        SubscriptionModel(
            "claude-fable-5",
            "Fable 5",
            "Latest frontier generation",
        ),
        SubscriptionModel(
            "claude-haiku-4-5",
            "Haiku 4.5",
            "Fastest and cheapest · light tasks",
        ),
    ),
    "codex": (
        SubscriptionModel(
            "gpt-5.5",
            "GPT-5.5",
            "Flagship · the Codex backend default",
            recommended=True,
        ),
        SubscriptionModel(
            "gpt-5.4",
            "GPT-5.4",
            "Strong general-purpose Codex model",
        ),
        SubscriptionModel(
            "gpt-5.4-mini",
            "GPT-5.4 mini",
            "Smaller and faster · light tasks",
        ),
        SubscriptionModel(
            "gpt-5.3-codex-spark",
            "GPT-5.3 Codex Spark",
            "Fast coding-specialized model",
        ),
    ),
}


def detect_auth_mode(provider: object) -> str | None:
    """Map a live `ctx.provider` to its subscription auth mode, or None.

    ClaudeAgentProvider only ever comes from `--auth=claude` (cli.py
    `_resolve_auth_or_die`), OpenAIOAuthProvider only from the codex-oauth
    path — so an isinstance check is the auth signal. API-key providers
    (LiteLLM, routed catalog providers) return None.
    """
    try:
        from .claude_agent_provider import ClaudeAgentProvider

        if isinstance(provider, ClaudeAgentProvider):
            return "claude"
    except ImportError:  # pragma: no cover — provider module always present
        pass
    try:
        from .providers import OpenAIOAuthProvider

        if isinstance(provider, OpenAIOAuthProvider):
            return "codex"
    except ImportError:  # pragma: no cover
        pass
    return None


def match(auth_mode: str, query: str) -> list[SubscriptionModel]:
    """Resolve `/model <query>` against the curated list for `auth_mode`.

    Precedence: exact id match, else id-prefix matches, else id-substring
    matches (all case-insensitive). Returns [] when nothing matches —
    callers fall back to the raw set-anything behavior.
    """
    models = SUBSCRIPTION_MODELS.get(auth_mode, ())
    q = query.strip().lower()
    if not q:
        return []
    exact = [m for m in models if m.id.lower() == q]
    if exact:
        return exact
    prefix = [m for m in models if m.id.lower().startswith(q)]
    if prefix:
        return prefix
    return [m for m in models if q in m.id.lower()]
