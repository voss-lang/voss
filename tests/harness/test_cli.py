from click.testing import CliRunner

from voss.harness.cli import main


class TestUnifiedVossCli:
    """Agent verbs must appear under the unified `voss` CLI."""

    def test_voss_help_lists_agent_verbs(self) -> None:
        from voss.cli import main as voss_main

        r = CliRunner().invoke(voss_main, ["--help"])
        assert r.exit_code == 0
        for verb in ("do", "chat", "doctor"):
            assert verb in r.output, f"missing agent verb: {verb}"
        for verb in ("compile", "run", "check", "init", "ast"):
            assert verb in r.output, f"missing compiler verb: {verb}"

    def test_voss_doctor_works(self, monkeypatch) -> None:
        # Force all checks OK so exit code is deterministic in CI without creds.
        from voss.harness import diagnostics as diag

        monkeypatch.setattr(
            diag, "run_all_checks",
            lambda _cwd: [
                diag.Check("python", diag.CheckResult.OK),
                diag.Check("voss import", diag.CheckResult.OK),
                diag.Check("provider auth", diag.CheckResult.OK),
                diag.Check("git", diag.CheckResult.OK),
                diag.Check("cwd writable", diag.CheckResult.OK),
                diag.Check("config dirs", diag.CheckResult.OK),
                diag.Check("project dirs", diag.CheckResult.OK),
            ],
        )

        from voss.cli import main as voss_main

        r = CliRunner().invoke(voss_main, ["doctor"])
        assert r.exit_code == 0
        assert "voss import" in r.output


class TestCli:
    def test_help(self) -> None:
        r = CliRunner().invoke(main, ["--help"])
        assert r.exit_code == 0
        assert "voss" in r.output
        assert "do" in r.output
        assert "chat" in r.output

    def test_doctor(self, monkeypatch) -> None:
        from voss.harness import diagnostics as diag

        monkeypatch.setattr(
            diag, "run_all_checks",
            lambda _cwd: [
                diag.Check("python", diag.CheckResult.OK),
                diag.Check("voss import", diag.CheckResult.OK),
                diag.Check("provider auth", diag.CheckResult.OK),
                diag.Check("git", diag.CheckResult.OK),
                diag.Check("cwd writable", diag.CheckResult.OK),
                diag.Check("config dirs", diag.CheckResult.OK),
                diag.Check("project dirs", diag.CheckResult.OK),
            ],
        )
        r = CliRunner().invoke(main, ["doctor"])
        assert r.exit_code == 0
        assert "voss import" in r.output
        assert "✓" in r.output

    def test_do_with_auth_none_exits_2(self, monkeypatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        r = CliRunner().invoke(main, ["do", "--auth", "none", "anything"])
        assert r.exit_code == 2
        assert "no usable credentials" in r.output

    def test_do_with_auth_api_no_env_exits_2(self, monkeypatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        r = CliRunner().invoke(main, ["do", "--auth", "api", "anything"])
        assert r.exit_code == 2
