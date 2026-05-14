---
title: Project Memory — VOSS.md + Cross-Session Recall
trigger_condition: First dogfood session where context loss hurts (user retypes the same project facts twice), OR external user requests "remember this about my project".
planted_date: 2026-05-14
related: [[tui-shell-textual]], [[voss-agent-unfair-advantage]]
---

## Summary

Give the Voss harness a persistent project-memory layer so it stops re-learning the repo every session. Two tiers:

1. **VOSS.md** — checked-into-repo project file (analog to `CLAUDE.md`). Human-curated: project intent, conventions, gotchas, build commands.
2. **Session-spanning recall** — agent-curated memory store (uses Voss's existing `memory.semantic` / `memory.episodic` primitives — see `voss/runtime/memory*`). Captures: decisions made across sessions, user style/preferences observed, repo idioms learned.

## Why

User flagged this as the most interesting capability axis ("project memory could be interesting"). It's also Voss's structural advantage: `memory.episodic(capacity: N turns)` and `memory.semantic(source: ...)` are already first-class language primitives. The harness should *use its own runtime* for memory — proof-by-existence that the language earns its keep.

## Scope sketch

- VOSS.md loader: read at session start, inject into harness system context. Section conventions (project, build, style, do/don't).
- Memory store: file-backed (`.voss/memory/`) — episodic (per-session) + semantic (cross-session, indexed). Reuse runtime memory primitives.
- Recall surface: agent decides when to query; user can `/recall <query>` slash command (when TUI lands).
- Forgetting: explicit `/forget` + time-decay defaults. Privacy-first: nothing leaves the repo by default.
- Save flow: end-of-session prompt — "remember any of these decisions?" — agent extracts candidates, user picks.

## Non-goals

- Cross-project memory sharing (separate concern; raises privacy questions).
- Cloud memory store (local-first; cloud is a post-v0.2 conversation).

## Open questions

- Is VOSS.md global per-project, or hierarchical (root + per-directory like CLAUDE.md)?
- How does memory interact with `voss sessions` / `voss resume` (CLIH-07/08)?
- Do we surface memory contents in the TUI (browseable panel) or only via slash commands?
- Schema: free-form markdown vs structured records? (Markdown likely — matches CLAUDE.md ecosystem.)

## Promotion path

Strong candidate for v0.2 first phase — depends on dogfood signal, not new infra. Could land before TUI if user demand presents.
