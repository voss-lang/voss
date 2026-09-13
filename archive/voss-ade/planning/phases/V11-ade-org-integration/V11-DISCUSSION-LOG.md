# Phase V11: ADE Org Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-07
**Phase:** V11-ade-org-integration
**Areas discussed:** Data-layer shape + TS types, Run selection / discovery, Replay reconstruction, Decision-action wiring

> Note: V11-SPEC.md locked 8 requirements (ambiguity 0.141). Discussion covered HOW-level implementation only. Visual design contract deferred to `/gsd-ui-phase` (V11-UI-SPEC, not yet run).

---

## Data-layer shape + TS types

### Tauri command granularity
| Option | Description | Selected |
|--------|-------------|----------|
| One aggregate `load_run(run_id)` | Single command shells all sources, returns one typed `RunData`; one refresh, one error boundary | ✓ |
| One command per source | Per-panel pulls own data; per-panel error states; more wiring | |
| Aggregate + per-source refresh | Aggregate snapshot + individual refresh; best UX, most code | |

**User's choice:** One aggregate `load_run(run_id)`

### TS typing of CLI JSON
| Option | Description | Selected |
|--------|-------------|----------|
| Hand-authored TS in app, runtime-validated | TS interfaces + boundary validation; drift surfaces as error; flagged for V13.1 codegen | ✓ |
| Hand-authored TS, no runtime validation | Plain interfaces, trust shape; drift fails silently | |
| Rust-side typed structs, TS mirrors | serde structs parse JSON, TS mirrors; stronger boundary, more upfront | |

**User's choice:** Hand-authored TS in app, runtime-validated
**Notes:** Explicitly a V11 stopgap — to be superseded by the V13.1 codegen contract snapshot.

---

## Run selection / discovery

### Discovery mechanism
| Option | Description | Selected |
|--------|-------------|----------|
| Tauri-side enumerate `.voss/sessions` | Rust command lists run ids + metadata; out of frontend; no new CLI contract | ✓ |
| New `voss runs --json` list command | CLI list command shelled; brushes "no new harness behavior" boundary | |
| Manual run_id entry only | User types id; minimal, poor UX | |

**User's choice:** Tauri-side enumerate `.voss/sessions`

### Default run on open
| Option | Description | Selected |
|--------|-------------|----------|
| Most-recent run auto-loaded | Open into latest run; picker to switch | ✓ |
| Empty state until picked | Picker first, nothing loads until chosen | |

**User's choice:** Most-recent run auto-loaded

---

## Replay reconstruction

### Where state-at-step is computed
| Option | Description | Selected |
|--------|-------------|----------|
| Fold `transitions[]` client-side | App folds history in-memory; instant scrub; reducer vitest-testable | ✓ |
| Per-step CLI/Tauri query | Re-query per step; latency + likely new CLI surface | |

**User's choice:** Fold `transitions[]` client-side

### Reducer scope
| Option | Description | Selected |
|--------|-------------|----------|
| Board/card state only | Matches SPEC acceptance; other panels = final snapshot; tight scope | ✓ |
| All panels time-travel | Every panel reflects step N; larger reducer, beyond acceptance line | |

**User's choice:** Board/card state only

---

## Decision-action wiring

### Confirmation before shelling CLI
| Option | Description | Selected |
|--------|-------------|----------|
| Confirm dialog with command preview | Shows exact CLI command + target card before running; matches V12 direction | ✓ |
| Immediate, no confirm | Acts immediately; risky for irreversible write path | |

**User's choice:** Confirm dialog with command preview

### Handling the CLI result
| Option | Description | Selected |
|--------|-------------|----------|
| Capture stdout/exit, show result, auto-refresh | Closed loop; failures visible; panels reload | ✓ |
| Fire-and-forget + manual refresh | Simplest; failures invisible, state stale | |

**User's choice:** Capture stdout/exit, show result, auto-refresh

---

## Claude's Discretion
- **Test-fixture strategy:** golden JSON fixtures from a real persisted run, vitest-driven; Tauri E2E skip-deferred on macOS; gate on vitest + `tsc --noEmit` + `cargo`.
- **Error/empty granularity:** view-level empty/error is primary boundary (aggregate load); per-panel "no data" where a source is individually absent.
- **Panel build sequencing within the phase:** left to the planner's wave ordering.

## Deferred Ideas
- Live streaming during an active run (SPEC follow-on).
- All-panels time-travel during replay.
- Codegen-typed CLI contract (V13.1).
- V11-UI-SPEC visual design contract (`/gsd-ui-phase V11`).
