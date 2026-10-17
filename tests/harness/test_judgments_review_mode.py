import pytest

from voss.harness import config as harness_config
from voss.harness import judgments as j


@pytest.fixture(autouse=True)
def isolated_judgments(monkeypatch):
    monkeypatch.delenv("VOSS_JUDGMENTS", raising=False)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(j.auth, "load_provider_key", lambda env_key: None)


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")


def _write_project(root, text):
    path = root / ".voss" / "config.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_shadow_when_enabled_with_key(tmp_path, key):
    _write_project(tmp_path, "judgments:\n  enabled: true\n  review: shadow\n")
    assert j.review_mode(tmp_path) == "shadow"


def test_shadow_with_keychain_key(monkeypatch, tmp_path):
    monkeypatch.setattr(j.auth, "load_provider_key", lambda env_key: "kc-key")
    _write_project(tmp_path, "judgments:\n  enabled: true\n  review: shadow\n")
    assert j.review_mode(tmp_path) == "shadow"


@pytest.mark.parametrize("value", ["off", "active", "ACTIVE", "on", "true", "1", "null", "[shadow]"])
def test_non_shadow_values_are_off(tmp_path, key, value):
    _write_project(tmp_path, f"judgments:\n  enabled: true\n  review: {value}\n")
    assert j.review_mode(tmp_path) == "off"


def test_missing_review_is_off(tmp_path, key):
    _write_project(tmp_path, "judgments:\n  enabled: true\n")
    assert j.review_mode(tmp_path) == "off"


@pytest.mark.parametrize("enabled", ["  enabled: false\n", ""])
def test_not_enabled_is_off(tmp_path, key, enabled):
    _write_project(tmp_path, f"judgments:\n{enabled}  review: shadow\n")
    assert j.review_mode(tmp_path) == "off"


def test_missing_key_is_off(tmp_path):
    _write_project(tmp_path, "judgments:\n  enabled: true\n  review: shadow\n")
    assert j.review_mode(tmp_path) == "off"


def test_kill_switch_wins(monkeypatch, tmp_path, key):
    _write_project(tmp_path, "judgments:\n  enabled: true\n  review: shadow\n")
    monkeypatch.setenv("VOSS_JUDGMENTS", "off")
    assert j.review_mode(tmp_path) == "off"


@pytest.mark.parametrize("text", ["judgments: [enabled: true\n", "- review\n", ""])
def test_malformed_config_is_off(tmp_path, key, text):
    _write_project(tmp_path, text)
    assert j.review_mode(tmp_path) == "off"


def test_missing_file_is_off(tmp_path, key):
    assert j.review_mode(tmp_path) == "off"


def test_global_toml_cannot_enable(tmp_path, key):
    path = harness_config.config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('[judgments]\nenabled = true\nreview = "shadow"\n')
    assert j.review_mode(tmp_path) == "off"
    assert "review" not in harness_config.get_judgments_config()


def test_review_modes_have_no_active():
    assert j.REVIEW_MODES == ("off", "shadow")
