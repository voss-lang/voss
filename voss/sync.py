"""`voss sync` shared render-context contract (V16-01).

SyncContext is the single frozen struct every synced artifact renders from
(D-17): layout vars + project facts + capabilities. This module deliberately
contains ONLY the contract and its builder — the sync write-loop (render,
diff, apply, manifest) lands in Plan 03.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from voss.harness.conventions import _load_memory_config, load_project_facts
from voss.layout import Layout, derive_layout


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
    # capabilities (D-05) + fact keys that came from detection (D-03 marker)
    capabilities: tuple[str, ...] = ()
    detected: frozenset[str] = frozenset()


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

    raw_review = facts.get("review")
    if isinstance(raw_review, dict):
        review = ReviewFacts(
            enabled=bool(raw_review.get("enabled", False)),
            reviewers=tuple(raw_review.get("reviewers") or ()),
        )
    else:
        review = ReviewFacts()

    raw_tools = facts.get("tools")
    tools = tuple(raw_tools) if isinstance(raw_tools, (list, tuple)) else ()

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
        detected=detected,
    )


__all__ = ["ReviewFacts", "SyncContext", "build_sync_context"]
