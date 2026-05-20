---
phase: O3-board-state-machine
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/session.py
  - voss/harness/session_tree.py
  - voss/harness/board/__init__.py
  - voss/harness/board/verdict.py
  - voss/harness/board/errors.py
  - tests/harness/board/__init__.py
  - tests/harness/board/test_verdict.py
  - tests/harness/board/test_verdict_imports.py
  - tests/harness/board/test_session_tree_additive.py
  - tests/harness/test_session_redaction.py
autonomous: true
requirements:
  - OBRD-01
  - OBRD-07
user_setup: []
must_haves:
  truths:
    - "`SessionTreeNode` carries new `transitions: list[dict]` and `retry_notes: list[dict]` fields that round-trip through `_write_node_file` / `_hydrate_node`."
    - "`SessionTreeManager.get_node(node_id)` returns the live `SessionTreeNode` (root or child) or `None`."
    - "`EXIT_REASONS` contains `\"timeout\"` (additive, sorted) and `RunRecord` validates it without raising."
    - "`voss/harness/board/` is an importable package exposing `ReviewerVerdict`, `Reviewer`, `BoardWIPError`, `BoardGateError`, `BoardTimeoutError`."
    - "`voss/harness/board/verdict.py` imports only from `typing`, `dataclasses`, `__future__` — verified by AST walk."
  artifacts:
    - path: "voss/harness/board/__init__.py"
      provides: "Public package surface"
      exports: ["ReviewerVerdict", "Reviewer", "BoardWIPError", "BoardGateError", "BoardTimeoutError"]
    - path: "voss/harness/board/verdict.py"
      provides: "Frozen ReviewerVerdict + Reviewer Protocol (O4 plug-in contract)"
      contains: "@dataclass(frozen=True, slots=True)\nclass ReviewerVerdict"
    - path: "voss/harness/board/errors.py"
      provides: "BoardError / BoardWIPError / BoardGateError / BoardTimeoutError with .reason / .failing_clauses"
      contains: "class BoardWIPError"
    - path: "voss/harness/session_tree.py"
      provides: "Adds `transitions` + `retry_notes` fields on SessionTreeNode and `get_node()` on SessionTreeManager"
      contains: "def get_node"
    - path: "tests/harness/board/test_verdict_imports.py"
      provides: "AST import-set proof for O4 plug-in safety"
      contains: "ast.parse"
  key_links:
    - from: "voss/harness/board/__init__.py"
      to: "voss/harness/board/verdict.py"
      via: "re-export"
      pattern: "from \\.verdict import ReviewerVerdict, Reviewer"
    - from: "voss/harness/session_tree.py"
      to: "SessionTreeNode.transitions / retry_notes"
      via: "to_dict / _hydrate_node round-trip"
      pattern: "transitions.*list|retry_notes.*list"
    - from: "voss/harness/session.py"
      to: "EXIT_REASONS"
      via: "frozenset literal containing \"timeout\""
      pattern: "EXIT_REASONS.*timeout"
---

<objective>
Land the substrate edits O3 depends on: extend `SessionTreeNode` with two additive list fields (`transitions`, `retry_notes`), add `SessionTreeManager.get_node()`, extend `EXIT_REASONS` with `"timeout"`, and scaffold the `voss/harness/board/` package with its zero-deps `verdict.py` (frozen `ReviewerVerdict` + `Reviewer` Protocol) and `errors.py`. No state machine, no gates, no tick driver — only the additive surface every downstream O3 wave reads from.

Purpose: O3-02/03/04 cannot land without (a) a place on the session-tree node to store per-card transition + retry history, (b) a way to look up that node by id, (c) a terminal `exit_reason` for forced-timeout cards, and (d) the frozen verdict shape that satisfies SPEC L124's "zero transitive harness imports" rule (so O4's reviewers can import it without circular deps). This wave is intentionally tiny and safe so it can run first and fast.

Output: 5 edited/created source files + 3 new test files; full board test suite scaffold (`tests/harness/board/` package marker) ready for subsequent waves to populate.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/O3-board-state-machine/O3-SPEC.md
@.planning/phases/O3-board-state-machine/O3-CONTEXT.md
@.planning/phases/O3-board-state-machine/O3-RESEARCH.md
@.planning/phases/O1-session-tree-substrate-budget-fan-out/O1-SPEC.md
@voss/harness/session.py
@voss/harness/session_tree.py
@tests/harness/test_session_redaction.py

<interfaces>
<!-- Pre-existing surfaces this plan touches. -->

From voss/harness/session.py (lines 74-79):
```python
EXIT_REASONS: frozenset[str] = frozenset(
    {"done", "max-iter", "budget", "interrupt", "batch-invariant"}
)
```
`RunRecord.__post_init__` (line 142-148) raises `ValueError` if `exit_reason` is set and not in `EXIT_REASONS`.

From voss/harness/session_tree.py (lines 47-58):
```python
@dataclass
class SessionTreeNode:
    id: str
    root_id: str
    parent_run_id: Optional[str]
    envelope: dict
    terminal_state: Optional[dict]
    created_at: str
    ended_at: Optional[str]
    rejected_raises: list = field(default_factory=list)
```
Hydrator at line 86-89 filters incoming dict by `_NODE_FIELDS` (computed via `dataclasses.fields`) — adding new fields auto-extends the allowlist.
Writer at line 92-97 uses `node.to_dict()` (which is `asdict(self)` minus private members).

From voss/harness/session_tree.py (lines 139-178):
```python
class SessionTreeManager:
    def __init__(self, root_node, *, reserve, cwd) -> None:
        self._root = root_node
        ...
        self._children: list[SessionTreeNode] = []
    async def allocate_child(self, limit) -> SessionTreeNode: ...
```
No `get_node` method exists today. Adding one is purely additive.

From tests/harness/test_session_redaction.py — the redaction allowlist test that validates which fields are persisted on disk. Any new field on `SessionTreeNode` must be added to the allowlist here.
</interfaces>

<open-question id="R-04-EXIT_REASONS">
Per O3-RESEARCH.md §5/§11 R-04 and O3-CONTEXT.md: forced-timeout cards need a terminal `exit_reason` but `EXIT_REASONS` currently lacks `"timeout"`.

**Locked recommendation:** extend `EXIT_REASONS` to `frozenset({"done", "max-iter", "budget", "interrupt", "batch-invariant", "timeout"})`. Additive — preserves O1 SPEC-5 (no field changes; only allowlist growth). Resolves the audit-fidelity concern (BoardTransition.reason="timeout" maps 1:1 to terminal node).

**Fallback:** keep `EXIT_REASONS` unchanged; map forced-timeout cards to `exit_reason="budget"` and keep `reason="timeout"` only on the transition delta. Plan O3-04 must change `_force_terminal` accordingly.

**Escalate to checkpoint:decision** if executor finds an O1 test that asserts `EXIT_REASONS == {…}` exactly (grep first; current state is `frozenset({"done","max-iter","budget","interrupt","batch-invariant"})`). If no such pin exists, executor proceeds with the extension.
</open-question>

<open-question id="R-01-R-03-node-fields">
Per O3-RESEARCH.md §5 / §11 R-01 + R-03 and CONTEXT.md `<open_questions>` #5/#6/#7: where do `BoardTransition` deltas and `RetryNote` entries live?

**Locked recommendation:** add two list fields on `SessionTreeNode` — `transitions: list = field(default_factory=list)` and `retry_notes: list = field(default_factory=list)`. Both are additive; both persist via the existing `_write_node_file` writer; both are precedented by the existing `rejected_raises: list` field (line 56). Card "owns" its history; F1-ready.

**Fallback:** Board-side in-memory `dict[node_id, list[...]]`. Loses persistence; conflicts with "audit surface IS the UX" (ORCHESTRATION-PLAN §4.7). Only use if executor finds an O1 SPEC-5 violation argument.

**Escalate to checkpoint:decision** only if `test_session_redaction.py` cannot be updated to include the new fields in the allowlist (the existing fields `turns`/`runs` already carry user-typed text — the precedent is open).
</open-question>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Additive substrate edits — SessionTreeNode fields, get_node, EXIT_REASONS extension</name>
  <files>
    voss/harness/session.py,
    voss/harness/session_tree.py,
    tests/harness/board/__init__.py,
    tests/harness/board/test_session_tree_additive.py,
    tests/harness/test_session_redaction.py
  </files>
  <behavior>
    - Test 1 (test_session_tree_additive.py): `SessionTreeNode.create_root(cwd=tmp, limit=1000)` exposes `node.transitions == []` and `node.retry_notes == []`.
    - Test 2: append to both lists, call `_write_node_file(node, cwd)`, re-hydrate via reading the JSON + `_hydrate_node`; round-trip preserves both lists.
    - Test 3: `SessionTreeManager(root, reserve=0, cwd=tmp).get_node(root.id)` returns the root; `get_node("does-not-exist")` returns None; `get_node(child.id)` after an `allocate_child(...)` returns the child.
    - Test 4: `RunRecord(id="x", started_at="", ended_at="", exit_reason="timeout")` constructs without raising (i.e. `EXIT_REASONS` contains `"timeout"`).
    - Test 5 (assertion in test_session_redaction.py): the redaction allowlist accepts `transitions` and `retry_notes` fields without flagging them as PII leaks.
  </behavior>
  <action>
    Additive-only edits. Do NOT change field order of `SessionTreeNode` — append new fields after `rejected_raises` to preserve JSON key ordering on disk for pre-existing nodes.

    1. `voss/harness/session.py` line 78-79: replace the literal frozenset with
       `frozenset({"done", "max-iter", "budget", "interrupt", "batch-invariant", "timeout"})`.
       Leave the comment block above (T1-01 / T2-03 history) intact; add a one-line note
       referencing O3 OBRD-09 / R-04. Do not edit `RunRecord.__post_init__`.

    2. `voss/harness/session_tree.py` `SessionTreeNode` dataclass (line 47-58): append two
       fields **after** `rejected_raises`:
           `transitions: list = field(default_factory=list)`
           `retry_notes: list = field(default_factory=list)`
       Both are typed `list` (not `list[dict]`) to match the loose-typing of `rejected_raises`
       and to avoid a `from __future__ import annotations` cascade. Cite O3-RESEARCH.md §5
       and §1.4 in a docstring line above the additions.
       Do NOT touch `_NODE_FIELDS` — it is computed via `dataclasses.fields(SessionTreeNode)`
       at line 84 and auto-includes both new fields.
       Do NOT touch `_hydrate_node` — its `.setdefault("rejected_raises", [])` pattern handles
       old JSON files; add two analogous `kept.setdefault("transitions", [])` and
       `kept.setdefault("retry_notes", [])` lines for backwards-compatibility with pre-O3 node JSON.

    3. `voss/harness/session_tree.py` `SessionTreeManager` (line 139): add a new method
       (placement: directly after `__init__`, before `allocate_child`):
       ```
       def get_node(self, node_id: str) -> SessionTreeNode | None:
           """Lookup a node by id from root or children. Additive — preserves O1 SPEC-5."""
           if self._root.id == node_id:
               return self._root
           for child in self._children:
               if child.id == node_id:
                   return child
           return None
       ```
       Synchronous (no lock) — readers do not mutate; if a concurrent `allocate_child` races,
       the worst case is "child not yet visible", which matches Python's `list.append` semantics.

    4. Create `tests/harness/board/__init__.py` (empty file — package marker).

    5. Create `tests/harness/board/test_session_tree_additive.py` with the 4 tests in
       `<behavior>` above. Use `tmp_path` fixture (pytest builtin). For the async
       `allocate_child` test, use `pytest.mark.asyncio` (already in repo deps per
       `tests/harness/test_session_tree.py`).

    6. `tests/harness/test_session_redaction.py`: locate the field allowlist (grep for
       `transitions` / `retry_notes` first; if test already field-introspects via
       `dataclasses.fields`, no change is needed). If the test maintains an explicit
       allowlist set, add `"transitions"` and `"retry_notes"` with a one-line comment
       citing O3 OBRD-01 / OBRD-08. **DO NOT** weaken the redaction test — only extend
       the allowlist.

    depends_on_o2_symbol: none (this task is O2-independent).
    locked_decisions_touched: D-recommend-R-04 (EXIT_REASONS extension), D-recommend-R-01/R-03 (node-owned lists).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_session_tree_additive.py tests/harness/test_session_redaction.py -x -q</automated>
    <automated>.venv/bin/python -c "from voss.harness.session import EXIT_REASONS; assert 'timeout' in EXIT_REASONS, EXIT_REASONS"</automated>
    <automated>.venv/bin/python -c "from voss.harness.session_tree import SessionTreeNode, SessionTreeManager; import inspect; assert hasattr(SessionTreeManager, 'get_node'); assert {'transitions','retry_notes'}.issubset({f.name for f in __import__('dataclasses').fields(SessionTreeNode)})"</automated>
    <automated>grep -nE 'transitions|retry_notes' voss/harness/session_tree.py | grep -v '^#' | grep -c default_factory</automated>
    <automated>.venv/bin/python -m pytest tests/harness/test_session_tree.py -x -q</automated>
  </verify>
  <done>
    `EXIT_REASONS` contains `"timeout"`; `SessionTreeNode` has `transitions` + `retry_notes` list fields with default_factory; `SessionTreeManager.get_node()` exists; `_hydrate_node` is backwards-compatible with pre-O3 JSON; redaction test green; existing `test_session_tree.py` green (no regression in O1 substrate); new `test_session_tree_additive.py` green.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Board package scaffold — verdict.py, errors.py, __init__.py + zero-deps proof</name>
  <files>
    voss/harness/board/__init__.py,
    voss/harness/board/verdict.py,
    voss/harness/board/errors.py,
    tests/harness/board/test_verdict.py,
    tests/harness/board/test_verdict_imports.py
  </files>
  <behavior>
    - Test 1 (test_verdict.py): `ReviewerVerdict(conf=0.9, source="A", tier="fast", verdict="pass", notes="ok", evidence_refs=())` constructs; attempting `v.conf = 0.5` raises `FrozenInstanceError`; the class has exactly 6 fields (`{f.name for f in fields(ReviewerVerdict)} == {"conf","source","tier","verdict","notes","evidence_refs"}`).
    - Test 2 (test_verdict.py): `Reviewer` is a `Protocol`; it has exactly one method `review`; `isinstance(stub_obj_with_review_method, Reviewer)` is True (structural).
    - Test 3 (test_verdict_imports.py): AST-parse `voss/harness/board/verdict.py`; collect every `ast.Import` and `ast.ImportFrom` module name; assert the set ⊆ `{"typing","dataclasses","__future__"}`. Fail-loud with the offending import name if any other module is referenced.
    - Test 4 (test_verdict.py): `BoardWIPError("InProgress", 3)` carries `.column == "InProgress"`, `.cap == 3`; `BoardGateError("conf below p", ["conf"])` carries `.reason` and `.failing_clauses`; `BoardTimeoutError("timeout")` carries `.reason == "timeout"`. All three subclass `BoardError` which subclasses `Exception`.
    - Test 5 (test_verdict.py): `from voss.harness.board import Board, Card, Column` raises `ImportError` (those symbols don't exist yet — wave 2 lands them). The `__init__.py` currently exports only `ReviewerVerdict, Reviewer, BoardWIPError, BoardGateError, BoardTimeoutError`. Soften with `try/except ImportError: pytest.skip(...)` if wave 2 ships in parallel.
  </behavior>
  <action>
    Strict-perimeter file creation. The single hardest constraint here is the `verdict.py`
    import set — adding any new import to that file fails the plug-in contract that O4 reads.

    1. Create `voss/harness/board/__init__.py`:
       ```python
       """Voss board state machine package (O3).

       Public API:
           ReviewerVerdict, Reviewer   — O4 plug-in contract (verdict.py)
           BoardWIPError, BoardGateError, BoardTimeoutError — typed errors (errors.py)

       Symbols added in subsequent O3 waves (NOT exported here yet):
           Board, Card, Column         — O3-02 machine.py
       """
       from .verdict import ReviewerVerdict, Reviewer
       from .errors import BoardError, BoardWIPError, BoardGateError, BoardTimeoutError

       __all__ = [
           "ReviewerVerdict", "Reviewer",
           "BoardError", "BoardWIPError", "BoardGateError", "BoardTimeoutError",
       ]
       ```

    2. Create `voss/harness/board/verdict.py` — **EXACT content** below; any additional
       import (e.g. `from voss.harness.session_tree import ...`) breaks the O4 contract
       and fails the AST import-set test:
       ```python
       """O4 plug-in contract. ZERO transitive harness imports — verified by test.

       Adding any import beyond `typing`, `dataclasses`, `__future__` here breaks the
       contract that O4's Reviewer A/B impls can import this module without circular
       dependencies. See O3-SPEC.md acceptance L124.
       """
       from __future__ import annotations

       from dataclasses import dataclass
       from typing import Literal, Protocol


       @dataclass(frozen=True, slots=True)
       class ReviewerVerdict:
           """Frozen 6-field verdict shape (SPEC OBRD-07).

           Fields:
               conf:          [0.0, 1.0] confidence score from Reviewer B
               source:        which reviewer authored this verdict (A or B)
               tier:          B.fast at intermediate gates; B.strong at ->Done
               verdict:       pass | fail | block (block = abort lineage)
               notes:         reviewer-authored text; appended to retry_notes on fail
               evidence_refs: pointers (file:line, test names, eval refs)
           """
           conf: float
           source: Literal["A", "B"]
           tier: Literal["fast", "strong"]
           verdict: Literal["pass", "fail", "block"]
           notes: str
           evidence_refs: tuple[str, ...]


       class Reviewer(Protocol):
           """The injectable reviewer interface.

           O3 ships DeterministicReviewerStub in stub.py (planned in O3-03); O4 will
           ship Reviewer A + Reviewer B production impls. `card` is typed as `object`
           to keep this module zero-deps; concrete impls may use stricter typing.
           """
           def review(self, card: object) -> ReviewerVerdict: ...
       ```
       Note `card: object` not `card: "Card"` — see O3-RESEARCH.md §3.2 / A5. Quoted forward
       references to `Card` would also work but require zero-deps semantics anyway; plain
       `object` is documented and simpler.

    3. Create `voss/harness/board/errors.py`:
       ```python
       """Typed exceptions for the board state machine (O3).

       `BoardError` is the base; the three subclasses each carry a structured
       attribute the audit surface (O6) reads.
       """
       from __future__ import annotations


       class BoardError(Exception):
           """Base for all board-state-machine errors."""


       class BoardWIPError(BoardError):
           """Raised when a transition would exceed a destination column's WIP cap.

           Attrs:
               column: the destination column whose cap was exceeded
               cap:    the cap value
           """
           def __init__(self, column: str, cap: int) -> None:
               self.column = column
               self.cap = cap
               super().__init__(f"WIP cap exceeded for column {column!r}: cap={cap}")


       class BoardGateError(BoardError):
           """Raised when a transition is refused by a gate predicate or by an unknown column name.

           Attrs:
               reason:          short human-readable refusal reason
               failing_clauses: list of predicate `.name` strings that returned False
           """
           def __init__(self, reason: str, failing_clauses: list[str] | None = None) -> None:
               self.reason = reason
               self.failing_clauses = list(failing_clauses) if failing_clauses else []
               super().__init__(reason)


       class BoardTimeoutError(BoardError):
           """Raised when a card is forced terminal by deadline / budget / retry-ceiling.

           Attrs:
               reason: one of {"timeout", "budget", "retry_ceiling"}
           """
           def __init__(self, reason: str) -> None:
               self.reason = reason
               super().__init__(f"forced terminal: {reason}")
       ```

    4. Create `tests/harness/board/test_verdict.py` — tests 1, 2, 4, 5 above.
       Cover `ReviewerVerdict` frozen behavior, `Reviewer` Protocol shape, the
       three error classes with their structured attributes, and `__init__`
       public surface.

    5. Create `tests/harness/board/test_verdict_imports.py` — test 3 above. Use
       `ast.parse(Path("voss/harness/board/verdict.py").read_text())`; walk via
       `ast.walk`; for each `ast.Import` collect `n.name for n in node.names`; for
       each `ast.ImportFrom` collect `node.module` (handle `node.level` — `from .` is `None`).
       Assert collected ⊆ `{"typing", "dataclasses", "__future__"}`. Print the
       offending module names on failure. **This test is the load-bearing
       OBRD-07 acceptance** — keep it small and direct.

    depends_on_o2_symbol: none.
    locked_decisions_touched: `ReviewerVerdict` frozen 6-field shape, `Reviewer` Protocol,
    typed-error attributes (`.reason`, `.failing_clauses`), package surface only —
    no state machine yet.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_verdict.py tests/harness/board/test_verdict_imports.py -x -q</automated>
    <automated>.venv/bin/python -c "from voss.harness.board import ReviewerVerdict, Reviewer, BoardWIPError, BoardGateError, BoardTimeoutError; import dataclasses; assert dataclasses.is_dataclass(ReviewerVerdict); assert {f.name for f in dataclasses.fields(ReviewerVerdict)} == {'conf','source','tier','verdict','notes','evidence_refs'}"</automated>
    <automated>.venv/bin/python -c "import ast, pathlib; t=ast.parse(pathlib.Path('voss/harness/board/verdict.py').read_text()); mods=set(); [mods.add(n.name) for node in ast.walk(t) if isinstance(node, ast.Import) for n in node.names]; [mods.add(node.module) for node in ast.walk(t) if isinstance(node, ast.ImportFrom)]; assert mods <= {'typing','dataclasses','__future__'}, mods"</automated>
    <automated>grep -c 'from .verdict\|from .errors' voss/harness/board/__init__.py</automated>
    <automated>grep -cE '^(import|from) ' voss/harness/board/verdict.py</automated>
  </verify>
  <done>
    `voss/harness/board/` is an importable package; `verdict.py` has zero transitive harness imports (AST-verified); `ReviewerVerdict` is frozen with the 6 SPEC-locked fields; `Reviewer` Protocol has exactly one `review` method; all three error classes carry structured attributes for O6 audit; tests green.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| O4 (external phase) ↔ `voss/harness/board/verdict.py` | O4's Reviewer A/B impls import this file; any harness dep here creates a circular-import bomb at O4-execute time. The AST import-set test is the boundary enforcer. |
| Pre-O3 session JSON ↔ post-O3 `_hydrate_node` | Existing `.voss/sessions/*/<id>.json` files on disk lack `transitions` / `retry_notes` keys. Hydrator must tolerate them. |
| Test redaction allowlist ↔ new `SessionTreeNode` fields | `tests/harness/test_session_redaction.py` is the gate that prevents accidental PII leak via a new persisted field. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-O3-01-01 | Tampering | `voss/harness/board/verdict.py` import set | mitigate | AST-parsing test asserts imports ⊆ {typing, dataclasses, __future__}; fails CI if any harness import added. |
| T-O3-01-02 | Repudiation | Forced-timeout cards lack a terminal `exit_reason` | mitigate | `EXIT_REASONS` extended with `"timeout"`; `RunRecord.__post_init__` validation continues to enforce the allowlist. |
| T-O3-01-03 | Information Disclosure | New `transitions` / `retry_notes` fields could leak PII through `_write_node_file` | mitigate | `test_session_redaction.py` allowlist updated explicitly; fields named in audit log; reviewer-authored text only — same threat surface as existing `turns` / `runs`. |
| T-O3-01-04 | Tampering | Pre-O3 node JSON files round-trip after upgrade | mitigate | `_hydrate_node.setdefault("transitions", [])` + `setdefault("retry_notes", [])`; existing test_session_tree.py regression suite green. |
| T-O3-01-05 | Elevation of Privilege | `ReviewerVerdict` constructed outside the trusted reviewer injection | accept | Mitigated at O3-04 (Reviewer is constructor-injected; not module-global). This wave only ships the shape. |
</threat_model>

<verification>
**Per-task verification** (already declared inline):
- `.venv/bin/python -m pytest tests/harness/board/ tests/harness/test_session_redaction.py tests/harness/test_session_tree.py -x -q`

**Cross-task (plan-level):**
- AST-walk test on `verdict.py` is the SPEC L124 gate.
- No new fields exposed beyond `transitions` + `retry_notes` on `SessionTreeNode` (grep `dataclasses.fields(SessionTreeNode)` confirms 9 fields total post-edit: id, root_id, parent_run_id, envelope, terminal_state, created_at, ended_at, rejected_raises, transitions, retry_notes — count is 10; assert this in a one-liner).
- O1 substrate regressions:
  `.venv/bin/python -m pytest tests/harness/test_session_tree.py tests/harness/test_subagent_recursion.py -x -q`

**Manual (one-time):**
- Confirm `EXIT_REASONS` literal in `voss/harness/session.py` is a sorted, additive change (no removals).
</verification>

<success_criteria>
- All 14 SPEC acceptance checkboxes that this wave addresses: L117 (frozen dataclass + Protocol), L118 (DeterministicReviewerStub-ready — stub itself ships in O3-03), L124 (zero-deps verdict.py). OBRD-01 partial (substrate for transitions list); OBRD-07 (full).
- Package importable from anywhere in the harness without circular-dep errors.
- O1 substrate tests green; no regressions in `test_session_tree.py`, `test_session_redaction.py`, `test_subagent_recursion.py`.
- `EXIT_REASONS` now includes `"timeout"`.
- `SessionTreeManager.get_node()` exists and is unit-tested.
</success_criteria>

<output>
Create `.planning/phases/O3-board-state-machine/O3-01-SUMMARY.md` on completion. Include:
- Confirmation that `_hydrate_node` is backwards-compatible (proof: existing pre-O3 JSON files in `.voss/sessions/` hydrate without raising).
- Final import set of `verdict.py` (paste AST output).
- Field count of `SessionTreeNode` after the change.
- Test counts: total / pass / fail for both new test files + redaction + session_tree regression.
</output>
