import pytest

from voss.harness import config as harness_config


@pytest.fixture(autouse=True)
def isolated_judgments(monkeypatch):
    monkeypatch.delenv("VOSS_JUDGMENTS", raising=False)
    monkeypatch.setattr("voss.harness.auth.load_provider_key", lambda env_key: None)


def _write_global(text):
    path = harness_config.config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_defaults():
    assert harness_config.get_judgments_config() == {
        "model": "jev-1.13.0", "timeout_ms": 5000, "max_calls_per_turn": 4,
        "max_request_bytes": 24000, "max_cost_usd": 0.01,
    }


def test_overrides():
    _write_global('[judgments]\nmodel = "jev-latest"\ntimeout_ms = 1500 # deadline\nmax_calls_per_turn = 2\nmax_request_bytes = 8000\nmax_cost_usd = 0.02\n')
    assert harness_config.get_judgments_config() == {
        "model": "jev-latest", "timeout_ms": 1500, "max_calls_per_turn": 2,
        "max_request_bytes": 8000, "max_cost_usd": 0.02,
    }


@pytest.mark.parametrize("key,value", [
    ("timeout_ms", "0"), ("timeout_ms", "-5"), ("max_calls_per_turn", '"x"'),
    ("max_request_bytes", "1.5"), ("max_cost_usd", "0"), ("max_cost_usd", "-1"),
    ("max_cost_usd", "nan"), ("max_cost_usd", "inf"), ("model", '""'),
])
def test_bad_values_warn(key, value):
    _write_global(f"[judgments]\n{key} = {value}\n")
    with pytest.warns(RuntimeWarning, match=key):
        assert harness_config.get_judgments_config()[key] == harness_config.JUDGMENTS_DEFAULTS[key]


def test_no_global_enabled_key():
    _write_global("[judgments]\nenabled = true\ncode_recall = active\nreview = shadow\n")
    assert harness_config.get_judgments_config() == harness_config.JUDGMENTS_DEFAULTS


def test_other_sections_unaffected():
    _write_global("[instructions]\nbudget_tokens = 1234\n[judgments]\ntimeout_ms = 1500\n")
    assert harness_config.get_instructions_config()["budget_tokens"] == 1234
    assert harness_config.get_judgments_config()["timeout_ms"] == 1500
