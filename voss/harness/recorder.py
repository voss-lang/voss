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

import json
import sys

from .session import EXIT_REASONS, BatchRecord, IterationRecord, RunRecord


def _emit_budget_osc(
    *,
    tokens_used: int,
    token_limit: int | None,
    cost_usd: float,
    iteration: int,
    model: str,
) -> None:
    """Write an OSC 1337 voss-budget= sequence to stdout (D-02, D-04).

    The Rust PTY reader (reader.rs extract_voss_osc) strips this sequence
    before bytes reach xterm, so the terminal never renders it.
    """
    payload = json.dumps(
        {
            "tokens_used": tokens_used,
            "token_limit": token_limit,
            "cost_usd": cost_usd,
            "iteration": iteration,
            "model": model,
        },
        separators=(",", ":"),
    )
    sys.stdout.write(f"\x1b]1337;voss-budget={payload}\x07")
    sys.stdout.flush()


INSPECT_TOOLS = {"fs_read", "fs_glob", "fs_grep"}
CHANGE_TOOLS = {"fs_write", "fs_edit"}
VALIDATE_TOOLS = {"shell_run", "voss_check"}
SKILL_EVENTS = {"skill_install", "skill_remove", "skill_update"}
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
    # M15-05: skill install/run/deny audit events
    skill_events: list[dict] = field(default_factory=list)
    scope_denials: list[dict] = field(default_factory=list)
    # T1-01: per-iteration sub-records appended via begin_iteration /
    # end_iteration; forwarded to RunRecord.iterations on finalize.
    _iterations: list[IterationRecord] = field(default_factory=list)

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

    def observe_skill_event(
        self,
        action: str,
        skill_id: str,
        source: str,
        *,
        ok: bool,
        error: str = "",
    ) -> None:
        """Record a skill install/remove/update/run event."""
        self.skill_events.append({
            "action": action,
            "skill_id": skill_id,
            "source": source,
            "ok": ok,
            "error": error[:FAILURE_TRUNC],
        })

    def observe_scope_denial(
        self, skill_id: str, tool: str, reason: str
    ) -> None:
        """Record a scope-limited gate denial for a third-party skill."""
        self.scope_denials.append({
            "skill_id": skill_id,
            "tool": tool,
            "reason": reason,
        })

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

    def begin_iteration(self) -> IterationRecord:
        """Open a new iteration sub-record (T1-01).

        Appends an IterationRecord with index = current count, started_at set
        to UTC ISO now, and other fields at defaults. Returns the record so
        callers can attach fields incrementally before end_iteration.
        """
        record = IterationRecord(
            index=len(self._iterations),
            started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        self._iterations.append(record)
        return record

    def end_iteration(
        self,
        *,
        plan: Any,
        tool_results: list[dict],
        cost_usd: float,
        prompt_tokens: int,
        completion_tokens: int,
        cache_creation_input_tokens: int = 0,
        cache_read_input_tokens: int = 0,
        exit_reason: Optional[str] = None,
    ) -> None:
        """Close the most recently opened iteration (T1-01).

        Writes the supplied fields onto the most recent open iteration (the
        one with empty ended_at). Validates exit_reason against EXIT_REASONS
        when not None — raises ValueError on mismatch.
        """
        if exit_reason is not None and exit_reason not in EXIT_REASONS:
            raise ValueError(
                f"invalid exit_reason {exit_reason!r}; "
                f"must be one of {sorted(EXIT_REASONS)}"
            )
        target: Optional[IterationRecord] = None
        for rec in reversed(self._iterations):
            if not rec.ended_at:
                target = rec
                break
        if target is None:
            raise RuntimeError("end_iteration called without an open iteration")
        target.plan = plan.model_dump() if hasattr(plan, "model_dump") else plan
        target.tool_results = list(tool_results)
        target.cost_usd = cost_usd
        target.prompt_tokens = prompt_tokens
        target.completion_tokens = completion_tokens
        target.cache_creation_input_tokens = cache_creation_input_tokens
        target.cache_read_input_tokens = cache_read_input_tokens
        target.exit_reason = exit_reason
        target.ended_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def begin_batch(
        self, *, batch_index: int, step_indices: list[int]
    ) -> BatchRecord:
        """Append a new BatchRecord onto the current iteration (T2-01).

        Must be called inside an iteration scope. The caller supplies
        batch_index; the recorder is a passive append site. Returns the
        appended BatchRecord so callers may hold a reference, though the
        normal flow patches via end_batch.
        """
        if not self._iterations:
            raise RuntimeError("begin_batch called outside an iteration scope")
        br = BatchRecord(
            batch_index=batch_index,
            step_indices=list(step_indices),  # defensive copy
            parallel_count=len(step_indices),
        )
        self._iterations[-1].batches.append(br)
        return br

    def end_batch(
        self, *, wall_clock_ms: int, ok_count: int, err_count: int
    ) -> None:
        """Patch the trailing BatchRecord on the current iteration (T2-01).

        Pure mutation of the trailing batch; does NOT append a new record.
        Caller (scheduler in T2-03) computes wall-clock + ok/err totals
        after asyncio.gather completes.
        """
        if not self._iterations or not self._iterations[-1].batches:
            raise RuntimeError("end_batch called without a matching begin_batch")
        br = self._iterations[-1].batches[-1]
        br.wall_clock_ms = wall_clock_ms
        br.ok_count = ok_count
        br.err_count = err_count

    def finalize(
        self,
        cwd: Path,
        cost_usd: float,
        *,
        exit_reason: Optional[str] = None,
    ) -> RunRecord:
        self.cost_usd = cost_usd
        self.diff_summary = _git_diff_stat(cwd)
        total_prompt = sum(it.prompt_tokens for it in self._iterations)
        total_completion = sum(it.completion_tokens for it in self._iterations)
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
            iterations=list(self._iterations),
            iteration_count=len(self._iterations),
            exit_reason=exit_reason,
            iteration_total_prompt_tokens=total_prompt,
            iteration_total_completion_tokens=total_completion,
            skill_events=list(self.skill_events),
            scope_denials=list(self.scope_denials),
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
