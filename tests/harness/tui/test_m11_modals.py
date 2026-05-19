from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from voss.harness.tui.widgets.budget_meter import BudgetMeter
from voss.harness.tui.widgets.confidence_bar import ConfidenceBar


class _ModalHost(App):
    def __init__(self, screen) -> None:
        super().__init__()
        self._screen = screen

    def compose(self) -> ComposeResult:
        return []

    def on_mount(self) -> None:
        self.push_screen(self._screen)


def _modal_class(module: str, name: str):
    mod = pytest.importorskip(module, reason=f"{name} implementation not present")
    return getattr(mod, name)


def _rendered_text(app: App) -> str:
    chunks: list[str] = []
    for node in app.query("*"):
        renderable = getattr(node, "renderable", None)
        if renderable is not None:
            chunks.append(str(renderable))
    return "\n".join(chunks)


def _probable_modal():
    cls = _modal_class(
        "voss.harness.tui.widgets.probable_modal",
        "ProbableInspectModal",
    )
    return cls(
        "Decision 0\nchoose parser\nconfidence: 0.82\nfeeds into tests",
        confidence=0.82,
    )


def _budget_trace_modal():
    cls = _modal_class(
        "voss.harness.tui.widgets.budget_trace_modal",
        "BudgetTraceModal",
    )
    return cls(
        "Frame 0\nprompt tokens: 10\ncompletion tokens: 5\n"
        "cumulative tokens: 68",
        used=68,
        total=100,
    )


def _voss_py_diff_modal():
    cls = _modal_class(
        "voss.harness.tui.widgets.voss_py_diff_modal",
        "VossPyDiffModal",
    )
    return cls(
        "Voss source\nfn greet(name: string) -> string\n\n"
        "Generated Python\ndef greet(name):\n    return name"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("factory", "expected"),
    [
        (_probable_modal, "probable"),
        (_budget_trace_modal, "budget"),
        (_voss_py_diff_modal, "python"),
    ],
)
async def test_modal_headings_render(factory, expected: str) -> None:
    app = _ModalHost(factory())
    async with app.run_test():
        assert expected in _rendered_text(app).lower()


@pytest.mark.asyncio
async def test_probable_inspect_modal_includes_confidence_value_and_bar() -> None:
    app = _ModalHost(_probable_modal())
    async with app.run_test():
        rendered = _rendered_text(app)
        assert "0.82" in rendered
        assert len(list(app.query(ConfidenceBar))) == 1


@pytest.mark.asyncio
async def test_budget_trace_modal_includes_cumulative_tokens_and_meter() -> None:
    app = _ModalHost(_budget_trace_modal())
    async with app.run_test():
        rendered = _rendered_text(app).lower()
        assert "cumulative tokens" in rendered
        assert "68" in rendered
        assert len(list(app.query(BudgetMeter))) == 1


@pytest.mark.asyncio
async def test_voss_py_diff_modal_has_no_accept_reject_apply_footer() -> None:
    app = _ModalHost(_voss_py_diff_modal())
    async with app.run_test():
        rendered = _rendered_text(app).lower()
        for forbidden in ("accept", "reject", "apply"):
            assert forbidden not in rendered
