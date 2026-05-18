# Phase A3: voss-app Grid Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-18
**Phase:** A3-voss-app-grid-engine
**Areas discussed:** N-pane renderer strategy, Split & equalize geometry, Directional focus tie-break, Close → focus + last-pane

SPEC.md was loaded (8 requirements locked). Discussion was scoped to HOW only; WHAT/why not re-asked.

---

## N-pane renderer strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Canvas per-pane, researcher validates @9 | Keep A2 D-01 xterm.js Canvas per pane; RESEARCH validates SPEC 9-pane perf bar, documents WebGL fallback only if Canvas fails. Avoids WebGL context-loss bug class. | ✓ |
| WebGL pooled context | xterm.js WebGL addon, shared/pooled context for headroom; reintroduces GPU/VM context-loss class A2 avoided. | |
| Researcher owns it, no preset | No preference locked; researcher picks purely against the SPEC perf bar. | |

**User's choice:** Canvas per-pane, researcher validates @9 (Recommended)
**Notes:** Recorded as a research directive — Canvas is the default; WebGL is a documented fallback gated on a failed 9-pane benchmark, not adopted preemptively. User favors A2's deliberate context-loss-avoidance over preemptive perf headroom.

---

## Split & equalize geometry

| Option | Description | Selected |
|--------|-------------|----------|
| 50/50 split + ⌘= rebalances whole tree | New sibling always 50%; ⌘= resets every split node to even (tmux even-* / i3). | ✓ |
| 50/50 split + ⌘= only focused subtree | Even split on insert; ⌘= equalizes only the focused pane's parent subtree. | |
| Proportional split + ⌘= whole tree | New sibling proportional share; ⌘= global rebalance. | |
| Let Claude decide | Planner discretion against Variant B density goal. | |

**User's choice:** 50/50 split + ⌘= rebalances whole tree (Recommended)
**Notes:** Chosen for predictability and the power-user muscle-memory model the Variant B sketch targets. `⌘D` fork reuses the same 50/50 insertion.

---

## Directional focus tie-break

| Option | Description | Selected |
|--------|-------------|----------|
| Nearest to focused pane's edge-midpoint (i3 style) | Project focused-edge-midpoint onto candidate shared edges; nearest wins. Deterministic, well-known. | ✓ |
| Largest shared border | Focus neighbor with most shared border length. | |
| Most-recently-focused among candidates | Track focus history; lands on most-recently-focused bordering candidate. | |
| Let Claude decide | Planner discretion; default to i3 unless research finds better. | |

**User's choice:** Nearest to focused pane's edge-midpoint, i3 style (Recommended)
**Notes:** Deterministic from layout alone (testable), no focus-history state required.

---

## Close → focus + last-pane

| Option | Description | Selected |
|--------|-------------|----------|
| Focus → expanded sibling; last pane → auto-spawn fresh | Focus to the sibling subtree that fills the space; closing final pane spawns a fresh default pane (app never empty). | ✓ |
| Focus → most-recently-focused; last pane → empty state | Focus to MRU surviving pane; last close shows empty state with "new pane" affordance. | |
| Focus → next index; last pane → quit app | Focus by next index; last close quits the app. | |
| Let Claude decide | Planner discretion. | |

**User's choice:** Focus → expanded sibling; last pane → auto-spawn fresh (Recommended)
**Notes:** Deliberate "app is never empty" product stance; avoids accidental-quit on stray `⌘W`; no empty-state surface in A3.

---

## Claude's Discretion

- Pane index recompute algorithm on close/structure change (positional reindex per GRD-03 "stable L-to-R, top-to-bottom" + D-04 — no sparse indices).
- Drag-resize debounce, PTY `SIGWINCH`/winsize ioctl timing, scrollback reflow on resize (inherited from A2 Claude-discretion; correctness + 20×5 clamp are the only hard requirements).
- Solid→Rust mirror sync cadence during an active drag (mirror-on-drag-end vs. throttled mid-drag), bounded by "matches after the change settles."
- Tauri command vs. event-stream mechanism for the mirror (rides A1 D-09 seam; exact shape = planner/researcher).

## Deferred Ideas

None — discussion stayed within A3 scope. Adjacent capabilities are already SPEC-fenced to their owning phases (presets/save-load → A4, session restore → A6, status bar → A9, command palette → A7).
