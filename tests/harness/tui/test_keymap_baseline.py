"""M9-03 KEYMAP baseline coverage tests.

R6 rebaseline (tui-redesign-spec §7.1, deliberate per the stale-sentinel
policy): the "transcript" context tier joins the keymap for nav mode —
esc/i (back to input), j/k + arrows (block focus), enter (toggle card),
y (copy block), g g / G (top / bottom + re-engage follow). Transcript rows
are handled by TranscriptView.on_key while it holds focus; they are NOT
App.BINDINGS (the App comprehension still filters to global/input/modal,
so the modal-dismiss escape binding is unshadowed).
"""
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
        # NB: `/` is intentionally NOT a keybinding — the slash palette opens
        # via text-change detection in InputBar so `/` stays typeable. See
        # test_input_bar_slash_palette_sync.
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
        # R6 transcript nav mode (spec §7.1)
        ("escape", "transcript"),
        ("i", "transcript"),
        ("j", "transcript"),
        ("k", "transcript"),
        ("down", "transcript"),
        ("up", "transcript"),
        ("enter", "transcript"),
        ("y", "transcript"),
        ("g", "transcript"),
        ("G", "transcript"),
    ],
)
def test_keymap_includes_ui_spec_row(key: str, context_substr: str) -> None:
    hit = [b for b in KEYMAP if b.key == key and context_substr in b.context]
    assert hit, f"missing binding for key={key!r}"


# --- M13 additive keymap-resolution guards (Wave 0) ---


def test_ctrl_o_resolves_to_toggle_detail() -> None:
    """R4 spec §7.2: ctrl+o is the global expand/collapse-all action
    (generalizes the M13 MAG-02 sub-agent detail reveal — same key,
    superset behavior across ToolCard bodies and AgentTree children)."""
    hit = [b for b in KEYMAP if b.key == "ctrl+o"]
    assert hit, "no ctrl+o binding in KEYMAP"
    assert any(b.action == "toggle_detail" for b in hit), (
        "ctrl+o does not resolve to toggle_detail"
    )
    assert any(b.context == "main" for b in hit), (
        "ctrl+o is not on the M9 'main' declarative registry tier"
    )
    # OQ-A3 dual contract: a "main" row resolves iff (a) the KEYMAP row
    # exists AND (b) a matching action_<name> handler lives on VossTUIApp
    # (the action_fork_turn precedent). Assert the App-handler half too.
    from voss.harness.tui.app import VossTUIApp

    assert callable(
        getattr(VossTUIApp, "action_toggle_detail", None)
    ), "VossTUIApp lacks a callable action_toggle_detail handler"


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
