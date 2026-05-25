"""M9-07 UI-SPEC Acceptance Visual Check 5 — `--no-unicode` glyph fallback.

The glyphs module reads `VOSS_NO_UNICODE=1` at import time and replaces
its locked Unicode codepoints with ASCII fallbacks from
`NO_UNICODE_FALLBACK`. The `--no-unicode` CLI flag exists on every
interactive entry (do/chat/edit/resume) and sets that env var BEFORE
make_renderer fires.

The import-time check forces a SUBPROCESS approach: once the glyphs
module has been imported once in a parent process, flipping the env var
won't re-run the module body. Each test runs a fresh Python interpreter
with the desired env state.
"""
from __future__ import annotations

import subprocess
import sys

import pytest


# Mapping mirrored from voss/harness/tui/glyphs.py NO_UNICODE_FALLBACK.
_FALLBACK_PAIRS = [
    ("PROMPT", "▌", "|"),
    ("USER_INPUT", "❯", ">"),
    ("TOOL_CALL", "⏵", ">"),
    ("WARN", "⚠", "!"),
    ("BAR_FILL", "█", "#"),
    ("BAR_EMPTY", "░", "."),
    ("BUDGET_FILL", "▰", "="),
    ("BUDGET_EMPTY", "▱", "-"),
    ("NEST_LAST", "└─", "+-"),
    ("NEST_MID", "├─", "+-"),
    ("FORK", "⎇", "+"),
]


def _read_glyph(name: str, *, env_value: str | None) -> str:
    """Spawn a fresh Python; return repr(glyph) printed by the subprocess."""
    env = {"PATH": "/usr/bin:/bin", "PYTHONPATH": ":".join(sys.path)}
    if env_value is not None:
        env["VOSS_NO_UNICODE"] = env_value
    out = subprocess.run(
        [
            sys.executable,
            "-c",
            f"from voss.harness.tui import glyphs; "
            f"import sys; sys.stdout.write(glyphs.{name})",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
    )
    assert out.returncode == 0, (
        f"subprocess failed: rc={out.returncode}, stderr={out.stderr}"
    )
    return out.stdout


@pytest.mark.parametrize("name,locked,fallback", _FALLBACK_PAIRS, ids=lambda v: v if isinstance(v, str) else "")
def test_voss_no_unicode_env_swaps_glyph(name: str, locked: str, fallback: str) -> None:
    assert _read_glyph(name, env_value="1") == fallback


@pytest.mark.parametrize("name,locked,fallback", _FALLBACK_PAIRS, ids=lambda v: v if isinstance(v, str) else "")
def test_locked_codepoint_without_env(name: str, locked: str, fallback: str) -> None:
    assert _read_glyph(name, env_value=None) == locked


def test_fallback_table_complete() -> None:
    """The NO_UNICODE_FALLBACK dict must cover every locked glyph constant."""
    from voss.harness.tui import glyphs

    for name, _locked, _fallback in _FALLBACK_PAIRS:
        assert name in glyphs.NO_UNICODE_FALLBACK, name


def test_no_unicode_flag_sets_env(tmp_path, monkeypatch) -> None:
    """--no-unicode CLI flag sets VOSS_NO_UNICODE=1 before make_renderer."""
    monkeypatch.delenv("VOSS_NO_UNICODE", raising=False)
    from voss.harness.cli import _apply_no_unicode_env

    _apply_no_unicode_env(True)
    assert __import__("os").environ.get("VOSS_NO_UNICODE") == "1"


def test_no_unicode_flag_false_does_not_set(monkeypatch) -> None:
    monkeypatch.delenv("VOSS_NO_UNICODE", raising=False)
    from voss.harness.cli import _apply_no_unicode_env

    _apply_no_unicode_env(False)
    assert __import__("os").environ.get("VOSS_NO_UNICODE") is None


def test_repl_prompt_uses_ascii_fallback(monkeypatch) -> None:
    monkeypatch.setenv("VOSS_NO_UNICODE", "1")
    from voss.harness.cli import _repl_prompt

    assert _repl_prompt().endswith("> ")
