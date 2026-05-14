"""M8-03 convention extraction tests."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="M8-03 — pending behavior implementation")


def test_scripted_signal_session_surfaces_candidate() -> None:
    pass


def test_decline_writes_nothing() -> None:
    pass


def test_accept_writes_one_file_with_evidence() -> None:
    pass


def test_no_signal_skips_llm_entirely() -> None:
    pass


def test_extraction_timeout_returns_empty() -> None:
    pass
