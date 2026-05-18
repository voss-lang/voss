---
phase: O1-session-tree-substrate-budget-fan-out
plan: 01
type: tdd
wave: 1
depends_on: []
files_modified:
  - tests/harness/test_session_tree.py
  - voss/harness/session_tree.py
autonomous: true
requirements: [SPEC-1, SPEC-2, SPEC-4, SPEC-5]
must_haves:
  truths:
    - "Spawning N children from a parent yields N persisted node files, each with parent_run_id = parent id"
    - "The full tree is reconstructable from persisted node files alone (root_id + parent_run_id)"
    - "Allocation with sum(child limits) + reserve <= parent limit succeeds"
    - "Allocation that would exceed parent - reserve raises a hard error and creates no partial/child state"
    - "Concurrent child allocations cannot oversell the parent envelope (invariant holds under asyncio.gather)"
    - "A cap-raise (upward envelope delta) raises the documented error AND records the rejected attempt on the node"
    - "Normal spend within the cap is unaffected by the cap-raise recording"
    - "git diff shows zero field changes on SessionRecord, RunRecord, BudgetScope; test_session_redaction.py passes unmodified"
  artifacts:
    - path: "voss/harness/session_tree.py"
      provides: "SessionTreeNode dataclass, SessionTreeManager allocator, mutate_envelope guarded mutator, _write_node_file, BudgetCapRaiseError, BudgetAllocationError, _hydrate_node"
      min_lines: 120
      exports: ["SessionTreeNode", "SessionTreeManager", "BudgetCapRaiseError", "BudgetAllocationError"]
    - path: "tests/harness/test_session_tree.py"
      provides: "Class-based pytest covering REQ-1/2/4/5 + concurrency no-oversell + schema isolation"
      contains: "class TestTreePersistence"
  key_links:
    - from: "voss/harness/session_tree.py"
      to: "voss_runtime.BudgetScope"
      via: "composition (D-02) — node owns a BudgetScope instance, consumed unchanged"
      pattern: "from voss_runtime import BudgetScope"
    - from: "voss/harness/session_tree.py SessionTreeManager.allocate_child"
      to: "asyncio.Lock"
      via: "check-and-append guarded by self._lock (D-02 concurrency)"
      pattern: "async with self\\._lock"
    - from: "voss/harness/session_tree.py mutate_envelope"
      to: "node.rejected_raises + BudgetCapRaiseError"
      via: "D-04 single guarded mutator: upward delta records + raises"
      pattern: "rejected_raises\\.append"
---

<objective>
Build the O1 session-tree substrate as ONE coherent new harness-side module plus its red-then-green test scaffold. This plan delivers everything that does NOT require touching `subagents.py`: the `SessionTreeNode` dataclass (locked schema), the `SessionTreeManager` allocator with the `sum(children) + reserve <= parent` fan-out invariant guarded by an `asyncio.Lock`, the D-04 single guarded envelope mutator, the per-node file persistence at `.voss/sessions/<root_id>/<node_id>.json` (0o600, mirroring `session.save()`), and the new exception types.

The four CONTEXT decisions interlock as one substrate (CONTEXT <specifics>): this plan implements D-01 (per-node file), D-02 (composed BudgetScope + asyncio.Lock allocator), and D-04 (guarded mutator). D-03 (the exception-at-boundary finalize that WRITES the D-01 file from inside `subagents.py`) is wired in plan O1-02, which depends on this module.

Purpose: This is the keystone of the entire O-track (ORCHESTRATION-PLAN §9). Every O-phase O2–O6 renders off this substrate. The fan-out invariant IS the security boundary of the caged autonomous engineering team (ROADMAP cage invariant: "Budget = security boundary: hard, pre-committed, non-extendable by EM").
Output: `voss/harness/session_tree.py` (new), `tests/harness/test_session_tree.py` (new, class-based).
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

<interfaces>
<!-- Extracted from the codebase. Executor uses these directly — no exploration needed. -->

voss_runtime/budget.py (composed unchanged per D-02):
- `_current_budget: ContextVar[Optional[BudgetScope]]` (module-level, default None)
- `class BudgetScope` — fields incl. `token_limit: Optional[int] = None`, `name`, `tokens_so_far`
- `BudgetScope.__aenter__` → `self._token = _current_budget.set(self)`; `__aexit__` → `_current_budget.reset(self._token)`
- `BudgetScope.add_usage(*, tokens: int = 0, cost: float = 0.0) -> None` (no await — atomic under asyncio)
- `BudgetScope.check() -> None` — raises `BudgetExceededError` when `tokens_so_far > token_limit`
- `BudgetScope.__aenter__` raises `ValueError` if all of token_limit/latency_ms/cost_usd are None
- `BudgetExceededError` importable from `voss_runtime.exceptions` (and re-exported in `voss_runtime.__all__`)

voss/harness/session.py (analog for persistence + hydrate; DO NOT MODIFY):
- `_sessions_dir(cwd: Path) -> Path` (line 57) — the `.voss/sessions/` resolver
- `EXIT_REASONS: frozenset = {"done","max-iter","budget","interrupt","batch-invariant"}` (line 74) — `"budget"` already present
- `save()` pattern (lines 205-213): `path.parent.mkdir(parents=True, exist_ok=True)` → `path.write_text(json.dumps(asdict(record), indent=2))` → `path.chmod(0o600)`
- `_SESSION_FIELDS = {f.name for f in dataclasses.fields(SessionRecord)}` + `_hydrate` unknown-key-drop (lines 184-191)

voss/harness/recorder.py (analog for id + finalize, read-only this plan):
- `RunRecorder.start()` (lines 50-54) uses `uuid.uuid4().hex[:12]` + `datetime.now(timezone.utc).isoformat(timespec="seconds")`
</interfaces>
</context>

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: Red test scaffold for session-tree substrate (Wave 0)</name>
  <files>tests/harness/test_session_tree.py</files>
  <read_first>
    - .planning/phases/O1-session-tree-substrate-budget-fan-out/O1-SPEC.md (9 acceptance criteria)
    - .planning/phases/O1-session-tree-substrate-budget-fan-out/O1-VALIDATION.md (per-task verification map + Wave 0 requirements)
    - .planning/phases/O1-session-tree-substrate-budget-fan-out/O1-PATTERNS.md (test module header lines 229-270, class structure lines 274-356, schema-lock style lines 360-377)
    - tests/harness/test_recorder_iterations.py (primary test analog: class-based, tmp_path, no provider, no git)
    - tests/harness/test_session.py (tmp_path file-persistence + 0o600 assertion style)
    - tests/harness/test_session_redaction.py (schema-lock test style; this file MUST remain unmodified)
    - tests/harness/conftest.py (autouse isolated_state fixture — available automatically, do not redeclare)
  </read_first>
  <behavior>
    - TestTreePersistence: creating a root then allocating N children writes N node files under .voss/sessions/<root_id>/, each with parent_run_id == root id; tree reconstructable by reading the directory; node file mode is 0o600; node JSON parses
    - TestBudgetFanOut::test_valid_allocation: sum(child limits) + reserve <= parent limit → all allocations return SessionTreeNode
    - TestBudgetFanOut::test_oversell_raises: an allocation exceeding parent - reserve raises BudgetAllocationError AND the rejected child file does NOT exist AND _children length is unchanged (no partial state)
    - TestCapRaiseGuard::test_raise_errors: mutate_envelope with delta > 0 raises BudgetCapRaiseError
    - TestCapRaiseGuard::test_raise_recorded: after the rejected raise, node.rejected_raises has one entry with requested_delta and a timestamp, and the node file on disk reflects it
    - TestCapRaiseGuard::test_spend_unaffected: mutate_envelope with delta <= 0 updates envelope["spent"] and does NOT raise
    - TestConcurrency::test_concurrent_no_oversell: asyncio.gather of 10 concurrent allocate_child(100) against root limit 900 reserve 100 → exactly 8 SessionTreeNode successes, 2 BudgetAllocationError (no oversell)
    - TestSchemaIsolation::test_budget_not_serialized: SessionTreeNode.to_dict() (and the on-disk JSON) does NOT contain `_budget`
    - TestSchemaIsolation::test_node_keys_exact: node JSON top-level keys == {id, root_id, parent_run_id, envelope, terminal_state, created_at, ended_at, rejected_raises}
    - TestSchemaIsolation::test_no_schema_merge: no SessionTreeNode field name collides with the SessionRecord or RunRecord field sets (asserts the redaction invariant is not silently breached by a shared field)
  </behavior>
  <action>
    Create `tests/harness/test_session_tree.py` following the class-based pytest convention from `test_recorder_iterations.py`. Module docstring: O1 session-tree substrate; no provider, no git. Import `asyncio`, `json`, `stat`, `Path`, `pytest`, and from `voss.harness.session_tree` import `SessionTreeNode`, `SessionTreeManager`, `BudgetCapRaiseError`, `BudgetAllocationError`. Use the autouse `isolated_state`/`tmp_path` fixture from `tests/harness/conftest.py` (do NOT add a new conftest). Async tests use plain `async def` (no `@pytest.mark.asyncio` decorator — `asyncio_mode = "auto"` is active per pyproject.toml line 68). Implement exactly the test classes and methods listed in <behavior>: `TestTreePersistence`, `TestBudgetFanOut`, `TestCapRaiseGuard`, `TestConcurrency`, `TestSchemaIsolation`. The concurrency math: root limit 900, reserve 100 → spendable 800 → 8 of 10 children of size 100 succeed. Assert 0o600 via `stat.S_IMODE(path.stat().st_mode) == 0o600`. For `test_no_schema_merge`, import `SessionRecord` and `RunRecord` from `voss.harness.session` and assert the set of `dataclasses.fields(SessionTreeNode)` names is disjoint from the SessionRecord/RunRecord field-name sets. This is a RED scaffold: `voss/harness/session_tree.py` does not yet exist so collection or import will fail — that is the expected RED state for this Wave 0 task. Commit message: `test(O1-01): add failing session-tree substrate tests`. NEVER modify `tests/harness/test_session_redaction.py`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -m pytest tests/harness/test_session_tree.py -q 2>&1 | grep -qE "ModuleNotFoundError|ImportError|collected 0 items|error" && echo RED-OK</automated>
  </verify>
  <acceptance_criteria>
    - `python -m pytest tests/harness/test_session_tree.py -q` fails RED on missing `voss.harness.session_tree` import (collection error), proving tests exist before implementation
    - File defines exactly the 5 test classes named in <behavior>
    - `git diff --stat tests/harness/test_session_redaction.py` shows 0 changed lines
  </acceptance_criteria>
  <done>Red test scaffold exists; pytest fails on the missing implementation module, not on a test logic error.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2: Implement session_tree.py substrate (D-01 + D-02 + D-04) — green</name>
  <files>voss/harness/session_tree.py</files>
  <read_first>
    - .planning/phases/O1-session-tree-substrate-budget-fan-out/O1-RESEARCH.md (Pattern 1 node dataclass lines 159-202, Pattern 2 allocator+Lock lines 204-246, Pattern 4 guarded mutator lines 306-340, Pattern 5 node file write lines 342-355, Pitfall 1/3/4/6, Concurrency Deep-Dive lines 518-535, Serialization schema lines 544-593)
    - .planning/phases/O1-session-tree-substrate-budget-fan-out/O1-PATTERNS.md (imports lines 30-51, fixed-field dataclass lines 55-105, node-id lines 108-121, file persistence lines 124-145, asyncio.Lock lines 148-159, _hydrate lines 92-104)
    - .planning/phases/O1-session-tree-substrate-budget-fan-out/O1-CONTEXT.md (D-01/D-02/D-04 + <specifics> interlock note)
    - voss/harness/session.py (analog: dataclass + _sessions_dir line 57 + save() lines 205-213 + _hydrate lines 184-191 + EXIT_REASONS line 74 — DO NOT MODIFY)
    - voss/harness/recorder.py (analog: uuid.uuid4().hex[:12] + UTC timestamp lines 50-54 — read only)
    - voss_runtime/budget.py (BudgetScope composed unchanged per D-02 — read only, DO NOT MODIFY)
    - tests/harness/test_session_redaction.py (the redaction invariant this module must not breach — read only, MUST stay unmodified)
  </read_first>
  <action>
    Create `voss/harness/session_tree.py` with `from __future__ import annotations` and the import idiom from `session.py` lines 43-55 plus `import asyncio`, `from voss_runtime import BudgetScope`, and `from voss_runtime.exceptions import BudgetExceededError`.

    Define `BudgetAllocationError(Exception)` (raised on oversell) and `BudgetCapRaiseError(Exception)` (raised on upward envelope delta; carry `node_id`, `attempted_delta`, and a reason string in the message per RESEARCH Pattern 4).

    Define `@dataclass class SessionTreeNode` with the LOCKED logical schema exactly: `id: str`, `root_id: str`, `parent_run_id: Optional[str]`, `envelope: dict` (shape `{"limit": int, "spent": int}`), `terminal_state: Optional[dict]` (None = open), `created_at: str`, `ended_at: Optional[str]`, `rejected_raises: list` via `field(default_factory=list)`, and a runtime-only `_budget` via `field(default=None, init=False, repr=False)` that is a `BudgetScope` instance and is NEVER persisted. Add classmethod `create_root(cls, *, cwd: Path, limit: int) -> SessionTreeNode` using `uuid.uuid4().hex[:12]` for the id (root_id == id), `parent_run_id=None`, `envelope={"limit": limit, "spent": 0}`, `terminal_state=None`, UTC `created_at` via `datetime.now(timezone.utc).isoformat(timespec="seconds")`, `ended_at=None`. Add `to_dict(self) -> dict` that does `dataclasses.asdict(self)` then pops `_budget` (it must never reach `json.dumps`).

    Define module-level `_NODE_FIELDS = {f.name for f in dataclasses.fields(SessionTreeNode)}` and `_hydrate_node(data: dict) -> SessionTreeNode` mirroring `session.py` `_hydrate` lines 184-191: keep only known keys, `setdefault("rejected_raises", [])`, reconstruct (forward-compat so O6 can write extra keys that drop silently).

    Define `_write_node_file(node: SessionTreeNode, cwd: Path) -> Path` copying `session.py` save() lines 205-213 exactly but with path `cwd / ".voss" / "sessions" / node.root_id / f"{node.id}.json"`: `path.parent.mkdir(parents=True, exist_ok=True)`, `path.write_text(json.dumps(node.to_dict(), indent=2))`, `path.chmod(0o600)`, return path. This is the D-01 per-node file; written at open AND (in plan O1-02) at finalize.

    Define `mutate_envelope(node, delta: int, cwd: Path) -> None` as the D-04 SINGLE guarded mutator: if `delta > 0` (cap-raise attempt) append a record `{"attempted_at": <utc iso>, "requested_delta": delta, "reason": "cap_raise_rejected"}` to `node.rejected_raises`, call `_write_node_file` to persist the audit trail BEFORE raising, then `raise BudgetCapRaiseError(node.id, delta, "non-extendable cap")`; otherwise (`delta <= 0`, a spend/downward write) do `node.envelope["spent"] += abs(delta)` then `_write_node_file`. There is NO separate raise-cap API — this is the one funnel (D-04).

    Define `class SessionTreeManager` owning one tree's allocation state: `__init__(self, root_node, *, reserve: int, cwd: Path)` storing root, reserve, cwd, `self._children: list[SessionTreeNode] = []`, and `self._lock = asyncio.Lock()`. Define `async def allocate_child(self, limit: int) -> SessionTreeNode` per RESEARCH Pattern 2: `async with self._lock:` compute `allocated = sum(c.envelope["limit"] for c in self._children)`, `available = self._root.envelope["limit"] - self._reserve - allocated`; if `limit > available` raise `BudgetAllocationError` with a message naming limit/available/reserve and create NO node and append NOTHING (no partial state — REQ-2b); else create a `SessionTreeNode` (`uuid.uuid4().hex[:12]`, `root_id=self._root.id`, `parent_run_id=self._root.id`, envelope `{"limit": limit, "spent": 0}`, terminal_state None), append to `self._children`, `_write_node_file(child, self._cwd)` (crash-safe: written before use — Pitfall 4), and return it. The lock guards ONLY this check-and-append; it MUST NOT be held across any later `run_turn` (Pitfall 3 — that integration is plan O1-02). Compose the per-node `BudgetScope`: set `child._budget = BudgetScope(token_limit=limit, name=child.id)` (D-02, consumed unchanged; the runtime is not edited).

    Constraints to honor: do NOT add or alter any field on `SessionRecord`/`RunRecord`/`BudgetScope` (REQ-5 redaction invariant — this is a separate harness-side type at a separate path); no new third-party dependency (stdlib + voss_runtime only); `SessionTreeNode` must NEVER be appended to `SessionRecord.runs` or serialized via `session.save()`. Add a `_finalized: bool = field(default=False, init=False, repr=False)` flag now (consumed by O1-02's D-03 finalize to prevent double-finalize — RESEARCH Pitfall 1 / Assumption A1). Do NOT add `depth`, `max_depth`, `MAX_DEPTH`, `DEPTH_LIMIT`, or `RECURSION_LIMIT` anywhere (preserves `test_subagent_recursion.py`).

    No fenced code in this action; follow RESEARCH.md Patterns 1/2/4/5 as the reference implementations. Commit message: `feat(O1-01): session-tree substrate — node, allocator, guarded mutator`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -m pytest tests/harness/test_session_tree.py -q && python -m pytest tests/harness/test_session_redaction.py -q && python -c "import ast,sys; src=open('voss/harness/session_tree.py').read(); src=''.join(l for l in src.splitlines(keepends=True) if not l.lstrip().startswith('#')); sys.exit(0 if not any(t in src for t in ('max_depth','MAX_DEPTH','DEPTH_LIMIT','RECURSION_LIMIT')) else 1)"</automated>
  </verify>
  <acceptance_criteria>
    - `python -m pytest tests/harness/test_session_tree.py -q` exits 0 (all classes green: TestTreePersistence, TestBudgetFanOut, TestCapRaiseGuard, TestConcurrency, TestSchemaIsolation)
    - `python -m pytest tests/harness/test_session_redaction.py -q` exits 0 UNMODIFIED (`git diff --stat tests/harness/test_session_redaction.py` shows 0 changed lines)
    - `git diff --stat voss/harness/session.py voss/harness/recorder.py voss_runtime/budget.py` shows 0 changed lines (no field add/remove on SessionRecord/RunRecord/BudgetScope — REQ-5)
    - Concurrency test: 10 concurrent `allocate_child(100)` against limit 900 / reserve 100 yields exactly 8 successes + 2 `BudgetAllocationError` (no oversell — REQ-7)
    - No `depth`/`max_depth`/`MAX_DEPTH`/`DEPTH_LIMIT`/`RECURSION_LIMIT` token in non-comment source
    - `SessionTreeNode.to_dict()` excludes `_budget`; node JSON keys are exactly the locked schema set
  </acceptance_criteria>
  <done>The substrate module is green against all of its tests; the redaction invariant test passes unmodified; SessionRecord/RunRecord/BudgetScope schemas are byte-unchanged.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| parent agent → child node allocation | A parent (later: EM in O5) requests a child envelope; the allocator is the cage enforcement point |
| in-memory node state → persisted node file | Node JSON on disk is the audit product (ORCHESTRATION-PLAN: "the session-tree recorder IS the human review product") |
| envelope writes → guarded mutator | All envelope mutation funnels through `mutate_envelope` (D-04 single funnel) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-O1-01 | Tampering | `SessionTreeManager.allocate_child` budget oversell race | mitigate | `asyncio.Lock` wraps the check-and-append; concurrency test asserts 10 concurrent allocations against a 900/reserve-100 envelope yield exactly 8 successes (no oversell) — REQ-7 |
| T-O1-02 | Elevation of Privilege | `mutate_envelope` cap-raise bypass (autonomous agent escaping its cage — the core O-track security property) | mitigate | Single guarded mutator (D-04): any `delta > 0` raises `BudgetCapRaiseError` AND records the attempt; no alternate raise-cap API exists; `TestCapRaiseGuard` asserts raise + recorded audit entry |
| T-O1-03 | Information Disclosure | per-node file written with wrong permissions leaking session/task data | mitigate | `_write_node_file` calls `path.chmod(0o600)` mirroring `session.save()`; `TestTreePersistence` asserts `stat.S_IMODE == 0o600` |
| T-O1-04 | Tampering | `_budget` (BudgetScope runtime object) leaking into / corrupting the persisted JSON | mitigate | `to_dict()` pops `_budget`; `TestSchemaIsolation::test_budget_not_serialized` asserts it is absent from on-disk JSON |
| T-O1-05 | Information Disclosure | redaction invariant breach via accidental schema merge into SessionRecord/RunRecord | mitigate | `SessionTreeNode` is a separate harness-side type at a separate path; `TestSchemaIsolation::test_no_schema_merge` asserts field-name disjointness; `test_session_redaction.py` passes unmodified (REQ-5) |
| T-O1-06 | Tampering | node-file path traversal via user-controlled id | accept | Node id is `uuid.uuid4().hex[:12]` — no user-controlled path component; rationale matches RESEARCH Security Domain table |
| T-O1-SC | Tampering | npm/pip/cargo installs | accept | O1 installs zero external packages (SPEC constraint "no new third-party dependencies"); stdlib + voss_runtime only — no Package Legitimacy Gate applicable |
</threat_model>

<verification>
- `python -m pytest tests/harness/test_session_tree.py -q` green (REQ-1, REQ-2, REQ-4, REQ-7)
- `python -m pytest tests/harness/test_session_redaction.py -q` green and UNMODIFIED (REQ-5)
- `git diff --stat voss/harness/session.py voss/harness/recorder.py voss_runtime/budget.py tests/harness/test_session_redaction.py` = 0 changed lines
- `python -m pytest tests/harness/ -x -q` green (wave merge gate, per O1-VALIDATION sampling rate)
</verification>

<success_criteria>
- `voss/harness/session_tree.py` exists exporting SessionTreeNode, SessionTreeManager, BudgetCapRaiseError, BudgetAllocationError
- Fan-out invariant `sum(children) + reserve <= parent` enforced; oversell raises with no partial state; holds under concurrent allocation
- D-04 guarded mutator: upward delta raises + records; spend allowed
- Per-node files at `.voss/sessions/<root_id>/<node_id>.json`, 0o600, `_budget` never serialized
- Zero field changes on SessionRecord/RunRecord/BudgetScope; `test_session_redaction.py` passes unmodified
- `test_subagent_recursion.py` still passes (no depth/max_depth symbols introduced)
</success_criteria>

<output>
Create `.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-01-SUMMARY.md` when done
</output>
