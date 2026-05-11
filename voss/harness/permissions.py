"""Permission gate for tool calls.

Modes:
- plan : reads auto, every write/shell prompts
- edit : reads + scoped writes auto, shell/net prompt   (default)
- auto : all allowlisted auto, destructive patterns prompt

Decisions persist per-cwd in ~/.config/voss/permissions.json.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Mode = Literal["plan", "edit", "auto"]

READ_ONLY = {"fs_read", "fs_glob", "fs_grep", "git_status", "git_diff", "voss_check"}
WRITE = {"fs_write", "fs_edit"}
SHELL = {"shell_run"}


def mode_allows(mode: Mode, tool_name: str, is_mutating: bool) -> tuple[bool, str]:
    """Strict tier check. Returns (allowed_by_mode, reason).

    plan : read-only — denies all mutating tools.
    edit : reads + fs_write/fs_edit — explicitly denies shell_run.
    auto : everything — caller still enforces allowlist/timeouts downstream.
    """
    if mode == "plan":
        if is_mutating:
            return False, "denied by mode plan"
        return True, "ok"
    if mode == "edit":
        if tool_name == "shell_run":
            return False, "denied by mode edit"
        return True, "ok"
    return True, "ok"


def _config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "voss" / "permissions.json"


@dataclass
class PermissionStore:
    """Persisted always-allow decisions per cwd."""

    cwd: Path
    always: set[str] = field(default_factory=set)

    @classmethod
    def load(cls, cwd: Path) -> "PermissionStore":
        p = _config_path()
        if not p.exists():
            return cls(cwd=cwd)
        try:
            data = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            return cls(cwd=cwd)
        key = str(cwd.resolve())
        always = set(data.get(key, {}).get("always", []))
        return cls(cwd=cwd, always=always)

    def save(self) -> None:
        p = _config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(p.read_text()) if p.exists() else {}
        except (OSError, json.JSONDecodeError):
            data = {}
        key = str(self.cwd.resolve())
        data[key] = {"always": sorted(self.always)}
        p.write_text(json.dumps(data, indent=2))

    def remember(self, signature: str) -> None:
        self.always.add(signature)
        self.save()


@dataclass
class PermissionGate:
    mode: Mode = "edit"
    store: PermissionStore | None = None
    auto_yes: bool = False  # for tests + non-interactive runs
    prompt_fn = None  # injected for tests

    def needs_prompt(self, tool_name: str) -> bool:
        if self.auto_yes:
            return False
        if self.mode == "auto":
            return False
        if self.mode == "plan":
            return tool_name not in READ_ONLY
        # edit
        return tool_name in WRITE or tool_name in SHELL

    def signature(self, tool_name: str, args: dict) -> str:
        if tool_name == "shell_run":
            return f"shell_run:{args.get('cmd', '').split()[0] if args.get('cmd') else ''}"
        return tool_name

    def check(self, tool_name: str, args: dict, *, is_mutating: bool = False) -> tuple[bool, str]:
        """Return (allowed, reason).

        Structural mode-tier denial fires FIRST (skips prompt entirely).
        Within-mode prompts still gate mutating tools per D-07.
        """
        allowed, why = mode_allows(self.mode, tool_name, is_mutating)
        if not allowed:
            return False, why
        if not self.needs_prompt(tool_name):
            return True, "auto"
        if self.store is not None:
            sig = self.signature(tool_name, args)
            if sig in self.store.always:
                return True, "remembered"
        return self._prompt(tool_name, args)

    def _prompt(self, tool_name: str, args: dict) -> tuple[bool, str]:
        if not sys.stdin.isatty():
            return False, "non-interactive denial"
        prompt = self.prompt_fn or _interactive_prompt
        choice = prompt(tool_name, args)
        if choice == "a":
            return True, "allowed once"
        if choice == "A":
            if self.store is not None:
                self.store.remember(self.signature(tool_name, args))
            return True, "allowed always"
        return False, "denied"


def _interactive_prompt(tool_name: str, args: dict) -> str:
    argstr = ", ".join(f"{k}={_short(v)}" for k, v in args.items())
    sys.stderr.write(f"\n  ⚠  {tool_name}({argstr})\n")
    sys.stderr.write("     [a] allow once  [A] allow always  [d] deny: ")
    sys.stderr.flush()
    line = sys.stdin.readline().strip()
    if not line:
        return "d"
    return line[0]


def _short(v: object, limit: int = 60) -> str:
    s = str(v)
    return s[: limit - 1] + "…" if len(s) > limit else s
