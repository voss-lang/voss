from click.testing import CliRunner

from voss.harness.cli import main


class TestCli:
    def test_help(self) -> None:
        r = CliRunner().invoke(main, ["--help"])
        assert r.exit_code == 0
        assert "voss" in r.output
        assert "do" in r.output
        assert "chat" in r.output

    def test_doctor(self) -> None:
        r = CliRunner().invoke(main, ["doctor"])
        assert r.exit_code == 0
        assert "default model" in r.output
        assert "voss_runtime" in r.output

    def test_do_without_provider_key_exits_2(self, monkeypatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        r = CliRunner().invoke(main, ["do", "anything"])
        assert r.exit_code == 2
        assert "no provider key" in r.output or "no provider key" in (r.stderr_bytes or b"").decode()
