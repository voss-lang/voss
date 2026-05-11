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
