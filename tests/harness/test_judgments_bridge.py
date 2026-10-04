import os

from click.testing import CliRunner
import pytest

from voss.harness import auth
from voss.harness import judgments as j
from voss.harness.cli import _bootstrap_runtime_config
from voss.harness.config import JUDGMENTS_DEFAULTS
from voss_runtime import RuntimeConfig, get_config, reset_config


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("VOSS_JUDGMENTS", raising=False)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    yield
    os.environ.pop("TYPESAFE_API_KEY", None)
    reset_config()


def keychain(monkeypatch, value):
    calls = []

    def load(env_key):
        calls.append(env_key)
        return value

    monkeypatch.setattr(auth, "load_provider_key", load)
    return calls


def test_keychain_only_key_is_copied_into_env(monkeypatch):
    calls = keychain(monkeypatch, "kc-sentinel")
    j.bridge_judgments_env()
    assert calls == ["TYPESAFE_API_KEY"]
    assert os.environ["TYPESAFE_API_KEY"] == "kc-sentinel"


def test_env_key_wins_without_keychain_lookup(monkeypatch):
    calls = keychain(monkeypatch, "kc-sentinel")
    monkeypatch.setenv("TYPESAFE_API_KEY", "env-sentinel")
    j.bridge_judgments_env()
    assert calls == []
    assert os.environ["TYPESAFE_API_KEY"] == "env-sentinel"


def test_kill_switch_skips_keychain(monkeypatch):
    calls = keychain(monkeypatch, "kc-sentinel")
    monkeypatch.setenv("VOSS_JUDGMENTS", "off")
    j.bridge_judgments_env()
    assert calls == []
    assert "TYPESAFE_API_KEY" not in os.environ


def test_missing_keychain_key_leaves_env_unset(monkeypatch, capsys):
    keychain(monkeypatch, None)
    j.bridge_judgments_env()
    assert "TYPESAFE_API_KEY" not in os.environ
    assert capsys.readouterr() == ("", "")


def test_voss_cli_startup_bridges_once_without_leaking_key(monkeypatch, tmp_path):
    from voss.cli import main

    calls = []
    monkeypatch.setattr(j, "bridge_judgments_env", lambda: calls.append(1))
    monkeypatch.setenv("TYPESAFE_API_KEY", "env-sentinel")
    source = tmp_path / "ok.voss"
    source.write_text("let x = 1\n")
    result = CliRunner().invoke(main, ["check", str(source)])
    assert result.exit_code == 0, result.output
    assert calls == [1]
    assert "env-sentinel" not in result.output


def test_run_server_bridges_before_create_app(monkeypatch):
    from voss.harness.server import app, serve

    order = []
    monkeypatch.setattr(j, "bridge_judgments_env", lambda: order.append("bridge"))

    def create_app(token):
        order.append("create_app")
        raise RuntimeError("stop")

    monkeypatch.setattr(app, "create_app", create_app)
    with pytest.raises(RuntimeError, match="stop"):
        serve.run_server(token="t")
    assert order == ["bridge", "create_app"]


def test_boot_pushes_judgments_limits_into_runtime_config(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    (tmp_path / "voss").mkdir()
    (tmp_path / "voss" / "config.toml").write_text("[judgments]\nmax_calls_per_turn = 2\nmax_cost_usd = 0.005\n")
    _bootstrap_runtime_config()
    cfg = get_config()
    assert cfg.judgments_max_calls_per_turn == 2
    assert cfg.judgments_max_cost_usd == 0.005
    assert cfg.judgments_model == JUDGMENTS_DEFAULTS["model"]


def test_runtime_config_defaults_match_harness_defaults():
    cfg = RuntimeConfig()
    assert {key: getattr(cfg, f"judgments_{key}") for key in JUDGMENTS_DEFAULTS} == JUDGMENTS_DEFAULTS


def test_bridged_key_never_reaches_runtime_config(monkeypatch):
    keychain(monkeypatch, "kc-sentinel")
    j.bridge_judgments_env()
    _bootstrap_runtime_config()
    assert os.environ["TYPESAFE_API_KEY"] == "kc-sentinel"
    assert "kc-sentinel" not in repr(get_config())
