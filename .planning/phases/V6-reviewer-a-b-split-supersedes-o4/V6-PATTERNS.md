# Phase V6: Reviewer A/B Split (supersedes O4) - Pattern Map

**Mapped:** 2026-06-06
**Files analyzed:** 11 (7 modified, 4 created)
**Analogs found:** 11 / 11

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `voss/harness/board/verdict.py` | model | transform | itself (current 6-field shape) | exact — additive field on the same dataclass |
| `voss/harness/board/reviewer_b.py` | service | request-response | itself (current `_ReviewerBOutput` + `_to_verdict`) | exact — extend pydantic mirror |
| `voss/harness/board/reviewer_a.py` | service | request-response | itself (current `_verdict_from_test_exit` + `_verdict_from_judge`) | exact — default new field |
| `voss/harness/board/gates.py` | middleware | request-response | itself (`GateContext` + `conf_meets_p` predicate class) | exact — add two slots + two predicate classes |
| `voss/harness/board/machine.py` | controller | request-response | itself (`Board.__init__`, `Board.move`, `_force_terminal`, `_append_delta`) | exact — extend existing seams |
| `voss/harness/cli.py` | controller | request-response | `sessions_cmd` (L2429) + `AGENT_COMMANDS` (L3777) | role-match — read-only CLI, no live manager |
| `voss/harness/board/review_persistence.py` (new, or inline) | utility | file-I/O | `_write_node_file` in `session_tree.py` (L97-102) | exact — 0o600 JSON write helper |
| `tests/harness/board/test_two_source_gate.py` (new) | test | CRUD | `test_critic_loop.py` + `test_stub_full_lifecycle.py` | exact — same board lifecycle + stub pattern |
| `tests/harness/board/test_domain_inferred.py` (new) | test | CRUD | `test_verdict.py` | exact — dataclass field assertions |
| `tests/harness/board/test_review_sidecar.py` (new) | test | file-I/O | `test_card_node_wiring.py` + `test_critic_loop.py` | role-match — board lifecycle + fs assertions |
| `tests/harness/board/test_review_cli.py` (new) | test | request-response | `test_reviewer_b.py` (fake provider pattern) | role-match — fake data source, click output |

---

## Pattern Assignments

### `voss/harness/board/verdict.py` (model, transform)

**Analog:** itself — current 6-field `ReviewerVerdict` frozen dataclass

**Current shape** (lines 13-30 — read directly):
```python
@dataclass(frozen=True, slots=True)
class ReviewerVerdict:
    conf: float
    source: Literal["A", "B"]
    tier: Literal["fast", "strong"]
    verdict: Literal["pass", "fail", "block"]
    notes: str
    evidence_refs: tuple[str, ...]
```

**V6 addition pattern** — append as 7th field (MUST be last; defaulted field after non-defaulted fields):
```python
    domain_inferred: Literal["code", "ai", "docs", "unknown"] = "unknown"
```

**Import constraint** (lines 1-10): `Literal` is already imported from `typing`. Zero new imports required. The module docstring calls this the "zero transitive harness import contract" — importing anything from `voss.*` here breaks it.

**Test to update:** `test_verdict.py` line 44-46 — `test_exactly_6_fields` — change the expected set from 6 fields to 7 fields:
```python
# Before:
assert names == {"conf", "source", "tier", "verdict", "notes", "evidence_refs"}
# After:
assert names == {"conf", "source", "tier", "verdict", "notes", "evidence_refs", "domain_inferred"}
```

---

### `voss/harness/board/reviewer_b.py` (service, request-response)

**Analog:** itself — `_ReviewerBOutput` pydantic mirror (lines 34-40) and `_to_verdict` static method (lines 147-174)

**Current `_ReviewerBOutput`** (lines 34-40):
```python
class _ReviewerBOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    conf: float
    verdict: Literal["pass", "fail", "block"]
    notes: str
    evidence_refs: list[str] = []
```

**V6 addition** — add `domain_inferred` field with string type (clamped in `_to_verdict`):
```python
    domain_inferred: str = "unknown"  # B infers; clamped to allowed set in _to_verdict
```

**Current `_to_verdict` success branch** (lines 167-174):
```python
return ReviewerVerdict(
    conf=float(parsed.conf),
    source="B",
    tier=tier,
    verdict=parsed.verdict,
    notes=parsed.notes,
    evidence_refs=tuple(parsed.evidence_refs),
)
```

**V6 addition** — add clamp constant and `domain_inferred` kwarg. Insert before `_to_verdict`:
```python
_ALLOWED_DOMAINS: frozenset[str] = frozenset({"code", "ai", "docs", "unknown"})
```
Extend the success branch:
```python
domain = parsed.domain_inferred if parsed.domain_inferred in _ALLOWED_DOMAINS else "unknown"
return ReviewerVerdict(
    conf=float(parsed.conf),
    source="B",
    tier=tier,
    verdict=parsed.verdict,
    notes=parsed.notes,
    evidence_refs=tuple(parsed.evidence_refs),
    domain_inferred=domain,
)
```

**Parse-fail branch** (lines 159-166) — already uses keyword construction, no change needed; `domain_inferred` defaults to `"unknown"` automatically.

---

### `voss/harness/board/reviewer_a.py` (service, request-response)

**Analog:** itself — `_verdict_from_test_exit` and `_verdict_from_judge` keyword constructions

**V6 change:** All `ReviewerVerdict(...)` keyword constructions in `reviewer_a.py` continue to omit `domain_inferred` — the default `"unknown"` applies automatically. No source edit is strictly required. If A maps `card.domain` → `"code"`/`"ai"` when trivially available, the pattern to follow is:

```python
# Optional: map known card.domain to domain_inferred
_DOMAIN_MAP = {"code": "code", "ai": "ai"}
domain_inferred = _DOMAIN_MAP.get(getattr(card, "domain", ""), "unknown")
```
Then pass `domain_inferred=domain_inferred` to the `ReviewerVerdict(...)` keyword construction. The keyword-only pattern is already established in all existing constructions — copy the exact kwarg style from `_verdict_from_test_exit`.

---

### `voss/harness/board/gates.py` (middleware, request-response)

**Analog:** itself — `GateContext` dataclass (lines 44-56) and `conf_meets_p` predicate class (lines 80-98)

**Current `GateContext`** (lines 44-56):
```python
@dataclass
class GateContext:
    """Per-move-attempt evaluation context. NOT frozen — verdict slot is
    mutable so conf_meets_p can cache the reviewer result."""
    card: Card
    node_envelope: dict
    team_ceiling: TeamCeiling
    team_p_overrides: dict
    retry_ceiling: int
    reserve: int
    now: float
    reviewer: Optional[Reviewer] = None
    verdict: Optional[ReviewerVerdict] = None
```

**V6 addition** — four new defaulted fields after the existing two optional fields:
```python
    reviewer_a: Optional[Reviewer] = None   # V6: A slot
    reviewer_b: Optional[Reviewer] = None   # V6: B slot
    verdict_a: Optional[ReviewerVerdict] = None  # V6: A cache
    verdict_b: Optional[ReviewerVerdict] = None  # V6: B cache
```
All defaulted — existing `GateContext(...)` constructions in `machine.py` and tests are unaffected.

**`conf_meets_p` pattern to copy for new predicates** (lines 80-98):
```python
class conf_meets_p:
    name = "conf"
    def evaluate(self, ctx: GateContext) -> bool:
        from .machine import _DEFAULT_RISK_THRESHOLDS  # lazy to break circular import
        if ctx.reviewer is None:
            return False
        if ctx.verdict is None:
            ctx.verdict = ctx.reviewer.review(ctx.card)
        threshold = ctx.team_p_overrides.get(
            ctx.card.risk_tier,
            _DEFAULT_RISK_THRESHOLDS[ctx.card.risk_tier],
        )
        return ctx.verdict.conf >= threshold
```

**V6 new predicates** — exact same shape, different slot names and pass condition:
```python
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

**`_CODE_DONE_PREDICATES` extension** (line 145): extend the tuple to include both new predicates. Preserve cheap→expensive ordering (scope_clean is cheapest; A runs a test/LLM call; B runs one provider.complete):
```python
_CODE_DONE_PREDICATES = (scope_clean(), a_verification_passes(), b_passes(), tests_pass())
_AI_DONE_PREDICATES   = (scope_clean(), a_verification_passes(), b_passes(), eval_meets_threshold())
```

---

### `voss/harness/board/machine.py` (controller, request-response)

**Analog:** itself — `Board.__init__` (lines 238-263), `Board.from_team_config` (lines 265-298), `Board.move` (lines 336-425), `_force_terminal` (lines 515-537), `_append_delta` (lines 467-493)

**`Board.__init__` extension pattern** — current signature (lines 238-250):
```python
def __init__(
    self,
    *,
    manager: SessionTreeManager,
    reviewer: Reviewer,
    cwd: Path,
    cfg: _BoardConfig,
    team_ceiling: TeamCeiling,
    root_node_id: str,
    clock: Callable[[], float] = time.monotonic,
    per_card_budget: int = 100_000,
    reserve: int = 0,
) -> None:
    self._manager = manager
    self._reviewer = reviewer
    ...
```

**V6 change** — make `reviewer` optional, add `reviewer_a`/`reviewer_b`:
```python
def __init__(
    self,
    *,
    manager: SessionTreeManager,
    reviewer: Optional[Reviewer] = None,   # back-compat alias
    reviewer_a: Optional[Reviewer] = None, # V6
    reviewer_b: Optional[Reviewer] = None, # V6
    cwd: Path,
    ...
) -> None:
    self._reviewer = reviewer  # kept for conf_meets_p at InProgress→InReview
    self._reviewer_a = reviewer_a if reviewer_a is not None else reviewer
    self._reviewer_b = reviewer_b if reviewer_b is not None else reviewer
```

**`GateContext` construction in `Board.move`** (lines 379-388) — current:
```python
ctx = GateContext(
    card=card,
    node_envelope=dict(node.envelope),
    team_ceiling=self._team_ceiling,
    team_p_overrides=dict(self._team_p_overrides),
    retry_ceiling=self._cfg.retry_ceiling,
    reserve=self._reserve,
    now=self._clock(),
    reviewer=self._reviewer,
)
```
**V6 addition** — add `reviewer_a` and `reviewer_b` kwargs:
```python
ctx = GateContext(
    ...,
    reviewer=self._reviewer,
    reviewer_a=self._reviewer_a,
    reviewer_b=self._reviewer_b,
)
```
The same addition applies to the `dry_run_gate` construction at lines 450-459.

**B-block detection seam** — insert in `Board.move` at the `if failing:` branch (lines 396-405). Current:
```python
if failing:
    self._append_delta(
        card, from_col=card.column, to_col=to,
        outcome="refused", failing_clauses=failing,
        verdict_snapshot=verdict_snapshot,
    )
    raise BoardGateError("gate refused", failing_clauses=failing)
```
**V6 change** — prepend a B-block check before the generic refuse:
```python
if failing:
    if ctx.verdict_b is not None and ctx.verdict_b.verdict == "block":
        # D-03: B-block is terminal, not retry-able.
        _write_review_sidecar(card, ctx, outcome="Blocked", cwd=self._cwd, manager=self._manager)
        return self._force_terminal(card, reason="retry_ceiling")
    self._append_delta(...)
    raise BoardGateError("gate refused", failing_clauses=failing)
```

**Sidecar write on success path** — insert in `Board.move` at the "all pass" point (after line 405, before line 407 rebuilds the card), when the transition is `("InReview","Done")` and both verdicts are present:
```python
# 4. Emit passed delta + rebuild card with new column.
if transition == ("InReview", "Done") and ctx.verdict_a is not None and ctx.verdict_b is not None:
    _write_review_sidecar(card, ctx, outcome="Done", cwd=self._cwd, manager=self._manager)
new_card = dataclasses.replace(card, column=to)
```

**`_force_terminal` pattern** (lines 515-537) — used verbatim for B-block routing; no changes to the method itself:
```python
def _force_terminal(self, card: Card, *, reason: str) -> Card:
    new_card = dataclasses.replace(card, column="Blocked")
    self._cards = [new_card if c.node_id == card.node_id else c for c in self._cards]
    self._append_delta(card, from_col=card.column, to_col="Blocked", outcome="forced", reason=reason)
    node = self._manager.get_node(card.node_id)
    if node is not None and not node._finalized:
        exit_reason = reason if reason in {"timeout", "budget"} else "max-iter"
        finalize_node(node, exit_reason=exit_reason, cwd=self._cwd)
    return new_card
```

**`_append_delta` pattern** (lines 467-493) — for reference; the root_id lookup `self._manager.get_node(card.node_id)` is the pattern to reuse in `_write_review_sidecar`:
```python
def _append_delta(self, card, *, from_col, to_col, outcome, failing_clauses=None, reason=None, verdict_snapshot=None):
    node = self._manager.get_node(card.node_id)
    if node is None:
        return
    ...
    _write_node_file(node, self._cwd)
```
Root ID = `node.root_id` (same pattern — fetch node first, then use `node.root_id`).

---

### `voss/harness/board/review_persistence.py` (utility, file-I/O) — or inline in `machine.py`

**Analog:** `_write_node_file` in `voss/harness/session_tree.py` (lines 97-102) — exact mirroring target

**`_write_node_file` to copy** (lines 97-102):
```python
def _write_node_file(node: SessionTreeNode, cwd: Path) -> Path:
    path = cwd / ".voss" / "sessions" / node.root_id / f"{node.id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(node.to_dict(), indent=2))
    path.chmod(0o600)
    return path
```

**V6 sidecar helper** — mirror this exactly, swapping the path suffix and payload:
```python
import dataclasses
import json
from pathlib import Path

def _write_review_sidecar(
    card: "Card",
    ctx: "GateContext",
    *,
    outcome: str,   # "Done" | "Blocked"
    cwd: Path,
    manager: "SessionTreeManager",
) -> Path:
    node = manager.get_node(card.node_id)
    if node is None:
        return  # defensive
    path = cwd / ".voss" / "sessions" / node.root_id / f"{card.node_id}.review.json"
    verdict_a = ctx.verdict_a
    verdict_b = ctx.verdict_b
    a_payload = None
    if verdict_a is not None:
        a_payload = {
            "test_path_or_rubric": verdict_a.evidence_refs[0] if verdict_a.evidence_refs else None,
            "result": verdict_a.verdict,
            "notes": verdict_a.notes,
        }
    payload = {
        "a_verification": a_payload,
        "b_verdict": dataclasses.asdict(verdict_b) if verdict_b is not None else None,
        "final_outcome": outcome,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
    path.chmod(0o600)
    return path
```

---

### `voss/harness/cli.py` — `review_cmd` + `AGENT_COMMANDS` (controller, request-response)

**Analog:** `sessions_cmd` (lines 2429-2448) — read-only from persisted store, no live manager

**`sessions_cmd` structure to mirror** (lines 2429-2448):
```python
@click.command("sessions")
@click.option("--all", "--global", "include_legacy", is_flag=True, help="...")
def sessions_cmd(include_legacy: bool) -> None:
    """List saved agent sessions..."""
    cwd = Path.cwd()
    records = session_store.list_sessions(cwd=cwd, include_legacy=include_legacy)
    if not records:
        click.echo("(no sessions)")
        return
    for r in records:
        click.echo(f"  {r.id[:8]}  {r.updated_at}  ...")
```

**V6 `review_cmd`** — same shape; `run_id` argument instead of option; reads `.review.json` sidecars instead of SessionRecords:
```python
@click.command("review")
@click.argument("run_id", required=False)
def review_cmd(run_id: str | None) -> None:
    """Show per-card A + B review for a run (latest if no run_id)."""
    cwd = Path.cwd()
    sessions_dir = cwd / ".voss" / "sessions"
    if run_id is None:
        run_id = _latest_root_id(sessions_dir)
        if run_id is None:
            click.echo("(no review runs found)", err=True)
            raise SystemExit(1)
    sidecar_dir = sessions_dir / run_id
    if not sidecar_dir.is_dir():
        click.echo(f"unknown run_id: {run_id}", err=True)
        raise SystemExit(1)
    sidecars = sorted(sidecar_dir.glob("*.review.json"))
    if not sidecars:
        click.echo("(no review artifacts for this run)")
        return
    for path in sidecars:
        data = json.loads(path.read_text())
        _render_review_card(path.stem, data)
```

**Latest-root discovery helper** — pattern from `_newest_jobs_dir` (lines 2478-2495) adapted for sessions subdirs:
```python
def _latest_root_id(sessions_dir: Path) -> str | None:
    try:
        roots = [d for d in sessions_dir.iterdir() if d.is_dir()]
    except OSError:
        return None
    if not roots:
        return None
    return max(roots, key=lambda d: d.stat().st_mtime).name
```

**`AGENT_COMMANDS` registration** (lines 3777-3807) — add `review_cmd` to the tuple:
```python
AGENT_COMMANDS = (
    do_cmd,
    ...,
    sessions_cmd,
    review_cmd,   # V6: add here
    jobs_cmd,
    ...
)
```

---

## New Test Files

### `tests/harness/board/test_two_source_gate.py` (VREV-03, VREV-04, VREV-07)

**Analog:** `test_critic_loop.py` (board lifecycle + stub) + `test_stub_full_lifecycle.py` (Backlog→Done flow)

**Fixture pattern to copy** — from `conftest.py` (lines 27-57) and `test_stub_full_lifecycle.py` (lines 17-33):
```python
from .conftest import build_test_team
from voss.harness.board.stub import DeterministicReviewerStub
from voss.harness.board import Board, BoardGateError

class TestBoardSlotBackCompat:
    @pytest.mark.asyncio
    async def test_legacy_reviewer_alias_satisfies_both_slots(self, tmp_recorder):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub(conf=0.99, verdict="pass")
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
        )
        # existing single-slot construction still works (back-compat D-01)
        assert board._reviewer_a is stub
        assert board._reviewer_b is stub
```

**Two-stub Board pattern** — for explicit A+B construction:
```python
stub_a = DeterministicReviewerStub(conf=0.99, verdict="pass", source="A", tier="fast")
stub_b = DeterministicReviewerStub(conf=0.95, verdict="pass", source="B", tier="strong")
board = Board.from_team_config(
    build_test_team(), recorder=manager,
    reviewer_a=stub_a, reviewer_b=stub_b, cwd=cwd,
)
```

**B-block → Blocked assertion pattern** — from `test_critic_loop.py` (lines 95-118):
```python
card = board.move(card, to="InReview")
with pytest.raises(SystemExit):  # or assert card.column == "Blocked"
    card = board.move(card, to="Done")
assert card.column == "Blocked"
node = manager.get_node(card.node_id)
assert node.terminal_state["exit_reason"] == "max-iter"
```

---

### `tests/harness/board/test_domain_inferred.py` (VREV-06)

**Analog:** `test_verdict.py` — dataclass field assertions, keyword construction

**Pattern to copy** (from `test_verdict.py` lines 19-46):
```python
from voss.harness.board.verdict import ReviewerVerdict
from dataclasses import fields

class TestDomainInferred:
    def test_7th_field_exists_with_default(self):
        v = ReviewerVerdict(conf=0.9, source="B", tier="fast", verdict="pass",
                            notes="ok", evidence_refs=())
        assert v.domain_inferred == "unknown"  # default applied

    def test_exactly_7_fields(self):
        names = {f.name for f in fields(ReviewerVerdict)}
        assert names == {"conf", "source", "tier", "verdict", "notes",
                         "evidence_refs", "domain_inferred"}
```

For B-populates tests, use `FakeReviewerBProvider` from `test_reviewer_b.py` (lines 19-45) as the fake provider pattern.

---

### `tests/harness/board/test_review_sidecar.py` (VREV-09)

**Analog:** `test_card_node_wiring.py` (filesystem assertions on `.voss/sessions/`) + `test_critic_loop.py` (board lifecycle)

**Filesystem assertion pattern** — `test_card_node_wiring.py` style:
```python
node = manager.get_node(card.node_id)
node_file = cwd / ".voss" / "sessions" / node.root_id / f"{card.node_id}.json"
assert node_file.exists()
```
Mirror for sidecar:
```python
sidecar_file = cwd / ".voss" / "sessions" / node.root_id / f"{card.node_id}.review.json"
assert sidecar_file.exists()
assert oct(sidecar_file.stat().st_mode)[-3:] == "600"
data = json.loads(sidecar_file.read_text())
assert "a_verification" in data
assert "b_verdict" in data
assert "final_outcome" in data
```

**Board setup pattern** — from `test_stub_full_lifecycle.py` (lines 17-33):
```python
stub_a = DeterministicReviewerStub(conf=0.99, verdict="pass", source="A", tier="fast")
stub_b = DeterministicReviewerStub(conf=0.95, verdict="pass", source="B", tier="strong")
board = Board.from_team_config(
    build_test_team(), recorder=manager,
    reviewer_a=stub_a, reviewer_b=stub_b, cwd=cwd,
)
card = await board.spawn_card(risk_tier="low")
card = dataclasses.replace(card, artifact=SimpleNamespace(tests_passed=True, scope_violations=()))
board._cards = [card if c.node_id == card.node_id else c for c in board._cards]
# Drive to Done
card = board.move(card, "Planned")
card = board.move(card, "InProgress")
card = board.move(card, "InReview")
card = board.move(card, "Done")
```

---

### `tests/harness/board/test_review_cli.py` (VREV-10)

**Analog:** `sessions_cmd` test pattern (no existing test file — follow `test_reviewer_b.py` fake provider approach but for filesystem + click)

**Click testing pattern** — use `click.testing.CliRunner`:
```python
from click.testing import CliRunner
from voss.harness.cli import review_cmd

class TestReviewCli:
    def test_unknown_run_id_exits_nonzero(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(review_cmd, ["nonexistent-run-id"],
                               catch_exceptions=False)
        assert result.exit_code != 0
        assert "unknown run_id" in result.output

    def test_no_sessions_exits_nonzero(self, tmp_path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(review_cmd, [], catch_exceptions=False)
        assert result.exit_code != 0

    def test_existing_run_exits_zero(self, tmp_path):
        # Write a fake .review.json sidecar, then invoke review_cmd.
        root_id = "testrootid"
        sidecar_dir = tmp_path / ".voss" / "sessions" / root_id
        sidecar_dir.mkdir(parents=True)
        sidecar = sidecar_dir / "nodeabc.review.json"
        sidecar.write_text(json.dumps({
            "a_verification": {"result": "pass", "notes": "ok", "test_path_or_rubric": None},
            "b_verdict": {"conf": 0.95, "verdict": "pass", "notes": "good",
                          "evidence_refs": [], "domain_inferred": "code",
                          "source": "B", "tier": "strong"},
            "final_outcome": "Done",
        }))
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(review_cmd, [root_id], catch_exceptions=False)
        assert result.exit_code == 0
```

---

## Shared Patterns

### Additive Defaulted Fields
**Source:** `verdict.py` `ReviewerVerdict`, `gates.py` `GateContext`
**Apply to:** Every V6 field addition (`domain_inferred`, `reviewer_a`, `reviewer_b`, `verdict_a`, `verdict_b`)
```python
# Pattern: defaulted fields appended AFTER all non-defaulted fields
# On @dataclass(frozen=True, slots=True): valid Python, existing constructions unaffected
field_name: Optional[Type] = None       # mutable dataclass
field_name: Literal["a","b"] = "a"     # frozen dataclass
```

### Lazy Reviewer Caching
**Source:** `gates.py` `conf_meets_p.evaluate` (lines 88-98)
**Apply to:** `a_verification_passes.evaluate`, `b_passes.evaluate`
```python
if ctx.verdict_X is None:
    ctx.verdict_X = ctx.reviewer_X.review(ctx.card)
return ctx.verdict_X.verdict == "pass"
```
Call at most once per GateContext (never cross-move caching).

### 0o600 JSON Sidecar Write
**Source:** `session_tree.py` `_write_node_file` (lines 97-102)
**Apply to:** `_write_review_sidecar` in `machine.py` or `review_persistence.py`
```python
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, indent=2))
path.chmod(0o600)
```

### Back-compat Alias Fallback
**Source:** `Card` dataclass additive fields (V4/V5 pattern) — conceptual
**Apply to:** `Board.__init__` `reviewer` → `reviewer_a`/`reviewer_b` fallback:
```python
self._reviewer_a = reviewer_a if reviewer_a is not None else reviewer
self._reviewer_b = reviewer_b if reviewer_b is not None else reviewer
```

### `from_team_config` Classmethod Extension
**Source:** `machine.py` `Board.from_team_config` (lines 265-298)
**Apply to:** Adding `reviewer_a`/`reviewer_b` parameters that pass through to `cls(...)`:
```python
@classmethod
def from_team_config(cls, team_config, *, recorder, reviewer=None,
                     reviewer_a=None, reviewer_b=None, cwd, ...):
    ...
    board = cls(manager=recorder, reviewer=reviewer,
                reviewer_a=reviewer_a, reviewer_b=reviewer_b,
                cwd=cwd, ...)
```

### Read-only CLI from Persisted Files
**Source:** `sessions_cmd` (cli.py lines 2429-2448)
**Apply to:** `review_cmd`
- No live Board/SessionTreeManager constructed
- Discover root dirs by mtime (pattern from `_newest_jobs_dir` L2478-2495)
- `click.echo(...)` for output; `raise SystemExit(1)` for errors
- Unknown-ID → `err=True` stderr + exit 1

### Board Lifecycle Test Setup
**Source:** `test_stub_full_lifecycle.py` (lines 17-33) + `conftest.py` (lines 27-57)
**Apply to:** All new board test files
```python
# Always use these fixtures:
#   tmp_recorder → (manager, cwd)
#   build_test_team() from conftest
#   DeterministicReviewerStub for fast/deterministic reviews
#   dataclasses.replace(card, artifact=...) to attach artifact before InReview
#   board._cards = [...] to update mutable card list after replace
```

---

## Pre-existing Test Fix (Wave 0 prerequisite)

**File:** `tests/harness/board/test_session_tree_additive.py`
**Test:** `TestExitReasonsExtension::test_exit_reasons_is_sorted_superset_of_pre_o3`
**Fix:** Update expected set to include `"killed"` (added post-O3 by O5 for EM kill-flow):
```python
# Before:
assert EXIT_REASONS == {"done","max-iter","budget","interrupt","batch-invariant","timeout"}
# After:
assert EXIT_REASONS == {"done","max-iter","budget","interrupt","batch-invariant","timeout","killed"}
```
This unblocks the green baseline before any V6 implementation.

---

## No Analog Found

All V6 files have close analogs in the codebase. No file requires RESEARCH.md patterns as a substitute.

---

## Metadata

**Analog search scope:** `voss/harness/board/`, `voss/harness/session_tree.py`, `voss/harness/cli.py`, `tests/harness/board/`
**Files read:** 14 source files + CONTEXT.md + RESEARCH.md
**Pattern extraction date:** 2026-06-06
