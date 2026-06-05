"""Persisted model preferences for the /models picker: recents + favorites.

Stored as JSON at ~/.config/voss/model_prefs.json (XDG-aware), separate from
config.toml so the ordered/list shapes stay clean:

    {"recent": [["ollama-cloud", "gemma3:27b"], ...],
     "favorites": [["opencode", "kimi-k2.5-free"], ...]}

Each item is a [provider_id, model_id] pair (a model id can repeat across
providers, so the provider scopes it). Recents are most-recent-first, deduped,
and capped. All writes are best-effort — a failure never breaks the picker.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

RECENT_CAP = 8
Pair = tuple[str, str]


def prefs_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "voss" / "model_prefs.json"


def _load(path: Path | None = None) -> dict:
    path = path or prefs_path()
    try:
        data = json.loads(path.read_text())
        if isinstance(data, dict):
            return data
    except (OSError, ValueError, TypeError):
        pass
    return {}


def _pairs(data: dict, key: str) -> list[Pair]:
    out: list[Pair] = []
    for item in data.get(key, []) or []:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            out.append((str(item[0]), str(item[1])))
    return out


def _save(data: dict, path: Path | None = None) -> bool:
    path = path or prefs_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
        path.chmod(0o600)
        return True
    except OSError:
        return False


def recent(path: Path | None = None) -> list[Pair]:
    """Recently-used (provider_id, model_id) pairs, most-recent first."""
    return _pairs(_load(path), "recent")


def favorites(path: Path | None = None) -> list[Pair]:
    """Favorited (provider_id, model_id) pairs, in insertion order."""
    return _pairs(_load(path), "favorites")


def record_recent(provider_id: str, model_id: str, *, path: Path | None = None,
                  cap: int = RECENT_CAP) -> None:
    """Move (provider_id, model_id) to the front of the recents list."""
    data = _load(path)
    pair = [provider_id, model_id]
    items = [p for p in _pairs(data, "recent") if list(p) != pair]
    items.insert(0, (provider_id, model_id))
    data["recent"] = [list(p) for p in items[:cap]]
    _save(data, path)


def is_favorite(provider_id: str, model_id: str, *, path: Path | None = None) -> bool:
    return (provider_id, model_id) in favorites(path)


def toggle_favorite(provider_id: str, model_id: str, *, path: Path | None = None) -> bool:
    """Add/remove a favorite. Returns the new state (True = now favorited)."""
    data = _load(path)
    pair = (provider_id, model_id)
    items = _pairs(data, "favorites")
    if pair in items:
        items = [p for p in items if p != pair]
        now = False
    else:
        items.append(pair)
        now = True
    data["favorites"] = [list(p) for p in items]
    _save(data, path)
    return now
