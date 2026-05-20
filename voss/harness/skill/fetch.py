"""Fetch skill bundles from local path, git URL, GitHub shorthand, or archive."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

GITHUB_SHORTHAND = re.compile(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$")


def fetch_bundle(source: str, staging_dir: Path) -> Path:
    """Fetch a skill bundle into *staging_dir*.

    Resolution order (Pitfall 6: local path beats shorthand):
      1. Local path (``Path(source).exists()``)
      2. GitHub shorthand (``owner/repo``)
      3. Git HTTPS URL
      4. Archive file (.zip / .tar / .gz / .tgz)

    Returns the bundle directory inside *staging_dir*.
    Raises ``ValueError`` on unrecognised source or forbidden transport.
    Raises ``RuntimeError`` on git clone failure.
    """
    # 1. Local path first
    local = Path(source)
    if local.exists():
        if local.is_dir():
            dest = staging_dir / local.name
            shutil.copytree(local, dest)
            return dest
        if local.suffix in (".zip", ".tar", ".gz", ".tgz"):
            return _extract_archive(local, staging_dir)
        raise ValueError(f"local path is not a directory or supported archive: {source!r}")

    # 2. GitHub shorthand
    if GITHUB_SHORTHAND.match(source):
        url = f"https://github.com/{source}.git"
        return _git_clone(url, staging_dir)

    # 3. Git URL (HTTPS only — reject git:// and http://)
    if source.startswith(("git://", "http://")):
        raise ValueError(
            f"insecure transport rejected (HTTPS required): {source!r}"
        )
    if source.startswith("https://"):
        return _git_clone(source, staging_dir)

    raise ValueError(f"unrecognised source: {source!r}")


def _git_clone(url: str, staging_dir: Path) -> Path:
    dest = staging_dir / "bundle"
    result = subprocess.run(
        ["git", "clone", "--depth=1", url, str(dest)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git clone failed: {result.stderr.strip()}")
    return dest


def _extract_archive(archive: Path, staging_dir: Path) -> Path:
    dest = staging_dir / "bundle"
    dest.mkdir(parents=True, exist_ok=True)
    shutil.unpack_archive(str(archive), str(dest))
    # If archive contained a single top-level dir, return that
    children = list(dest.iterdir())
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return dest
