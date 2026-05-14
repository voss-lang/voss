"""Click subcommand group for `voss memory <vacuum|adopt|size>`.

Owned by M8-04 (MEM-06). Group + command shells defined concretely so the
main CLI can register them.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import click

from . import voss_md
from .memory_store import MemoryStore


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
    cwd = Path(cwd_str).resolve()
    store = MemoryStore(cwd)
    if not store.root.exists():
        click.echo(f"no memory store at {store.root}", err=True)
        sys.exit(1)
    store.bind(session_id="vacuum")
    reclaimed = store.vacuum()
    click.echo(f"reclaimed: {reclaimed} bytes")


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
    cwd = Path(cwd_str).resolve()
    voss_md_path = cwd / "VOSS.md"
    if not voss_md_path.exists():
        click.echo("VOSS.md not found", err=True)
        sys.exit(1)
    blocks = voss_md.parse(voss_md_path.read_text())
    target = next(
        (b for b in blocks if b.kind == "machine" and b.id == fence_id),
        None,
    )
    if target is None:
        click.echo(f"fence id={fence_id} not found", err=True)
        sys.exit(1)
    new_hash = hashlib.sha256(target.body.encode()).hexdigest()
    voss_md.write_fence_body(
        voss_md_path,
        fence_id=fence_id,
        body=target.body,
        adopt=True,
    )
    click.echo(f"adopted: id={fence_id} hash={new_hash[:16]}...")


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
    cwd = Path(cwd_str).resolve()
    store = MemoryStore(cwd)
    root = store.root
    if not root.exists():
        click.echo("no memory store", err=True)
        sys.exit(1)
    total = 0
    for source in ("turns", "ledgers", "decisions", "conventions", "notes"):
        src_dir = root / source
        size = (
            sum(p.stat().st_size for p in src_dir.rglob("*") if p.is_file())
            if src_dir.exists()
            else 0
        )
        total += size
        click.echo(f"  {source}: {size:>10} bytes")
    pct = 100 * total / max(1, store.cap_bytes)
    click.echo(f"  TOTAL: {total} / {store.cap_bytes} bytes ({pct:.1f}%)")
