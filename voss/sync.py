"""`voss sync` context contract + orchestrator (V16-01/V16-03).

SyncContext is the single frozen struct every synced artifact renders from
(D-17): layout vars + project facts + capabilities. sync() renders the
managed docs and the VOSS.md workflow fence from one SyncContext, diffs
byte-for-byte against disk, and writes only on difference (R1 idempotency).
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import click

from voss.harness import voss_md
from voss.harness.conventions import _load_memory_config, load_project_facts
from voss.harness.prompt_override import SYNCED_PROMPTS
from voss.layout import Layout, derive_layout
from voss.template_render import render_package_template


@dataclass(frozen=True)
class ReviewFacts:
    """`project.review` block (D-02). enabled=False is the absent-marker (D-04)."""

    enabled: bool = False
    reviewers: tuple[str, ...] = ()


@dataclass(frozen=True)
class SyncContext:
    """Layout vars + project facts + capabilities (D-02, D-05).

    D-04: every field holds an explicit value or an absent-marker (None /
    empty) — never undefined — so StrictUndefined still catches genuine
    template bugs while `{% if %}` blocks omit missing facts.
    """

    # layout vars (derive_layout)
    project_name: str
    project_root: Path
    is_worktree: bool
    command_prefix: str
    voss_dir: Path
    docs_dir: Path
    # project facts (D-02; config wins over detection, D-01)
    type: str | None = None
    install_command: str | None = None
    check_command: str | None = None
    tools: tuple[str, ...] = ()
    review: ReviewFacts = ReviewFacts()
    # capabilities (D-05) + (key, value) facts that came from detection (D-03)
    capabilities: tuple[str, ...] = ()
    detected: tuple[tuple[str, str], ...] = ()


def _detect_capabilities(layout: Layout, review: ReviewFacts) -> tuple[str, ...]:
    """Active Voss capabilities, detected from config + `.voss/` dirs (D-05)."""
    caps: list[str] = []
    memory_cfg = _load_memory_config(layout.project_root)
    if (layout.voss_dir / "memory").is_dir() or memory_cfg:
        caps.append("memory")
        if memory_cfg.get("extract_conventions", True):
            caps.append("conventions")
    if review.enabled:
        caps.append("review")
    if (layout.voss_dir / "eval").is_dir():
        caps.append("eval")
    return tuple(caps)


def build_sync_context(cwd: Path) -> SyncContext:
    """Build the shared SyncContext for `cwd`.

    Wires derive_layout (layout vars) + load_project_facts (project facts:
    `_load_project_config` config block with fs-detection fallback, config
    wins per D-01) + capability detection. Orchestration (write loop) is
    deferred to Plan 03.
    """
    layout = derive_layout(cwd)
    facts, detected = load_project_facts(layout.project_root)

    def _str_tuple(raw: object) -> tuple[str, ...]:
        """Coerce a config list to a string tuple; a bare scalar means one item."""
        if isinstance(raw, (list, tuple)):
            return tuple(str(item) for item in raw)
        if isinstance(raw, str) and raw:
            return (raw,)
        return ()

    raw_review = facts.get("review")
    if isinstance(raw_review, dict):
        review = ReviewFacts(
            enabled=bool(raw_review.get("enabled", False)),
            reviewers=_str_tuple(raw_review.get("reviewers")),
        )
    else:
        review = ReviewFacts()

    tools = _str_tuple(facts.get("tools"))

    def _str_or_none(key: str) -> str | None:
        value = facts.get(key)
        return value if isinstance(value, str) and value else None

    return SyncContext(
        project_name=layout.project_name,
        project_root=layout.project_root,
        is_worktree=layout.is_worktree,
        command_prefix=layout.command_prefix,
        voss_dir=layout.voss_dir,
        docs_dir=layout.docs_dir,
        type=_str_or_none("type"),
        install_command=_str_or_none("install_command"),
        check_command=_str_or_none("check_command"),
        tools=tools,
        review=review,
        capabilities=_detect_capabilities(layout, review),
        # (key, value) pairs straight from the facts dict — robust against
        # detection keys that are not SyncContext field names (D-03).
        detected=tuple((key, str(facts[key])) for key in sorted(detected)),
    )


@dataclass(frozen=True)
class ArtifactStatus:
    path: str
    status: str  # written | unchanged | fence-updated | skipped (edited) | removed


@dataclass(frozen=True)
class SyncResult:
    statuses: tuple[ArtifactStatus, ...]
    detected: tuple[tuple[str, str], ...]  # (fact key, value) pairs from fs detection (D-03)


_DOC_TEMPLATES = (
    ("cheatsheet.md", "cheatsheet.md.jinja"),
    ("commands.md", "commands.md.jinja"),
)
_REVIEW_DOC = ("review.md", "review.md.jinja")
_FENCE_TEMPLATE = "voss_md_fence.md.jinja"
_FENCE_ID = "workflow"
_MANIFEST_NAME = "sync-state.json"


def _write_text_atomic(path: Path, text: str) -> None:
    """mkstemp in dest dir -> write -> os.replace (mirrors voss/cli.py)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(text)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _read_manifest(voss_root: Path) -> dict[str, str]:
    """Read .voss/sync-state.json; missing/malformed fails safe to {} (T-V16-10)."""
    path = voss_root / _MANIFEST_NAME
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str)}


def _diff_write(
    dest: Path,
    rendered: str,
    *,
    voss_root: Path,
    project_root: Path,
    dry_run: bool,
) -> ArtifactStatus:
    """Byte-diff rendered text against disk; write atomically only on difference."""
    resolved = dest.resolve()
    if not resolved.is_relative_to(voss_root):
        raise ValueError(f"refused to write outside .voss: {resolved}")
    rel = _rel(resolved, project_root)
    existing: str | None = None
    if resolved.exists():
        existing = resolved.read_text()
    if existing == rendered:
        return ArtifactStatus(rel, "unchanged")
    if not dry_run:
        _write_text_atomic(resolved, rendered)
    return ArtifactStatus(rel, "written")


def sync(cwd: Path, *, dry_run: bool = False, force: bool = False) -> SyncResult:
    """Regenerate the managed docs, VOSS.md workflow fence, and manifest.

    Idempotent (R1): every artifact is rendered from one SyncContext and
    byte-diffed against disk; an unchanged tree produces zero writes.
    Docs are machine-owned (R3): always regenerated, no edit guard.
    The fence goes through voss_md.write_fence_body without adopt (D-16):
    hash drift raises HashMismatch instead of silently overwriting (R4).
    The drift gate runs before any write, so a refused sync leaves the
    tree untouched; dry_run shares the gate (drift is a real failure per
    D-15, even when reporting-only).
    dry_run (D-14) runs the identical diff pass and writes nothing.
    force (D-16) applies to synced prompts ONLY: it overwrites edited
    prompts and re-adopts when the manifest is missing (D-11). It has no
    effect on docs or the fence.
    """
    context = build_sync_context(cwd)
    ctx_map = asdict(context)
    voss_root = context.voss_dir.resolve()
    project_root = context.project_root
    recorded_hashes = _read_manifest(voss_root)
    statuses: list[ArtifactStatus] = []
    manifest: dict[str, str] = {}

    # Fence drift gate FIRST, before any write: a drifted fence refuses the
    # whole sync with the tree untouched (same HashMismatch as
    # write_fence_body — D-16, R4). Without this ordering a refused sync
    # would already have rewritten docs and left the manifest stale.
    fence_body = render_package_template(
        "voss", f"templates/docs/{_FENCE_TEMPLATE}", ctx_map
    )
    voss_md_path = project_root / "VOSS.md"
    existing_body = voss_md.read_fence_body(voss_md_path, fence_id=_FENCE_ID)

    docs = list(_DOC_TEMPLATES)
    if context.review.enabled:
        docs.append(_REVIEW_DOC)  # D-08: review.md skipped entirely when disabled

    for name, resource in docs:
        rendered = render_package_template("voss", f"templates/docs/{resource}", ctx_map)
        dest = context.docs_dir / name
        manifest[_rel(dest.resolve(), project_root)] = hashlib.sha256(
            rendered.encode()
        ).hexdigest()
        statuses.append(
            _diff_write(
                dest,
                rendered,
                voss_root=voss_root,
                project_root=project_root,
                dry_run=dry_run,
            )
        )

    if not context.review.enabled:
        # Machine-owned cleanup: a review.md generated while review was
        # enabled must not outlive the config flip (R3 ownership).
        stale_review = (context.docs_dir / _REVIEW_DOC[0]).resolve()
        if stale_review.is_relative_to(voss_root) and stale_review.exists():
            if not dry_run:
                stale_review.unlink()
            statuses.append(ArtifactStatus(_rel(stale_review, project_root), "removed"))

    manifest[f"VOSS.md#{_FENCE_ID}"] = hashlib.sha256(fence_body.encode()).hexdigest()
    if existing_body == fence_body:
        statuses.append(ArtifactStatus("VOSS.md", "unchanged"))
    else:
        if not dry_run:
            voss_md.write_fence_body(voss_md_path, fence_id=_FENCE_ID, body=fence_body)
        statuses.append(ArtifactStatus("VOSS.md", "fence-updated"))

    # Synced prompts (R5/R6): hash-guard — never clobber a user edit without
    # hash evidence (D-11), --force overwrites (D-16). Sync-time render only;
    # ${} runtime placeholders pass through untouched (D-18).
    for name, resource in SYNCED_PROMPTS:
        rendered = render_package_template("voss", resource, {})
        dest = (voss_root / "prompts" / f"{name}.txt").resolve()
        if not dest.is_relative_to(voss_root):
            raise ValueError(f"refused to write outside .voss: {dest}")
        rel = _rel(dest, project_root)
        new_hash = hashlib.sha256(rendered.encode()).hexdigest()
        if not dest.exists():
            if not dry_run:
                _write_text_atomic(dest, rendered)
            statuses.append(ArtifactStatus(rel, "written"))
            manifest[rel] = new_hash
            continue
        on_disk = dest.read_text()
        recorded = recorded_hashes.get(rel)
        on_disk_hash = hashlib.sha256(on_disk.encode()).hexdigest()
        edited = recorded is None or on_disk_hash != recorded  # D-11: no evidence => edited
        if edited and not force:
            click.echo(f"warning: {rel} has local edits; skipped (--force to overwrite)", err=True)
            statuses.append(ArtifactStatus(rel, "skipped (edited)"))
            if recorded is not None:
                manifest[rel] = recorded  # keep drift evidence; never adopt silently
            continue
        if on_disk == rendered:
            statuses.append(ArtifactStatus(rel, "unchanged"))
        else:
            if not dry_run:
                _write_text_atomic(dest, rendered)
            statuses.append(ArtifactStatus(rel, "written"))
        manifest[rel] = new_hash

    manifest_text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    statuses.append(
        _diff_write(
            voss_root / _MANIFEST_NAME,
            manifest_text,
            voss_root=voss_root,
            project_root=project_root,
            dry_run=dry_run,
        )
    )

    return SyncResult(statuses=tuple(statuses), detected=context.detected)


__all__ = [
    "ArtifactStatus",
    "ReviewFacts",
    "SyncContext",
    "SyncResult",
    "build_sync_context",
    "sync",
]
