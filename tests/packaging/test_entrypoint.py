from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path


def _read_pyproject() -> dict:
    return tomllib.loads(Path("pyproject.toml").read_text())


def test_project_scripts_declares_voss_entrypoint():
    data = _read_pyproject()
    scripts = data.get("project", {}).get("scripts", {})
    assert scripts.get("voss") == "voss.cli:main"


def test_cli_module_main_is_importable():
    import voss.cli as cli

    assert callable(cli.main)


def test_module_help_smoke():
    result = subprocess.run(
        [sys.executable, "-m", "voss.cli", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "compile" in result.stdout
