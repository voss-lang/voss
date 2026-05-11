"""Per-turn mechanical observation collaborator (COG-08 D-15).

Wraps run_turn's tool dispatch loop to capture inspected/changed/validation/
failures without changing the agent surface. Semantic fields (goal/decisions/
risks/follow_ups/assumptions/avoided) are populated by a separate privileged
`record_run` closing call dispatched in M2-03.
"""
from __future__ import annotations

import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .session import RunRecord


INSPECT_TOOLS = {"fs_read", "fs_glob", "fs_grep"}
CHANGE_TOOLS = {"fs_write", "fs_edit"}
VALIDATE_TOOLS = {"shell_run", "voss_check"}
FAILURE_TRUNC = 200
SUMMARY_TRUNC = 160


@dataclass
class RunRecorder:
    id: str
    started_at: str
    inspected: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    validation: list[dict] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)
    cost_usd: float = 0.0
    diff_summary: str = ""
    # semantic fields (populated by absorb() in M2-03)
    goal: str = ""
    plan: Optional[dict] = None
    avoided: list[dict] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    decisions: list[dict] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)

    @classmethod
    def start(cls) -> "RunRecorder":
        return cls(
            id=uuid.uuid4().hex[:12],
            started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

    def observe(self, tool_name: str, args: dict, result: Any, *, ok: bool) -> None:
        if not ok:
            self.failures.append(
                {"tool": tool_name, "error": str(result)[:FAILURE_TRUNC]}
            )
            return
        if tool_name in INSPECT_TOOLS:
            path = args.get("path") or args.get("pattern") or ""
            if path:
                self.inspected.append(path)
        elif tool_name in CHANGE_TOOLS:
            path = args.get("path", "")
            if path:
                self.changed.append(path)
        elif tool_name in VALIDATE_TOOLS:
            text = str(result) if result is not None else ""
            exit_code = _parse_exit(text)
            summary = text.splitlines()[0] if text else ""
            cmd = args.get("cmd") or f"{tool_name}({args})"
            self.validation.append(
                {
                    "cmd": cmd,
                    "exit": exit_code,
                    "summary": summary[:SUMMARY_TRUNC],
                }
            )

    def absorb(self, semantics: Any, plan: Any = None) -> None:
        """Copy semantic fields from a duck-typed semantics object.

        Tolerates SimpleNamespace stubs and pydantic BaseModel instances via
        getattr. `semantics is None` is a no-op (mechanical-only persistence).
        """
        if semantics is None:
            if plan is not None:
                self.plan = plan.model_dump() if hasattr(plan, "model_dump") else plan
            return
        self.goal = getattr(semantics, "goal", self.goal)
        self.avoided = getattr(semantics, "avoided", self.avoided)
        self.assumptions = getattr(semantics, "assumptions", self.assumptions)
        self.decisions = getattr(semantics, "decisions", self.decisions)
        self.risks = getattr(semantics, "risks", self.risks)
        self.follow_ups = getattr(semantics, "follow_ups", self.follow_ups)
        if plan is not None:
            self.plan = plan.model_dump() if hasattr(plan, "model_dump") else plan

    def finalize(self, cwd: Path, cost_usd: float) -> RunRecord:
        self.cost_usd = cost_usd
        self.diff_summary = _git_diff_stat(cwd)
        return RunRecord(
            id=self.id,
            started_at=self.started_at,
            ended_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            goal=self.goal,
            plan=self.plan,
            inspected=list(self.inspected),
            changed=list(self.changed),
            avoided=list(self.avoided),
            assumptions=list(self.assumptions),
            decisions=list(self.decisions),
            risks=list(self.risks),
            validation=list(self.validation),
            failures=list(self.failures),
            diff_summary=self.diff_summary,
            follow_ups=list(self.follow_ups),
            cost_usd=self.cost_usd,
        )


def _parse_exit(result: str) -> int:
    """Parse `[exit N]` prefix from shell_run result. Returns 0 on failure."""
    if not result.startswith("[exit "):
        return 0
    close = result.find("]")
    if close < 0:
        return 0
    try:
        return int(result[6:close])
    except ValueError:
        return 0


def write_decisions_md(cwd: Path, run, session_id: str) -> list[Path]:
    """Mirror each decision to .voss/decisions/YYYY-MM-DD-<slug>.md (D-08, COG-06)."""
    from .cognition import reserve_filename, slug

    if not run.decisions:
        return []
    decisions_dir = cwd / ".voss" / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for d in run.decisions:
        title = d.get("title") or "untitled"
        body = d.get("body", "")
        try:
            conf = float(d.get("confidence", 0.0))
        except (TypeError, ValueError):
            conf = 0.0
        path = reserve_filename(decisions_dir, slug(title))
        id_str = path.stem
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        content = (
            "---\n"
            f"id: {id_str}\n"
            "status: active\n"
            f"related_session: {session_id}\n"
            f"confidence: {conf:.2f}\n"
            f"created_at: {created_at}\n"
            "---\n\n"
            f"# {title}\n\n"
            f"{body}\n"
        )
        path.write_text(content)
        paths.append(path)
    return paths


def _git_diff_stat(cwd: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "diff", "--stat"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if out.returncode != 0:
        return ""
    return out.stdout[:4096]
