"""V16-01 project: config block reader + fs detection tests (D-01..D-03)."""
from __future__ import annotations

from pathlib import Path

from voss.harness.conventions import _load_project_config, load_project_facts


def _write_config(root: Path, text: str) -> None:
    voss = root / ".voss"
    voss.mkdir(parents=True, exist_ok=True)
    (voss / "config.yml").write_text(text)


class TestLoadProjectConfig:
    def test_absent_config_returns_empty(self, tmp_path: Path) -> None:
        assert _load_project_config(tmp_path) == {}

    def test_wellformed_project_block(self, tmp_path: Path) -> None:
        _write_config(
            tmp_path,
            "project:\n  type: python\n  install_command: pip install -e .\n",
        )
        cfg = _load_project_config(tmp_path)
        assert cfg == {"type": "python", "install_command": "pip install -e ."}

    def test_malformed_yaml_returns_empty(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "project: [unclosed\n  ::bad")
        assert _load_project_config(tmp_path) == {}

    def test_non_dict_project_block_returns_empty(self, tmp_path: Path) -> None:
        _write_config(tmp_path, "project: just-a-string\n")
        assert _load_project_config(tmp_path) == {}


class TestDetection:
    def test_pyproject_detects_python(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
        facts, detected = load_project_facts(tmp_path)
        assert facts["type"] == "python"
        assert "type" in detected

    def test_package_json_detects_node(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{}")
        facts, detected = load_project_facts(tmp_path)
        assert facts["type"] == "node"
        assert "type" in detected

    def test_config_wins_over_detection(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
        _write_config(tmp_path, "project:\n  type: node\n")
        facts, detected = load_project_facts(tmp_path)
        assert facts["type"] == "node"
        assert "type" not in detected

    def test_nothing_to_detect(self, tmp_path: Path) -> None:
        facts, detected = load_project_facts(tmp_path)
        assert "type" not in facts
        assert detected == frozenset()
