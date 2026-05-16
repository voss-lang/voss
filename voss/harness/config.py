"""Harness config persistence (~/.config/voss/config.toml).

Today the only key is [harness] preferred_model, set by the REPL /model
slash command. Kept narrow on purpose — anything richer goes under .voss/ in M2.

T1-04 added an [agent] section reader / writer for max_iterations (default
8). [agent] was picked over [loop] because it leaves room for future agent-
loop neighbors (confidence_threshold, timeout, etc.) without renaming.
"""
from __future__ import annotations

import os
import re
import warnings
from pathlib import Path

from voss_runtime._config import RuntimeConfig


def config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "voss" / "config.toml"


_HARNESS_BLOCK = re.compile(r"^\[harness\][^\[]*", re.MULTILINE)
_AGENT_BLOCK = re.compile(r"^\[agent\][^\[]*", re.MULTILINE)
_KV = re.compile(r'^\s*(\w+)\s*=\s*"((?:[^"\\]|\\.)*)"\s*$', re.MULTILINE)


def _parse_harness_section(text: str) -> dict[str, str]:
    m = _HARNESS_BLOCK.search(text)
    if not m:
        return {}
    block = m.group(0)
    return {k: v for k, v in _KV.findall(block)}


def _parse_agent_section(text: str) -> dict[str, str]:
    m = _AGENT_BLOCK.search(text)
    if not m:
        return {}
    block = m.group(0)
    return {k: v for k, v in _KV.findall(block)}


def load_harness_config() -> dict[str, str]:
    """Return the `[harness]` section as a dict. Missing file -> {}."""
    p = config_path()
    if not p.exists():
        return {}
    try:
        text = p.read_text()
    except OSError:
        return {}
    return _parse_harness_section(text)


def load_agent_config() -> dict[str, str]:
    """Return the `[agent]` section as a dict. Missing file / section -> {}."""
    p = config_path()
    if not p.exists():
        return {}
    try:
        text = p.read_text()
    except OSError:
        return {}
    return _parse_agent_section(text)


def get_max_iterations() -> int:
    """Resolve agent.max_iterations, falling back to RuntimeConfig default."""
    default = RuntimeConfig().max_iterations
    cfg = load_agent_config()
    raw = cfg.get("max_iterations")
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        warnings.warn(
            f"[agent] max_iterations = {raw!r} is not an integer; "
            f"falling back to default {default}",
            RuntimeWarning,
            stacklevel=2,
        )
        return default


def set_preferred_model(name: str) -> Path:
    """Persist `[harness] preferred_model = "<name>"`. Preserves other sections."""
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    existing = p.read_text() if p.exists() else ""

    new_block = f'[harness]\npreferred_model = "{name}"\n'
    if _HARNESS_BLOCK.search(existing):
        new_text = _HARNESS_BLOCK.sub(new_block, existing, count=1)
    elif existing.strip():
        new_text = existing.rstrip() + "\n\n" + new_block
    else:
        new_text = new_block

    p.write_text(new_text)
    p.chmod(0o600)
    return p


def set_max_iterations(n: int) -> Path:
    """Persist `[agent] max_iterations = "<n>"`. Preserves [harness] section."""
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    existing = p.read_text() if p.exists() else ""

    new_block = f'[agent]\nmax_iterations = "{n}"\n'
    if _AGENT_BLOCK.search(existing):
        new_text = _AGENT_BLOCK.sub(new_block, existing, count=1)
    elif existing.strip():
        new_text = existing.rstrip() + "\n\n" + new_block
    else:
        new_text = new_block

    p.write_text(new_text)
    p.chmod(0o600)
    return p
