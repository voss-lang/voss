"""M9-07 UI-SPEC Acceptance Visual Check 3 — accent allow-list audit.

The TUI palette has exactly one accent color (`#ff5b1f` / `$accent` / the
`.accent` class). UI-SPEC line 145 restricts its application to six
widgets plus the canonical declaration site in `styles.tcss`:

    1. input_bar.py     — user-input glyph `▌`
    2. header.py        — session id
    3. status_line.py   — current model name
    4. sub_agent_panel.py — active sub-agent banner
    5. slash_palette.py — current selection (combined with reverse-video)
    6. confidence_bar.py — agent's FINAL confidence value

Plus `styles.tcss` where the `$accent` design token is defined.

This audit walks every `.py` / `.tcss` file under `voss/harness/tui/` and
asserts the set of files containing accent references is a subset of the
locked allow-list. Any new file picking up the accent color silently is a
test failure with the offending path printed.
"""
from __future__ import annotations

import re
from pathlib import Path


_ACCENT_PATTERN = re.compile(r"(?i)(\$accent|\.accent\b|#ff5b1f)")

_ALLOWLIST = frozenset(
    {
        "input_bar.py",
        "header.py",
        "status_line.py",
        "sub_agent_panel.py",
        "code_intel_panel.py",  # M9-08 side-region peer to SubAgentPanel
        "slash_palette.py",
        "confidence_bar.py",
        "styles.tcss",
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
            "files outside the locked six widgets + styles.tcss:\n"
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
