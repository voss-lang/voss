from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Any

from voss_runtime import tool

from .sandbox import jail_path, shell_allowed, SandboxError


def make_toolset(cwd: Path) -> dict[str, Any]:
    """Build the harness toolset bound to a project cwd.

    Returns a dict of tool name -> async callable.
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

    @tool(name="shell_run", description="Run a shell command from the allowlist. Output truncated to 4KB.")
    async def shell_run(cmd: str) -> str:
        ok, reason = shell_allowed(cmd)
        if not ok:
            return f"<denied: {reason}>"
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
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

    return {
        "fs_read": fs_read,
        "fs_glob": fs_glob,
        "shell_run": shell_run,
    }
