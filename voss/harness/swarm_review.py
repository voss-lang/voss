from __future__ import annotations

import asyncio
import logging
from pathlib import Path

PENDING: set[asyncio.Task] = set()
logger = logging.getLogger(__name__)


def schedule_candidate_review(
    repo_root: Path, swarm_id: str, task_id: str, goal: str, head: str, violations: list[str]
) -> None:
    try:
        from voss.harness import conventions, judgments

        if judgments.judgments_state(repo_root) != "enabled" or conventions._load_judgments_review(repo_root) != "shadow":
            return
        task = asyncio.get_running_loop().create_task(
            asyncio.to_thread(review_candidate, Path(repo_root), swarm_id, task_id, goal, head, bool(violations))
        )
        PENDING.add(task)
        task.add_done_callback(PENDING.discard)
    except Exception as exc:
        logger.warning("swarm candidate review not scheduled for task %s: %s", task_id, type(exc).__name__)


def review_candidate(repo_root: Path, swarm_id: str, task_id: str, goal: str, head: str, scope_failed: bool) -> None:
    try:
        from voss.harness import config, decision_review, judgments
        from voss_runtime.judgments import JudgmentLedger

        if judgments.review_mode(repo_root) != "shadow":
            return
        cfg = config.get_judgments_config()
        ledger = JudgmentLedger(cfg["max_calls_per_turn"], cfg["max_cost_usd"])
        try:
            asyncio.run(
                decision_review.assess_candidate(
                    cwd=repo_root,
                    criteria=goal,
                    head=head,
                    checks=(decision_review.CheckResult("scope", "failed" if scope_failed else "passed"),),
                    ledger=ledger,
                    mode="shadow",
                )
            )
        finally:
            decision_review.write_candidate_review(
                decision_review.candidate_review_path(repo_root, swarm_id, task_id), ledger
            )
    except Exception as exc:
        logger.warning("swarm candidate review failed for task %s: %s", task_id, type(exc).__name__)
