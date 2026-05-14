"""M8 Req 7 grep gate + M8-03 SemanticMemory reuse assertions.

The first test is a STATIC GREP GATE — runs green from Wave 0 onward to
guarantee no `class *Memory` subclasses appear under voss/harness/. This
pins the Req 7 invariant from day one.

The second test asserts that `SemanticMemory.__init__` is invoked at least
once on the first `recall` call (proves composition-not-rewrite of the
runtime semantic store).
"""
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock

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


def test_semantic_memory_init_called_on_recall(
    tmp_voss_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """First recall must construct SemanticMemory exactly once (lazy probe contract)."""
    from voss.harness import memory_store as ms_mod

    init_calls: list[dict] = []

    class FakeSemanticMemory:
        def __init__(self, *, persist_dir: str, collection_name: str = "voss_memory") -> None:
            init_calls.append({"persist_dir": persist_dir, "collection_name": collection_name})
            self._collection = MagicMock()
            self._collection.query.return_value = {
                "ids": [[]],
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]],
            }

        def add(self, *args, **kwargs) -> None:
            self._collection.add(*args, **kwargs)

    monkeypatch.setattr(ms_mod, "SemanticMemory", FakeSemanticMemory)

    store = ms_mod.MemoryStore(tmp_voss_repo).bind(session_id="s1")
    assert init_calls == [], "SemanticMemory must not be constructed before first recall/write"

    store.recall("anything", top_k=3)
    assert len(init_calls) == 1, f"expected exactly 1 SemanticMemory init; got {init_calls}"

    # Second recall must reuse the cached instance — no new init.
    store.recall("anything else", top_k=3)
    assert len(init_calls) == 1, "SemanticMemory must be cached; second recall re-instantiated"
