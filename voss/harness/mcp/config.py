"""Schema and loader for .voss/mcp.yml."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, ValidationError

STRICT = {"extra": "forbid"}


class McpConfigError(Exception):
    """Raised when MCP config cannot be loaded or substituted."""


class McpServerConfig(BaseModel):
    model_config = STRICT
    command: list[str]
    args: list[str] = Field(default_factory=list)
    timeout_s: float = 30.0
    env: Optional[list[str]] = None


class McpConfig(BaseModel):
    model_config = STRICT
    servers: dict[str, McpServerConfig] = Field(default_factory=dict)


_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _substitute(value: str, *, cwd: Path) -> str:
    def repl(match: re.Match[str]) -> str:
        var = match.group(1)
        val = os.environ.get(var)
        if val is None:
            raise McpConfigError(f"required env var {var!r} is unset")
        return val

    value = _VAR_RE.sub(repl, value)
    return value.replace("{cwd}", str(cwd))


def substitute_server(config: McpServerConfig, *, cwd: Path) -> McpServerConfig:
    """Return a copy with command/args substitutions applied."""

    return McpServerConfig(
        command=[_substitute(item, cwd=cwd) for item in config.command],
        args=[_substitute(item, cwd=cwd) for item in config.args],
        timeout_s=config.timeout_s,
        env=config.env,
    )


def load_mcp_config(cwd: Path) -> McpConfig | None:
    """Load {cwd}/.voss/mcp.yml, returning None when absent."""

    path = cwd / ".voss" / "mcp.yml"
    if not path.exists():
        return None
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise McpConfigError(f"{path}: invalid YAML: {exc}") from exc
    try:
        return McpConfig.model_validate(raw)
    except ValidationError as exc:
        raise McpConfigError(f"{path}: validation error: {exc}") from exc
