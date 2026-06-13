"""R8: the auth-aware /model slash command — curated lists per subscription
auth, fuzzy selection precedence, persistence, and the TUI picker/fallback
dispatch (faked app; the modal itself is pilot-tested in tests/harness/tui)."""
from __future__ import annotations

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
    return SimpleNamespace(provider=provider, renderer=renderer)


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
    assert [m.id for m in match("claude", "claude-opus")] == ["claude-opus-4-8"]
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

    assert f"claude-sonnet-4-5 {glyphs.CHECK}" in out
    assert "select: /model <id>" in out


def test_plain_bare_codex_lists_gpt5(env, capsys) -> None:
    configure(default_model="gpt-5.5")
    registry = cli._build_slash_registry()
    registry.dispatch(_ctx(_codex_provider()), "/model")
    out = capsys.readouterr().out
    assert "1. gpt-5.5" in out
    assert "2. gpt-5.4" in out
    assert "3. gpt-5.4-mini" in out
    assert "4. gpt-5.3-codex-spark" in out


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
    assert get_config().default_model == "claude-opus-4-8"
    cfg = harness_config.load_harness_config()
    assert cfg.get("preferred_model") == "claude-opus-4-8"


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


def test_codex_substring_pick(env) -> None:
    configure(default_model="gpt-5.5")
    registry = cli._build_slash_registry()
    registry.dispatch(_ctx(_codex_provider()), "/model mini")
    assert get_config().default_model == "gpt-5.4-mini"


# ---------------------------------------------------------------------------
# TUI dispatch: auth picker vs catalog fallback
# ---------------------------------------------------------------------------


def test_tui_claude_opens_auth_picker_and_pick_applies(env) -> None:
    from voss.harness.tui.widgets.auth_model_picker_modal import (
        AuthModelPickerModal,
    )

    app = _FakeTUIApp()
    registry = cli._build_slash_registry()
    registry.dispatch(_ctx(ClaudeAgentProvider(), app=app), "/model")
    assert len(app.pushed) == 1
    screen, callback = app.pushed[0]
    assert isinstance(screen, AuthModelPickerModal)
    # simulate the user picking opus in the modal
    opus = SUBSCRIPTION_MODELS["claude"][1]
    callback(opus)
    assert get_config().default_model == "claude-opus-4-8"
    assert app.model == "claude-opus-4-8"  # live status source updated
    cfg = harness_config.load_harness_config()
    assert cfg.get("preferred_model") == "claude-opus-4-8"
    # esc → None must be a no-op
    callback(None)
    assert get_config().default_model == "claude-opus-4-8"


def test_tui_api_key_auth_falls_back_to_catalog_modal(env, monkeypatch) -> None:
    from voss.harness.tui.widgets.model_picker_modal import ModelPickerModal

    raw = {
        "ollama-cloud": {
            "id": "ollama-cloud",
            "name": "Ollama Cloud",
            "env": ["OLLAMA_API_KEY"],
            "api": "https://ollama.com/v1",
            "models": {
                "gemma3:27b": {
                    "id": "gemma3:27b", "name": "gemma3:27b",
                    "tool_call": False, "cost": None,
                    "limit": {"context": 131072},
                }
            },
        }
    }
    monkeypatch.setattr(mc, "load_catalog", lambda **_kw: mc.parse_catalog(raw))
    app = _FakeTUIApp()
    registry = cli._build_slash_registry()
    registry.dispatch(_ctx(object(), app=app), "/model")
    assert len(app.pushed) == 1
    screen, _callback = app.pushed[0]
    assert isinstance(screen, ModelPickerModal)
