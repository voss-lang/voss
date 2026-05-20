from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

try:
    import tomli_w
except Exception:  # noqa: BLE001
    tomli_w = None  # type: ignore[assignment]


@dataclass(frozen=True)
class PluginManifest:
    id: str
    name: str
    description: str = ""
    enabled: bool = False
    commands: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    agents: tuple[str, ...] = ()
    source: Path | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    # skill binding
    voss_entry: str = ""
    skill_id: str = ""
    skill_mutating: bool = False
    # declared scopes (default-deny)
    scope_tools: str = "read-only"
    scope_fs: str = "cwd"
    scope_net: bool = False
    # trust
    sig_file: str = ""
    author_identity: str = ""
    # install metadata
    source_url: str = ""
    bundle_dir: Path | None = None


def user_plugin_dir() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "voss" / "plugins"


def project_plugin_dir(cwd: Path) -> Path:
    return cwd / ".voss" / "plugins"


def enablement_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "voss" / "plugins.toml"


def _load_enablement() -> dict[str, bool]:
    path = enablement_path()
    if not path.exists():
        return {}
    try:
        raw = tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    plugins = raw.get("plugins", {})
    if not isinstance(plugins, dict):
        return {}
    out: dict[str, bool] = {}
    for plugin_id, data in plugins.items():
        if isinstance(data, dict) and isinstance(data.get("enabled"), bool):
            out[str(plugin_id)] = bool(data["enabled"])
    return out


def set_plugin_enabled(plugin_id: str, enabled: bool) -> Path:
    path = enablement_path()
    current = _load_enablement()
    current[plugin_id] = enabled
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"plugins": {k: {"enabled": v} for k, v in sorted(current.items())}}
    if tomli_w is not None:
        text = tomli_w.dumps(payload)
    else:
        lines: list[str] = []
        for key, value in payload["plugins"].items():
            lines.append(f"[plugins.{key}]")
            lines.append(f"enabled = {'true' if value['enabled'] else 'false'}")
            lines.append("")
        text = "\n".join(lines)
    path.write_text(text)
    path.chmod(0o600)
    return path


def _string_list(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(str(x) for x in raw if isinstance(x, str))


def _read_manifest(
    path: Path,
    *,
    command_ids: set[str],
    skill_ids: set[str],
    agent_ids: set[str],
    enabled_overrides: dict[str, bool],
) -> PluginManifest | None:
    try:
        raw = tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return None
    plugin_id = str(raw.get("id", "")).strip()
    if not plugin_id:
        return None
    commands = _string_list(raw.get("commands"))
    skills = _string_list(raw.get("skills"))
    agents = _string_list(raw.get("agents"))
    warnings: list[str] = []
    known_commands: list[str] = []
    for command in commands:
        if command in command_ids:
            known_commands.append(command)
        else:
            warnings.append(f"unknown command: {command}")
    known_skills: list[str] = []
    for skill in skills:
        if skill in skill_ids:
            known_skills.append(skill)
        else:
            warnings.append(f"unknown skill: {skill}")
    known_agents: list[str] = []
    for agent in agents:
        if agent in agent_ids:
            known_agents.append(agent)
        else:
            warnings.append(f"unknown agent: {agent}")
    enabled = enabled_overrides.get(plugin_id, bool(raw.get("enabled", False)))
    # skill binding
    skill_tbl = raw.get("skill", {})
    if not isinstance(skill_tbl, dict):
        skill_tbl = {}
    # scopes (default-deny)
    scopes_tbl = raw.get("scopes", {})
    if not isinstance(scopes_tbl, dict):
        scopes_tbl = {}
    # trust
    trust_tbl = raw.get("trust", {})
    if not isinstance(trust_tbl, dict):
        trust_tbl = {}
    # install metadata
    install_tbl = raw.get("install", {})
    if not isinstance(install_tbl, dict):
        install_tbl = {}
    return PluginManifest(
        id=plugin_id,
        name=str(raw.get("name", plugin_id)),
        description=str(raw.get("description", "")),
        enabled=enabled,
        commands=tuple(known_commands),
        skills=tuple(known_skills),
        agents=tuple(known_agents),
        source=path,
        warnings=tuple(warnings),
        voss_entry=str(skill_tbl.get("entry", "")),
        skill_id=str(skill_tbl.get("id", "")),
        skill_mutating=bool(skill_tbl.get("mutating", False)),
        scope_tools=str(scopes_tbl.get("tools", "read-only")),
        scope_fs=str(scopes_tbl.get("fs", "cwd")),
        scope_net=bool(scopes_tbl.get("net", False)),
        sig_file=str(trust_tbl.get("sig_file", "")),
        author_identity=str(raw.get("author_identity", "")),
        source_url=str(install_tbl.get("source_url", "")),
        bundle_dir=path.parent if path.name == "manifest.toml" else None,
    )


def load_plugins(
    cwd: Path,
    *,
    command_ids: Iterable[str] = (),
    skill_ids: Iterable[str] = (),
    agent_ids: Iterable[str] = (),
) -> list[PluginManifest]:
    enabled_overrides = _load_enablement()
    manifests: list[PluginManifest] = []
    ids = (set(command_ids), set(skill_ids), set(agent_ids))
    for root in (project_plugin_dir(cwd), user_plugin_dir()):
        if not root.exists():
            continue
        for path in sorted(root.glob("*.toml")):
            manifest = _read_manifest(
                path,
                command_ids=ids[0],
                skill_ids=ids[1],
                agent_ids=ids[2],
                enabled_overrides=enabled_overrides,
            )
            if manifest is not None:
                manifests.append(manifest)
        # Also discover installed bundle subdirs: <root>/<id>/manifest.toml
        for path in sorted(root.glob("*/manifest.toml")):
            manifest = _read_manifest(
                path,
                command_ids=ids[0],
                skill_ids=ids[1],
                agent_ids=ids[2],
                enabled_overrides=enabled_overrides,
            )
            if manifest is not None:
                manifests.append(manifest)
    return manifests
