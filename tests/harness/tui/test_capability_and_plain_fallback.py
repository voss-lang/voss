"""M9-01 capability + --plain + auto-fallback + min-size guard tests."""
from __future__ import annotations

import importlib
import sys

import pytest

from voss.harness.tui.capability import (
    TUIDecision,
    min_size_guard,
    tui_available,
    tui_should_activate,
)


def test_tui_available_with_textual() -> None:
    assert tui_available() is True


def test_plain_flag_returns_false() -> None:
    d = tui_should_activate(
        argv=["--plain"],
        env={},
        stdout_isatty=True,
        json_mode=False,
        size=(120, 40),
    )
    assert d == TUIDecision(activate=False, reason="--plain flag")


def test_voss_plain_env_returns_false() -> None:
    d = tui_should_activate(
        argv=[],
        env={"VOSS_PLAIN": "1"},
        stdout_isatty=True,
        json_mode=False,
        size=(120, 40),
    )
    assert d == TUIDecision(activate=False, reason="VOSS_PLAIN env")


def test_non_tty_returns_false() -> None:
    d = tui_should_activate(
        argv=[],
        env={},
        stdout_isatty=False,
        json_mode=False,
        size=(120, 40),
    )
    assert d == TUIDecision(activate=False, reason="non-TTY stdout")


def test_json_mode_returns_false() -> None:
    d = tui_should_activate(
        argv=[],
        env={},
        stdout_isatty=True,
        json_mode=True,
        size=(120, 40),
    )
    assert d == TUIDecision(activate=False, reason="--json mode")


@pytest.mark.parametrize("size", [(79, 24), (80, 23), (50, 10)])
def test_too_small_returns_false(size: tuple[int, int]) -> None:
    d = tui_should_activate(
        argv=[],
        env={},
        stdout_isatty=True,
        json_mode=False,
        size=size,
    )
    assert d == TUIDecision(activate=False, reason="terminal below 80x24")


def test_happy_path_activates() -> None:
    d = tui_should_activate(
        argv=[],
        env={},
        stdout_isatty=True,
        json_mode=False,
        size=(80, 24),
    )
    assert d == TUIDecision(activate=True, reason="ok")


def test_min_size_guard_locked_string() -> None:
    assert min_size_guard((79, 24)) == (
        "voss: terminal must be at least 80×24 "
        "(current: 79×24). Resize or use --plain."
    )


def test_capability_import_does_not_eager_import_textual(monkeypatch: pytest.MonkeyPatch) -> None:
    """`from voss.harness.tui import capability` must NOT pull in textual at import time."""
    for mod_name in list(sys.modules):
        if mod_name == "textual" or mod_name.startswith("textual."):
            monkeypatch.delitem(sys.modules, mod_name, raising=False)
    for mod_name in list(sys.modules):
        if mod_name == "voss.harness.tui.capability":
            monkeypatch.delitem(sys.modules, mod_name, raising=False)

    monkeypatch.setattr("voss.harness.tui.capability._AVAILABLE", None, raising=False)

    cap = importlib.import_module("voss.harness.tui.capability")
    assert hasattr(cap, "tui_should_activate")
    assert "textual" not in sys.modules, (
        "importing capability.py must not eagerly import textual"
    )
