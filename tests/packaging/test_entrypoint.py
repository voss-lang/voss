from __future__ import annotations

import importlib.resources
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest


def _read_pyproject() -> dict:
    return tomllib.loads(Path("pyproject.toml").read_text())


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


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


def test_installed_package_data_includes_grammar_and_init_templates():
    root = importlib.resources.files("voss")
    assert root.joinpath("grammar.lark").is_file()
    assert root.joinpath("py.typed").is_file()
    assert root.joinpath("templates/init/hello.voss").is_file()
    assert root.joinpath("templates/init/.gitattributes").is_file()
    assert root.joinpath("templates/init/README.md.jinja").is_file()
    assert root.joinpath("templates/init/pyproject.toml.jinja").is_file()
    assert root.joinpath("templates/audit/markdown.md.jinja").is_file()


@pytest.mark.parametrize(
    "subcommand", ["compile", "run", "check", "init", "ast"]
)
def test_console_script_subcommand_help_after_install(subcommand):
    voss_bin = shutil.which("voss")
    if voss_bin:
        cmd = [voss_bin, subcommand, "--help"]
    else:
        cmd = [sys.executable, "-m", "voss.cli", subcommand, "--help"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


@pytest.mark.slow
def test_editable_install_exposes_voss_help(tmp_path):
    venv_dir = tmp_path / "venv"
    subprocess.run(
        [sys.executable, "-m", "venv", "--system-site-packages", str(venv_dir)],
        check=True,
        timeout=60,
    )
    venv_python = venv_dir / "bin" / "python"
    if not venv_python.exists():
        venv_python = venv_dir / "Scripts" / "python.exe"
    subprocess.run(
        [
            str(venv_python),
            "-m",
            "pip",
            "install",
            "-q",
            "--no-deps",
            "-e",
            str(_repo_root()),
        ],
        check=True,
        timeout=300,
    )
    module_help = subprocess.run(
        [str(venv_python), "-m", "voss.cli", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert module_help.returncode == 0, module_help.stderr
    voss_bin = venv_dir / "bin" / "voss"
    if not voss_bin.exists():
        voss_bin = venv_dir / "Scripts" / "voss.exe"
    assert voss_bin.exists()
    bin_help = subprocess.run(
        [str(voss_bin), "--help"], capture_output=True, text=True, timeout=30
    )
    assert bin_help.returncode == 0, bin_help.stderr
    assert "compile" in bin_help.stdout
