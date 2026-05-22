# Phase F3: Budget & Token Visualization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-21
**Phase:** F3-budget-token-visualization
**Areas discussed:** Data pipeline, HUD placement & display, Metrics scope & format, Update cadence & performance

---

## Data Pipeline — harness → ADE

### Q1: How should budget/cost data flow from the harness process to the ADE UI?

| Option | Description | Selected |
|--------|-------------|----------|
| OSC escape sequences in PTY stream | Harness emits custom OSC codes interleaved with terminal output. Rust reader parses them out. Reuses existing Channel<PtyEvent>. | ✓ |
| File watcher on session files | Rust file watcher detects session file changes, reads budget values, pushes to frontend. | |
| Sidecar Unix socket / named pipe | Harness opens local socket; ADE connects as client. Structured JSON messages. | |

**User's choice:** OSC escape sequences (Recommended)
**Notes:** Zero new IPC — same pattern as OSC title already parsed in A2.

### Q2: What OSC code number?

| Option | Description | Selected |
|--------|-------------|----------|
| OSC 1337 with voss prefix | iTerm2-style private range. `voss-budget=` prefix avoids collisions. Extensible namespace. | ✓ |
| OSC 9999 (private range) | High unused number. No namespace convention. | |
| You decide | Planner picks. | |

**User's choice:** OSC 1337 with `voss-budget=` prefix

### Q3: Cumulative totals or deltas?

| Option | Description | Selected |
|--------|-------------|----------|
| Cumulative totals | Each emission has full state. Idempotent. | ✓ |
| Per-iteration deltas | Smaller payloads but requires frontend accumulation. | |
| Both | Redundant but self-correcting. | |

**User's choice:** Cumulative totals

### Q4: When should the harness emit?

| Option | Description | Selected |
|--------|-------------|----------|
| After each LLM response | Once per iteration at end_iteration() call. | ✓ |
| After each tool call + LLM response | Higher frequency. | |
| You decide | Planner picks. | |

**User's choice:** After each LLM response

---

## HUD Placement & Display

### Q5: Where should the budget/cost HUD live?

| Option | Description | Selected |
|--------|-------------|----------|
| Per-pane header bar | Budget meter in 22px PaneHeader for agent panes only. | ✓ |
| A10 status bar cluster | Bottom bar, focused pane only. | |
| Both — header mini + status bar detail | Two surfaces, different density. | |

**User's choice:** Per-pane header bar

### Q6: How should the budget bar render?

| Option | Description | Selected |
|--------|-------------|----------|
| Right-aligned cost + thin bar | Cost text + mini bar before ⋯ menu. Semantic tokens. | ✓ |
| Full-width sub-bar below header | 2-3px bar spanning full width. Adds height. | |
| You decide | Planner picks. | |

**User's choice:** Right-aligned cost + thin bar

### Q7: What about unbounded agent runs?

| Option | Description | Selected |
|--------|-------------|----------|
| Cost only, no bar | Just '$0.08' when no limit. Bar needs a cap. | ✓ |
| Bar at 0% forever | Empty bar, looks broken. | |
| Hide entire segment | Nothing shown without budget. | |

**User's choice:** Cost only, no bar

### Q8: Color thresholds?

| Option | Description | Selected |
|--------|-------------|----------|
| 3-tier color | 0-70% accent, 70-90% warning, 90-100% error. | ✓ |
| Single color | Always accent. | |
| You decide | Planner picks. | |

**User's choice:** 3-tier color

---

## Metrics Scope & Format

### Q9: What metrics at a glance?

| Option | Description | Selected |
|--------|-------------|----------|
| Cost + budget % only | Header shows cost + bar. Detail in popover. | ✓ |
| Cost + tokens + model | All inline. Crowded. | |
| Tokens + budget bar only | No cost display. | |

**User's choice:** Cost + budget bar; tokens/model/iterations in popover

### Q10: Click-to-popover detail?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, click-to-popover | Reuses A10 Popover. Tokens, model, iterations, cost. | ✓ |
| Hover tooltip only | Lightweight but less discoverable. | |
| No detail view in F3 | Ship minimal, iterate later. | |

**User's choice:** Click-to-popover

### Q11: Budget state persistence?

| Option | Description | Selected |
|--------|-------------|----------|
| No persistence — fresh on restart | Self-heals after first OSC emission. | ✓ |
| Cache in session.json | Zero-gap but adds schema coupling. | |
| Read from F1 registry | More structured but registry not designed for live data. | |

**User's choice:** No persistence

---

## Update Cadence & Performance

### Q12: Concurrent multi-pane budget updates?

| Option | Description | Selected |
|--------|-------------|----------|
| Per-pane store, no coordination | Each pane owns its budget signal independently. | ✓ |
| Global budget store | Single store keyed by pane ID. Enables aggregation. | |
| You decide | Planner picks. | |

**User's choice:** Per-pane local signal

### Q13: Visual transitions?

| Option | Description | Selected |
|--------|-------------|----------|
| CSS transition on bar width | 150ms ease-out. prefers-reduced-motion respected. | ✓ |
| No animation | Instant snap. | |
| You decide | Planner picks. | |

**User's choice:** 150ms CSS transition

### Q14: Debounce in Rust reader?

| Option | Description | Selected |
|--------|-------------|----------|
| No debounce needed | Per-LLM-response cadence is naturally low-frequency. | ✓ |
| 100ms debounce | Safety net. Adds complexity. | |
| You decide | Planner picks. | |

**User's choice:** No debounce

---

## Claude's Discretion

None — user selected recommended options for all decisions.

## Deferred Ideas

None — discussion stayed within phase scope.
