from __future__ import annotations

import logging
from pathlib import Path

from voss.harness import config, judgments
from voss.harness.decision_review import assess, build_packet, candidate_from_diff, checks_from_artifact, run_sync
from voss.harness.session_tree import write_judgments_sidecar
from voss_runtime.judgments import JudgmentLedger

logger = logging.getLogger(__name__)


def _evidence(card, name: str) -> str:
    return getattr(card, name, None) or getattr(card.artifact, name, None) or ""


class ShadowReviewer:
    def __init__(self, inner, *, cwd: Path, manager) -> None:
        self._inner = inner
        self._cwd = cwd
        self._manager = manager

    def review(self, card, **kwargs):
        verdict = self._inner.review(card, **kwargs)
        if kwargs.get("tier") == "strong":
            try:
                self._shadow(card)
            except Exception as exc:
                logger.warning("requirement assessment skipped: %s", type(exc).__name__)
        return verdict

    def _shadow(self, card) -> None:
        if judgments.review_mode(self._cwd) != "shadow":
            return
        diff = _evidence(card, "file_diff")
        packet = build_packet(
            _evidence(card, "acceptance_criteria"),
            diff=diff,
            code=_evidence(card, "repo_context"),
            checks=checks_from_artifact(card.artifact),
            candidate=candidate_from_diff(self._cwd, diff),
            verification_note=_evidence(card, "a_verification_summary"),
        )
        cfg = config.get_judgments_config()
        ledger = JudgmentLedger(cfg["max_calls_per_turn"], cfg["max_cost_usd"])
        run_sync(assess(packet, mode="shadow", ledger=ledger))
        write_judgments_sidecar(self._cwd, self._manager._root.id, ledger)
