"""M8-04 vacuum command tests."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="M8-04 — pending behavior implementation")


def test_vacuum_reclaims_tombstoned_bytes() -> None:
    pass


def test_vacuum_deletes_tombstoned_files() -> None:
    pass
