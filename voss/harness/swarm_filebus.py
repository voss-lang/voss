"""Swarm file-bus — pure file IO for the A13 task/result transport (R3).

Under the R3 reconciliation (SWARM-RECONCILIATION.md), a swarm member is a real
CLI (claude/codex/opencode/…) that cannot subscribe to voss's SSE bus — files are
the only IPC a black-box CLI offers. So the A13 file-bus is the LIVE coordination
transport, not an audit afterthought: the host writes one `tasks/<role>.task.md`
per member, the member writes back `results/<role>.result.md`, and completion is
detected by that result file appearing.

This module is deliberately pure file IO (no SwarmStore, no provider, no git) so
it is trivially unit-testable and importable from both the headless server spawn
path and the GUI/Rust execution plane. The on-disk formats are the EXACT shapes
documented in A13-SPEC.md "File Formats" — keeping them byte-compatible means the
existing frontend `swarmReconcile.ts` manifest reader and any A13-era CLI prompt
stay valid.

The bus lives in the MAIN checkout's `.voss/swarm/<id>/` (shared across members),
NOT inside any per-member git worktree: members are hermetic in their worktree and
never read `.voss` themselves — the host hands each CLI its task inline.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .swarm_store import Task

# Result-file `status` values a member may report. We do not enforce these on
# read (forward-compatible), but they document the contract for writers.
STATUS_COMPLETE = "complete"
STATUS_FAILED = "failed"


# ---------------------------------------------------------------------------
# Directory helpers — create-as-needed so callers never pre-mkdir.
# ---------------------------------------------------------------------------
def swarm_dir(repo_root: str | Path, swarm_id: str) -> Path:
    """`<repo_root>/.voss/swarm/<swarm_id>`, created if missing.

    repo_root is the MAIN checkout (not a member worktree) — the bus is shared.
    """
    d = Path(repo_root) / ".voss" / "swarm" / swarm_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def tasks_dir(repo_root: str | Path, swarm_id: str) -> Path:
    """`<swarm>/tasks` — one `<role>.task.md` per member, written by the host."""
    d = swarm_dir(repo_root, swarm_id) / "tasks"
    d.mkdir(parents=True, exist_ok=True)
    return d


def results_dir(repo_root: str | Path, swarm_id: str) -> Path:
    """`<swarm>/results` — one `<role>.result.md` per member, written by the CLI."""
    d = swarm_dir(repo_root, swarm_id) / "results"
    d.mkdir(parents=True, exist_ok=True)
    return d


def shared_dir(repo_root: str | Path, swarm_id: str) -> Path:
    """`<swarm>/shared` — `context.md` shared project context for all members."""
    d = swarm_dir(repo_root, swarm_id) / "shared"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Frontmatter codec
# ---------------------------------------------------------------------------
def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Split a `---`-delimited YAML frontmatter document into (meta, body).

    pyyaml is already vendored (yaml 6.x), so we parse the frontmatter with it
    rather than hand-rolling a parser. A document with no leading `---` is treated
    as all-body with empty metadata (tolerant read).
    """
    if not text.startswith("---"):
        return {}, text
    # Frontmatter is the region between the first two `---` fences.
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    _, raw_meta, body = parts
    meta = yaml.safe_load(raw_meta) or {}
    if not isinstance(meta, dict):
        meta = {}
    # The body keeps a single leading newline after the closing fence; strip just
    # that separator so callers get the markdown as authored.
    return meta, body.lstrip("\n")


def _dump_frontmatter(meta: dict, body: str) -> str:
    """Render (meta, body) back into a `---`-fenced markdown document.

    `sort_keys=False` preserves the field order the writer chose so the file reads
    top-to-bottom like the A13-SPEC example (swarm/agent/cli/model).
    """
    fm = yaml.safe_dump(meta, sort_keys=False, default_flow_style=False).strip()
    return f"---\n{fm}\n---\n\n{body}"


# ---------------------------------------------------------------------------
# Task files (host → member)
# ---------------------------------------------------------------------------
def write_task_file(
    repo_root: str | Path,
    swarm_id: str,
    role_name: str,
    task: Task,
    *,
    agent: str,
    model: str,
    context: str = "",
) -> Path:
    """Write `tasks/<role_name>.task.md` for one member, A13 format.

    The frontmatter carries the routing axis (swarm/agent/cli/model) the R3
    runtime needs; the body restates the task goal, the member's ownedFiles (so an
    advisory-only CLI still sees its scope), and the explicit "write your result
    to results/<role>.result.md" instruction that closes the completion loop. We
    set both `agent` and `cli` to the same value because A13's example used `cli`
    while R3's `Role` calls the axis `agent` — emitting both keeps every reader
    (frontend manifest reader expects `cli`) satisfied.
    """
    meta = {
        "swarm": swarm_id,
        "agent": agent,
        "cli": agent,
        "model": model,
    }
    owned = "\n".join(f"- `{f}`" for f in task.owned_files) or "- (none declared)"
    context_block = context.strip() or (
        "Read `.voss/swarm/shared/context.md` for shared project context."
    )
    body = (
        "## Your Task\n\n"
        f"{task.goal}\n\n"
        "## Context\n\n"
        "- This is part of a coordinated swarm; other agents work on related tasks.\n"
        f"- {context_block}\n"
        "- You OWN exactly these files — do NOT modify anything else:\n"
        f"{owned}\n\n"
        "## When Done\n\n"
        f"Write your results summary to `results/{role_name}.result.md` with:\n"
        "- What you changed\n"
        "- Files modified\n"
        "- Any issues encountered\n"
    )
    path = tasks_dir(repo_root, swarm_id) / f"{role_name}.task.md"
    path.write_text(_dump_frontmatter(meta, body), encoding="utf-8")
    return path


def write_shared_context(repo_root: str | Path, swarm_id: str, text: str) -> Path:
    """Write `shared/context.md` — project context every member's task references."""
    path = shared_dir(repo_root, swarm_id) / "context.md"
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Result files (member → host)
# ---------------------------------------------------------------------------
class ResultFile(BaseModel):
    """Parsed `results/<role>.result.md` — a member's completion report.

    extra="ignore" mirrors the SwarmStore `_Base` convention: a newer CLI may add
    frontmatter keys, and a forward-compatible reader must not raise on them.
    """

    model_config = ConfigDict(extra="ignore")

    agent: str = ""
    status: str = STATUS_COMPLETE
    files_modified: list[str] = Field(default_factory=list)
    duration_secs: int | None = None
    summary: str = ""


def result_path(repo_root: str | Path, swarm_id: str, role_name: str) -> Path:
    """Absolute path of a member's result file (may not exist yet)."""
    return results_dir(repo_root, swarm_id) / f"{role_name}.result.md"


def result_exists(repo_root: str | Path, swarm_id: str, role_name: str) -> bool:
    """True once the member has written its result file — the completion signal."""
    return result_path(repo_root, swarm_id, role_name).exists()


def read_result_file(
    repo_root: str | Path, swarm_id: str, role_name: str
) -> ResultFile | None:
    """Parse `results/<role_name>.result.md` into a ResultFile.

    Returns None when the file does not exist yet (the common poll case — the
    member is still working), so callers can distinguish "not done" from a parsed
    result. The markdown body is taken as the summary so a member that omits a
    `summary:` key still reports its prose write-up.
    """
    path = result_path(repo_root, swarm_id, role_name)
    if not path.exists():
        return None
    meta, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    # Body wins as the human summary; a frontmatter `summary:` is a fallback for
    # writers that put everything in metadata.
    summary = body.strip() or str(meta.get("summary", ""))
    return ResultFile(
        agent=str(meta.get("agent", "")),
        status=str(meta.get("status", STATUS_COMPLETE)),
        files_modified=list(meta.get("files_modified", []) or []),
        duration_secs=meta.get("duration_secs"),
        summary=summary,
    )
