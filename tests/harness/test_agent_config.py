"""T1-04 Task 2: [agent] max_iterations TOML round-trip + RuntimeConfig field."""
from __future__ import annotations

import warnings

import pytest

from voss.harness import config as harness_config
from voss_runtime._config import RuntimeConfig, configure, get_config, reset_config


@pytest.fixture
def xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture(autouse=True)
def _reset_runtime():
    reset_config()
    yield
    reset_config()


class TestRuntimeConfigField:
    def test_default_max_iterations_is_8(self) -> None:
        assert get_config().max_iterations == 8
        assert RuntimeConfig().max_iterations == 8

    def test_configure_then_reset_round_trips(self) -> None:
        configure(max_iterations=12)
        assert get_config().max_iterations == 12
        reset_config()
        assert get_config().max_iterations == 8


class TestLoadAgentConfig:
    def test_missing_file_returns_empty(self, xdg) -> None:
        assert harness_config.load_agent_config() == {}
        assert not harness_config.config_path().exists()

    def test_loads_max_iterations_value(self, xdg) -> None:
        p = harness_config.config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('[agent]\nmax_iterations = "12"\n')
        cfg = harness_config.load_agent_config()
        assert cfg == {"max_iterations": "12"}


class TestGetMaxIterations:
    def test_no_config_returns_default(self, xdg) -> None:
        assert harness_config.get_max_iterations() == 8

    def test_valid_override_coerced_to_int(self, xdg) -> None:
        harness_config.set_max_iterations(12)
        assert harness_config.get_max_iterations() == 12

    def test_invalid_value_falls_back_with_warning(self, xdg) -> None:
        p = harness_config.config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('[agent]\nmax_iterations = "not-a-number"\n')
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            n = harness_config.get_max_iterations()
        assert n == 8
        assert any(
            issubclass(w.category, RuntimeWarning)
            and "max_iterations" in str(w.message)
            for w in caught
        )


class TestSetMaxIterations:
    def test_writes_agent_block(self, xdg) -> None:
        path = harness_config.set_max_iterations(20)
        text = path.read_text()
        assert "[agent]" in text
        assert 'max_iterations = "20"' in text

    def test_round_trip(self, xdg) -> None:
        harness_config.set_max_iterations(20)
        assert harness_config.load_agent_config() == {"max_iterations": "20"}
        assert harness_config.get_max_iterations() == 20


class TestCrossSection:
    def test_both_sections_survive_independent_writes(self, xdg) -> None:
        harness_config.set_preferred_model("claude-sonnet-4-5")
        harness_config.set_max_iterations(16)
        text = harness_config.config_path().read_text()
        assert "[harness]" in text
        assert "[agent]" in text
        assert "preferred_model" in text
        assert "max_iterations" in text

        # Both readers see their values.
        assert harness_config.load_harness_config()["preferred_model"] == (
            "claude-sonnet-4-5"
        )
        assert harness_config.get_max_iterations() == 16

    def test_rewriting_one_section_preserves_the_other(self, xdg) -> None:
        harness_config.set_preferred_model("model-a")
        harness_config.set_max_iterations(10)
        harness_config.set_preferred_model("model-b")
        assert harness_config.get_max_iterations() == 10
        assert harness_config.load_harness_config()["preferred_model"] == "model-b"

        harness_config.set_max_iterations(99)
        assert harness_config.get_max_iterations() == 99
        assert harness_config.load_harness_config()["preferred_model"] == "model-b"
