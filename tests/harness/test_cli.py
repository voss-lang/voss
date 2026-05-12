from pathlib import Path

import pytest
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


class TestAnalyzeRouting:
    """/analyze slash + natural-language route both invoke _handle_analyze."""

    def _patch_analyze_skill(self, monkeypatch) -> list[dict]:
        calls: list[dict] = []

        def fake_run(*, cwd, provider, history, record, renderer, tools, gate):
            calls.append({"cwd": cwd, "record_id": record.id})

        import voss.harness.skills.analyze as analyze_mod

        monkeypatch.setattr(analyze_mod, "run", fake_run)
        return calls

    def _drive_repl(self, monkeypatch, tmp_path: Path, input_text: str):
        from voss_runtime import EpisodicMemory

        from voss.harness import session as session_store
        from voss.harness.cli import _run_repl
        from voss.harness.providers import AnthropicOAuthProvider  # noqa: F401

        # Build a no-op provider — analyze.run is stubbed so it's unused.
        class _NoopProvider:
            async def complete(self, **_):
                raise AssertionError("provider.complete should not be called")

            def count_tokens(self, **_):
                return 1

        record = session_store.SessionRecord.new(
            cwd=tmp_path, model="claude-test"
        )
        # Feed lines via monkeypatched input() so the REPL exits after one cmd.
        lines = iter(input_text.splitlines())
        monkeypatch.setattr("builtins.input", lambda *_: next(lines))

        _run_repl(
            cwd=tmp_path,
            json_mode=False,
            mode="plan",
            history=EpisodicMemory(capacity=10),
            record=record,
            provider=_NoopProvider(),
            auth_detail="stub",
        )

    def test_slash_analyze_routes(self, monkeypatch, tmp_path: Path) -> None:
        calls = self._patch_analyze_skill(monkeypatch)
        self._drive_repl(monkeypatch, tmp_path, "/analyze\n/exit\n")
        assert len(calls) == 1
        assert calls[0]["cwd"] == tmp_path

    def test_natural_analyze_routes(self, monkeypatch, tmp_path: Path) -> None:
        calls = self._patch_analyze_skill(monkeypatch)
        self._drive_repl(monkeypatch, tmp_path, "analyze this repo\n/exit\n")
        assert len(calls) == 1


@pytest.mark.skip(reason="Wave 4 — pending plan M2-06")
def test_doctor_cognition_rows() -> None:
    pass
