"""Click subcommand group for `voss memory <vacuum|adopt|size>`.

Owned by M8-04 (MEM-06). Group + command shells defined concretely so the
main CLI can register them; bodies raise NotImplementedError until M8-04.
"""
from __future__ import annotations

from pathlib import Path  # noqa: F401  (consumed by M8-04 bodies)

import click


@click.group("memory")
def memory_group() -> None:
    """Manage Voss project memory store."""


@memory_group.command("vacuum")
@click.option(
    "--cwd",
    "cwd_str",
    default=".",
    type=click.Path(file_okay=False),
    help="Project root.",
)
def memory_vacuum_cmd(cwd_str: str) -> None:
    """Compact chroma + delete tombstoned entries; report bytes reclaimed."""
    raise NotImplementedError("M8-04")


@memory_group.command("adopt")
@click.option(
    "--cwd",
    "cwd_str",
    default=".",
    type=click.Path(file_okay=False),
    help="Project root.",
)
@click.option(
    "--id",
    "fence_id",
    required=True,
    help="Fence id to adopt (D-07 hash-mismatch resolution).",
)
def memory_adopt_cmd(cwd_str: str, fence_id: str) -> None:
    """Adopt the on-disk fence body as the new baseline (resolves HashMismatch)."""
    raise NotImplementedError("M8-04")


@memory_group.command("size")
@click.option(
    "--cwd",
    "cwd_str",
    default=".",
    type=click.Path(file_okay=False),
    help="Project root.",
)
def memory_size_cmd(cwd_str: str) -> None:
    """Report memory store size per source."""
    raise NotImplementedError("M8-04")
