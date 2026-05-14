"""M8-06 /save (memory note) slash command tests; regression for Pitfall 1 collision."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="M8-06 — pending behavior implementation")


def test_save_note_writes_to_memory_notes_dir() -> None:
    pass


def test_save_note_does_not_rename_session() -> None:
    pass
