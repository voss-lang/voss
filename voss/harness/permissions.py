"""Permission gate for tool calls.

Modes:
- plan : reads auto, every write/shell prompts
- edit : reads + scoped writes auto, shell/net prompt   (default)
- auto : all allowlisted auto, destructive patterns prompt

Decisions persist per-cwd in ~/.config/voss/permissions.json.

CTRL-08: every `fs_write` / `fs_edit` call renders a unified diff preview to
stderr BEFORE the call is allowed to proceed. This is scope-independent — it
fires whether or not an EditScope is attached, so `voss do --mode=edit` and
`voss chat --mode=edit` writes get the same preview as `voss edit`.

Project-level layering (.voss/permissions.yml, added in M2)
-----------------------------------------------------------
When .voss/permissions.yml is loaded into a PermissionsConfig and attached
to the gate, its rules layer on top of the session mode:

  - deny (project) ALWAYS wins, even in mode=auto.
  - allow (project) is recorded but does NOT expand session-mode
    permissions (a project allow does not auto-approve a tool that the
    session mode would have prompted for).

This mirrors M1's "least-privilege wins" stance.
"""
from __future__ import annotations

import difflib
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Literal, Optional

from .cognition_schemas import PermissionsConfig

if TYPE_CHECKING:
    from .edit_scope import EditScope

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
    prompt_fn: Optional[Callable] = None  # injected for tests
    edit_scope: Optional["EditScope"] = None  # set by voss edit; None for do/chat
    scope_prompt_fn: Optional[Callable] = None  # injected for tests
    project_policy: Optional[PermissionsConfig] = None  # .voss/permissions.yml

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
        allowed, why = self._check_impl(tool_name, args, is_mutating=is_mutating)
        from . import telemetry

        if telemetry.enabled():
            telemetry.emit(
                "permission.result",
                "info",
                data={
                    "tool": tool_name,
                    "allowed": allowed,
                    "why": why,
                    "mode": self.mode,
                    "args": telemetry.redact_tool_args(dict(args)),
                },
            )
        return allowed, why

    def _check_impl(self, tool_name: str, args: dict, *, is_mutating: bool = False) -> tuple[bool, str]:
        """Return (allowed, reason).

        Order of operations:
          0. Project-policy deny (`.voss/permissions.yml`) — deny wins over
             allow and over session-mode auto. Project allow does NOT expand
             mode (recorded but not short-circuiting).
          1. Mode-tier structural denial (skips everything else).
          2. CTRL-08 diff preview for any fs_write/fs_edit (scope-independent).
          3. Scope check (only if edit_scope set) — expand-prompt fires AFTER
             the diff render, so user sees the diff before deciding.
          4. Within-mode interactive prompt or auto-yes path.
        """
        if self.project_policy is not None:
            if tool_name in self.project_policy.tool_policy.deny:
                return False, "denied by .voss/permissions.yml"

        allowed, why = mode_allows(self.mode, tool_name, is_mutating)
        if not allowed:
            return False, why

        # CTRL-08: diff preview for ALL mutating writes, regardless of scope.
        if tool_name in WRITE:
            self._render_diff_preview(tool_name, args)

        # Scope check for writes — only if an edit_scope is attached.
        if self.edit_scope is not None and tool_name in WRITE:
            target = args.get("path", "")
            if target and not self.edit_scope.allows_write(target):
                ok, expand_kind = self._prompt_expand(target)
                if not ok:
                    return False, "out-of-scope denied"
                if expand_kind == "always":
                    self.edit_scope.expand(target)
                return True, f"out-of-scope: {expand_kind}"

        if not self.needs_prompt(tool_name):
            return True, "auto"
        if self.store is not None:
            sig = self.signature(tool_name, args)
            if sig in self.store.always:
                return True, "remembered"
        return self._prompt(tool_name, args)

    def _render_diff_preview(self, tool_name: str, args: dict) -> None:
        """Render a unified diff to stderr before applying a write (CTRL-08).

        Scope-independent: runs for every fs_write / fs_edit. Resolves the
        target against `edit_scope.cwd` if set, else the process cwd.
        Failure (file unreadable, encoding error) is swallowed silently —
        diff preview is best-effort and must not block the gate.
        """
        try:
            path = args.get("path", "")
            if not path:
                return
            base_dir = self.edit_scope.cwd if self.edit_scope is not None else Path(".")
            base = Path(base_dir).resolve()
            p = (base / path).resolve()
            current = p.read_text() if p.exists() else ""
            if tool_name == "fs_write":
                new = args.get("content", "")
            elif tool_name == "fs_edit":
                old = args.get("old", "")
                replacement = args.get("new", "")
                new = current.replace(old, replacement, 1) if old in current else current
            else:
                return
            diff = "".join(
                difflib.unified_diff(
                    current.splitlines(keepends=True),
                    new.splitlines(keepends=True),
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                    n=3,
                )
            )
            if diff:
                sys.stderr.write("\n  diff preview:\n")
                for line in diff.splitlines():
                    sys.stderr.write(f"    {line}\n")
                sys.stderr.flush()
        except (OSError, UnicodeDecodeError):
            return

    def _prompt_expand(self, target: str) -> tuple[bool, str]:
        """Prompt: expand scope to include <target>? [y/once/always/n]."""
        if self.scope_prompt_fn is None and not sys.stdin.isatty():
            return False, "non-interactive denial"
        prompt = self.scope_prompt_fn or _interactive_expand_prompt
        choice = prompt(target)
        if choice in ("y", "once"):
            return True, "once"
        if choice == "always":
            return True, "always"
        return False, "denied"

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


def _interactive_expand_prompt(target: str) -> str:
    sys.stderr.write(f"\n  ⚠  expand scope to include {target}?\n")
    sys.stderr.write("     [y] yes once  [a] always (this session)  [n] no: ")
    sys.stderr.flush()
    line = sys.stdin.readline().strip().lower()
    if not line:
        return "n"
    if line.startswith("a"):
        return "always"
    if line.startswith("y"):
        return "once"
    return "n"


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
