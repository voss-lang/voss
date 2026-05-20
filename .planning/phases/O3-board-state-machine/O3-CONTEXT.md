# Phase O3: Board State Machine + Gated Transitions — Context

**Gathered:** 2026-05-19
**Status:** Ready for planning (SPEC.md locked, 9 requirements)
**Source of truth:** `.planning/phases/O3-board-state-machine/O3-SPEC.md` (WHAT) + this file (HOW)

<spec_lock>
## Locked by SPEC.md — MUST read before planning

`.planning/phases/O3-board-state-machine/O3-SPEC.md` — 9 requirements, 14 falsifiable acceptance checkboxes, explicit out-of-scope list. Downstream agents read SPEC.md directly; CONTEXT.md does NOT duplicate requirements text.

Key WHAT decisions already locked (do not re-ask):
- Card == O1 session-tree node (no parallel store)
- One board per compiled `team{}` block, one root tree node per board
- 6 columns: `Backlog → Planned → InProgress → InReview → Blocked → Done`
- Per-column WIP enforcement (default `InProgress:3, InReview:2`)
- Artifact-only confidence gating
- 3-bucket risk tier `p` {low 0.60 / med 0.80 / high 0.95}
- `ReviewerVerdict` frozen dataclass + `Reviewer` Protocol — O4 plug-in contract
- Critic loop bounded by retry-ceiling AND budget, first-hit
- Budget-fraction primary + wall-clock safety net timeout
</spec_lock>

<domain>
## Phase Boundary

O3 is the first phase that **runs** the cage. O1 ships the budget-fanned session tree; O2 compiles `team{}` to a registry + opaque `BoardSpec`; O3 turns that opaque spec into an executing state machine whose transitions are gated, whose cards are session-tree nodes, and whose terminal verdicts (`Done` / `Blocked`) honor the cage invariants.

See SPEC.md "Boundaries" — In-scope / Out-of-scope lists are the canonical perimeter.
</domain>

<decisions>
## Implementation Decisions (HOW)

### Module Layout
- `voss/harness/board/` **package**, not a single module. Files:
  - `__init__.py` — public API: `Board`, `Card`, `Column`, `BoardWIPError`, `BoardGateError`, `BoardTimeoutError`.
  - `verdict.py` — `ReviewerVerdict` (frozen dataclass) + `Reviewer` (`Protocol`). **Constraint (SPEC):** imports ONLY from `typing` and `dataclasses`. Zero transitive harness deps — this is the file O4 imports.
  - `machine.py` — `Board`, `Card` (value-object holding `node_id`, `column`, `risk_tier`, `retry_count`, `deadline`), `Board.from_team_config`, `Board.move`, `Board.dry_run_gate`, `Board.start`/`stop`.
  - `gates.py` — gate-predicate registry + the predicates (`scope_ok`, `budget_ok`, `conf_meets_p`, `tests_pass`, `eval_meets_threshold`, `scope_clean`, `retry_under_ceiling`, `not_timed_out`). Each predicate has a stable `.name` referenced by SPEC's acceptance criterion #5.
  - `tick.py` — clock abstraction (`Clock` Protocol over `time.monotonic`), `_tick_loop` coroutine, `Board._tick_once()` test hook.
  - `errors.py` — typed exceptions with `.reason` field.
  - `stub.py` — `DeterministicReviewerStub` for O3 tests; production callers must not import.

### Gate-Predicate Registry
- **Shape:** frozen `dict[tuple[Column, Column], tuple[Predicate, ...]]` built once at `Board.from_team_config()` time from the compiled team config + a fixed default table.
- `Predicate` is a `Protocol` with `name: str` and `evaluate(ctx: GateContext) -> bool`. `GateContext` holds `card`, `verdict` (optional), `budget_state`, `now`.
- `dry_run_gate(card, transition)` walks the predicate tuple in order, collects each `predicate.name` whose `evaluate(...)` returned False, returns `(passed, failing_clauses)`.
- Predicate ordering is part of the contract: budget/scope predicates first (cheap), confidence/eval predicates last (expensive). Tests pin the order.
- Custom per-team predicates: `team_config.board.extra_gates` (deferred plumbing — O5 owns runtime injection; O3 reads the dict if present but does not require it).

### `Board.tick()` Driver
- **Driver:** `Board.start()` spawns `asyncio.create_task(_tick_loop())`; `Board.stop()` cancels it and awaits drain.
- `_tick_loop()`:
  ```
  while not cancelled:
      _tick_once(now=clock.now())
      await asyncio.sleep(interval_s)  # default 1.0
  ```
- `_tick_once(now)` is the test entry point — synchronous, idempotent. Tests pass a frozen `Clock` fake and step it manually.
- The async driver is the ONLY non-test path. No `threading.Timer`, no lazy-on-transition.
- `interval_s` is injectable; default 1.0. Production tunes via `team_config.board.tick_interval_s`.

### `RunRecord` Transition-Delta Payload
- Every transition (passed, refused, or forced) emits exactly one `RunRecord` delta on the card's node. Fields:
  ```
  {
    "kind": "board.transition",
    "from": <column>,
    "to":   <column>,
    "outcome": "passed" | "refused" | "forced",
    "failing_clauses": [<predicate.name>, ...] | null,   # only when outcome=refused
    "reason": "timeout" | "budget" | "retry_ceiling" | null,  # only when outcome=forced
    "verdict_snapshot": <ReviewerVerdict-as-dict> | null,  # present iff a verdict was consulted
    "retry_count": <int>,
  }
  ```
- `failing_clauses` is null for `passed`/`forced` outcomes (no clauses failed in the dry-run sense).
- `reason` is null for `passed`/`refused`.
- `verdict_snapshot` is the frozen dataclass dumped via `dataclasses.asdict` — captured exactly once per transition.
- Schema lives in `voss/harness/board/machine.py` as a `TypedDict` (no new persisted-record schema; uses the existing `RunRecord.payload` field).
- **Audit invariant:** count of `board.transition` deltas == count of transition attempts (passed + refused + forced). O6 will assert this.

### Card↔Recorder wiring
- `Board.from_team_config(team_config, recorder, parent_node_id=None)` accepts the recorder + an optional parent node id. If parent_node_id is None, Board creates its own root node via `recorder.open_root(...)`; otherwise it opens a child node under `parent_node_id`.
- Board does NOT own the recorder lifecycle; caller (harness top-level) owns it.

### `Reviewer` injection
- `Board.from_team_config(..., reviewer: Reviewer)` accepts the reviewer as a constructor arg. Tests pass `DeterministicReviewerStub`; O4 will pass real Reviewer-A/B implementations. No global / module-level reviewer singleton.

### Claude's discretion (resolve at plan/exec)
- Whether `Card` is a `@dataclass(frozen=True)` (immutable; rebuilt on every column change) or a mutable dataclass with controlled setters. Frozen+rebuild matches the O2/O1 "frozen value-object" pattern but allocates more — defer to planner.
- Exact key names inside `team_config.board` for tick interval / wall-clock latency (`tick_interval_s` vs `tick_ms`). O2's compiled `BoardSpec` is currently opaque `raw_items` (tuple); planner decides whether to land a typed shape in O3 or keep reading from `raw_items`.
- Where the predicate-name string constants live (one module-level frozen tuple in `gates.py` vs a class attribute). Style only.
</decisions>

<canonical_refs>
## Canonical References — MANDATORY READS for downstream agents

- `.planning/phases/O3-board-state-machine/O3-SPEC.md` — **Locked requirements; MUST read before planning.**
- `.planning/ORCHESTRATION-PLAN.md` — §2 Roles, §3 Board, §4 Cage Invariants, §8 Decision log. Source of every WHAT in SPEC.md.
- `.planning/ROADMAP.md` — O3 entry (line 1456+), dependency chain `O1 → O2 → O3 → O4 → O5 → O6`.
- `.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-SPEC.md` — Budget envelope invariant, terminal-finalize, reserved drain. SPEC-1..SPEC-5.
- `.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-CONTEXT.md` — Recorder + budget integration points.
- `.planning/phases/O2-voss-team-spec-roster/O2-CONTEXT.md` — `TeamConfig`, `SubagentRegistry`, `BoardSpec` shape.
- `.planning/phases/O2-voss-team-spec-roster/O2-RESEARCH.md` — `BoardSpec.raw_items` opaque tuple representation O3 reads.
- `.planning/phases/O2-voss-team-spec-roster/O2-01-PLAN.md`, `O2-02-PLAN.md`, `O2-03-PLAN.md` — what O3 builds on (note: O2 plans not yet executed; coordinate dependency).
- `voss/harness/recorder.py` — `RunRecorder` (line 28). Board emits RunRecord deltas via this.
- `voss/harness/session.py` — `RunRecord` (line 116), `SessionRecord` (line 150). Card uses these node ids.
- `voss/harness/subagents.py` — `run_subagent` (line 90), extended `SubagentSpec` (post-O2). Board will dispatch via this when O5 wires the EM.
- `voss/harness/skill/scope.py` — `_min_mode` (line 74), `scoped_gate` (line 82). Reuse pattern for any per-card permission cap O5 needs; do NOT duplicate the auth engine.
- `voss/harness/permissions.py` — `PermissionGate` (line 146), `Mode` (line 42). Existing auth tier vocabulary.
- `voss/grammar.lark` — `BOARD_KEY` (line 218), `gate_decl` (line 219), `gate_predicate` (line 221). Already parses; O3 makes it executable.
</canonical_refs>

<code_context>
## Reusable Assets & Patterns

- **Frozen value-object pattern** (from M15 + O2): `@dataclass(frozen=True, slots=True)` for all immutable state. `Card`, `ReviewerVerdict`, `GateContext` all follow this.
- **Protocol + injectable impl** (from M15 `Reviewer`-equivalent and O2 reviewer): `Protocol` in `verdict.py` decoupled from harness, deterministic stub for tests, real impl injected by caller.
- **`_min_mode` + `scoped_gate`** (from `voss/harness/skill/scope.py`): the cap-not-expand rule. If/when O3 needs to cap per-card permissions, REUSE — do not re-implement.
- **`RunRecord.payload`** (from O1 session.py): typed `dict` field already on the record. Transition delta uses this; no new persisted-record schema (preserves O1 SPEC-5).
- **Async harness** (existing): everything inside `voss/harness/` runs under asyncio; `Board._tick_loop` integrates as `asyncio.create_task`.
- **Test clock injection pattern** (M14 watch): clock-as-Protocol with a `MonotonicClock` default impl and a `FakeClock` for tests. Reuse the same shape.
</code_context>

<deferred>
## Deferred Ideas — out of O3, captured for later phases

- Continuous-formula `p` (scope × budget × core-file-touch) — deferred to O6 calibration; O3 ships the 3-bucket tier.
- Cross-board scheduling / global WIP — out of O3 (one-board-per-team{}); reconsider when multi-team workloads land.
- Persistence across process restarts — F1 (Durable Session Persistence).
- TUI/UI surface for the board — not in any O-phase; separate concern.
- Card priority / non-FIFO queue ordering inside a column — backlog item.
- EM-injected custom gate predicates — `team_config.board.extra_gates` plumbing is O5's call; O3 reads the dict if present but doesn't define injection semantics.
</deferred>

<open_questions>
## Open Questions for Researcher / Planner

1. Whether O2's `BoardSpec.raw_items` is upgraded to a typed shape in O3 or read opaquely with a thin adapter. Research O2-RESEARCH.md §5 + O2-02-PLAN.md for the current representation before deciding.
2. `Card` frozen-rebuild vs mutable-with-controlled-setters — both satisfy the SPEC; planner picks one and binds the choice to a test.
3. Whether `Board.start()` returns the task handle or stores it internally — affects how `Board.stop()` joins.
4. Wall-clock deadline source: `team_config.ceiling.latency` (declared on the team) vs `team_config.board.card_deadline` (declared on the board). SPEC says "from `team_config.ceiling.latency` (default 30 min)" — confirm this lives on `ceiling`, not `board`.
</open_questions>

## Dependencies
- Depends on: **O1** (recorder + budget envelope + terminal-finalize), **O2** (compiled `TeamConfig` + `BoardSpec` + enriched `SubagentRegistry`).
- Blocks: **O4** (consumes the `Reviewer` Protocol O3 freezes), **O5** (EM dispatches via `Board.move`), **O6** (audit consumes `board.transition` deltas).
- Note: **O2 plans are written but not yet executed.** O3 planning may proceed in parallel, but O3 execution depends on O2 landing first.

---

*Phase: O3-board-state-machine*
*Context updated: 2026-05-19*
*Next step: `/gsd-plan-phase O3` — produce O3-NN-PLAN.md files (wave-numbered) driven by SPEC.md + this CONTEXT.md.*
