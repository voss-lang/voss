"""M5 EVAL-05 / D-16: build wheel, install in temp venv, smoke the post-install
CLI surface.

These three tests prove the v0.1 wheel installs cleanly into a fresh, isolated
virtualenv (no `--system-site-packages`, no `--no-deps`) and exposes the
post-install command surface that M6's npm wrapper will rely on. Marked
`@pytest.mark.slow` because `python -m build` performs a real wheel build
(~tens of seconds) and the venv create + pip install are network-dependent
on first invocation.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests.packaging.test_entrypoint import _repo_root


def _build_wheel(dist: Path) -> Path:
    """Build the repo wheel into `dist/` and return the wheel path."""
    dist.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--outdir",
            str(dist),
            str(_repo_root()),
        ],
        check=True,
        timeout=600,
    )
    wheels = list(dist.glob("voss-*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel, got {wheels}"
    return wheels[0]


def _make_venv(venv_dir: Path) -> Path:
    """Create an isolated venv and return the python interpreter path."""
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        check=True,
        timeout=60,
    )
    py = venv_dir / "bin" / "python"
    if not py.exists():
        py = venv_dir / "Scripts" / "python.exe"
    return py


def _voss_bin(venv_dir: Path) -> Path:
    bin_path = venv_dir / "bin" / "voss"
    if not bin_path.exists():
        bin_path = venv_dir / "Scripts" / "voss.exe"
    return bin_path


@pytest.mark.slow
def test_wheel_builds(tmp_path):
    """`python -m build --wheel` produces exactly one `voss-*.whl`."""
    dist = tmp_path / "dist"
    wheel = _build_wheel(dist)
    assert wheel.is_file()


@pytest.mark.slow
def test_install(tmp_path):
    """A clean tempvenv accepts the wheel via `pip install <wheel>` WITH deps.

    Diverges from `test_editable_install_exposes_voss_help` (which uses
    `--no-deps` + `--system-site-packages`): smoke must validate the wheel
    installs its full declared dependency set into an isolated venv. That is
    the contract M6 npm bundling will rely on.
    """
    dist = tmp_path / "dist"
    wheel = _build_wheel(dist)

    venv_dir = tmp_path / "venv"
    py = _make_venv(venv_dir)

    subprocess.run(
        [str(py), "-m", "pip", "install", "-q", str(wheel)],
        check=True,
        timeout=600,
    )
    assert _voss_bin(venv_dir).exists()


@pytest.mark.slow
def test_smoke_asserts(tmp_path):
    """Exercise the post-install CLI surface inside an isolated tempvenv."""
    dist = tmp_path / "dist"
    wheel = _build_wheel(dist)

    venv_dir = tmp_path / "venv"
    py = _make_venv(venv_dir)
    subprocess.run(
        [str(py), "-m", "pip", "install", "-q", str(wheel)],
        check=True,
        timeout=600,
    )

    voss_bin = _voss_bin(venv_dir)
    assert voss_bin.exists()
    repo = _repo_root()

    # voss --help
    r = subprocess.run(
        [str(voss_bin), "--help"], capture_output=True, text=True, timeout=30
    )
    assert r.returncode == 0, r.stderr

    # voss compile samples/classify.voss → tmp_path/classify.py
    # (cwd=repo so the source path resolves; -o keeps the generated .py out of
    # the repo tree so other repo-purity tests stay green).
    out_py = tmp_path / "classify.py"
    r = subprocess.run(
        [
            str(voss_bin),
            "compile",
            "samples/classify.voss",
            "-o",
            str(out_py),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=repo,
    )
    assert r.returncode == 0, r.stderr
    assert out_py.is_file()

    # voss check samples/classify.voss
    r = subprocess.run(
        [str(voss_bin), "check", "samples/classify.voss"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=repo,
    )
    assert r.returncode == 0, r.stderr

    # voss doctor — exit ∈ {0, 1} per M1 D-13 (1 in a clean tempvenv with no
    # provider creds; 0 if creds happen to be in env).
    r = subprocess.run(
        [str(voss_bin), "doctor"], capture_output=True, text=True, timeout=30
    )
    assert r.returncode in {0, 1}, f"voss doctor crashed: {r.stderr}"
    combined = (r.stdout + r.stderr).lower()
    assert "python" in combined or "provider" in combined

    # import voss_runtime
    r = subprocess.run(
        [str(py), "-c", "import voss_runtime"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, r.stderr
