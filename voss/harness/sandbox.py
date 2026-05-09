from __future__ import annotations

import os
import shlex
from pathlib import Path

DEFAULT_SHELL_ALLOWLIST = {
    "ls", "cat", "head", "tail", "grep", "rg", "find", "wc",
    "git", "pytest", "python", "python3", "voss", "npm", "node",
    "echo", "pwd", "which",
}

DENY_TOKENS = ("rm -rf", "sudo", "curl http", "nc ", " > /", "shutdown", "reboot", "mkfs")


class SandboxError(RuntimeError):
    pass


def jail_path(cwd: Path, target: str | os.PathLike) -> Path:
    """Resolve target relative to cwd; reject paths that escape cwd."""
    cwd_real = cwd.resolve()
    p = Path(target)
    if not p.is_absolute():
        p = cwd_real / p
    p = p.resolve()
    try:
        p.relative_to(cwd_real)
    except ValueError as e:
        raise SandboxError(f"path escapes cwd: {p}") from e
    return p


def shell_allowed(cmd: str, allowlist: set[str] = DEFAULT_SHELL_ALLOWLIST) -> tuple[bool, str]:
    """Return (allowed, reason)."""
    lowered = cmd.lower()
    for bad in DENY_TOKENS:
        if bad in lowered:
            return False, f"denied token: {bad!r}"
    try:
        parts = shlex.split(cmd)
    except ValueError as e:
        return False, f"unparseable: {e}"
    if not parts:
        return False, "empty command"
    binary = Path(parts[0]).name
    if binary not in allowlist:
        return False, f"binary not in allowlist: {binary}"
    return True, "ok"
