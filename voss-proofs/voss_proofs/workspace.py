"""Isolated per-run workspaces: fixture copy, git baseline, env isolation, diff capture."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

SECRET_ENV = re.compile(r"(_API_KEY|_TOKEN|_SECRET|_PASSWORD)$|^TYPESAFE_")
PARENT_AGENT_ENV = re.compile(r"^(CLAUDECODE|CLAUDE_PID|CLAUDE_EFFORT)$|^(CLAUDE_CODE_|CLAUDE_PLUGIN_|CODEX_COMPANION_)")
EXCLUDED = "\n".join([
    ".voss/", ".voss-cache/", "__pycache__/", "*.pyc", ".pytest_cache/",
    "node_modules/", "target/", "",
])


@dataclass
class Workspace:
    root: Path
    repo: Path
    home: Path

    def cleanup(self) -> None:
        shutil.rmtree(claude_project_dir(self.repo), ignore_errors=True)
        shutil.rmtree(self.root, ignore_errors=True)


def claude_project_dir(repo: Path) -> Path:
    """Where Claude Code keeps sessions and auto-memory for `repo`. A later run could read it, so it goes too."""
    return Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(repo.resolve()))


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout


def prepare(task_dir: Path, scenario: str) -> Workspace:
    root = Path(tempfile.mkdtemp(prefix=f"proofs-{scenario}-"))
    repo, home = root / "repo", root / "home"
    home.mkdir()
    fixture = task_dir / "fixture"
    if fixture.is_dir():
        shutil.copytree(fixture, repo)
    else:
        repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / ".git" / "info" / "exclude").write_text(EXCLUDED)
    _git(repo, "add", "-A")
    _git(
        repo, "-c", "user.name=proofs", "-c", "user.email=proofs@localhost",
        "-c", "commit.gpgsign=false", "commit", "-q", "--allow-empty", "-m", "init",
    )
    return Workspace(root, repo, home)


def env(ws: Workspace, *, live: bool, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Live runs keep the real HOME (subscription auth lives there); offline runs get
    a throwaway HOME/XDG and no secrets. Neither inherits the session of an agent driving proofs."""
    out = {k: v for k, v in os.environ.items() if not PARENT_AGENT_ENV.search(k)}
    real_home = Path.home()
    out["PATH"] = f"{Path(sys.executable).parent}{os.pathsep}{out.get('PATH', '')}"
    out.setdefault("RUSTUP_HOME", str(real_home / ".rustup"))
    out.setdefault("CARGO_HOME", str(real_home / ".cargo"))
    out["CARGO_TARGET_DIR"] = str(ws.root / "cargo-target")
    out["GOCACHE"] = str(ws.root / "go-cache")
    if not live:
        out = {k: v for k, v in out.items() if not SECRET_ENV.search(k)}
        out["HOME"] = str(ws.home)
        for var in ("XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME"):
            out[var] = str(ws.home / var.lower())
        out["CODEX_HOME"] = str(ws.home / ".codex")
    out.update(extra or {})
    return out


def stage(repo: Path) -> None:
    _git(repo, "add", "-A")


def diff(repo: Path) -> str:
    stage(repo)
    return _git(repo, "diff", "--cached", "--binary", "HEAD")


def changed_paths(repo: Path) -> list[str]:
    stage(repo)
    return [p for p in _git(repo, "diff", "--cached", "--name-only", "HEAD").splitlines() if p]


def install_hidden(task_dir: Path, repo: Path) -> None:
    hidden = task_dir / "hidden"
    shutil.rmtree(repo / "hidden", ignore_errors=True)
    if hidden.is_dir():
        shutil.copytree(hidden, repo / "hidden")


def scenario_hash(task_dir: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(p for p in task_dir.rglob("*") if p.is_file()):
        if "__pycache__" in path.parts:
            continue
        h.update(path.relative_to(task_dir).as_posix().encode() + b"\0")
        h.update(path.read_bytes() + b"\0")
    return h.hexdigest()
