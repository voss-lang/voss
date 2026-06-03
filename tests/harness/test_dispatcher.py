"""H6.3 — native-client dispatcher in `voss` (voss/cli.py)."""

from __future__ import annotations

from click.testing import CliRunner

import voss.cli as vcli


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


def test_ui_execs_binary_when_found(monkeypatch):
    monkeypatch.setattr(vcli, "_find_voss_tui", lambda: "/fake/voss-tui")
    captured = {}

    def fake_exec(path, argv):
        captured["path"] = path
        captured["argv"] = argv
        raise SystemExit(0)

    monkeypatch.setattr(vcli.os, "execvp", fake_exec)
    CliRunner().invoke(vcli.main, ["ui", "--cwd", "."])
    assert captured["path"] == "/fake/voss-tui"
    assert captured["argv"] == ["/fake/voss-tui", "--cwd", "."]


def test_ui_falls_back_when_missing(monkeypatch):
    monkeypatch.setattr(vcli, "_find_voss_tui", lambda: None)
    calls = {"n": 0}
    monkeypatch.setattr(
        vcli, "_run_inprocess_chat", lambda ctx: calls.__setitem__("n", calls["n"] + 1)
    )

    def no_exec(*a, **k):
        raise AssertionError("execvp must not run when binary is missing")

    monkeypatch.setattr(vcli.os, "execvp", no_exec)
    result = CliRunner().invoke(vcli.main, ["ui"])
    assert calls["n"] == 1
    assert "voss-tui not found" in result.output


def test_should_use_native_tui_flag(monkeypatch):
    monkeypatch.setenv("VOSS_USE_TUI", "1")
    assert vcli._should_use_native_tui() is True
    monkeypatch.setenv("VOSS_USE_TUI", "0")
    assert vcli._should_use_native_tui() is False
    monkeypatch.delenv("VOSS_USE_TUI", raising=False)
    assert vcli._should_use_native_tui() is False
