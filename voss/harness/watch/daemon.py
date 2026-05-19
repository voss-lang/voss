"""Daemon detach helper for long-running watch tasks."""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Any


def spawn_detached_worker(original_argv: list[str]) -> int:
    """Spawns a detached worker process that runs independently of the parent.
    
    Strips out any '--daemon' arguments and injects '--_is-worker' for re-entry guarding.
    """
    filtered_args = [arg for arg in original_argv if arg != "--daemon"]
    if "--_is-worker" not in filtered_args:
        filtered_args.append("--_is-worker")

    worker_argv = [sys.executable, "-m", "voss.harness.cli", "watch"] + filtered_args

    # start_new_session is True to detach the child on POSIX (by calling setsid()).
    # On Windows, start_new_session is ignored/supported best-effort.
    proc = subprocess.Popen(
        worker_argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=True,
    )

    # Intentionally do not wait or block on the process.
    return proc.pid


def is_worker_invocation(argv: list[str]) -> bool:
    """Check if the argv represents a worker re-entry invocation."""
    return "--_is-worker" in argv
