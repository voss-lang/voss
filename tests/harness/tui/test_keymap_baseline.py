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
        ("ctrl+o", "main"),
    ],
)
def test_keymap_includes_ui_spec_row(key: str, context_substr: str) -> None:
    hit = [b for b in KEYMAP if b.key == key and context_substr in b.context]
    assert hit, f"missing binding for key={key!r}"


# --- M13 additive keymap-resolution guards (Wave 0) ---


def test_ctrl_o_resolves_to_toggle_subagent_detail() -> None:
    """M13 MAG-02: ctrl+o must resolve to the toggle_subagent_detail action.

    RED from Wave 0 (the binding lands in W2B). Not xfail-marked — this
    asserts a static module table and must be hard-RED that W2B turns
    green.
    """
    hit = [b for b in KEYMAP if b.key == "ctrl+o"]
    assert hit, "no ctrl+o binding in KEYMAP"
    assert any(b.action == "toggle_subagent_detail" for b in hit), (
        "ctrl+o does not resolve to toggle_subagent_detail"
    )
    assert any(b.context == "main" for b in hit), (
        "ctrl+o is not on the M9 'main' declarative registry tier"
    )
    # OQ-A3 dual contract: a "main" row resolves iff (a) the KEYMAP row
    # exists AND (b) a matching action_<name> handler lives on VossTUIApp
    # (the action_fork_turn precedent). Assert the App-handler half too.
    from voss.harness.tui.app import VossTUIApp

    assert callable(
        getattr(VossTUIApp, "action_toggle_subagent_detail", None)
    ), "VossTUIApp lacks a callable action_toggle_subagent_detail handler"


def test_ctrl_c_still_interrupt() -> None:
    """M13 back-compat half of the keymap guard — GREEN from Wave 0.

    ctrl+c must remain bound to `interrupt` (keymap.py:37). M13 must not
    repurpose ctrl+c when adding the ctrl+o reveal binding.
    """
    hit = [b for b in KEYMAP if b.key == "ctrl+c"]
    assert hit, "no ctrl+c binding in KEYMAP"
    assert any(b.action == "interrupt" for b in hit), (
        "ctrl+c no longer resolves to interrupt — back-compat breach"
    )


def test_every_binding_has_description_and_action() -> None:
    for b in KEYMAP:
        assert isinstance(b, Binding)
        assert b.description, f"missing description: {b}"
        assert b.action, f"missing action: {b}"
