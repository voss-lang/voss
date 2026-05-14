"""Cognition prompt token budget overflow.

`_compose_cognition_prompt` enforces a 6000-token budget. When the
architecture body + constraints exceed it, the constraints section is
truncated and the renderer's `show_cognition_overflow` hook fires.

This test pins both behaviors with a tiny synthetic bundle and a custom
token counter that forces overflow.
"""
from __future__ import annotations

from types import SimpleNamespace

from voss.harness.agent import _compose_cognition_prompt


class _SpyRenderer:
    def __init__(self) -> None:
        self.overflow_calls: list[dict] = []
        self.warnings: list[str] = []

    def show_cognition_overflow(self, *, architecture_tokens: int, budget: int) -> None:
        self.overflow_calls.append(
            {"architecture_tokens": architecture_tokens, "budget": budget}
        )

    def show_warning(self, msg: str) -> None:
        self.warnings.append(msg)


def _bundle(arch: str = "x" * 200) -> SimpleNamespace:
    from voss.harness.cognition_schemas import ConstraintRule, ConstraintsConfig

    constraints = ConstraintsConfig(
        rules=[
            ConstraintRule(forbid=["eval", "exec"]),
            ConstraintRule(custom="prefer Path over os.path"),
        ]
    )
    return SimpleNamespace(
        initialized=True,
        architecture_md=arch,
        constraints=constraints,
    )


def test_no_overflow_returns_full_body() -> None:
    """Counter under budget → full body, no renderer call."""
    spy = _SpyRenderer()
    out = _compose_cognition_prompt(
        _bundle(),
        model="stub",
        token_count_fn=lambda text, model: 100,
        renderer=spy,
    )
    assert "## Constraints" in out or "## Architecture" in out
    assert spy.overflow_calls == []


def test_overflow_truncates_constraints_and_calls_renderer() -> None:
    """Counter over budget → constraints dropped, renderer notified."""
    spy = _SpyRenderer()
    out = _compose_cognition_prompt(
        _bundle(),
        model="stub",
        token_count_fn=lambda text, model: 999_999,
        renderer=spy,
    )
    assert "(constraints truncated due to budget)" in out, out
    assert len(spy.overflow_calls) == 1
    assert spy.overflow_calls[0]["architecture_tokens"] == 999_999
    assert spy.overflow_calls[0]["budget"] == 6000


def test_counter_failure_emits_warning_returns_full_body() -> None:
    """Token counter raising must not crash the turn — warning + full body."""
    spy = _SpyRenderer()

    def boom(text: str, *, model: str) -> int:
        raise RuntimeError("counter broken")

    out = _compose_cognition_prompt(
        _bundle(),
        model="stub",
        token_count_fn=boom,
        renderer=spy,
    )
    assert "(constraints truncated" not in out
    assert spy.warnings, "expected warning when counter raises"


def test_uninitialized_bundle_returns_empty() -> None:
    bundle = SimpleNamespace(initialized=False)
    out = _compose_cognition_prompt(
        bundle, model="stub", token_count_fn=lambda *a, **k: 1
    )
    assert out == ""
