"""`/analyze` skill: hybrid bootstrap of `.voss/` + `.voss-cache/`.

Harness owns 4 cognition files (preserve-if-exists). LLM owns the
`id=architecture` fence body of `VOSS.md` (post-M8). The agent emits a
single `fs_write` to a staging path; the harness folds the staged content
into the fence atomically via `voss_md.write_fence_body`. Post-turn
rebuilds `repo.idx` + `.voss/.gitignore` + appends `.voss-cache/` to the
project-root `.gitignore`.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import click

from .. import cognition, voss_md
from ..agent import run_turn


STAGE_FILENAME = ".analyze.staging.md"


def run(
    *,
    cwd: Path,
    provider,
    history,
    record,
    renderer,
    tools,
    gate,
) -> None:
    inventory = cognition.build_bootstrap_inventory(cwd)
    stubs_result = cognition.init_voss_stubs(cwd, inventory=inventory)
    cognition.write_voss_gitignore(cwd)
    cognition.append_gitignore_line_idempotent(cwd / ".gitignore", ".voss-cache/")

    voss_md_path = cwd / "VOSS.md"
    fence_id = "architecture"
    stage_path = cognition.voss_dir(cwd) / STAGE_FILENAME

    arch_backup: str | None = None
    try:
        arch_backup = voss_md.read_fence_body(voss_md_path, fence_id=fence_id)
    except voss_md.HashMismatch as exc:
        arch_backup = exc.on_disk
    except (OSError, UnicodeDecodeError):
        arch_backup = None

    stage_path.unlink(missing_ok=True)
    prompt = cognition.bootstrap_prompt(inventory, target_path=f".voss/{STAGE_FILENAME}")

    asyncio.run(
        run_turn(
            prompt,
            tools=tools,
            cwd=cwd,
            renderer=renderer,
            model=record.model,
            provider=provider,
            history=history,
            permissions=gate,
            cognition=None,
            session_id=record.id,
        )
    )

    staged: str | None = None
    if stage_path.exists():
        try:
            staged = stage_path.read_text()
        except (OSError, UnicodeDecodeError):
            staged = None

    arch_ok = staged is not None and bool(cognition.FRONTMATTER_RE.match(staged))

    if arch_ok:
        voss_md.write_fence_body(voss_md_path, fence_id=fence_id, body=staged)
    else:
        if arch_backup is not None:
            voss_md.write_fence_body(voss_md_path, fence_id=fence_id, body=arch_backup)
            click.echo(
                "warning: architecture fence regeneration failed schema check; "
                "rolled back to previous version",
                err=True,
            )
        else:
            click.echo(
                "warning: architecture fence not written by agent — re-run /analyze",
                err=True,
            )

    stage_path.unlink(missing_ok=True)

    idx = cognition.build_repo_idx(cwd)
    idx_path = cognition.cache_dir(cwd) / "repo.idx"
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    idx_path.write_text(json.dumps(idx, indent=2))

    new_stubs = sum(1 for v in stubs_result.values() if v)
    click.echo(
        f"cognition initialized: .voss/ ({new_stubs} new stubs, "
        f"architecture fence refreshed) + .voss-cache/repo.idx "
        f"({len(idx['files'])} files indexed)"
    )
