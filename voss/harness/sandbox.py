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

# Shell metacharacters that change command-flow semantics. Even though Voss
# invokes the allowlisted binary directly via `create_subprocess_exec` (not
# `_shell`), we still reject these tokens at allowlist time so a misuse of
# the API by a future caller can't accidentally re-enable shell parsing.
# These cover: command chaining (`;`, `&&`, `||`, `&`), pipelines (`|`),
# redirection (`>`, `<`, `>>`, `<<`), command substitution (`$(`, backtick),
# and process substitution (`<(`, `>(`).
SHELL_METACHARS = (";", "|", "&&", "||", "&", "$(", "`", ">", "<", ">>", "<<", "<(", ">(")


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
    """Return (allowed, reason).

    Hardening contract:
    1. Lowercase deny-token scan covers historically-dangerous patterns.
    2. Reject any shell metacharacter — pipelines/chaining/redirection/substitution
       are unambiguous shell features with no legitimate use under a strict
       binary allowlist. The caller (`shell_run`) executes via
       `create_subprocess_exec` (no shell), so a metacharacter in the cmd
       would either be passed as a literal argument (surprising) or indicate
       intent to invoke `_shell` (forbidden). Reject either way.
    3. Allowlist check is case-insensitive on the binary name so legitimate
       commands work on case-insensitive filesystems (macOS APFS).
    """
    lowered = cmd.lower()
    for bad in DENY_TOKENS:
        if bad in lowered:
            return False, f"denied token: {bad!r}"
    for meta in SHELL_METACHARS:
        if meta in cmd:
            return False, f"shell metacharacter not allowed: {meta!r}"
    try:
        parts = shlex.split(cmd)
    except ValueError as e:
        return False, f"unparseable: {e}"
    if not parts:
        return False, "empty command"
    binary = Path(parts[0]).name.lower()
    if binary not in allowlist:
        return False, f"binary not in allowlist: {binary}"
    return True, "ok"


def split_command(cmd: str) -> list[str]:
    """Split an allowlist-approved command into argv for `create_subprocess_exec`.

    Caller MUST have already validated `cmd` via `shell_allowed` and gotten
    `(True, "ok")`. Returns the argv list ready for execvp-style invocation.
    Empty input raises SandboxError — `shell_allowed` already rejects this
    case, so reaching it here is a programmer error.
    """
    try:
        parts = shlex.split(cmd)
    except ValueError as e:
        raise SandboxError(f"unparseable command: {e}") from e
    if not parts:
        raise SandboxError("empty command")
    return parts


def write_cache(project_root: Path, relpath: str | os.PathLike, text: str) -> Path:
    """Write inside project_root/.voss-cache using the sandbox path jail."""
    cache_root = jail_path(project_root, ".voss-cache")
    cache_root.mkdir(parents=True, exist_ok=True)
    target = jail_path(cache_root, relpath)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(text)
    tmp.replace(target)
    return target
