from __future__ import annotations

import pytest

# Task fixtures are repos-under-test, not part of this suite: matrix fixtures
# carry their own test_calc.py meant to run inside the runner's isolated copy
# (cwd=fixture), where pytest resolves `from calc import add` at cwd.
collect_ignore_glob = ["golden/*", "matrix/*"]


@pytest.fixture(autouse=True)
def _set_voss_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    """All eval tests run with VOSS_DEV=1 so the gated verb is accessible."""
    monkeypatch.setenv("VOSS_DEV", "1")
