"""M8-05 wires VOSS.md into system context; behavior implemented in M8-01."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="M8-05 — pending behavior implementation")


def test_voss_md_loaded_in_system_context() -> None:
    pass


def test_missing_file_degrades_silently() -> None:
    pass
