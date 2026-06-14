"""_resolve_auth_or_die claude-agent branch — provider build + model snap."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from voss.harness import cli
from voss.harness.auth import CodexCreds
from voss.harness.claude_agent_provider import ClaudeAgentProvider
from voss.harness.providers import OpenAIOAuthProvider
from voss_runtime import configure, get_config


@pytest.fixture
def xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def restore_default_model():
    before = get_config().default_model
    yield
    configure(default_model=before)


def _claude_agent_resolution():
    return SimpleNamespace(
        source="claude-agent",
        detail="claude CLI + subscription creds (max)",
        anthropic_oauth=object(),
        codex_oauth=None,
        openai_api_key=None,
        cli_path=Path("/opt/bin/claude"),
    )


def _codex_oauth_resolution():
    return SimpleNamespace(
        source="codex-oauth",
        detail="~/.codex/auth.json (ChatGPT, OAuth)",
        anthropic_oauth=None,
        codex_oauth=CodexCreds(
            api_key=None,
            access_token="access",
            refresh_token="refresh",
            account_id="acct",
            auth_mode="ChatGPT",
        ),
        openai_api_key=None,
        cli_path=None,
    )


def _patch_resolve(monkeypatch):
    monkeypatch.setattr(
        cli.auth_mod, "resolve", lambda pref: _claude_agent_resolution()
    )


def test_claude_agent_builds_provider_with_cli_path(
    xdg, monkeypatch, restore_default_model, capsys
) -> None:
    _patch_resolve(monkeypatch)
    res, provider = cli._resolve_auth_or_die("claude")
    assert res.source == "claude-agent"
    assert isinstance(provider, ClaudeAgentProvider)
    assert provider.cli_path == "/opt/bin/claude"
    err = capsys.readouterr().err
    assert "deprecated" not in err
    assert "claude-agent" in err


def test_resolve_auth_can_suppress_subscription_notice(
    xdg, monkeypatch, restore_default_model, capsys
) -> None:
    monkeypatch.setattr(cli.auth_mod, "resolve", lambda pref: _codex_oauth_resolution())
    configure(default_model="gpt-5.5")

    res, provider = cli._resolve_auth_or_die("codex", announce=False)

    assert res.source == "codex-oauth"
    assert isinstance(provider, OpenAIOAuthProvider)
    err = capsys.readouterr().err
    assert "codex-oauth" not in err
    assert "ChatGPT subscription" not in err


def test_chat_cmd_suppresses_auth_notice_before_repl(monkeypatch, tmp_path) -> None:
    captured = {}
    fake_res = SimpleNamespace(source="codex-oauth", detail="chatgpt oauth")
    fake_provider = object()

    def fake_resolve(_pref, *, announce=True):
        captured["announce"] = announce
        return fake_res, fake_provider

    def fake_repl(**kwargs):
        captured["provider"] = kwargs["provider"]
        captured["auth_detail"] = kwargs["auth_detail"]

    monkeypatch.setattr(cli, "_resolve_default_model", lambda _model: None)
    monkeypatch.setattr(cli, "_resolve_auth_or_die", fake_resolve)
    monkeypatch.setattr(cli, "_apply_boot_model", lambda provider, **_kwargs: provider)
    monkeypatch.setattr(cli, "_emit_harness_boot_telemetry", lambda *_args: None)
    monkeypatch.setattr(cli, "_run_repl", fake_repl)
    monkeypatch.setattr(
        cli.session_store.SessionRecord,
        "new",
        lambda **_kwargs: SimpleNamespace(id="session", turns=[], runs=[]),
    )
    monkeypatch.setattr(
        cli,
        "get_config",
        lambda: SimpleNamespace(default_model="gpt-5.5"),
    )

    cli.chat_cmd.callback(
        model=None,
        cwd_str=str(tmp_path),
        json_mode=False,
        plain=False,
        no_unicode=False,
        mode="plan",
        allow_net=None,
        auth_pref="codex",
        keep_logs=False,
    )

    assert captured["announce"] is False
    assert captured["provider"] is fake_provider
    assert captured["auth_detail"] == "codex-oauth — chatgpt oauth"


def test_claude_agent_snaps_non_claude_default_model(
    xdg, monkeypatch, restore_default_model
) -> None:
    _patch_resolve(monkeypatch)
    configure(default_model="gpt-4o")
    cli._resolve_auth_or_die("claude")
    assert get_config().default_model == "claude-sonnet-4-5"


def test_claude_agent_leaves_explicit_claude_model_alone(
    xdg, monkeypatch, restore_default_model
) -> None:
    _patch_resolve(monkeypatch)
    configure(default_model="claude-opus-4-5")
    cli._resolve_auth_or_die("claude")
    assert get_config().default_model == "claude-opus-4-5"


def test_codex_oauth_uses_codex_cli_config_default(
    xdg, monkeypatch, tmp_path, restore_default_model
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    p = tmp_path / ".codex" / "config.toml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('model = "gpt-5.4"\n')
    monkeypatch.setattr(cli.auth_mod, "resolve", lambda pref: _codex_oauth_resolution())
    configure(default_model="claude-sonnet-4-5")

    res, provider = cli._resolve_auth_or_die("codex")

    assert res.source == "codex-oauth"
    assert isinstance(provider, OpenAIOAuthProvider)
    assert get_config().default_model == "gpt-5.4"
