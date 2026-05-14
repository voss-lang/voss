"""M9-03 RESERVED_SLASH_NAMES contract tests."""
from __future__ import annotations

import pytest

from voss.harness.tui.reserved_slash_names import RESERVED_SLASH_NAMES


def test_reserved_slash_names_locked_order() -> None:
    assert RESERVED_SLASH_NAMES == ("/recall", "/forget", "/memory", "/save")


def test_reserved_slash_names_is_immutable_tuple() -> None:
    assert isinstance(RESERVED_SLASH_NAMES, tuple)
    with pytest.raises(AttributeError):
        RESERVED_SLASH_NAMES.append("/extra")  # type: ignore[attr-defined]
