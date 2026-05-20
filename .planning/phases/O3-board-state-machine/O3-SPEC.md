# Phase O3: Board State Machine + Gated Transitions — Specification

**Created:** 2026-05-19
**Ambiguity score:** 0.19 (gate: ≤ 0.20)
**Requirements:** 9 locked

## Goal

The harness gains a 6-column Kanban board that **is** the orchestrator state machine — per-board state lives on the O1 session-tree, each card maps 1:1 to a session-tree node, transitions between columns are gated by falsifiable predicates that consume O1 budget envelopes and a frozen `ReviewerVerdict` interface (O4 plugs in later), with per-column WIP, a `→Done` double gate, and budget+wall-clock timeouts that drive cards to a terminal `Done` or `Blocked` verdict.

## Background

No board, column, gate-predicate, or card-state machinery exists in the codebase today. `voss/grammar.lark` already declares board lexer keys (`columns | wip | p | retry | liveness`) at line 218 and a `gate_decl` production at line 219, and O2 parses these as opaque `BoardSpec.raw_items` — but nothing **executes** that declaration. O1 ships parent→child budget fan-out with reserved drain + terminal-finalize on `voss/harness/subagents.py` and the session tree on `voss/harness/recorder.py`/`session.py`; verdict semantics (`Blocked`/`Done`) were explicitly deferred from O1 to this phase. O2 ships an enriched `SubagentRegistry` consumed by the harness. O3 is the first phase that **runs** the cage.

Without O3, the budget substrate has no consumer, the parsed `team{}` config is dead data, and the cage invariants (every card reaches a verdict; →Done is double-gated; EM cannot widen scope by walking the board) have no enforcement surface. O4/O5/O6 cannot start until O3 freezes the consumer interfaces they each plug into.

## Requirements

1. **Card == session-tree node**: Every board card maps 1:1 to an O1 session-tree node. Column/status is a node attribute on the existing record schema; transitions emit `RunRecord` deltas.
   - Current: O1 ships parent→child session-tree nodes; nothing maps a "card" concept onto a node.
   - Target: A `Card` value-object holds `(node_id, column, risk_tier, retry_count, deadline)` and is looked up by `node_id`. No separate card registry / persistence file. Column is a node attribute, not a parallel store.
   - Acceptance: For every card observed in the board, `recorder.get_node(card.node_id)` returns a live `SessionRecord`; transitions append a `RunRecord` to that node whose payload includes `from_column` / `to_column`.

2. **Board lifecycle — one board per compiled `team{}`**: Each compiled `team{}` declaration spawns exactly one `Board` whose root is a new session-tree root node.
   - Current: `team{}` compiles to `(TeamConfig, SubagentRegistry)` (O2); no board is instantiated.
   - Target: A `Board.from_team_config(team_config, recorder) -> Board` factory creates the root node, registers the column set + WIP caps + retry ceiling + liveness timeout from `team_config`, and returns a live board. Multiple concurrent `team{}` blocks → multiple independent boards (no global state).
   - Acceptance: Two `Board.from_team_config(...)` calls with the same `TeamConfig` produce distinct boards with distinct root node ids and disjoint card sets; teardown of one does not affect the other.

3. **6-column state machine + per-column WIP**: The board exposes exactly 6 columns and enforces a per-column WIP cap.
   - Current: No board, no columns, no WIP cap.
   - Target: Columns: `Backlog → Planned → InProgress → InReview → Blocked → Done`. Each column has a declared cap (from `team_config.board.wip`, defaulting to: `Backlog: ∞, Planned: ∞, InProgress: 3, InReview: 2, Blocked: ∞, Done: ∞`). A transition that would exceed a destination cap is refused with `BoardWIPError`.
   - Acceptance: `board.move(card, to='InProgress')` succeeds for the first 3 cards and raises `BoardWIPError` on the 4th when `InProgress` cap is 3; cap-of-0 column refuses every transition into it.

4. **Gate predicates**: Each non-terminal transition is gated by a typed predicate; gates are pure functions of `(card, verdict, budget_state)`.
   - Current: No gate-predicate code; `gate_decl` parses but does not evaluate.
   - Target: A `Gates` registry binds each transition to a predicate:
     - `Backlog→Planned`: `scope.ok(card)` (no artifact yet — no confidence)
     - `Planned→InProgress`: `scope.ok(card) ∧ budget.ok(card)` (no artifact yet)
     - `InProgress→InReview`: `verdict.conf(B.fast) ≥ p(card.risk) ∧ scope.ok(card) ∧ budget.ok(card)`
     - `InReview→Done` (code): `verdict.conf(B.strong) ≥ p(card.risk) ∧ tests.pass(card.artifact) ∧ scope.clean(card)`
     - `InReview→Done` (ai): `verdict.conf(B.strong) ≥ p(card.risk) ∧ eval.score(card.artifact) ≥ card.eval_threshold ∧ scope.clean(card)`
     - `any→Blocked`: `budget.exhausted ∨ verdict.conf_below_floor ∨ scope.violation ∨ retry.ceiling_hit ∨ timeout`
   - Acceptance: Each transition refused by a failing predicate raises `BoardGateError` whose `.reason` field names the failing clause; a `dry_run_gate(card, transition) -> (passed: bool, failing_clauses: list[str])` method exists for inspection.

5. **Artifact-only confidence gating**: Confidence (`conf(B) ≥ p`) is only checked on transitions whose source state has produced an artifact (`InProgress→InReview`, `InReview→Done`). Non-artifact transitions gate on budget + scope only.
   - Current: No confidence gate.
   - Target: `Gates.confidence_required(transition) -> bool` returns `True` only for `InProgress→InReview` and `InReview→Done`. Other transitions never call into `verdict.conf`.
   - Acceptance: Mocking the verdict provider to raise on call proves `Backlog→Planned` and `Planned→InProgress` succeed without invoking it; `InProgress→InReview` raises the mock.

6. **Risk-tiered `p`**: The confidence threshold `p` per card is selected by a 3-bucket risk tier.
   - Current: No risk model.
   - Target: `card.risk_tier ∈ {"low", "med", "high"}` with thresholds `{low: 0.60, med: 0.80, high: 0.95}` (overridable per board via `team_config.board.p`). Default tier when EM tags none = `"med"`.
   - Acceptance: A card with `risk_tier="high"` and `verdict.conf=0.94` is refused `InProgress→InReview`; the same card with `verdict.conf=0.95` passes. The 3 thresholds are sourced from one named constant, not magic numbers in predicates.

7. **`ReviewerVerdict` dataclass + reviewer protocol — O4 consumer contract**: O3 freezes the verdict shape so O4 (Reviewer A/B implementations) plugs in without breaking O3 tests.
   - Current: No verdict type; reviewers don't exist yet.
   - Target: `@dataclass(frozen=True) ReviewerVerdict(conf: float, source: Literal["A","B"], tier: Literal["fast","strong"], verdict: Literal["pass","fail","block"], notes: str, evidence_refs: tuple[str, ...])` and `class Reviewer(Protocol): def review(self, card: Card) -> ReviewerVerdict: ...`. O3 ships an in-tree `DeterministicReviewerStub` for tests; production wiring is O4's responsibility.
   - Acceptance: A `Reviewer` implementation that returns a `ReviewerVerdict` is the only thing O4 must supply for the board to run; O3 tests exercise the full board with the stub and require zero changes when O4 lands.

8. **Critic loop — retry ceiling AND budget, first hit → Blocked**: A failed review returns the card to `InProgress` with reviewer notes appended to its episodic memory; the loop is bounded by both retry count and budget.
   - Current: No critic loop.
   - Target: `verdict.verdict == "fail"` on `InReview` transitions the card back to `InProgress`, increments `card.retry_count`, and appends a `RetryNote(round, verdict.notes)` to the node's episodic memory. The loop ends when either `card.retry_count > team_config.board.retry.ceiling` (default 3) OR `budget.exhausted` — whichever fires first → `any→Blocked` with `reason="retry_ceiling"` or `reason="budget"`.
   - Acceptance: 4 sequential fail-verdicts drive a card with `retry.ceiling=3` to `Blocked(reason="retry_ceiling")`. A single fail-verdict that overshoots the card's spendable envelope drives the card to `Blocked(reason="budget")` on the same iteration. Retry notes from all rounds are readable on the node's episodic memory in order.

9. **Timeout — budget-fraction primary + wall-clock safety net**: Every card has both a budget envelope (from O1) and a wall-clock deadline; either trips → `Blocked`.
   - Current: O1 enforces budget envelopes; no wall-clock deadline.
   - Target: At card spawn, `Board` records `card.deadline = spawn_ts + team_config.ceiling.latency` (default 30 min). A periodic `Board.tick()` (default every 1 s; injectable for tests) checks all `not-yet-terminal` cards: any whose `deadline < now` are forced `→Blocked(reason="timeout")` and any whose O1 envelope is exhausted are forced `→Blocked(reason="budget")`. Liveness invariant: every spawned card reaches `Done` or `Blocked` in finite time.
   - Acceptance: A card whose deadline elapses while idle (no budget spent) lands in `Blocked(reason="timeout")` after one `tick()`. A card whose O1 envelope is drained while idle lands in `Blocked(reason="budget")` after one `tick()`. A 100-card stress run with `InProgress` WIP=3 and budget-starved spawns finishes with **zero** non-terminal cards.

## Boundaries

**In scope:**
- `Board` state machine + 6 columns + per-column WIP enforcement
- `Card` value-object keyed by `SessionRecord` node id (no parallel persistence)
- Gate-predicate registry implementing every transition in the §3 table
- `ReviewerVerdict` dataclass + `Reviewer` protocol (frozen interface only)
- In-tree `DeterministicReviewerStub` for O3 tests
- `risk_tier`-based `p` selection with team-level override
- Critic loop with retry-ceiling AND budget bound
- Budget + wall-clock timeout via injectable `Board.tick()`
- `BoardWIPError`, `BoardGateError`, `BoardTimeoutError` typed errors with `.reason`
- Integration with O1 `recorder` + budget envelopes (no new schema)
- Integration with O2 `TeamConfig` / compiled `SubagentRegistry`

**Out of scope:**
- Reviewer-A and Reviewer-B *implementations* — that is O4 (O3 only freezes the consumer interface and ships a deterministic stub)
- EM (Engineering Manager) board mutation, ticket authoring, AC/DoD generation, specialist dispatch — that is O5 (O3 exposes the board API; O5 calls it)
- Audit product, killed-card surfacing, calibration telemetry, sign-off forcing function — that is O6 (O3 emits the `RunRecord` deltas O6 will consume)
- `team{}` grammar/parser changes — O2 ships `BoardSpec` as opaque tuple; O3 reads it but does not modify the parser
- New schema for `SessionRecord` / `RunRecord` — O1 invariant is preserved (record shape unchanged)
- UI / TUI surface for the board — headless library only; visualization is a separate concern
- Cross-board scheduling / global WIP — each board is independent (decision: "one board per team{}")
- Continuous-formula `p` (scope × budget × core-file-touch) — deferred to O6 calibration; 3-bucket tier is the locked O3 model
- Card priority / queue ordering inside a column — FIFO is the default; priority systems are not in scope
- Persistence across process restarts — board state lives in-memory + via O1 records; durable replay across restarts is F1 (Durable Session Persistence)

## Constraints

- **Reuse the O1 session tree**: card state IS a node attribute; no new persisted-record schema (preserves O1's "strict harness-additive blast radius" invariant SPEC-5).
- **Reuse the O2 compiled config**: read `TeamConfig.ceiling`, `TeamConfig.board`, `SubagentRegistry` — do not re-parse `team{}` blocks.
- **Reuse `voss/harness/skill/scope.py:_min_mode` and `scoped_gate`** for any per-card permission cap that O5 (EM dispatch) will need; do not introduce a parallel authorization engine.
- **`ReviewerVerdict` and `Reviewer` must be importable by O4 without circular deps**: they live in `voss/harness/board/verdict.py`, importing only from `typing` and `dataclasses`.
- **`Board.tick()` must be injectable**: tests pass a monotonic-clock fake and trigger `tick()` synchronously; no `asyncio.sleep` in the core loop.
- **All state transitions emit exactly one `RunRecord` delta** on the card's session-tree node; transitions refused by a gate emit a delta with `outcome="refused"` and the failing-clause list — silent refusal is forbidden (O6 audit invariant).
- **Liveness invariant**: every spawned card reaches `Done` or `Blocked` in finite time (reserved drain + wall-clock timeout combined guarantee).
- **EM-immutability inherited from O2**: nothing in O3 exposes a mutation API for `TeamConfig.ceiling` or `TeamConfig.p`; gates read them and never rebind.

## Acceptance Criteria

- [ ] `Card.column` is reachable only via `recorder.get_node(card.node_id)` — no separate card-state store exists in the repository.
- [ ] `Board.from_team_config(...)` creates a board whose root session-tree node id is observable via `board.root_node_id`.
- [ ] Exactly 6 column names are accepted by `Board.move(card, to=...)`; any other string raises `BoardGateError("unknown column: …")`.
- [ ] A WIP cap of N on column C refuses the (N+1)th transition into C with `BoardWIPError`.
- [ ] `dry_run_gate(card, transition)` returns the list of failing predicate clauses by stable name (`"conf"`, `"tests"`, `"eval"`, `"scope"`, `"budget"`, `"retry"`, `"timeout"`).
- [ ] Mocked `Reviewer.review` is **not** invoked for `Backlog→Planned` or `Planned→InProgress` (artifact-only confidence proof).
- [ ] Risk thresholds {low: 0.60, med: 0.80, high: 0.95} are sourced from a single named constant referenced from a single import site.
- [ ] `ReviewerVerdict` is a frozen dataclass with the exact 6 fields listed in REQ-7; `Reviewer` is a `Protocol` with one method.
- [ ] `DeterministicReviewerStub(conf=0.99, verdict="pass")` runs the full lifecycle Backlog→…→Done without invoking any real LLM.
- [ ] 4 sequential `verdict=fail` rounds against a `retry.ceiling=3` card land in `Blocked(reason="retry_ceiling")` with 3 `RetryNote` entries readable on the node's episodic memory.
- [ ] A card whose wall-clock deadline elapses after `Board.tick()` lands in `Blocked(reason="timeout")`.
- [ ] A card whose O1 envelope is drained after `Board.tick()` lands in `Blocked(reason="budget")`.
- [ ] 100-card stress: WIP=3, deterministic stub, mixed budget/timeout/pass cards — every card terminates as `Done` or `Blocked`; zero non-terminal cards after the run.
- [ ] Every state transition (passed or refused) emits exactly one `RunRecord` delta on the card's node — count of records matches count of transition attempts.
- [ ] `voss/harness/board/verdict.py` imports only from `typing`, `dataclasses` (no transitive harness imports — O4 plug-in safety).

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                                 |
|--------------------|-------|------|--------|-----------------------------------------------------------------------|
| Goal Clarity       | 0.88  | 0.75 | ✓      | Card-on-node, board scope, verdict shape, columns all pinned          |
| Boundary Clarity   | 0.85  | 0.70 | ✓      | Explicit out-of-scope list with O4/O5/O6/F1 phase pointers            |
| Constraint Clarity | 0.75  | 0.65 | ✓      | Reuse points pinned; `Board.tick()` injectability locked              |
| Acceptance Criteria| 0.70  | 0.70 | ✓      | 14 pass/fail criteria; stress test bounded                            |
| **Ambiguity**      | 0.19  | ≤0.20| ✓      |                                                                       |

## Interview Log

| Round | Perspective | Question summary                                      | Decision locked                                                                                                                                                          |
|-------|-------------|-------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1     | Researcher  | Where does card state live relative to O1 tree?       | Card IS an O1 session-tree node; no parallel store.                                                                                                                       |
| 1     | Researcher  | What O4 consumer interface does O3 freeze NOW?        | `ReviewerVerdict` frozen dataclass + `Reviewer` protocol; in-tree `DeterministicReviewerStub` for O3 tests.                                                              |
| 1     | Researcher  | Board scope per session-tree root?                    | One board per compiled `team{}` block; one root tree node per board; concurrent boards are independent.                                                                  |
| 2     | Simplifier  | Cut columns for MVP?                                  | Keep all 6 (Backlog/Planned/InProgress/InReview/Blocked/Done) — downstream O4/O5/O6 assume the full set; Blocked is structural for liveness.                             |
| 2     | Simplifier  | Risk `p` formula vs tier vs fixed?                    | 3-bucket tier {low 0.60 / med 0.80 / high 0.95}, team-overridable; continuous formula deferred to O6 calibration.                                                        |
| 2     | Simplifier  | Timeout — wall-clock, budget, both?                   | Budget-fraction primary (via O1 envelope), wall-clock safety net (default 30 min from `team_config.ceiling.latency`) — both → `Blocked` with distinct `.reason`.         |

---

*Phase: O3-board-state-machine*
*Spec created: 2026-05-19*
*Next step: `/gsd-discuss-phase O3` — implementation decisions (how to wire the state machine onto `recorder.py`, where the gate-predicate registry lives, etc.)*
