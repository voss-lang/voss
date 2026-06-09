# Phase V15: Live Plane Integration (sidecar handshake + structured pane rendering) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-09
**Phase:** V15-Live Plane Integration (sidecar handshake + structured pane rendering)
**Areas discussed:** Run-start pane behavior, Attach surface, Transcript density + retention, Lifecycle affordance placement

---

## Run-start pane behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-open + show it | Pane spawns in Live Work grid immediately; Run Review flips to Live Work focused on new pane | ✓ |
| Auto-open, no mode flip | Background spawn; LIVE chip + attention row point at it | |
| No auto-pane | Headless start; user opens pane from card | |

**User's choice:** Auto-open + show it
**Notes:** Matches "grid is for steering agents" conviction — instant feedback the run is real.

| Option | Description | Selected |
|--------|-------------|----------|
| Same as quick-launch spawn | Reuse sidebar quick-launch path: new cell + balanceRatios equalize | ✓ |
| Split from focused pane | ⌘D-style split of focused | |
| Claude decides | Planner picks cleanest | |

**User's choice:** Same as quick-launch spawn

| Option | Description | Selected |
|--------|-------------|----------|
| One pane per run, no cap | Honest 1:1 mapping; grid proven at 9 panes | ✓ |
| Cap w/ reuse | Limit live structured panes; reuse oldest-idle | |

**User's choice:** One pane per run, no cap

---

## Attach surface

| Option | Description | Selected |
|--------|-------------|----------|
| Sidebar sessions section | Cockpit sidebar "Server sessions" list (GET /session): id/title/age + Attach | ✓ |
| Command palette only | "Attach to session…" picker; zero chrome, weak discoverability | |
| Both sidebar + palette | Both in V15; more surface to test | |

**User's choice:** Sidebar sessions section

| Option | Description | Selected |
|--------|-------------|----------|
| All listed, recent-first | Honest mirror of GET /session, newest first | ✓ |
| Recent N w/ 'show all' | Cap visible + expand | |
| Serve-created only | Filter CLI sessions — risky, protocol may not mark origin | |

**User's choice:** All listed, recent-first

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — register native card | Attach registers via native-card bridge; attached ≡ started | ✓ |
| No — pane only | Pane without board presence — splits the model | |

**User's choice:** Yes — register native card

---

## Transcript density + retention

| Option | Description | Selected |
|--------|-------------|----------|
| Mockup-faithful mixed | Mutating tools show inline excerpt; reads one-line (recommended) | |
| All collapsed one-liners | Every tool = one line, click to expand | ✓ |
| All expanded | Full args + result inline | |

**User's choice:** All collapsed one-liners
**Notes:** Deliberate deviation from the mockup's inline fs_edit excerpts — UI-SPEC must encode collapsed-by-default; expansion reveals excerpt content on demand.

| Option | Description | Selected |
|--------|-------------|----------|
| Capped, trim oldest | Last N events in DOM; header + pending permission pinned | ✓ |
| Unbounded | Full transcript — jank risk on multi-hour runs | |
| Capped + virtualized scroll | Windowed rendering — overkill for V15 | |

**User's choice:** Capped, trim oldest (Claude picks N ~ few hundred)

| Option | Description | Selected |
|--------|-------------|----------|
| Growing block + pulse → settle | delta appends w/ honest pulse; finalize settles; sticky-bottom | ✓ |
| Claude decides | Planner picks consistent w/ V14 pulse discipline | |

**User's choice:** Growing block + pulse → settle

---

## Lifecycle affordance placement

| Option | Description | Selected |
|--------|-------------|----------|
| In-pane boot placeholder | "starting Voss…" + elapsed in pane until handshake; statusbar secondary | ✓ |
| Statusbar only | Empty pane reads broken | |
| RunCommandBar inline | Bar may dismiss — state orphaned | |

**User's choice:** In-pane boot placeholder

| Option | Description | Selected |
|--------|-------------|----------|
| Banner row + dimmed chrome | Ended banner + dim + statusbar flip + disabled-with-reason; ExitBanner language | ✓ |
| Banner only, no dim | Weaker glanceability | |
| Claude decides | Match ExitBanner cleanest | |

**User's choice:** Banner row + dimmed chrome

| Option | Description | Selected |
|--------|-------------|----------|
| In-pane error + retry | Placeholder becomes error: message + stderr tail + Retry button | ✓ |
| Toast + pane closes | Easy to miss, loses stderr | |
| Modal | Heavyweight | |

**User's choice:** In-pane error + retry

---

## Claude's Discretion

- Exact transcript cap value (~few hundred events)
- Structured pane internal architecture (component split, renderer structure)
- EM-header data sourcing from the event stream
- Stub-provider test mechanics

## Deferred Ideas

- Queue↔pane focus linking — candidate gray area, not discussed; may fold into UI-SPEC if trivial
- Attach-while-turn-busy semantics (409 nuance) — researcher note, not a V15 requirement
- Session list management (delete/rename from sidebar) — own phase
