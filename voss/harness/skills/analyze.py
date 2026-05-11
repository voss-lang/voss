"""`/analyze` skill: hybrid bootstrap of `.voss/` + `.voss-cache/`.

Harness owns 4 cognition files (preserve-if-exists). LLM owns only
`.voss/architecture.md` via a single fs_write driven from a prompt that
carries all pre-computed inventory. Post-turn rebuilds repo.idx +
`.voss/.gitignore` + appends `.voss-cache/` to project-root `.gitignore`.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import click

from .. import cognition
from ..agent import run_turn


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

    prompt = cognition.bootstrap_prompt(inventory)
    arch_path = cognition.voss_dir(cwd) / "architecture.md"
    arch_backup = arch_path.read_text() if arch_path.exists() else None

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

    arch_ok = False
    if arch_path.exists():
        try:
            text = arch_path.read_text()
        except OSError:
            text = ""
        if cognition.FRONTMATTER_RE.match(text):
            arch_ok = True

    if not arch_ok:
        if arch_backup is not None:
            arch_path.write_text(arch_backup)
            click.echo(
                "warning: architecture.md regeneration failed schema check; "
                "rolled back to previous version",
                err=True,
            )
        else:
            click.echo(
                "warning: architecture.md not written by agent — re-run /analyze",
                err=True,
            )

    idx = cognition.build_repo_idx(cwd)
    idx_path = cognition.cache_dir(cwd) / "repo.idx"
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    idx_path.write_text(json.dumps(idx, indent=2))

    new_stubs = sum(1 for v in stubs_result.values() if v)
    click.echo(
        f"cognition initialized: .voss/ ({new_stubs} new stubs, "
        f"architecture.md refreshed) + .voss-cache/repo.idx "
        f"({len(idx['files'])} files indexed)"
    )
