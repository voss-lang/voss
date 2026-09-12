#!/usr/bin/env python3
"""Trim a Python-Build-Standalone extract per RESEARCH §4.

CLI:
  prune_pbs.py <dir-containing-python/>  [--dry-run]

Auto-detects platform shape by looking for sentinel files inside python/:
  python/python.exe      -> Windows targets
  python/bin/python3     -> Unix targets

Missing prune targets are NOT errors; PBS layout evolves and the script is
tolerant by design (RESEARCH §4). Always exits 0 if shape was detected,
even if some targets were absent.

Idempotent: running twice removes everything possible the first time and
finds nothing the second.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

UNIX_PRUNE_DIRS = [
    "include",
    "lib/python3.12/idlelib",
    "lib/python3.12/tkinter",
    "lib/python3.12/lib2to3",
    "lib/python3.12/ensurepip",
    "lib/python3.12/turtledemo",
    "share",
]
UNIX_PRUNE_GLOBS = [
    ("lib", "itcl*"),
    ("lib", "tcl*"),
    ("lib", "tk*"),
    ("lib", "thread*"),
]
UNIX_PRUNE_BINS = [
    "bin/2to3",
    "bin/2to3-3.12",
    "bin/idle3",
    "bin/idle3.12",
    "bin/python3-config",
    "bin/python3.12-config",
]

WIN_PRUNE_DIRS = [
    "include",
    "Lib/idlelib",
    "Lib/tkinter",
    "Lib/lib2to3",
    "Lib/turtledemo",
    "tcl",
]
WIN_PRUNE_FILES = [
    "pythonw.exe",
]


def _remove(path: Path, dry_run: bool) -> bool:
    if path.is_symlink() or path.is_file():
        if dry_run:
            print(f"Would prune file: {path}")
        else:
            path.unlink(missing_ok=True)
            print(f"Pruned file: {path}")
        return True
    if path.is_dir():
        if dry_run:
            print(f"Would prune dir:  {path}")
        else:
            shutil.rmtree(path, ignore_errors=False)
            print(f"Pruned dir:  {path}")
        return True
    return False


def prune_unix(python_dir: Path, dry_run: bool) -> int:
    removed = 0
    for rel in UNIX_PRUNE_DIRS:
        if _remove(python_dir / rel, dry_run):
            removed += 1
        else:
            print(f"Skipped (absent): {python_dir / rel}")
    for parent_rel, pattern in UNIX_PRUNE_GLOBS:
        parent = python_dir / parent_rel
        if parent.is_dir():
            for match in parent.glob(pattern):
                if _remove(match, dry_run):
                    removed += 1
    for rel in UNIX_PRUNE_BINS:
        if _remove(python_dir / rel, dry_run):
            removed += 1
        else:
            print(f"Skipped (absent): {python_dir / rel}")
    return removed


def prune_windows(python_dir: Path, dry_run: bool) -> int:
    removed = 0
    for rel in WIN_PRUNE_DIRS:
        if _remove(python_dir / rel, dry_run):
            removed += 1
        else:
            print(f"Skipped (absent): {python_dir / rel}")
    for rel in WIN_PRUNE_FILES:
        if _remove(python_dir / rel, dry_run):
            removed += 1
        else:
            print(f"Skipped (absent): {python_dir / rel}")
    return removed


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Prune a PBS Python extract.")
    parser.add_argument("root", type=Path, help="Directory containing python/")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv[1:])

    python_dir = args.root / "python"
    if (python_dir / "python.exe").exists():
        shape = "windows"
        removed = prune_windows(python_dir, args.dry_run)
    elif (python_dir / "bin" / "python3").exists():
        shape = "unix"
        removed = prune_unix(python_dir, args.dry_run)
    else:
        sys.stderr.write(
            f"prune_pbs: could not detect Unix or Windows shape at {python_dir}\n"
        )
        return 2

    print(f"prune_pbs: shape={shape} removed={removed} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
