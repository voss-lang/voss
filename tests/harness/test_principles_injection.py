"""V2-02: principles injection — overflow event + capped distinct block."""
from __future__ import annotations

from pathlib import Path

from voss.harness.agent import (
    PRINCIPLES_BUDGET_TOKENS,
    _compose_principles_block,
    _compose_system_blocks,
)
from voss.harness.principles import DEFAULT_PRINCIPLES, resolve_principles


class _StubRenderer:
    def __init__(self) -> None:
        self.overflow_calls: list[dict] = []
        self.warnings: list[str] = []

    def show_principles_overflow(self, *, principles_tokens: int, budget: int = 1000) -> None:
        self.overflow_calls.append({"tokens": principles_tokens, "budget": budget})

    def show_warning(self, msg: str) -> None:
        self.warnings.append(msg)


# ---- Task 1: overflow event shape -----------------------------------------


def test_overflow_event_shape() -> None:
    r = _StubRenderer()
    r.show_principles_overflow(principles_tokens=1234, budget=PRINCIPLES_BUDGET_TOKENS)
    assert r.overflow_calls == [{"tokens": 1234, "budget": 1000}]


def test_all_renderers_have_method() -> None:
    from voss.harness.render import (
        CompactRenderer,
        JsonRenderer,
        PlainRenderer,
        TtyRenderer,
    )

    for cls in (TtyRenderer, CompactRenderer, PlainRenderer, JsonRenderer):
        assert hasattr(cls, "show_principles_overflow")


# ---- Task 2: compose + inject ---------------------------------------------


def test_block_has_heading_and_defaults(tmp_path: Path) -> None:
    cfg = resolve_principles(tmp_path)  # no file → six defaults
    body = _compose_principles_block(cfg, model="m")
    assert body.startswith("## Principles")
    for _, text in DEFAULT_PRINCIPLES:
        assert text in body


def test_overflow_truncates_and_emits(tmp_path: Path) -> None:
    cfg = resolve_principles(tmp_path)
    r = _StubRenderer()
    # token_count_fn always over budget → forces overflow + full truncation
    body = _compose_principles_block(
        cfg, model="m", token_count_fn=lambda t, *, model: 9999, renderer=r
    )
    assert len(r.overflow_calls) == 1
    assert r.overflow_calls[0]["tokens"] == 9999
    assert "truncated due to budget" in body


def test_under_budget_keeps_full_body(tmp_path: Path) -> None:
    cfg = resolve_principles(tmp_path)
    r = _StubRenderer()
    body = _compose_principles_block(
        cfg, model="m", token_count_fn=lambda t, *, model: 10, renderer=r
    )
    assert r.overflow_calls == []
    assert "truncated" not in body


def test_principles_is_distinct_block() -> None:
    blocks = _compose_system_blocks(
        voss_md_block="# VOSS.md\nx",
        cognition_text="# Project cognition\ny",
        principles_text="## Principles\n\n- be good",
        project_index_text="",
        prior_context_text="",
        loop_system="loop",
    )
    texts = [b["text"] for b in blocks]
    # a standalone block, not merged into cognition or VOSS.md
    assert "## Principles\n\n- be good" in texts
    cognition_block = next(t for t in texts if t.startswith("# Project cognition"))
    assert "## Principles" not in cognition_block


def test_empty_principles_no_block() -> None:
    blocks = _compose_system_blocks(
        voss_md_block="# VOSS.md\nx",
        cognition_text="# Project cognition\ny",
        principles_text="",
        prior_context_text="",
        loop_system="loop",
    )
    texts = [b["text"] for b in blocks]
    assert not any(t.startswith("## Principles") for t in texts)
