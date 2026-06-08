# Phase V14: ADE Run Cockpit (Integrated Redesign + Live Data Unification) - Context

**Gathered:** 2026-06-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Recompose V11's built 10-panel org view (`apps/voss-app/src/org/`) into one integrated run cockpit, and merge the live PTY/SSE agent registry with the static CLI-JSON `RunData` snapshot into a single normalized UI model with card↔session/pane binding. Adds a RunCommandBar intake surface and a global AttentionQueue. Reuses existing panel bodies — not a panel rewrite. New harness contracts, freeform canvas, embedded browser, and replay rollback are explicitly out.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**10 requirements are locked** (7 must-ship core · 3 best-effort gated). See `V14-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `V14-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- Normalized UI data model (Run/Card/Agent/SessionNode/Evidence/Decision) + snapshot/registry adapters + single selection store (VCKP-01).
- Card↔session/pane id-bridge + click-to-focus/reveal (VCKP-02).
- RunCommandBar intake that starts terminal-agent AND Voss-native runs (VCKP-03).
- Global AttentionQueue from snapshot decisions + live events (VCKP-04).
- Integrated cockpit layout recomposing the existing 10 panel components (VCKP-05).
- Live SSE wiring via V13.1 with snapshot fallback + live/snapshot label (VCKP-06, best-effort).
- A13 swarm-manifest reconciliation into roster/board (VCKP-07, best-effort).
- Live Work ↔ Run Review mode toggle preserving the grid (VCKP-08).
- Feedback write-path where the harness exposes one, disabled-with-reason otherwise (VCKP-09, best-effort).
- Dense/keyboard/a11y pass on A12 tokens (VCKP-10).
- Refreshed sparse quick-launch modal for ad-hoc terminal agents (VCKP-11).
- "Manage with Voss" adopt flow — forward-only tracking/audit/review for a running agent (VCKP-12).

**Out of scope (from SPEC.md):**
- Rewriting panel internals (reuse, not rewrite).
- New harness contracts / new SSE event types / new emit points (V14 is a PROTOCOL v1 client).
- Freeform/Studio infinite canvas.
- Embedded browser / VerificationArtifact panel.
- Rollback / re-run from replay (replay stays inspect-only).
- Custom/user-defined board columns.
- Real `voss serve` end-to-end live verification (fixture/mock-verified here; real-server rides V13.1).

</spec_lock>

<decisions>
## Implementation Decisions

### Cockpit layout & old-tab fate
- **D-01:** Cockpit-only. The existing `OrgViewShell` `ORG_TABS`/`activeTab` tab switcher (`org/OrgViewShell.tsx:45,68`) is **removed**. The cockpit (Board spine + Card detail drawer + Timeline/replay rail + bottom gate bar) is the single Run Review surface.
- **D-02:** The 10 existing panel components (`org/panels/*.tsx`) are reused as drawer/rail sections, NOT as tabs. Replay and Audit become drawer/rail sections, not standalone tabs. No legacy tab "escape hatch" is kept — avoid maintaining two layouts.

### RunCommandBar placement & visibility
- **D-03:** RunCommandBar is an **always-on top strip** above the work surface, present in BOTH Live Work and Run Review modes (Warp universal-input style). Not ⌘K-invoked — intake must be visible (aligns with SPEC "no hidden mode" rule).
- **D-04:** The existing `AgentSidebar` Quick-Launch flow **coexists** as the fast per-CLI spawn path; RunCommandBar is the richer run-intake path (mode/team/scope/budget/native-vs-terminal). Do not remove Quick-Launch.

### AttentionQueue surfacing
- **D-05:** Surface = **StatusBar count pill + dockable queue panel**. The pill reuses the existing StatusBar agent-pill pattern (`App.tsx` StatusBar, agent-count pill); clicking it opens the dockable AttentionQueue panel. Non-modal by default.
- **D-06:** Blocking items (permission request, sign-off available) **pulse the pill** to escalate attention; they do not hard-modal the cockpit. (Per-pane permission prompts in the live grid are unchanged — this queue is the global aggregator, not a replacement for the existing modal in the grid.)

### Cross-surface selection behavior
- **D-07:** Clicking a board card bound to a LIVE pane **stays in the cockpit**: the detail drawer shows an embedded **read-only live-pane peek** (tail of pane output) plus an explicit **"Open in grid"** button that flips `orgViewOpen` (`App.tsx:240`) and focuses the full PTY pane. Jump-to-grid is opt-in, never automatic.
- **D-08:** The detail drawer is **persistent** with a defined **no-selection empty state** (prompt to select a card). Selection is the single global `selectedCard` store driving Board highlight + drawer + timeline + gate bar together.

### Agent spawn & adopt UX (mockup-validated)
- **D-09 (VCKP-11) Quick-launch modal — sparse/premium.** CLI preset cards each show the user's **default model** (Claude Code · sonnet-4-6, Codex · gpt-5.1, …); one optional "what should it work on?" prompt; working dir + pane placement (Right/Below/New tab). **Removed: raw-command field + the "terminal agent" explainer block.** Preset resolves the user's configured CLI command/model. Mockup signed off by operator 2026-06-08.
- **D-10 (VCKP-12) "Manage with Voss" adopt flow — plain language.** Title "Let Voss manage this agent"; sections "Add it to / As the task / Limits / From now on, Voss will". CTA "Hand to Voss". Outcomes not mechanics — **no** `cage`/`Voss-native`/`PermissionGate`/`session-tree`/`partial lineage`/`pane` in UI copy. Operator approved the friendlier rewrite 2026-06-08.
- **D-11 Adoption is forward-only + best-effort for external agents.** Locked: keep the running work (don't discard/re-run-clean); audit node marked `partial_lineage`; pre-adoption activity excluded. **Engineering limit locked:** an external CLI agent is PTY-only — Voss cannot intercept its internal tool loop, so adoption gives cost-tracking + transcript-audit + budget-monitor + review-before-done + **advisory** scope, **NOT** per-tool PermissionGate enforcement (that stays Voss-native only). Adopt copy must not overstate control.
- **D-12 Role/Risk on adopt** pre-inferred (risk from scope/budget, role from CLI) but **editable** — visible by default per mockup.

### Claude's Discretion
- id-bridge correlation mechanism (how a card id maps to a live `paneId`/`sessionNodeId`) — technical; researcher investigates whether the harness emits a stable correlation id, else the run-launch correlation-id-stamp fallback from SPEC §Constraints applies. **This is the keystone risk — resolve before the binding wave.**
- Adapter shapes (`snapshot→model`, `registry→model overlay`) and selection-store implementation (Solid signals vs store) — planner's call, consistent with existing `org/orgStore.ts` signal style.
- Exact cockpit CSS/region sizing + collapse behavior — within A12 Ignite tokens.
- Roster IA (how Voss-native team + A13 swarm + external terminal agents group in the roster) — left to planner within VCKP-01/07; default to sectioned single roster.
- Gate bar exact field set + card-vs-run reactivity — planner's call within VCKP-05.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase spec (locked — read first)
- `.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-SPEC.md` — Locked requirements VCKP-01..10, boundaries, acceptance criteria. MUST read before planning.
- `.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-DESIGN-BRIEF.md` — Gap→requirement map, unified data-model sketch, cockpit layout contract, wave plan, risks (id-bridge keystone, per-card field availability).

### Research source
- `.planning/research/ade-ui-design-contract-research.md` — Market design-contract analysis the phase closes (six UI primitives, two-mode ADE, attention queue, board-as-state-machine).

### Visual design — operator-reviewed 2026-06-08 (throwaway mockups, removed)
Three HTML mockups were reviewed and approved, then deleted (throwaway). Their decisions are captured in `<decisions>` above and in SPEC VCKP-03/05/11/12:
- Run Review cockpit — Board spine + detail drawer + timeline rail + gate bar + StatusBar AttentionQueue pill.
- Live Work — 3 live agent terminals (Warp-tiled), per-pane role chrome, inline permission gate, RunCommandBar, board summary strip.
- Quick-launch modal (VCKP-11) + "Manage with Voss" adopt modal (VCKP-12).
Re-mockup via `/gsd-ui-phase V14` if a refreshed visual contract is wanted before build.

### V11 (built — the surface being recomposed)
- `.planning/phases/V11-ade-org-integration/V11-SPEC.md` — Original 10-panel org contract (VADE-01..10), CLI-JSON consumer, one-write-path, D-02 snapshot guard.
- `.planning/phases/V11-ade-org-integration/V11-UI-SPEC.md` — Org-panel UI contract + A12 token reuse.
- `apps/voss-app/src/org/types.ts` — `RunData`/`CardSnapshot`/`SessionTreeNode`/`AuditReport`/`ReviewSidecar`/`BoardFrame`; the model VCKP-01 extends. Note: no `Agent` type; per-card confidence absent (live SSE event only).
- `apps/voss-app/src/org/OrgViewShell.tsx` — `ORG_TABS`/`activeTab` switcher being removed (D-01).
- `apps/voss-app/src/org/orgStore.ts` — `runData` signal + `load_run`/`enumerate_runs` Tauri invokes; snapshot-only data path.
- `apps/voss-app/src/org/boardDerive.ts` — 6-column board card derivation (reused by Board spine).
- `apps/voss-app/src/org/guards.ts` — D-02 snapshot contract boundary (must not regress).
- `apps/voss-app/src/org/decisionActions.ts` — existing one-write-path (`voss audit --approve`); VCKP-09 extends best-effort.

### Protocol + live plane
- `.planning/PROTOCOL.md` §6/§7 — locked v1 SSE event union (`permission.updated`/`budget.updated`/`confidence.updated`/`gate.updated`/`session.idle`/`probable`) + permission dimension; source for AttentionQueue (VCKP-04) and live wiring (VCKP-06). V14 is a client — no new events.
- `apps/voss-app/src/components/sidebar/AgentSidebar.tsx` — live agent list + Quick-Launch (coexists per D-04).
- `apps/voss-app/src-tauri/` — agent registry / PTY pane commands (live plane; id-bridge source).

### Dependencies (gated)
- `.planning/phases/V13.1-typescript-local-client-sdk/V13.1-SPEC.md` — TS local client + contract snapshot; gates VCKP-06 live wiring + Voss-native run-start in VCKP-03.
- `.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-SPEC.md` — `.voss/swarm/{manifest,tasks,results}` file protocol; gates VCKP-07.

### Theme
- `.planning/phases/A12-voss-app-ade-visual-redesign/A12-UI-SPEC.md` — Ignite tokens (the only theme allowed; VCKP-10).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `org/panels/*.tsx` (Roster/Board/Tree/Audit/Verdict/Budget/Scope/Diff/Blocked/Replay): reused as cockpit drawer/rail sections (D-02), not rewritten.
- `org/orgStore.ts` signals (`runData`/`runEntries`/`currentRunId`): snapshot data source; VCKP-01 adapters overlay the live registry onto this.
- `org/boardDerive.ts`: 6-column derivation → Board spine.
- `org/guards.ts`: D-02 contract — keep green.
- `components/sidebar/AgentSidebar.tsx`: live agent rows + Quick-Launch (coexist, D-04).
- `App.tsx` `orgViewOpen` signal (line 240): the grid↔org toggle "Open in grid" reuses (D-07); StatusBar agent-pill pattern reused for AttentionQueue pill (D-05).

### Established Patterns
- Solid signals for store state (`createSignal` in orgStore) — selection store should match.
- Grid↔org view via `display:none` swap (`App.tsx:1183,1263`) — Live↔Review (VCKP-08) extends this without PTY regression.
- Tauri `invoke()` for data (no SSE today) — live wiring (VCKP-06) introduces the first SSE consumer, gated on V13.1.

### Integration Points
- Selection store ← Board spine, detail drawer, timeline rail, gate bar (one `selectedCard` drives all).
- id-bridge ← snapshot `RunData` (card/session ids) ⨯ live registry (`paneId`) — keystone correlation point.
- AttentionQueue ← snapshot decisions (Blocked/sign-off) + live SSE events (permission/gate/budget) — spans both planes.
- RunCommandBar → existing PTY/CLI launch (terminal) + V13.1 protocol session-create (native).

</code_context>

<specifics>
## Specific Ideas

- "Warp universal-input" feel for the RunCommandBar (always-on top strip, mode/context chips).
- "Lemonade attention-detection" without modal spam — pill pulses, dockable panel, no hard interrupt for non-blocking events.
- Read-only "pane peek" in the drawer with an opt-in "Open in grid" — keep cockpit context, jump only on intent.

</specifics>

<deferred>
## Deferred Ideas

- Freeform/Studio investigation canvas — explicitly out (future phase if ever).
- Embedded browser / VerificationArtifact panel — needs webview infra; future phase.
- Replay rollback / re-run — out; replay stays inspect-only.
- Reject/Unblock full write actions — blocked on harness write path; VCKP-09 only goes best-effort.
- Custom board columns — columns stay the orchestrator state machine.

</deferred>

---

*Phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification*
*Context gathered: 2026-06-08*
