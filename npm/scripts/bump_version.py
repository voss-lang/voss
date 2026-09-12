#!/usr/bin/env python3
"""Sync version from pyproject.toml [project].version into the npm/ tree.

Single source of truth: pyproject.toml. CLI surface:
  bump_version.py             # update all 6 package.jsons
  bump_version.py main        # update npm/package.json only
  bump_version.py <triple>    # update one platform manifest

Rewrites `version` in each target package.json and refreshes each entry
in npm/package.json's `optionalDependencies` to the new version so the
main package keeps pinning its platform subpackages exactly.

Output style: 2-space indent + trailing newline (matches M6-01 placeholders
and `npm publish` defaults; makes diffs minimal and deterministic).
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"
NPM_DIR = ROOT / "npm"
PLATFORMS = [
    "darwin-arm64",
    "darwin-x64",
    "linux-x64",
    "linux-arm64",
    "win32-x64",
]


def read_pyproject_version(pyproject: Path = PYPROJECT) -> str:
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def update_json(path: Path, version: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = version
    opts = data.get("optionalDependencies")
    if isinstance(opts, dict):
        for key in list(opts.keys()):
            opts[key] = version
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {path.relative_to(ROOT)} -> {version}")


def main(argv: list[str]) -> int:
    target = argv[1] if len(argv) > 1 else "all"
    valid = {"all", "main", *PLATFORMS}
    if target not in valid:
        sys.stderr.write(
            f"bump_version: unknown target {target!r}. "
            f"Expected one of: {sorted(valid)}\n"
        )
        return 2

    version = read_pyproject_version()
    main_pkg = NPM_DIR / "package.json"

    if target in ("all", "main"):
        update_json(main_pkg, version)
    if target == "all":
        for triple in PLATFORMS:
            update_json(NPM_DIR / "platforms" / triple / "package.json", version)
    elif target in PLATFORMS:
        update_json(NPM_DIR / "platforms" / target / "package.json", version)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
