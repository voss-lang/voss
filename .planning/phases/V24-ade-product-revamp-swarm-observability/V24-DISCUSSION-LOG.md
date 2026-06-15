# Phase V24: ADE Product Revamp + Swarm Observability - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-14
**Phase:** V24-ade-product-revamp-swarm-observability
**Areas discussed:** Portal ↔ grid spatial model, Run intake + safety posture, Swarm Map layout + scope, Product vocabulary / naming

---

## Portal ↔ Grid Spatial Model

### Q1 — Portal surface vs grid canvas

| Option | Description | Selected |
|--------|-------------|----------|
| Canvas swap (grid persists behind) | Portal surface takes the canvas; grid stays mounted/alive, snaps back instantly | ✓ |
| Persistent split beside grid | Portal docks beside grid, resizable; denser, more layout state | |
| Overlay / drawer over grid | Portal floats over grid as dismissible drawer; can feel cramped for Swarm Map | |

**User's choice:** Canvas swap.

### Q2 — Launch / no-active-run view

| Option | Description | Selected |
|--------|-------------|----------|
| Terminal grid (terminal-first) | Boots to terminals; Voss opt-in; matches L1 credibility | ✓ (Claude pick) |
| Overview surface | Boots to mission control; risks contradicting terminal-first | |
| Last-used / remembered | Restore last active surface per workspace | (folded in) |

**User's choice:** "What do you think?" — delegated to Claude.
**Notes:** Claude recommended terminal grid for fresh/project-less workspaces (L1 constraint), with last-used restore for workspaces that already have active managed runs. Locked as discretion (D-02), override invited.

---

## Run Intake + Safety Posture

### Q1 — Composer location

| Option | Description | Selected |
|--------|-------------|----------|
| Global, always-present (top/command bar) | Reachable anywhere, Cmd-K style; replaces RunCommandBar clutter | ✓ |
| Runs surface only | Lives in Runs portal view; cleaner chrome, more deliberate | |
| Both (global trigger → Runs) | Global trigger opens composer, submit lands in Runs | |

**User's choice:** Global, always-present.

### Q2 — Default safety mode

| Option | Description | Selected |
|--------|-------------|----------|
| Read only | Analyze/plan, no edit until elevated; safest default | ✓ |
| Can edit | Edits within scope by default; faster but riskier | |
| Remember per workspace | Last chosen; first run defaults Read only | |

**User's choice:** Read only.

### Q3 — Advanced controls visibility

| Option | Description | Selected |
|--------|-------------|----------|
| All hidden behind 'Advanced' | Shows only ask + safety mode; everything else collapsed | ✓ |
| Safety + budget visible, rest advanced | Surface two highest-stakes knobs | |
| Show all inline | Power-dense; contradicts no-clutter goal | |

**User's choice:** All hidden behind Advanced.

---

## Swarm Map Layout + Scope

### Q1 — Default layout shape

| Option | Description | Selected |
|--------|-------------|----------|
| Layered lanes (objective → agents → work → artifacts) | Directed lanes by node type; most readable, easiest honest-signal | |
| Radial (objective center, agents orbit) | Center = objective; agents orbit; matches ROADMAP 'center node' phrasing | ✓ |
| Force-directed cloud | Physics graph; organic but drifts, noisy for replay | |

**User's choice:** Radial.

### Q2 — Default map scope

| Option | Description | Selected |
|--------|-------------|----------|
| Single focused run | One run/objective at a time; clearest for review/replay | |
| All active runs at once | One map of every live run; true mission control, denser | ✓ |
| Toggle (run default, all-runs zoom-out) | Single-run default + zoom-out; more to build | |

**User's choice:** All active runs at once.
**Notes:** Claude flagged the multi-center tension and reconciled: model = one radial cluster per run/objective, packed across canvas, click-to-focus a cluster (D-07). Keeps it honest/legible at scale.

---

## Product Vocabulary / Naming

### Q1 — Top-level noun for a unit of managed agent work

| Option | Description | Selected |
|--------|-------------|----------|
| Run | Matches RunData/currentRunId code + Codex/Devin convention; least churn | |
| Task | Linear-like, friendlier; collides with board task nodes | ✓ |
| Run as label, Task as board node | Run = whole effort, task/card = board items | |

**User's choice:** Task.
**Notes:** Choice collides with board task nodes + `RunData`/`runId` code. Claude reconciled (D-09): user-facing unit = "Task"; board items shown as "steps"/"cards"; code identifiers stay `runId`/`RunData` (display layer only). "Runs" portal item → labeled "Tasks."

### Q2 — Observability surface name

| Option | Description | Selected |
|--------|-------------|----------|
| Swarm Map | Distinctive, on-brand, matches ROADMAP + swarm/ code | ✓ |
| Run Graph | Plainer but generic | |
| Swarm Map (primary) + 'graph view' in copy | Brand name in nav, descriptive in tooltips | |

**User's choice:** Swarm Map.

### Q3 — Safety-mode labels

| Option | Description | Selected |
|--------|-------------|----------|
| Read only / Can edit / Autopilot | ROADMAP proposed set; plain, escalating | ✓ |
| Read only / Can edit / Full auto | 'Full auto' over 'Autopilot' | |
| Plan / Edit / Auto (keep current) | Today's labels; raw/internal-feeling | |

**User's choice:** Read only / Can edit / Autopilot.

---

## Claude's Discretion

- **D-02** — Launch view (terminal grid for fresh/project-less; last-used restore for workspaces with active runs). User asked "what do you think?".
- **D-09** — Task/step naming reconciliation (user-facing "Task" + board "steps/cards" + unchanged `runId` code). Claude-proposed to resolve the collision from the Task choice.

## Deferred Ideas

None deferred to other phases — discussion stayed within V24 scope. Four in-phase
detail areas (replay/timeline interaction, Voss-vs-non-Voss pane distinction,
mission-control IA granularity, Swarm Map alert/attention handling) were offered
but left to SPEC/research rather than decided here.
