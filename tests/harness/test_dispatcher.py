"""H6.3 — native-client dispatcher in `voss` (voss/cli.py)."""

from __future__ import annotations

import sys

import pytest
from click.testing import CliRunner

import voss.cli as vcli


@pytest.fixture(autouse=True)
def isolated_cli_path(tmp_path, monkeypatch):
    monkeypatch.setattr(vcli, "__file__", str(tmp_path / "voss" / "cli.py"))


def test_find_voss_tui_env_existing(tmp_path, monkeypatch):
    fake = tmp_path / "voss-tui"
    fake.write_text("#!/bin/sh\n")
    monkeypatch.setenv("VOSS_TUI_BIN", str(fake))
    assert vcli._find_voss_tui() == str(fake)


def test_find_voss_tui_env_missing_path(monkeypatch):
    monkeypatch.setenv("VOSS_TUI_BIN", "/nonexistent/voss-tui")
    assert vcli._find_voss_tui() is None


def test_find_voss_tui_from_path(monkeypatch):
    monkeypatch.delenv("VOSS_TUI_BIN", raising=False)
    monkeypatch.setattr(
        "shutil.which",
        lambda n: "/usr/local/bin/voss-tui" if n == "voss-tui" else None,
    )
    assert vcli._find_voss_tui() == "/usr/local/bin/voss-tui"


@pytest.mark.parametrize("platform,filename", [("darwin", "voss-tui"), ("win32", "voss-tui.exe")])
def test_editable_install_finds_local_build_from_any_cwd(tmp_path, monkeypatch, platform, filename):
    monkeypatch.delenv("VOSS_TUI_BIN", raising=False)
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setattr("shutil.which", lambda _: "/older/voss-tui")
    binary = tmp_path / "tui" / filename
    binary.parent.mkdir()
    binary.write_text("local build")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    assert vcli._find_voss_tui() == str(binary)
    override = tmp_path / filename
    override.write_text("explicit build")
    monkeypatch.setenv("VOSS_TUI_BIN", str(override))
    assert vcli._find_voss_tui() == str(override)


def test_find_voss_tui_missing_local_build_and_path(monkeypatch):
    monkeypatch.delenv("VOSS_TUI_BIN", raising=False)
    monkeypatch.setattr("shutil.which", lambda _: None)
    assert vcli._find_voss_tui() is None


def test_ui_execs_binary_when_found(monkeypatch):
    monkeypatch.setattr(vcli, "_find_voss_tui", lambda: "/fake/voss-tui")
    captured = {}

    def fake_exec(path, argv, env):
        captured["path"] = path
        captured["argv"] = argv
        captured["env"] = env
        raise SystemExit(0)

    monkeypatch.setattr(vcli.os, "execvpe", fake_exec)
    CliRunner().invoke(vcli.main, ["ui", "--cwd", "."])
    assert captured["path"] == "/fake/voss-tui"
    assert captured["argv"] == ["/fake/voss-tui", "--cwd", "."]
    assert captured["env"]["VOSS_SERVER_PYTHON"] == sys.executable


def test_ui_falls_back_when_missing(monkeypatch):
    monkeypatch.setattr(vcli, "_find_voss_tui", lambda: None)
    calls = {"n": 0}
    monkeypatch.setattr(
        vcli, "_run_inprocess_chat", lambda ctx: calls.__setitem__("n", calls["n"] + 1)
    )

    def no_exec(*a, **k):
        raise AssertionError("execvpe must not run when binary is missing")

    monkeypatch.setattr(vcli.os, "execvpe", no_exec)
    result = CliRunner().invoke(vcli.main, ["ui"])
    assert calls["n"] == 1
    assert "voss-tui not found" in result.output


def test_should_use_native_tui_flag(monkeypatch):
    monkeypatch.setenv("VOSS_USE_TUI", "1")
    assert vcli._should_use_native_tui() is True
    monkeypatch.setenv("VOSS_USE_TUI", "0")
    assert vcli._should_use_native_tui() is False
    monkeypatch.delenv("VOSS_USE_TUI", raising=False)
    assert vcli._should_use_native_tui() is True


@pytest.mark.parametrize("flag,native", [("1", True), ("true", True), ("0", False), ("false", False), (None, True)])
@pytest.mark.parametrize("binary", ["/fake/voss-tui", None])
def test_bare_voss_prefers_go_unless_disabled_or_missing(monkeypatch, flag, native, binary):
    if flag is None:
        monkeypatch.delenv("VOSS_USE_TUI", raising=False)
    else:
        monkeypatch.setenv("VOSS_USE_TUI", flag)
    monkeypatch.setenv("VOSS_BIN", "/custom/server")
    monkeypatch.setattr(vcli, "_find_voss_tui", lambda: binary)
    calls = []

    def fake_exec(path, argv, env):
        calls.append("native")
        assert argv == [path]
        assert env["VOSS_SERVER_PYTHON"] == sys.executable
        assert env["VOSS_BIN"] == "/custom/server"
        raise SystemExit(0)

    monkeypatch.setattr(vcli.os, "execvpe", fake_exec)
    monkeypatch.setattr(vcli, "_run_inprocess_chat", lambda ctx: calls.append("textual"))
    result = CliRunner().invoke(vcli.main, [])
    assert result.exit_code == 0, result.output
    assert calls == ["native" if native and binary else "textual"]
