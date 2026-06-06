# Phase V7: Engineering Manager Loop (supersedes O5) — Specification

**Created:** 2026-06-06
**Ambiguity score:** 0.137 (gate: ≤ 0.20)
**Requirements:** 5 locked (delta on shipped O5)

## Goal

Make the org loop runnable end-to-end: ship `voss team run "goal"` that composes the V3 team + V4 session tree + V5 board + V6 reviewers + the shipped em_loop, runs autonomously to terminal, persists the RunFinal, and presents a human sign-off — without touching the frozen record schemas. This is the phase that turns the shipped O-track pieces into a usable product.

## Background

O5 shipped a complete EM loop (`voss/harness/em/`, plans O5-00..05 with SUMMARYs):
- `loop.py` `em_loop()` — idea → plan → dispatch → `Board.tick()` → repeat until all cards terminal → returns `RunFinal`.
- `handle.py` `EMBoardHandle` — the cage facade: `create_ticket`/`set_ac`/`dispatch_card`/routing-rationale/kill/rescope + `_NodeAudit` lineage; **deliberately omits** `set_ceiling`/`set_p`/`set_budget`/`extend_budget` and rejects dispatch to a role not in `roster_ids`.
- `llm.py` (EM prompt + immutable cage rules), `tickets.py` (`Ticket`/`KillRecord`/`RescopeRecord`/`RoutingRationale`/`RunFinal` with evidence_refs/diff_summary/residual), `stub.py` (`DeterministicEMStub`).

So **EM-01..10 are shipped.** Gaps vs the runnable product:
- **No `voss team run` CLI** — the PRD §5.1 entrypoint that composes team+board+reviewers+loop doesn't exist.
- **RunFinal not persisted** — `em_loop` returns it in-process; `voss audit` (V9) needs it on disk.
- **No human sign-off surface** — the loop is "autonomous to Done, human sign-off only", but the present-and-sign-off step lives at the (absent) CLI layer.

V7 supersedes O5 (ROADMAP); O5 artifacts retained as reference. V7 sits on V3 (team), V4 (session tree), V5 (board), V6 (reviewers). **Locked direction (interview):** delta on shipped O5; `voss team run` composes the V3–V6 stack with a default-roster fallback; autonomous to terminal then end sign-off (forcing function → V9); RunFinal persisted to a session-root sidecar; reject records only (no revert).

## Requirements

1. **`voss team run "goal"` CLI** (VEM-CLI): a single command runs the org loop end-to-end.
   - Current: no `team run` command; `em_loop` is only reachable in code.
   - Target: `voss team run "<goal>"` loads the team (`.voss/team.voss` if present), builds `SessionTreeManager` (V4) + `Board` (V5) + Reviewer-A/B (V6), runs `em_loop` autonomously until all cards are terminal.
   - Acceptance: `voss team run "<goal>"` executes a full idea→cards→review→terminal run on the stub provider and exits 0; the run produces ≥1 card and a `RunFinal`.

2. **Default-roster fallback** (VEM-CLI): the command works out-of-box.
   - Current: team config must be authored.
   - Target: if `.voss/team.voss` is absent, `voss team run` uses the V3 default 7-role roster + a default ceiling; an explicit team file overrides.
   - Acceptance: with no team file, the run uses the default roster and completes; with a team file, that roster/ceiling is used.

3. **RunFinal persistence** (VEM-PERSIST): the final summary is durable.
   - Current: `RunFinal` is returned, not written.
   - Target: on completion, persist `RunFinal` to `.voss/sessions/<root_id>/run-final.json` (evidence_refs, diff_summary, residual, em_iterations, sign-off decision).
   - Acceptance: after a run, `run-final.json` exists under the root and contains the RunFinal fields; it is re-readable without re-running.

4. **Human sign-off** (VEM-SIGNOFF): the run ends at a human decision.
   - Current: no sign-off surface.
   - Target: after the autonomous run, the CLI prints the RunFinal summary and prompts the human to approve/reject; the decision is recorded into the persisted RunFinal. Reject records the decision but does **not** revert edits (already on disk within scope). The sign-off *forcing function* (mandatory killed-card/misroute diff before approve) is V9.
   - Acceptance: the CLI prints the RunFinal summary and prompts approve/reject; the chosen decision is recorded in `run-final.json`; reject leaves the working tree unchanged.

5. **EM loop + cage verification** (verify): EM-01..10 regress green; O5 superseded.
   - Current: em_loop + cage shipped + tested.
   - Target: verify after wiring — idea→tickets/cards; role assigned from roster only; routing_rationale per assignment; kill/rescope lineage persisted; EM cannot mutate ceiling/p/roster or construct gates outside team config; RunFinal carries evidence + residual risk. Mark O5 superseded.
   - Acceptance: dispatch to an undeclared role is denied; no ceiling/p/budget-extend path exists on the handle; kill/rescope lineage + routing rationale are recorded; existing O5 tests pass.

## Boundaries

**In scope:**
- `voss team run "goal"` CLI composing V3 team + V4 session tree + V5 board + V6 reviewers + em_loop.
- Default-roster fallback when no team file.
- RunFinal persistence to a session-root sidecar.
- Basic human sign-off (print summary + approve/reject, recorded).
- Verification/regression of the EM loop + cage; mark O5 superseded.

**Out of scope:**
- Sign-off **forcing function** (mandatory killed-card/misroute diff before approve unlocks) — V9.
- Full audit product, calibration telemetry, slop-rejection spot-audit — V9.
- Reject-revert / rollback of run edits — out of scope (record only).
- ADE goal-input / live-run UI — V11.
- In-flight interactive checkpoints (V7 is autonomous-to-terminal then sign-off).
- Any field change to `RunRecord`/`SessionRecord`/`voss_runtime.BudgetScope` — frozen.
- New third-party dependencies.

## Constraints

- Composition **reuses** V3 `compile_team` (+ default-roster fallback), V4 `SessionTreeManager` (with its pre-emptive budget guard), V5 `Board`, V6 Reviewer-A/B — no reimplementation.
- EM cage intact: the run cannot mutate ceiling/p/roster (EMBoardHandle omissions); reviewers stay independent.
- Autonomous to all-cards-terminal; human sign-off only at the end; reject records, never reverts.
- `run-final.json` is a read-only sidecar consumed by `voss audit` (V9).
- No change to frozen `RunRecord`/`SessionRecord`/`BudgetScope`; no new deps.

## Acceptance Criteria

- [ ] `voss team run "<goal>"` composes team+session-tree+board+Reviewer-A/B+em_loop and runs autonomously to all-cards-terminal; produces ≥1 card + a RunFinal; exits 0 on stub provider.
- [ ] No `.voss/team.voss` → default 7-role roster + default ceiling used; an explicit team file overrides.
- [ ] On completion `RunFinal` persists to `.voss/sessions/<root_id>/run-final.json` (evidence_refs/diff_summary/residual/em_iterations) and is re-readable.
- [ ] The CLI prints the RunFinal summary + prompts approve/reject; the decision is recorded into `run-final.json`; reject leaves the working tree unchanged.
- [ ] EM cage regress: dispatch to an undeclared role is denied; no set_ceiling/set_p/extend_budget on the handle; kill/rescope lineage + routing_rationale recorded.
- [ ] Existing O5 em tests pass; idea→≥1 card→review→terminal→RunFinal proven on stub provider.
- [ ] `git diff` shows zero field changes on `RunRecord`/`SessionRecord`/`BudgetScope`.

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                            |
|--------------------|-------|------|--------|------------------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | Delta = team run CLI + persistence + sign-off; loop shipped       |
| Boundary Clarity   | 0.88  | 0.70 | ✓      | Forcing-function→V9, revert out, ADE→V11, checkpoints out         |
| Constraint Clarity | 0.80  | 0.65 | ✓      | Reuse V3–V6, cage intact, autonomous + record-only sign-off       |
| Acceptance Criteria| 0.84  | 0.70 | ✓      | 7 pass/fail criteria, delta-focused                              |
| **Ambiguity**      | 0.137 | ≤0.20| ✓      |                                                                  |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective       | Question summary                                  | Decision locked                                                       |
|-------|-------------------|--------------------------------------------------|----------------------------------------------------------------------|
| 0     | Researcher (scout)| What of EM-01..10 already exists?               | O5 shipped the full em_loop + cage; gaps = CLI + persistence + sign-off |
| 1     | Researcher        | V7 scope given O5 shipped?                        | Delta + voss team run composing V3–V6; O5 superseded                  |
| 1     | Researcher        | Human control model?                             | Autonomous to terminal + end sign-off; forcing function → V9         |
| 1     | Researcher        | RunFinal persistence location?                   | Sidecar `.voss/sessions/<root>/run-final.json`                       |
| 2     | Boundary Keeper   | No team file behavior?                            | Default 7-role roster + default ceiling fallback                     |
| 2     | Failure Analyst   | Reject semantics?                                | Record only, no revert (edits already on disk)                      |

---

*Phase: V7-engineering-manager-loop-supersedes-o5*
*Spec created: 2026-06-06*
*Next step: /gsd-discuss-phase V7 — implementation decisions (run output format, composition wiring, sign-off prompt)*
