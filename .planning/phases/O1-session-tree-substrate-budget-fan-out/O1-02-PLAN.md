---
phase: O1-session-tree-substrate-budget-fan-out
plan: 02
type: tdd
wave: 2
depends_on: ["O1-01-session-tree-substrate-budget-fan-out"]
files_modified:
  - tests/harness/test_session_tree.py
  - voss/harness/session_tree.py
  - voss/harness/subagents.py
autonomous: true
requirements: [SPEC-1, SPEC-3, SPEC-5]
must_haves:
  truths:
    - "Spawning a child via run_subagent creates a tree node linked to its parent (parent_run_id = parent's node id) and writes the node file at open BEFORE run_turn executes"
    - "A budget-drained child (soft exit_reason='budget' OR hard BudgetExceededError) finalizes exactly one terminal RunRecord with exit_reason='budget' and a closed node (terminal_state set, ended_at populated)"
    - "Finalize happens exactly once even if both budget signals could fire (the _finalized guard prevents double-finalize)"
    - "After parent teardown no node remains in an open state (zero node files with terminal_state == None)"
    - "reserve is honored: run_turn receives token_budget = envelope_limit - reserve while the composed BudgetScope.token_limit stays at envelope_limit"
    - "test_subagent_recursion.py passes unmodified (only node + reserve kwargs added; no depth/max_depth symbols)"
    - "test_session_redaction.py passes unmodified; git diff zero field changes on SessionRecord/RunRecord/BudgetScope"
  artifacts:
    - path: "voss/harness/subagents.py"
      provides: "run_subagent extended with node + reserve kwargs and the D-03 always-finalize try/except boundary wrapping run_turn"
      contains: "except BudgetExceededError"
    - path: "voss/harness/session_tree.py"
      provides: "finalize_node(node, *, exit_reason, final, cwd) helper with _finalized double-finalize guard"
      contains: "def finalize_node"
    - path: "tests/harness/test_session_tree.py"
      provides: "TestDrainFinalize + TestNoOpenNodes covering REQ-3 and REQ-3b"
      contains: "class TestDrainFinalize"
  key_links:
    - from: "voss/harness/subagents.py run_subagent"
      to: "voss/harness/session_tree.py finalize_node"
      via: "D-03 single boundary: both the soft exit_reason=='budget' path and the except BudgetExceededError path call finalize_node"
      pattern: "finalize_node\\("
    - from: "voss/harness/subagents.py run_subagent"
      to: "run_turn token_budget"
      via: "reserve carved: token_budget = node.envelope['limit'] - reserve (RESEARCH Pitfall 7)"
      pattern: "token_budget="
    - from: "voss/harness/session_tree.py finalize_node"
      to: "node._finalized guard"
      via: "exactly-once finalize (RESEARCH Pitfall 1 / Assumption A1)"
      pattern: "_finalized"
---

<objective>
Wire the D-03 exception-at-single-boundary finalize into `voss/harness/subagents.py` — the one spawn chokepoint (`SPAWN_TOOL_NAME = "subagent_run"`) — so a budget-drained child ALWAYS finalizes exactly one terminal `RunRecord` with `exit_reason="budget"` and a closed tree node. This closes Leak 4 (stranded half-open child — ORCHESTRATION-PLAN §7 residual-risk register), the structural risk D-03 exists to eliminate.

This plan consumes the substrate built in O1-01. It adds the `finalize_node` helper (with the `_finalized` double-finalize guard) to `session_tree.py`, extends `run_subagent` with `node` + `reserve` kwargs and the `try/except BudgetExceededError` boundary wrapping the existing `run_turn` call, handles BOTH budget mechanisms (soft `result.run.exit_reason == "budget"` after a clean return AND hard `except BudgetExceededError` from compiled `.voss` ctx{}), and carves the reserve via `token_budget = envelope_limit - reserve`.

Purpose: O1's terminal-finalize guarantee (SPEC REQ-3) is the liveness half of the cage invariant ("Liveness guaranteed: reserved non-spendable drain budget" — ROADMAP O-track invariants). Without this boundary, an autonomous agent driven to budget exhaustion can strand a half-open node and create an audit gap.
Output: `voss/harness/subagents.py` (surgical modify), `voss/harness/session_tree.py` (add `finalize_node`), `tests/harness/test_session_tree.py` (add TestDrainFinalize + TestNoOpenNodes).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-SPEC.md
@.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-CONTEXT.md
@.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-RESEARCH.md
@.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-PATTERNS.md
@.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-VALIDATION.md
@.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-01-SUMMARY.md

<interfaces>
<!-- From O1-01 (this plan's dependency) + codebase. Use directly. -->

voss/harness/session_tree.py (built in O1-01):
- `SessionTreeNode` — fields `{id, root_id, parent_run_id, envelope, terminal_state, created_at, ended_at, rejected_raises}` + runtime `_budget` (BudgetScope) + `_finalized: bool` flag (already added in O1-01)
- `SessionTreeNode.create_root(*, cwd, limit)` / `SessionTreeManager(root, *, reserve, cwd)` / `async allocate_child(limit)`
- `_write_node_file(node, cwd) -> Path` ; `mutate_envelope(node, delta, cwd)` ; `BudgetCapRaiseError`, `BudgetAllocationError`
- `to_dict()` pops `_budget`

voss/harness/subagents.py (MODIFY — surgical, lines per O1-PATTERNS):
- `SPAWN_TOOL_NAME = "subagent_run"` (line 19)
- `async def run_subagent(*, agent_id, task, registry, cwd, renderer, provider, model, gate, cognition=None) -> str` (lines 76-87)
- existing body (lines 88-103): `spec = registry.get(agent_id)`; `if spec is None: return f"<error: unknown subagent {agent_id!r}>"`; `child_tools = make_toolset(cwd, renderer=renderer)`; `result = await run_turn(agent_task(spec, task), tools=child_tools, cwd=cwd, renderer=renderer, model=model, provider=provider, history=EpisodicMemory(capacity=20), permissions=gate, cognition=cognition)`; `return result.final`
- `attach_subagent_tool` (line 106) / inner `subagent_run` tool (line 121)

voss/harness/recorder.py (terminal record producer — read only):
- `RunRecorder.finalize(cwd, cost_usd, *, exit_reason=None) -> RunRecord` (line 192); validates exit_reason against EXIT_REASONS (line 134)

voss/harness/session.py (read only, DO NOT MODIFY):
- `EXIT_REASONS` includes `"budget"` (line 74) — terminal `exit_reason="budget"` needs NO schema change
- `_scan_dir` (line 216) globs flat `*.json` only — never sees the tree subdir; resume path unaffected

voss/harness/agent.py budget mechanisms (RESEARCH lines 41, 437-443 — read only, DO NOT MODIFY):
- `run_turn` SOFT token check exits cleanly with `result.run.exit_reason == "budget"` (does NOT raise)
- `BudgetExceededError` is the HARD path, raised only from compiled `.voss` ContextScope.ask()
- reserve: pass `token_budget = envelope_limit - reserve` to `run_turn`; `record_run_call` (post-loop LLM finalize) consumes the reserve tokens

tests/harness/test_subagent_recursion.py (MUST stay unmodified):
- asserts `"depth" not in params` and `"max_depth" not in params` on run_subagent; asserts no MAX_DEPTH/DEPTH_LIMIT/RECURSION_LIMIT module constant. Adding `node` + `reserve` kwargs is SAFE; adding any depth symbol is NOT.
</interfaces>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: Red tests for drain-finalize + no-open-nodes (Wave 0 for this plan)</name>
  <files>tests/harness/test_session_tree.py, voss/harness/session_tree.py</files>
  <read_first>
    - .planning/phases/O1-session-tree-substrate-budget-fan-out/O1-SPEC.md (REQ-3 + acceptance criteria 4,5)
    - .planning/phases/O1-session-tree-substrate-budget-fan-out/O1-RESEARCH.md (Pattern 3 boundary lines 248-304, Pitfall 1 double-finalize lines 387-395, Assumption A1)
    - .planning/phases/O1-session-tree-substrate-budget-fan-out/O1-PATTERNS.md (test class structure lines 274-356; EXIT_REASONS membership lines 440-450)
    - .planning/phases/O1-session-tree-substrate-budget-fan-out/O1-01-SUMMARY.md (what O1-01 delivered: SessionTreeNode incl. _finalized flag)
    - voss/harness/session_tree.py (the module from O1-01 — extend, do not rewrite)
    - voss/harness/recorder.py (RunRecorder.finalize signature line 192 — read only)
    - voss/harness/session.py (EXIT_REASONS line 74 — read only, DO NOT MODIFY)
    - tests/harness/test_recorder_iterations.py (RunRecorder test analog for finalize forwarding)
    - tests/harness/test_session_redaction.py (redaction invariant — read only, MUST stay unmodified)
  </read_first>
  <behavior>
    - TestDrainFinalize::test_finalize_sets_terminal_and_ended: finalize_node(node, exit_reason="budget", final="halted: budget", cwd=tmp_path) sets node.terminal_state to a dict containing exit_reason="budget" and final, populates node.ended_at, and rewrites the node file so the on-disk JSON reflects the closed state
    - TestDrainFinalize::test_finalize_is_idempotent: calling finalize_node twice on the same node finalizes exactly once — second call is a no-op; node.ended_at is unchanged between the two calls (the _finalized guard holds)
    - TestDrainFinalize::test_exit_reason_must_be_valid: finalize_node with an exit_reason not in EXIT_REASONS raises ValueError
    - TestNoOpenNodes::test_no_open_node_after_finalize: after allocating children and finalizing each via finalize_node, scanning the tree directory yields zero node files with terminal_state == None
  </behavior>
  <action>
    Extend `tests/harness/test_session_tree.py` with two new classes `TestDrainFinalize` and `TestNoOpenNodes` exactly per <behavior>. Import `finalize_node` from `voss.harness.session_tree`. Reuse the existing module imports and the autouse `tmp_path`/`isolated_state` fixture from `tests/harness/conftest.py`; do NOT add a conftest. For `test_no_open_node_after_finalize`, read every `*.json` under `.voss/sessions/<root_id>/`, `json.loads` each, and assert none has `terminal_state` is None after all are finalized. For `test_exit_reason_must_be_valid` use a string not in EXIT_REASONS (e.g. "quit").

    Then add a STUB `finalize_node` to `voss/harness/session_tree.py` so the import resolves but the new tests fail RED on behavior (a function that exists but does not set terminal_state / does not honor the guard / does not validate exit_reason yet). The existing O1-01 test classes (TestTreePersistence/TestBudgetFanOut/TestCapRaiseGuard/TestConcurrency/TestSchemaIsolation) MUST still pass — the stub must not regress them (do not let the new symbol break collection or the schema-isolation key set). This is the RED step for this plan's Wave 0. Commit message: `test(O1-02): add failing drain-finalize + no-open-node tests`. NEVER modify `tests/harness/test_session_redaction.py` or `tests/harness/test_subagent_recursion.py`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -m pytest "tests/harness/test_session_tree.py::TestDrainFinalize" "tests/harness/test_session_tree.py::TestNoOpenNodes" -q 2>&1 | grep -qE "failed|error" && python -m pytest tests/harness/test_session_tree.py -q -k "TreePersistence or BudgetFanOut or CapRaiseGuard or Concurrency or SchemaIsolation" && echo RED-NEW-GREEN-OLD</automated>
  </verify>
  <acceptance_criteria>
    - `TestDrainFinalize` and `TestNoOpenNodes` exist and fail RED (behavior unimplemented), proving tests precede the real finalize logic
    - All O1-01 test classes still pass green (stub did not regress them)
    - `git diff --stat tests/harness/test_session_redaction.py tests/harness/test_subagent_recursion.py` shows 0 changed lines in each
  </acceptance_criteria>
  <done>New drain/finalize tests exist and are RED; pre-existing substrate tests remain green.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2: Implement finalize_node guard + wire D-03 boundary into run_subagent — green</name>
  <files>voss/harness/session_tree.py, voss/harness/subagents.py</files>
  <read_first>
    - .planning/phases/O1-session-tree-substrate-budget-fan-out/O1-RESEARCH.md (Pattern 3 boundary lines 248-304, Pitfall 1/2/3/7, two-budget-mechanism finding lines 41 + 437-443, Open Questions 1-3 resolutions lines 651-664, resume-compat lines 597-617)
    - .planning/phases/O1-session-tree-substrate-budget-fan-out/O1-PATTERNS.md (subagents.py surgical-modify lines 161-219 incl. exact existing signature + body + the CRITICAL test_subagent_recursion constraint; EXIT_REASONS lines 440-450)
    - .planning/phases/O1-session-tree-substrate-budget-fan-out/O1-CONTEXT.md (D-03 + <specifics> interlock; resume Claude's-Discretion note)
    - voss/harness/subagents.py (the modify target — lines 19, 76-103, 106, 121)
    - voss/harness/session_tree.py (extend the finalize_node stub from Task 1 into the real guarded implementation)
    - voss/harness/recorder.py (RunRecorder.finalize(cwd, cost_usd, *, exit_reason=None) line 192 — read only)
    - voss/harness/session.py (EXIT_REASONS line 74; _scan_dir line 216 globs flat *.json only — read only, DO NOT MODIFY)
    - tests/harness/test_subagent_recursion.py (the pinning test — MUST pass unmodified; only node+reserve kwargs allowed)
    - tests/harness/test_session_redaction.py (redaction invariant — read only, MUST pass unmodified)
  </read_first>
  <action>
    Implement the real `finalize_node(node: SessionTreeNode, *, exit_reason: str, final: str = "", cwd: Path) -> None` in `voss/harness/session_tree.py`: FIRST check `node._finalized` — if already True, return immediately (idempotent, exactly-once — RESEARCH Pitfall 1 / Assumption A1; the check-and-set is safe under asyncio cooperative scheduling because there is no await between them). Validate `exit_reason` against `voss.harness.session.EXIT_REASONS` (raise `ValueError` if not a member, mirroring `RunRecorder` line 134 semantics) — import EXIT_REASONS from session.py, do not redefine it. Set `node.terminal_state = {"exit_reason": exit_reason, "final": final}`, set `node.ended_at = datetime.now(timezone.utc).isoformat(timespec="seconds")`, set `node._finalized = True`, then `_write_node_file(node, cwd)` to persist the closed state (D-01 second write — the close write). Do not touch `_budget`.

    Modify `voss/harness/subagents.py` `run_subagent` surgically per O1-PATTERNS lines 161-219:
    - Extend the signature: after `cognition: Any = None,` add `node: "SessionTreeNode | None" = None,` and `reserve: int = 0,`. Add the import for `finalize_node` (runtime) and `SessionTreeNode` (TYPE_CHECKING-guarded is acceptable for the annotation) from `voss.harness.session_tree`. Do NOT add `depth`, `max_depth`, `MAX_DEPTH`, `DEPTH_LIMIT`, or `RECURSION_LIMIT` (preserves `test_subagent_recursion.py`).
    - Keep the early guard OUTSIDE the boundary: `spec = registry.get(agent_id); if spec is None: return f"<error: unknown subagent {agent_id!r}>"` stays exactly as-is, before any try.
    - Compute `spendable = (node.envelope["limit"] - reserve) if node else None` (RESEARCH Pitfall 7: subtract reserve from the soft token budget; the composed `BudgetScope.token_limit` from O1-01 stays at the full `envelope["limit"]`).
    - Wrap from `run_turn` onward in the D-03 boundary. Enter the per-node `BudgetScope` via `async with node._budget` ONLY when `node and node._budget` (else no scope context — do not fabricate one for the no-node legacy path). Call the existing `run_turn(...)` unchanged EXCEPT add `token_budget=spendable` only when `node` is provided (legacy callers with `node=None` get the unchanged call — backward compatible).
    - SOFT path: after `run_turn` returns, if `node` and `result.run` and `result.run.exit_reason == "budget"` → `finalize_node(node, exit_reason="budget", final=result.final, cwd=cwd)`; elif `node` → `finalize_node(node, exit_reason="done", final=result.final, cwd=cwd)`. Then `return result.final`.
    - HARD path: `except BudgetExceededError:` → if `node`: `finalize_node(node, exit_reason="budget", final="<halted: budget>", cwd=cwd)`; `return "<halted: budget>"`. The two paths are mutually exclusive (run_turn either returns or raises) and the `_finalized` guard makes a double call a no-op anyway (RESEARCH Pitfall 1).
    - The `asyncio.Lock` from O1-01's `SessionTreeManager` is NOT held here — allocation already happened upstream; this boundary must not re-acquire or hold it across `run_turn` (RESEARCH Pitfall 3).

    Do NOT modify `session.py`, `recorder.py`, `voss_runtime/budget.py`, `agent.py`, or any persisted-record schema (REQ-5 redaction invariant; resume path unchanged — `_scan_dir` globs flat `*.json` and never sees the tree subdir, RESEARCH lines 597-617). No new third-party dependency. No fenced code in this action; follow RESEARCH Pattern 3 as the reference. Update `tests/harness/test_session_tree.py` only by turning the Task-1 RED classes green plus, if warranted, one end-to-end TestNoOpenNodes case that drives a stub-provider child to drain — do NOT weaken any existing assertion. Commit message: `feat(O1-02): D-03 always-finalize boundary in run_subagent`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -m pytest tests/harness/test_session_tree.py tests/harness/test_session_redaction.py tests/harness/test_subagent_recursion.py -q && test -z "$(git diff --stat voss/harness/session.py voss/harness/recorder.py voss_runtime/budget.py voss/harness/agent.py)" && python -m pytest tests/harness/ -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `python -m pytest tests/harness/test_session_tree.py -q` exits 0 with TestDrainFinalize + TestNoOpenNodes green (REQ-3, REQ-3b) and all O1-01 classes still green
    - `python -m pytest tests/harness/test_session_redaction.py tests/harness/test_subagent_recursion.py -q` exits 0 UNMODIFIED (`git diff --stat` on both = 0 changed lines)
    - `git diff --stat voss/harness/session.py voss/harness/recorder.py voss_runtime/budget.py voss/harness/agent.py` = empty (zero changed lines — REQ-5: no field add/remove on SessionRecord/RunRecord/BudgetScope; no agent.py budget edit)
    - `run_subagent` signature gains exactly `node` and `reserve`; `inspect.signature` shows no `depth`/`max_depth`; no MAX_DEPTH/DEPTH_LIMIT/RECURSION_LIMIT constant in subagents.py
    - Drain test: a child driven to budget exhaustion produces exactly one terminal node with `exit_reason="budget"`, `terminal_state` set, `ended_at` populated; second finalize is a no-op (idempotent)
    - `python -m pytest tests/harness/ -x -q` exits 0 (wave merge gate)
  </acceptance_criteria>
  <done>The D-03 boundary always finalizes a drained child exactly once; no open node survives parent teardown; all schema-lock and recursion-pin tests pass unmodified; full harness suite green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| child agent execution → terminal finalize | A child driven to budget exhaustion must always cross into a closed, recorded state (Leak 4 closure point) |
| run_subagent boundary → persisted node file | The single spawn chokepoint is where the audit record is sealed; a missed seal is an audit gap |
| budget exhaustion signal → exactly-once finalize | Two budget mechanisms (soft exit + hard exception) must not double-finalize |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-O1-07 | Repudiation | stranded half-open child node — no terminal record (Leak 4, ORCHESTRATION-PLAN §7) | mitigate | D-03 single-boundary always-finalize: both the soft `exit_reason=="budget"` path and `except BudgetExceededError` call `finalize_node`; `TestNoOpenNodes` asserts zero open nodes after teardown |
| T-O1-08 | Tampering | double-finalize corrupting the node file (terminal_state / ended_at overwritten) | mitigate | `_finalized` guard in `finalize_node` (check-and-set, no await between — atomic under asyncio); `TestDrainFinalize::test_finalize_is_idempotent` asserts second call is a no-op |
| T-O1-09 | Elevation of Privilege | child consuming the reserve so the terminal finalize call cannot complete (liveness break) | mitigate | reserve carved at the boundary: `token_budget = envelope_limit - reserve` to `run_turn`; the reserve covers the post-loop `record_run_call` finalize (RESEARCH Pitfall 7) |
| T-O1-10 | Tampering | redaction-invariant breach via subagents.py touching a persisted-record schema or agent.py budget path | mitigate | Surgical kwargs-only modify; acceptance gate asserts `git diff --stat` on session.py/recorder.py/budget.py/agent.py is empty; `test_session_redaction.py` passes unmodified (REQ-5) |
| T-O1-11 | Tampering | `node` kwarg accidentally introducing a depth symbol that breaks the recursion pin | mitigate | Only `node` + `reserve` kwargs added; acceptance asserts `test_subagent_recursion.py` passes unmodified and no depth/MAX_DEPTH symbol exists |
| T-O1-SC | Tampering | npm/pip/cargo installs | accept | O1 installs zero external packages (SPEC constraint "no new third-party dependencies"); stdlib + voss_runtime only — no Package Legitimacy Gate applicable |
</threat_model>

<verification>
- `python -m pytest tests/harness/test_session_tree.py -q` green incl. TestDrainFinalize + TestNoOpenNodes (REQ-3, REQ-3b)
- `python -m pytest tests/harness/test_session_redaction.py tests/harness/test_subagent_recursion.py -q` green and UNMODIFIED (REQ-5 + recursion pin)
- `git diff --stat voss/harness/session.py voss/harness/recorder.py voss_runtime/budget.py voss/harness/agent.py` = empty
- `python -m pytest tests/harness/ -x -q` green (wave merge + phase gate, per O1-VALIDATION sampling rate)
- Manual (non-blocking, O1-VALIDATION Manual-Only): run a root to mid-tree, kill, `voss resume`, confirm flat session loads and the tree dir is ignored by `_scan_dir`
</verification>

<success_criteria>
- `run_subagent` extended with `node` + `reserve` kwargs and a D-03 try/except boundary around `run_turn`
- Budget-drained child (soft OR hard path) always finalizes exactly one terminal `RunRecord` with `exit_reason="budget"` + closed node; idempotent under double signal
- No open node after parent teardown (REQ-3b)
- reserve honored: `run_turn` token_budget = envelope_limit - reserve; composed BudgetScope.token_limit unchanged
- Zero field/line changes on SessionRecord/RunRecord/BudgetScope/agent.py; `test_session_redaction.py` and `test_subagent_recursion.py` pass unmodified
- Full `tests/harness/` suite green
</success_criteria>

<output>
Create `.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-02-SUMMARY.md` when done
</output>
