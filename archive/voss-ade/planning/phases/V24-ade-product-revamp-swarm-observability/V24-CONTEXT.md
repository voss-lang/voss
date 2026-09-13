# Phase V24: ADE Product Revamp + Swarm Observability - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Reframe `apps/voss-app` into a product-coherent ADE: a **terminal workbench**
(run manually), an **agent mission-control layer** for managed Voss work, and a
**review/observability system** (Swarm Map + replay) that makes agent activity
understandable. Voss is the operating layer *around* the work, not a requirement
imposed on every pane.

**Hard preserves (non-negotiable):** Warp-style terminal grid, multiple
terminals, command-palette/grid ops, project-less use, user-owned terminal
workflows, session persistence — all working without Voss credentials or Voss
interpretation.

This phase clarifies **HOW** to implement the scoped revamp. New capabilities
(IDE/editor, mandatory Voss wrapping, team/billing admin, generic-SaaS
observability, new agent protocols) are out of scope — see ROADMAP V24
"Out of scope."

</domain>

<decisions>
## Implementation Decisions

### Portal ↔ Grid Spatial Model
- **D-01:** Left-portal surfaces (Overview/Tasks/Agents/Swarm Map/Review/Context/Memory/Settings) use **canvas-swap**. The selected surface takes the main canvas; the terminal grid stays **mounted and alive behind it** and snaps back instantly on return. NOT a persistent split, NOT a floating drawer. (Closest to Linear/Warp vertical-tab focus model.)
- **D-02 (discretion):** Launch / no-active-run view = **terminal grid** for fresh and project-less workspaces (enforces the L1 "ignore Voss, still a terminal" constraint on first paint). Workspaces that already have active managed runs restore their **last-used surface**. Booting straight to Overview was rejected — contradicts terminal-first thesis.

### Run Intake + Safety Posture
- **D-03:** The "Ask Voss to…" composer is **global and always-present** (top / command-bar, Cmd-K-style), reachable from any surface. Replaces today's exposed `RunCommandBar` Plan/Edit/Auto + target/budget clutter.
- **D-04:** Default safety mode = **Read only** — agent can analyze/plan but cannot edit until the user elevates. Matches the cage/trust posture; least surprising for a product about controlled agent work.
- **D-05:** Composer shows **only the ask + safety mode** by default. Scope, agent target, team, budget, and attached context are **all collapsed behind "Advanced."**

### Swarm Map Layout + Scope
- **D-06:** Default layout = **radial** — objective/run is the **center node**, agent nodes (Voss/Codex/Claude/reviewer/tester/…) orbit it, work + artifact + alert nodes radiate outward.
- **D-07:** Default scope = **all active runs at once** (true mission control). Reconciliation for the multi-center problem: the model is **one radial cluster per run/objective**, packed across the canvas; click a cluster to **focus/expand** it. This keeps each run honest and legible at scale rather than collapsing many objectives into one tangled center.

### Product Vocabulary / Naming
- **D-08:** Top-level user-facing unit of managed agent work = **"Task."** The "Tasks" portal item; the composer "creates a Task." (Note: the ROADMAP-listed "Runs" portal item is therefore labeled **"Tasks"** for IA consistency.)
- **D-09 (discretion):** Collision reconciliation — board work-items *inside* a Task are displayed as **"steps" / "cards"** in copy, **never "tasks,"** so the Swarm Map stays unambiguous. **Code identifiers stay `runId` / `RunData` / `currentRunId`** — display layer only; zero internal rename churn.
- **D-10:** Observability surface name = **"Swarm Map"** (nav + brand; on-brand with the swarm-coordination differentiator).
- **D-11:** Safety-mode labels = **Read only / Can edit / Autopilot.** Retire the exposed top-level **Plan / Edit / Auto** modes.

### Quiet Top Chrome (from ROADMAP scope, no fork)
- Top chrome keeps **project/window identity, command palette/status, mode indicators only**. The `fanout / pipeline / swarm / watchers` presets (today's `PresetSwitcher`) are **demoted to a layout menu / pane toolbar** — they are layout presets, not product navigation.

### Claude's Discretion
- **D-02** (launch view nuance) and **D-09** (Task/step naming reconciliation) were decided by Claude at the user's invitation. Flag to override before/at planning if either is wrong.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase definition (source of truth for scope/constraints)
- `.planning/ROADMAP.md` § "Phase V24: ADE Product Revamp + Swarm Observability" (≈ lines 2432–2474) — goal, product thesis, full scope, **Out of scope**, **Cross-cutting constraints**, dependency/consumes list, 8-plan / 6-wave structure.
- `.planning/phases/V24-ade-product-revamp-swarm-observability/V24-SPEC.md` — **PENDING.** VADE2-01..08 will be locked here (V-track: requirements live in the SPEC, not REQUIREMENTS.md). MUST read once it exists; this CONTEXT covers implementation forks, not the locked requirement text.

### Product/design framing (W0 inputs + targets)
- `apps/voss-app/CONCEPT.md` — existing product concept framing.
- `apps/voss-app/FEATURES.md` — existing feature inventory.
- V24-01 (W0) produces the missing **PRODUCT.md / DESIGN.md or ADE UI-SPEC** + copy vocabulary — those become canonical for W1–W5.

### Dependency / consumed substrate
- **V14** — cockpit components + selection model (recomposed here): `apps/voss-app/src/org/cockpit/*`, `apps/voss-app/src/org/selection.ts`.
- **V15** — live sidecar / SSE / protocol panes (feeds live Swarm Map): `apps/voss-app/src/org/live/*`.
- **A1–A13** — terminal grid + swarm substrate: `apps/voss-app/src/grid/*`, `apps/voss-app/src/swarm/*`.
- **Consumes when available:** V17 coordination bus/claims (graph edges, agent↔agent messages); V20 residue hardening (mission briefs, critical-risk gates); V9 audit artifacts (replay/review trust).

</canonical_refs>

<code_context>
## Existing Code Insights

(Scout of `apps/voss-app/src` — no `.planning/codebase/` maps exist yet.)

### Reusable Assets
- `src/org/cockpit/` — `CockpitShell`, `CockpitSidebar`, `RunCommandBar` (→ global composer rebuild, D-03), `runIntake.ts`, `TimelineRail` (→ replay scrubber), `CardDrawer`, `GateBar`, `serverSessions.ts`.
- `src/org/OrgViewShell.tsx` — current org/mission-control shell; portal canvas-swap host candidate.
- `src/org/replayReducer.ts`, `src/org/panels/ReplayPanel.tsx` — replay state for V24-07 timeline.
- `src/org/attention/*` (`AttentionPanel`, `attentionQueue`) — attention/alert actions for mission-control rows + Swarm Map alert nodes.
- `src/swarm/swarmTypes.ts`, `src/org/swarmReconcile.ts` — swarm node/edge model + reconcile; base for Swarm Map (D-06/07).
- `src/org/panels/*` — `BoardPanel`, `RosterPanel`, `BudgetPanel`, `ScopePanel`, `SessionTreePanel`, `AuditPanel`, `DiffPanel`, `VerdictPanel`, `BlockedPanel` — data already derived for graph nodes.
- `src/org/selection.ts` — deep-link/selection (`openInGridRequest`, `openInReviewRequest`, `setSelectedCardId`) for node→pane/drawer/diff click-through (D-06 node deep-links).
- `src/grid/GridRoot.tsx` (+ `grid/tree.ts`) — persistent grid canvas (stays mounted behind portal, D-01).
- `src/components/titlebar/PresetSwitcher.tsx` — the fanout/pipeline/swarm/watchers presets to **demote** (quiet-chrome decision).
- `src/components/sidebar/*` — `AgentSidebar`, `UsageSection`, `ActivitySection`, `SessionsSection`, `FileTree`, `GitSection`.
- `src/org/orgStore.ts` (`currentRunId`) — run/Task state; keep `runId` identifiers (D-09).

### Established Patterns (constraints)
- **State boundaries (cross-cutting, do not break):** Solid owns UI state; Tauri/Rust owns process/filesystem lifecycle; Python harness remains the orchestration source of truth.
- **No hidden `.voss/` writes on project open** — durable project writes stay lazy/intentional.
- Per-pane registries: `pane/paneSessionRegistry`, `budgetRegistry`, `contextRegistry`, `procRegistry`, `adoptionRegistry`, `agentDetect` — the seam between terminal panes and managed-run metadata.
- Honest-signal rule: Swarm Map renders only from real events/artifacts; missing signal → honest placeholder or omit, **never fake** agent communication. Motion communicates live state/flow/replay only; respect reduced-motion with a static trace/list fallback.

### Integration Points
- Portal nav layer wraps/sits above `GridRoot` + `OrgViewShell`, swapping the canvas while the grid stays mounted (D-01).
- Global composer replaces `RunCommandBar`'s exposed controls; advanced controls fold the existing scope/agent/budget/context registries (D-03/05).
- Swarm Map consumes `swarmReconcile` + board/session-tree/registry/audit data into the radial-cluster model (D-06/07).

</code_context>

<specifics>
## Specific Ideas

- Market references named in ROADMAP origin: **Warp** (separates terminal/agent contexts, vertical tabs/notifications/review), **Codex/Devin** (agent command center), agent-observability tools (graphs/traces/cost/tool calls). Voss differentiator = terminal-first control plane with memory, scope, budget, review, audit, **visible swarm coordination**.
- "Feel closer to **Linear** for agent work than a toolbar of raw run controls" — the target for Overview/Tasks/Agents surfaces.
- Replay is a **trust/audit** feature, not decorative motion.

</specifics>

<deferred>
## Deferred Ideas

None to other phases — discussion stayed within V24 scope.

**In-phase details intentionally left to SPEC / researcher / planner** (offered as
"more gray areas," user moved to context — these are NOT decided, NOT scope creep):
- Replay/timeline interaction detail (scrubber granularity, live↔replay handoff).
- Voss-vs-non-Voss pane visual distinction (how managed panes read differently from raw terminals).
- Mission-control IA granularity (Overview vs Tasks vs Agents as 3 routes vs unified inbox — ROADMAP enumerates separate routes; confirm in SPEC).
- Alert/attention node handling in the Swarm Map (permissions, failed tests, budget/scope gates).

</deferred>

---

*Phase: V24-ade-product-revamp-swarm-observability*
*Context gathered: 2026-06-14*
