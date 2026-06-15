# Phase V24: ADE Product Revamp + Swarm Observability — Specification

**Created:** 2026-06-14
**Ambiguity score:** 0.15 (gate: ≤ 0.20)
**Requirements:** 8 locked

## Goal

Reframe `apps/voss-app` from a terminal app that exposes internal layout
presets and orchestration plumbing into a product-coherent ADE: a terminal
workbench (unchanged for manual use), a left-portal mission-control layer for
managed agent work, and a Swarm Map observability/replay surface — such that a
fluent developer understands what Voss does on first open without learning
internal labels, while every preserved terminal capability still works without
Voss.

## Background

`apps/voss-app/src` already contains the substrate: `grid/` (Warp-style tiling),
`org/cockpit/*` (V14 cockpit — `CockpitShell`, `RunCommandBar`, `runIntake`,
`TimelineRail`, `GateBar`, `CardDrawer`), `org/` (board derive, `replayReducer`,
`attention/`, `selection`, `orgStore`/`currentRunId`), `swarm/` (`swarmTypes`,
`swarmReconcile`), `org/live/*` (SSE/sidecar/protocol), `org/panels/*` (board,
roster, budget, scope, session-tree, audit, diff, verdict, blocked), and
`components/titlebar/PresetSwitcher` (the `fanout/pipeline/swarm/watchers`
presets). The problem: top-level chrome surfaces layout presets as navigation
and exposes raw modes (`Plan/Edit/Auto`), targets, and snapshot/review labels
before the user understands the product. No left portal, no humane intake
composer, and no Swarm Map exist yet. V-track requirements live here (not in
`REQUIREMENTS.md`). Implementation decisions are captured in `V24-CONTEXT.md`.

## Requirements

1. **Product/design contract (VADE2-01)**: A written product + design contract precedes UI churn and locks vocabulary.
   - Current: No PRODUCT.md/DESIGN.md/ADE UI-SPEC exists for `apps/voss-app`; `CONCEPT.md`/`FEATURES.md` describe features, not product register or copy vocabulary.
   - Target: A committed product/design contract (PRODUCT.md/DESIGN.md or ADE UI-SPEC) defining default register (product, primary user Ben), IA model, success criteria, and the locked copy vocabulary: top-level unit = **"Task"** (portal item "Tasks"); observability surface = **"Swarm Map"**; safety modes = **Read only / Can edit / Autopilot**; board work-items = "steps"/"cards"; internal `runId`/`RunData` identifiers retained in code only.
   - Acceptance: The contract file exists, is committed, and enumerates the IA, success criteria, and the vocabulary above; downstream plans cite it.

2. **Left portal shell + route/state model (VADE2-02)**: A left portal is the navigation model; the terminal grid is the persistent canvas.
   - Current: Navigation is driven by top chrome / `PresetSwitcher`; no left portal; `OrgViewShell` and `GridRoot` are not composed under a portal route model.
   - Target: A left portal with items Overview, Tasks, Agents, Swarm Map, Review, Context, Memory, Settings, backed by a route/state model. Selecting a surface uses **canvas-swap**: the surface takes the canvas while `GridRoot` stays mounted/alive and restores instantly on return. New product surfaces = Overview/Tasks/Agents/Swarm Map; Review/Context/Memory/Settings wire to existing V14/panels/drawers as-is (no redesign).
   - Target launch behavior: fresh/project-less workspaces boot to the terminal grid; workspaces with active managed runs restore last-used surface.
   - Acceptance: Each portal item routes to its surface; switching surfaces and back preserves grid/pane state (terminals not torn down — verifiable by pane/session identity persisting across a portal round-trip); fresh workspace opens on the grid.

3. **Quiet top chrome + layout-control demotion (VADE2-03)**: Top chrome shows product identity only; layout presets are not navigation.
   - Current: Top chrome exposes `fanout/pipeline/swarm/watchers` presets and mode/target plumbing as top-level controls.
   - Target: Top chrome retains project/window identity, command palette/status, and mode indicators only. `fanout/pipeline/swarm/watchers` (today's `PresetSwitcher`) are demoted to a layout menu / pane toolbar.
   - Acceptance: Default top-level chrome contains no `fanout/pipeline/swarm/watchers` preset controls and no raw `Plan/Edit/Auto` mode toggles; the presets remain reachable from a layout menu/pane control (test or screenshot-review confirms both placement changes).

4. **Humane run intake composer (VADE2-04)**: A progressive "Ask Voss to…" composer replaces exposed run plumbing.
   - Current: `RunCommandBar` exposes `Plan/Edit/Auto`, `Voss run`, `Terminal agent`, and budget/scope controls inline.
   - Target: A global, always-present "Ask Voss to…" composer (command-bar style) showing only the ask + safety mode by default, with safety **defaulting to Read only**; scope, agent target, team, budget, and attached context collapsed behind "Advanced". No raw internal labels shown by default.
   - Acceptance: The composer is reachable from any surface; on open it shows only the prompt field + a safety-mode control defaulted to Read only; scope/agent/team/budget/context are not visible until "Advanced" is expanded.

5. **Mission-control Overview/Tasks/Agents surfaces (VADE2-05)**: Managed agent work reads like a status system, not a toolbar.
   - Current: Run state is surfaced via cockpit panels/attention queue without a Linear-like overview of work by status.
   - Target: Overview/Tasks/Agents surfaces present active, blocked, reviewing, done, adopted, and terminal-agent work with clear statuses, attention actions, and pane/run deep links (reusing `org/selection` click-through).
   - Acceptance: For a fixture set of runs spanning each status, each appears under the correct status grouping; an attention action on a blocked item is actionable; a deep link from a row opens the corresponding pane/drawer.

6. **Swarm Map static model (VADE2-06)**: An honest graph derived only from real signals.
   - Current: `swarmReconcile`/`swarmTypes` exist but there is no Swarm Map surface rendering objective/agent/work/artifact/alert nodes.
   - Target: A static Swarm Map deriving nodes/edges from RunData, board/session tree, registry, budget/context, and audit/review artifacts. Layout = **radial** (objective/run center, agents orbit, work/artifact/alert nodes radiate); multi-run default = one radial cluster per run, click a cluster to focus. Missing signals render honest placeholders or are omitted — never synthesized.
   - Acceptance: A guard test feeds empty and partial signal sources and asserts the map renders honest placeholders / omits nodes and **emits no edge without a real source** (no fabricated agent communication); with full fixture data, objective/agent/work/artifact/alert nodes render in radial clusters.

7. **Live Swarm Map + replay (VADE2-07)**: Live state and audit replay over the graph.
   - Current: `org/live/*` (SSE/registry) and `replayReducer`/`ReplayPanel`/`TimelineRail` exist but are not wired to a Swarm Map.
   - Target: Live edge/node updates from SSE/registry with subtle animated connectors (delegation/messages/tool calls/edits/review/validation/blockers) and a reduced-motion static fallback; completed runs replay through a timeline scrubber.
   - Acceptance: With a live fixture/stream, edges update on new events; with `prefers-reduced-motion`, connectors render static (no animation) with an equivalent trace/list; a completed run can be scrubbed through its timeline and the graph state reflects the scrub position.

8. **Validation gates (VADE2-08)**: The revamp is proven, not assumed.
   - Current: No V24-specific validation exists.
   - Target: A validation pass covering terminal-first preservation, cockpit/deep-link behavior, visual screenshot checks, a11y/reduced-motion, the no-fake-signal guard, and focused Tauri/Rust/TS verification.
   - Acceptance: The manual terminal-first checklist (open/split/focus/run-arbitrary-command/launch custom CLI agent/project-less/session-persist, all without Voss credentials) passes and is documented; existing grid/pane/terminal unit tests stay green; the no-fake-signal guard test (R6) passes; deep-link and a11y/reduced-motion checks pass; focused Tauri/Rust/TS suites pass.

## Boundaries

**In scope:**
- Product/design contract + locked vocabulary (R1)
- Left portal + route/state model with canvas-swap; grid stays mounted (R2)
- Quiet top chrome + preset demotion (R3)
- Global humane "Ask Voss to…" composer, Read-only default, advanced-collapsed (R4)
- Overview/Tasks/Agents mission-control surfaces with statuses, attention, deep links (R5)
- Swarm Map static model — radial, multi-run clusters, honest missing-signal handling (R6)
- Live Swarm Map updates + reduced-motion fallback + replay scrubber (R7)
- Validation: manual L1 checklist, no-fake-signal guard, deep-link/a11y/visual/Tauri/Rust/TS (R8)
- New surfaces built for Overview/Tasks/Agents/Swarm Map; Review/Context/Memory/Settings wired to existing V14/panels as-is

**Out of scope:**
- Replacing the terminal grid with an IDE/editor — preserves terminal-first thesis
- Mandatory Voss wrapping for all panes — L1 credibility constraint
- Redesigning Review/Context/Memory/Settings surfaces — reuse existing shipped UIs this phase
- Cloud/team admin, billing/licensing UI — future audience, not this phase
- Generic observability-SaaS dashboards / decorative-only graph animation — motion must convey real state
- Changing harness orchestration semantics; new agent protocols beyond `voss serve`, SDK/SSE, PTY registry, board/session/audit data, later V17 bus — orchestration source of truth unchanged
- Automated terminal-first regression suite as the L1 *acceptance* gate — user chose manual checklist (existing unit tests stay green as baseline only)

## Constraints

- **L1 terminal credibility is non-negotiable:** a user can ignore Voss and use the app as a terminal (no Voss credentials required for terminal workflows).
- **Honest signals only:** the Swarm Map renders from real events/artifacts; missing signal → honest placeholder or omission, never fabricated agent communication.
- **Motion communicates state:** animation conveys live state/flow/replay only; respect `prefers-reduced-motion` with a static trace/list fallback.
- **App state boundaries intact:** Solid owns UI state; Tauri/Rust owns process/filesystem lifecycle; the Python harness remains the orchestration source of truth.
- **No hidden writes to `.voss/` on project open:** durable project writes stay lazy and intentional.
- **Dependencies:** consumes V14 (cockpit/selection) and V15 (live sidecar/SSE) substrate; A1–A13 grid/swarm substrate. Consumes V17 bus/claims, V20 residue, V9 audit when available; absence must degrade to honest placeholders, not blockers.

## Acceptance Criteria

- [ ] Product/design contract committed with IA, success criteria, and locked vocabulary (Task / Swarm Map / Read only·Can edit·Autopilot / steps·cards)
- [ ] Left portal exposes all 8 items; selecting a surface uses canvas-swap and grid/pane state survives a portal round-trip
- [ ] Fresh/project-less workspace boots to the terminal grid
- [ ] Default top chrome contains no `fanout/pipeline/swarm/watchers` presets and no raw `Plan/Edit/Auto` toggles; presets reachable via layout menu/pane control
- [ ] "Ask Voss to…" composer is global, defaults to Read only, and hides scope/agent/team/budget/context behind "Advanced"
- [ ] Overview/Tasks/Agents show fixture runs under correct statuses with working attention action + deep link
- [ ] Swarm Map renders radial clusters (one per run) from full fixture data
- [ ] No-fake-signal guard test passes: empty/partial sources yield placeholders/omission and zero source-less edges
- [ ] Live edges update from a stream fixture; reduced-motion yields static connectors + trace fallback; completed run is replay-scrubbable
- [ ] Manual terminal-first checklist passes and is documented; existing grid/pane/terminal unit tests stay green
- [ ] Deep-link, a11y/reduced-motion, visual screenshot, and focused Tauri/Rust/TS checks pass

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                        |
|--------------------|-------|------|--------|----------------------------------------------|
| Goal Clarity       | 0.88  | 0.75 | ✓      | Full 8-plan scope confirmed                  |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | Portal depth + explicit out-of-scope locked  |
| Constraint Clarity | 0.80  | 0.65 | ✓      | L1, honest-signal, motion, state boundaries  |
| Acceptance Criteria| 0.82  | 0.70 | ✓      | Falsifiable bars incl. no-fake-signal guard  |
| **Ambiguity**      | 0.15  | ≤0.20| ✓      |                                              |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective         | Question summary                          | Decision locked                                                   |
|-------|---------------------|-------------------------------------------|------------------------------------------------------------------|
| 1     | Researcher+Simplifier | Must-ship core vs stretch (8 plans)?    | All 8 plans (W0–W5) in V24, incl. live Swarm Map + replay        |
| 1     | Researcher+Simplifier | Portal-surface depth (8 items)?         | New: Overview/Tasks/Agents/Swarm Map; reuse existing for the rest |
| 2     | Failure Analyst     | L1 preservation falsifiable bar?          | Manual terminal-first checklist (existing unit tests green baseline) |
| 2     | Failure Analyst     | Swarm Map "no fake comms" enforcement?    | Guard test: nodes/edges only from real sources; missing→placeholder |
| 2     | Failure Analyst     | What single thing = product failure?      | Two hard-fails: raw internal labels in default chrome OR presets-as-nav |

---

*Phase: V24-ade-product-revamp-swarm-observability*
*Spec created: 2026-06-14*
*Next step: /gsd-discuss-phase V24 — implementation decisions (CONTEXT.md already exists from a prior discuss run; re-run to reconcile against this SPEC, or proceed to /gsd-plan-phase V24)*
