"""Configuration loader for .voss/lsp.yml + packaged defaults.

Strict Pydantic models (extra=forbid). Defaults are always loaded from the
installed package; user .voss/lsp.yml is an overlay that can disable languages
or override command/args.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

STRICT = {"extra": "forbid"}


class LspServerConfig(BaseModel):
    model_config = STRICT
    command: list[str]
    args: list[str] = Field(default_factory=list)
    init_options: dict[str, Any] = Field(default_factory=dict)
    root_markers: list[str] = Field(default_factory=list)
    disabled: bool = False


class LspConfig(BaseModel):
    model_config = STRICT
    servers: dict[str, LspServerConfig] = Field(default_factory=dict)
    default_max_results: int = 50
    scan_timeout_ms: int = 5000
    partial_index_threshold_ms: int = 30000


# Lazy import of package data (avoids import-time cost when not using code extra)
def _load_defaults() -> dict[str, Any]:
    """Load the packaged defaults/lsp.yml."""
    # The defaults file lives next to this module inside the installed package
    defaults_path = Path(__file__).parent / "defaults" / "lsp.yml"
    if not defaults_path.exists():
        # Fallback for development layout
        defaults_path = Path(__file__).parent.parent.parent.parent / "voss/harness/code/defaults/lsp.yml"
    if not defaults_path.exists():
        raise FileNotFoundError(f"Could not locate defaults/lsp.yml at {defaults_path}")
    raw = yaml.safe_load(defaults_path.read_text(encoding="utf-8")) or {}
    return raw


def load_lsp_config(cwd: Path | None = None) -> LspConfig:
    """Load packaged defaults, then overlay optional .voss/lsp.yml from cwd.

    Never raises on missing user file — user file is purely optional.
    """
    defaults = _load_defaults()
    try:
        base = LspConfig.model_validate({"servers": defaults})
    except ValidationError as exc:
        raise RuntimeError(f"Invalid packaged defaults/lsp.yml: {exc}") from exc

    if cwd is None:
        return base

    user_path = cwd / ".voss" / "lsp.yml"
    if not user_path.exists():
        return base

    try:
        raw_user = yaml.safe_load(user_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError(f"{user_path}: invalid YAML: {exc}") from exc

    try:
        user_cfg = LspConfig.model_validate(raw_user)
    except ValidationError as exc:
        raise RuntimeError(f"{user_path}: validation error: {exc}") from exc

    # Merge: user overrides win, but we keep disabled=false entries from defaults
    merged_servers = dict(base.servers)
    for name, user_server in user_cfg.servers.items():
        if name in merged_servers:
            # Simple override — user can disable by setting disabled: true
            merged_servers[name] = user_server
        else:
            merged_servers[name] = user_server

    return LspConfig(
        servers=merged_servers,
        default_max_results=user_cfg.default_max_results or base.default_max_results,
        scan_timeout_ms=user_cfg.scan_timeout_ms or base.scan_timeout_ms,
        partial_index_threshold_ms=user_cfg.partial_index_threshold_ms or base.partial_index_threshold_ms,
    )
