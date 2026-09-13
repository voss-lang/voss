# Phase V11: ADE Org Integration — Specification

**Created:** 2026-06-06
**Ambiguity score:** 0.141 (gate: ≤ 0.20)
**Requirements:** 8 locked

## Goal

Turn the desktop app into a visual Agentic Development Environment for the org loop: a dedicated Org/Run view that hosts the ten org panels (roster, board, session-tree, audit, reviewer-verdict, budget, scope, diff drilldown, blocked-card decision, replay), each rendering from the V4–V9 CLI JSON via thin Tauri wrappers — read/replay first, with decision actions shelling the V7/V9 CLI so there is one decision path.

## Background

The A-track shell is shipped (`apps/voss-app/`: panes, grid engine, sidebar, command palette, ContextPanel, StatusBar, workspaces, themes/variant-b, A13 swarm view; A12 UI-SPEC sets the ADE visual direction). There are **no org panels** yet — nothing renders the board, roster, audit, reviewers, or session tree.

V11 is the render sink for everything V4–V9 persist and export: `voss board` (V5), `voss review` (V6), `voss audit --json` + session-tree export (V9/V4), `run-final.json` (V7). The harness CLIs already (per their SPECs) emit JSON; V11 consumes it.

**Locked direction (interview):** panels consume the V5/V6/V9 CLI JSON through thin Tauri command wrappers (no raw-file parsing in the app); all 10 panels; read/replay first with blocked-decision + sign-off actions shelling the V7/V9 CLI (one write path); a dedicated Org/Run view mode (toggle from the terminal-grid view); static snapshot + manual refresh (live streaming deferred); visual contract deferred to `/gsd-ui-phase` (V11-UI-SPEC). Depends on V5/V6/V7/V9/V4 JSON exports.

## Requirements

1. **CLI-JSON data layer** (VADE-DATA): the app reads run data through typed Tauri commands.
   - Current: no harness-run data access in the app.
   - Target: thin Tauri command wrappers invoke `voss board`/`voss review`/`voss audit --json`/session-tree export and return typed run data to the Solid app; no raw `.voss/sessions` parsing logic in the frontend.
   - Acceptance: a Tauri command returns typed data from each source for a persisted run; an invalid/missing run yields an empty/error state (no crash).

2. **Org/Run view mode** (VADE-VIEW): a dedicated view hosts the panels.
   - Current: the app has the terminal-grid view + swarm view; no org view.
   - Target: a toggleable Org/Run view (separate from the terminal-grid view) hosts the org panels in a layout, reusing existing tokens/sidebar; data is a static snapshot with a manual refresh control; switching views does not disturb the terminal grid.
   - Acceptance: toggling to Org/Run shows the panels and back restores the grid unchanged; a refresh control re-reads the data.

3. **Structural state panels** (VADE-01/02/03/05): roster, board, session-tree, reviewer-verdict.
   - Current: none.
   - Target: roster panel (team roles); board panel (6 columns + cards with role/risk/status/budget); session-tree panel (navigable parent→child tree); reviewer-verdict panel (Reviewer-A and Reviewer-B shown separately).
   - Acceptance: each panel renders correct data for a persisted run; the board shows the 6 columns; the session tree is navigable; A and B verdicts are visually separated.

4. **Audit panel** (VADE-04): the audit is rendered.
   - Current: none.
   - Target: a panel renders the V9 audit JSON — the §9 sections, claims-vs-evidence (with unsupported flags), and the residual-risk section.
   - Acceptance: the audit panel renders the audit sections from `voss audit --json`; unsupported EM claims are visibly flagged; the residual-risk section is shown.

5. **Budget + scope visualization** (VADE-06/07): budget and scope are visual.
   - Current: none (StatusBar has a basic budget stub from F3).
   - Target: budget visualization per root/card/agent; scope visualization per role/card.
   - Acceptance: budget viz shows per-root, per-card, and per-agent allocation/consumption; scope viz shows per-role and per-card scope.

6. **Diff + verification drilldown** (VADE-08): inspect a card's change + verification.
   - Current: none.
   - Target: from a card or review, a drilldown shows the diff + the verification result (tests/eval) tied to it.
   - Acceptance: opening a card's drilldown shows its diff and the associated verification outcome.

7. **Blocked-card decision flow** (VADE-09): blocked cards are actionable via the CLI.
   - Current: none.
   - Target: a panel lists blocked cards with reasons; the **approve** (and sign-off) action invokes the real V9 CLI (`voss audit <run_id> --cwd <path> --approve`) — the ADE displays state and shells the decision; it never writes run decisions directly. **Reject/unblock and per-card decisions are rendered disabled-with-explanation** because no non-interactive V7/V9 CLI command exists for them yet (verified in `voss/harness/cli.py`: sign-off via `voss team run` is interactive-only; there is no standalone `voss reject/unblock <card>`). Enabling them is a future harness phase, out of V11's consumer scope.
   - Acceptance: blocked cards + reasons render; triggering the **approve** action invokes `voss audit <run_id> --approve` (observable CLI call), not a direct app write; reject/unblock affordances are present but disabled with an explanation until a non-interactive CLI command exists.

8. **Run replay** (VADE-10): a run can be replayed.
   - Current: none.
   - Target: a replay mode steps through a run's persisted transition history (`transitions[]` + `run-final.json`) as a static reconstruction.
   - Acceptance: replay steps forward/back through the persisted transitions of a run and reflects board/card state at each step.

## Boundaries

**In scope:**
- Tauri CLI-JSON data layer.
- Org/Run view mode (static snapshot + manual refresh).
- All 10 panels (roster/board/session-tree/audit/reviewer/budget/scope/diff/blocked-decision/replay).
- Decision actions that shell the V7/V9 CLI.

**Out of scope:**
- Live streaming during an active run — static + manual refresh only (follow-on).
- The ADE writing run decisions directly — the CLI is the single write path.
- Any new harness data/persistence or change to the V4–V9 CLI JSON contracts — V11 is a consumer.
- The **visual design contract** — produced by `/gsd-ui-phase` (V11-UI-SPEC) after this SPEC.
- New harness behavior / org-loop logic.

## Constraints

- Panels consume the V5/V6/V9 CLI JSON via thin Tauri wrappers; no duplicated raw-file parsing in the frontend; no direct harness-data writes.
- **One decision path:** blocked-card/sign-off actions shell the V7/V9 CLI; the ADE never writes run decisions directly.
- Static snapshot + manual refresh; live streaming out of scope.
- Reuse A-track tokens/components (variant-b, sidebar, ContextPanel patterns) and the A12 ADE visual direction.
- Depends on V4/V5/V6/V7/V9 exposing JSON exports; V11 does not modify those contracts.
- No regression to the terminal-grid view; existing voss-app tests stay green.

## Acceptance Criteria

- [ ] A Tauri command layer returns typed run data from `voss board`/`voss review`/`voss audit --json`/session-tree export; invalid/missing run → empty/error state, no crash.
- [ ] An Org/Run view toggles from the terminal-grid view and back without disturbing the grid; a manual refresh re-reads data.
- [ ] Roster, board (6 columns + cards), session-tree (navigable), and reviewer-verdict (A+B separate) panels render correct data for a persisted run.
- [ ] The audit panel renders the V9 audit JSON sections; unsupported EM claims are flagged; residual-risk is shown.
- [ ] Budget viz shows per root/card/agent; scope viz shows per role/card.
- [ ] A diff + verification drilldown opens from a card/review showing the diff + test/eval result.
- [ ] The blocked-card panel lists blocked cards + reasons; the approve action invokes `voss audit <run_id> --approve` (observable CLI call), not a direct app write; reject/unblock are rendered disabled-with-explanation (no non-interactive CLI command exists yet).
- [ ] Run replay steps through a run's persisted transitions and reflects board/card state at each step.
- [ ] `npm run build` + existing voss-app tests (vitest) + `tsc --noEmit` are green; the terminal-grid view does not regress.

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                             |
|--------------------|-------|------|--------|-------------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | 10 panels + data layer + view mode pinned                         |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | Live streaming out, CLI single write path, UI-SPEC separate       |
| Constraint Clarity | 0.80  | 0.65 | ✓      | CLI-JSON consumer, one decision path, A-track reuse               |
| Acceptance Criteria| 0.82  | 0.70 | ✓      | 9 pass/fail criteria                                             |
| **Ambiguity**      | 0.141 | ≤0.20| ✓      |                                                                   |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective       | Question summary                                  | Decision locked                                                        |
|-------|-------------------|--------------------------------------------------|-----------------------------------------------------------------------|
| 0     | Researcher (scout)| What ADE org panels exist?                       | None; A-track shell shipped; V11 = render sink for V4–V9 data          |
| 1     | Researcher        | How do panels get run data?                       | Consume V5/V6/V9 CLI JSON via thin Tauri wrappers                      |
| 1     | Simplifier        | How many of the 10 panels?                        | All 10                                                                 |
| 1     | Boundary Keeper   | Read vs write for decisions?                       | Read/replay first; decision actions shell the V7/V9 CLI               |
| 2     | Researcher        | Visual-contract path?                              | Run /gsd-ui-phase (V11-UI-SPEC) after this SPEC                        |
| 2     | Boundary Keeper   | Panel hosting/layout?                              | Dedicated Org/Run view mode                                            |
| 2     | Failure Analyst   | Refresh model?                                     | Static snapshot + manual refresh; live streaming deferred             |

---

*Phase: V11-ade-org-integration*
*Spec created: 2026-06-06*
*Next step: /gsd-ui-phase V11 (visual contract) → /gsd-discuss-phase V11 (implementation decisions)*
