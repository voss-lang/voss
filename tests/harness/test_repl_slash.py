"""Tests for REPL slash command helpers extracted from _run_repl.

Strategy: test the slash helpers directly with monkeypatched auth + config,
rather than driving the full REPL loop (covered by Plan 07 e2e).
"""
from __future__ import annotations

import pytest

from voss.harness import auth as auth_mod
from voss.harness import config as harness_config
from voss.harness.auth import AnthropicOAuthCreds
from voss.harness.cli import _handle_login, _print_slash_help


@pytest.fixture
def isolate_config(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))


class TestLoginHandler:
    def test_no_creds_prints_upstream_command(self, monkeypatch, capsys):
        monkeypatch.setattr(auth_mod, "load_anthropic_oauth", lambda: None)
        monkeypatch.setattr(auth_mod, "load_codex", lambda: None)
        _handle_login("anthropic")
        captured = capsys.readouterr()
        assert "claude /login" in captured.out

    def test_existing_fresh_creds_no_refresh(self, monkeypatch, capsys):
        creds = AnthropicOAuthCreds(
            access_token="t",
            refresh_token="r",
            expires_at_ms=10**15,  # far future
            subscription_type="max",
        )
        monkeypatch.setattr(auth_mod, "load_anthropic_oauth", lambda: creds)
        refresh_called: list = []
        monkeypatch.setattr(
            auth_mod, "refresh_anthropic",
            lambda c, **kw: refresh_called.append(c) or c,
        )
        _handle_login("anthropic")
        captured = capsys.readouterr()
        assert "OK" in captured.out
        assert not refresh_called

    def test_expired_creds_triggers_refresh(self, monkeypatch, capsys):
        creds = AnthropicOAuthCreds(
            access_token="t",
            refresh_token="r",
            expires_at_ms=0,  # expired
            subscription_type="max",
        )
        monkeypatch.setattr(auth_mod, "load_anthropic_oauth", lambda: creds)
        refresh_called: list = []
        monkeypatch.setattr(
            auth_mod, "refresh_anthropic",
            lambda c, **kw: refresh_called.append(c) or c,
        )
        _handle_login("anthropic")
        captured = capsys.readouterr()
        assert "refreshed" in captured.out.lower()
        assert refresh_called

    def test_no_provider_arg_lists_both(self, monkeypatch, capsys):
        monkeypatch.setattr(auth_mod, "load_anthropic_oauth", lambda: None)
        monkeypatch.setattr(auth_mod, "load_codex", lambda: None)
        _handle_login(None)
        captured = capsys.readouterr()
        assert "Claude" in captured.out
        assert "Codex" in captured.out

    def test_unknown_provider_warns(self, monkeypatch, capsys):
        monkeypatch.setattr(auth_mod, "load_anthropic_oauth", lambda: None)
        monkeypatch.setattr(auth_mod, "load_codex", lambda: None)
        _handle_login("xenon")
        captured = capsys.readouterr()
        assert "unknown provider" in captured.err


class TestSlashHelp:
    def test_help_lists_new_commands(self, capsys):
        _print_slash_help()
        captured = capsys.readouterr()
        for token in ("/login", "/model", "/mode", "--confirm"):
            assert token in captured.out, f"missing slash token: {token}"


class TestModeEscalationParsing:
    """Parse-level checks for /mode auto vs /mode auto --confirm."""

    def test_mode_auto_without_confirm_detected(self):
        parts = "/mode auto".split()
        assert parts[1] == "auto"
        assert "--confirm" not in parts

    def test_mode_auto_with_confirm_detected(self):
        parts = "/mode auto --confirm".split()
        assert parts[1] == "auto"
        assert "--confirm" in parts


class TestModelPersistence:
    def test_set_preferred_model_round_trip(self, isolate_config):
        harness_config.set_preferred_model("claude-sonnet-4-20250514")
        cfg = harness_config.load_harness_config()
        assert cfg.get("preferred_model") == "claude-sonnet-4-20250514"


def test_memory_commands_registered() -> None:
    from voss.harness.cli import _build_slash_registry

    registry = _build_slash_registry()
    for name in ("/recall", "/forget", "/memory", "/save", "/save-session"):
        assert registry.lookup(name) is not None, f"slash {name} not registered"


def test_t6_prd_slash_commands_registered() -> None:
    """T6 — PRD §2.4 slash debt. /diff /apply /discard /budget /resume /why
    must all register; /cost gains --by-model and --by-tool handling."""
    from voss.harness.cli import _build_slash_registry

    registry = _build_slash_registry()
    for name in ("/diff", "/apply", "/discard", "/budget", "/resume", "/why"):
        assert registry.lookup(name) is not None, f"slash {name} not registered"


class TestT6Behaviors:
    """T6 — Verify /why /budget /cost --by-model and /discard dry-run paths
    against a fake ReplContext. Heavier integrations (live /resume, /diff
    against a real repo) covered by Plan 07 e2e."""

    @pytest.fixture
    def fake_ctx(self, tmp_path):
        from types import SimpleNamespace

        # Stub Plan-like for /why.
        plan = SimpleNamespace(
            rationale="picked the read-only path first",
            confidence=0.82,
            steps=[
                SimpleNamespace(name="fs_grep", why="locate symbol"),
                SimpleNamespace(name="fs_read", why="confirm context"),
            ],
            open_question=None,
            final_when_done="symbol mapped",
        )
        record = SimpleNamespace(
            id="abc123",
            name="fake-session",
            cwd=str(tmp_path),
            model="claude-sonnet-4-7",
            total_cost_usd=0.0,
            turns=[],
            # runs[-1] is the most recent; /discard reverts its changed list.
            runs=[
                {"cost_usd": 0.008, "changed": []},
                {"cost_usd": 0.012, "changed": ["voss/harness/cli.py"]},
            ],
        )
        return SimpleNamespace(
            cwd=tmp_path,
            record=record,
            history=None,
            last_plan=plan,
            total_cost=0.020,
            budget_usd=None,
            prior_context=None,
        )

    def test_why_renders_rationale_and_steps(self, fake_ctx, capsys):
        from voss.harness.cli import _build_slash_registry

        reg = _build_slash_registry()
        reg.lookup("/why").handler(fake_ctx, [], "/why")
        out = capsys.readouterr().out
        assert "picked the read-only path first" in out
        assert "0.82" in out
        assert "fs_grep" in out and "fs_read" in out

    def test_why_no_plan_errors_cleanly(self, fake_ctx, capsys):
        from voss.harness.cli import _build_slash_registry

        fake_ctx.last_plan = None
        reg = _build_slash_registry()
        reg.lookup("/why").handler(fake_ctx, [], "/why")
        err = capsys.readouterr().err
        assert "no plan yet" in err

    def test_budget_set_and_show(self, fake_ctx, capsys):
        from voss.harness.cli import _build_slash_registry

        reg = _build_slash_registry()
        reg.lookup("/budget").handler(fake_ctx, ["5.00"], "/budget 5.00")
        assert fake_ctx.budget_usd == 5.00
        reg.lookup("/budget").handler(fake_ctx, [], "/budget")
        out = capsys.readouterr().out
        assert "$5.00" in out and "0.0200" in out

    def test_budget_zero_clears(self, fake_ctx):
        from voss.harness.cli import _build_slash_registry

        fake_ctx.budget_usd = 5.0
        reg = _build_slash_registry()
        reg.lookup("/budget").handler(fake_ctx, ["0"], "/budget 0")
        assert fake_ctx.budget_usd is None

    def test_budget_rejects_bad_input(self, fake_ctx, capsys):
        from voss.harness.cli import _build_slash_registry

        reg = _build_slash_registry()
        reg.lookup("/budget").handler(fake_ctx, ["abc"], "/budget abc")
        err = capsys.readouterr().err
        assert "usage" in err.lower()

    def test_cost_by_model_groups_by_session_model(self, fake_ctx, capsys):
        from voss.harness.cli import _build_slash_registry

        reg = _build_slash_registry()
        reg.lookup("/cost").handler(fake_ctx, ["--by-model"], "/cost --by-model")
        out = capsys.readouterr().out
        assert "claude-sonnet-4-7" in out
        assert "$0.0200" in out  # 0.012 + 0.008

    def test_cost_by_tool_is_honest_stub(self, fake_ctx, capsys):
        from voss.harness.cli import _build_slash_registry

        reg = _build_slash_registry()
        reg.lookup("/cost").handler(fake_ctx, ["--by-tool"], "/cost --by-tool")
        out = capsys.readouterr().out
        assert "T4" in out  # references the phase that closes this gap

    def test_discard_dry_run_lists_files(self, fake_ctx, capsys):
        from voss.harness.cli import _build_slash_registry

        reg = _build_slash_registry()
        reg.lookup("/discard").handler(fake_ctx, [], "/discard")
        out = capsys.readouterr().out
        assert "voss/harness/cli.py" in out
        assert "--confirm" in out

    def test_discard_no_runs_is_no_op(self, fake_ctx, capsys):
        from voss.harness.cli import _build_slash_registry

        fake_ctx.record.runs = []
        reg = _build_slash_registry()
        reg.lookup("/discard").handler(fake_ctx, [], "/discard")
        out = capsys.readouterr().out
        assert "no runs" in out

    def test_apply_explains_v01_semantics(self, fake_ctx, capsys):
        from voss.harness.cli import _build_slash_registry

        reg = _build_slash_registry()
        reg.lookup("/apply").handler(fake_ctx, [], "/apply")
        out = capsys.readouterr().out
        assert "immediately" in out.lower()
