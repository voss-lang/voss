"""Haskell frontend wiring (optional binary)."""

from __future__ import annotations

import shutil

import pytest

from voss.exceptions import VossParseError
from voss.parser import parse


def test_voss_frontend_haskell_requires_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOSS_FRONTEND", "haskell")
    monkeypatch.delenv("VOSS_FRONTEND_HS_EXE", raising=False)
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    with pytest.raises(VossParseError, match="executable not found"):
        parse("let x = 1\n", file="t.voss")
