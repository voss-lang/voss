---
title: Agent Capability Surface — Tools, Skills, MCP, Multi-Agent in Chat
trigger_condition: TUI shell ([[tui-shell-textual]]) lands and exposes a stable plugin/skill API; capabilities slot in as they prove valuable. OR external user reports "voss chat can't do X that Claude Code can".
planted_date: 2026-05-14
related: [[tui-shell-textual]], [[project-memory-voss-md]], [[voss-agent-unfair-advantage]]
---

## Summary

Buildout of agent capabilities sitting *above* the TUI shell. User signaled all of these matter ("all of those"); track as one seed for sequencing, split into sub-phases at promotion time.

## Capability inventory

1. **Codebase intelligence**
   - LSP client (reuse `voss/harness/` symbol scanning if any; else add).
   - `ast-grep` / `tree-sitter` symbol search exposed as a tool.
   - Project index built on session start; refreshed on file watch.

2. **Voss-aware tools** *(unfair advantage axis — see [[voss-agent-unfair-advantage]])*
   - `.voss` lint/type-check as a first-class agent skill.
   - Probable-value inspector: show confidence + propagation graph for a chosen value at a runtime point.
   - Budget tracer: visualize `ctx(budget:)` consumption across a workflow run.
   - `.voss` → Python diff viewer: agent edits `.voss`, user sees both sides.

3. **MCP bridge** *(already roadmap candidate DIST-03 — link here, do not duplicate)*
   - Bring external MCP server ecosystem into harness.
   - Two directions: consume external MCP tools, expose harness skills as MCP server.

4. **Multi-agent in chat**
   - Expose runtime `spawn`/`gather` to the chat session — user says "research X" → harness spawns sub-agent in a side panel (TUI), user watches budgets per sub-agent.
   - Sub-agent message bus visible in UI.
   - This is where M4 dogfood (`voss-authored harness loop`) compounds.

5. **Long-running / watch tasks**
   - Background job manager (test watcher, dev server, file-watch driven re-checks).
   - Surfaced in TUI as a bottom-pane status strip.

6. **Skill / plugin marketplace**
   - Third-party `.voss` skills installable (`voss skill add <name>`).
   - Trust model: signed manifests, sandbox boundary, permission scopes.
   - Registry source TBD (GitHub-based likely for v0.2; central registry later).

## Why grouped

User said all of these matter; sequencing comes from the TUI landing first (capabilities need a UI surface) plus MCP DIST-03 being a parallel candidate. Splitting now is premature.

## Promotion path

When trigger fires: split into capability-by-capability phases. Suggested order at promotion time:
1. Codebase intelligence (highest leverage, lowest novelty risk).
2. Voss-aware tools (differentiator — pairs with M4 outputs).
3. MCP bridge (existing roadmap candidate — promote DIST-03 in coordination).
4. Multi-agent in chat (depends on TUI panels).
5. Long-running tasks (depends on TUI bottom pane).
6. Skill marketplace (last — needs trust/sandbox story first).
