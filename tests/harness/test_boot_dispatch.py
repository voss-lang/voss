from __future__ import annotations

import sys
from pathlib import Path

import click
import pytest

from voss.harness import cache as harness_cache
from voss.harness import cli as cli_mod
from voss.harness import config as harness_config
from voss.harness.agent import run_turn as python_run_turn
from voss.harness.diagnostics import StaleHarnessCacheError


def test_resolve_python_by_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("VOSS_HARNESS", raising=False)
    monkeypatch.setattr(harness_config, "load_harness_config", lambda: {})

    assert cli_mod._resolve_run_turn(tmp_path) is python_run_turn


def test_env_backend_overrides_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VOSS_HARNESS", "python")
    monkeypatch.setattr(harness_config, "load_harness_config", lambda: {"backend": "rust"})

    assert cli_mod._resolve_run_turn(tmp_path) is python_run_turn


def test_config_fallback_selects_python(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("VOSS_HARNESS", raising=False)
    monkeypatch.setattr(harness_config, "load_harness_config", lambda: {"backend": "python"})

    assert cli_mod._resolve_run_turn(tmp_path) is python_run_turn


def test_invalid_backend_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VOSS_HARNESS", "rust")

    with pytest.raises(click.ClickException, match="invalid VOSS_HARNESS='rust'"):
        cli_mod._resolve_run_turn(tmp_path)


def test_compiled_stale_cache_raises_before_import(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("VOSS_HARNESS", "compiled")
    sys.modules.pop("voss_compiled_harness_loop", None)
    source_dir = tmp_path / "voss" / "harness" / "agent"
    source_dir.mkdir(parents=True)
    (source_dir / "loop.voss").write_text("# loop\n")

    with pytest.raises(StaleHarnessCacheError):
        cli_mod._resolve_run_turn(tmp_path)

    assert "voss_compiled_harness_loop" not in sys.modules


def test_compiled_backend_validates_cache_then_imports(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("VOSS_HARNESS", "compiled")
    sys.modules.pop("voss_compiled_harness_loop", None)
    source_dir = tmp_path / "voss" / "harness" / "agent"
    source_dir.mkdir(parents=True)
    (source_dir / "loop.voss").write_text("# loop\n")
    harness_cache.write_manifest(tmp_path, harness_cache.compute_source_shas(tmp_path))
    loop_py = tmp_path / harness_cache.CACHE_HARNESS_DIR / "loop.py"
    loop_py.write_text(
        "async def run_turn(*args, **kwargs):\n"
        "    return 'compiled'\n"
    )

    runner = cli_mod._resolve_run_turn(tmp_path)

    assert runner.__name__ == "run_turn"
    assert runner.__module__ == "voss_compiled_harness_loop"
    assert runner is not python_run_turn
