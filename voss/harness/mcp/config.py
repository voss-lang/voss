"""
MCP configuration discovery with Voss overrides.
"""
from __future__ import annotations

import os
import re
import warnings
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

from .. import local_sources
from ..config import config_path

STRICT = {"extra": "forbid"}


class McpConfigError(Exception):
    """Raised when MCP config cannot be loaded or substituted."""


class McpServerConfig(BaseModel):
    model_config = STRICT
    command: list[str] = Field(default_factory=list)
    args: list[str] = Field(default_factory=list)
    timeout_s: float = 30.0
    env: Optional[list[str] | dict[str, str]] = None
    env_vars: list[str] | None = None
    cwd: str | None = None
    url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    env_headers: dict[str, str] = Field(default_factory=dict)
    bearer_token_env_var: str | None = None
    enabled: bool = True
    enabled_tools: list[str] | None = None
    disabled_tools: list[str] = Field(default_factory=list)
    source: str = "voss"

    @model_validator(mode="after")
    def validate_transport(self):
        if self.enabled and bool(self.command) == bool(self.url):
            raise ValueError("specify either command or url")
        return self


class McpServerExposureConfig(BaseModel):
    model_config = STRICT
    name: str | None = None
    exposed_tools: list[str] | Literal["*"] = "*"
    exposed_skills: list[str] | Literal["*"] = "*"


class McpConfig(BaseModel):
    model_config = STRICT
    server: McpServerExposureConfig | None = None
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
        **{k: v for k, v in (config.model_dump() if isinstance(config, McpServerConfig) else vars(config)).items()
           if k not in {"command", "args", "env", "cwd", "url", "headers"}},
        command=[_substitute(item, cwd=cwd) for item in config.command],
        args=[_substitute(item, cwd=cwd) for item in config.args],
        env=({k: _substitute(v, cwd=cwd) for k, v in config.env.items()}
             if isinstance(config.env, dict) else config.env),
        cwd=_substitute(config.cwd, cwd=cwd) if getattr(config, "cwd", None) else None,
        url=_substitute(config.url, cwd=cwd) if getattr(config, "url", None) else None,
        headers={k: _substitute(v, cwd=cwd) for k, v in getattr(config, "headers", {}).items()},
    )


def load_mcp_config(cwd: Path) -> McpConfig | None:
    """Discover local servers, then apply user and project Voss overrides."""
    servers: dict[str, McpServerConfig] = {}
    claude = local_sources.read_config(local_sources.user_home() / ".claude.json")
    layers = [(claude.get("mcpServers", {}), "claude")]
    layers.append((local_sources.read_config(local_sources.codex_home() / "config.toml").get("mcp_servers", {}), "codex"))
    for root in local_sources.project_dirs(cwd):
        layers.append((local_sources.read_config(root / ".mcp.json").get("mcpServers", {}), "claude"))
        layers.append((local_sources.read_config(root / ".codex" / "config.toml").get("mcp_servers", {}), "codex"))
    projects = claude.get("projects", {})
    project = projects.get(str(cwd.resolve()), {}) if isinstance(projects, dict) else {}
    if not isinstance(project, dict):
        project = {}
    layers.append((project.get("mcpServers", {}), "claude"))
    for entries, source in layers:
        if not isinstance(entries, dict):
            continue
        for name, entry in entries.items():
            try:
                servers[name] = _import_server(entry, source)
            except (ValueError, TypeError, AttributeError):
                servers.pop(name, None)
                warnings.warn(f"Unsupported MCP configuration: {source}/{name}", stacklevel=2)
    for name in project.get("disabledMcpServers", []):
        if name in servers and servers[name].source == "claude":
            servers[name].enabled = False
    result = McpConfig(servers=servers)
    for path in (config_path().parent / "mcp.yml", cwd / ".voss" / "mcp.yml"):
        if not path.is_file():
            continue
        try:
            override = McpConfig.model_validate(yaml.safe_load(path.read_text()) or {})
        except (OSError, yaml.YAMLError, ValidationError):
            raise McpConfigError(f"{path}: invalid MCP configuration") from None
        result.servers.update(override.servers)
        if override.server is not None:
            result.server = override.server
    result.servers = {name: server for name, server in result.servers.items() if server.enabled}
    return result if result.servers or result.server else None


def _import_server(entry: dict, source: str) -> McpServerConfig:
    if entry.get("type", "stdio" if "command" in entry else "http") not in ("stdio", "http"):
        raise ValueError("unsupported transport")
    if entry.get("experimental_environment") == "remote" or entry.get("http_headers_helper"):
        raise ValueError("requires host execution")
    command = entry.get("command", [])
    if isinstance(command, str):
        command = [command]
    return McpServerConfig(
        command=command, args=entry.get("args", []), env=entry.get("env"),
        env_vars=entry.get("env_vars"),
        cwd=entry.get("cwd"), url=entry.get("url"),
        headers=entry.get("http_headers", entry.get("headers", {})),
        env_headers=entry.get("env_http_headers", {}),
        bearer_token_env_var=entry.get("bearer_token_env_var"),
        enabled=entry.get("enabled", not entry.get("disabled", False)),
        enabled_tools=entry.get("enabled_tools"), disabled_tools=entry.get("disabled_tools", []),
        timeout_s=entry.get("tool_timeout_sec", 30.0), source=source,
    )
