"""M9-02 glyph + color contract tests."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from voss.harness.tui import glyphs


def test_locked_glyph_codepoints() -> None:
    """Locked glyph table — contract v2 rebaseline (R2+R3, spec §4.2).

    R2 rule: `WORKING` (U+2726) and `SPINNER_FRAMES` (U+2800 braille
    block) join the allow-list for the R2 working indicator. SPINNER_FRAMES
    is a multi-char string constant iterated by index, not a single glyph.

    R3 rule: `TOOL_OK` (U+23FA), `OUTPUT_ELBOW` (U+23BF), and
    `CHEVRON_CLOSED`/`CHEVRON_OPEN` (U+25B8/U+25BE) join for ToolCards.
    `TOOL_CALL ⏵` is retained for the plain renderer's one-line format.
    """
    assert glyphs.PROMPT == "▌"
    assert glyphs.USER_INPUT == "❯"
    assert glyphs.TOOL_CALL == "⏵"
    assert glyphs.WARN == "⚠"
    assert glyphs.BAR_FILL == "█"
    assert glyphs.BAR_EMPTY == "░"
    assert glyphs.BUDGET_FILL == "▰"
    assert glyphs.BUDGET_EMPTY == "▱"
    assert glyphs.NEST_LAST == "└─"
    assert glyphs.NEST_MID == "├─"
    assert glyphs.FORK == "⎇"
    assert glyphs.WORKING == "✦"
    assert glyphs.SPINNER_FRAMES == "⠋⠙⠹⠸⠼⠴⠦⠧"
    assert glyphs.TOOL_OK == "⏺"
    assert glyphs.OUTPUT_ELBOW == "⎿"
    assert glyphs.CHEVRON_CLOSED == "▸"
    assert glyphs.CHEVRON_OPEN == "▾"


def test_glyph_not_in_allowlist_raises() -> None:
    with pytest.raises(AttributeError):
        glyphs.EMOJI_THUMBS_UP


def test_styles_tcss_has_accent_color() -> None:
    text = (Path(__file__).resolve().parents[3] / "voss" / "harness" / "tui" / "styles.tcss").read_text()
    assert text.count("#ff5b1f") >= 1


def test_styles_tcss_has_only_locked_palette() -> None:
    path = Path(__file__).resolve().parents[3] / "voss" / "harness" / "tui" / "styles.tcss"
    keep_lines = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("/*") or stripped.startswith("*") or stripped.endswith("*/"):
            continue
        if stripped.startswith("//"):
            continue
        keep_lines.append(line)
    body = "\n".join(keep_lines)
    matches = re.findall(r"#[0-9A-Fa-f]{6}", body)
    assert len(matches) == 5, f"expected 5 hex colors, got {matches}"
    locked = {"#FF5B1F", "#888888", "#5FD75F", "#FFD75F", "#FF5F5F"}
    assert set(m.upper() for m in matches) == locked


def test_no_emoji_in_tui_source() -> None:
    """No pictograph emojis in TUI source — UI-SPEC bans them.

    Pattern matches actual emojis (pictographs, smileys, hearts, fire, etc.)
    while excluding U+2700-U+277F which contains the locked angle-bracket
    glyph `❯` used by the input bar (UI-SPEC explicit allow).
    """
    tui = Path(__file__).resolve().parents[3] / "voss" / "harness" / "tui"
    emoji_pattern = re.compile(
        r"[\U0001F300-\U0001FAFF\U0001F600-\U0001F64F\U00002780-\U000027BF]"
    )
    for py in [
        tui / "glyphs.py",
        tui / "styles.tcss",
        tui / "app.py",
        *(tui / "widgets").glob("*.py"),
    ]:
        text = py.read_text()
        m = emoji_pattern.search(text)
        assert m is None, f"emoji found in {py}: {m.group()!r}"
