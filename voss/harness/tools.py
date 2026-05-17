from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from voss_runtime import ToolDescriptor, tool

from .sandbox import jail_path, shell_allowed, split_command, SandboxError
from .tui.widgets.diff_modal import DiffDecision, Hunk

if TYPE_CHECKING:
    from voss.harness.net import NetSession


@dataclass(frozen=True)
class ToolEntry:
    """Registry entry pairing a ToolDescriptor with structural classification.

    `is_mutating` drives mode-tier denial in PermissionGate (see D-06):
    classification is data at registration, not name-pattern matching.

    `is_network` drives the allow_net gate in PermissionGate (T3-02). It is
    independent of `is_mutating`: a network tool may be read-only
    (web_fetch) yet still must clear the allow_net check.
    """

    descriptor: ToolDescriptor
    is_mutating: bool
    is_network: bool = False

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


def _read_one_for_bundle(cwd: Path, path: str) -> str:
    """Per-slot reader for fs_read_many. Never raises; returns content OR error envelope."""
    try:
        p = jail_path(cwd, path)
    except SandboxError:
        return f"<error: path outside cwd: {path}>"
    if not p.exists():
        return f"<error: not found: {path}>"
    if p.is_dir():
        return f"<error: is a directory: {path}>"
    try:
        text = p.read_text()
    except UnicodeDecodeError:
        return f"<error: binary file: {path}>"
    if len(text) > 30720:  # 30KB cap (T2-CONTEXT.md D-13)
        text = text[:30720] + f"\n<truncated, total {len(text)} bytes>"
    return text


def make_toolset(
    cwd: Path,
    *,
    renderer=None,
    net: "NetSession | None" = None,
) -> dict[str, ToolEntry]:
    """Build the harness toolset bound to a project cwd.

    Returns a dict of tool name -> ToolEntry. Each entry carries an
    explicit `is_mutating` boolean used by PermissionGate.

    T2-04: When `renderer` is provided AND exposes `show_diff_modal`,
    `fs_edit_many` routes through the M9-05 DiffModal for per-hunk
    approval. When `renderer is None` (test-friendly path) or the
    renderer lacks `show_diff_modal` (e.g., JSON / plain renderers),
    the modal step is skipped and the tool writes after validation.
    The LLM agent never controls this kwarg — it is set by the
    in-process harness construction site (cli.py, eval/runner.py,
    subagents.py) at production startup.
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

    @tool(
        name="fs_read_many",
        description=(
            "Read N files as one bundle. Returns sections separated by "
            "`=== {path} ===`. Per-path errors are inline (other paths "
            "still readable). Each file capped at 30KB."
        ),
    )
    async def fs_read_many(paths: list[str]) -> str:
        if not paths:
            return "<no paths requested>"
        sections: list[str] = []
        for path in paths:
            body = _read_one_for_bundle(cwd, path)
            sections.append(f"=== {path} ===\n{body}\n")
        return "\n".join(sections)

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

    @tool(
        name="fs_edit_many",
        description=(
            "Atomically apply N edits to one file. Each `edits` entry is "
            "{old, new}; each `old` must match uniquely in the working "
            "buffer (left-to-right). Routes through the diff modal with "
            "one Hunk per edit. Rejecting OR skipping any hunk cancels "
            "the whole batch — file unchanged on disk."
        ),
    )
    async def fs_edit_many(path: str, edits: list[dict]) -> str:
        # T2-04 / PAR-03: validate-then-write-once single-file multi-edit.
        if not edits:
            return "<error: empty edits list>"
        p = jail_path(cwd, path)
        if not p.exists():
            return f"<error: not found: {path}>"
        if p.is_dir():
            return f"<error: is a directory: {path}>"
        try:
            snapshot = p.read_text()
        except UnicodeDecodeError:
            return f"<error: binary file: {path}>"

        # Phase 1: validate each edit against the CURRENT working buffer
        # (not the original snapshot — Pitfall 5: left-to-right propagation).
        buf = snapshot
        hunks: list[Hunk] = []
        for i, e in enumerate(edits):
            old = e.get("old", "")
            new = e.get("new", "")
            if not old:
                return f"<error: batch rejected at index {i}: empty `old`>"
            count = buf.count(old)
            if count == 0:
                return f"<error: batch rejected at index {i}: `old` not found>"
            if count > 1:
                return (
                    f"<error: batch rejected at index {i}: "
                    f"`old` matches {count} times>"
                )
            idx = buf.find(old)
            line_start = buf.count("\n", 0, idx) + 1
            old_lines = [f"- {ln}" for ln in (old.splitlines() or [""])]
            new_lines = [f"+ {ln}" for ln in (new.splitlines() or [""])]
            hunks.append(
                Hunk(file=path, start=line_start, lines=old_lines + new_lines)
            )
            buf = buf[:idx] + new + buf[idx + len(old):]

        # Phase 2: per-hunk modal approval (skipped when renderer lacks
        # show_diff_modal — test or non-TUI renderers).
        modal = getattr(renderer, "show_diff_modal", None) if renderer is not None else None
        if modal is not None:
            decisions = modal(hunks, timeout_s=300.0)
            if not decisions:
                return "<denied: modal cancelled or timed out>"
            for i, d in enumerate(decisions):
                # STRICT skip semantics: skip is treated as reject (resolves
                # RESEARCH.md Open Question 1 per the recommendation).
                if d.decision in ("reject", "skip"):
                    return f"<denied: hunk {i} rejected>"

        # Phase 3: atomic single write (file untouched until here).
        p.write_text(buf)
        delta = buf.count("\n") - snapshot.count("\n")
        sign = "+" if delta >= 0 else ""
        return f"edited {path} ({sign}{delta} lines, {len(edits)} hunks)"

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
        "fs_read_many": ToolEntry(descriptor=fs_read_many, is_mutating=False),
        "fs_glob": ToolEntry(descriptor=fs_glob, is_mutating=False),
        "fs_grep": ToolEntry(descriptor=fs_grep, is_mutating=False),
        "fs_write": ToolEntry(descriptor=fs_write, is_mutating=True),
        "fs_edit": ToolEntry(descriptor=fs_edit, is_mutating=True),
        "fs_edit_many": ToolEntry(descriptor=fs_edit_many, is_mutating=True),
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
