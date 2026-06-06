# Phase V7: Engineering Manager Loop (supersedes O5) - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning
**Source:** Direct synthesis from V7-SPEC.md (ambiguity 0.137; discuss-phase skipped — SPEC interview already locked direction)

<domain>
## Phase Boundary

Make the org loop runnable end-to-end. O5 already shipped the full EM loop + cage (`voss/harness/em/`, plans O5-00..05 with SUMMARYs): `em_loop()` (idea→plan→dispatch→`Board.tick()`→repeat→`RunFinal`), `EMBoardHandle` cage facade (deliberately omits `set_ceiling`/`set_p`/`set_budget`/`extend_budget`; rejects dispatch to a role not in `roster_ids`), `llm.py`, `tickets.py`, `stub.py`. **EM-01..10 are shipped.**

V7 builds the three gaps that turn the shipped pieces into a usable product, and verifies the rest:
- **VEM-CLI** — `voss team run "<goal>"` (compose V3 team + V4 session tree + V5 board + V6 reviewers + `em_loop`) + default-roster fallback.
- **VEM-PERSIST** — persist `RunFinal` to a session-root sidecar (`run-final.json`).
- **VEM-SIGNOFF** — print the RunFinal summary + prompt approve/reject, recorded into the sidecar (record-only, no revert).

V7 sits on V3 (team), V4 (session tree), V5 (board), V6 (reviewers). It is **composition + CLI + persistence + sign-off** — no EM-loop or cage reimplementation, no new orchestration logic. The sign-off *forcing function* and the full audit product are **V9**.

</domain>

<decisions>
## Implementation Decisions

### Scope: delta-only on shipped O5
- Build only the 3 gaps (CLI compose, RunFinal persistence, sign-off); verify/regress EM-01..10 + cage.
- O5 marked superseded (bookkeeping); O5 artifacts retained as reference.

### `voss team run "goal"` CLI (VEM-CLI)
- Add a **`run` subcommand to the EXISTING `team` click group** (`voss/harness/cli.py:3777`, alongside `team check`) — do not create a new top-level group.
- Composition (reuse, no reimplementation): load team via V3 `compile_team` (`.voss/team.voss` if present) → build `SessionTreeManager` → `Board.from_team_config(..., reviewer_a=..., reviewer_b=...)` → run the shipped async `em_loop` autonomously until all cards terminal.
- **V6 dependency reality (VERIFIED ON DISK 2026-06-06 — supersedes the stale V7-RESEARCH "V6 unexecuted" claim):** V6 is **COMPLETE** (commits + `d35c7ae` merge to dev; board+em suites 100% green). `Board.from_team_config` accepts `reviewer_a`/`reviewer_b` (machine.py:281-283) with a legacy `reviewer=` alias that fans out to both (machine.py:260-262 — so a single-reviewer call won't `TypeError`); `ReviewerVerdict.domain_inferred` exists (verdict.py:34); `voss review` ships (cli.py:2487). V7 composes against the **real V6 A/B surface — inject `reviewer_a` + `reviewer_b`** (the SPEC's "compose V6 Reviewer-A/B"). For the stub-provider smoke run, use the shipped board reviewer stubs (`DeterministicReviewerStub` for each slot, or `ReviewerA`/`ReviewerB`) so the V6 two-source Done gate (`a_verification_passes` + `b_passes`) is satisfied.
- `em_loop` is **async** → the command drives it via the harness's existing async-run pattern.
- Acceptance: `voss team run "<goal>"` runs a full idea→cards→review→terminal run on the **stub provider**, produces ≥1 card + a `RunFinal`, exits 0.

### Default-roster fallback (VEM-CLI)
- If `.voss/team.voss` is **absent**, use the V3 `DEFAULT_ROSTER` (the built-in 7-role roster, `team.py:48`) + a default ceiling.
- An explicit `.voss/team.voss` **overrides** the default.
- Acceptance: no team file → default roster completes the run; team file present → that roster/ceiling is used.

### RunFinal persistence (VEM-PERSIST)
- On completion, persist `RunFinal` to **`.voss/sessions/<root_id>/run-final.json`** — a read-only sidecar consumed by `voss audit` (V9).
- **Shipped `RunFinal` fields (verified by research — `em/tickets.py:112`):** `root_id`, `idea`, `total_cards`, `done_count`, `blocked_count`, `killed_count`, `rescope_count`, `em_iterations`, `ts`, `kind`. (The earlier draft's `evidence_refs`/`diff_summary`/`residual` are NOT on RunFinal — those live on `Ticket`; do not invent them on the sidecar.)
- Serialize via `dataclasses.asdict(rf)` (RunFinal is frozen+slots); write the 10 fields **plus a superset `sign_off` key** for the decision — do NOT mutate the frozen dataclass.
- Acceptance: after a run, `run-final.json` exists under the root, contains the RunFinal fields + `sign_off`, and is re-readable without re-running.

### Human sign-off (VEM-SIGNOFF)
- After the autonomous run completes, the CLI **prints the RunFinal summary** and **prompts approve/reject**.
- The decision is **recorded into the persisted `run-final.json`**.
- **Reject records the decision but does NOT revert** edits (already on disk, within scope). No rollback path.
- The sign-off *forcing function* (mandatory killed-card/misroute diff before approve unlocks) is **V9** — V7 is a plain print + prompt + record.
- Acceptance: CLI prints summary + prompts approve/reject; chosen decision recorded; reject leaves the working tree unchanged.

### EM loop + cage verification (verify)
- After wiring, verify: idea→tickets/cards; role assigned from roster only; `routing_rationale` per assignment; kill/rescope lineage persisted; EM **cannot** mutate ceiling/p/roster or construct gates outside team config (the `EMBoardHandle` omissions hold); `RunFinal` carries evidence + residual risk.
- Acceptance: dispatch to an undeclared role denied; no `set_ceiling`/`set_p`/`extend_budget` path on the handle; kill/rescope lineage + routing_rationale recorded; existing O5 em tests pass.

### Bookkeeping: O5 supersession
- ROADMAP/STATE mark O5 superseded by V7.
- `git diff` shows **zero field changes** on `RunRecord`/`SessionRecord`/`BudgetScope`.

### Claude's Discretion
- RunFinal summary print format (table vs structured text) and the approve/reject prompt mechanism (click `confirm`/`prompt`).
- The serialization shape of `run-final.json` (field layout) — must round-trip the RunFinal fields + sign-off; consumed by V9 (keep it a flat, stable JSON object).
- How the default ceiling value is chosen (reuse V3's default-roster ceiling injection).
- Exact async-drive call site for `em_loop` within the CLI command.
- Test organization within `tests/harness/` conventions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Shipped EM package (the delta target — reuse, do not reimplement)
- `voss/harness/em/loop.py` — `em_loop()` (async; idea→plan→dispatch→`Board.tick()`→`RunFinal`; patches `em_iterations`).
- `voss/harness/em/handle.py` — `EMBoardHandle` cage facade (omits `set_ceiling`/`set_p`/`set_budget`/`extend_budget`; rejects undeclared-role dispatch; `_NodeAudit` lineage).
- `voss/harness/em/tickets.py` — `Ticket`/`KillRecord`/`RescopeRecord`/`RoutingRationale`/`RunFinal` (frozen; `evidence_refs`/`diff_summary`/`residual`/`em_iterations`).
- `voss/harness/em/llm.py` (EM prompt + immutable cage rules), `stub.py` (`DeterministicEMStub`), `protocols.py`, `schema.py`, `errors.py`, `__init__.py`.

### Composition dependencies (reuse)
- `voss/harness/team.py` — `compile_team` (`:588`), `DEFAULT_ROSTER` (`:48`, the 7-role roster), `TeamConfig`/`SubagentRegistry`, `roster_ids` (`:309`), default-roster ceiling injection (`:448`, `:634`).
- `voss/harness/session_tree.py` — V4 `SessionTreeManager` (pre-emptive budget guard) + persisted node JSON at `.voss/sessions/<root_id>/`.
- `voss/harness/board/machine.py` — V5 `Board` (the run's board).
- `voss/harness/board/reviewer_a.py`, `reviewer_b.py`, `verdict.py` — V6 Reviewer-A/B interface (V6 builds intelligence; V7 injects them).

### CLI surface (where `voss team run` lands)
- `voss/harness/cli.py:3777` — existing `@click.group("team")` + `team check` subcommand (the analog; add `run` here).

### Frozen schemas (do NOT modify any field)
- `RunRecord`, `SessionRecord`, `voss_runtime.BudgetScope` — frozen; `git diff` must show zero field changes.

### Prior-phase + spec reference
- `.planning/phases/O5-engineering-manager-loop/` — O5 SPEC/RESEARCH/PATTERNS/CONTEXT + O5-00..05 SUMMARYs (design rationale; retained as reference).
- `.planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-SPEC.md` — locked requirements + 7 acceptance criteria.
- `.planning/phases/V3-.../`, `V4-.../V4-CONTEXT.md`, `V5-.../V5-CONTEXT.md` — upstream dependency decisions.
- `docs/ORCHESTRATION_LAYERS.md` — PRD EM-01..10 + §5.1 entrypoint source.

</canonical_refs>

<specifics>
## Specific Ideas

- `voss team run "<goal>"`: resolve team (file or `DEFAULT_ROSTER`) → `compile_team` → instantiate `SessionTreeManager` + `Board.from_team_config(..., reviewer_a=..., reviewer_b=...)` (real V6 A/B slots; stub each for the smoke run) → **pre-spawn ≥1 board card** (`await board.spawn_card(risk_tier="med")`, since `em_loop` creates Tickets, not board cards) → `asyncio.run(em_loop(idea=goal, em_handle=..., em_agent=stub, ...))` → `RunFinal` → write `.voss/sessions/<root_id>/run-final.json` → print summary → prompt approve/reject → record decision into the sidecar.
- `run-final.json` is the V9 audit input — keep it a stable, flat JSON object (`dataclasses.asdict(RunFinal)` 10 fields + `sign_off` decision).
- **Acceptance gate = `tests/harness/em/`** (V7's domain — EM cage + loop). V6 shipped so `tests/harness/board/` is ALSO green now; the new V7 CLI tests live in `tests/harness/test_team_run_cli.py`. (Earlier draft's "board/ has 13 RED, exclude it" rationale was from the stale pre-merge research — board/ is green; em/ scoping stands because the EM cage is what V7 verifies, not because board/ is broken.)
- Reject is record-only: write `decision: "reject"` into the sidecar; touch nothing else on disk.
- Cage stays intact: V7 only *injects* the handle; it adds no mutation methods. The "EM cannot mutate ceiling/p/roster" guarantee is the O5 `EMBoardHandle` omission, re-verified.
- Tests: pytest, class-based, `tests/harness/` conventions; stub provider + `DeterministicEMStub` for the end-to-end run; click `CliRunner` for the CLI + sign-off prompt. **No new third-party deps.**

</specifics>

<deferred>
## Deferred Ideas

- Sign-off **forcing function** (mandatory killed-card/misroute diff before approve unlocks) → **V9**.
- Full audit product, calibration telemetry, slop-rejection spot-audit → **V9**.
- Reject-revert / rollback of run edits → out of scope (record only).
- ADE goal-input / live-run UI → **V11**.
- In-flight interactive checkpoints (V7 is autonomous-to-terminal then sign-off).
- Any field change to `RunRecord`/`SessionRecord`/`BudgetScope` — frozen.

</deferred>

---

*Phase: V7-engineering-manager-loop-supersedes-o5*
*Context synthesized: 2026-06-06 direct from V7-SPEC.md (discuss-phase skipped per locked SPEC interview)*
