---
title: TUI Shell for Voss Harness (Textual-based)
trigger_condition: v0.1 daily-driver feedback surfaces UX friction with line-streamed CLI, OR first external user runs `voss chat` on a real codebase and reports interaction pain.
planted_date: 2026-05-14
related: [[project-memory-voss-md]], [[agent-capability-surface]]
---

## Summary

Replace current `rich`-based line-streamed CLI for `voss chat`/`voss do` with a full-screen TUI (Textual or equivalent). Match Claude Code / Aider interaction depth; expose Voss's language primitives in the UI so users *see* what makes Voss different.

## Why

Today: `voss chat` prints stream to stdout. No per-hunk diff approval, no slash palette discovery, no scrollable session history, no live view of running `.voss` workflow internals. User confirmed every gap on this list hurts ("all of them honestly"). This is the #1 thing blocking the harness from feeling like a real daily-driver coding agent.

## Scope sketch (not a plan — for trigger-time scoping)

- Textual app shell with: header (session id, budget remaining), main pane (turn history), input bar (slash command palette w/ autocomplete), modal pane (diff approval per hunk, permission prompts).
- Streaming view of running `.voss` workflow: probable values with confidence bars, `ctx(budget:)` token meter draining live, `spawn`/`gather` sub-agent panels.
- Session resume UX: scroll prior turns, fork from any turn, branch sessions.
- Keybindings: vim-ish navigation, `/` slash palette, `?` help overlay.
- Fallback: `--plain` flag preserves current line mode for pipes/CI.

## Non-goals (at trigger time)

- Editor integration (separate VSCode extension track — EDIT-01/02).
- Web UI (far post-v0.1).

## Open questions

- Textual vs prompt_toolkit vs hand-rolled curses? (Textual likely — composability, css-ish styling.)
- Does TUI block on Windows console quirks? (Vendored Python via M6 npm — verify.)
- Does live workflow visualization need new runtime hooks, or can recorder.py stream already? (See `voss/harness/recorder.py`.)

## Promotion path

When trigger fires: `/gsd-spec-phase` → `/gsd-discuss-phase` → `/gsd-plan-phase`. Likely splits into 2 phases (shell skeleton; workflow-internals visualization).
