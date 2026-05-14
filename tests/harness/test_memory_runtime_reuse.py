"""M8 Req 7 grep gate + M8-02 SemanticMemory reuse assertions.

The first test is a STATIC GREP GATE — runs green from Wave 0 onward to
guarantee no `class *Memory` subclasses appear under voss/harness/. This
pins the Req 7 invariant from day one.

The second test (semantic init on recall) is M8-02 behavior and stays
skipped until that wave lands.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


_HARNESS_DIR = Path(__file__).resolve().parents[2] / "voss" / "harness"
_CLASS_MEMORY_RE = re.compile(r"^class\s+[A-Za-z_]+Memory\b")


def test_no_harness_memory_class_definitions_outside_runtime() -> None:
    """Req 7: no class whose name ends in 'Memory' may be defined under voss/harness/.

    MemoryStore is allowed (ends in 'Store', not 'Memory'). This protects the
    composition-over-subclassing invariant for voss_runtime.memory types.
    """
    offenders: list[str] = []
    for py in _HARNESS_DIR.rglob("*.py"):
        try:
            text = py.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            # Skip comment-only lines
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if _CLASS_MEMORY_RE.match(line):
                offenders.append(f"{py.relative_to(_HARNESS_DIR.parent.parent)}:{lineno}: {line}")
    assert not offenders, (
        "Found class definitions ending in 'Memory' under voss/harness/ "
        "(Req 7 forbids subclassing voss_runtime.memory types):\n"
        + "\n".join(offenders)
    )


@pytest.mark.skip(reason="M8-02 — pending behavior implementation")
def test_semantic_memory_init_called_on_recall() -> None:
    pass
