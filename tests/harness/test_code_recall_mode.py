import pytest

from voss.harness import config as harness_config
from voss.harness import judgments as j
from voss_runtime.judgments import JudgmentLedger


@pytest.fixture(autouse=True)
def isolated_judgments(monkeypatch):
    monkeypatch.delenv("VOSS_JUDGMENTS", raising=False)
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setattr(j.auth, "load_provider_key", lambda env_key: None)


def _write_project(root, text):
    path = root / ".voss" / "config.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.mark.parametrize("mode", ["shadow", "active", "off"])
def test_enabled_project_mode(tmp_path, mode):
    _write_project(tmp_path, f"judgments:\n  enabled: true\n  code_recall: {mode}\n")
    assert j.code_recall_mode(tmp_path) == mode


def test_kill_switch_wins(monkeypatch, tmp_path):
    _write_project(tmp_path, "judgments:\n  enabled: true\n  code_recall: active\n")
    monkeypatch.setenv("VOSS_JUDGMENTS", "off")
    assert j.code_recall_mode(tmp_path) == "off"


@pytest.mark.parametrize("enabled", ["  enabled: false\n", ""])
def test_not_enabled_is_off(tmp_path, enabled):
    _write_project(tmp_path, f"judgments:\n{enabled}  code_recall: active\n")
    assert j.code_recall_mode(tmp_path) == "off"


def test_missing_key_is_off(monkeypatch, tmp_path):
    _write_project(tmp_path, "judgments:\n  enabled: true\n  code_recall: active\n")
    monkeypatch.delenv("TYPESAFE_API_KEY")
    assert j.code_recall_mode(tmp_path) == "off"


@pytest.mark.parametrize("value", ["ACTIVE", "on", "true", "1", "null", "[active]"])
def test_non_literal_values_are_off(tmp_path, value):
    _write_project(tmp_path, f"judgments:\n  enabled: true\n  code_recall: {value}\n")
    assert j.code_recall_mode(tmp_path) == "off"


@pytest.mark.parametrize("text", ["judgments:\n  enabled: true\n", "judgments: [enabled: true\n"])
def test_missing_or_malformed_is_off(tmp_path, text):
    _write_project(tmp_path, text)
    assert j.code_recall_mode(tmp_path) == "off"


def test_missing_file_is_off(tmp_path):
    assert j.code_recall_mode(tmp_path) == "off"


def test_global_toml_cannot_enable(tmp_path):
    path = harness_config.config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('[judgments]\nenabled = true\ncode_recall = "active"\n')
    assert j.code_recall_mode(tmp_path) == "off"


def test_make_client_defaults():
    client = j.make_client("k")
    assert client.timeout_ms == harness_config.get_judgments_config()["timeout_ms"]
    assert isinstance(client.ledger, JudgmentLedger)
    assert client.ledger is not j.make_client("k").ledger


def test_make_client_overrides():
    ledger = JudgmentLedger(4, 0.01)
    client = j.make_client("k", timeout_ms=1500, ledger=ledger)
    assert client.timeout_ms == 1500
    assert client.ledger is ledger
