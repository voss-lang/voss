"""M9-07 UI-SPEC Acceptance Visual Check 3 — accent allow-list audit.

Contract v2 rebaseline (R5, spec §4.1/§8): the accent allow-list is
re-verified at SIX widget sites (header.py and sub_agent_panel.py left the
codebase in R5/R4; no new site was added — the UserBlock styling uses the
tint-only Open Question 2 default, `$accent 6%`, and tints of palette vars
in styles.tcss do not count):

    1. input_bar.py      — user-input glyph `▌` (.accent class)
    2. status_line.py    — brand `▌ voss` in the left zone
    3. slash_palette.py  — current selection (combined with reverse-video)
    4. confidence_bar.py — agent's FINAL confidence value
    5. code_intel_panel.py — side-region code intelligence header
    6. turn_view.py      — brand wordmark/logo + assistant ● gutter

Plus the two declaration sites: `styles.tcss` (the `$accent` design token
and the bordered-widget rules — MentionPalette/InputBar borders live there
so the .py files stay audit-clean) and `palette.py` (the audited
Python-side mirror for Rich Text styles; see test_palette_matches_tcss).

This audit walks every `.py` / `.tcss` file under `voss/harness/tui/` and
asserts the set of files containing accent references (`$accent`,
`.accent`, the raw hex, or the palette `ACCENT` constant) is a subset of
the locked allow-list. Any new file picking up the accent color silently
is a test failure with the offending path printed.
"""
from __future__ import annotations

import re
from pathlib import Path


_ACCENT_PATTERN = re.compile(r"(\$accent|\.accent\b|(?i:#ff5b1f)|\bACCENT\b)")

_ALLOWLIST = frozenset(
    {
        # 6 widget sites
        "input_bar.py",
        "status_line.py",
        "code_intel_panel.py",  # M9-08 side-region peer
        "turn_view.py",
        "slash_palette.py",
        "confidence_bar.py",
        # 2 declaration sites
        "styles.tcss",
        "palette.py",
    }
)


def _tui_root() -> Path:
    return Path(__file__).resolve().parents[3] / "voss" / "harness" / "tui"


def _scan_for_accent() -> dict[str, list[tuple[Path, int, str]]]:
    """Walk the TUI tree; return {basename: [(path, lineno, line), ...]}."""
    hits: dict[str, list[tuple[Path, int, str]]] = {}
    root = _tui_root()
    for path in sorted(list(root.rglob("*.py")) + list(root.rglob("*.tcss"))):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if _ACCENT_PATTERN.search(line):
                hits.setdefault(path.name, []).append((path, lineno, line))
    return hits


def test_accent_only_in_allowlist_files() -> None:
    hits = _scan_for_accent()
    offending = {
        name: refs for name, refs in hits.items() if name not in _ALLOWLIST
    }
    if offending:
        lines = []
        for name, refs in sorted(offending.items()):
            for path, lineno, line in refs:
                lines.append(f"  {path}:{lineno}: {line.strip()}")
        msg = (
            "UI-SPEC accent allow-list violation. Accent color appears in "
            "files outside the audited widgets + styles.tcss:\n"
            + "\n".join(lines)
            + f"\nAllow-list: {sorted(_ALLOWLIST)}"
        )
        raise AssertionError(msg)


def test_accent_declaration_site_present() -> None:
    """`styles.tcss` must declare the `$accent` design token."""
    tcss = _tui_root() / "styles.tcss"
    text = tcss.read_text(encoding="utf-8")
    assert "$accent" in text, "styles.tcss must declare $accent token"
    assert "#ff5b1f" in text, "styles.tcss must bind $accent to #ff5b1f"
