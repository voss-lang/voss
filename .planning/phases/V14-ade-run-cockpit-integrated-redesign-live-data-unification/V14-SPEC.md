# Phase V14: ADE Run Cockpit (Integrated Redesign + Live Data Unification) — Specification

**Created:** 2026-06-08
**Ambiguity score:** 0.141 (gate: ≤ 0.20)
**Requirements:** 12 locked (9 must-ship core · 3 best-effort gated)
**Revised:** 2026-06-08 — added VCKP-11 (quick-launch refresh) + VCKP-12 (adopt running agent / "Manage with Voss"); mockups under `.planning/sketches/`.

## Goal

Recompose V11's 10 built org panels into a single integrated run cockpit (Board spine + Card detail drawer + Timeline/replay rail + gate bar) and merge the live PTY/SSE agent registry with the static CLI-JSON `RunData` into one normalized UI model with card↔session/pane binding — replacing the current tab-switching, snapshot-only org view.

## Background

V11 shipped and is live in `apps/voss-app`: `org/OrgViewShell.tsx` renders a 10-tab bar (Roster, Board, Tree, Audit, Verdict, Budget, Scope, Diff, Blocked, Replay), one panel active at a time. Data comes from `org/orgStore.ts` via Tauri `invoke('load_run' | 'enumerate_runs')` returning a static `RunData` snapshot (`org/types.ts:202`), validated by `org/guards.ts` (D-02), with manual refresh. `org/decisionActions.ts` shells `voss audit --approve` (one write path; Reject/Unblock disabled).

Separately, a **live data plane** exists: the agent registry in `src-tauri/src/lib.rs` + `components/sidebar/AgentSidebar.tsx` drives PTY panes from SSE/process state. The two planes describe the same logical entities (agent, card, budget) but share no types and no ids: `org/types.ts` has no `Agent` type, `CardSnapshot` is minimal (`id/role/risk/status/budget`), and a board card has no link to a live pane.

PROTOCOL v1 is locked (SSE event union incl. `permission.updated`, `budget.updated`, `confidence.updated`, `gate.updated`, `session.idle`, `probable`). V13.1 (TS local client SDK) is in progress and owns the committed contract snapshot. A13 swarm defines `.voss/swarm/{manifest.json,tasks/,results/}`.

What does NOT exist yet: a normalized UI model unifying the two planes; card↔session/pane binding; the cockpit composition (panels are tab-isolated, no shared selection drives them); a `RunCommandBar` intake surface; a global `AttentionQueue`; any live-event wiring into the org view. The deep-research design-contract analysis (`research/ade-ui-design-contract-research.md`) identifies these as the structural gaps V14 closes.

## Requirements

Tiers: **[CORE]** = must ship for V14 to be DONE. **[GATED]** = best-effort; ships if its dependency is ready, else degrades gracefully and does NOT fail the phase.

1. **[CORE] Normalized UI data model (VCKP-01)**: One view-layer model unifies the live registry and the snapshot.
   - Current: `org/types.ts` has `RunData`/`CardSnapshot`/`SessionTreeNode`/`AuditReport`/`ReviewSidecar` (snapshot only); live agents live in the Rust registry + `AgentSidebar` with no shared TS model.
   - Target: a TS model `{ Run, Card, Agent, SessionNode, Evidence, Decision }` (extending `org/types.ts`) with adapters `snapshot→model` and `registry→model overlay`; a single selection store (`selectedRun`/`selectedCard`) is the one source every surface reads.
   - Acceptance: a unit test feeds a golden `RunData` snapshot + a fake live-registry payload into the adapters and asserts one merged model where a card carries both snapshot fields and live-overlay fields (status, live budget, `paneId`); selecting a card in the store is observable by ≥2 distinct surfaces in a component test.

2. **[CORE] Card ↔ session/pane binding (VCKP-02)**: Every board card resolves to its live pane and/or recorded session node via a shared id map.
   - Current: no id correlates a board card (`boardDerive.ts`) with a live PTY pane (registry) or always with its `SessionTreeNode`.
   - Target: an id-bridge that maps `card → { paneId?, sessionNodeId? }`; clicking a card focuses its live pane when running, else opens its detail; clicking a live pane reveals its card.
   - Acceptance: with a fixture where card `C1` is bound to pane `P1` and node `N1`, a test asserts `resolveCard('C1')` returns `{paneId:'P1', sessionNodeId:'N1'}`; a click handler test focuses `P1`; a card with no live pane falls back to detail-open without error.

3. **[CORE] RunCommandBar (VCKP-03)**: Primary intake strip that starts runs.
   - Current: no `RunCommandBar`/`GoalBar` exists anywhere in `src/`.
   - Target: an intake bar with goal/command input · mode segmented control (Plan/Edit/Auto) · team selector · scope chip · budget chip · context attach · explicit **Voss-native vs terminal-agent** indicator. It **starts both**: terminal-agent runs via the existing PTY/CLI launch path, and Voss-native runs via protocol session-create (V13.1 client). Auto mode cannot start without budget AND scope visible. Mode is never hidden in placeholder text.
   - Acceptance: a test starts a terminal-agent run from the bar (asserts the existing launch path is invoked with mode/team/scope/budget); a fixture/mock-client test starts a Voss-native run (asserts a protocol session-create call with the assembled spec); an Auto-mode start with no budget or no scope is blocked with a visible reason.

4. **[CORE] AttentionQueue (VCKP-04)**: Global queue that prevents hidden stalls.
   - Current: no attention/permission queue; permission prompts surface only per-pane (live) or not at all (org).
   - Target: a global queue with item categories sourced from `permission.updated`, `gate.updated`, `budget.updated` (threshold), `confidence.updated` (below gate), `session.idle`, verification-failed, and sign-off-available; each item deep-links to its card/session/evidence. Permission items show tool + args + dimension + affected path + {allow-once, allow-scoped, deny}.
   - Acceptance: a test injects a permission event, a budget-threshold event, and a sign-off-available event and asserts three queue items render, each with a working deep-link to its bound card/session; a permission item exposes allow-once/allow-scoped/deny actions.

5. **[CORE] Integrated cockpit layout (VCKP-05)**: One layout, one selection, tabs demoted.
   - Current: `OrgViewShell.tsx:32-56` is a horizontal tab bar; selecting a panel shows only that panel; no shared selection links panels.
   - Target: a cockpit view = Board spine (6 columns, compact cards) + Card detail drawer (selected-card source-of-truth, composed from existing Audit/Verdict/Diff/Scope/Budget/Blocked panel bodies) + Timeline/replay rail (SessionTree + Replay) + bottom gate bar (budget/confidence/scope/unsupported-claims). The same selected card/run drives all four regions. Existing panel components are reused (not rewritten); the old tab view remains reachable as a fallback toggle.
   - Acceptance: a component test selects card `C1` once and asserts the Board highlights `C1`, the detail drawer shows `C1` content, the timeline rail scrolls to `C1`'s node, and the gate bar reflects `C1`'s envelope — from a single selection action; zero regression to the existing `⌘⇧O` toggle and the terminal grid (existing tests stay green).

6. **[GATED: V13.1] Live SSE wiring (VCKP-06)**: In-flight runs update without manual refresh.
   - Current: `orgStore.ts` is snapshot-only; no EventSource/SSE consumption in the org view.
   - Target: when a Voss-native run is in-flight and the V13.1 client/server is available, the cockpit consumes the SSE event union for live board/budget/confidence/gate updates; falls back to snapshot + manual refresh otherwise; UI renders a visible **live vs snapshot** state label.
   - Acceptance: a fixture/mock SSE stream drives a board+budget update in the cockpit with no manual refresh (test-verifiable now); the live-vs-snapshot label renders `live` under the mock stream and `snapshot` without one. (Real `voss serve` end-to-end verification deferred to when V13.1 ships.)

7. **[GATED: A13] Swarm reconciliation (VCKP-07)**: Swarm agents appear in the cockpit.
   - Current: `.voss/swarm/manifest.json` agents are not roster rows or board cards; the board derives from `RunData` only.
   - Target: when `.voss/swarm/` is present, manifest agents render as roster rows and board cards; per-agent swarm status (pending/running/complete) maps to board columns; swarm goal shows as the run idea.
   - Acceptance: a test with a fixture `manifest.json` (2 agents) renders 2 roster rows + 2 board cards with columns matching each agent's status; absence of `.voss/swarm/` degrades to "no swarm" with no error.

8. **[CORE] Live Work ↔ Run Review mode toggle (VCKP-08)**: One run, two modes, grid preserved.
   - Current: only the `⌘⇧O` grid↔org toggle exists; no Live/Review distinction over a single run.
   - Target: a Live Work ↔ Run Review toggle over the same selected run that preserves the terminal grid (extends the existing toggle); starting in Live Work yields the same session-tree/audit evidence path as a delegated run.
   - Acceptance: a test toggles Live↔Review on one run and asserts the selected run/card persists across the switch and the terminal grid state is unchanged after returning.

9. **[GATED: harness write path] Feedback write-path (VCKP-09)**: Inline comment routes to the bound session.
   - Current: V11 has one write path (`voss audit --approve`); Reject/Unblock are disabled-with-reason.
   - Target: an inline card/diff comment routes a follow-up to the bound session **where the protocol exposes a write path**; rendered disabled-with-reason where it does not. No fake affordances.
   - Acceptance: where a write path exists, a test asserts a comment dispatches a follow-up to the correct `sessionNodeId`; where it does not, the affordance renders disabled with a visible reason string (no silent no-op).

10. **[CORE] Dense operational pass + accessibility (VCKP-10)**: Cockpit is keyboard-navigable and token-consistent.
    - Current: no a11y pass on org surfaces; cockpit surfaces do not exist yet.
    - Target: keyboard navigation across Board → detail drawer → timeline; reduced-motion honored; state colors meet contrast; budget/cost/confidence rendered in monospace numerics; reuses A12 Ignite tokens only (no new theme).
    - Acceptance: a test drives keyboard focus Board→drawer→timeline and asserts focus order; a grep/lint check asserts no new theme tokens introduced (A12 tokens only); reduced-motion media query disables cockpit animations.

11. **[CORE] Ad-hoc agent launch — refreshed quick-launch (VCKP-11)**: Sparse, premium launch modal for terminal agents.
    - Current: an A12 launch modal exists off `AgentSidebar` Quick-Launch, but is config-heavy (raw-command field + explainer copy).
    - Target: a minimal launch modal — CLI preset cards (Claude/Codex/Gemini/OpenCode/Aider/Custom) each showing the user's **default model**, one optional "what should it work on?" prompt, working directory + pane placement (Right/Below/New tab). **No raw-command field, no explainer block** — the preset resolves the user's configured CLI command/model. Spawns a PTY terminal agent (Path 1, no cage). Mockup: `.planning/sketches/V14-spawn-modals-mockup.html` (Quick-launch).
    - Acceptance: launching from a preset spawns a PTY terminal agent in the chosen pane placement using the preset's resolved command; the modal exposes no raw-command field and no explainer paragraph; `⌘↵` launches, Esc/Cancel dismisses without spawning; the agent appears under "External Terminal Agents" in the roster.

12. **[CORE] Adopt a running agent into a run — "Manage with Voss" (VCKP-12)**: Bring an ad-hoc terminal agent under run management, **forward-only**, in plain language.
    - Current: an ad-hoc terminal agent has no card, budget, scope, review, or audit, and no path to gain them after launch.
    - Target: a plain-language "Let Voss manage this agent" flow — add to current/new run · bind as a task (role/risk, both pre-inferred + editable) · set budget + scope. From adoption forward, Voss **tracks cost, records the PTY transcript as an audit node, monitors the budget (stop/warn at limit), and requires review before the task is marked done**; scope is shown **advisory**. Copy states outcomes, not internal mechanics ("cage", "PermissionGate", "session-tree node" never appear). Pre-adoption activity is excluded; the audit node is marked **partial lineage**. Mockup: `.planning/sketches/V14-spawn-modals-mockup.html` (Manage with Voss).
    - **Honest limit (locked):** for an *external* CLI agent Voss sees the PTY stream, **not** the agent's internal tool loop — so true per-tool PermissionGate enforcement is **NOT** possible on adopted external agents (that remains Voss-native only). The adopt UI must not promise per-tool gating it cannot deliver; it offers budget-monitor + transcript-audit + review-gate + advisory-scope.
    - Acceptance: adopting a running pane creates/links a card bound to that pane's session, applies budget + scope, starts a transcript audit node marked `partial_lineage`, and enforces review-before-done; pre-adoption events are absent from its budget/audit; the modal copy contains no internal-mechanics jargon and makes no per-tool-gate promise for external agents. Where no harness adopt path exists yet, the action renders disabled-with-reason (no fake affordance).

## Boundaries

**In scope:**
- Normalized UI data model + snapshot/registry adapters + single selection store (VCKP-01).
- Card↔session/pane id-bridge + click-to-focus/reveal (VCKP-02).
- RunCommandBar intake that starts terminal-agent AND Voss-native runs (VCKP-03).
- Global AttentionQueue sourced from snapshot decisions + live events (VCKP-04).
- Integrated cockpit layout recomposing the existing 10 panel components (VCKP-05).
- Live SSE wiring via V13.1 with snapshot fallback + live/snapshot label (VCKP-06, best-effort).
- A13 swarm-manifest reconciliation into roster/board (VCKP-07, best-effort).
- Live Work ↔ Run Review mode toggle preserving the grid (VCKP-08).
- Feedback write-path where the harness exposes one, disabled-with-reason otherwise (VCKP-09, best-effort).
- Dense/keyboard/a11y pass on A12 tokens (VCKP-10).
- Refreshed sparse quick-launch modal for ad-hoc terminal agents (VCKP-11).
- "Manage with Voss" adopt flow — forward-only tracking/audit/review for a running agent (VCKP-12).

**Out of scope:**
- Rewriting panel internals — V14 recomposes existing `org/panels/*`, it does not reimplement them. (Reuse, not rewrite.)
- Retroactive audit/budget of pre-adoption activity — adoption is forward-only; the audit node is marked `partial_lineage`. (The alternative "discard + re-run clean as Voss-native" was considered and deferred — keep the running work, accept partial lineage.)
- Per-tool PermissionGate enforcement on adopted *external* CLI agents — impossible from the PTY layer; remains Voss-native only.
- New harness contracts / new SSE event types / new emit points — V14 is a PROTOCOL v1 client; new events are a separate harness phase.
- Freeform/Studio infinite canvas — cockpit-first; canvas deferred indefinitely.
- Embedded browser / VerificationArtifact panel — no webview infra; future phase.
- Rollback / re-run from replay — replay stays inspect-only (preserves V11 contract).
- Custom/user-defined board columns — the 6 columns encode the orchestrator state machine; custom labels excluded.
- Real `voss serve` end-to-end live verification — fixture/mock-verified in V14; real-server verification rides V13.1 shipping.

## Constraints

- **Reuse, don't rewrite:** the 10 `org/panels/*.tsx` components, `org/types.ts`, `org/orgStore.ts`, `org/guards.ts` (D-02 contract), and `decisionActions.ts` are reused. The D-02 snapshot contract must not regress.
- **A12 tokens only:** no new theme; cockpit uses the existing Ignite palette/token set.
- **Keystone — id bridge:** correlating live pane/agent ids with snapshot card/session-node ids is the make-or-break dependency for VCKP-01/02. If no shared key exists today, V14 must mint a correlation id at run-launch (RunCommandBar stamps it; harness echoes it back). This must be verified before the binding wave; treat as the top risk.
- **Per-card field availability:** proposed card badges must be cross-checked against `org/types.ts` + PROTOCOL before use — `AuditCard.retry_count`/`is_killed` exist; per-card confidence is a live SSE event, NOT a snapshot field. Do not design fields the app cannot load.
- **Dependency gating:** VCKP-06 gates on V13.1 (contract snapshot + SSE client); VCKP-07 gates on A13; VCKP-09 gates on a harness write path. Each degrades gracefully when its dependency is absent.
- **No grid/PTY regression:** the terminal grid, `⌘⇧O` toggle, and live PTY panes must remain unaffected.
- **Adoption is best-effort for external agents:** an adopted external CLI agent gets cost tracking, PTY-transcript audit (partial lineage), budget monitor (kill/warn at limit), review-before-done, and advisory scope — NOT per-tool gate enforcement. Adopt copy must reflect this; do not overstate control.
- **Spawn-UX copy rule:** user-facing spawn/adopt surfaces state outcomes, never internal mechanics. Terms `cage`, `Voss-native`, `PermissionGate`, `session-tree node`, `partial lineage`, `pane` do not appear in the UI (they live in SPEC/code only).

## Acceptance Criteria

- [ ] Adapters merge a golden snapshot + fake live-registry payload into one model where a card carries both snapshot and live-overlay fields (VCKP-01).
- [ ] A single `selectedCard` action is observed by ≥2 surfaces (VCKP-01) and drives Board + detail drawer + timeline + gate bar together (VCKP-05).
- [ ] `resolveCard(id)` returns `{paneId?, sessionNodeId?}`; card-click focuses the bound live pane, else opens detail without error (VCKP-02).
- [ ] RunCommandBar starts a terminal-agent run with mode/team/scope/budget; starts a Voss-native run via mock protocol session-create; Auto with missing budget/scope is blocked with a visible reason (VCKP-03).
- [ ] AttentionQueue renders permission + budget-threshold + sign-off items, each deep-linking to its card/session; permission item exposes allow-once/allow-scoped/deny (VCKP-04).
- [ ] Mock SSE stream updates board+budget with no manual refresh; live-vs-snapshot label renders `live`/`snapshot` correctly (VCKP-06, best-effort).
- [ ] Fixture `manifest.json` renders swarm agents as roster rows + board cards by status; absent `.voss/swarm/` degrades to no-swarm without error (VCKP-07, best-effort).
- [ ] Live↔Review toggle preserves selected run/card and leaves the terminal grid unchanged (VCKP-08).
- [ ] Feedback comment dispatches to the correct `sessionNodeId` where a write path exists, else renders disabled-with-reason (no silent no-op) (VCKP-09, best-effort).
- [ ] Keyboard focus traverses Board→drawer→timeline; no new theme tokens introduced (A12 only); reduced-motion disables cockpit animation (VCKP-10).
- [ ] Quick-launch modal spawns a PTY agent from a preset (default model), with no raw-command field and no explainer block; agent lands under External Terminal Agents (VCKP-11).
- [ ] "Manage with Voss" adopts a running pane: binds a card, applies budget+scope, starts a `partial_lineage` transcript-audit node, enforces review-before-done; copy carries no internal-mechanics jargon and no per-tool-gate promise for external agents (VCKP-12).
- [ ] Existing V11/grid tests stay green; D-02 snapshot contract and `⌘⇧O` toggle do not regress.

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                        |
|--------------------|-------|------|--------|--------------------------------------------------------------|
| Goal Clarity       | 0.88  | 0.75 | ✓      | Recompose + unify; core-7 vs gated-3 crisp                   |
| Boundary Clarity   | 0.90  | 0.70 | ✓      | Explicit in/out; reuse-not-rewrite; gated deps named         |
| Constraint Clarity | 0.78  | 0.65 | ✓      | id-bridge keystone + per-card field check + A12-only locked  |
| Acceptance Criteria| 0.85  | 0.70 | ✓      | Fixture/mock-driven falsifiable bars; terminal real          |
| **Ambiguity**      | 0.141 | ≤0.20| ✓      |                                                              |

Status: ✓ = met minimum. All dimensions met; no assumptions flagged.

## Interview Log

| Round | Perspective        | Question summary                         | Decision locked                                                                 |
|-------|--------------------|------------------------------------------|---------------------------------------------------------------------------------|
| 0     | (pre-spec brief)   | V11↔V14 relationship                     | V11 is BUILT; V14 recomposes existing panels (not a rewrite)                    |
| 0     | (pre-spec brief)   | Live-data aggressiveness                 | Unify model now; live SSE wiring gated on V13.1 with snapshot fallback          |
| 1     | Boundary/Simplifier| Irreducible must-ship core of the 10     | Core-7 (01/02/03/04/05/08/10) must-ship; 06/07/09 best-effort, degrade gracefully|
| 1     | Boundary           | Does RunCommandBar start runs?           | Starts BOTH native + terminal; native start fixture-verifiable, rides V13.1 gate |
| 1     | Failure Analyst    | Falsifiable bar for "live works"         | Fixture/mock SSE drives update + visible live/snapshot label; real-server deferred|
| 2     | Simplifier (mockup)| Quick-launch modal scope                 | Sparse premium modal: preset+default-model, one prompt, dir/pane; drop raw-command + explainer (VCKP-11)|
| 2     | Boundary (mockup)  | Can an ad-hoc agent be adopted?          | Yes — "Manage with Voss" adopt flow, forward-only, plain language (VCKP-12)      |
| 2     | Failure Analyst    | Can adoption truly gate an external CLI? | No — PTY-only visibility; adoption = cost/audit/budget-monitor/review, NOT per-tool gate (locked limit)|
| 2     | Boundary (mockup)  | Keep pre-adoption work or re-run clean?  | Keep running work; mark audit node `partial_lineage` (re-run-clean alternative deferred)|

---

*Phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification*
*Spec created: 2026-06-08*
*Next step: /gsd-discuss-phase V14 — implementation decisions (id-bridge mechanism, cockpit layout/CSS, adapter shapes, store wiring)*
