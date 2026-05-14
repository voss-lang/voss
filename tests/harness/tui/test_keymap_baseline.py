"""M9-03 KEYMAP baseline coverage tests."""
from __future__ import annotations

import pytest

from voss.harness.tui.keymap import KEYMAP, Binding


def test_keymap_size_at_least_14() -> None:
    assert len(KEYMAP) >= 14


@pytest.mark.parametrize(
    "key,context_substr",
    [
        ("tab", "global"),
        ("shift+tab", "global"),
        ("enter", "input"),
        ("shift+enter", "input"),
        ("slash", "input"),
        ("escape", "modal"),
        ("question_mark", "global"),
        ("j", "main"),
        ("k", "main"),
        ("ctrl+d", "main"),
        ("ctrl+u", "main"),
        ("g", "main"),
        ("G", "main"),
        ("ctrl+c", "global"),
        ("ctrl+l", "global"),
    ],
)
def test_keymap_includes_ui_spec_row(key: str, context_substr: str) -> None:
    hit = [b for b in KEYMAP if b.key == key and context_substr in b.context]
    assert hit, f"missing binding for key={key!r}"


def test_every_binding_has_description_and_action() -> None:
    for b in KEYMAP:
        assert isinstance(b, Binding)
        assert b.description, f"missing description: {b}"
        assert b.action, f"missing action: {b}"
