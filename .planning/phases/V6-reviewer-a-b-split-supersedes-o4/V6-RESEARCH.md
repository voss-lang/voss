# Phase V6: Reviewer A/B Split (supersedes O4) - Research

**Researched:** 2026-06-06
**Domain:** Board reviewer wiring delta — two-source Done gate, verdict domain field, review persistence, CLI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Done-gate composition (VREV-03/04/07)**
- D-01: `Board.__init__` / `from_team_config` gain `reviewer_a` + `reviewer_b` parameters. Keep the legacy `reviewer` parameter as an **optional back-compat alias** so existing O3/V5 construction and `DeterministicReviewerStub` keep working unchanged.
- D-02: Two separate gating sources at `InReview→Done`, two distinct predicates, each caching to **separate** `GateContext` slots (`verdict_a`, `verdict_b`) — not the single shared `ctx.verdict`. A's predicate passes when A's authored verification PASSES. B's predicate passes when B's verdict == `pass`. Both required.
- D-03: B `block` routes the card to **Blocked** via the existing terminal path (`_force_terminal` / `critic_step` block→terminal). A plain A-fail or B-`fail` follows the critic-loop retry path; only `block` is terminal-at-gate.
- D-04: B stays EM-narrative-blind. A and B see different context packets. Regression-protected.
- D-05: Reuse existing `gates.py` predicate registry shape. New A/B predicates extend the `("InReview","Done")` tuple.

**`ReviewerVerdict.domain_inferred` (VREV-06)**
- D-06: Add `domain_inferred: Literal["code","ai","docs","unknown"] = "unknown"` as a **7th, defaulted field** on `ReviewerVerdict` (`verdict.py`).
- D-07: B populates it (extend `_ReviewerBOutput` + `_to_verdict`). A defaults to `"unknown"` (may map `card.domain`→`"code"`/`"ai"` when trivially available).
- D-08: Preserve `verdict.py`'s **zero-transitive-harness-import contract**. `Literal` already imported — no new imports.

**Review-artifact persistence (VREV-09)**
- D-09: Per-card review sidecar at `.voss/sessions/<root_id>/<node_id>.review.json` (0o600). Do NOT add fields to `SessionTreeNode`.
- D-10: Sidecar payload: A's authored verification (test file path / rubric text + result), B's full verdict dict, final outcome (`Done` / `Blocked`). Written at gate-evaluation time. Mirror `_write_node_file` write/permission helper.

**`voss review <run_id>` CLI (VREV-10)**
- D-11: Mirror `voss board [root_id]` exactly. Click command in `AGENT_COMMANDS`. Read-only from persisted `.review.json` sidecars. `<run_id>` == root_id. Defaults to most-recent root dir under `.voss/sessions/` when omitted.
- D-12: Output per card: A's verification (test/rubric + result) + B's verdict (verdict/conf/tier/domain/evidence/notes) + final Done/Blocked. Plain text, ordered by card.
- D-13: Exit codes: `voss review` (no arg) → prints latest run, exits 0; unknown run_id → non-zero exit + stderr message.

**Verification / regression + supersession (VREV-05)**
- D-14: Verify-only of REV-01..05,07,08. Existing O4 reviewer tests regress green. Mark O4 superseded.
- D-15: `git diff` must show zero field changes on `RunRecord`/`SessionRecord`/`BudgetScope`.

### Claude's Discretion

- Exact predicate class names/shapes for the A and B Done-gate arms, and whether A/B run sequentially or the order within the `("InReview","Done")` tuple (cheap→expensive ordering preserved).
- Internal JSON key names within the `.review.json` sidecar.
- `voss review` text-rendering layout — match `voss board` house style.
- Test organization within `tests/harness/board/` conventions.
- Whether the sidecar is written by the board at gate time, by a small persistence helper, or both A and B contribute — as long as a single durable sidecar per card results.

### Deferred Ideas (OUT OF SCOPE)

- ADE reviewer-verdict panel rendering → V11.
- Reviewer calibration telemetry + slop-rejection spot-audit → V9 / O6 residual register.
- EM routing / card creation → V7.
- Board state-machine changes beyond reviewer wiring → V5 (closed).
- Recursive/multi-level reviewer fan-out → out of track.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VREV-03 | A's authored verification and B's verdict are both required at Done; A-fail refuses Done | Two-source predicate composition at `("InReview","Done")` in `gates.py` + `machine.py` |
| VREV-04 | B `block` sends card to Blocked; B stays EM-narrative-blind | `_force_terminal` / `critic_step` path already exists; `reviewer_b.py` structural isolation preserved |
| VREV-06 | `ReviewerVerdict` carries `domain_inferred ∈ {code,ai,docs,unknown}`; B populates, A defaults | 7th defaulted field on frozen dataclass; `_ReviewerBOutput` pydantic mirror extended |
| VREV-07 | Board takes `reviewer_a` + `reviewer_b`; back-compat legacy `reviewer` alias | `Board.__init__` / `from_team_config` parameter extension |
| VREV-09 | A's verification + B's verdict persist under the card's session-tree node | `.review.json` sidecar via mirrored `_write_node_file`; written at gate-evaluation time |
| VREV-10 | `voss review <run_id>` CLI; read-only from persisted review artifacts; unknown run → non-zero | Click command in `AGENT_COMMANDS`; no `voss board` precursor exists yet — use `sessions_cmd` as pattern |
| VREV-05 (verify) | REV-01..05,07,08 regress green; O4 superseded | 92 tests currently passing (1 pre-existing fail unrelated to V6); existing O4 tests regress green |
</phase_requirements>

---

## Summary

V6 is a wiring delta on shipped O4 code. All reviewer intelligence (`reviewer_a.py`, `reviewer_b.py`) is already implemented and tested. The work is connecting the two reviewers into the board as genuinely independent gating sources, extending `ReviewerVerdict` with one defaulted field, persisting the review artifacts as a sidecar JSON, and shipping a read-only CLI command.

**The critical finding is that `voss board` does NOT yet exist.** V5-CONTEXT.md specifies it as a deliverable, but V5 has not been executed — `AGENT_COMMANDS` in `cli.py` contains no `board` command and no `review` command. V6-CONTEXT.md D-11 says "mirror `voss board [root_id]` exactly (V5 precedent)" but V5 hasn't shipped yet. The planner must either (a) acknowledge that `voss review` will use `sessions_cmd` as its CLI pattern (the closest read-only-from-persisted command that does exist), or (b) plan V6 to ship its own discovery/render convention and leave `voss board` to V5. The V6 CONTEXT decision (D-11) is unambiguous: `voss review` is a V6 deliverable; the pattern to mirror is `sessions_cmd`, not a nonexistent `voss board`.

The current test suite has **one pre-existing failing test** (`test_exit_reasons_is_sorted_superset_of_pre_o3`) that asserts `EXIT_REASONS == {"done","max-iter","budget","interrupt","batch-invariant","timeout"}` but the actual set now also contains `"killed"` (added post-O3 for EM kill-flow). This is a pre-V6 regression unrelated to reviewer wiring — the planner should flag it and decide whether to fix it in V6 or carry it forward.

**Primary recommendation:** Implement in this order: (1) add `domain_inferred` to `ReviewerVerdict` and update `_ReviewerBOutput` + `_to_verdict`; (2) add `verdict_a`/`verdict_b` slots to `GateContext` and new predicates for the A and B Done-gate arms; (3) extend `Board.__init__` / `from_team_config` with `reviewer_a`/`reviewer_b` back-compat parameters; (4) wire the two-source gate + B-block→Blocked seam in `Board.move`; (5) implement the `.review.json` sidecar writer; (6) ship `voss review` CLI command.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Two-source Done gate composition | Board state machine (`machine.py`) | Gate predicate registry (`gates.py`) | `Board.move()` drives gate evaluation; predicates are the policy |
| Reviewer verdict caching (per move attempt) | Gate context (`gates.py` `GateContext`) | — | GateContext is the per-evaluation scratch pad; mutable by design |
| B `block` → Blocked routing | Board state machine (`machine.py`) | — | `_force_terminal` is the terminal routing seam; already handles `critic_step` block |
| `domain_inferred` field | Board-local `ReviewerVerdict` (`verdict.py`) | `reviewer_b.py` (populates) | verdict.py owns the data contract; B populates via `_ReviewerBOutput` |
| Review artifact persistence | Board state machine (written at gate time) | session_tree substrate (write helper) | Gate evaluation is the moment verdicts are known; sidecar mirrors `_write_node_file` |
| `voss review` CLI | CLI layer (`cli.py`) | — | Read-only from `.review.json` sidecars; no live Board constructed |

---

## Standard Stack

### Core (all already in the project — no new deps)

| Module | Version | Purpose | Why Standard |
|--------|---------|---------|--------------|
| `voss/harness/board/verdict.py` | shipped | `ReviewerVerdict` dataclass + `Reviewer` Protocol | Zero-dep plug-in contract; extend with 7th field |
| `voss/harness/board/gates.py` | shipped | `GateContext` + predicate registry | Add `verdict_a`/`verdict_b` slots + new predicates |
| `voss/harness/board/machine.py` | shipped | `Board`, `move()`, `_force_terminal` | Add `reviewer_a`/`reviewer_b` slots + two-source gate wiring |
| `voss/harness/board/reviewer_b.py` | shipped | `ReviewerB`, `_ReviewerBOutput`, `_to_verdict` | Extend pydantic mirror with `domain_inferred` |
| `voss/harness/session_tree.py` | shipped | `_write_node_file` (0o600 helper) | Mirror for `.review.json` sidecar write |
| `voss/harness/cli.py` | shipped | `sessions_cmd` pattern + `AGENT_COMMANDS` tuple | Pattern for `voss review` CLI registration |
| `click` | already dep | CLI command definition | Same pattern as all existing commands |
| `pydantic` | already dep | `_ReviewerBOutput` extension | Already used in `reviewer_b.py` |
| `dataclasses` | stdlib | `ReviewerVerdict` modification | Already used |

**No new third-party dependencies required.** [VERIFIED: codebase inspection]

### No Package Legitimacy Audit Required

V6 installs zero new packages. All dependencies are already present in the project. [VERIFIED: CONTEXT.md D-06, D-08; codebase inspection]

---

## Architecture Patterns

### System Architecture Diagram

```
Board.move("InReview", "Done")
        │
        ├─ [gate registry lookup] ─────────────────────────────────────────┐
        │   ("InReview","Done") → (scope_clean, conf_meets_b, a_pass, b_pass)
        │
        ├─ scope_clean.evaluate(ctx)  ─────────► pass?
        │
        ├─ a_verification_passes.evaluate(ctx) ─► calls ctx.reviewer_a.review(card)
        │   │                                     caches → ctx.verdict_a
        │   │   A-fail ──────────────────────────► raise BoardGateError (critic retry)
        │
        ├─ b_passes.evaluate(ctx) ──────────────► calls ctx.reviewer_b.review(card)
        │   │                                     caches → ctx.verdict_b
        │   │   B-fail ─────────────────────────► raise BoardGateError (critic retry)
        │   │   B-block ─────────────────────────► detect in Board.move → _force_terminal
        │
        ├─ all pass ──────────────────────────────► write .review.json sidecar
        │                                            emit transition delta
        │                                            finalize node (Done)
        └─ return new_card(column="Done")

.voss/sessions/<root_id>/
    <node_id>.json          ← existing node file (transitions[], envelope, etc.)
    <node_id>.review.json   ← NEW sidecar (A verification, B verdict, final outcome)

voss review [run_id]
    └─ reads .review.json sidecars (no live Board)
    └─ renders per-card A + B + final outcome
    └─ exits 0 (latest run) or non-zero (unknown run_id)
```

### Recommended Project Structure (delta files only)

```
voss/harness/board/
├── verdict.py          # +domain_inferred field (7th, defaulted)
├── gates.py            # +verdict_a/verdict_b on GateContext
│                       # +a_verification_passes predicate class
│                       # +b_passes predicate class
├── machine.py          # +reviewer_a/reviewer_b slots on Board
│                       # +two-source gate wiring in move()
│                       # +B-block→Blocked seam
│                       # +sidecar write call
├── reviewer_b.py       # +domain_inferred in _ReviewerBOutput + _to_verdict
└── review_persistence.py  (NEW: _write_review_sidecar helper — or inline in machine.py)

voss/harness/cli.py     # +review_cmd + AGENT_COMMANDS registration

tests/harness/board/
├── test_verdict.py                  # UPDATE: 6-field→7-field assertion
├── test_two_source_gate.py          # NEW: A/B two-source gate tests (VREV-03/04/07)
├── test_domain_inferred.py          # NEW: domain_inferred field tests (VREV-06)
├── test_review_sidecar.py           # NEW: sidecar persistence tests (VREV-09)
└── test_review_cli.py               # NEW: voss review CLI tests (VREV-10)
```

### Pattern 1: GateContext Dual Verdict Slots

`GateContext` currently has one mutable `verdict: Optional[ReviewerVerdict] = None` slot used by `conf_meets_p` for single-reviewer caching. The V6 extension adds two independent slots:

```python
# Source: direct inspection of voss/harness/board/gates.py
@dataclass
class GateContext:
    card: Card
    node_envelope: dict
    team_ceiling: TeamCeiling
    team_p_overrides: dict
    retry_ceiling: int
    reserve: int
    now: float
    reviewer: Optional[Reviewer] = None          # legacy single-slot (back-compat)
    verdict: Optional[ReviewerVerdict] = None    # legacy single cache (back-compat)
    reviewer_a: Optional[Reviewer] = None        # V6: A slot
    reviewer_b: Optional[Reviewer] = None        # V6: B slot
    verdict_a: Optional[ReviewerVerdict] = None  # V6: A cache
    verdict_b: Optional[ReviewerVerdict] = None  # V6: B cache
```

All new fields are defaulted — existing `GateContext` construction in tests and `machine.py` is unaffected. [VERIFIED: codebase inspection]

### Pattern 2: Two-Source Done Gate Predicates

The `_CODE_DONE_PREDICATES` tuple currently is `(scope_clean(), conf_meets_p(), tests_pass())`. V6 extends this with two new predicate classes that each cache to their own slot:

```python
# Conceptual shape (exact names at Claude's discretion per CONTEXT D-01)
class a_verification_passes:
    name = "reviewer_a"
    def evaluate(self, ctx: GateContext) -> bool:
        if ctx.reviewer_a is None:
            return False
        if ctx.verdict_a is None:
            ctx.verdict_a = ctx.reviewer_a.review(ctx.card)
        return ctx.verdict_a.verdict == "pass"

class b_passes:
    name = "reviewer_b"
    def evaluate(self, ctx: GateContext) -> bool:
        if ctx.reviewer_b is None:
            return False
        if ctx.verdict_b is None:
            ctx.verdict_b = ctx.reviewer_b.review(ctx.card)
        return ctx.verdict_b.verdict == "pass"  # "block" also returns False here
```

Note: `b_passes` returning `False` for `block` is correct — the `block`→Blocked routing is handled SEPARATELY in `Board.move()` (see Pitfall 3 below), not by the predicate itself.

### Pattern 3: B-block Detection in `Board.move()`

After the predicate loop completes and `failing` is non-empty, the `Board.move()` refusal path must check whether the B verdict is `block` — if so, route to `_force_terminal` instead of raising `BoardGateError`:

```python
# Conceptual — in Board.move(), after predicate evaluation
if failing:
    # Check for B-block before generic refuse.
    b_verdict = ctx.verdict_b
    if b_verdict is not None and b_verdict.verdict == "block":
        # D-03: B-block is terminal, not retry-able.
        new_card = self._force_terminal(card, reason="retry_ceiling")
        # sidecar write with outcome="Blocked"
        _write_review_sidecar(card, ctx, outcome="Blocked", cwd=self._cwd)
        return new_card  # caller sees Blocked card
    self._append_delta(...)
    raise BoardGateError("gate refused", failing_clauses=failing)
```

This is the cleanest seam: `_force_terminal` already handles Blocked routing + `finalize_node`. The sidecar is written before returning. [VERIFIED: machine.py inspection]

### Pattern 4: Back-compat `reviewer` Alias in `Board.__init__`

```python
def __init__(
    self,
    *,
    manager: SessionTreeManager,
    reviewer: Optional[Reviewer] = None,     # legacy alias
    reviewer_a: Optional[Reviewer] = None,   # V6
    reviewer_b: Optional[Reviewer] = None,   # V6
    cwd: Path,
    cfg: _BoardConfig,
    team_ceiling: TeamCeiling,
    root_node_id: str,
    clock: Callable[[], float] = time.monotonic,
    per_card_budget: int = 100_000,
    reserve: int = 0,
) -> None:
    # Back-compat: when only legacy `reviewer` is passed, both A and B use it.
    self._reviewer_a = reviewer_a if reviewer_a is not None else reviewer
    self._reviewer_b = reviewer_b if reviewer_b is not None else reviewer
    self._reviewer = reviewer  # preserve for conf_meets_p legacy call path
    ...
```

The legacy `conf_meets_p` predicate still uses `ctx.reviewer` (set from `self._reviewer`) for `InProgress→InReview` and any other non-Done transitions. The V6 A/B predicates use `ctx.reviewer_a` / `ctx.reviewer_b`. [VERIFIED: gates.py + machine.py inspection]

### Pattern 5: Sidecar Write — Mirror `_write_node_file`

```python
# Source: voss/harness/session_tree.py _write_node_file pattern
def _write_review_sidecar(
    card: Card,
    ctx: GateContext,
    *,
    outcome: str,  # "Done" | "Blocked"
    cwd: Path,
    a_verification: dict | None = None,  # test_path/rubric + result
) -> Path:
    node = ctx.card  # node_id is on card
    path = cwd / ".voss" / "sessions" / "<root_id>" / f"{card.node_id}.review.json"
    payload = {
        "a_verification": a_verification,
        "b_verdict": dataclasses.asdict(ctx.verdict_b) if ctx.verdict_b else None,
        "final_outcome": outcome,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
    path.chmod(0o600)
    return path
```

Root ID must come from the node file path (the board already knows `self._cwd`; root_id is encoded in the `SessionTreeNode.root_id` field accessible via `self._manager.get_node(card.node_id).root_id`). [VERIFIED: session_tree.py inspection]

### Pattern 6: `voss review` CLI — Mirror `sessions_cmd`

**CRITICAL FINDING: `voss board` does not exist.** V5 has not been executed yet. The closest read-only-from-persisted command is `sessions_cmd` (L2429 in cli.py). The planner must use `sessions_cmd` as the structural template for `voss review`, not a nonexistent `voss board`.

```python
# Pattern from sessions_cmd (L2429) adapted for voss review
@click.command("review")
@click.argument("run_id", required=False)
def review_cmd(run_id: str | None) -> None:
    """Show per-card A + B review for a run (latest if no run_id)."""
    cwd = Path.cwd()
    sessions_dir = cwd / ".voss" / "sessions"
    if run_id is None:
        run_id = _latest_root_id(sessions_dir)  # select by mtime
        if run_id is None:
            click.echo("(no review runs found)", err=True)
            raise SystemExit(1)
    sidecar_dir = sessions_dir / run_id
    if not sidecar_dir.is_dir():
        click.echo(f"unknown run_id: {run_id}", err=True)
        raise SystemExit(1)
    sidecars = sorted(sidecar_dir.glob("*.review.json"))
    if not sidecars:
        click.echo("(no review artifacts for this run)", err=True)
        # exits 0 — run exists, just no sidecars yet
        return
    for path in sidecars:
        data = json.loads(path.read_text())
        _render_review_card(data)  # renders A + B + outcome
```

Root discovery by mtime matches V5-CONTEXT D-11 (same convention referenced in V5 for `voss board`). [VERIFIED: V5-CONTEXT.md + cli.py inspection]

### Anti-Patterns to Avoid

- **Single-slot verdict caching for A+B**: do not reuse `ctx.verdict` for both reviewers. A and B must have separate cache slots so re-running one doesn't invalidate the other.
- **Predicate-level block routing**: do NOT route B-block to Blocked inside the `b_passes.evaluate()` predicate. That method must remain a boolean; terminal routing belongs in `Board.move()` after predicate evaluation.
- **Modifying `SessionTreeNode` schema**: the sidecar is a separate file beside the node file. Do not add `review` fields to `SessionTreeNode` (D-09).
- **Touching frozen schemas**: `RunRecord`, `SessionRecord`, `BudgetScope` must have zero field changes (D-15).
- **Calling reviewer from inside `GateContext` constructor**: reviewer calls must remain lazy (inside `evaluate()`) so they fire at most once per move attempt.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sidecar file write with 0o600 permissions | custom writer | Mirror `_write_node_file` | Already handles `mkdir -p`, JSON dump, `chmod 0o600` correctly |
| Reviewer sync/async bridge | custom thread pool | Existing pattern in `reviewer_a.py` + `reviewer_b.py` | Both already implement the same ThreadPoolExecutor bridge |
| CLI root discovery | custom ls/sort | Mirror `sessions_cmd` mtime sorting convention | Established pattern; `voss board` will use same convention when V5 ships |
| Predicate registry | custom dict | `Gates.build_default()` extension | 4-transition registry already defined; extend the `("InReview","Done")` tuple |

---

## Integration Question Answers

### Q1: Two-source Done gate composition

**Current shape:** `("InReview","Done")` maps to `_CODE_DONE_PREDICATES = (scope_clean(), conf_meets_p(), tests_pass())`. The AI variant is swapped in by `Board.move()` artifact introspection.

**V6 extension:** Add two new predicate instances to the Done tuples. The predicate ordering should be `(scope_clean, [A verification], [B passes], tests_pass/eval_meets_threshold)` to preserve cheap→expensive ordering (scope_clean is cheap; A runs a test/LLM call; B runs one `provider.complete()`; tests_pass reads an attribute).

**GateContext changes:** Add `reviewer_a`, `reviewer_b`, `verdict_a`, `verdict_b` as defaulted fields — all `Optional`, all `None`. `GateContext` is NOT frozen (`@dataclass` without `frozen=True`), so adding fields is clean.

**Board slot changes:** `Board.__init__` stores `self._reviewer_a` and `self._reviewer_b`. When `GateContext` is constructed in `Board.move()`, populate `ctx.reviewer_a` and `ctx.reviewer_b` from the board's slots. The legacy `ctx.reviewer` keeps its existing value so `conf_meets_p` (used on `InProgress→InReview`) still works unchanged.

**Back-compat with single `reviewer`:** When `reviewer` is passed alone (existing tests, `DeterministicReviewerStub`), both `self._reviewer_a` and `self._reviewer_b` fall back to `reviewer`. The Done gate predicate for A will call the stub; it returns whatever the stub returns. This means existing Done-gate tests that use the stub with `verdict="pass"` will still pass the new A predicate (`verdict == "pass"`). Existing tests that use the stub with `verdict="fail"` will now also fail the A predicate — this is correct behavior that was previously not enforced.

**Concrete impact on `test_stub_full_lifecycle.py`:** The stub has `verdict="pass"` by default. The test passes `DeterministicReviewerStub(conf=0.99, verdict="pass")` as `reviewer=`. The new A predicate checks `ctx.verdict_a.verdict == "pass"` — satisfied. The new B predicate checks `ctx.verdict_b.verdict == "pass"` — satisfied. No test changes required for this test. [VERIFIED: codebase inspection]

### Q2: B-block → Blocked routing

**The seam:** `Board.move()` at L397–405 (the `if failing:` branch). Currently raises `BoardGateError`. For a B-block verdict, the call path must instead invoke `self._force_terminal(card, reason="retry_ceiling")`.

**Exact location:** After the predicate loop:
```
if failing:
    if ctx.verdict_b is not None and ctx.verdict_b.verdict == "block":
        # Sidecar write (outcome="Blocked"), then force terminal.
        _write_review_sidecar(card, ctx, outcome="Blocked", cwd=self._cwd)
        return self._force_terminal(card, reason="retry_ceiling")
    self._append_delta(...)
    raise BoardGateError(...)
```

`_force_terminal` with `reason="retry_ceiling"` maps to `exit_reason="max-iter"` (line 535 of machine.py: `exit_reason = reason if reason in {"timeout", "budget"} else "max-iter"`). This is semantically correct for a block — the card is permanently terminated, not retryable.

**Why `critic_step` is NOT the seam for this path:** `critic_step` handles post-review verdict routing triggered by the EM loop (the external caller passing a verdict). The gate-detected B-block is different: it's triggered inside `Board.move()` itself when the gate evaluates a B-block verdict at the Done gate. The EM loop doesn't call `critic_step` in this scenario — the gate itself detects the block.

### Q3: `domain_inferred` additivity

**The frozen dataclass with slots:** `ReviewerVerdict` uses `@dataclass(frozen=True, slots=True)`. Adding a 7th defaulted field is valid Python and does NOT break existing positional or keyword construction.

**Positional construction impact:** The current 6-field shape means any positional construction `ReviewerVerdict(0.9, "A", "fast", "pass", "notes", ())` would break with a 7th field. Search results:
- `reviewer_a.py` `_verdict_from_test_exit()` (L71-78): keyword construction — safe.
- `reviewer_a.py` `_verdict_from_judge()` (L82-89): keyword construction — safe.
- `reviewer_a.py` exception fallback (L187-191): keyword construction — safe.
- `reviewer_b.py` `_to_verdict()` parse-fail branch (L159-165): keyword construction — safe.
- `reviewer_b.py` `_to_verdict()` success branch (L167-173): keyword construction — safe.
- `stub.py` `DeterministicReviewerStub.review()` (L24-32): keyword construction — safe.
- `test_verdict.py` `test_constructs_with_6_fields` (L20-28): keyword construction — safe.
- `test_verdict.py` `test_frozen` (L36-42): keyword construction — safe.
- `test_critic_loop.py` `_fail_verdict()` and `block_verdict` (L16-19, L113-117): keyword construction — safe.

**The one test that MUST be updated:** `test_verdict.py::TestReviewerVerdict::test_exactly_6_fields` (L44-46) asserts `names == {"conf", "source", "tier", "verdict", "notes", "evidence_refs"}`. This becomes a 7-field assertion after V6. This is the "intended, scoped edit to that contract" per CONTEXT D-08.

**Zero-import contract:** `Literal` is already imported in `verdict.py` (line 10: `from typing import Literal, Protocol, runtime_checkable`). Adding `domain_inferred: Literal["code","ai","docs","unknown"] = "unknown"` requires no new imports. [VERIFIED: verdict.py inspection]

### Q4: Review sidecar persistence

**Where written:** In `Board.move()` at the point where the gate evaluation concludes — either on the passing path (before emitting the passed transition delta) or on the B-block path (before calling `_force_terminal`). This ensures the sidecar is written exactly once per card review evaluation that produces both A and B verdicts.

**What writes it:** A small private helper function (e.g., `_write_review_sidecar`) that mirrors `_write_node_file`. It takes the card, the gate context (which carries `verdict_a` and `verdict_b`), an outcome string, and `cwd`. It writes to `cwd / ".voss" / "sessions" / root_id / f"{card.node_id}.review.json"`.

**Root ID lookup:** The board's `_manager.get_node(card.node_id)` returns the `SessionTreeNode`, which has `.root_id`. This is safe — the same lookup already happens in `_append_delta` (line 478-480 of machine.py).

**A's verification payload:** A's verdict carries `evidence_refs` with the test file path (code-card) or rubric identifier (AI-card), and `notes` contains the test output. The sidecar should record: `{"test_path_or_rubric": verdict_a.evidence_refs[0] if verdict_a.evidence_refs else None, "result": verdict_a.verdict, "notes": verdict_a.notes}`.

**Sidecar payload shape (keys at Claude's discretion per CONTEXT D-10):**
```json
{
  "a_verification": {
    "test_path_or_rubric": "a_test.py",
    "result": "pass",
    "notes": "...(test output)..."
  },
  "b_verdict": {
    "conf": 0.95,
    "source": "B",
    "tier": "strong",
    "verdict": "pass",
    "notes": "...",
    "evidence_refs": ["api.py:10"],
    "domain_inferred": "code"
  },
  "final_outcome": "Done"
}
```

**Re-readable without re-running:** `voss review` reads these files directly. No live Board or ReviewerB is constructed.

### Q5: `voss review` CLI

**`voss board` does not exist.** Confirmed by: (1) `AGENT_COMMANDS` tuple inspection — no `board_cmd` or `board` command; (2) `grep -n "board_cmd\|\"board\"\|'board'"` in cli.py returns no results. V5 is "ready for planning" per STATE.md but has not been executed.

**Actual pattern to mirror:** `sessions_cmd` at L2429:
- `@click.command("sessions")` → use `@click.command("review")`
- Read from persisted store (`.voss/sessions/`)
- No live manager or provider construction
- `click.echo` for output

**Latest-root discovery:** `sessions_cmd` uses `session_store.list_sessions()` which is for `SessionRecord` flat files, not the session tree. For `voss review`, the root discovery is different: list subdirectories of `.voss/sessions/`, sort by mtime (descending), pick first. This is the convention V5 CONTEXT specifies for `voss board` and which V6 D-11 says to mirror.

**run_id == root_id:** The root directory name under `.voss/sessions/` IS the root_id (confirmed by `_write_node_file`: `path = cwd / ".voss" / "sessions" / node.root_id / f"{node.id}.json"`).

**Exit-code convention:**
- `voss review` (no arg) → latest root → print sidecars → exit 0
- `voss review <run_id>` → print sidecars for that root → exit 0
- `voss review <unknown_run_id>` → `click.echo(f"unknown run_id: {run_id}", err=True)` → `raise SystemExit(1)`
- `voss review` (no arg, no sessions exist) → error + exit 1

**Registration:** Add `review_cmd` to `AGENT_COMMANDS` tuple in cli.py (alongside `sessions_cmd`).

### Q6: Regression surface

**Existing O4 reviewer tests (all must regress green):**
- `tests/harness/board/test_reviewer_a.py` — 5 test classes (ORVW-01/02/03/08/09); all keyword ReviewerVerdict construction, 0 6-field assertions. Safe after `domain_inferred` added.
- `tests/harness/board/test_reviewer_b.py` — 5 test classes (ORVW-04/05/06/07/09); 0 6-field field-count assertions. Safe.
- `tests/harness/board/test_reviewer_integration.py` — 1 test class; constructs Board with `reviewer=reviewer_b` (single slot). With the back-compat alias, `self._reviewer_b = reviewer_b` → the integration test's `reviewer_b` becomes the B-slot. The test's Done gate will now also invoke `self._reviewer_a` (which falls back to `reviewer_b` since no `reviewer_a` was passed). The stub-as-both-A-and-B will return `verdict="pass"` for both — test remains green.
- `tests/harness/board/test_stub.py` — `DeterministicReviewerStub` returns `ReviewerVerdict` keyword construction; safe.
- `tests/harness/board/test_stub_full_lifecycle.py` — uses `reviewer=stub` with `verdict="pass"`; back-compat alias routes to both A and B slots; both return pass; test green.
- `tests/harness/board/test_critic_loop.py` — uses `reviewer=stub` with `verdict="fail"` or `verdict="block"`; these tests DON'T drive to Done gate (they use `critic_step`); gate is not reached; safe.
- `tests/harness/board/test_verdict.py` — **ONE test must be updated**: `test_exactly_6_fields` (line 44-46).
- All other board tests (gate predicates, WIP, columns, lifecycle, tick, etc.) use `reviewer=stub`; none assert the 6-field shape.

**Pre-existing failing test (unrelated to V6):**
`tests/harness/board/test_session_tree_additive.py::TestExitReasonsExtension::test_exit_reasons_is_sorted_superset_of_pre_o3` asserts `EXIT_REASONS == {"done","max-iter","budget","interrupt","batch-invariant","timeout"}` but EXIT_REASONS currently also contains `"killed"` (added by O5 for EM kill-flow). This test is failing before V6 starts. The planner should flag this as a pre-existing regression to be fixed in the first V6 plan (it's a one-line test fix — update the expected set to include `"killed"`).

**Test invocation command:**
```bash
.venv/bin/python -m pytest tests/harness/board/ -q
```

**Current baseline:** 92 passed, 1 failed (pre-existing, unrelated).

---

## Common Pitfalls

### Pitfall 1: `voss board` Does Not Exist — CLI Pattern Selection

**What goes wrong:** Planner references V5's `voss board` as the template for `voss review` and tries to import a `board_cmd` function that doesn't exist.

**Why it happens:** V6-CONTEXT D-11 says "Mirror `voss board [root_id]` exactly (V5 precedent, `cli.py`)." V5 has not been executed.

**How to avoid:** Use `sessions_cmd` (L2429) as the structural template. The data source is different (`.review.json` sidecars vs `SessionRecord` flat files), but the click command shape, error handling, and exit code convention are identical.

**Warning signs:** Any plan that imports `board_cmd` from `cli.py` or references `inspect_group.command("board")`.

### Pitfall 2: B-block Detected Inside Predicate, Not at `Board.move()` Level

**What goes wrong:** The `b_passes` predicate class attempts to call `self._force_terminal` when it detects `block`, but predicates don't have access to the board instance. The board state is not mutated correctly.

**Why it happens:** It seems elegant to handle block inside the predicate — but predicates are stateless objects; they return `bool` and write to `GateContext` only.

**How to avoid:** Keep predicates boolean. Block detection happens in `Board.move()` after the predicate loop, by inspecting `ctx.verdict_b.verdict`.

**Warning signs:** A predicate class with `self._board` or `self._force_terminal` reference.

### Pitfall 3: B Verdicts from Both A-slot and B-slot on Legacy Single-Reviewer Construction

**What goes wrong:** When the legacy `reviewer` argument is used (e.g., in existing tests), both `self._reviewer_a` and `self._reviewer_b` point to the same stub. At the Done gate, the A predicate calls `stub.review()` (caches `verdict_a = stub_verdict`) and the B predicate also calls `stub.review()` (caches `verdict_b = stub_verdict`). This is correct — but if the stub has `verdict="fail"`, the A predicate fails AND the B predicate fails. Tests that use `DeterministicReviewerStub(conf=0.99, verdict="fail")` and drive to Done will now fail at the A arm too, not just conf. This is the intended behavior. Just be aware the two-source gate applies even for the legacy single-slot.

**How to avoid:** This is not a bug — it's correct. But test authors need to know: if a test expects Done to be refused for a particular reason, both A and B verdicts from the stub will be evaluated.

### Pitfall 4: `domain_inferred` Slots Annotation on Frozen Slots Dataclass

**What goes wrong:** Adding `domain_inferred` to `@dataclass(frozen=True, slots=True)` requires the field to appear AFTER all non-defaulted fields in the class definition (Python dataclass ordering rule). If placed before any non-defaulted field, Python raises `TypeError: non-default argument follows default argument`.

**How to avoid:** Place `domain_inferred: Literal["code","ai","docs","unknown"] = "unknown"` as the LAST field in `ReviewerVerdict`. The current 6 fields (`conf`, `source`, `tier`, `verdict`, `notes`, `evidence_refs`) have no defaults, so a defaulted 7th field at the end is valid.

**Warning signs:** `TypeError: non-default argument` during test collection.

### Pitfall 5: Sidecar Written on Refused Transitions (A-fail or B-fail)

**What goes wrong:** The sidecar is written on every gate evaluation, including A-fail or B-fail that result in a critic retry. This overwrites any prior partial sidecar from an earlier review attempt.

**How to avoid:** Write the sidecar only when BOTH A and B have been evaluated (i.e., both `ctx.verdict_a` and `ctx.verdict_b` are populated). On A-fail, `verdict_b` may be None (B wasn't called yet). Write only when both are present — either on the passing path (both called, both pass) or on the B-block path (both called, B blocks). On a pure A-fail, skip the sidecar write (the critic retry will re-evaluate next time).

**Alternatively:** Always write when at least B is known; mark `a_verification` as null when A didn't run. The CONTEXT only requires that after a reviewed card, A verification + B verdict are readable — the "after" implies the final evaluation.

### Pitfall 6: Root ID Missing When Writing Sidecar

**What goes wrong:** `_write_review_sidecar` needs the `root_id` to construct the sidecar path, but `card` only has `node_id`. The `root_id` is on the `SessionTreeNode`.

**How to avoid:** Fetch the node: `node = self._manager.get_node(card.node_id)` — the board already does this at line 376 of `machine.py` before gate evaluation. Reuse the same `node` reference (already fetched into local variable `node` in `Board.move()`).

### Pitfall 7: `test_exactly_6_fields` Must Be Updated (Not Deleted)

**What goes wrong:** The test pinning the 6-field shape is the OBRD-07 acceptance test; deleting it removes the field-count invariant entirely.

**How to avoid:** Update it to assert `names == {"conf", "source", "tier", "verdict", "notes", "evidence_refs", "domain_inferred"}`. This is the "one intended, scoped edit" per CONTEXT D-08.

---

## Code Examples

### Example 1: `domain_inferred` Addition to `ReviewerVerdict`

```python
# Source: direct inspection of voss/harness/board/verdict.py (current shape)
# V6 change: add domain_inferred as 7th field with default
@dataclass(frozen=True, slots=True)
class ReviewerVerdict:
    conf: float
    source: Literal["A", "B"]
    tier: Literal["fast", "strong"]
    verdict: Literal["pass", "fail", "block"]
    notes: str
    evidence_refs: tuple[str, ...]
    domain_inferred: Literal["code", "ai", "docs", "unknown"] = "unknown"  # V6 addition
```

### Example 2: `_ReviewerBOutput` Extension

```python
# Source: direct inspection of voss/harness/board/reviewer_b.py
# V6 change: add domain_inferred to pydantic mirror
class _ReviewerBOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    conf: float
    verdict: Literal["pass", "fail", "block"]
    notes: str
    evidence_refs: list[str] = []
    domain_inferred: str = "unknown"  # B infers; clamped in _to_verdict

# _to_verdict extension:
_ALLOWED_DOMAINS = frozenset({"code", "ai", "docs", "unknown"})

@staticmethod
def _to_verdict(resp, tier):
    parsed = resp.parsed
    if parsed is None:
        return ReviewerVerdict(conf=0.0, source="B", tier=tier,
                               verdict="block", notes="structured output was None",
                               evidence_refs=())
    domain = parsed.domain_inferred if parsed.domain_inferred in _ALLOWED_DOMAINS else "unknown"
    return ReviewerVerdict(
        conf=float(parsed.conf), source="B", tier=tier,
        verdict=parsed.verdict, notes=parsed.notes,
        evidence_refs=tuple(parsed.evidence_refs),
        domain_inferred=domain,
    )
```

### Example 3: `_write_node_file` (existing — mirror this)

```python
# Source: voss/harness/session_tree.py L97-102
def _write_node_file(node: SessionTreeNode, cwd: Path) -> Path:
    path = cwd / ".voss" / "sessions" / node.root_id / f"{node.id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(node.to_dict(), indent=2))
    path.chmod(0o600)
    return path
```

### Example 4: Latest-Root Discovery Pattern (for CLI)

```python
# Pattern for _latest_root_id() in review_cmd
def _latest_root_id(sessions_dir: Path) -> str | None:
    roots = [d for d in sessions_dir.iterdir() if d.is_dir()]
    if not roots:
        return None
    return max(roots, key=lambda d: d.stat().st_mtime).name
```

---

## Runtime State Inventory

This section does not apply — V6 is a pure code/wiring delta on the board and CLI. No rename/refactor/migration phase. No stored data, live service config, OS-registered state, secrets, or build artifacts require update.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single `reviewer` slot on Board (O3) | Two independent `reviewer_a` + `reviewer_b` slots with back-compat alias (V6) | V6 | A and B are now genuinely independent gating sources |
| 6-field frozen `ReviewerVerdict` | 7-field with `domain_inferred` defaulted (V6) | V6 | Additive; all existing construction unaffected |
| No review artifact persistence | `.review.json` sidecar per card at gate time (V6) | V6 | Review artifacts are durable and re-readable |
| No `voss review` CLI | `voss review [run_id]` read-only from sidecars (V6) | V6 | Review outcomes inspectable without re-running |
| Single reviewer called once at Done (O3/V5) | A verification AND B verdict both required at Done (V6) | V6 | Self-Done guard is now two genuine independent sources |

**Deprecated / outdated:**
- Single `ctx.verdict` caching: still used for `conf_meets_p` at `InProgress→InReview` but supplemented by `ctx.verdict_a` / `ctx.verdict_b` at Done. Not removed for back-compat.
- Single `reviewer` parameter on `Board`: not removed — back-compat alias. Deprecated semantically (new code passes `reviewer_a`/`reviewer_b`).

---

## Open Questions

1. **Should V6 also ship `voss board`?**
   - What we know: V5 has not been executed; V5 is the specified source of `voss board`; V6-CONTEXT D-11 says to mirror it.
   - What's unclear: Should V6 ship a minimal `voss board` to satisfy D-11's reference, or should it accept that `sessions_cmd` is the pattern and ship only `voss review`?
   - Recommendation: Ship only `voss review` using `sessions_cmd` as the pattern. The SPEC and CONTEXT both say V6 delivers `voss review`, not `voss board`. Note the V5 dependency in the plan commentary.

2. **A-slot reviewer at `InProgress→InReview` gate**
   - What we know: `conf_meets_p` uses `ctx.reviewer` (the legacy single slot) at `InProgress→InReview`. V6 adds A and B as separate slots only at the Done gate.
   - What's unclear: Should A also be invoked at `InProgress→InReview` (the intermediate gate) for the V6 two-source requirement? CONTEXT D-05 says "existing `scope_clean`/`conf`/`tests`/`eval` predicates are reused for A's verification arm" — this implies the intermediate gate stays as-is.
   - Recommendation: Keep `InProgress→InReview` using the single `conf_meets_p` (legacy slot). Only the Done gate gets the two-source A+B predicates.

3. **Sidecar on A-fail-only transitions (before B is called)**
   - What we know: If A fails, B may not be invoked. The sidecar needs B's verdict but B may be None.
   - What's unclear: Write a partial sidecar on A-fail (B null) or skip?
   - Recommendation: Skip the sidecar write entirely on A-fail (B wasn't called; sidecar is incomplete). Write only when both verdicts are present. A-fail drives a critic retry; the next successful review will write the sidecar.

---

## Environment Availability

Step 2.6 SKIPPED — V6 has no external dependencies beyond the project's existing Python venv. All tools and libraries required are already installed. [VERIFIED: no new deps; all modules imported from existing project packages]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (with pytest-asyncio) |
| Config file | `pytest.ini` / `pyproject.toml` (project standard) |
| Quick run command | `.venv/bin/python -m pytest tests/harness/board/ -q --tb=short -x` |
| Full suite command | `.venv/bin/python -m pytest tests/harness/board/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VREV-03 | A-fail refuses Done; B-fail refuses Done; both pass → Done | unit | `.venv/bin/python -m pytest tests/harness/board/test_two_source_gate.py -x` | ❌ Wave 0 |
| VREV-04 | B-block at Done gate → card moves to Blocked | unit | `.venv/bin/python -m pytest tests/harness/board/test_two_source_gate.py::TestBBlockAtGate -x` | ❌ Wave 0 |
| VREV-06 | `ReviewerVerdict` carries `domain_inferred`; B populates; existing construction works | unit | `.venv/bin/python -m pytest tests/harness/board/test_domain_inferred.py -x` | ❌ Wave 0 |
| VREV-07 | Board accepts `reviewer_a`/`reviewer_b`; legacy `reviewer` still works | unit | `.venv/bin/python -m pytest tests/harness/board/test_two_source_gate.py::TestBoardSlotBackCompat -x` | ❌ Wave 0 |
| VREV-09 | `.review.json` sidecar written at gate; re-readable without re-running | unit | `.venv/bin/python -m pytest tests/harness/board/test_review_sidecar.py -x` | ❌ Wave 0 |
| VREV-10 | `voss review` (latest) exits 0; unknown run exits non-zero | smoke | `.venv/bin/python -m pytest tests/harness/board/test_review_cli.py -x` | ❌ Wave 0 |
| VREV-05 | Existing O4 reviewer tests regress green | regression | `.venv/bin/python -m pytest tests/harness/board/ -q` | ✅ (mostly) |
| D-08 (contract) | `verdict.py` imports only stdlib | unit | `.venv/bin/python -m pytest tests/harness/board/test_verdict_imports.py -x` | ✅ |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/harness/board/ -q --tb=short -x`
- **Per wave merge:** `.venv/bin/python -m pytest tests/harness/board/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/harness/board/test_two_source_gate.py` — covers VREV-03, VREV-04, VREV-07
- [ ] `tests/harness/board/test_domain_inferred.py` — covers VREV-06
- [ ] `tests/harness/board/test_review_sidecar.py` — covers VREV-09
- [ ] `tests/harness/board/test_review_cli.py` — covers VREV-10
- [ ] `tests/harness/board/test_verdict.py` — UPDATE `test_exactly_6_fields` to 7-field assertion

### Pre-existing Failure to Fix in Wave 0

`tests/harness/board/test_session_tree_additive.py::TestExitReasonsExtension::test_exit_reasons_is_sorted_superset_of_pre_o3` — asserts `EXIT_REASONS == {"done","max-iter","budget","interrupt","batch-invariant","timeout"}` but `EXIT_REASONS` currently also contains `"killed"`. Fix: update the test's expected set to include `"killed"`. One-line change, pre-existing regression.

---

## Security Domain

V6 makes no authentication, session, access control, cryptographic, or data-handling changes that are security-relevant in the ASVS sense. The `.review.json` sidecar inherits the same 0o600 permissions model as the existing node files — user-only read/write. No ASVS categories apply beyond V5 Input Validation (the `domain_inferred` clamp to the allowed set is the relevant control — prevents garbage from the LLM propagating as a domain value).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `voss board` has not been implemented (V5 not executed); `sessions_cmd` is the correct CLI pattern | Q5, Pattern 6 | If V5 has shipped partially (e.g., in an uncommitted state), a `board_cmd` might exist — inspect cli.py before implementing `review_cmd` |
| A2 | The pre-existing `test_exit_reasons_is_sorted_superset_of_pre_o3` failure is unrelated to V6 and should be fixed in Wave 0 as a green-baseline task | Regression surface, Wave 0 Gaps | If EXIT_REASONS is intentionally not finalized, fixing the test assertion may be premature |
| A3 | All `ReviewerVerdict` constructions across the codebase use keyword arguments (no positional-only calls exist) | Q3 | If any positional construction exists outside the inspected files, adding the 7th field would break it — grep `ReviewerVerdict(` before implementing |

---

## Sources

### Primary (HIGH confidence)

- [VERIFIED: codebase inspection] `voss/harness/board/verdict.py` — current 6-field `ReviewerVerdict` shape; import contract
- [VERIFIED: codebase inspection] `voss/harness/board/gates.py` — `GateContext` single verdict slot; predicate registry shape; `_CODE_DONE_PREDICATES`
- [VERIFIED: codebase inspection] `voss/harness/board/machine.py` — `Board.__init__` (single `reviewer`); `Board.from_team_config`; `Board.move()` gate evaluation; `_force_terminal`; `_append_delta`; `critic_step`
- [VERIFIED: codebase inspection] `voss/harness/board/reviewer_a.py` — all `ReviewerVerdict` constructions keyword-only
- [VERIFIED: codebase inspection] `voss/harness/board/reviewer_b.py` — `_ReviewerBOutput` pydantic mirror; `_to_verdict`; all `ReviewerVerdict` constructions keyword-only
- [VERIFIED: codebase inspection] `voss/harness/board/stub.py` — `DeterministicReviewerStub`; keyword `ReviewerVerdict` construction
- [VERIFIED: codebase inspection] `voss/harness/session_tree.py` — `_write_node_file` pattern; `SessionTreeNode.root_id` field
- [VERIFIED: codebase inspection] `voss/harness/cli.py` — `AGENT_COMMANDS` tuple; no `board_cmd` present; `sessions_cmd` pattern at L2429
- [VERIFIED: codebase inspection] `tests/harness/board/` — full test inventory; 92 passing / 1 failing baseline; `test_exactly_6_fields` identified as the one required test update
- [VERIFIED: codebase inspection] `.planning/config.json` — `nyquist_validation: true`

### Secondary (MEDIUM confidence)

- [CITED: V6-CONTEXT.md D-01..D-15] — locked implementation decisions; all honored in this research
- [CITED: V5-CONTEXT.md] — `voss board` CLI design decisions (unimplemented; used as intent reference only)
- [CITED: V4-CONTEXT.md] — session tree persistence layout; additive-field discipline

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all modules inspected directly from source; no third-party deps
- Architecture: HIGH — predicate registry shape, gate evaluation flow, `_force_terminal` seam all verified by reading machine.py + gates.py
- Pitfalls: HIGH — identified from direct code inspection (6-field test, voss board absence, B-block seam, slots defaulting)

**Research date:** 2026-06-06
**Valid until:** 2026-07-06 (stable codebase; no fast-moving dependencies)
