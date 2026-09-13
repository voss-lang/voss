# Phase V11: ADE Org Integration - Context

**Gathered:** 2026-06-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Turn the desktop app (`apps/voss-app/`) into a visual Agentic Development Environment for the org loop: a dedicated **Org/Run view** hosting the ten org panels (roster, board, session-tree, audit, reviewer-verdict, budget, scope, diff drilldown, blocked-card decision, replay), each rendering from the V4–V9 CLI JSON via **thin Tauri command wrappers**. Read/replay first; decision actions shell the V7/V9 CLI so there is **one write path**. Static snapshot + manual refresh; live streaming deferred.

The **visual design contract is NOT in this phase** — it is produced by `/gsd-ui-phase` (V11-UI-SPEC), which had not been run when this context was gathered. This discussion captured **non-visual implementation decisions only**.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**8 requirements are locked.** See `V11-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `V11-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- Tauri CLI-JSON data layer.
- Org/Run view mode (static snapshot + manual refresh).
- All 10 panels (roster/board/session-tree/audit/reviewer/budget/scope/diff/blocked-decision/replay).
- Decision actions that shell the V7/V9 CLI.

**Out of scope (from SPEC.md):**
- Live streaming during an active run — static + manual refresh only (follow-on).
- The ADE writing run decisions directly — the CLI is the single write path.
- Any new harness data/persistence or change to the V4–V9 CLI JSON contracts — V11 is a consumer.
- The **visual design contract** — produced by `/gsd-ui-phase` (V11-UI-SPEC) after this SPEC.
- New harness behavior / org-loop logic.

</spec_lock>

<decisions>
## Implementation Decisions

### Data layer + TS types
- **D-01:** Tauri exposes **one aggregate command `load_run(run_id)`** that shells all sources (`voss board` / `voss review` / `voss audit --json` / session-tree export / `run-final.json`) and returns a single typed `RunData` object. One refresh call, one error boundary. (Chosen over per-source commands and aggregate+per-source refresh — accepted that a slow/failing source affects the whole load; acceptable for a static-snapshot model.)
- **D-02:** The frontend types the CLI JSON with **hand-authored TS interfaces in `apps/voss-app/src`, runtime-validated at the Tauri boundary** (guards/zod-style) so contract drift surfaces as an explicit error rather than a silent render miss. These types are a **V11 stopgap — explicitly flagged for replacement by the V13.1 codegen contract snapshot** when that phase lands. Add a comment/marker so V13.1 can find and supersede them.

### Run discovery + default
- **D-03:** Run discovery is a **Rust/Tauri-side command that enumerates `.voss/sessions/`** (run ids + light metadata: mtime, status). This stays out of the frontend (SPEC bars *frontend* raw-parsing, not the Rust wrapper) and adds **no new harness CLI contract**. Discovery only — panel data still flows through `load_run`. (Chosen over a new `voss runs --json` CLI command, which would brush the "no new harness behavior" boundary, and over manual run_id entry.)
- **D-04:** Opening the Org/Run view **auto-loads the most-recent run**; a picker lets the user switch runs.

### Replay
- **D-05:** Replay folds `transitions[]` + `run-final.json` **client-side** — `load_run` returns the full transition history once and the app folds it in-memory (a reducer) to derive state at step N. Instant forward/back scrubbing, no per-step re-shell. The reducer lives in the app and is **vitest-testable**. (Chosen over per-step CLI/Tauri queries.)
- **D-06:** The replay reducer reconstructs **board/card state only** (columns + card status/role/risk/budget) per step — matching the SPEC acceptance line ("reflects board/card state at each step"). Other panels (audit, reviewers, budget, scope) show the **final snapshot**, not time-travelled. Keeps the reducer tight and avoids scope creep.

### Decision actions (the one write path)
- **D-07:** Every decision action (approve / reject / unblock / sign-off) shows a **confirmation dialog with the exact CLI command + target card** before shelling the V7/V9 CLI. Mirrors V12's "human confirmation includes the exact command" direction; appropriate for an irreversible write path.
- **D-08:** After a decision action, the Tauri wrapper **captures stdout / stderr / exit code**; the app shows success/failure **inline** and **auto-refreshes `load_run`** so panels reflect the new state. Closed loop — failures are visible, no stale state. (Chosen over fire-and-forget + manual refresh.)

### Claude's Discretion
- **Test-fixture strategy:** Use **golden JSON fixtures captured from a real persisted run**, driving panel/reducer tests in **vitest**. Tauri WebDriver E2E stays **skip-deferred on macOS** (platform-blocked — see prior A-track decision); gate on vitest + `tsc --noEmit` + `cargo` instead.
- **Error/empty granularity:** With the aggregate `load_run` (D-01), the **view-level** empty/error state is the primary boundary (invalid/missing run → empty/error, no crash, per SPEC acceptance). Per-panel "no data for this section" states are fine where a source is individually absent within an otherwise-valid run.
- **Panel build sequencing within the phase:** left to the planner (wave ordering). Suggested natural order: data layer + view shell → structural panels (roster/board/session-tree/reviewer) → audit → budget/scope → diff drilldown → blocked-decision → replay.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase contract (read first)
- `.planning/phases/V11-ade-org-integration/V11-SPEC.md` — **Locked requirements (VADE-01..10), boundaries, acceptance criteria. MUST read before planning.**
- `.planning/ROADMAP.md` §"Phase V11: ADE Org Integration" (~line 2013) — goal/scope/cross-cutting.

### Product / org-layer model
- `.planning/docs/ORCHESTRATION_LAYERS.md` — canonical PRD; ADE-01..10 (namespaced VADE-01..10), org-loop model.

### Upstream JSON producers V11 consumes (read for the JSON shapes)
- `.planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-CONTEXT.md` — session-tree + budget fan-out (keystone); transitions / session-tree export.
- `.planning/phases/V5-board-state-machine-supersedes-o3/V5-CONTEXT.md` — `voss board` JSON (6 columns + cards).
- `.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-CONTEXT.md` — `voss review` JSON (Reviewer-A / Reviewer-B).
- `.planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-CONTEXT.md` — EM loop; `run-final.json`; decision CLI surface (V7 write path).
- `.planning/phases/V8-multi-agent-chat-live-steering-absorbs-m13/V8-CONTEXT.md` — persisted session-tree nodes (ADE child-panel surface deferred here to V11).
- V9 audit (Phase V9, `voss audit --json`) — audit §9 sections, claims-vs-evidence, residual-risk; decision/sign-off CLI surface (V9 write path). See V9 SPEC/CONTEXT in `.planning/phases/V9-*/`.

### Forward dependency (do NOT block on; flag for handoff)
- V13.1 TypeScript Local Client SDK — owns the future codegen contract snapshot that will **replace** the V11 hand-authored TS types (D-02). Leave a marker.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (A-track shell, `apps/voss-app/src/`)
- **Sidebar** (`components/sidebar/`), **command palette** (`command-palette/`), **theme/variant-b** (`theme/`, `themes/`), **ContextPanel / StatusBar** patterns, **workspaces** (`workspaces/`), **grid engine** (`grid/`), **swarm view** (`swarm/`, A13) — reuse tokens/components for the Org/Run view chrome (final visual contract from V11-UI-SPEC).
- **A12 UI-SPEC** sets the ADE visual direction; **A13 swarm view** is the closest precedent for a non-grid panel view that toggles from the terminal grid.

### Established Patterns
- **Solid + `produce`/proxy caveat:** pure tree/reducer utils called from the render layer must hand-clone — `produce` drafts are Proxies → `DATA_CLONE_ERR` (see memory `voss-app-solid-produce-no-structuredclone`). The replay reducer (D-05) must respect this.
- **Tauri command wrapper pattern:** `src-tauri` + `crates/voss-app-core` are the live voss-app-track members; `load_run` and the sessions-enumerate command belong here.
- **Vite target:** non-Windows = `safari15` (not safari13) — Solid destructuring transform.

### Integration Points
- New **Org/Run view mode** toggles from the existing terminal-grid view (and swarm view) without disturbing the grid (SPEC acceptance: toggle back restores grid unchanged).
- `load_run` / sessions-enumerate Tauri commands connect the Solid frontend to the `voss` CLI (subprocess) — the only data path; no `.voss/sessions` parsing in the frontend.

</code_context>

<specifics>
## Specific Ideas

- Decision-action confirmation should display the **literal CLI command string** that will be shelled (e.g. `voss <decision> <run_id> <card_id> ...`), so the user sees exactly what the one-write-path will run.
- Replay UX = forward/back step scrubbing over the persisted transitions of the loaded run.

</specifics>

<deferred>
## Deferred Ideas

- **Live streaming during an active run** — explicitly out of scope (SPEC follow-on); static snapshot + manual refresh only for V11.
- **All-panels time-travel during replay** — considered; deferred to keep the reducer tight (D-06 is board/card only).
- **Codegen-typed CLI contract** — replaces V11's hand-authored TS types; owned by V13.1, not this phase.
- **V11-UI-SPEC (visual design contract)** — run `/gsd-ui-phase V11` to produce it; this discussion deliberately did not lock visual styling/layout chrome.

None of the above are scope creep into V11 — each is its own phase or a noted follow-on.

</deferred>

---

*Phase: V11-ade-org-integration*
*Context gathered: 2026-06-07*
