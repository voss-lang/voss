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
_TOOLS_BLOCK = re.compile(r"^\[tools\][^\[]*", re.MULTILINE)
_KV = re.compile(r'^\s*(\w+)\s*=\s*"((?:[^"\\]|\\.)*)"\s*$', re.MULTILINE)
# Bare (unquoted) right-hand values for [tools] keys like
# `allow_net = true`. The existing _KV regex only matches double-quoted
# strings; TOML booleans are bare, so they need their own matcher.
# The pattern captures any non-whitespace token after `=`; get_allow_net
# validates 'true' / 'false' and warns on anything else.
_KV_BARE = re.compile(r"^\s*(\w+)\s*=\s*([^\s\"#]+)\s*$", re.MULTILINE)


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


def _parse_tools_section(text: str) -> dict[str, str]:
    """Return `[tools]` keys. Booleans go through _KV_BOOL (no quotes);
    quoted-string values would go through _KV. allow_net is boolean only."""
    m = _TOOLS_BLOCK.search(text)
    if not m:
        return {}
    block = m.group(0)
    out: dict[str, str] = {}
    for k, v in _KV.findall(block):
        out[k] = v
    for k, v in _KV_BARE.findall(block):
        # Don't overwrite a quoted-string match with a stray bare token
        # (e.g. when a value coincidentally lacks quotes).
        out.setdefault(k, v)
    return out


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


def load_tools_config() -> dict[str, str]:
    """Return the `[tools]` section as a dict. Missing file / section -> {}."""
    p = config_path()
    if not p.exists():
        return {}
    try:
        text = p.read_text()
    except OSError:
        return {}
    return _parse_tools_section(text)


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


def get_max_parallel_reads() -> int:
    """Resolve [agent] max_parallel_reads with range validation (T2-02, PAR-05).

    Range 1-32 inclusive. Missing key returns the RuntimeConfig default
    silently. Out-of-range or non-int values fall back to the default
    (get_config().max_parallel_reads) and emit a RuntimeWarning naming the
    offending value.
    """
    from voss_runtime import get_config

    default = get_config().max_parallel_reads
    cfg = load_agent_config()
    raw = cfg.get("max_parallel_reads")
    if raw is None:
        return default
    try:
        n = int(raw)
    except (TypeError, ValueError):
        warnings.warn(
            f"[agent] max_parallel_reads = {raw!r} is not an integer; "
            f"falling back to default {default}",
            RuntimeWarning,
            stacklevel=2,
        )
        return default
    if not (1 <= n <= 32):
        warnings.warn(
            f"[agent] max_parallel_reads = {n} out of range 1-32; "
            f"falling back to default {default}",
            RuntimeWarning,
            stacklevel=2,
        )
        return default
    return n


def get_allow_net() -> bool:
    """Resolve [tools] allow_net, falling back to RuntimeConfig default (False).

    Accepts exact 'true' / 'false' (case-insensitive). Any other value emits
    RuntimeWarning and falls back to the default. NET-05a/b acceptance.
    """
    default = RuntimeConfig().allow_net
    cfg = load_tools_config()
    raw = cfg.get("allow_net")
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    warnings.warn(
        f"[tools] allow_net = {raw!r} is not a boolean; "
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
