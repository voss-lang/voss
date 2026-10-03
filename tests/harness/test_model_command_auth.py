"""R8: the auth-aware /model slash command — curated lists per subscription
auth, fuzzy selection precedence, persistence, and the TUI picker/fallback
dispatch (faked app; the modal itself is pilot-tested in tests/harness/tui)."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from voss.harness import auth as auth_mod
from voss.harness import cli
from voss.harness import config as harness_config
from voss.harness import model_catalog as mc
from voss.harness.claude_agent_provider import ClaudeAgentProvider
from voss.harness.subscription_models import (
    SUBSCRIPTION_MODELS,
    detect_auth_mode,
    match,
)
from voss_runtime._config import configure, get_config


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    # Bare /model in plain CLI probes cred files; keep it hermetic.
    monkeypatch.setattr(auth_mod, "load_anthropic_oauth", lambda: None)
    monkeypatch.setattr(auth_mod, "load_codex", lambda: None)
    configure(default_model="claude-sonnet-4-5")
    return tmp_path


def _codex_provider():
    from voss.harness.auth import CodexCreds
    from voss.harness.providers import OpenAIOAuthProvider

    creds = CodexCreds(
        api_key=None, access_token="t", refresh_token="r",
        account_id="a", auth_mode="ChatGPT",
    )
    return OpenAIOAuthProvider(creds)


class _FakeTUIApp:
    """Stands in for the live app: cli only checks the class NAME."""

    def __init__(self) -> None:
        self.pushed: list = []
        self.model = ""

    def push_screen(self, screen, callback=None) -> None:
        self.pushed.append((screen, callback))

    def query_one(self, *a, **kw):  # no widgets mounted in tests
        raise RuntimeError("no widget tree")


_FakeTUIApp.__name__ = "VossTUIApp"


def _ctx(provider, app=None):
    renderer = SimpleNamespace(app=app) if app is not None else None
    return SimpleNamespace(
        provider=provider,
        renderer=renderer,
        record=SimpleNamespace(model=get_config().default_model),
    )


def _codex_oauth_resolution():
    from voss.harness.auth import CodexCreds

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


def _catalog_raw():
    return {
        "anthropic": {
            "id": "anthropic",
            "name": "Anthropic",
            "env": ["ANTHROPIC_API_KEY"],
            "api": None,
            "models": {
                "claude-sonnet-4-5": {
                    "id": "claude-sonnet-4-5",
                    "name": "Claude Sonnet 4.5",
                    "tool_call": True,
                    "cost": {"input": 3, "output": 15},
                    "limit": {"context": 200000},
                },
            },
        },
        "opencode": {
            "id": "opencode",
            "name": "OpenCode Zen",
            "env": ["OPENCODE_API_KEY"],
            "api": "https://opencode.ai/zen/v1",
            "models": {
                "mimo-v2-flash-free": {
                    "id": "mimo-v2-flash-free",
                    "name": "MiMo V2 Flash Free",
                    "tool_call": True,
                    "cost": {"input": 0, "output": 0},
                    "limit": {"context": 131072},
                },
            },
        },
        "ollama-cloud": {
            "id": "ollama-cloud",
            "name": "Ollama Cloud",
            "env": ["OLLAMA_API_KEY"],
            "api": "https://ollama.com/v1",
            "models": {
                "gemma3:27b": {
                    "id": "gemma3:27b",
                    "name": "gemma3:27b",
                    "tool_call": False,
                    "cost": None,
                    "limit": {"context": 131072},
                }
            },
        },
    }


# ---------------------------------------------------------------------------
# detection + matching helpers
# ---------------------------------------------------------------------------


def test_detect_auth_mode_claude_codex_and_none() -> None:
    assert detect_auth_mode(ClaudeAgentProvider()) == "claude"
    assert detect_auth_mode(_codex_provider()) == "codex"
    assert detect_auth_mode(object()) is None
    assert detect_auth_mode(None) is None


def test_match_precedence_exact_then_prefix_then_substring() -> None:
    # exact id wins even though it is also a prefix of nothing else
    assert [m.id for m in match("codex", "gpt-5.5")] == ["gpt-5.5"]
    # unique prefix
    assert [m.id for m in match("claude", "claude-opus")] == ["claude-opus-5-5"]
    # ambiguous prefix returns all candidates
    assert len(match("claude", "claude")) == len(SUBSCRIPTION_MODELS["claude"])
    # substring
    assert [m.id for m in match("claude", "haiku")] == ["claude-haiku-4-5"]
    # no match
    assert match("claude", "gemma") == []


# ---------------------------------------------------------------------------
# plain-CLI bare /model
# ---------------------------------------------------------------------------


def test_plain_bare_lists_curated_numbered_with_active_marked(env, capsys) -> None:
    configure(default_model="claude-sonnet-5-5")
    registry = cli._build_slash_registry()
    handled = registry.dispatch(_ctx(ClaudeAgentProvider()), "/model")
    assert handled is True
    out = capsys.readouterr().out
    # availability lines kept
    assert "Claude:" in out and "Codex:" in out
    # numbered curated list, active marked, select hint
    for i, m in enumerate(SUBSCRIPTION_MODELS["claude"], 1):
        assert f"{i}. {m.id}" in out
    from voss.harness.tui import glyphs

    assert f"claude-sonnet-5-5 {glyphs.CHECK}" in out
    assert "select: /model <id>" in out


def test_plain_bare_codex_lists_current_models_before_older_models(env, capsys) -> None:
    configure(default_model="gpt-5.5")
    registry = cli._build_slash_registry()
    registry.dispatch(_ctx(_codex_provider()), "/model")
    out = capsys.readouterr().out
    assert "1. gpt-6-astra" in out
    assert "2. gpt-6.1-sol" in out
    assert "3. gpt-6-luna" in out
    assert "4. gpt-5.5" in out


def test_plain_bare_no_subscription_keeps_old_dump(env, capsys) -> None:
    registry = cli._build_slash_registry()
    registry.dispatch(_ctx(object()), "/model")
    out = capsys.readouterr().out
    assert "active: claude-sonnet-4-5" in out
    assert "subscription models" not in out


# ---------------------------------------------------------------------------
# /model <arg> selection precedence + persistence
# ---------------------------------------------------------------------------


def test_unambiguous_prefix_applies_and_persists(env) -> None:
    registry = cli._build_slash_registry()
    registry.dispatch(_ctx(ClaudeAgentProvider()), "/model claude-opus")
    assert get_config().default_model == "claude-opus-5-5"
    cfg = harness_config.load_harness_config()
    assert cfg.get("preferred_model") == "claude-opus-5-5"


def test_ambiguous_query_does_not_change_model(env, capsys) -> None:
    registry = cli._build_slash_registry()
    registry.dispatch(_ctx(ClaudeAgentProvider()), "/model claude")
    assert get_config().default_model == "claude-sonnet-4-5"
    err = capsys.readouterr().err
    assert "matches" in err


def test_unknown_id_falls_back_to_raw_set(env) -> None:
    registry = cli._build_slash_registry()
    registry.dispatch(_ctx(ClaudeAgentProvider()), "/model my-custom-model")
    assert get_config().default_model == "my-custom-model"
    cfg = harness_config.load_harness_config()
    assert cfg.get("preferred_model") == "my-custom-model"


@pytest.mark.parametrize("query,model", [
    ("astra", "gpt-6-astra"),
    ("sol", "gpt-6.1-sol"),
    ("luna", "gpt-6-luna"),
])
def test_codex_substring_pick(env, query, model) -> None:
    configure(default_model="gpt-5.5")
    registry = cli._build_slash_registry()
    registry.dispatch(_ctx(_codex_provider()), f"/model {query}")
    assert get_config().default_model == model
    assert harness_config.load_harness_config().get("preferred_model") == model


@pytest.mark.parametrize("query,model", [
    ("gpt-6.1-sol", "gpt-6.1-sol"),
    ("astra", "gpt-6-astra"),
])
def test_typed_codex_model_switches_from_claude(env, monkeypatch, query, model) -> None:
    from voss.harness.providers import OpenAIOAuthProvider

    monkeypatch.setattr(auth_mod, "resolve", lambda pref: _codex_oauth_resolution())
    monkeypatch.setattr(cli, "_codex_default_model", lambda: "gpt-6-astra")
    app = _FakeTUIApp()
    ctx = _ctx(ClaudeAgentProvider(), app=app)

    cli._build_slash_registry().dispatch(ctx, f"/model {query}")

    assert isinstance(ctx.provider, OpenAIOAuthProvider)
    assert get_config().default_model == model
    assert app.provider == "Codex"
    assert app.model == model
    cfg = harness_config.load_harness_config()
    assert cfg["auth"] == "codex"
    assert cfg["preferred_model"] == model


def test_typed_claude_model_switches_from_codex(env, monkeypatch) -> None:
    configure(default_model="gpt-6.1-sol")
    monkeypatch.setattr(auth_mod, "resolve", lambda pref: SimpleNamespace(
        source="claude-agent", cli_path=Path("/opt/bin/claude"),
    ))
    app = _FakeTUIApp()
    ctx = _ctx(_codex_provider(), app=app)

    cli._build_slash_registry().dispatch(ctx, "/model claude-opus-5-5")

    assert isinstance(ctx.provider, ClaudeAgentProvider)
    assert get_config().default_model == "claude-opus-5-5"
    assert app.provider == "Anthropic"
    assert app.model == "claude-opus-5-5"
    cfg = harness_config.load_harness_config()
    assert cfg["auth"] == "claude"
    assert cfg["preferred_model"] == "claude-opus-5-5"


def test_typed_model_provider_failure_preserves_selection(env, monkeypatch, capsys) -> None:
    from dataclasses import replace

    harness_config.set_preferred_model("claude-sonnet-5-5")
    harness_config.set_preferred_auth("claude")
    configure(default_model="claude-sonnet-5-5")
    resolution = _codex_oauth_resolution()
    resolution.codex_oauth = replace(resolution.codex_oauth, auth_mode=42)
    monkeypatch.setattr(auth_mod, "resolve", lambda pref: resolution)
    provider = ClaudeAgentProvider()
    app = _FakeTUIApp()
    app.model = "claude-sonnet-5-5"
    ctx = _ctx(provider, app=app)

    cli._build_slash_registry().dispatch(ctx, "/model gpt-6.1-sol")

    assert ctx.provider is provider
    assert get_config().default_model == "claude-sonnet-5-5"
    assert app.model == ctx.record.model == "claude-sonnet-5-5"
    cfg = harness_config.load_harness_config()
    assert cfg["auth"] == "claude"
    assert cfg["preferred_model"] == "claude-sonnet-5-5"
    assert "model switch failed" in capsys.readouterr().err


@pytest.mark.parametrize("source", ["none", "codex"])
def test_typed_cross_provider_model_requires_subscription(env, monkeypatch, capsys, source) -> None:
    harness_config.set_preferred_model("claude-sonnet-5-5")
    harness_config.set_preferred_auth("claude")
    configure(default_model="claude-sonnet-5-5")
    monkeypatch.setattr(auth_mod, "resolve", lambda pref: SimpleNamespace(source=source))
    provider = ClaudeAgentProvider()
    ctx = _ctx(provider)

    cli._build_slash_registry().dispatch(ctx, "/model gpt-6.1-sol")

    assert ctx.provider is provider
    assert get_config().default_model == "claude-sonnet-5-5"
    cfg = harness_config.load_harness_config()
    assert cfg["auth"] == "claude"
    assert cfg["preferred_model"] == "claude-sonnet-5-5"
    assert "codex login" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# TUI dispatch: auth picker vs catalog fallback
# ---------------------------------------------------------------------------


def test_tui_model_auth_opens_auth_picker_and_pick_applies(env) -> None:
    from voss.harness.tui.widgets.auth_model_picker_modal import (
        AuthModelPickerModal,
    )

    app = _FakeTUIApp()
    registry = cli._build_slash_registry()
    registry.dispatch(_ctx(ClaudeAgentProvider(), app=app), "/model auth")
    assert len(app.pushed) == 1
    screen, callback = app.pushed[0]
    assert isinstance(screen, AuthModelPickerModal)
    # simulate the user picking opus in the modal
    opus = SUBSCRIPTION_MODELS["claude"][1]
    callback(opus)
    assert get_config().default_model == "claude-opus-5-5"
    assert app.model == "claude-opus-5-5"  # live status source updated
    cfg = harness_config.load_harness_config()
    assert cfg.get("preferred_model") == "claude-opus-5-5"
    # esc → None must be a no-op
    callback(None)
    assert get_config().default_model == "claude-opus-5-5"


def test_tui_bare_model_opens_catalog_under_codex_auth(env, monkeypatch) -> None:
    from voss.harness.tui.widgets.model_picker_modal import ModelPickerModal

    monkeypatch.setattr(mc, "load_catalog", lambda **_kw: mc.parse_catalog(_catalog_raw()))
    app = _FakeTUIApp()
    registry = cli._build_slash_registry()
    registry.dispatch(_ctx(_codex_provider(), app=app), "/model")
    assert len(app.pushed) == 1
    screen, _callback = app.pushed[0]
    assert isinstance(screen, ModelPickerModal)
    group_ids = {g.id for g in screen._groups}
    assert {"anthropic", "opencode", "ollama-cloud"} <= group_ids


def test_tui_catalog_anthropic_pick_switches_from_codex_to_claude(
    env, monkeypatch
) -> None:
    from voss.harness.claude_agent_provider import ClaudeAgentProvider

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(mc, "load_catalog", lambda **_kw: mc.parse_catalog(_catalog_raw()))
    monkeypatch.setattr(
        "voss.harness.model_router.resolve_key",
        lambda _entry, **_kw: None,
    )
    monkeypatch.setattr(
        "voss.harness.model_router.auth.resolve",
        lambda pref: SimpleNamespace(source="claude-agent", cli_path=Path("/opt/bin/claude")),
    )

    app = _FakeTUIApp()
    ctx = _ctx(_codex_provider(), app=app)
    registry = cli._build_slash_registry()
    registry.dispatch(ctx, "/model")
    screen, callback = app.pushed[0]
    entry = next(g.models[0] for g in screen._groups if g.id == "anthropic")

    callback(entry)

    assert isinstance(ctx.provider, ClaudeAgentProvider)
    assert ctx.provider.cli_path == "/opt/bin/claude"
    assert app.provider == "Anthropic"
    assert app.model == "claude-sonnet-4-5"
    cfg = harness_config.load_harness_config()
    assert cfg.get("auth") == "claude"
    assert cfg.get("preferred_model") == "claude-sonnet-4-5"
    assert "preferred_provider" not in cfg


def test_auth_slash_switches_current_session_and_persists(env, monkeypatch) -> None:
    from voss.harness.providers import OpenAIOAuthProvider

    configure(default_model="claude-sonnet-4-5")
    monkeypatch.setattr(cli.auth_mod, "resolve", lambda pref: _codex_oauth_resolution())
    monkeypatch.setattr(cli, "_codex_default_model", lambda: "gpt-5.5")

    app = _FakeTUIApp()
    app.provider = "Anthropic"
    ctx = _ctx(ClaudeAgentProvider(), app=app)
    registry = cli._build_slash_registry()

    registry.dispatch(ctx, "/auth codex")

    assert isinstance(ctx.provider, OpenAIOAuthProvider)
    assert get_config().default_model == "gpt-5.5"
    assert ctx.record.model == "gpt-5.5"
    assert app.provider == "Codex"
    assert app.model == "gpt-5.5"
    cfg = harness_config.load_harness_config()
    assert cfg.get("auth") == "codex"


def test_tui_catalog_openai_pick_keeps_subscription_and_labels_codex(env, monkeypatch) -> None:
    from voss.harness.providers import OpenAIOAuthProvider

    monkeypatch.setattr(auth_mod, "load_codex", lambda: _codex_oauth_resolution().codex_oauth)
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setattr(mc, "load_catalog", lambda **_kw: mc.parse_catalog({"openai": {
        "name": "OpenAI", "env": ["OPENAI_API_KEY"],
        "models": {"gpt-6.1-sol": {"id": "gpt-6.1-sol", "name": "GPT-6.1 Sol"}},
    }}))
    app = _FakeTUIApp()
    ctx = _ctx(_codex_provider(), app=app)
    cli._build_slash_registry().dispatch(ctx, "/model")
    screen, callback = app.pushed[0]

    callback(screen._groups[0].models[0])

    assert isinstance(ctx.provider, OpenAIOAuthProvider)
    assert app.provider == "Codex"
    assert app.model == "gpt-6.1-sol"
    cfg = harness_config.load_harness_config()
    assert cfg["auth"] == "codex"
    assert cfg["preferred_model"] == "gpt-6.1-sol"
    assert "preferred_provider" not in cfg


def test_tui_api_key_auth_falls_back_to_catalog_modal(env, monkeypatch) -> None:
    from voss.harness.tui.widgets.model_picker_modal import ModelPickerModal

    monkeypatch.setattr(mc, "load_catalog", lambda **_kw: mc.parse_catalog(_catalog_raw()))
    app = _FakeTUIApp()
    registry = cli._build_slash_registry()
    registry.dispatch(_ctx(object(), app=app), "/model")
    assert len(app.pushed) == 1
    screen, _callback = app.pushed[0]
    assert isinstance(screen, ModelPickerModal)
