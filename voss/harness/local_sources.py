"""Local Claude/Codex configuration locations shared by MCP and skills."""
from __future__ import annotations

import json
import os
import tomllib
import warnings
from pathlib import Path


def user_home() -> Path:
    return Path.home()


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", user_home() / ".codex"))


def project_dirs(cwd: Path) -> list[Path]:
    cwd = cwd.resolve()
    directories = []
    for root in (cwd, *cwd.parents):
        directories.append(root)
        if (root / ".git").exists():
            return list(reversed(directories))
    return [cwd]


def read_config(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
        value = tomllib.loads(text) if path.suffix == ".toml" else json.loads(text)
        if not isinstance(value, dict):
            raise ValueError("expected object")
        return value
    except (OSError, ValueError):
        warnings.warn(f"Could not read local configuration: {path}", stacklevel=2)
        return {}
