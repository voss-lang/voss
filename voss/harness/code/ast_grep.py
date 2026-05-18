"""
ast-grep CLI wrapper (M10-03 Task 1).

Uses subprocess + --json=stream for structural search.
Strictly read-only. Soft dependency.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any

from .models import SearchHit, CodeLocation

AST_GREP_TIMEOUT = 8.0
MAX_OUTPUT_BYTES = 256 * 1024


async def search(
    pattern: str,
    root: Path,
    *,
    max_results: int = 50,
    timeout: float = AST_GREP_TIMEOUT,
) -> list[SearchHit] | dict[str, Any]:
    """
    Run ast-grep on the given root for the pattern.
    Returns list of SearchHit or a structured error dict.
    """
    binary = shutil.which("ast-grep")
    if not binary:
        return {
            "result": "unavailable",
            "tool": "ast-grep",
            "fallback": "regex",
            "hint": "Install ast-grep (brew install ast-grep or cargo install ast-grep)",
        }

    # Hard-coded read-only flags per plan
    argv = [
        binary,
        "run",
        "--pattern", pattern,
        "--json=stream",
        "--color", "never",
        "--threads", "0",
        str(root),
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as e:
        return {"result": "error", "message": str(e)}

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        try:
            await proc.wait()
        except Exception:
            pass
        return {"result": "timeout", "timeout_s": timeout}

    text = stdout.decode("utf-8", errors="replace")
    if len(text) > MAX_OUTPUT_BYTES:
        text = text[:MAX_OUTPUT_BYTES]

    hits: list[SearchHit] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if isinstance(data, dict):
                hit = _parse_match(data)
                if hit:
                    hits.append(hit)
                    if len(hits) >= max_results:
                        break
        except json.JSONDecodeError:
            continue  # skip malformed line

    if proc.returncode not in (0, None):
        # ast-grep returns non-zero for no matches sometimes; treat as empty
        if not hits:
            return hits

    return hits


def _parse_match(data: dict) -> SearchHit | None:
    """Convert one ast-grep JSON match into SearchHit."""
    try:
        file = data.get("file", "")
        text = data.get("text", "")
        range_ = data.get("range", {})
        start = range_.get("start", {})
        end = range_.get("end", {})

        loc = CodeLocation(
            file=file,
            line=start.get("line", 0) + 1,  # 1-based
            column=start.get("column", 0),
            end_line=end.get("line", 0) + 1,
            end_column=end.get("column", 0),
        )
        return SearchHit(
            location=loc,
            language=data.get("language", "unknown"),
            matched_text=text[:200],
            source="ast-grep",
        )
    except Exception:
        return None
