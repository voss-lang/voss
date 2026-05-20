"""Gate-predicate registry for the board state machine (O3-03).

Implements OBRD-04 (typed gate predicates), OBRD-05 (artifact-only confidence),
OBRD-06 (risk-tier thresholds from _DEFAULT_RISK_THRESHOLDS single source).

SPEC L114: 7 stable predicate names = ("conf","tests","eval","scope","budget","retry","timeout").
SPEC L115: confidence (conf) only checked on transitions with an artifact
           (InProgress→InReview, InReview→Done).
SPEC L116: risk thresholds sourced from _DEFAULT_RISK_THRESHOLDS (machine.py) — IMPORTED, not redefined.

Predicate ordering: cheap (budget/scope/retry/timeout) → expensive (conf/tests/eval).

Two predicates share name="scope" (scope_ok and scope_clean). This is intentional per
OQ scope-clean-naming — SPEC's 7-name enumeration is the contract; dry_run_gate
deduplicates duplicate clause names via order-preserving append-if-absent.

Reviewer cardinality: conf_meets_p calls reviewer.review(card) AT MOST ONCE per move
attempt; the result is cached on GateContext.verdict for the duration of a single
evaluation pass. Cross-attempt caching is forbidden (artifact may change).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Protocol

from voss.harness.team import TeamCeiling, TeamRoleScope
from .verdict import Reviewer, ReviewerVerdict

if TYPE_CHECKING:
    from .machine import Card, Column, RiskTier


# SPEC L114 — 7 stable predicate names. Tests pin this tuple.
_PREDICATE_NAMES: tuple[str, ...] = (
    "conf", "tests", "eval", "scope", "budget", "retry", "timeout",
)


class Predicate(Protocol):
    name: str
    def evaluate(self, ctx: GateContext) -> bool: ...


@dataclass
class GateContext:
    """Per-move-attempt evaluation context. NOT frozen — verdict slot is
    mutable so conf_meets_p can cache the reviewer result."""
    card: Card
    node_envelope: dict
    team_ceiling: TeamCeiling
    team_p_overrides: dict
    retry_ceiling: int
    reserve: int
    now: float
    reviewer: Optional[Reviewer] = None
    verdict: Optional[ReviewerVerdict] = None


# ---------------------------------------------------------------------------
# 8 predicate classes (7 stable names; scope_ok + scope_clean share "scope")
# ---------------------------------------------------------------------------

class scope_ok:
    """Card scope is contained within team ceiling scope."""
    name = "scope"
    def evaluate(self, ctx: GateContext) -> bool:
        if ctx.card.scope is None or ctx.team_ceiling.scope is None:
            return True
        return ctx.card.scope.is_contained_in(ctx.team_ceiling.scope)


class budget_ok:
    """Card's node envelope has remaining budget (minus reserve)."""
    name = "budget"
    def evaluate(self, ctx: GateContext) -> bool:
        env = ctx.node_envelope
        return env["spent"] < env["limit"] - ctx.reserve


class conf_meets_p:
    """Reviewer confidence meets risk-tier threshold.

    Calls reviewer.review(card) AT MOST ONCE per GateContext (cached on
    ctx.verdict). Threshold sourced from team_p_overrides falling back
    to _DEFAULT_RISK_THRESHOLDS.
    """
    name = "conf"
    def evaluate(self, ctx: GateContext) -> bool:
        from .machine import _DEFAULT_RISK_THRESHOLDS  # lazy to break circular import
        if ctx.reviewer is None:
            return False
        if ctx.verdict is None:
            ctx.verdict = ctx.reviewer.review(ctx.card)
        threshold = ctx.team_p_overrides.get(
            ctx.card.risk_tier,
            _DEFAULT_RISK_THRESHOLDS[ctx.card.risk_tier],
        )
        return ctx.verdict.conf >= threshold


class tests_pass:
    """Artifact carries tests_passed == True."""
    name = "tests"
    def evaluate(self, ctx: GateContext) -> bool:
        return bool(getattr(ctx.card.artifact, "tests_passed", False))


class eval_meets_threshold:
    """Artifact eval_score meets card.eval_threshold (AI domain)."""
    name = "eval"
    def evaluate(self, ctx: GateContext) -> bool:
        score = getattr(ctx.card.artifact, "eval_score", 0.0)
        return float(score) >= ctx.card.eval_threshold


class scope_clean:
    """Scope contained AND no scope_violations on artifact."""
    name = "scope"  # intentional dedup with scope_ok
    def evaluate(self, ctx: GateContext) -> bool:
        if ctx.card.scope is not None and ctx.team_ceiling.scope is not None:
            if not ctx.card.scope.is_contained_in(ctx.team_ceiling.scope):
                return False
        return not bool(getattr(ctx.card.artifact, "scope_violations", ()))


class retry_under_ceiling:
    """Card retry count has not exceeded the ceiling."""
    name = "retry"
    def evaluate(self, ctx: GateContext) -> bool:
        return ctx.card.retry_count <= ctx.retry_ceiling


class not_timed_out:
    """Card deadline has not elapsed."""
    name = "timeout"
    def evaluate(self, ctx: GateContext) -> bool:
        return ctx.now < ctx.card.deadline


# ---------------------------------------------------------------------------
# Gates registry
# ---------------------------------------------------------------------------

# Pre-built predicate tuples for the two Done variants.
_CODE_DONE_PREDICATES = (scope_clean(), conf_meets_p(), tests_pass())
_AI_DONE_PREDICATES = (scope_clean(), conf_meets_p(), eval_meets_threshold())


@dataclass(frozen=True, slots=True)
class Gates:
    """Frozen gate registry mapping transitions to predicate tuples."""
    transitions: dict  # dict[tuple[Column,Column], tuple[Predicate,...]]

    @staticmethod
    def confidence_required(transition: tuple[str, str]) -> bool:
        """True only for artifact transitions (SPEC L115)."""
        return transition in {("InProgress", "InReview"), ("InReview", "Done")}

    @classmethod
    def build_default(cls) -> Gates:
        """Build the default 4-transition gate registry.

        Predicate ordering: cheap → expensive. conf_meets_p only on
        artifact transitions (SPEC L115). Default Done path = code;
        Board.move swaps to AI predicates by artifact introspection.
        """
        return cls(transitions={
            ("Backlog", "Planned"): (scope_ok(),),
            ("Planned", "InProgress"): (budget_ok(), scope_ok()),
            ("InProgress", "InReview"): (budget_ok(), scope_ok(), conf_meets_p()),
            ("InReview", "Done"): _CODE_DONE_PREDICATES,
        })
