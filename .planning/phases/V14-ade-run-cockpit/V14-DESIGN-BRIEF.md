# V14 — ADE Run Cockpit (Integrated Redesign + Live Data Unification)

> Spec-ready design brief. Feeds `/gsd-spec-phase V14`. Source: `.planning/research/ade-ui-design-contract-research.md` gap analysis (2026-06-08).
> Status: DRAFT brief — not yet SPEC-locked.
> Track: V (Agent Engineering Organization Layer). Builds on V11 (built), A12 (built), A13 (swarm), V13.1 (TS client, in progress).

---

## 1. Why this phase exists

V11 shipped the ADE Org/Run view: 10 panels (Roster, Board, Tree, Audit, Verdict, Budget, Scope, Diff, Blocked, Replay) in a **tabbed** shell (`apps/voss-app/src/org/OrgViewShell.tsx`), fed by **static CLI-JSON snapshots** loaded through Tauri `invoke('load_run')` with manual refresh (`apps/voss-app/src/org/orgStore.ts`).

The deep-research design-contract analysis surfaced four structural gaps that V11's panel-by-panel delivery does not close. These are **design-contract gaps**, not bugs — V11's facts are all correct, but the product shape stops at "10 inspectable panels" instead of "one integrated run cockpit."

### Gap → V14 requirement map

| # | Gap (from research) | Evidence in code | V14 requirement |
|---|---|---|---|
| G1 | **Two disjoint data planes never reconciled.** Live PTY/SSE agent registry (grid + AgentSidebar) and static CLI-JSON `RunData` (org view) describe the same logical entities (agent, card, budget) with no shared types or ids. | live: agent registry in `src-tauri/src/lib.rs` + `AgentSidebar.tsx`; snapshot: `RunData` in `org/types.ts:202`, no `Agent` type, `CardSnapshot` minimal (`types.ts:212`) | VCKP-01, VCKP-02 |
| G2 | **No universal run-intake surface.** Research's #1 pattern (GoalBar/RunCommandBar) has no home; A13 launches swarm from sidebar with bare NL goal — no mode/team/scope/budget/risk chips, no Voss-native vs terminal-agent indicator. | no `GoalBar`/`RunCommandBar` anywhere in `src/` | VCKP-03 |
| G3 | **No global attention/permission queue.** `permission.updated`/`gate.updated`/`budget.updated`/`session.idle` exist in PROTOCOL but surface only per-pane (live) or not at all (org). Stalls stay hidden. | PROTOCOL §6/§7; no `AttentionQueue` component | VCKP-04 |
| G4 | **Tabs, not a cockpit.** Selecting work in one panel does not drive the others. Research calls for Board spine + Card detail drawer + Timeline rail + Gate bar with one shared selection. | `OrgViewShell.tsx:32-56` horizontal tab bar, single active panel | VCKP-05 |
| G5 | **Org view is snapshot-only.** No live updates for in-flight runs; the cockpit cannot show a run as it happens. | `orgStore.ts:34` `invoke('load_run')`, manual `refreshRun` | VCKP-06 |
| G6 | **A13 swarm disconnected from the board model.** Swarm `.voss/swarm/manifest.json` agents are not roster rows or board cards; swarm status not mapped to columns. | A13-SPEC `.voss/swarm/`; org board derives from `RunData` only (`boardDerive.ts`) | VCKP-07 |
| G7 | **No feedback write-path.** V11 has one write path (`voss audit --approve`); Reject/Unblock disabled. Research's "comment routes back to agent" loop cannot close. | V11 VADE-09; `decisionActions.ts` | VCKP-09 (best-effort, harness-gated) |

---

## 2. Scope (decisions locked 2026-06-08)

- **V11 is built.** V14 **recomposes the existing panel components** (`org/panels/*.tsx`) into the cockpit — reuse panel bodies, replace the tab shell, add the new surfaces. Not a rewrite of panel internals.
- **Unify model; live wiring gated on V13.1.** V14 builds the normalized UI model + card↔session binding unconditionally. Live SSE is wired **where the V13.1 TS client exists**; static-snapshot remains the fallback. V14 does not block on V13.1 shipping.

## 3. Requirements (VCKP-*) — to be SPEC-locked

| ID | Requirement | Must/Should |
|---|---|---|
| **VCKP-01** | **Normalized UI data model.** Single TS model `{ Run, Card, Agent, SessionNode, Evidence, Decision }` (extends `org/types.ts`) that merges the live agent registry and the snapshot `RunData` into one view layer. One selection store (`selectedCard`/`selectedRun`) drives every surface. | Must |
| **VCKP-02** | **Card ↔ session/pane binding.** A board card resolves to (a) its live PTY pane if running, (b) its session-tree node if recorded, via a shared id map. Click card → focus pane (live) or open detail (review). | Must |
| **VCKP-03** | **RunCommandBar.** Primary intake strip: goal/command input · mode segmented control (Plan/Edit/Auto) · team selector (`.voss team{}`) · scope chip · budget chip · context attach · explicit **Voss-native vs terminal-agent** execution indicator. Starts run via protocol (Voss-native) or CLI/PTY (terminal agent). No hidden mode in placeholder; Auto never starts without visible budget/scope. | Must |
| **VCKP-04** | **AttentionQueue.** Global queue sourced from `permission.updated`, `gate.updated`, `budget.updated` (threshold), `confidence.updated` (below gate), `session.idle`, verification-failed, sign-off-available. Each item links to its card/session/evidence. Permission items show tool+args+dimension+affected path + allow-once/allow-scoped/deny. | Must |
| **VCKP-05** | **Integrated cockpit layout.** Run Review surface = Board spine (6 columns, compact cards) + Card detail drawer (selected card source-of-truth) + Timeline/replay rail (session-tree transitions) + bottom gate bar (budget/confidence/scope/unsupported-claims). Tabs demoted to secondary nav. One selected card/run drives all four regions. | Must |
| **VCKP-06** | **Live wiring (V13.1-gated).** When a Voss-native run is in-flight and the V13.1 client/server is available, the cockpit consumes the SSE event union for live board/budget/confidence/gate updates. Falls back to snapshot + manual refresh when no live server. UI distinguishes `live` vs `snapshot` state. | Must (fallback) / Should (live) |
| **VCKP-07** | **Swarm reconciliation.** A13 `.voss/swarm/manifest.json` agents render as roster rows and board cards; swarm per-agent status (pending/running/complete) maps to board columns; swarm goal shows as the run idea. | Should |
| **VCKP-08** | **Live Work ↔ Run Review mode toggle** over the same run, preserving the terminal grid (extends existing `⌘⇧O` toggle). Starting in Live Work yields the same session-tree/audit evidence as a delegated run. | Should |
| **VCKP-09** | **Feedback write-path (best-effort, harness-gated).** Inline card/diff comment → follow-up to the bound session **where the protocol exposes a write path**; rendered disabled-with-reason where it does not. No fake affordances. | Could |
| **VCKP-10** | **Dense operational pass + a11y.** Keyboard nav across board/detail/timeline, reduced-motion, contrast on state colors, monospace numerics for budget/cost/confidence. Reuses A12 Ignite tokens; no new theme. | Should |

## 4. Unified data model (VCKP-01 sketch)

```
Run        { id, idea, cwd, team, status, source:'live'|'snapshot', created, ended, signoff }
Card       { id, title, column, role, risk, scope, budget{spent,limit}, confidence?,
             verification?, reviewerA?, reviewerB?, retries, blockReason?,
             paneId?, sessionNodeId? }            // ← VCKP-02 binding
Agent      { id, role, provider, model, status, cardId?, sessionNodeId?, paneId?,
             budget{spent,limit}, permissionMode, attention? }
SessionNode{ id, parent, role, cardId?, envelope, transitions[], terminalState }
Evidence   { type:'diff'|'test'|'screenshot'|'verdict'|'auditSection', source,
             cardId?, sessionNodeId?, ts, payloadRef }
Decision   { kind:'permission'|'gate'|'block'|'signoff', cardId?, sessionNodeId?, ... }
```

Merge rule: `RunData` (snapshot) is the spine; the live registry overlays `Agent`/`Card` runtime fields (status, live budget, paneId) by id. Id bridge is the keystone — see Risks R1.

## 5. Cockpit layout contract (VCKP-05)

```
Titlebar / Workspace Tabs                          (existing, A12)
RunCommandBar                                      (NEW — VCKP-03)
┌────────────┬───────────────────────────┬───────────────────────┐
│ Team       │  Board Spine (6 cols)      │ Card Detail Drawer    │
│ Sidebar    │  compact cards             │ (selected card)       │
│ (live +    │  ───────────────────────  │ idea/AC · reviewerA/B │
│  swarm)    │  Timeline / Replay Rail    │ scope · budget · diff │
│            │                            │ tools · decisions     │
├────────────┴───────────────────────────┴───────────────────────┤
│ Gate Bar: budget · confidence · scope · unsupported claims      │
│ AttentionQueue (NEW — VCKP-04, global, dockable)                │
└─────────────────────────────────────────────────────────────────┘
Status Bar                                         (existing, A10/A12)
```

Existing panels are reused as drawer/rail content:
- `BoardPanel` → Board spine (cards become compact, click-to-select).
- `RosterPanel` → Team sidebar rows (merged with live registry + swarm).
- `SessionTreePanel` + `ReplayPanel` → Timeline rail.
- `AuditPanel`/`VerdictPanel`/`DiffPanel`/`ScopePanel`/`BudgetPanel`/`BlockedPanel` → Card detail drawer sections + gate bar.

## 6. Proposed build order (waves)

| Wave | Plans | Delivers |
|---|---|---|
| **W0** | V14-00 | Test scaffold; normalized-model type stubs; selection store skeleton; id-bridge fixture (snapshot run + fake live registry). |
| **W1** | V14-01 | **VCKP-01** normalized UI model + adapters (snapshot→model, registry→model overlay) + single selection store. Pure data layer, no layout change yet. |
| **W2** | V14-02, V14-03 (parallel) | V14-02 **VCKP-02** card↔session/pane binding + id map + click-to-focus. · V14-03 **VCKP-05** cockpit layout shell (Board spine + detail drawer + timeline rail + gate bar) recomposing existing panels behind a `cockpit` view-mode flag (tabs kept as fallback toggle). |
| **W3** | V14-04, V14-05 (parallel) | V14-04 **VCKP-03** RunCommandBar (intake + mode/team/scope/budget chips + native/terminal indicator; start via CLI path first). · V14-05 **VCKP-04** AttentionQueue (sources from snapshot decisions + live events). |
| **W4** | V14-06 | **VCKP-06** live SSE wiring via V13.1 client (feature-detected), live/snapshot state indicator, snapshot fallback. |
| **W5** | V14-07, V14-08 (parallel) | V14-07 **VCKP-07** swarm reconciliation (manifest→roster/board). · V14-08 **VCKP-08** Live↔Review mode toggle parity. |
| **W6** | V14-09 | **VCKP-09** feedback write-path (harness-gated) + **VCKP-10** a11y/dense pass + phase-final human-verify checkpoint. |

~10 plans / 7 waves (counts firm up at SPEC).

## 7. Dependencies

- **V11** (built) — HARD. Reuses all 10 panel components + `org/types.ts` + `orgStore.ts` + `guards.ts` D-02 contract.
- **A12** (built) — visual token base (Ignite theme). No new theme.
- **V13.1** (TS local client SDK, in progress) — for VCKP-06 live wiring only. **Soft**: snapshot fallback works without it. Live wiring waves (W4) gate on V13.1 contract snapshot + SSE client landing.
- **A13** (swarm) — for VCKP-07 only. **Soft**: degrade to "no swarm" when `.voss/swarm/` absent.
- **PROTOCOL.md** event union (locked v1) — source of truth for live event shapes (VCKP-04, VCKP-06).

## 8. Risks

- **R1 (keystone): id bridge between planes.** Live pane/agent ids and snapshot card/session-node ids may have no shared key today. Mitigation: W1 defines the id-bridge contract first; if no shared key exists, V14 must mint one at run-launch (RunCommandBar stamps a `cardId`/`sessionId` the harness echoes back). This is the make-or-break for VCKP-01/02 — verify the harness emits a stable correlation id before W2.
- **R2: unverified per-card fields.** Research proposed card badges (per-card confidence, reviewer A/B, retry) — only some exist in snapshot types (`AuditCard.retry_count`/`is_killed` ✓; per-card confidence ✗, it's a live SSE event). SPEC must cross-check each badge against `org/types.ts` + PROTOCOL before designing the card. Don't design fields the app can't load.
- **R3: V13.1 slip.** If V13.1 contract snapshot slips, W4 (live wiring) stalls. Mitigation: W0–W3 + W5 deliver full value on snapshots; W4 is independently shippable later.
- **R4: feedback write-path may not exist.** VCKP-09 is Could-tier precisely because the harness write path is unproven. Render disabled-with-reason rather than block the phase.

## 9. Out of scope

- Freeform/Studio canvas (Lemonade-style infinite canvas) — explicitly deferred; cockpit-first.
- Embedded browser / VerificationArtifact panel (research Pattern 7) — no webview infra; future phase.
- New harness contracts / new emit points — V14 is a **client** of PROTOCOL v1; if live data needs new events, that's a separate harness (M/V-runtime) phase.
- Rollback / re-run from replay — replay stays inspect-only (V11 contract preserved).
- Custom/user-defined board columns — columns stay the orchestrator state machine (6 fixed).

## 10. Success criteria (SPEC will make pass/fail)

1. One selection (card/run) visibly drives Board + detail drawer + timeline + gate bar simultaneously.
2. A running agent's live pane is reachable from its board card (and vice-versa) via the id bridge.
3. RunCommandBar starts a run with visible mode/team/scope/budget and a native-vs-terminal indicator; Auto cannot start without budget/scope shown.
4. AttentionQueue surfaces a permission request + a budget-threshold + a sign-off-available item, each deep-linking to its card/session.
5. With a live server (V13.1) the cockpit updates board/budget without manual refresh; without one, it falls back to snapshot and labels itself `snapshot`.
6. Swarm manifest agents appear as roster rows + board cards when `.voss/swarm/` is present.
7. Zero regression to the terminal grid, the existing `⌘⇧O` toggle, and V11's D-02 snapshot contract.
8. Reuses A12 tokens only; no new theme; keyboard-navigable cockpit.

---

*Next step: `/gsd-spec-phase V14` to lock VCKP-01..10 requirements + ambiguity gate, then `/gsd-ui-phase` for the cockpit UI-SPEC (recompose contract over the existing panels), then plan/execute.*
