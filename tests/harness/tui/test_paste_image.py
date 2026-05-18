"""T8 INPUT-05 paste-image acceptance tests."""
from __future__ import annotations

import pytest


pytestmark = pytest.mark.xfail(
    reason="T8 Wave 3 - paste-image support not yet implemented",
    strict=False,
)


def test_probe_clipboard_image_returns_none_when_unimplemented(monkeypatch) -> None:
    from voss.harness.tui.widgets.input_bar import _probe_clipboard_image

    def raise_not_implemented():
        raise NotImplementedError

    monkeypatch.setattr(
        "voss.harness.tui.widgets.input_bar._read_clipboard_image",
        raise_not_implemented,
    )
    assert _probe_clipboard_image() is None


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("gpt-4o", True),
        ("claude-3-5-sonnet", True),
        ("text-only-model", False),
    ],
)
def test_model_supports_vision_name_gate(model: str, expected: bool) -> None:
    from voss.harness.tui.widgets.input_bar import _model_supports_vision

    assert _model_supports_vision(model) is expected


def test_snap10_no_vision_notice_anchor(snap_compare) -> None:
    from voss.harness.tui.app import VossTUIApp

    assert snap_compare(VossTUIApp(model="text-only-model"), terminal_size=(80, 24))
