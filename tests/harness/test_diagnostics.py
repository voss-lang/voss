"""Unit tests for voss/harness/diagnostics.py and the doctor CLI.

Covers D-11 (check set + display order), D-12 (glyphs), D-13 (diagnose-only),
and D-14 (exit code semantics including WARN-only stderr nuance).
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from voss.harness import auth as auth_mod
from voss.harness import diagnostics as diag
from voss.harness.cli import doctor_cmd


# ---------------------------------------------------------------------------
# Pure-check tests
# ---------------------------------------------------------------------------


class TestCheckPythonVersion:
    def test_ok_on_current_runtime(self):
        c = diag.check_python_version()
        assert c.result is diag.CheckResult.OK
        assert c.name == "python"

    def test_fail_when_too_old(self, monkeypatch):
        class FakeVI(tuple):
            major = 3
            minor = 9
            micro = 0

        monkeypatch.setattr(diag.sys, "version_info", FakeVI((3, 9, 0, "final", 0)))
        c = diag.check_python_version()
        assert c.result is diag.CheckResult.FAIL
        assert "3.10" in c.detail
        assert c.fix


class TestCheckVossImport:
    def test_ok(self):
        c = diag.check_voss_import()
        assert c.result is diag.CheckResult.OK


class TestCheckGitOnPath:
    def test_ok_when_found(self, monkeypatch):
        monkeypatch.setattr(diag.shutil, "which", lambda _name: "/usr/bin/git")
        c = diag.check_git_on_path()
        assert c.result is diag.CheckResult.OK
        assert c.detail == "/usr/bin/git"

    def test_fail_when_missing(self, monkeypatch):
        monkeypatch.setattr(diag.shutil, "which", lambda _name: None)
        c = diag.check_git_on_path()
        assert c.result is diag.CheckResult.FAIL
        assert c.fix


class TestCheckCwdWritable:
    def test_ok_on_tmp(self, tmp_path: Path):
        c = diag.check_cwd_writable(tmp_path)
        assert c.result is diag.CheckResult.OK
        assert str(tmp_path) in c.detail

    def test_fail_on_readonly(self, tmp_path: Path):
        ro = tmp_path / "ro"
        ro.mkdir()
        ro.chmod(0o500)
        try:
            c = diag.check_cwd_writable(ro)
            assert c.result is diag.CheckResult.FAIL
            assert c.fix
        finally:
            ro.chmod(0o700)


class TestCheckConfigDirsCreatable:
    def test_ok_with_xdg_override(self, monkeypatch, tmp_path: Path):
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
        c = diag.check_config_dirs_creatable()
        assert c.result is diag.CheckResult.OK

    def test_fail_when_unwritable(self, monkeypatch, tmp_path: Path):
        blocker = tmp_path / "blocker"
        blocker.write_text("not a dir")  # exists as a file → mkdir under it fails
        monkeypatch.setenv("XDG_CONFIG_HOME", str(blocker))
        monkeypatch.setenv("XDG_STATE_HOME", str(blocker))
        c = diag.check_config_dirs_creatable()
        assert c.result is diag.CheckResult.FAIL


class TestCheckProjectDirs:
    def test_ok(self, tmp_path: Path):
        c = diag.check_project_dirs(tmp_path)
        assert c.result is diag.CheckResult.OK

    def test_warn_not_fail_on_failure(self, tmp_path: Path):
        ro = tmp_path / "ro"
        ro.mkdir()
        ro.chmod(0o500)
        try:
            c = diag.check_project_dirs(ro)
            assert c.result in (diag.CheckResult.OK, diag.CheckResult.WARN)
            assert c.result is not diag.CheckResult.FAIL
        finally:
            ro.chmod(0o700)


class TestCheckProviderAuth:
    def test_ok_when_anthropic_oauth_fresh(self, monkeypatch):
        fake = auth_mod.AnthropicOAuthCreds(
            access_token="a",
            refresh_token="r",
            expires_at_ms=10**15,
            subscription_type="pro",
        )
        monkeypatch.setattr(auth_mod, "load_anthropic_oauth", lambda: fake)
        monkeypatch.setattr(auth_mod, "load_codex", lambda: None)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        c = diag.check_provider_auth()
        assert c.result is diag.CheckResult.OK
        assert "Claude" in c.detail

    def test_warn_when_anthropic_expired(self, monkeypatch):
        fake = auth_mod.AnthropicOAuthCreds(
            access_token="a", refresh_token="r", expires_at_ms=0, subscription_type="pro"
        )
        monkeypatch.setattr(auth_mod, "load_anthropic_oauth", lambda: fake)
        monkeypatch.setattr(auth_mod, "load_codex", lambda: None)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        c = diag.check_provider_auth()
        assert c.result is diag.CheckResult.WARN

    def test_warn_when_only_codex(self, monkeypatch):
        codex = auth_mod.CodexCreds(
            api_key="sk-x",
            access_token=None,
            refresh_token=None,
            account_id=None,
            auth_mode="ApiKey",
        )
        monkeypatch.setattr(auth_mod, "load_anthropic_oauth", lambda: None)
        monkeypatch.setattr(auth_mod, "load_codex", lambda: codex)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        c = diag.check_provider_auth()
        assert c.result is diag.CheckResult.WARN

    def test_fail_when_nothing(self, monkeypatch):
        monkeypatch.setattr(auth_mod, "load_anthropic_oauth", lambda: None)
        monkeypatch.setattr(auth_mod, "load_codex", lambda: None)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        c = diag.check_provider_auth()
        assert c.result is diag.CheckResult.FAIL
        assert c.fix


class TestRunAllChecks:
    def test_returns_checks_in_display_order(self, tmp_path: Path):
        results = diag.run_all_checks(tmp_path)
        assert len(results) == 8
        names = [c.name for c in results]
        assert names == [
            "python",
            "voss import",
            "provider auth",
            "git",
            "cwd writable",
            "config dirs",
            "project dirs",
            "harness cache",
        ]


class TestAggregateExitCode:
    def test_all_ok(self):
        rs = [diag.Check("a", diag.CheckResult.OK), diag.Check("b", diag.CheckResult.OK)]
        assert diag.aggregate_exit_code(rs) == 0

    def test_with_warn(self):
        rs = [diag.Check("a", diag.CheckResult.OK), diag.Check("b", diag.CheckResult.WARN)]
        assert diag.aggregate_exit_code(rs) == 0

    def test_with_fail(self):
        rs = [diag.Check("a", diag.CheckResult.OK), diag.Check("b", diag.CheckResult.FAIL)]
        assert diag.aggregate_exit_code(rs) == 1


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


def _patch_all_ok(monkeypatch):
    monkeypatch.setattr(
        diag, "check_python_version",
        lambda: diag.Check("python", diag.CheckResult.OK, detail="3.13"),
    )
    monkeypatch.setattr(
        diag, "check_voss_import",
        lambda: diag.Check("voss import", diag.CheckResult.OK, detail="ok"),
    )
    monkeypatch.setattr(
        diag, "check_provider_auth",
        lambda: diag.Check("provider auth", diag.CheckResult.OK, detail="creds"),
    )
    monkeypatch.setattr(
        diag, "check_git_on_path",
        lambda: diag.Check("git", diag.CheckResult.OK, detail="/usr/bin/git"),
    )
    monkeypatch.setattr(
        diag, "check_cwd_writable",
        lambda _cwd: diag.Check("cwd writable", diag.CheckResult.OK, detail="ok"),
    )
    monkeypatch.setattr(
        diag, "check_config_dirs_creatable",
        lambda: diag.Check("config dirs", diag.CheckResult.OK, detail="ok"),
    )
    monkeypatch.setattr(
        diag, "check_project_dirs",
        lambda _cwd: diag.Check("project dirs", diag.CheckResult.OK, detail="ok"),
    )
    monkeypatch.setattr(
        diag, "check_harness_cache",
        lambda _cwd: diag.Check("harness cache", diag.CheckResult.OK, detail="ok"),
    )


class TestDoctorCmd:
    def test_exits_zero_in_healthy_env(self, monkeypatch, tmp_path):
        _patch_all_ok(monkeypatch)
        result = CliRunner().invoke(doctor_cmd, ["--cwd", str(tmp_path)])
        assert result.exit_code == 0

    def test_exits_one_on_fail(self, monkeypatch, tmp_path):
        _patch_all_ok(monkeypatch)
        monkeypatch.setattr(
            diag, "check_provider_auth",
            lambda: diag.Check(
                "provider auth", diag.CheckResult.FAIL,
                detail="no creds", fix="claude /login",
            ),
        )
        result = CliRunner().invoke(doctor_cmd, ["--cwd", str(tmp_path)])
        assert result.exit_code == 1
        assert "claude /login" in result.output

    def test_only_warn_exits_zero(self, monkeypatch, tmp_path):
        _patch_all_ok(monkeypatch)
        monkeypatch.setattr(
            diag, "check_provider_auth",
            lambda: diag.Check(
                "provider auth", diag.CheckResult.WARN, detail="only codex",
            ),
        )
        result = CliRunner().invoke(doctor_cmd, ["--cwd", str(tmp_path)])
        assert result.exit_code == 0

    def test_warn_only_surfaces_stderr_summary(self, monkeypatch, tmp_path):
        _patch_all_ok(monkeypatch)
        monkeypatch.setattr(
            diag, "check_provider_auth",
            lambda: diag.Check(
                "provider auth", diag.CheckResult.WARN, detail="only codex",
            ),
        )
        runner = CliRunner()
        result = runner.invoke(doctor_cmd, ["--cwd", str(tmp_path)])
        assert result.exit_code == 0
        assert "warning" in result.stderr.lower(), (
            f"WARN-only doctor must surface a stderr summary (D-14); got stderr: {result.stderr!r}"
        )
        assert "provider auth" in result.stderr.lower()

    def test_all_ok_no_stderr_summary(self, monkeypatch, tmp_path):
        _patch_all_ok(monkeypatch)
        runner = CliRunner()
        result = runner.invoke(doctor_cmd, ["--cwd", str(tmp_path)])
        assert result.exit_code == 0
        assert result.stderr.strip() == "", (
            f"all-OK doctor must NOT emit stderr; got: {result.stderr!r}"
        )

    def test_output_contains_glyphs(self, monkeypatch, tmp_path):
        _patch_all_ok(monkeypatch)
        result = CliRunner().invoke(doctor_cmd, ["--cwd", str(tmp_path)])
        assert any(g in result.output for g in ("✓", "⚠", "✗"))

    def test_fix_text_shown_on_fail(self, monkeypatch, tmp_path):
        _patch_all_ok(monkeypatch)
        monkeypatch.setattr(
            diag, "check_git_on_path",
            lambda: diag.Check(
                "git", diag.CheckResult.FAIL,
                detail="missing", fix="brew install git",
            ),
        )
        result = CliRunner().invoke(doctor_cmd, ["--cwd", str(tmp_path)])
        assert result.exit_code == 1
        assert "brew install git" in result.output
