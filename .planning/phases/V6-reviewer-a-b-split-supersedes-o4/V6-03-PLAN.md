---
phase: V6-reviewer-a-b-split-supersedes-o4
plan: 03
type: execute
wave: 2
depends_on: [V6-01, V6-02]
files_modified:
  - voss/harness/board/gates.py
  - voss/harness/board/machine.py
  - voss/harness/board/review_persistence.py
autonomous: true
requirements: [VREV-03, VREV-04, VREV-07, VREV-09]
must_haves:
  truths:
    - "A card reaches Done only if A's authored verification PASSES AND B's verdict == pass"
    - "A-verification failing refuses Done; B verdict != pass refuses Done"
    - "A B `block` verdict at the Done gate moves the card to Blocked (terminal), not a retry"
    - "Board accepts reviewer_a + reviewer_b; legacy single `reviewer` aliases both slots (back-compat)"
    - "A and B are each invoked at most once per move attempt (cached to separate verdict_a/verdict_b slots)"
    - "On Done or B-block, a .review.json sidecar is written (0o600) under the card's session-tree root dir"
  artifacts:
    - path: "voss/harness/board/gates.py"
      provides: "GateContext verdict_a/verdict_b/reviewer_a/reviewer_b slots + a_verification_passes + b_passes predicates wired into the (InReview,Done) tuples"
      contains: "verdict_a"
    - path: "voss/harness/board/machine.py"
      provides: "Board reviewer_a/reviewer_b slots + back-compat alias + B-block→Blocked seam + sidecar write calls"
      contains: "reviewer_a"
    - path: "voss/harness/board/review_persistence.py"
      provides: "_write_review_sidecar (0o600 .review.json mirror of _write_node_file)"
      contains: "review.json"
  key_links:
    - from: "voss/harness/board/machine.py"
      to: "voss/harness/board/gates.py"
      via: "GateContext constructed with reviewer_a/reviewer_b populated from board slots"
      pattern: "reviewer_a=self._reviewer_a"
    - from: "voss/harness/board/machine.py"
      to: "voss/harness/board/review_persistence.py"
      via: "_write_review_sidecar called on Done and on B-block paths"
      pattern: "_write_review_sidecar"
    - from: "voss/harness/board/gates.py"
      to: "voss/harness/board/verdict.py"
      via: "predicates read ctx.verdict_a.verdict / ctx.verdict_b.verdict"
      pattern: "\\.verdict == \"pass\""
---

<objective>
Wire Reviewer-A and Reviewer-B into the board Done gate as two genuinely independent gating sources, route a B `block` to Blocked, and persist the review artifacts as a `.review.json` sidecar (VREV-03/04/07/09). This is the core V6 delta: `GateContext` gains four defaulted slots, two new predicates extend the `(InReview,Done)` tuples, `Board` gains `reviewer_a`/`reviewer_b` with a back-compat `reviewer` alias, `Board.move()` gets the B-block detection seam, and a new `review_persistence._write_review_sidecar` mirrors `_write_node_file`.

Purpose: Realize the two-source Done gate the SPEC requires — A's authored verification PASS **and** B's verdict pass, both independent; B retains Residual-2 block authority; review outputs become durable and re-readable.
Output: `gates.py` (slots + predicates), `machine.py` (Board slots + B-block seam + sidecar calls), `review_persistence.py` (new helper).
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-SPEC.md
@.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-CONTEXT.md
@.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-PATTERNS.md
@.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-RESEARCH.md

<interfaces>
<!-- Extracted from V6-PATTERNS.md + V6-RESEARCH.md (read from source). Exact seams below. -->

gates.py GateContext (L44-56) — NOT frozen, mutable verdict slot for caching:
  card, node_envelope, team_ceiling, team_p_overrides, retry_ceiling, reserve, now,
  reviewer: Optional[Reviewer] = None, verdict: Optional[ReviewerVerdict] = None
  → ADD: reviewer_a, reviewer_b, verdict_a, verdict_b (all Optional, default None)

gates.py conf_meets_p predicate (L80-98) — the lazy-cache pattern to copy:
  if ctx.reviewer is None: return False
  if ctx.verdict is None: ctx.verdict = ctx.reviewer.review(ctx.card)
  return ctx.verdict.conf >= threshold

gates.py Done tuples (L145-146):
  _CODE_DONE_PREDICATES = (scope_clean(), conf_meets_p(), tests_pass())
  _AI_DONE_PREDICATES   = (scope_clean(), conf_meets_p(), eval_meets_threshold())
  registry: ("InReview","Done"): _CODE_DONE_PREDICATES  (L171); AI variant swapped by artifact introspection in Board.move

machine.py Board.__init__ (L238-263): keyword-only; `reviewer: Reviewer` (required) → self._reviewer
machine.py Board.from_team_config (L266-298): builds cls(...); passes reviewer through
machine.py Board.move (L336-425): builds GateContext (L379-388 + dry_run_gate L450-459); predicate loop → `if failing:` at L396-405 raises BoardGateError
machine.py _force_terminal (L515-537): dataclasses.replace(card, column="Blocked") + finalize_node(exit_reason); reason not in {timeout,budget} → "max-iter"
machine.py _append_delta (L467-493): node = self._manager.get_node(card.node_id); node.root_id available

session_tree.py _write_node_file (L97-102) — the 0o600 mirror target:
  path = cwd/".voss"/"sessions"/node.root_id/f"{node.id}.json"; mkdir parents; write_text(json.dumps(...,indent=2)); chmod(0o600)

Existing gate-predicate test file (regression target, NOT test_gates.py): tests/harness/board/test_gate_predicates_basic.py (also test_dry_run_gate.py, test_risk_thresholds.py)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: GateContext dual slots + A/B Done-gate predicates</name>
  <read_first>
    - voss/harness/board/gates.py (GateContext L44-56, conf_meets_p L80-98, Done tuples L145-146, registry L171)
    - V6-PATTERNS.md "gates.py" section (exact slot list, predicate class bodies, tuple extension)
    - voss/harness/board/verdict.py (ReviewerVerdict.verdict Literal — pass/fail/block)
    - tests/harness/board/test_two_source_gate.py (RED scaffold: two-source + back-compat assertions)
    - tests/harness/board/test_gate_predicates_basic.py (existing predicate-registry regression target)
  </read_first>
  <behavior>
    - a_verification_passes.evaluate returns True iff ctx.verdict_a.verdict == "pass" (calling reviewer_a at most once, caching to ctx.verdict_a); False when reviewer_a is None
    - b_passes.evaluate returns True iff ctx.verdict_b.verdict == "pass" (caching to ctx.verdict_b); "block" and "fail" both return False
    - Each reviewer is invoked at most once per GateContext (lazy-cache, no cross-move caching)
    - Adding the four GateContext slots does not break any existing GateContext(...) construction
  </behavior>
  <action>
    In `voss/harness/board/gates.py`:
    (1) Append four defaulted fields to `GateContext` after the existing `verdict` slot: `reviewer_a: Optional[Reviewer] = None`, `reviewer_b: Optional[Reviewer] = None`, `verdict_a: Optional[ReviewerVerdict] = None`, `verdict_b: Optional[ReviewerVerdict] = None`. All defaulted — existing constructions unaffected.
    (2) Add two predicate classes mirroring `conf_meets_p`'s lazy-cache shape (V6-PATTERNS gates.py section). `a_verification_passes` (`name = "reviewer_a"`): if `ctx.reviewer_a is None` return False; if `ctx.verdict_a is None` set `ctx.verdict_a = ctx.reviewer_a.review(ctx.card)`; return `ctx.verdict_a.verdict == "pass"`. `b_passes` (`name = "reviewer_b"`): same against `reviewer_b`/`verdict_b`, return `ctx.verdict_b.verdict == "pass"` (so "block" AND "fail" both yield False — block routing is handled in machine.py, NOT here; Pitfall 2). Exact class names are at Claude's discretion per D-02 but must match what the tests assert.
    (3) Extend the Done predicate tuples preserving cheap→expensive ordering (D-05): `_CODE_DONE_PREDICATES = (scope_clean(), a_verification_passes(), b_passes(), tests_pass())` and `_AI_DONE_PREDICATES = (scope_clean(), a_verification_passes(), b_passes(), eval_meets_threshold())`. Leave `("InProgress","InReview")` using the legacy `conf_meets_p` unchanged (Open Question 2 — only Done gets the two-source arms).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_two_source_gate.py::TestTwoSourceGate tests/harness/board/test_gate_predicates_basic.py tests/harness/board/test_dry_run_gate.py -x 2>&1 | tail -6</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'verdict_a\|verdict_b\|reviewer_a\|reviewer_b' voss/harness/board/gates.py` ≥ 4 (slots present)
    - gates.py contains two predicate classes that read `ctx.verdict_a.verdict == "pass"` and `ctx.verdict_b.verdict == "pass"` respectively
    - Neither new predicate references `_force_terminal` or a board instance (Pitfall 2 — predicates stay boolean)
    - Both `_CODE_DONE_PREDICATES` and `_AI_DONE_PREDICATES` include the A and B predicates in cheap→expensive order
    - `.venv/bin/python -m pytest tests/harness/board/test_gate_predicates_basic.py tests/harness/board/test_dry_run_gate.py -x` exits 0 (existing predicate tests, no regression)
  </acceptance_criteria>
  <done>GateContext has independent A/B reviewer+verdict slots; two boolean predicates gate Done on A-pass AND B-pass; existing predicate tests green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Board reviewer_a/reviewer_b slots + back-compat alias + GateContext wiring</name>
  <read_first>
    - voss/harness/board/machine.py (Board.__init__ L238-263, from_team_config L266-298, GateContext construction in move L379-388 + dry_run_gate L450-459)
    - V6-PATTERNS.md "machine.py" section (init signature change, alias fallback, GateContext kwargs)
    - voss/harness/board/gates.py (the new slots from Task 1)
    - tests/harness/board/test_two_source_gate.py::TestBoardSlotBackCompat (RED scaffold this satisfies)
    - tests/harness/board/test_reviewer_integration.py, tests/harness/board/test_stub_full_lifecycle.py (back-compat regression targets)
  </read_first>
  <behavior>
    - Board(..., reviewer_a=A, reviewer_b=B) stores distinct A and B slots
    - Board(..., reviewer=stub) (legacy alias) sets both _reviewer_a and _reviewer_b to stub (back-compat D-01)
    - The legacy _reviewer slot is preserved and still drives conf_meets_p at InProgress→InReview
    - GateContext built in move() (and dry_run_gate) carries reviewer_a/reviewer_b from the board slots; the legacy reviewer slot still populated
  </behavior>
  <action>
    In `voss/harness/board/machine.py`:
    (1) `Board.__init__`: make `reviewer` Optional (`reviewer: Optional[Reviewer] = None`), add keyword-only `reviewer_a: Optional[Reviewer] = None` and `reviewer_b: Optional[Reviewer] = None`. Store `self._reviewer = reviewer` (preserved for `conf_meets_p` at the intermediate gate), `self._reviewer_a = reviewer_a if reviewer_a is not None else reviewer`, `self._reviewer_b = reviewer_b if reviewer_b is not None else reviewer` (back-compat alias fallback, D-01).
    (2) `Board.from_team_config`: add pass-through `reviewer=None`, `reviewer_a=None`, `reviewer_b=None` params forwarding to `cls(...)`.
    (3) In `Board.move`, extend BOTH GateContext constructions (the gate eval at L379-388 and the `dry_run_gate` at L450-459) with `reviewer_a=self._reviewer_a` and `reviewer_b=self._reviewer_b` kwargs (keep the existing `reviewer=self._reviewer`).
    Do NOT add the B-block seam or sidecar calls here — that is Task 3. This task only adds the slots and wires them into GateContext.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_two_source_gate.py::TestBoardSlotBackCompat tests/harness/board/test_reviewer_integration.py tests/harness/board/test_stub_full_lifecycle.py -x 2>&1 | tail -6</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'self._reviewer_a\|self._reviewer_b' voss/harness/board/machine.py` ≥ 2
    - The alias fallback `reviewer_a if reviewer_a is not None else reviewer` (and the B equivalent) is present
    - `grep -c 'reviewer_a=self._reviewer_a' voss/harness/board/machine.py` ≥ 2 (both gate-eval and dry_run_gate GateContext constructions)
    - `.venv/bin/python -m pytest tests/harness/board/test_two_source_gate.py::TestBoardSlotBackCompat -x` exits 0 (legacy alias sets both slots)
    - `.venv/bin/python -m pytest tests/harness/board/test_reviewer_integration.py tests/harness/board/test_stub_full_lifecycle.py -x` exits 0 (existing single-reviewer flows still drive to Done)
  </acceptance_criteria>
  <done>Board takes reviewer_a/reviewer_b with a legacy reviewer alias; both gate contexts carry the A/B slots; existing single-reviewer board tests stay green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: B-block→Blocked seam + .review.json sidecar persistence</name>
  <read_first>
    - voss/harness/board/machine.py (Board.move `if failing:` branch L396-405, the all-pass/rebuild point after L405, _force_terminal L515-537, _append_delta L467-493 for the node.root_id lookup)
    - voss/harness/session_tree.py (_write_node_file L97-102 — the 0o600 mirror target)
    - V6-PATTERNS.md "review_persistence.py" + "machine.py" B-block/sidecar sections (exact helper body + seam placement)
    - V6-RESEARCH.md Pitfall 5 (skip sidecar on pure A-fail) + Pitfall 6 (root_id from node)
    - tests/harness/board/test_two_source_gate.py::TestBBlockAtGate, tests/harness/board/test_review_sidecar.py (RED scaffolds this satisfies)
  </read_first>
  <behavior>
    - A B verdict == "block" at the Done gate routes the card to column "Blocked" via _force_terminal(reason="retry_ceiling"); terminal exit_reason == "max-iter"
    - A plain A-fail or B-"fail" still raises BoardGateError (critic retry path) — only "block" is terminal-at-gate
    - On a successful Done (both verdicts present and pass) a <node_id>.review.json sidecar is written with mode 0o600 and keys a_verification, b_verdict, final_outcome
    - On B-block, a sidecar with final_outcome="Blocked" is written before _force_terminal returns
    - No sidecar is written on a pure A-fail where verdict_b was never populated (Pitfall 5)
  </behavior>
  <action>
    (1) Create `voss/harness/board/review_persistence.py` with `_write_review_sidecar(card, ctx, *, outcome, cwd, manager)` mirroring `_write_node_file` (V6-PATTERNS review_persistence.py section): fetch `node = manager.get_node(card.node_id)` (defensive return if None), build path `cwd/".voss"/"sessions"/node.root_id/f"{card.node_id}.review.json"`, assemble payload `{"a_verification": {test_path_or_rubric: verdict_a.evidence_refs[0] if present else None, result: verdict_a.verdict, notes: verdict_a.notes} or None, "b_verdict": dataclasses.asdict(verdict_b) or None, "final_outcome": outcome}`, `mkdir(parents=True, exist_ok=True)`, `write_text(json.dumps(payload, indent=2))`, `chmod(0o600)`. Internal JSON key names are at Claude's discretion (D-10) as long as A-verification, B-verdict-full, and final-outcome are all present and re-readable. Import only stdlib (`dataclasses`, `json`, `pathlib`). Do NOT import the board package at module top if it would create a cycle — type-hint with strings.
    (2) In `Board.move`'s `if failing:` branch, BEFORE the generic `_append_delta`+`raise BoardGateError`, add: if `ctx.verdict_b is not None and ctx.verdict_b.verdict == "block"`, call `_write_review_sidecar(card, ctx, outcome="Blocked", cwd=self._cwd, manager=self._manager)` then `return self._force_terminal(card, reason="retry_ceiling")` (D-03; Pitfall 2 — block routing lives here, not in the predicate). Otherwise fall through to the existing refuse path unchanged.
    (3) On the success path: at the point in `Board.move` where the Done transition passes and the card is rebuilt with the new column, when `transition == ("InReview","Done")` and BOTH `ctx.verdict_a is not None` and `ctx.verdict_b is not None`, call `_write_review_sidecar(card, ctx, outcome="Done", cwd=self._cwd, manager=self._manager)` before/at the rebuild. Guard on both verdicts present so a pure A-fail does not write a partial sidecar (Pitfall 5).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/board/test_review_sidecar.py tests/harness/board/test_two_source_gate.py -x 2>&1 | tail -8</automated>
  </verify>
  <acceptance_criteria>
    - `voss/harness/board/review_persistence.py` exists and `_write_review_sidecar` chmods the file to `0o600` and writes keys `a_verification`, `b_verdict`, `final_outcome`
    - `grep -q 'review.json' voss/harness/board/review_persistence.py` succeeds
    - `grep -q '_force_terminal(card, reason="retry_ceiling")' voss/harness/board/machine.py` succeeds AND it is gated on `ctx.verdict_b ... == "block"`
    - `grep -c '_write_review_sidecar' voss/harness/board/machine.py` ≥ 2 (Done path + Blocked path)
    - `.venv/bin/python -m pytest tests/harness/board/test_two_source_gate.py::TestBBlockAtGate -x` exits 0 (B-block → Blocked, exit_reason max-iter)
    - `.venv/bin/python -m pytest tests/harness/board/test_review_sidecar.py -x` exits 0 (sidecar exists, 0o600, three keys, re-readable)
  </acceptance_criteria>
  <done>B-block routes to Blocked at the gate; the .review.json sidecar persists A verification + B verdict + outcome (0o600) on Done and Blocked; pure A-fail writes no partial sidecar.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| LLM verdict JSON → board gate | Reviewer-B's parsed verdict drives terminal routing (block→Blocked); already parse-fail→block hardened upstream |
| board → filesystem (.voss/sessions/<root_id>/) | Sidecar path is built from node.root_id + card.node_id (internally generated session-tree IDs, not user/LLM-controlled) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V6-03-01 | Information Disclosure | .review.json on disk | mitigate | `chmod(0o600)` — user-only read/write, identical to the existing node-file permission model (V6-RESEARCH Security Domain) |
| T-V6-03-02 | Tampering | path traversal in sidecar path | accept | `root_id`/`node_id` are session-tree-generated IDs (not external input); same trust posture as `_write_node_file` which already uses them unescaped |
| T-V6-03-03 | Elevation of Privilege | B-block routing bypass | mitigate | Block detection in `Board.move()` after the predicate loop (not in a predicate); `b_passes` returns False for "block" so Done is refused, and the seam forces terminal — block cannot silently pass |
| T-V6-03-04 | Tampering | partial/overwriting sidecar on A-fail | mitigate | Sidecar written only when both verdict_a and verdict_b are present (Pitfall 5) — no partial overwrite on critic retry |
| T-V6-03-05 | Tampering | accidental field change to frozen records | mitigate | This plan touches only gates.py/machine.py/review_persistence.py; RunRecord/SessionRecord/BudgetScope untouched (verified in V6-05 git-diff gate) |
| T-V6-03-SC | Tampering | npm/pip/cargo installs | mitigate | Zero new dependencies; no install tasks |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/board/test_two_source_gate.py tests/harness/board/test_review_sidecar.py -x` exits 0.
- `.venv/bin/python -m pytest tests/harness/board/ -q` — full board suite green (no regression in O4 reviewer tests, critic loop, lifecycle, gates).
- A B-block card ends in column "Blocked" with terminal exit_reason "max-iter"; a both-pass card reaches Done and leaves a 0o600 `.review.json`.
</verification>

<success_criteria>
- Two-source Done gate: A verification PASS AND B verdict pass both required (VREV-03).
- B `block` → Blocked terminal at the gate (VREV-04); B stays EM-narrative-blind (unchanged reviewer_b.py).
- Board takes reviewer_a/reviewer_b with legacy alias (VREV-07).
- `.review.json` sidecar persists A verification + B verdict + outcome, 0o600, re-readable (VREV-09).
- A and B each reviewed at most once per move attempt.
- No frozen record schema touched.
</success_criteria>

<output>
Create `.planning/phases/V6-reviewer-a-b-split-supersedes-o4/V6-03-SUMMARY.md` when done.
</output>
