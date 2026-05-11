"""D-09 resolution order: persisted preferred_model overrides hard-coded default.

Catches the B3 regression where _run_repl's `if persisted and not record.model:`
guard was always False because callers built SessionRecord with cfg.default_model
already populated. The fix moves the lookup into the command (do/chat/edit)
BEFORE SessionRecord.new(...). These tests pin that behavior.
"""
from __future__ import annotations

import pytest

from voss.harness import config as harness_config
from voss.harness.cli import _resolve_default_model
from voss_runtime import configure, get_config


@pytest.fixture
def isolated_xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    yield tmp_path
    # Restore a sane default model after each test so other suites aren't
    # poisoned by configure() side effects.
    configure(default_model="claude-sonnet-4-20250514")


class TestResolutionOrder:
    def test_persisted_wins_when_no_explicit(self, isolated_xdg):
        harness_config.set_preferred_model("claude-opus-4-7")
        configure(default_model="some-default")  # baseline distinct value

        _resolve_default_model(None)

        assert get_config().default_model == "claude-opus-4-7"

    def test_explicit_overrides_persisted(self, isolated_xdg):
        harness_config.set_preferred_model("claude-opus-4-7")
        _resolve_default_model("gpt-4o")
        assert get_config().default_model == "gpt-4o"

    def test_no_persisted_no_explicit_is_noop(self, isolated_xdg):
        configure(default_model="baseline-model")
        prior = get_config().default_model

        _resolve_default_model(None)

        assert get_config().default_model == prior
