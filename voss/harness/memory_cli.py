"""Click subcommand group for `voss memory <vacuum|adopt|size>`.

Owned by M8-04 (MEM-06). Group + command shells defined concretely so the
main CLI can register them.
"""
from __future__ import annotations

import hashlib
import json
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


# ---------------------------------------------------------------------------
# V23 VRNK-07 operator verbs: pin / unpin / list / show / reindex
# ---------------------------------------------------------------------------

# Locator vocabulary accepted for pinning/showing — guards .pins.json against
# path-injection (T-V23-07-01); must mirror make_id prefixes.
_VALID_PIN_PREFIXES = ("turn", "ledger", "decision", "convention", "note")


def _memory_store_for(cwd_str: str, use_global: bool) -> MemoryStore:
    """Resolve the project or --global store; exit 1 when missing (D-12)."""
    if use_global:
        store = make_global_store()
        if store is None:
            click.echo("global store disabled or unavailable", err=True)
            sys.exit(1)
        store.root.mkdir(parents=True, exist_ok=True)
        return store
    store = MemoryStore(Path(cwd_str).resolve())
    if not store.root.exists():
        click.echo(f"no memory store at {store.root}", err=True)
        sys.exit(1)
    return store


def _read_pins_raw(store: MemoryStore) -> list[dict]:
    """Read the raw .pins.json entries (locator + pinned_at), corrupt-tolerant."""
    path = store._pins_path
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    return [e for e in data.get("pins", []) if isinstance(e, dict) and e.get("locator")]


def _locator_exists(store: MemoryStore, locator: str) -> bool:
    """True when `locator` has a known prefix AND a backing memory row (Pitfall 6 / V5)."""
    prefix, _, rest = locator.partition(":")
    if prefix not in _VALID_PIN_PREFIXES or not rest:
        return False
    if prefix in ("note", "convention", "decision"):
        return store._read_pinned_body(locator) is not None
    sub = "turns" if prefix == "turn" else "ledgers"
    stem = rest.split(":")[0]
    return (store.root / sub / f"{stem}.jsonl").exists()


def _locator_body(store: MemoryStore, locator: str) -> str | None:
    """Full body for show (D-14): file body for note/convention/decision, jsonl for turn/ledger."""
    body = store._read_pinned_body(locator)
    if body is not None:
        return body
    prefix, _, rest = locator.partition(":")
    if prefix not in ("turn", "ledger"):
        return None
    sub = "turns" if prefix == "turn" else "ledgers"
    path = store.root / sub / f"{rest.split(':')[0]}.jsonl"
    if not path.exists():
        return None
    try:
        return path.read_text(errors="ignore")
    except OSError:
        return None


@memory_group.command("pin")
@click.argument("locator")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Project root.")
@click.option("--global", "use_global", is_flag=True, help="Pin in the global store.")
def memory_pin_cmd(locator: str, cwd_str: str, use_global: bool) -> None:
    """Pin a memory locator so it is always injected into agent context."""
    store = _memory_store_for(cwd_str, use_global)
    if not _locator_exists(store, locator):
        click.echo(f"unknown locator: {locator}", err=True)
        sys.exit(1)
    entries = _read_pins_raw(store)
    if locator in {e["locator"] for e in entries}:
        click.echo(f"already pinned: {locator}")
        return
    entries.append(
        {"locator": locator, "pinned_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    )
    store._save_pins(entries)
    click.echo(f"pinned: {locator}")


@memory_group.command("unpin")
@click.argument("locator")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Project root.")
@click.option("--global", "use_global", is_flag=True, help="Unpin from the global store.")
def memory_unpin_cmd(locator: str, cwd_str: str, use_global: bool) -> None:
    """Remove a memory locator from the pinned tier."""
    store = _memory_store_for(cwd_str, use_global)
    entries = _read_pins_raw(store)
    if locator not in {e["locator"] for e in entries}:
        click.echo(f"not pinned: {locator}", err=True)
        sys.exit(1)
    store._save_pins([e for e in entries if e["locator"] != locator])
    click.echo(f"unpinned: {locator}")


@memory_group.command("show")
@click.argument("locator")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Project root.")
@click.option("--global", "use_global", is_flag=True, help="Read from the global store.")
def memory_show_cmd(locator: str, cwd_str: str, use_global: bool) -> None:
    """Print a memory's full body + telemetry + pin flag (D-14)."""
    store = _memory_store_for(cwd_str, use_global)
    if not _locator_exists(store, locator):
        click.echo(f"unknown locator: {locator}", err=True)
        sys.exit(1)
    tel = store._load_telemetry_compacted().get(locator, {})
    click.echo(f"locator: {locator}")
    click.echo(f"pinned: {locator in store._load_pins()}")
    click.echo(f"retrieval_count: {tel.get('retrieval_count', 0)}")
    click.echo(f"last_retrieved: {tel.get('last_retrieved') or '—'}")
    click.echo("---")
    click.echo(_locator_body(store, locator) or "(no body)")


@memory_group.command("list")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Project root.")
@click.option("--source", "source", default=None, help="Filter by source (turns/notes/...).")
@click.option("--pinned", "pinned_only", is_flag=True, help="Only pinned rows.")
@click.option("--json", "as_json", is_flag=True, help="Emit a JSON array.")
@click.option("--global", "use_global", is_flag=True, help="List the global store.")
def memory_list_cmd(
    cwd_str: str, source: str | None, pinned_only: bool, as_json: bool, use_global: bool
) -> None:
    """List memory rows with telemetry + pin columns (filterable)."""
    store = _memory_store_for(cwd_str, use_global)
    pins = store._load_pins()
    telemetry = store._load_telemetry_compacted()

    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for cand in store._bm25_corpus(None):
        loc = cand.hit.locator
        if loc in seen:
            continue
        seen.add(loc)
        rows.append((loc, cand.hit.source))
    for loc in pins:  # surface pinned rows even if the corpus skipped them
        if loc not in seen:
            seen.add(loc)
            rows.append((loc, loc.split(":")[0]))

    if source:
        want = source.rstrip("s")
        rows = [r for r in rows if r[1] == want]
    if pinned_only:
        rows = [r for r in rows if r[0] in pins]
    rows.sort()

    if as_json:
        click.echo(
            json.dumps(
                [
                    {
                        "locator": loc,
                        "source": src,
                        "retrieval_count": telemetry.get(loc, {}).get("retrieval_count", 0),
                        "last_retrieved": telemetry.get(loc, {}).get("last_retrieved") or None,
                        "pinned": loc in pins,
                    }
                    for loc, src in rows
                ]
            )
        )
        return
    if not rows:
        click.echo("(none)")
        return
    click.echo(f"{'locator':40} {'source':12} {'count':>5} {'last_retrieved':25} pin")
    for loc, src in rows:
        tel = telemetry.get(loc, {})
        flag = "pinned" if loc in pins else ""
        click.echo(
            f"{loc:40} {src:12} {tel.get('retrieval_count', 0):>5} "
            f"{tel.get('last_retrieved') or '—':25} {flag}"
        )


@memory_group.command("reindex")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Project root.")
@click.option("--check", "check", is_flag=True, help="Report drift without re-embedding (exit 1 on drift).")
@click.option("--global", "use_global", is_flag=True, help="Reindex the global store.")
def memory_reindex_cmd(cwd_str: str, check: bool, use_global: bool) -> None:
    """Detect/repair chroma drift of the file-based mirror (sync --check contract)."""
    store = _memory_store_for(cwd_str, use_global)
    result = store.reindex(check=check)
    if not result.chroma_available:
        click.echo("chroma not installed — reindex is a no-op")
        return
    if check:
        if result.stale:
            for loc in result.stale:
                click.echo(loc)
            click.echo(f"drift: {len(result.stale)} stale entries")
            raise SystemExit(1)
        click.echo("memory index in sync")
        return
    click.echo(f"re-embedded: {result.reembedded}")
