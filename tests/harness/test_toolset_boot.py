"""
Boot-path regression for make_toolset (V19-03 fallout).
`voss chat` from a large non-git cwd hung before the TUI appeared: the
"""
from __future__ import annotations

from pathlib import Path

import pytest

import voss.harness.code.service as code_service
from voss.harness.tools import make_toolset


def test_make_toolset_boot_does_not_build_code_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Path] = []
    monkeypatch.setattr(
        code_service, "build_index", lambda cwd: calls.append(cwd)
    )

    toolset = make_toolset(tmp_path)

    assert calls == [], "boot path must not run the synchronous M10 build_index"
    # The recall wiring itself still lands (degrades cleanly if absent).
    assert "code_search" in toolset
