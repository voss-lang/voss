"""M8-04 vacuum + M8-02 inline eviction tests."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="M8-04 — pending behavior implementation")


def test_inline_evict_when_source_over_quota() -> None:
    pass


def test_post_write_size_under_cap() -> None:
    pass


def test_oldest_evicted_first_within_source() -> None:
    pass
