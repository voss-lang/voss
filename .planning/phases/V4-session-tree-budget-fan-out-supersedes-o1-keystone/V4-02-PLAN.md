---
phase: V4-session-tree-budget-fan-out-supersedes-o1-keystone
plan: 02
type: execute
wave: 2
depends_on: ["V4-01"]
files_modified:
  - voss/harness/subagents.py
  - tests/harness/test_session_tree.py
autonomous: true
requirements: [VTREE-04, VTREE-07, VTREE-02]
must_haves:
  truths:
    - "A node whose envelope is exhausted (spent >= limit) cannot START another iteration/call — the guard halts before any spend and finalizes exit_reason=budget"
    - "After a run_turn completes, the node's spent is incremented by actual token usage (the wiring that makes the guard live)"
    - "A child driven to budget exhaustion stops at the boundary — no overspend beyond the envelope — and yields exactly one finalized node"
    - "error, timeout, and budget termination paths each emit exactly one finalized node (terminal_state set, ended_at populated)"
    - "No node remains open after run_subagent returns or raises (finally safety net)"
    - "Concurrent children still cannot oversell the parent (allocate_child asyncio.Lock invariant holds)"
  artifacts:
    - path: "voss/harness/subagents.py"
      provides: "Pre-emptive spend guard + mutate_envelope spend wiring + except TimeoutError/Exception + finally finalize in run_subagent"
      contains: "node.envelope[\"spent\"] >= node.envelope[\"limit\"]"
    - path: "tests/harness/test_session_tree.py"
      provides: "TestSpendGuard + TestAllReasonsFinalize test classes"
      contains: "TestSpendGuard"
  key_links:
    - from: "voss/harness/subagents.py::run_subagent"
      to: "session_tree.finalize_node"
      via: "pre-emptive guard before async-with-scope + try/except/finally"
      pattern: "finalize_node\\(node, exit_reason="
    - from: "voss/harness/subagents.py::run_subagent"
      to: "session_tree.mutate_envelope"
      via: "post-run_turn spend update from result.run token totals"
      pattern: "mutate_envelope\\(node, delta=-"
---

<objective>
The keystone correctness fix. Wire `run_subagent` so the budget envelope becomes a real security boundary, not a post-hoc audit: (1) a pre-emptive spend guard that refuses to begin a call when `spent >= limit`; (2) the `mutate_envelope` spend-update after each `run_turn` that makes the guard live (without it the guard is dead code — `spent` never moves); (3) an all-reason finalize boundary so error/timeout/budget paths each emit exactly one finalized node and no node is ever left open.

Purpose: VTREE-04 (pre-emptive guard, the keystone) + VTREE-07 (always-finalize). Today `run_subagent` records spend post-hoc and catches only `BudgetExceededError`, leaving error/timeout paths with open nodes. This plan closes both. Depends on V4-01 (needs `"error"` in EXIT_REASONS for the exception path; aligned with the scope/role schema).

Output: a guarded, always-finalizing `run_subagent`; deterministic guard + all-reason tests; verified no-oversell regression.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-SPEC.md
@.planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-RESEARCH.md
@.planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-PATTERNS.md
@.planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-01-SUMMARY.md

<interfaces>
<!-- run_subagent current body (subagents.py lines 211-285). Guard goes after the
     `spec is None` early return, before `async with scope:`. Spend update goes after
     `async with scope:` exits, before the soft-exit check. New except branches go
     after the existing `except BudgetExceededError`, with a final `finally`. -->

From voss/harness/subagents.py:
- async def run_subagent(*, agent_id, task, registry, cwd, renderer, provider, model,
    gate, cognition=None, node: SessionTreeNode | None = None, reserve: int = 0) -> str
- current imports (line 18): `from .session_tree import finalize_node`  # must extend with mutate_envelope
- current imports: NO `import asyncio`  # must add
- existing: `except BudgetExceededError:` finalizes exit_reason="budget" (KEEP unchanged)

From voss/harness/session_tree.py (V4-01 state):
- finalize_node(node, *, exit_reason, final="", cwd) -> None  # idempotent via node._finalized
- mutate_envelope(node, delta, cwd)  # delta<0 increments spent; delta>0 raises BudgetCapRaiseError
- SessionTreeNode.envelope == {"limit": int, "spent": int}; node._finalized: bool

From voss/harness/session.py (V4-01 state):
- EXIT_REASONS now includes "error"  # exception path uses exit_reason="error"
- RunRecord.iteration_total_prompt_tokens: int = 0
- RunRecord.iteration_total_completion_tokens: int = 0  # token source for spend update (CONFIRMED in codebase)

From run_turn result:
- result.final: str ; result.run: RunRecord | None ; result.run.exit_reason: str | None
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Pre-emptive spend guard + post-run_turn spend wiring in run_subagent</name>
  <read_first>
    - voss/harness/subagents.py (full read — lines 1-19 imports, 211-285 run_subagent body)
    - voss/harness/session_tree.py (finalize_node + mutate_envelope signatures; envelope dict shape)
    - voss/harness/session.py (lines 118-145 — RunRecord field names iteration_total_prompt_tokens / iteration_total_completion_tokens)
    - .planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-PATTERNS.md (subagents.py sections 1 + 4 — guard insertion point + spend-update pattern)
    - .planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-RESEARCH.md (Focus Area 1, Pitfall 1)
  </read_first>
  <behavior>
    - run_subagent called with a node where spent >= limit: run_turn is NEVER invoked (mock asserts zero calls); returns the "<halted: budget — envelope exhausted>" string; node._finalized is True with terminal_state.exit_reason == "budget".
    - run_subagent called with a node where spent < limit and a mocked run_turn returning a RunRecord with iteration_total_prompt_tokens=30, iteration_total_completion_tokens=20: after the call node.envelope["spent"] increased by 50.
    - run_turn result.run is None: no spend update, no crash (spent unchanged).
    - normal completion (exit_reason != "budget"): node finalized exit_reason="done".
  </behavior>
  <action>
    In voss/harness/subagents.py: add `import asyncio` to the imports (top of file). Extend line 18 import to `from .session_tree import finalize_node, mutate_envelope`. Insert the pre-emptive guard in run_subagent AFTER the `if spec is None: return ...` early return and BEFORE `spendable = ...` / `async with scope:` — guard logic: `if node is not None and node.envelope["spent"] >= node.envelope["limit"]:` then (idempotent) `if not node._finalized: finalize_node(node, exit_reason="budget", final="<halted: budget — envelope exhausted>", cwd=cwd)` and `return "<halted: budget — envelope exhausted>"`. The guard must be a pure read of the node's own envelope before any spend — do NOT hold a lock (asyncio cooperative scheduling makes the check+return atomic; no await between them; per RESEARCH Concurrency Analysis). Then, on the normal path AFTER `async with scope:` exits and BEFORE the existing soft-exit `if node and result.run and result.run.exit_reason == "budget"` check, add the spend update: when `node and result.run is not None`, compute `tokens_used = (result.run.iteration_total_prompt_tokens or 0) + (result.run.iteration_total_completion_tokens or 0)` and if `tokens_used > 0` call `mutate_envelope(node, delta=-tokens_used, cwd=cwd)` (negative delta increments spent; positive would raise BudgetCapRaiseError). Keep the existing soft-exit budget/done finalize branches and the existing `except BudgetExceededError` branch unchanged in this task (the new except/finally branches are Task 2). Document in the SUMMARY the known V4 gap: the `attach_subagent_tool` closure calls run_subagent WITHOUT node=, so the tool-dispatched path is unguarded in V4 (same as O1; node plumbing through the tool closure is V5/V7 work).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestSpendGuard -x -q</automated>
  </verify>
  <acceptance_criteria>
    - Source assertion: `grep -n "import asyncio" voss/harness/subagents.py` returns the new import.
    - Source assertion: `grep -n "from .session_tree import finalize_node, mutate_envelope" voss/harness/subagents.py` confirms the extended import.
    - Source assertion: `grep -c "node.envelope\[\"spent\"\] >= node.envelope\[\"limit\"\]" voss/harness/subagents.py` returns at least 1 (the guard).
    - Source assertion: `grep -n "mutate_envelope(node, delta=-tokens_used" voss/harness/subagents.py` confirms the spend wiring.
    - Behavior: `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestSpendGuard -x -q` passes — including the test asserting run_turn is NOT called when spent>=limit, and the test asserting spent increments by actual token usage after a call.
  </acceptance_criteria>
  <done>Guard halts a node at/over its envelope before any spend and finalizes budget; spent is updated from real token totals after each run_turn (guard is live, not dead code); normal-path finalize unchanged.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: All-reason finalize boundary (except TimeoutError / except Exception / finally)</name>
  <read_first>
    - voss/harness/subagents.py (run_subagent try/except body as modified in Task 1)
    - voss/harness/session_tree.py (finalize_node idempotence via _finalized — lines 113-123)
    - voss/harness/session.py (EXIT_REASONS now includes "error" + "timeout" + "budget")
    - .planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-PATTERNS.md (subagents.py section 2 — except/finally append; note asyncio.TimeoutError must precede Exception)
    - .planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-RESEARCH.md (Focus Area 2, Pitfalls 3 + 5)
  </read_first>
  <behavior>
    - run_turn raises asyncio.TimeoutError: node finalized exactly once with exit_reason="timeout", ended_at populated; the TimeoutError re-raises to the caller.
    - run_turn raises a generic Exception("boom"): node finalized exactly once with exit_reason="error", ended_at populated; the exception re-raises.
    - run_turn raises BudgetExceededError: node finalized exactly once exit_reason="budget" (existing behavior preserved); no double-finalize from finally.
    - finalize_node accepts every value in EXIT_REASONS (parametrized): done, max-iter, budget, interrupt, batch-invariant, timeout, killed, error — each seals the node.
    - After any of the above, the node is never left open (terminal_state is not None).
  </behavior>
  <action>
    In voss/harness/subagents.py run_subagent: append two new except branches AFTER the existing `except BudgetExceededError` and add a `finally`. Order matters — `except asyncio.TimeoutError:` MUST come before `except Exception:` because TimeoutError is an Exception subclass in Python 3.11+. TimeoutError branch: if node, `finalize_node(node, exit_reason="timeout", final="<halted: timeout>", cwd=cwd)` then `raise` (re-raise; caller defines timeout semantics — RESEARCH Pitfall 5). Exception branch: `except Exception as exc:` if node, `finalize_node(node, exit_reason="error", final=f"<error: {exc}>", cwd=cwd)` then `raise` (uses the "error" reason added in V4-01). Finally branch: `finally:` `if node is not None and not node._finalized: finalize_node(node, exit_reason="error", final="<uncaught>", cwd=cwd)` — the idempotence safety net (finalize_node also re-checks _finalized, double-guard per RESEARCH Pitfall 3) guaranteeing no open node on any path. Author the new test classes: `TestSpendGuard` (if not fully covered in Task 1, complete it) and `TestAllReasonsFinalize` in tests/harness/test_session_tree.py — mock voss.harness.subagents.run_turn with AsyncMock (use unittest.mock patch) to inject the timeout/error/budget exceptions and a normal RunRecord; parametrize finalize_node over the full EXIT_REASONS set; assert exactly one finalize (terminal_state set + ended_at set) and re-raise behavior. Use a minimal SubagentRegistry with a registered spec, a no-op Renderer/gate as in existing subagent tests (follow the conventions already in tests/harness/). Follow async class style (no @pytest.mark.asyncio; asyncio_mode=auto).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestAllReasonsFinalize tests/harness/test_session_tree.py::TestSpendGuard -x -q</automated>
  </verify>
  <acceptance_criteria>
    - Source assertion: `grep -n "except asyncio.TimeoutError" voss/harness/subagents.py` appears BEFORE `grep -n "except Exception as exc" voss/harness/subagents.py` (TimeoutError caught first).
    - Source assertion: `grep -c "finally:" voss/harness/subagents.py` returns at least 1; `grep -n "not node._finalized" voss/harness/subagents.py` confirms the safety-net guard.
    - Source assertion: `grep -n "exit_reason=\"error\"" voss/harness/subagents.py` confirms the exception path uses the V4-01 "error" reason.
    - Behavior: `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestAllReasonsFinalize -x -q` passes — timeout→one node exit_reason=timeout (re-raises), error→one node exit_reason=error (re-raises), budget→one node exit_reason=budget; parametrized finalize over all EXIT_REASONS green.
    - Behavior: no double-finalize — TestAllReasonsFinalize asserts terminal_state.exit_reason matches the FIRST finalize even though `finally` runs (idempotence).
  </acceptance_criteria>
  <done>error/timeout/budget paths each emit exactly one finalized node; finally net guarantees no open node; finalize_node accepts every EXIT_REASONS value including the new "error".</done>
</task>

<task type="auto">
  <name>Task 3: Verify no-oversell concurrency regression (VTREE-02/04 invariant)</name>
  <read_first>
    - tests/harness/test_session_tree.py (lines 99-162 — TestBudgetFanOut + TestConcurrency, the existing no-oversell tests that must regress green)
    - voss/harness/session_tree.py (allocate_child asyncio.Lock block, lines 165-192 — unchanged by V4; verify lock invariant)
    - .planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-VALIDATION.md (Keystone concurrency proof — deterministic, no sleep-timing)
  </read_first>
  <action>
    Verify the fan-out invariant holds after the guard/finalize wiring: run the existing TestConcurrency::test_concurrent_no_oversell and TestBudgetFanOut tests — they must regress green unchanged (allocate_child's asyncio.Lock was NOT touched by V4-02; the guard is a per-node envelope read with no cross-node locking). If, and only if, the existing TestConcurrency does not already assert the post-condition `sum(child limits) + reserve <= parent limit` under concurrent allocate_child via asyncio.gather, add one deterministic test (no sleep-based timing — use asyncio.gather of N allocate_child calls that collectively would breach the parent and assert BudgetAllocationError is raised for the breaching ones AND the persisted children never exceed the parent envelope). Do NOT modify allocate_child or any production concurrency code in this task — this is verification + (conditional) test hardening only.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestConcurrency tests/harness/test_session_tree.py::TestBudgetFanOut -x -q</automated>
  </verify>
  <acceptance_criteria>
    - Regression: `.venv/bin/python -m pytest tests/harness/test_session_tree.py::TestConcurrency tests/harness/test_session_tree.py::TestBudgetFanOut -x -q` passes.
    - Source assertion: `git diff -- voss/harness/session_tree.py | grep -E "^[+-]" | grep -i "lock"` returns no lines (allocate_child lock untouched by this plan).
    - Full-file: `.venv/bin/python -m pytest tests/harness/test_session_tree.py -x -q` green (guard/finalize/concurrency all coexisting).
  </acceptance_criteria>
  <done>Concurrent children cannot oversell the parent envelope (regression holds, deterministic proof, no sleep-timing); allocate_child lock untouched.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| child node envelope ↔ run_turn spend | THE budget security boundary (cage). A child spending past its envelope = cage escape. Pre-emptive guard is the containment |
| concurrent sibling children ↔ shared parent envelope | concurrent fan-out must not oversell the parent (asyncio.Lock in allocate_child) |
| termination path ↔ node finalization | an unfinalized (open) node leaks budget accounting and is a resource/DoS leak |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V4-10 | Elevation of Privilege | budget-cage escape via post-hoc spend | mitigate | Pre-emptive guard at run_subagent entry refuses to BEGIN a call when spent>=limit (Task 1); proven by TestSpendGuard asserting run_turn is never called past the envelope |
| T-V4-11 | Tampering | oversell race under concurrent fan-out | mitigate | allocate_child asyncio.Lock (existing, untouched) guards check-then-append; deterministic no-oversell regression (Task 3) under asyncio.gather, no sleep-timing |
| T-V4-12 | Denial of Service | orphan/unfinalized node leaking budget | mitigate | try/except(Timeout,Exception)/finally guarantees exactly one finalize on every path (Task 2); finally net + finalize_node idempotence prove no open node after teardown |
| T-V4-13 | Elevation of Privilege | dead guard (spent never updated) silently disables the cage | mitigate | mutate_envelope spend wiring after every run_turn (Task 1) makes the guard live; TestSpendGuard::spent-updated-after-call asserts spent moves with real token totals — the explicit anti-dead-code signal (RESEARCH Pitfall 1) |
| T-V4-14 | Elevation of Privilege | tool-dispatched subagent_run bypasses guard (node=None) | accept | DOCUMENTED V4 gap (same as O1): attach_subagent_tool closure passes no node, so the `if node is not None` guard is skipped. Node-through-tool plumbing is V5/V7. V4 proves the mechanism on the direct run_subagent(node=...) path; recorded in SUMMARY |
| T-V4-SC | Tampering | npm/pip/cargo installs | n/a | Zero third-party installs in V4 |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_session_tree.py -x -q` — full file green (guard + all-reason finalize + concurrency).
- `.venv/bin/python -m pytest tests/harness/test_session_redaction.py -x -q` — UNMODIFIED, green.
- `git diff -- voss/harness/subagents.py` — only the guard, the asyncio/mutate_envelope imports, the spend-update, and the except/finally branches; no signature change to run_subagent.
</verification>

<success_criteria>
- A node at/over its envelope cannot start another call; the guard halts before any spend and finalizes budget (VTREE-04).
- spent is updated from real token totals after each run_turn — the guard is live (VTREE-04, anti-dead-code).
- error/timeout/budget each emit exactly one finalized node; no node open after teardown; finalize_node accepts every EXIT_REASONS value (VTREE-07).
- Concurrent children cannot oversell the parent (VTREE-02/04 regression).
- Documented V4 gap: tool-dispatched path unguarded (node=None) — V5/V7.
- test_session_redaction.py unmodified; zero frozen-schema field changes.
</success_criteria>

<output>
Create `.planning/phases/V4-session-tree-budget-fan-out-supersedes-o1-keystone/V4-02-SUMMARY.md` when done. Record: the keystone wiring, the spend-update token source confirmation, and the documented unguarded tool-dispatch gap (T-V4-14).
</output>
