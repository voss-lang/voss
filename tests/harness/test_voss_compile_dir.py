from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from voss.cli import main


def _write_agent_sources(project_root: Path) -> Path:
    agent_dir = project_root / "voss" / "harness" / "agent"
    agent_dir.mkdir(parents=True)
    (agent_dir / "loop.voss").write_text("let loop = 1\n")
    (agent_dir / "router.voss").write_text("let router = 2\n")
    return agent_dir


def test_compile_dir_emits_per_file_artifacts(tmp_path):
    agent_dir = _write_agent_sources(tmp_path)

    result = CliRunner().invoke(
        main,
        ["compile", str(agent_dir), "--project-root", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / ".voss-cache" / "harness" / "loop.py").exists()
    assert (tmp_path / ".voss-cache" / "harness" / "router.py").exists()
    assert not (agent_dir / "loop.py").exists()
    assert not (agent_dir / "router.py").exists()


def test_manifest_schema(tmp_path):
    agent_dir = _write_agent_sources(tmp_path)

    result = CliRunner().invoke(
        main,
        ["compile", str(agent_dir), "--project-root", str(tmp_path)],
    )

    assert result.exit_code == 0, result.output
    manifest = tmp_path / ".voss-cache" / "harness" / "_manifest.json"
    data = json.loads(manifest.read_text())
    assert data["version"] == 1
    assert isinstance(data["voss_version"], str)
    assert isinstance(data["compiled_at"], str)
    assert set(data["sources"]) == {"loop.voss", "router.voss"}
    for entry in data["sources"].values():
        assert len(entry["sha256"]) == 64
        assert entry["lines"] >= 1


def test_voss_cache_ignored():
    gitignore = Path(__file__).resolve().parents[2] / ".gitignore"

    assert ".voss-cache/" in gitignore.read_text()
