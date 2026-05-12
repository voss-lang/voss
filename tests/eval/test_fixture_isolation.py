"""M5 D-06: each run gets fresh tempdir + git init; no shared state across runs."""
import subprocess
from pathlib import Path
from shutil import copytree


# TODO Wave 2: replace inline helper with `from voss.eval.runner import _prepare_fixture`.
def _prepare_fixture(task_dir: Path, tmp: Path) -> Path:
    """Per-run hermetic git init (D-06)."""
    cwd = tmp / "fixture"
    copytree(task_dir / "fixture", cwd)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=cwd, check=True)
    subprocess.run(["git", "add", "-A"], cwd=cwd, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=eval@voss",
            "-c",
            "user.name=eval",
            "commit",
            "-q",
            "-m",
            "init",
        ],
        cwd=cwd,
        check=True,
    )
    return cwd


def test_prepare_fixture_creates_git_repo(tmp_path):
    src = tmp_path / "src"
    (src / "fixture").mkdir(parents=True)
    (src / "fixture" / "hello.txt").write_text("hi\n")

    cwd = _prepare_fixture(src, tmp_path / "run0")

    assert (cwd / ".git").is_dir()
    assert (cwd / "hello.txt").read_text() == "hi\n"


def test_two_runs_dont_share_state(tmp_path):
    src = tmp_path / "src"
    (src / "fixture").mkdir(parents=True)
    (src / "fixture" / "f.txt").write_text("a\n")

    first = _prepare_fixture(src, tmp_path / "run-a")
    second = _prepare_fixture(src, tmp_path / "run-b")
    (first / "f.txt").write_text("CHANGED\n")

    assert (second / "f.txt").read_text() == "a\n"
