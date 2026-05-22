# Phase F4: Visual Context Heatmap - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-22
**Phase:** F4-visual-context-heatmap
**Areas discussed:** Panel hosting, Data granularity, Pinning & reverse channel, Emission & payload

---

## Panel Hosting

| Option | Description | Selected |
|--------|-------------|----------|
| Collapsible side panel | Right-side drawer (~240px), slides in/out, ⌘I toggle, persistent | ✓ |
| Expanded budget popover | Extend F3 BudgetPopover with file list tab | |
| Dedicated grid pane | Non-terminal pane type in grid tree | |
| Bottom drawer | Horizontal panel below grid (~150px) | |

**User's choice:** Collapsible side panel
**Notes:** With ASCII preview mockup showing file list with token counts.

| Option | Description | Selected |
|--------|-------------|----------|
| Per-pane | Panel content switches on focus change | ✓ |
| Global aggregate | Shows all agent panes merged | |

**User's choice:** Per-pane

| Option | Description | Selected |
|--------|-------------|----------|
| Outside grid (overlay) | Panel overlays right edge, grid doesn't reflow | ✓ |
| Inside grid (push) | Panel pushes grid left, terminals resize | |
| You decide | Planner discretion | |

**User's choice:** Outside grid (overlay)

| Option | Description | Selected |
|--------|-------------|----------|
| Pane index + cwd | Header shows "Context — ●3 ~/project" | ✓ |
| Agent command | Header shows agent command string | |
| You decide | Planner discretion | |

**User's choice:** Pane index + cwd

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed 240px | No drag-resize, consistent | ✓ |
| Resizable with drag handle | User can drag to resize, min 180px / max 400px | |
| You decide | Planner discretion | |

**User's choice:** Fixed 240px

| Option | Description | Selected |
|--------|-------------|----------|
| Persist in settings | Store open/closed in ~/.config/voss-app/settings.json | ✓ |
| Always start closed | No persistence | |
| Persist in session.json | Per-project open/closed | |

**User's choice:** Persist in settings

| Option | Description | Selected |
|--------|-------------|----------|
| 150ms CSS slide | transform: translateX() with ease-out | ✓ |
| Instant toggle | display: none/block, no animation | |

**User's choice:** 150ms CSS slide

| Option | Description | Selected |
|--------|-------------|----------|
| Empty state with hint | Muted "No agent context" message | ✓ |
| Auto-hide panel | Collapse when shell focused | |
| Show last agent context | Keep stale context visible | |

**User's choice:** Empty state with hint

| Option | Description | Selected |
|--------|-------------|----------|
| Status bar button | Icon in A10 status bar right cluster | ✓ |
| PaneHeader button | Button in each agent pane's header | |
| Command palette only | No visible button, ⌘I/⌘P only | |

**User's choice:** Status bar button

| Option | Description | Selected |
|--------|-------------|----------|
| No search in F4 | Scroll suffices, defer search | ✓ |
| Simple filter input | Text input filters file list | |

**User's choice:** No search in F4

| Option | Description | Selected |
|--------|-------------|----------|
| Below overlays | Same z-tier as grid | ✓ |
| Above grid, below modals | Explicit z-index tier | |

**User's choice:** Below overlays

| Option | Description | Selected |
|--------|-------------|----------|
| Compact summary row | "1,248 / 200k tokens" + progress bar at top | ✓ |
| No summary, just file list | Budget bar already shows totals | |
| You decide | Planner discretion | |

**User's choice:** Compact summary row

---

## Data Granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Per-file | Each row = one file path with tokens + state | ✓ |
| Per-context-slot | Each row = one context slot (system/tool/conversation) | |
| Hybrid: files + categories | Tree-style grouping by category | |

**User's choice:** Per-file

| Option | Description | Selected |
|--------|-------------|----------|
| 3-state: full/compressed/dropped | Green/yellow/gray color coding | ✓ |
| 2-state: in-context/out | Simple binary | |
| 4-state: + pinned | Fourth visual state for pins | |

**User's choice:** 3-state

| Option | Description | Selected |
|--------|-------------|----------|
| By token count descending | Biggest consumers at top | ✓ |
| By recency | Most recently accessed first | |
| By state then tokens | Group by state, then sort | |
| You decide | Planner discretion | |

**User's choice:** By token count descending

| Option | Description | Selected |
|--------|-------------|----------|
| Name + tokens + mini bar | Left-truncated filename, count, proportional bar. Hover for full path | ✓ |
| Name + tokens + percentage | No bar, just percentage text | |
| Full path + tokens + bar | Complete relative path | |

**User's choice:** Name + tokens + mini bar

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, special rows | System prompt + conversation as styled rows at top | ✓ |
| Files only | Invisible overhead | |
| Summary only in header | Non-file tokens as "overhead" in summary | |

**User's choice:** Yes, special rows

---

## Pinning & Reverse Channel

| Option | Description | Selected |
|--------|-------------|----------|
| Ship with pinning | Full interactive feature | ✓ |
| Read-only first | Heatmap without reverse channel | |
| Pin UI visible but non-functional | Buttons disabled with "Coming soon" | |

**User's choice:** Ship with pinning

| Option | Description | Selected |
|--------|-------------|----------|
| PTY stdin injection | ADE writes ESC]1337;voss-pin= into PTY stdin | ✓ |
| Shared pin file | .voss/context-pins.json watched by harness | |
| Tauri sidecar IPC | New HTTP/socket channel | |
| You decide | Planner discretion | |

**User's choice:** PTY stdin injection

| Option | Description | Selected |
|--------|-------------|----------|
| Next iteration | Pin queued, applied next LLM request | ✓ |
| Immediate context rebuild | Interrupt current cycle | |
| You decide | Planner discretion | |

**User's choice:** Next iteration

| Option | Description | Selected |
|--------|-------------|----------|
| Immune to compression | Pinned file stays full fidelity always | ✓ |
| Always included, may compress | Guarantees presence not fidelity | |
| Priority ordering | Preferentially kept full | |

**User's choice:** Immune to compression

| Option | Description | Selected |
|--------|-------------|----------|
| No, only existing context files | Pin button only on files already in context | ✓ |
| Yes, pin any file path | Add file browser for arbitrary paths | |
| You decide | Planner discretion | |

**User's choice:** No, only existing context files

---

## Emission & Payload

| Option | Description | Selected |
|--------|-------------|----------|
| New voss-context= type | Separate OSC type, new PtyEvent variant | ✓ |
| Extend voss-budget= payload | Add file list to budget payload | |

**User's choice:** New voss-context= type

| Option | Description | Selected |
|--------|-------------|----------|
| Per-iteration, after budget | Same cadence as F3 at end_iteration() | ✓ |
| On context change only | Emit only when file list changes | |
| Per tool call | After every fs_read/fs_write | |

**User's choice:** Per-iteration, after budget

| Option | Description | Selected |
|--------|-------------|----------|
| path + tokens + state + pinned | Minimal complete payload for 3-state + pin model | ✓ |
| Above + compression ratio | Add original_tokens field | |
| You decide | Planner discretion | |

**User's choice:** path + tokens + state + pinned

| Option | Description | Selected |
|--------|-------------|----------|
| Full snapshot each time | Complete file list every emission, ~4KB | ✓ |
| Delta only | Changes since last emit | |
| Cap at N files | Top-N by token count | |

**User's choice:** Full snapshot each time

| Option | Description | Selected |
|--------|-------------|----------|
| Via next context emission | pinned:true in next snapshot, self-healing | ✓ |
| Immediate ack via separate OSC | voss-pin-ack= immediately | |
| No ack, optimistic UI | Frontend toggles instantly | |

**User's choice:** Via next context emission

---

## Claude's Discretion

None — user made explicit choices for all decisions.

## Deferred Ideas

None — discussion stayed within phase scope.
