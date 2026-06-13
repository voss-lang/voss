"""Click subcommand group for `voss memory <vacuum|adopt|size>`.

Owned by M8-04 (MEM-06). Group + command shells defined concretely so the
main CLI can register them.
"""
from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import click
import portalocker

from . import voss_md
from .cognition import reserve_filename, slug
from .memory_store import MemoryStore, _repo_id, make_global_store, make_id


_PROMOTABLE_SOURCES = {
    "note": ("notes", "note"),
    "decision": ("decisions", "decision"),
    "convention": ("conventions", "convention"),
}


def _first_markdown_body_line(path: Path) -> str:
    try:
        lines = path.read_text(errors="ignore").splitlines()
    except OSError:
        return ""
    in_frontmatter = False
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if idx == 0 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue
        if stripped:
            return stripped[:80]
    return ""


def _path_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _resolve_promote_source(store: MemoryStore, locator: str) -> tuple[str, str, Path] | None:
    source_prefix, sep, rest = locator.partition(":")
    if not sep or not rest:
        return None
    source_info = _PROMOTABLE_SOURCES.get(source_prefix)
    if source_info is None:
        return None
    source_dir, source_type = source_info
    if source_prefix == "decision":
        path = store.root.parent / rest
    else:
        path = store.root / source_dir / f"{rest}.md"
    if not _path_under(path, store.root.parent):
        return None
    return source_dir, source_type, path


def _with_promoted_frontmatter(content: str, *, provenance: str, ts: str) -> str:
    promoted = f"promoted_from: {provenance}\npromoted_at: {ts}\n"
    if content.startswith("---\n"):
        return content.replace("---\n", f"---\n{promoted}", 1)
    return f"---\n{promoted}---\n\n{content}"


def _remove_existing_promotions(gstore: MemoryStore, source_dir: str, provenance: str) -> None:
    needle = f"promoted_from: {provenance}"
    for path in (gstore.root / source_dir).glob("*.md"):
        try:
            if needle in path.read_text(errors="ignore"):
                path.unlink(missing_ok=True)
        except OSError:
            continue


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
@click.option(
    "--global",
    "use_global",
    is_flag=True,
    help="Compact global store (~/.voss/memory/).",
)
def memory_vacuum_cmd(cwd_str: str, use_global: bool) -> None:
    """Compact chroma + delete tombstoned entries; report bytes reclaimed."""
    if use_global:
        store = make_global_store()
        if store is None:
            click.echo("global store disabled or unavailable", err=True)
            sys.exit(1)
    else:
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


@memory_group.command("promote")
@click.argument("locator", required=False)
@click.option(
    "--cwd",
    "cwd_str",
    default=".",
    type=click.Path(file_okay=False),
    help="Project root.",
)
@click.option(
    "--list",
    "list_only",
    is_flag=True,
    help="List promotable entries instead of promoting.",
)
def memory_promote_cmd(locator: str | None, cwd_str: str, list_only: bool) -> None:
    """Copy a project memory entry into the global store with provenance tag."""
    cwd = Path(cwd_str).resolve()
    store = MemoryStore(cwd)

    if list_only:
        for source in ("notes", "decisions", "conventions"):
            source_dir = store.root / source
            if not source_dir.exists():
                continue
            for path in sorted(source_dir.rglob("*.md")):
                loc = store._locator_from_path(source, path)
                click.echo(f"{loc}: {_first_markdown_body_line(path)}")
        return

    if not locator:
        click.echo("error: missing memory locator", err=True)
        sys.exit(1)

    source_prefix = locator.split(":", 1)[0]
    if source_prefix in ("turn", "ledger"):
        click.echo(
            f"error: turns and ledgers cannot be promoted (got: {source_prefix})",
            err=True,
        )
        sys.exit(1)

    resolved = _resolve_promote_source(store, locator)
    if resolved is None:
        click.echo(f"error: locator cannot be promoted: {locator}", err=True)
        sys.exit(1)
    source_dir, source_type, source_path = resolved
    if not source_path.exists():
        click.echo(f"error: memory entry not found: {locator}", err=True)
        sys.exit(1)
    try:
        content = source_path.read_text()
    except OSError as exc:
        click.echo(f"error: could not read memory entry: {exc}", err=True)
        sys.exit(1)

    gstore = make_global_store()
    if gstore is None:
        click.echo("global store disabled or unavailable", err=True)
        sys.exit(1)
    gstore.bind(session_id="promote")
    provenance = f"{_repo_id(cwd)}/{locator}"
    chroma = gstore._maybe_chroma()
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    dest_dir = gstore.root / source_dir
    lock_path = gstore.root / ".locks" / f"{source_dir}.lock"

    with portalocker.Lock(
        str(lock_path),
        mode="a",
        flags=portalocker.LOCK_EX,
        timeout=5,
    ):
        if chroma is not None:
            existing = chroma._collection.get(where={"promoted_from": provenance})
            existing_ids = existing.get("ids", [])
            if existing_ids:
                chroma._collection.delete(ids=existing_ids)
        _remove_existing_promotions(gstore, source_dir, provenance)
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = reserve_filename(dest_dir, slug(source_path.stem))
        body = _with_promoted_frontmatter(content, provenance=provenance, ts=ts)
        path.write_text(body)
        path.chmod(0o600)
        if chroma is not None:
            chroma.add(
                text=content,
                metadata={
                    "source_type": source_type,
                    "promoted_from": provenance,
                    "ts": ts,
                    "path": str(path),
                    "tombstoned": False,
                },
                id=make_id(source_type, path.stem),
            )

    click.echo(f"promoted: {locator} -> global:{path.stem}")


@memory_group.command("forget")
@click.argument("locator")
@click.option("--global", "use_global", is_flag=True, help="Tombstone from global store.")
@click.option("--yes", "confirm", is_flag=True, help="Skip confirmation prompt.")
@click.option(
    "--cwd",
    "cwd_str",
    default=".",
    type=click.Path(file_okay=False),
    help="Project root.",
)
def memory_forget_cmd(locator: str, use_global: bool, confirm: bool, cwd_str: str) -> None:
    """Tombstone memory entries. --global targets the global store."""
    if use_global:
        store = make_global_store()
        if store is None:
            click.echo("global store disabled or unavailable", err=True)
            sys.exit(1)
        store.root.mkdir(parents=True, exist_ok=True)
    else:
        store = MemoryStore(Path(cwd_str).resolve())
    n = store.forget(locator, confirm=confirm)
    click.echo(f"tombstoned: {n} entries")


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
