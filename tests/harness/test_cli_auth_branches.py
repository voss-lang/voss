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
