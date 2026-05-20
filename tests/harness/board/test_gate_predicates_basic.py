"""O3-03 Task 1: Predicate names, Gates registry shape, confidence_required."""
from __future__ import annotations

from voss.harness.board.gates import (
    Gates,
    _PREDICATE_NAMES,
    budget_ok,
    conf_meets_p,
    eval_meets_threshold,
    not_timed_out,
    retry_under_ceiling,
    scope_clean,
    scope_ok,
    tests_pass,
)


class TestPredicateNames:
    def test_exactly_7_stable_names(self):
        assert _PREDICATE_NAMES == (
            "conf", "tests", "eval", "scope", "budget", "retry", "timeout",
        )

    def test_each_predicate_name_in_stable_set(self):
        all_preds = [
            scope_ok(), scope_clean(), budget_ok(), conf_meets_p(),
            tests_pass(), eval_meets_threshold(), retry_under_ceiling(),
            not_timed_out(),
        ]
        names = {p.name for p in all_preds}
        assert names == set(_PREDICATE_NAMES)

    def test_scope_ok_and_scope_clean_share_name(self):
        assert scope_ok().name == "scope"
        assert scope_clean().name == "scope"


class TestGatesRegistry:
    def test_build_default_has_4_transitions(self):
        g = Gates.build_default()
        assert len(g.transitions) == 4
        assert ("Backlog", "Planned") in g.transitions
        assert ("Planned", "InProgress") in g.transitions
        assert ("InProgress", "InReview") in g.transitions
        assert ("InReview", "Done") in g.transitions

    def test_predicate_ordering_cheap_before_expensive(self):
        g = Gates.build_default()
        # InProgress→InReview: budget, scope before conf
        names = [p.name for p in g.transitions[("InProgress", "InReview")]]
        assert names.index("budget") < names.index("conf")

    def test_confidence_required(self):
        assert Gates.confidence_required(("InProgress", "InReview")) is True
        assert Gates.confidence_required(("InReview", "Done")) is True
        assert Gates.confidence_required(("Backlog", "Planned")) is False
        assert Gates.confidence_required(("Planned", "InProgress")) is False
