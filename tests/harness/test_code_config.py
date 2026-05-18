"""Basic tests for the LSP config loader (M10-01 Task 1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from voss.harness.code.config import LspConfig, load_lsp_config


def test_load_defaults_without_user_file(tmp_path: Path) -> None:
    cfg = load_lsp_config(cwd=tmp_path)
    assert isinstance(cfg, LspConfig)
    assert "python" in cfg.servers
    assert "rust" in cfg.servers
    assert cfg.servers["python"].disabled is False


def test_user_overlay_can_disable_language(tmp_path: Path) -> None:
    voss_dir = tmp_path / ".voss"
    voss_dir.mkdir()
    (voss_dir / "lsp.yml").write_text("servers:\n  python:\n    command: [\"pyright-langserver\", \"--stdio\"]\n    disabled: true\n", encoding="utf-8")

    cfg = load_lsp_config(cwd=tmp_path)
    assert cfg.servers["python"].disabled is True


def test_strict_extra_rejection(tmp_path: Path) -> None:
    voss_dir = tmp_path / ".voss"
    voss_dir.mkdir()
    (voss_dir / "lsp.yml").write_text("servers: {}\nunknown_key: 42\n", encoding="utf-8")

    with pytest.raises(RuntimeError):
        load_lsp_config(cwd=tmp_path)


def test_defaults_do_not_require_pygls_installed() -> None:
    # Importing the module must not trigger import of pygls
    import sys
    assert "pygls" not in sys.modules
    from voss.harness.code import config as c
    assert hasattr(c, "load_lsp_config")
