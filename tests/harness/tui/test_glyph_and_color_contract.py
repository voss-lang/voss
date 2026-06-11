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
    """Color contract v2 rebaseline (R5, spec §4.1).

    v2 rule: exactly 9 hex values in styles.tcss — the 5 locked foreground
    roles plus $bg/$surface/$raised/$text. (The spec header says "exactly
    10 hex" but its own table lists 9 distinct values: "$dim doubles as dim
    text; no sixth gray" — the table's value count is authoritative.)
    Translucent uses of palette vars ($accent 8%) do not count as new hex.
    """
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
    assert len(matches) == 9, f"expected 9 hex colors, got {matches}"
    locked = {
        "#FF5B1F",  # $accent
        "#888888",  # $dim (doubles as dim text)
        "#5FD75F",  # $good
        "#FFD75F",  # $warn
        "#FF5F5F",  # $error
        "#121212",  # $bg
        "#1C1C1C",  # $surface
        "#262626",  # $raised
        "#DADADA",  # $text
    }
    assert set(m.upper() for m in matches) == locked


def _tui_root() -> Path:
    return Path(__file__).resolve().parents[3] / "voss" / "harness" / "tui"


_HEX_LITERAL = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")


def test_no_hex_literal_in_py_outside_palette() -> None:
    """Color contract v2 rebaseline (R5, spec §4.1).

    v2 rule: zero hex color literals in voss/harness/tui/**/*.py EXCEPT
    palette.py — the single Python-side mirror for Rich Text styles that
    cannot read tcss vars (assistant gutter, logo, status zones, diff
    lines). IGNITE_ORANGE / status_line literals / DEFAULT_CSS hex are gone.
    """
    offending: list[str] = []
    for py in sorted(_tui_root().rglob("*.py")):
        if py.name == "palette.py":
            continue
        for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            if _HEX_LITERAL.search(line):
                offending.append(f"{py}:{lineno}: {line.strip()}")
    assert not offending, (
        "hex color literals outside palette.py:\n" + "\n".join(offending)
    )


def test_palette_matches_tcss() -> None:
    """Color contract v2 rebaseline (R5, spec §4.1).

    v2 rule: palette.py values must exactly match the styles.tcss
    declarations — tcss is the source of truth, palette.py is the audited
    Rich-side mirror. Compares every `$var: #hex;` declaration against
    palette.TCSS_VARS (names and values, case-insensitive hex).
    """
    from voss.harness.tui import palette

    tcss = (_tui_root() / "styles.tcss").read_text(encoding="utf-8")
    declared = {
        m.group(1): m.group(2).lower()
        for m in re.finditer(r"^\$([a-z-]+):\s*(#[0-9a-fA-F]{6});", tcss, re.MULTILINE)
    }
    mirrored = {name: value.lower() for name, value in palette.TCSS_VARS.items()}
    assert declared == mirrored, (
        f"palette.py out of sync with styles.tcss:\n"
        f"  tcss:    {declared}\n  palette: {mirrored}"
    )


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
