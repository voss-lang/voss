# Phase A6: voss-app Session Persist - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-20
**Phase:** A6-voss-app-session-persist
**Areas discussed:** Scrollback extraction, Save trigger & crash safety, Restore banner UX, Session vs layout priority

---

## Scrollback Extraction

### When to extract

| Option | Description | Selected |
|--------|-------------|----------|
| On quit only | Extract 2k lines per pane during Tauri close-requested handler. Simpler, no ongoing overhead. | ✓ |
| Periodic snapshot + quit | Background timer snapshots scrollback every N seconds into memory. Crash-resilient but adds ongoing CPU/memory cost. | |
| You decide | Claude/planner picks. | |

**User's choice:** On quit only
**Notes:** None

### Scrollback format

| Option | Description | Selected |
|--------|-------------|----------|
| Plain text only | Strip ANSI sequences, store raw text per line. Smaller file, simpler parsing. | ✓ |
| ANSI-preserved | Store raw terminal output with escape sequences. Retains colors. Larger file. | |
| You decide | Claude/planner picks. | |

**User's choice:** Plain text only
**Notes:** None

### Alternate-screen handling

| Option | Description | Selected |
|--------|-------------|----------|
| Save normal buffer only | Always read from buffer.normal. If alt-screen was active, saved scrollback = pre-vim history. | ✓ |
| Save whichever is active | Read from buffer.active. If vim was open, save the vim screen. | |
| You decide | Claude/planner picks. | |

**User's choice:** Save normal buffer only
**Notes:** None

---

## Save Trigger & Crash Safety

### Periodic auto-save

| Option | Description | Selected |
|--------|-------------|----------|
| Quit-only scrollback, periodic tree | Tree auto-saved on structural changes (~2s debounce). Scrollback on quit only. Crash preserves layout. | ✓ |
| Quit-only everything | Single save on close-requested. Crash = full session loss. | |
| Full periodic auto-save | Tree + scrollback every ~30s. Crash-resilient for everything. Higher CPU cost. | |
| You decide | Claude/planner picks. | |

**User's choice:** Quit-only for scrollback, periodic for tree
**Notes:** None

### Close handler behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Block close, save, then quit | Tauri close-requested is cancellable. Extract scrollback, write session.json, then allow close. | ✓ |
| Fire-and-forget save | Start save async, allow close immediately. Risk: save may not finish. | |
| You decide | Claude/planner picks. | |

**User's choice:** Block close, save, then quit
**Notes:** None

### Auto-save trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Structural changes only | Save after split/close/fork/preset-switch/focus-change, debounced ~2s. Reuses markStructuralChange. | ✓ |
| Fixed interval timer | setInterval every 30s regardless. Simpler but writes unchanged data. | |
| You decide | Claude/planner picks. | |

**User's choice:** Structural changes only
**Notes:** None

---

## Restore Banner UX

### Component pattern

| Option | Description | Selected |
|--------|-------------|----------|
| New RestoreBanner | Separate component, same mount point as ExitBanner/CloseConfirmBanner. Different purpose = different component. | ✓ |
| Reuse ExitBanner with mode | Add 'restored' mode to existing ExitBanner. Shares logic but mixes concerns. | |
| You decide | Claude/planner picks. | |

**User's choice:** New RestoreBanner, sibling to ExitBanner
**Notes:** None

### Dismiss behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-dismiss on first keystroke | Banner disappears when user types. Zero friction. | ✓ |
| Explicit dismiss button | Stays until user clicks Dismiss or presses Escape. | |
| Timed auto-dismiss | Fades after 5 seconds. User may miss it. | |
| You decide | Claude/planner picks. | |

**User's choice:** Auto-dismiss on first keystroke
**Notes:** None

### Banner copy

| Option | Description | Selected |
|--------|-------------|----------|
| "Session restored — N lines" | Short, factual. Shows actual line count. 22px height, Variant B dim fg. | ✓ |
| "[restored] — scrollback from previous session" | Matches PER-02 wording literally. Slightly longer. | |
| You decide | Claude/planner picks. | |

**User's choice:** "Session restored — N lines"
**Notes:** None

---

## Session vs Layout Priority

### Restore chain

| Option | Description | Selected |
|--------|-------------|----------|
| Session wins, layout is fallback | session.json = last state. default.json only when no session. Matches "reopen = back where I was". | ✓ |
| Layout wins, session layers scrollback | default.json determines geometry. session.json only restores scrollback into slots. | |
| You decide | Claude/planner picks. | |

**User's choice:** Session wins, layout is fallback
**Notes:** None

### projectLessAccepted persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — skip setup window | global-session.json records project-less mode. Relaunch restores directly. Setup window only on first launch. | ✓ |
| No — always show setup window | Project-less is transient. Setup window every launch without a project. | |
| You decide | Claude/planner picks. | |

**User's choice:** Yes — skip setup window on relaunch
**Notes:** Resolves A5 D-04's explicit deferral to A6.

### Corrupt session handling

| Option | Description | Selected |
|--------|-------------|----------|
| Fall through to default.json, then fresh | Corrupt → log + try default.json → fresh pane. Matches A4 D-09 fail-safe. | ✓ |
| Show toast + fresh pane | Skip default.json. Toast notification. Always fresh pane. | |
| You decide | Claude/planner picks. | |

**User's choice:** Fall through to default.json, then fresh
**Notes:** None

---

## Claude's Discretion

- Exact `session.json` schema shape (field names, nesting) — bounded by `GridState` wrapper + scrollback arrays + version field
- xterm.js buffer extraction implementation (loop `getLine()` vs serialize addon)
- Auto-save debounce exact timing (~2s target)
- RestoreBanner visual layout within 22px constraint
- Whether structural-change auto-save fires on focus-change
- Forward-migration strategy for session.json version bumps

## Deferred Ideas

None — discussion stayed within A6 scope.
