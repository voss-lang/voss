"""Voss agent harness — scratch impl for v1.1 milestone (HARNESS-PLAN.md H1).

Invoke via `python -m voss.harness ...` until wired into voss.cli.
"""

__all__ = ["main"]

from .cli import main
