from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from voss_runtime import ToolDescriptor, tool

from .sandbox import jail_path, shell_allowed, split_command, SandboxError


@dataclass(frozen=True)
class ToolEntry:
    """Registry entry pairing a ToolDescriptor with structural classification.

    `is_mutating` drives mode-tier denial in PermissionGate (see D-06):
    classification is data at registration, not name-pattern matching.
    """

    descriptor: ToolDescriptor
    is_mutating: bool

    @property
    def name(self) -> str:
        return self.descriptor.name

    @property
    def description(self) -> str:
        return self.descriptor.description

    @property
    def parameters(self) -> dict:
        return self.descriptor.parameters

    def invoke(self, **kwargs: Any) -> Any:
        return self.descriptor.invoke(**kwargs)

    def invoke_dict(self, args: dict) -> Any:
        return self.descriptor.invoke(**args)


def make_toolset(cwd: Path) -> dict[str, ToolEntry]:
    """Build the harness toolset bound to a project cwd.

    Returns a dict of tool name -> ToolEntry. Each entry carries an
    explicit `is_mutating` boolean used by PermissionGate.
    """

    @tool(name="fs_read", description="Read a UTF-8 text file from the project. Path must be inside cwd.")
    async def fs_read(path: str) -> str:
        p = jail_path(cwd, path)
        if not p.exists():
            return f"<error: not found: {path}>"
        if p.is_dir():
            return f"<error: is a directory: {path}>"
        try:
            return p.read_text()
        except UnicodeDecodeError:
            return f"<error: binary file: {path}>"

    @tool(name="fs_glob", description="List files matching a glob pattern, relative to cwd.")
    async def fs_glob(pattern: str) -> str:
        results = sorted(str(p.relative_to(cwd)) for p in cwd.glob(pattern) if p.is_file())
        return "\n".join(results) if results else "<no matches>"

    @tool(name="shell_run", description="Run an allowlisted command (no shell). Output truncated to 4KB.")
    async def shell_run(cmd: str) -> str:
        # Allowlist + metacharacter check first. shell_allowed rejects pipelines,
        # redirection, command substitution, chaining — anything that requires a
        # shell to interpret. The actual invocation uses `create_subprocess_exec`
        # so the binary is executed directly, never via `/bin/sh -c`.
        ok, reason = shell_allowed(cmd)
        if not ok:
            return f"<denied: {reason}>"
        try:
            argv = split_command(cmd)
        except SandboxError as e:
            return f"<denied: {e}>"
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            try:
                out, _ = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            except asyncio.TimeoutError:
                proc.kill()
                return "<timeout: 30s>"
        except (OSError, SandboxError) as e:
            return f"<error: {e}>"
        text = out.decode("utf-8", errors="replace")
        if len(text) > 4096:
            text = text[:4096] + f"\n<truncated, total {len(out)} bytes>"
        return f"[exit {proc.returncode}]\n{text}"

    @tool(name="fs_write", description="Write text to a file inside cwd. Creates parent dirs. Overwrites existing.")
    async def fs_write(path: str, content: str) -> str:
        p = jail_path(cwd, path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"wrote {len(content)} bytes to {path}"

    @tool(
        name="fs_edit",
        description=(
            "Replace exact `old` text with `new` in a file. `old` must appear "
            "exactly once. Returns line count delta."
        ),
    )
    async def fs_edit(path: str, old: str, new: str) -> str:
        p = jail_path(cwd, path)
        if not p.exists():
            return f"<error: not found: {path}>"
        text = p.read_text()
        count = text.count(old)
        if count == 0:
            return f"<error: `old` not found in {path}>"
        if count > 1:
            return f"<error: `old` matches {count} times, must be unique>"
        new_text = text.replace(old, new, 1)
        p.write_text(new_text)
        delta = new_text.count("\n") - text.count("\n")
        sign = "+" if delta >= 0 else ""
        return f"edited {path} ({sign}{delta} lines)"

    @tool(name="fs_grep", description="Recursively search for a regex pattern. Returns matching lines with file:line.")
    async def fs_grep(pattern: str, glob: str = "**/*") -> str:
        import re

        try:
            rx = re.compile(pattern)
        except re.error as e:
            return f"<error: bad regex: {e}>"
        hits: list[str] = []
        for p in cwd.glob(glob):
            if not p.is_file():
                continue
            try:
                rel = p.relative_to(cwd)
            except ValueError:
                continue
            try:
                for i, line in enumerate(p.read_text().splitlines(), 1):
                    if rx.search(line):
                        hits.append(f"{rel}:{i}: {line}")
                        if len(hits) >= 200:
                            break
            except (UnicodeDecodeError, OSError):
                continue
            if len(hits) >= 200:
                break
        return "\n".join(hits) if hits else "<no matches>"

    @tool(name="git_status", description="Run `git status --porcelain`.")
    async def git_status() -> str:
        return await _shell_capture(cwd, ["git", "status", "--porcelain"])

    @tool(name="git_diff", description="Run `git diff` (unstaged) or `git diff --cached` (staged) on optional path.")
    async def git_diff(staged: bool = False, path: str = "") -> str:
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--cached")
        if path:
            cmd.append(path)
        return await _shell_capture(cwd, cmd)

    @tool(
        name="voss_check",
        description="Run `voss check` on a .voss file or directory. Returns analyzer diagnostics.",
    )
    async def voss_check(path: str = ".") -> str:
        p = jail_path(cwd, path)
        return await _shell_capture(cwd, ["voss", "check", str(p)])

    @tool(
        name="record_run",
        description=(
            "(privileged) Close the current turn with semantic fields. "
            "Dispatched by the harness; never include in plan steps."
        ),
    )
    async def record_run(
        goal: str = "",
        avoided: list | None = None,
        assumptions: list | None = None,
        decisions: list | None = None,
        risks: list | None = None,
        follow_ups: list | None = None,
    ) -> str:
        return "ok"

    return {
        "fs_read": ToolEntry(descriptor=fs_read, is_mutating=False),
        "fs_glob": ToolEntry(descriptor=fs_glob, is_mutating=False),
        "fs_grep": ToolEntry(descriptor=fs_grep, is_mutating=False),
        "fs_write": ToolEntry(descriptor=fs_write, is_mutating=True),
        "fs_edit": ToolEntry(descriptor=fs_edit, is_mutating=True),
        "shell_run": ToolEntry(descriptor=shell_run, is_mutating=True),
        "git_status": ToolEntry(descriptor=git_status, is_mutating=False),
        "git_diff": ToolEntry(descriptor=git_diff, is_mutating=False),
        "voss_check": ToolEntry(descriptor=voss_check, is_mutating=False),
        "record_run": ToolEntry(descriptor=record_run, is_mutating=True),
    }


async def _shell_capture(cwd: Path, argv: list[str], timeout: float = 30.0) -> str:
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except OSError as e:
        return f"<error: {e}>"
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return f"<timeout: {timeout}s>"
    text = out.decode("utf-8", errors="replace")
    if len(text) > 4096:
        text = text[:4096] + f"\n<truncated, total {len(out)} bytes>"
    return f"[exit {proc.returncode}]\n{text}"
