"""Persisted [harness] auth default — honored when no explicit --auth."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from voss.harness import cli
from voss.harness import config as hconfig


@pytest.fixture
def xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return tmp_path


def _fake_resolution():
    return SimpleNamespace(
        source="env-openai", detail="x", openai_api_key="k",
        anthropic_oauth=None, codex_oauth=None,
    )


def _capture_resolve(monkeypatch):
    captured = {}

    def fake(pref):
        captured["pref"] = pref
        return _fake_resolution()

    monkeypatch.setattr(cli.auth_mod, "resolve", fake)
    return captured


def test_persisted_auth_used_when_auto(xdg, monkeypatch):
    hconfig.set_preferred_auth("codex")
    captured = _capture_resolve(monkeypatch)
    cli._resolve_auth_or_die("auto")
    assert captured["pref"] == "codex"


def test_explicit_auth_overrides_persisted(xdg, monkeypatch):
    hconfig.set_preferred_auth("codex")
    captured = _capture_resolve(monkeypatch)
    cli._resolve_auth_or_die("claude")  # explicit
    assert captured["pref"] == "claude"


def test_no_persisted_stays_auto(xdg, monkeypatch):
    captured = _capture_resolve(monkeypatch)
    cli._resolve_auth_or_die("auto")
    assert captured["pref"] == "auto"


def test_invalid_persisted_ignored(xdg, monkeypatch):
    hconfig.set_preferred_auth("bogus")
    captured = _capture_resolve(monkeypatch)
    cli._resolve_auth_or_die("auto")
    assert captured["pref"] == "auto"


def test_auth_slash_command_persists(xdg):
    registry = cli._build_slash_registry()
    ctx = SimpleNamespace(record=SimpleNamespace(model=None))
    registry.dispatch(ctx, "/auth codex")
    assert hconfig.load_harness_config().get("auth") == "codex"


def test_auth_slash_rejects_invalid(xdg):
    registry = cli._build_slash_registry()
    ctx = SimpleNamespace()
    registry.dispatch(ctx, "/auth nonsense")
    assert hconfig.load_harness_config().get("auth") is None
