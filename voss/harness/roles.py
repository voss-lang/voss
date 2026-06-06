"""Model roles + fallback chains.

A *role* names a model-selection intent (`default` turn, `smol` cheap
subagents, `slow` deep reasoning, `plan`, `commit`). Each role maps to an
ordered list of `(provider, model)` candidates declared in the harness config:

    [harness.roles.default]
    chain = [
      { provider = "anthropic", model = "claude-opus-4-8" },
      { provider = "opencode",  model = "claude-opus-4-5" },
    ]

    [harness.roles.smol]
    chain = [{ provider = "anthropic", model = "claude-haiku-4-5" }]

`build_role_provider` resolves a chain against the live model catalog + key
store and returns a `FallbackProvider` that cascades on 429/quota. This module
is the policy layer; the cascade mechanics live in
`voss_runtime.providers.fallback`.
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from voss_runtime.providers.base import ModelProvider
from voss_runtime.providers.fallback import FallbackProvider

from . import model_catalog, model_router
from .model_catalog import ProviderGroup

ROLES = ("default", "smol", "slow", "plan", "commit")

KeyGetter = Callable[[str], "str | None"]


@dataclass(frozen=True)
class RoleCandidate:
    provider: str
    model: str


def load_role_chains(path: Path | None = None) -> dict[str, list[RoleCandidate]]:
    """Parse `[harness.roles.<role>] chain = [{provider, model}, ...]`.

    Missing file/section or a parse error yields `{}` (caller keeps defaults).
    Unknown role names are kept as-is (validated at use); rows missing
    provider/model are skipped; a role with no valid rows is omitted.
    """
    from . import config as _config

    p = path or _config.config_path()
    if not p.exists():
        return {}
    try:
        data = tomllib.loads(p.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    roles = ((data.get("harness") or {}).get("roles")) or {}
    out: dict[str, list[RoleCandidate]] = {}
    for role, spec in roles.items():
        chain = (spec or {}).get("chain") or []
        cands: list[RoleCandidate] = []
        for row in chain:
            if not isinstance(row, dict):
                continue
            prov, mdl = row.get("provider"), row.get("model")
            if prov and mdl:
                cands.append(RoleCandidate(str(prov), str(mdl)))
        if cands:
            out[role] = cands
    return out


def build_role_provider(
    role: str,
    *,
    groups: list[ProviderGroup] | None = None,
    catalog_loader: Callable[[], list[ProviderGroup]] | None = None,
    getter: KeyGetter = os.environ.get,
    keyring_get: KeyGetter | None = None,
    chains: dict[str, list[RoleCandidate]] | None = None,
) -> tuple[ModelProvider, str] | None:
    """Build a `FallbackProvider` for `role` from its configured chain.

    Each candidate is resolved against the model catalog (provider_id +
    model_id) and its API key. Returns `(provider, primary_model)`, or `None`
    when the chain is absent/empty or no candidate resolves in the catalog (the
    caller then keeps its existing single-model provider). Never raises on
    catalog/IO problems.
    """
    from . import auth

    if keyring_get is None:
        keyring_get = auth.load_provider_key

    cmap = chains if chains is not None else load_role_chains()
    cands = cmap.get(role) or []
    if not cands:
        return None

    if groups is None:
        loader = catalog_loader or model_catalog.load_catalog
        try:
            groups = loader()
        except Exception:  # noqa: BLE001 — offline/parse: keep caller's default
            return None

    built: list[tuple[ModelProvider, str]] = []
    for c in cands:
        entry = model_router.find_entry(groups, c.provider, c.model)
        if entry is None:
            continue
        key = model_router.resolve_key(entry, getter=getter, keyring_get=keyring_get)
        prov, mstr = model_router.build_provider_for_model(entry, api_key=key)
        built.append((prov, mstr))
    if not built:
        return None
    return FallbackProvider(built), built[0][1]


def role_or_default(
    role: str,
    default_provider: ModelProvider,
    default_model: str,
    **kw,
) -> tuple[ModelProvider, str]:
    """Resolve `role` to its `(provider, model)`, or `(default_provider,
    default_model)` when the role chain is absent/unresolvable. The lookup is
    network-free unless the role actually has a configured chain (see
    `build_role_provider`)."""
    built = build_role_provider(role, **kw)
    return built if built is not None else (default_provider, default_model)
