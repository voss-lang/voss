"""Reviewer-A: verification-authoring reviewer (O4-03, ORVW-01..03, 08, 09).

A derives the judging bar from the original human idea — NOT from EM's AC/DoD.
For code cards, A authors tests and runs them via shell_run (exit code = verdict).
For AI cards, A authors a rubric and delegates to judge_run (Verdict.confidence
becomes ReviewerVerdict.conf).

EpisodicMemory is created fresh per review() call (Pitfall 2: no cross-card
bleed). uuid4 generates a fresh session_id per call.

Reviewer.review Protocol is sync. ReviewerA bridges the async run_turn + judge_run
calls using a thread-pool executor when an event loop is already running.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import re
import uuid
from pathlib import Path
from typing import Callable, Optional

from voss_runtime import EpisodicMemory
from voss_runtime.providers.base import ModelProvider

from voss.template_render import render_package_template
from voss.eval.judge import Verdict, judge_run
from voss.harness.agent import TurnResult, run_turn
from voss.harness.permissions import PermissionGate
from voss.harness.prompt_override import default_runtime_vars, load_prompt
from voss.harness.render import Renderer
from voss.harness.subagents import SubagentSpec
from voss.harness.team import filter_toolset_for_role, gate_for_role
from voss.harness.tools import make_toolset

from .verdict import ReviewerVerdict


REVIEWER_A_ROLE_PROMPT = render_package_template(
    "voss",
    "templates/prompts/reviewer_a_role.txt.jinja",
    {},
)


def _reviewer_a_task(original_idea: str, artifact_text: str, domain: str) -> str:
    """Format the task prompt for Reviewer-A's run_turn call."""
    return (
        f"## Original Idea\n{original_idea}\n\n"
        f"## Artifact\n{artifact_text}\n\n"
        f"## Domain\n{domain}\n\n"
        f"Derive verification from the original idea and produce the "
        f"{'test file (run it via shell_run)' if domain == 'code' else 'rubric'}."
    )


def _verdict_from_test_exit(exit_code: int, test_file: str, output: str) -> ReviewerVerdict:
    """Code-card path: shell_run exit code → ReviewerVerdict."""
    return ReviewerVerdict(
        conf=1.0 if exit_code == 0 else 0.0,
        source="A",
        tier="strong",
        verdict="pass" if exit_code == 0 else "fail",
        notes=output[:2000],
        evidence_refs=(test_file,),
    )


def _verdict_from_judge(v: Verdict, rubric_id: str) -> ReviewerVerdict:
    """AI-card path: judge.Verdict → ReviewerVerdict."""
    return ReviewerVerdict(
        conf=v.confidence,
        source="A",
        tier="strong",
        verdict=v.verdict,
        notes=v.rationale,
        evidence_refs=(rubric_id,),
    )


_EXIT_CODE_RE = re.compile(r"\[exit\s+(\d+)\]")


def _extract_exit_code(tool_results: list[str]) -> tuple[int, str]:
    """Parse the exit code from shell_run output in tool_results."""
    for result in reversed(tool_results):
        m = _EXIT_CODE_RE.search(result)
        if m:
            return int(m.group(1)), result
    # No exit code found — treat as failure.
    return 1, "no shell_run exit code found in tool_results"


class ReviewerA:
    """Verification-authoring reviewer implementing the Reviewer Protocol.

    Uses run_turn with fresh EpisodicMemory per card to derive what "done"
    means from the original idea. For code cards: test file + shell_run.
    For AI cards: rubric + judge_run.
    """

    def __init__(
        self,
        *,
        provider: ModelProvider,
        model: str,
        cwd: Path,
        renderer: Renderer,
        base_gate: PermissionGate,
        run_turn_fn: Optional[Callable] = None,
        judge_run_fn: Optional[Callable] = None,
    ) -> None:
        self._provider = provider
        self._model = model
        self._cwd = cwd
        self._renderer = renderer
        self._base_gate = base_gate
        self._run_turn_fn = run_turn_fn or run_turn
        self._judge_run_fn = judge_run_fn or judge_run

        # SubagentSpec for permission gating. Prompt resolved at load time so
        # a project copy under .voss/prompts/ is honored (V16-04, R5).
        prompt_root = Path(cwd).resolve()
        self._spec = SubagentSpec(
            id="reviewer_a",
            description="Derives verification bar from original idea",
            role_prompt=load_prompt(
                "reviewer_a_role",
                resource="templates/prompts/reviewer_a_role.txt.jinja",
                cwd=prompt_root,
                runtime_vars=default_runtime_vars("reviewer-a", prompt_root),
            ),
            tools=frozenset({"fs", "shell"}),
        )
        # Validate gate compatibility at construction time.
        self._gate = gate_for_role(self._spec, base_gate)

    def review(self, card: object) -> ReviewerVerdict:
        """Produce a ReviewerVerdict by authoring and running verification.

        Sync (matches Reviewer Protocol). Bridges async internals via
        thread-pool executor when event loop is running.
        """
        coro = self._review_async(card)
        try:
            asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        except RuntimeError:
            return asyncio.run(coro)

    async def _review_async(self, card: object) -> ReviewerVerdict:
        """Async implementation of review()."""
        # Fresh memory + session per call (ORVW-08: no cross-card bleed).
        memory = EpisodicMemory(capacity=20)
        session_id = str(uuid.uuid4())

        original_idea = getattr(card, "original_idea", "") or ""
        artifact_text = getattr(card, "artifact_text", "") or str(getattr(card, "artifact", "") or "")
        domain = getattr(card, "domain", "code") or "code"

        task_prompt = _reviewer_a_task(original_idea, artifact_text, domain)

        tools = filter_toolset_for_role(
            self._spec,
            make_toolset(self._cwd, renderer=self._renderer),
        )

        try:
            result: TurnResult = await self._run_turn_fn(
                task_prompt,
                tools=tools,
                cwd=self._cwd,
                renderer=self._renderer,
                model=self._model,
                provider=self._provider,
                history=memory,
                permissions=self._gate,
                session_id=session_id,
            )
        except Exception as exc:
            return ReviewerVerdict(
                conf=0.0, source="A", tier="strong", verdict="fail",
                notes=f"run_turn failed: {exc}"[:2000],
                evidence_refs=(),
            )

        if domain == "code":
            exit_code, output = _extract_exit_code(result.tool_results)
            return _verdict_from_test_exit(exit_code, "a_test.py", output)

        # AI-card path: result.final is A's authored rubric.
        rubric = result.final or ""
        try:
            verdict_obj, _ = await self._judge_run_fn(
                provider=self._provider,
                model=self._model,
                task_prompt=original_idea,
                final=artifact_text,
                file_diff=getattr(card, "file_diff", "") or "",
                rubric=rubric,
            )
        except Exception:
            verdict_obj = None

        if verdict_obj is None:
            return ReviewerVerdict(
                conf=0.0, source="A", tier="strong", verdict="fail",
                notes="judge_run returned None (skipped)",
                evidence_refs=(),
            )
        return _verdict_from_judge(verdict_obj, f"rubric:{session_id[:8]}")
