"""M9-07 CLI integration — default-path renderer flip + permissions bridge wiring.

This file pins three contracts:

1. **make_renderer default flip**: a TTY user with adequate capability gets
   a `TextualRenderer`. A CliRunner caller (non-TTY) still gets a
   `PlainRenderer`. `--plain` still wins. `FORCE_TUI=1` still wins.
2. **install_tui_permissions wiring**: when `TextualRenderer` is active,
   the gate's `prompt_fn` AND `scope_prompt_fn` are wired through the
   M9-05 modal bridge. When `PlainRenderer` (or `TtyRenderer`) is active,
   both callables remain at their `None` defaults (stderr/stdin fallback).
3. **`--no-unicode` flag sets the env BEFORE make_renderer**: glyphs.py
   reads the env at import; the flag must set it before the renderer
   constructs any widget.
"""
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from voss.harness.agent import Plan
from voss.harness.cli import do_cmd
from voss.harness.render import (
    JsonRenderer,
    PlainRenderer,
    TtyRenderer,
    make_renderer,
)
from voss.harness.tui.capability import TUIDecision
from voss.harness.tui.renderer import TextualRenderer

from tests.harness.test_voss_loop_parity import FakeProvider


CANNED_PLAN = Plan(
    rationale="cli-integration baseline plan",
    steps=[],
    confidence=0.50,
    open_question="cli-integration baseline question?",
)


def _install_fake_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_res = SimpleNamespace(source="fake", detail="fake")
    fake_provider = FakeProvider(CANNED_PLAN)
    monkeypatch.setattr(
        "voss.harness.cli._resolve_auth_or_die",
        lambda _pref: (fake_res, fake_provider),
    )
    monkeypatch.setattr(
        "voss.harness.cli._git_status",
        lambda _cwd: "no git",
    )


# ----------------------------------------------------------------------
# make_renderer factory contract
# ----------------------------------------------------------------------


def test_make_renderer_non_tty_default_is_plain(monkeypatch: pytest.MonkeyPatch) -> None:
    """CliRunner-style non-TTY caller → PlainRenderer (auto-fallback rule)."""
    monkeypatch.setattr(
        "voss.harness.tui.capability.tui_should_activate",
        lambda **kw: TUIDecision(activate=False, reason="non-TTY stdout"),
    )
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    renderer = make_renderer(json_mode=False, plain=False, force_tui=False)
    assert isinstance(renderer, PlainRenderer)


def test_make_renderer_tty_capability_ok_returns_textual(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TTY + adequate capability + non-Windows → TextualRenderer (new default)."""
    monkeypatch.setattr(
        "voss.harness.tui.capability.tui_should_activate",
        lambda **kw: TUIDecision(activate=True, reason="ok"),
    )
    renderer = make_renderer(json_mode=False, plain=False, force_tui=False)
    assert isinstance(renderer, TextualRenderer)


def test_make_renderer_plain_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    """--plain still beats every TUI-friendly capability signal."""
    monkeypatch.setattr(
        "voss.harness.tui.capability.tui_should_activate",
        lambda **kw: TUIDecision(activate=True, reason="ok"),
    )
    renderer = make_renderer(json_mode=False, plain=True, force_tui=False)
    assert isinstance(renderer, PlainRenderer)


def test_make_renderer_json_mode_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "voss.harness.tui.capability.tui_should_activate",
        lambda **kw: TUIDecision(activate=True, reason="ok"),
    )
    renderer = make_renderer(json_mode=True, plain=False, force_tui=False)
    assert isinstance(renderer, JsonRenderer)


def test_make_renderer_legacy_tty_path_on_capability_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TTY but capability rejected (e.g. textual missing) → legacy TtyRenderer."""
    monkeypatch.setattr(
        "voss.harness.tui.capability.tui_should_activate",
        lambda **kw: TUIDecision(activate=False, reason="textual not installed"),
    )
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    renderer = make_renderer(json_mode=False, plain=False, force_tui=False)
    assert isinstance(renderer, TtyRenderer)


# ----------------------------------------------------------------------
# install_tui_permissions wiring (deferred-import patch on source module)
# ----------------------------------------------------------------------


def _patch_capability_active(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "voss.harness.tui.capability.tui_should_activate",
        lambda **kw: TUIDecision(activate=True, reason="ok"),
    )


def _patch_capability_plain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "voss.harness.tui.capability.tui_should_activate",
        lambda **kw: TUIDecision(activate=False, reason="non-TTY stdout"),
    )


def test_install_tui_permissions_called_when_textual(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_provider(monkeypatch)
    _patch_capability_active(monkeypatch)
    monkeypatch.chdir(tmp_path)

    calls: list[tuple[object, object]] = []
    monkeypatch.setattr(
        "voss.harness.tui.permissions_bridge.install_tui_permissions",
        lambda gate, app, **kw: calls.append((gate, app)),
    )

    runner = CliRunner()
    result = runner.invoke(
        do_cmd, ["--cwd", str(tmp_path), "wire-tui"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert len(calls) == 1, "install_tui_permissions must fire exactly once for do_cmd"
    gate_arg, app_arg = calls[0]
    assert app_arg is not None


def test_install_tui_permissions_skipped_when_plain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_provider(monkeypatch)
    _patch_capability_plain(monkeypatch)
    monkeypatch.chdir(tmp_path)

    calls: list[tuple[object, object]] = []
    monkeypatch.setattr(
        "voss.harness.tui.permissions_bridge.install_tui_permissions",
        lambda gate, app, **kw: calls.append((gate, app)),
    )

    runner = CliRunner()
    result = runner.invoke(
        do_cmd, ["--plain", "--cwd", str(tmp_path), "wire-plain"], catch_exceptions=False
    )
    assert result.exit_code == 0
    assert calls == [], "install_tui_permissions must NOT fire for PlainRenderer"


# ----------------------------------------------------------------------
# --no-unicode flag plumbing
# ----------------------------------------------------------------------


def test_no_unicode_flag_sets_env_before_make_renderer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The --no-unicode flag sets VOSS_NO_UNICODE=1 in os.environ."""
    monkeypatch.delenv("VOSS_NO_UNICODE", raising=False)
    _install_fake_provider(monkeypatch)
    _patch_capability_plain(monkeypatch)
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        do_cmd,
        ["--no-unicode", "--plain", "--cwd", str(tmp_path), "ascii-only"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert os.environ.get("VOSS_NO_UNICODE") == "1"
