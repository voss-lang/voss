---
phase: O3-board-state-machine
plan: 04
type: execute
wave: 4
depends_on:
  - O3-03
files_modified:
  - voss/harness/board/tick.py
  - voss/harness/board/machine.py
  - voss/harness/board/__init__.py
  - tests/harness/board/conftest.py
  - tests/harness/board/test_tick_clock.py
  - tests/harness/board/test_timeout_tick.py
  - tests/harness/board/test_budget_tick.py
  - tests/harness/board/test_critic_loop.py
  - tests/harness/board/test_100_card_stress.py
  - tests/harness/board/test_board_lifecycle.py
autonomous: true
requirements:
  - OBRD-08
  - OBRD-09
  - OBRD-01
user_setup: []
must_haves:
  truths:
    - "`Board.__init__(clock: Callable[[], float] = time.monotonic)` accepts a callable clock injectable."
    - "`Board._tick_once(now: float)` is synchronous, idempotent, forces terminal-only (no forward progression)."
    - "A wall-clock deadline elapse drives the card to `Blocked(reason=\"timeout\")` after one tick."
    - "An O1-envelope drain drives the card to `Blocked(reason=\"budget\")` after one tick."
    - "4 sequential `verdict=\"fail\"` rounds against `retry.ceiling=3` land the card in `Blocked(reason=\"retry_ceiling\")` with 3 RetryNotes on `node.retry_notes`."
    - "`Board.start()` spawns an asyncio task; `Board.stop()` cancels and awaits drain."
    - "100-card stress run: zero non-terminal cards; mix of Done + Blocked outcomes."
    - "`exit_reason` written to `terminal_state` honors `EXIT_REASONS` (timeout uses literal `\"timeout\"`)."
  artifacts:
    - path: "voss/harness/board/tick.py"
      provides: "Clock Protocol, MonotonicClock default, FakeClock for tests, _tick_loop coroutine"
      contains: "class FakeClock"
    - path: "voss/harness/board/machine.py"
      provides: "Critic loop wired (InReview fail → InProgress + RetryNote); Board._tick_once for forced terminals; Board.start/stop; finalize_node calls on Blocked/Done"
      contains: "def _tick_once"
    - path: "tests/harness/board/test_100_card_stress.py"
      provides: "Deterministic 100-card stress proves liveness invariant"
      contains: "def test_100_card_stress"
  key_links:
    - from: "voss/harness/board/machine.py"
      to: "voss/harness/board/tick.py"
      via: "asyncio.create_task(_tick_loop(self, ...))"
      pattern: "asyncio\\.create_task"
    - from: "voss/harness/board/machine.py"
      to: "voss/harness/session_tree.finalize_node"
      via: "called on forced-terminal in _force_terminal"
      pattern: "finalize_node\\("
    - from: "voss/harness/board/machine.py"
      to: "SessionTreeNode.retry_notes"
      via: "RetryNote append on InReview fail"
      pattern: "retry_notes\\.append"
---

<objective>
Close OBRD-08 (critic loop) and OBRD-09 (timeout + 100-card stress). Land `tick.py` (Clock + FakeClock + `_tick_loop`); add `Board._tick_once`, `Board.start`, `Board.stop`, and the critic-loop branch in `Board.move`. Finalize terminal nodes via `finalize_node(exit_reason=...)`. Prove the cage's liveness invariant via a deterministic 100-card stress test.

Purpose: This is the wave that proves the cage closes. Before O3-04, cards can sit in any non-terminal column forever. After O3-04, every spawned card reaches `Done` or `Blocked` in finite time because (a) reviewer `fail` verdicts increment retry_count and accumulate RetryNotes until ceiling hit → Blocked, (b) periodic `_tick_once` checks wall-clock and budget envelopes and forces terminal, (c) on terminal, `finalize_node` seals the session-tree node. The 100-card stress test is the structural proof.

Output: 1 new source file (`tick.py`) + 1 source edit (`machine.py`) + 6 new test files covering OBRD-08, OBRD-09, full Board lifecycle (start/stop).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/O3-board-state-machine/O3-SPEC.md
@.planning/phases/O3-board-state-machine/O3-CONTEXT.md
@.planning/phases/O3-board-state-machine/O3-RESEARCH.md
@.planning/phases/O3-board-state-machine/O3-01-PLAN.md
@.planning/phases/O3-board-state-machine/O3-02-PLAN.md
@.planning/phases/O3-board-state-machine/O3-03-PLAN.md
@voss/harness/board/machine.py
@voss/harness/board/gates.py
@voss/harness/board/stub.py
@voss/harness/session_tree.py
@voss/harness/lifecycle.py

<interfaces>
<!-- Post-O3-03 surfaces -->

From voss/harness/session_tree.py:
```python
EXIT_REASONS = frozenset({"done", "max-iter", "budget", "interrupt", "batch-invariant", "timeout"})  # post-O3-01

def finalize_node(node, *, exit_reason: str, final: str = "", cwd: Path) -> None:
    """Seal a tree node to disk exactly once. Validates exit_reason ∈ EXIT_REASONS."""

def mutate_envelope(node, delta: int, cwd: Path) -> None:
    """Single guarded mutator for envelope changes."""
```

From voss/harness/lifecycle.py (cited from O3-RESEARCH.md §1.5) — canonical asyncio pattern:
```python
if start_task:
    rec.task = asyncio.create_task(_supervise(rec, ...))
# Cancellation:
task.cancel()
try: await task
except asyncio.CancelledError: pass
```

From voss/harness/board/machine.py (post-O3-03):
```python
class Board:
    def __init__(self, *, manager, reviewer, cwd, cfg, team_ceiling, root_node_id,
                 clock: Callable[[], float] = time.monotonic, per_card_budget=100_000, reserve=0) -> None: ...
    def move(self, card, to) -> Card: ...   # Gate-aware; raises BoardGateError / BoardWIPError
    def dry_run_gate(self, card, transition) -> tuple[bool, list[str]]: ...
    @property
    def root_node_id(self) -> str: ...
    def cards(self) -> list[Card]: ...
    # _tick_task slot exists but unused; start/stop NOT yet implemented
```

From voss/harness/board/gates.py (post-O3-03):
```python
class GateContext:
    card: Card; node_envelope: dict; team_ceiling: TeamCeiling
    team_p_overrides: dict; retry_ceiling: int; reserve: int; now: float
    reviewer: Reviewer | None; verdict: ReviewerVerdict | None
# 8 predicates with stable .name; conf_meets_p caches verdict on ctx.
```
</interfaces>

<pre_conditions>
- O3-03 shipped: gates.py, stub.py exist; Board.move evaluates predicates and emits passed/refused deltas.
- O3-01 shipped: `EXIT_REASONS` contains `"timeout"`; `SessionTreeNode.retry_notes` field exists; `SessionTreeManager.get_node` exists.
- pytest-asyncio in deps (verified — `tests/harness/test_session_tree.py` uses it).
</pre_conditions>

<open-question id="exit-reason-mapping">
Per O3-RESEARCH.md §5 / §11 R-04: forced-timeout cards need a terminal `exit_reason`. O3-01 extended `EXIT_REASONS` with `"timeout"`.

**Locked recommendation:** call `finalize_node(node, exit_reason="timeout")` for forced-timeout cards and `finalize_node(node, exit_reason="budget")` for forced-budget cards. The `BoardTransition.reason` field on the per-node `transitions` list retains the precise value either way; O6 audit can cross-reference.

**Fallback:** Map both to `exit_reason="budget"` (O3-RESEARCH.md original recommendation); rely solely on the `BoardTransition.reason` for audit fidelity. Choose this only if a checker raises an objection to extending `EXIT_REASONS`.

**Escalate to checkpoint:decision** only if O3-01 ships without the `EXIT_REASONS` extension. (O3-01 plan locks the extension; this branch should not fire.)
</open-question>

<open-question id="tick-forward-progression">
Per O3-RESEARCH.md §11 Open Question 2: should `_tick_once` advance non-terminal cards via forward gate evaluation, or ONLY force terminal states (timeout/budget)?

**Locked recommendation:** `_tick_once` ONLY forces terminal states. Forward progression is exclusively via `Board.move` (called by EM in O5 or by test drivers). This keeps tick deterministic (no reviewer calls on the tick path), preserves "the audit surface IS the UX" (forward moves emit per-call deltas), and matches SPEC L120/L121 (which speak only of timeout + budget → Blocked, not forward progression).

**Fallback:** add a `_advance_eligible(card)` helper that the tick loop calls per non-terminal card. Adds tick-loop reviewer cost; harder to test deterministically. Reject unless an explicit SPEC line requires it.

**Escalate to checkpoint:decision** only if the 100-card stress test cannot make progress with explicit-move-only — which it can per O3-RESEARCH.md §10 (the stress test uses an explicit move loop).
</open-question>

<open-question id="clock-protocol-vs-callable">
Per O3-CONTEXT.md `<code_context>` correction: NO `Clock` Protocol exists in the harness today; the actual convention is a `Callable[[], float] = time.monotonic` injectable (see `voss/harness/auth.py:423`).

**Locked recommendation:** support BOTH. `Board.__init__(clock: Callable[[], float] = time.monotonic)` (already in O3-02 by O3-CONTEXT.md `<code_context>` correction). In `tick.py`, also provide a `FakeClock` dataclass (per O3-RESEARCH.md §6) that exposes `now()` AND is callable via `__call__` so it works both as a Protocol AND as a `Callable[[], float]`. This satisfies the SPEC "monotonic-clock fake" requirement and the existing `auth.py` convention.

Concrete shape:
```python
@dataclass
class FakeClock:
    _t: float = 0.0
    def __call__(self) -> float: return self._t   # Callable[[], float] form
    def now(self) -> float: return self._t         # Protocol form
    def advance(self, dt: float) -> None: self._t += dt
```

**Fallback:** drop the Protocol entirely, ship only `FakeClock(_t: float)` with `__call__`. Smaller surface.

**Escalate to checkpoint:decision** only if a reviewer flags the dual-form as overdesign — the executor may collapse to `Callable[[], float]` form only if so.
</open-question>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: tick.py — FakeClock + _tick_loop; Board._tick_once forces terminals; finalize_node integration</name>
  <files>
    voss/harness/board/tick.py,
    voss/harness/board/machine.py,
    tests/harness/board/conftest.py,
    tests/harness/board/test_tick_clock.py,
    tests/harness/board/test_timeout_tick.py,
    tests/harness/board/test_budget_tick.py
  </files>
  <behavior>
    - Test 1 (test_tick_clock.py): `FakeClock(0.0)` — `clock()` returns 0.0; `clock.now()` returns 0.0; `clock.advance(30.0)`; both `clock()` and `clock.now()` return 30.0. Importable from `voss.harness.board.tick`.
    - Test 2 (test_timeout_tick.py): spawn card with `deadline_override=clock()+30.0`. `clock.advance(31.0)`. Call `board._tick_once(clock())`. Card column becomes `"Blocked"`; the node's last transition has `outcome="forced"`, `reason="timeout"`, `from` is the card's previous column, `to="Blocked"`. The node's `terminal_state == {"exit_reason": "timeout", "final": ""}` (proves `finalize_node` was called).
    - Test 3 (test_budget_tick.py): spawn card with `per_card_budget=1000`. Drain its envelope via `mutate_envelope(node, -1000, cwd)`. Call `board._tick_once(clock())`. Card becomes `"Blocked"`; node's last transition `reason="budget"`; `terminal_state["exit_reason"] == "budget"`.
    - Test 4 (test_timeout_tick.py): `_tick_once` is idempotent — call it twice with the same `now`; the second call appends NO new transition (already-terminal cards are skipped).
    - Test 5 (test_timeout_tick.py): cards already in `Done` or `Blocked` are skipped by `_tick_once` even if their deadline is in the past.
    - Test 6 (conftest update): add `fake_clock()` fixture returning a `FakeClock(0.0)` instance.
  </behavior>
  <action>
    1. Create `voss/harness/board/tick.py`:
       ```python
       """Clock abstraction + async tick loop for Board (O3 OBRD-09).

       Two clock forms supported:
         (a) Callable[[], float] — the auth.py:423 convention.
         (b) Clock Protocol — for tests that want clock.advance(dt) ergonomics.
       FakeClock satisfies BOTH (callable + .now()/.advance()).
       """
       from __future__ import annotations

       import asyncio
       import time
       from dataclasses import dataclass
       from typing import Protocol


       class Clock(Protocol):
           def now(self) -> float: ...


       class MonotonicClock:
           """Default production clock — wraps time.monotonic()."""
           def __call__(self) -> float:
               return time.monotonic()
           def now(self) -> float:
               return time.monotonic()


       @dataclass
       class FakeClock:
           """Test clock — manually advanced via advance(dt). Satisfies both
           Callable[[], float] and Clock Protocol."""
           _t: float = 0.0

           def __call__(self) -> float:
               return self._t

           def now(self) -> float:
               return self._t

           def advance(self, dt: float) -> None:
               self._t += dt


       async def _tick_loop(board: "object", clock, interval_s: float) -> None:
           """Async loop. ONE production path. Cancellation via asyncio.CancelledError.

           board is opaquely typed to avoid the machine→tick→machine import cycle;
           it must expose `_tick_once(now: float) -> None`.
           """
           while True:
               now = clock() if callable(clock) and not hasattr(clock, "now") else clock.now() if hasattr(clock, "now") else clock()
               # simpler: prefer .now() if available, else call directly
               try:
                   now_val = clock.now()
               except AttributeError:
                   now_val = clock()
               board._tick_once(now_val)
               await asyncio.sleep(interval_s)
       ```
       (Simplify the `now_val` extraction — the duplicated branches above were illustrative. Final form:
       ```python
       async def _tick_loop(board, clock, interval_s):
           while True:
               now_val = clock.now() if hasattr(clock, "now") else clock()
               board._tick_once(now_val)
               await asyncio.sleep(interval_s)
       ```
       This single-line form is what should land.)

    2. `voss/harness/board/machine.py` — add `_tick_once`, `_force_terminal`, `start`, `stop`:
       ```python
       # near imports:
       import asyncio
       from voss.harness.session_tree import finalize_node, mutate_envelope
       from .tick import _tick_loop, MonotonicClock

       # inside class Board:
       def _tick_once(self, now: float) -> None:
           """Synchronous test entry. Forces terminal states only — no forward progression.

           Idempotent: terminal cards are skipped; already-terminal nodes are not
           re-finalized.
           """
           # snapshot to avoid mutation-during-iteration
           for card in list(self._cards):
               if card.column in _TERMINAL_COLUMNS:
                   continue
               # 1. wall-clock check
               if now >= card.deadline:
                   self._force_terminal(card, reason="timeout")
                   continue
               # 2. budget exhaustion check
               node = self._manager.get_node(card.node_id)
               if node is None:
                   continue
               env = node.envelope
               if env["spent"] >= env["limit"] - self._reserve:
                   self._force_terminal(card, reason="budget")

       def _force_terminal(self, card: Card, *, reason: str) -> Card:
           """Force a card to Blocked with the given reason; finalize the node."""
           # build new card in Blocked column
           new_card = dataclasses.replace(card, column="Blocked")
           self._cards = [new_card if c.node_id == card.node_id else c for c in self._cards]
           # emit forced delta
           self._append_delta(card, from_col=card.column, to_col="Blocked",
                              outcome="forced", reason=reason)
           # finalize_node — exit_reason maps directly (timeout/budget both in EXIT_REASONS post-O3-01)
           node = self._manager.get_node(card.node_id)
           if node is not None and not node._finalized:
               # retry_ceiling exit_reason — map to "max-iter" to use existing EXIT_REASONS literal
               #   (only "timeout"/"budget" are forced from _tick_once; "retry_ceiling" comes from _critic_fail)
               exit_reason = reason if reason in {"timeout", "budget"} else "max-iter"
               finalize_node(node, exit_reason=exit_reason, final="", cwd=self._cwd)
           return new_card

       def start(self) -> None:
           """Start the periodic tick loop (idempotent)."""
           if self._tick_task is not None and not self._tick_task.done():
               return
           self._tick_task = asyncio.create_task(
               _tick_loop(self, self._clock, self._cfg.tick_interval_s)
           )

       async def stop(self) -> None:
           """Cancel the tick loop and await drain."""
           if self._tick_task is None:
               return
           self._tick_task.cancel()
           try:
               await self._tick_task
           except asyncio.CancelledError:
               pass
           self._tick_task = None
       ```
       Note: `_clock` was stored as `Callable[[], float]` in O3-02; if a `FakeClock` instance is passed, both `clock()` and `clock.now()` work. For internal use (`_tick_once` is called with `now` from `clock.now()` or `clock()`), accept whichever form.

    3. Update `Board.move` — when a transition succeeds to `"Done"`, also call `finalize_node(node, exit_reason="done")` (matches SPEC L110 "transitions emit RunRecord delta" + the finalize boundary). When a transition is forced into `"Blocked"` via critic-loop ceiling, the critic-loop code in O3-04 Task 2 calls `_force_terminal(card, reason="retry_ceiling")`. The `_force_terminal` helper above maps `"retry_ceiling"` → `exit_reason="max-iter"` for the finalize call (preserves EXIT_REASONS allowlist without further extension); the transition delta retains `reason="retry_ceiling"` for O6 audit fidelity. **Document this mapping in `_force_terminal`'s docstring** — it's a deliberate compression.

    4. Conftest update: add `fake_clock` fixture:
       ```python
       @pytest.fixture
       def fake_clock():
           from voss.harness.board.tick import FakeClock
           return FakeClock(0.0)
       ```

    5. Tests as listed in `<behavior>`. The wave reuses the existing test team / tmp_recorder fixtures; the only new fixture is `fake_clock`. For the budget-drain test, use the existing `mutate_envelope(node, -limit, cwd)` from session_tree.py.

    depends_on_o2_symbol: none new.
    locked_decisions_touched: `_tick_once` terminal-only (no forward progression); `finalize_node` mapping retry_ceiling→"max-iter" (avoids further EXIT_REASONS extension); Clock dual-form (Callable AND Protocol); `_tick_loop` is the only production path (no threading.Timer).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_tick_clock.py tests/harness/board/test_timeout_tick.py tests/harness/board/test_budget_tick.py -x -q</automated>
    <automated>.venv/bin/python -c "from voss.harness.board.tick import FakeClock, MonotonicClock; c=FakeClock(); c.advance(10.0); assert c()==10.0 and c.now()==10.0"</automated>
    <automated>.venv/bin/python -c "from voss.harness.board.machine import Board; import inspect; assert 'start' in dir(Board) and 'stop' in dir(Board) and '_tick_once' in dir(Board) and '_force_terminal' in dir(Board)"</automated>
    <automated>grep -c 'finalize_node' voss/harness/board/machine.py</automated>
    <automated>grep -c 'asyncio.create_task' voss/harness/board/machine.py</automated>
  </verify>
  <done>
    `tick.py` ships; `_tick_once` is sync, idempotent, terminal-only; wall-clock and budget exhaustion both force `Blocked` with correct reason; `finalize_node` is called exactly once per forced terminal; `Board.start`/`stop` follow the `lifecycle.py:351-372` pattern; both clock forms (Callable + Protocol) work.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Critic loop (InReview fail → InProgress + RetryNote) + Board.start/stop integration + 100-card stress</name>
  <files>
    voss/harness/board/machine.py,
    voss/harness/board/__init__.py,
    tests/harness/board/test_critic_loop.py,
    tests/harness/board/test_100_card_stress.py,
    tests/harness/board/test_board_lifecycle.py
  </files>
  <behavior>
    - Test 1 (test_critic_loop.py): with stub `DeterministicReviewerStub(conf=0.99, verdict="fail")` and `retry.ceiling=3`, drive card Backlog→Planned→InProgress→InReview→InProgress(fail#1)→InReview→InProgress(fail#2)→InReview→InProgress(fail#3)→InReview→fail#4. After the 4th fail, card is in `Blocked` with `reason="retry_ceiling"`. `manager.get_node(card.node_id).retry_notes` has exactly 3 entries (rounds 1, 2, 3); each is a dict with keys `{"round": int, "notes": str, "at": str}` in chronological order. Round 4's note is NOT in the list (ceiling hit before append).
    - Test 2 (test_critic_loop.py): the `Blocked` transition delta has `outcome="forced"` and `reason="retry_ceiling"`. The node's `terminal_state["exit_reason"] == "max-iter"` (per the documented mapping).
    - Test 3 (test_board_lifecycle.py): `asyncio.run` driver — `board.start()` spawns a task; assert `board._tick_task is not None and not board._tick_task.done()`. `await board.stop()` — task is cancelled; `board._tick_task is None`. Calling `stop()` when no task is running is a no-op.
    - Test 4 (test_board_lifecycle.py): integration — `board.start()` with `tick_interval_s=0.05`, FakeClock advanced to past a card's deadline; await `asyncio.sleep(0.2)`; `await board.stop()`; assert the card is now Blocked. (This is the ONLY test that exercises the real async loop; all other tests use `_tick_once` directly.)
    - Test 5 (test_100_card_stress.py): 100 cards with mixed outcomes (60% pass, 20% timeout, 10% budget-starved, 10% retry-ceiling). After driving deterministically with `_tick_once` + explicit `move` loop, EVERY card is in `Done` or `Blocked`. At least one Done; at least one Blocked of each reason (timeout, budget, retry_ceiling). Total wall-clock < 5 seconds.
    - Test 6 (test_100_card_stress.py): transition-delta count invariant holds across all 100 cards — `sum(len(node.transitions) for card in board.cards()) == total_attempts_made`.
  </behavior>
  <action>
    1. `voss/harness/board/machine.py` — add critic-loop branch to `Board.move`:

       After the gate-evaluation block (post-O3-03), if the transition is `("InReview","InProgress")` driven by a reviewer `fail`, AND `card.retry_count < cfg.retry_ceiling`:
       - Increment retry_count via `dataclasses.replace`.
       - Append `RetryNote` to `node.retry_notes`.
       - Persist via `_write_node_file`.
       - Emit `outcome="passed"` delta for the InReview→InProgress transition.

       Concrete logic — this is the trickiest part of the wave. The critic loop is **driven by the caller** (test driver / O5 EM) calling `move(card_in_inreview, "InProgress")` AFTER observing `verdict.verdict == "fail"` from a prior `move(card, "InReview")` attempt. The fail-verdict scenario:

       - `board.move(card, "InReview")` — predicates evaluate; `conf_meets_p` calls `reviewer.review`; verdict.conf=0.99 passes the threshold BUT `verdict.verdict == "fail"`. The predicate tuple `(budget_ok, scope_ok, conf_meets_p)` does NOT check `verdict.verdict`. So the move SUCCEEDS into InReview. **This is correct semantically:** the card enters InReview, the reviewer reports its verdict, and the EM (or test driver) reads the verdict from the transition delta's `verdict_snapshot` and decides to call `move(card_in_inreview, "InProgress")` to start the next critic round.

       - Therefore the critic loop is NOT an automatic branch inside `move`. It is a **convention**: the test driver / EM inspects the last transition's `verdict_snapshot["verdict"]`, and if `"fail"` AND `retry_count < ceiling`, calls `move(card, "InProgress")` to retry. If `retry_count >= ceiling`, the driver calls `_force_terminal(card, reason="retry_ceiling")` directly.

       - **Simpler API surface** — expose `Board.critic_step(card: Card, last_verdict: ReviewerVerdict) -> Card`:
         ```python
         def critic_step(self, card: Card, last_verdict: ReviewerVerdict) -> Card:
             """Process a reviewer 'fail' verdict.

             If retry_count < ceiling: card returns to InProgress with retry_count+1
             and a RetryNote appended to node.retry_notes. If ceiling hit:
             card forced to Blocked(reason="retry_ceiling").
             """
             if last_verdict.verdict != "fail":
                 return card   # no-op for pass/block
             new_retry = card.retry_count + 1
             if new_retry > self._cfg.retry_ceiling:
                 return self._force_terminal(card, reason="retry_ceiling")
             # rebuild card with incremented retry, column back to InProgress
             new_card = dataclasses.replace(card, column="InProgress", retry_count=new_retry)
             self._cards = [new_card if c.node_id == card.node_id else c for c in self._cards]
             # append RetryNote
             node = self._manager.get_node(card.node_id)
             if node is not None:
                 note = {
                     "round": new_retry,
                     "notes": last_verdict.notes,
                     "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 }
                 node.retry_notes.append(note)
             # emit a passed transition delta InReview→InProgress
             self._append_delta(card, from_col="InReview", to_col="InProgress",
                                outcome="passed",
                                verdict_snapshot=dataclasses.asdict(last_verdict))
             if node is not None:
                 _write_node_file(node, self._cwd)
             return new_card
         ```
         This isolates the critic-loop behavior from the gate-evaluation path. Add `critic_step` to `__init__.py` exports.

       Also handle `verdict == "block"` — the reviewer signaled "abort lineage" per SPEC REQ-7. Add an explicit branch in `critic_step` for `last_verdict.verdict == "block"`: `return self._force_terminal(card, reason="retry_ceiling")` (mapped to "max-iter" exit_reason). Or introduce a new reason `"reviewer_block"` — but SPEC L114 lists exactly 7 stable predicate names and `BoardTransition.reason ∈ {"timeout","budget","retry_ceiling"}`. **Lock decision: map `block` to `retry_ceiling`.** Block is a hard fail; ceiling is conceptually saturated.

    2. Also expose `Board.spawn_card` synchronously where tests need it. `allocate_child` is async; the 100-card stress test runs inside `asyncio.run(...)`. Keep `spawn_card` async; the stress test awaits 100 spawns in sequence (cheap).

       Alternatively, since `allocate_child` uses an `asyncio.Lock` but no real await beyond that, a sync wrapper is feasible:
       ```python
       def spawn_card_sync(self, **kwargs) -> Card:
           """Sync wrapper for spawn_card — uses asyncio.get_event_loop().run_until_complete.
           For tests / callers outside an async context only.
           """
           import asyncio
           return asyncio.get_event_loop().run_until_complete(self.spawn_card(**kwargs))
       ```
       **Decision:** keep `spawn_card` async only; tests use `asyncio.run` or `@pytest.mark.asyncio`. The 100-card stress test is `@pytest.mark.asyncio async def test_100_card_stress(...)`.

    3. `voss/harness/board/__init__.py` — export `Board.critic_step` is a method, not a top-level symbol; no new export needed. Verify `Board, Card, Column, ReviewerVerdict, Reviewer, BoardError, BoardWIPError, BoardGateError, BoardTimeoutError` are all in `__all__`.

    4. `tests/harness/board/test_critic_loop.py`:
       - Spawn card with passing artifact + scope.
       - Move through Backlog→Planned→InProgress→InReview using stub `DeterministicReviewerStub(conf=0.99, verdict="fail")`.
       - Use `verdict_snapshot` from the most-recent transition to confirm fail verdict.
       - Call `card = board.critic_step(card, ReviewerVerdict(conf=0.99, source="B", tier="strong", verdict="fail", notes="round-1-notes", evidence_refs=()))` — assert card.column=="InProgress", card.retry_count==1, node.retry_notes has 1 entry with round=1.
       - Repeat moves InReview + critic_step rounds 2 and 3 (retry_count=2, 3).
       - On round 4: `card = board.critic_step(card, ReviewerVerdict(verdict="fail", ...))` — card.column=="Blocked", reason="retry_ceiling", node.retry_notes still has 3 entries, terminal_state["exit_reason"]=="max-iter".

    5. `tests/harness/board/test_100_card_stress.py` — pytest-asyncio test per O3-RESEARCH.md §10:
       - FakeClock; build team with WIP=3 / latency=600s.
       - Spawn 100 cards with mixed configurations:
         - 60: passing artifact, normal deadline.
         - 20: passing artifact, deadline_override = clock()+0.1 (will timeout on first tick).
         - 10: passing artifact, per_card_budget=1 (will hit budget on first move that touches envelope; force via mutate_envelope).
         - 10: failing artifact (tests_passed=False; eval_score=0.0; will fail at →Done; drive critic_step until ceiling).
       - Drive deterministically in a bounded loop (max 50 iterations):
         - `clock.advance(1.0); board._tick_once(clock())` — forces timeout cards.
         - For each non-terminal card: attempt the next forward move (`_next_in_path(c.column)`); on success continue; on `BoardGateError(failing_clauses=["conf","tests","eval"])` for InReview→Done with failing artifact, call `board.critic_step(c, last_verdict_from_delta)`; on retry-ceiling result, card lands Blocked.
         - For budget-starved cards: manually `mutate_envelope(node, -node.envelope["limit"], cwd)` to drain; next `_tick_once` forces Blocked.
         - Break when all cards in `_TERMINAL_COLUMNS`.
       - Assertions:
         - Every card is `Done` or `Blocked`.
         - `sum(card.column == "Done" for card in board.cards()) >= 1`.
         - For each reason `r ∈ {"timeout", "budget", "retry_ceiling"}`: at least one card's last forced transition has `reason=r`.
         - `sum(len(manager.get_node(c.node_id).transitions) for c in board.cards()) == total_attempts_tracked`.

    6. `tests/harness/board/test_board_lifecycle.py` — async-driver test:
       - `@pytest.mark.asyncio`; build a board with `tick_interval_s=0.05`.
       - Spawn a card with `deadline_override=fake_clock()+0.0` (already past).
       - `board.start()`; await `asyncio.sleep(0.15)` (≥ 3 tick intervals); `await board.stop()`.
       - Assert card is Blocked with reason="timeout".
       - Also verify `start()` is idempotent (calling twice is no-op).
       - Verify `stop()` when not started is a no-op.

    depends_on_o2_symbol: none new.
    locked_decisions_touched: critic_step is a separate explicit API (caller-driven, not automatic); `verdict.verdict == "block"` maps to `retry_ceiling`; `retry_ceiling` exit_reason maps to `"max-iter"` for finalize_node (transition delta retains precise reason); 100-card stress uses _tick_once + explicit move loop (no real asyncio.sleep).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_critic_loop.py -x -q</automated>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_board_lifecycle.py -x -q</automated>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_100_card_stress.py -x -q --timeout 30</automated>
    <automated>.venv/bin/python -m pytest tests/harness/board/ -x -q</automated>
    <automated>.venv/bin/python -m pytest tests/harness/test_session_tree.py tests/harness/test_session_redaction.py tests/harness/test_subagent_recursion.py -x -q</automated>
    <automated>.venv/bin/python -c "from voss.harness.board.machine import Board; assert 'critic_step' in dir(Board)"</automated>
    <automated>grep -c 'retry_notes.append' voss/harness/board/machine.py</automated>
  </verify>
  <done>
    Critic loop works: 4 sequential fails on ceiling=3 lands `Blocked(reason="retry_ceiling")` with 3 RetryNotes in chronological order on `node.retry_notes`; `Board.start/stop` follow the lifecycle.py async pattern; 100-card stress run completes in <5s with zero non-terminal cards; transition-delta count invariant holds; reviewer verdict="block" maps to retry_ceiling termination; full board test suite green; no regressions in O1 substrate tests.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `_tick_once` ↔ `Board.move` | Both can transition a card to Blocked. `_tick_once` is terminal-only (timeout/budget); `move` is gate-evaluated (refused→raise) and never forces terminal. `critic_step` may call `_force_terminal` when ceiling hit. All three paths emit a delta; only `_tick_once` and `critic_step` call `finalize_node`. |
| Async `_tick_loop` ↔ Sync `_tick_once` | Production path goes through `_tick_loop` (which calls `_tick_once`). Tests call `_tick_once` directly. The two must produce identical state. |
| Reviewer `verdict.verdict ∈ {"pass","fail","block"}` ↔ `critic_step` dispatch | `pass` is a no-op (forward progression is the caller's call); `fail` retries until ceiling; `block` forces terminal. Mapping is documented in `critic_step` docstring. |
| `EXIT_REASONS` ↔ `finalize_node` calls | `"timeout"` and `"budget"` are forced from `_tick_once`; `"max-iter"` (mapped from retry_ceiling) is forced from `critic_step`; `"done"` is forced from a successful move to "Done". All four are in `EXIT_REASONS` post-O3-01. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-O3-04-01 | Denial-of-Service | Card stuck non-terminal forever (liveness violation) | mitigate | Dual mechanism: wall-clock deadline + budget envelope. 100-card stress (SPEC L122 acceptance) is the structural proof. |
| T-O3-04-02 | Repudiation | Forced-terminal lacks audit record | mitigate | `_force_terminal` calls `_append_delta` BEFORE `finalize_node`; both persist via `_write_node_file`. Test_transition_count_invariant (O3-02) extends across forced terminals via test_100_card_stress. |
| T-O3-04-03 | Tampering | Async tick loop races with sync `Board.move` | mitigate | `_tick_once` snapshots `self._cards` via `list(self._cards)` before iterating. `_cards` list is replaced wholesale on each transition (not mutated in-place). Python list operations are GIL-atomic. Real concurrent risk only with multi-threading — not in scope. |
| T-O3-04-04 | Information Disclosure | `RetryNote` contains reviewer-authored `notes` text on disk | mitigate | `retry_notes` field added to redaction allowlist in O3-01; structurally identical to `transitions.verdict_snapshot.notes`. |
| T-O3-04-05 | Spoofing | Caller drives `critic_step` with a fabricated `ReviewerVerdict` | accept | `critic_step` API takes the verdict as a parameter; caller (EM in O5) is the trust boundary, not Board. Board itself does not re-invoke the reviewer in critic_step (the verdict was already produced by the prior `move(card, "InReview")` call). |
| T-O3-04-06 | Elevation of Privilege | `_force_terminal` allows card column change without gate evaluation | accept | This is intentional — forced terminals are SPEC L120/L121 + L119 behavior. Audit invariant compensates: delta has `outcome="forced"` and explicit `reason`. |
</threat_model>

<verification>
**Plan-level automated:**
- Full board suite: `.venv/bin/python -m pytest tests/harness/board/ -x -q --timeout 30`
- O1 substrate regression: `.venv/bin/python -m pytest tests/harness/test_session_tree.py tests/harness/test_session_redaction.py tests/harness/test_subagent_recursion.py -x -q`
- 100-card stress under timeout: `--timeout 30` confirms the test completes in <30s (target <5s).
- Verdict.py import-set still ⊆ {typing, dataclasses, __future__} (O3-01 invariant).
- Single-source-threshold grep still == 1.

**Manual review:**
- Inspect a persisted node JSON for a card driven through full critic loop; confirm `retry_notes` and `transitions` round-trip cleanly.
- Confirm `finalize_node` is called exactly once per terminal card (grep `terminal_state` count in test outputs).
</verification>

<success_criteria>
- SPEC L119 acceptance: 4 sequential fails on `retry.ceiling=3` lands `Blocked(reason="retry_ceiling")` with 3 RetryNotes.
- SPEC L120 acceptance: wall-clock deadline → `Blocked(reason="timeout")` after one tick.
- SPEC L121 acceptance: O1 envelope drained → `Blocked(reason="budget")` after one tick.
- SPEC L122 acceptance: 100-card stress with WIP=3, mixed outcomes — zero non-terminal cards.
- SPEC L123 acceptance: transition-delta count == transition-attempt count across all 100 cards.
- `Board.start`/`Board.stop` follow `lifecycle.py:351-372` pattern.
- `_tick_once` is sync, idempotent, terminal-only (no forward progression).
- `finalize_node` is called exactly once per terminal card with `exit_reason ∈ EXIT_REASONS`.
- Full O3 phase: 14 SPEC acceptance checkboxes pass.
</success_criteria>

<output>
Create `.planning/phases/O3-board-state-machine/O3-04-SUMMARY.md` on completion. Include:
- 100-card stress test final wall-clock duration.
- Breakdown of card outcomes (Done count, Blocked-by-reason counts).
- Confirmation of liveness invariant: zero non-terminal cards.
- `finalize_node` call count vs terminal-card count (must match).
- Note on the `retry_ceiling → "max-iter"` exit_reason mapping (per documented decision).
- Full O3 phase acceptance: list each of the 14 SPEC acceptance checkboxes and its proving test file.
</output>
