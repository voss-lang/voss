# Phase V7: Engineering Manager Loop (supersedes O5) - Research

**Researched:** 2026-06-06
**Domain:** Python CLI composition — click group + async em_loop + session-tree + board + RunFinal persistence + sign-off
**Confidence:** HIGH (all code verified against live source; compositions proven via direct execution)

---

<user_constraints>
## User Constraints (from V7-CONTEXT.md)

### Locked Decisions

- Build only the 3 gaps (CLI compose, RunFinal persistence, sign-off); verify/regress EM-01..10 + cage.
- O5 marked superseded (bookkeeping); O5 artifacts retained as reference.
- Add a `run` subcommand to the EXISTING `@click.group("team")` at `voss/harness/cli.py:3777` (alongside `team check`).
- Composition order: load team via V3 `compile_team` → build V4 `SessionTreeManager` → build V5 `Board` → inject reviewer → run shipped async `em_loop`.
- `em_loop` is async → drive via the harness's existing async-run pattern (`asyncio.run(coro)` in a sync click command, same as `asyncio.run(run_critique(...))` at cli.py:3575).
- Acceptance: stub provider, ≥1 card, RunFinal, exits 0.
- Default-roster fallback: use `DEFAULT_ROSTER` (team.py:48) + a synthesized default ceiling when `.voss/team.voss` absent; explicit file overrides.
- RunFinal persisted to `.voss/sessions/<root_id>/run-final.json` — a read-only sidecar.
- RunFinal is frozen → serialize fields; do NOT mutate the dataclass.
- Sign-off appended to sidecar as a superset key (not a RunFinal mutation).
- Reject records the decision but does NOT revert edits.
- Cage stays intact (V7 only injects the handle; adds no mutation methods).
- Tests: pytest, class-based, `tests/harness/` conventions; stub provider + `DeterministicEMStub`; click `CliRunner`.
- No new third-party dependencies.
- Zero field changes to `RunRecord`, `SessionRecord`, `BudgetScope`.

### Claude's Discretion

- RunFinal summary print format (table vs structured text) and the approve/reject prompt mechanism (click `confirm`/`prompt`).
- The serialization shape of `run-final.json` (field layout) — must round-trip the RunFinal fields + sign-off; consumed by V9 (keep it a flat, stable JSON object).
- How the default ceiling value is chosen (reuse V3's default-roster ceiling injection).
- Exact async-drive call site for `em_loop` within the CLI command.
- Test organization within `tests/harness/` conventions.

### Deferred Ideas (OUT OF SCOPE)

- Sign-off forcing function (mandatory killed-card/misroute diff before approve unlocks) → V9.
- Full audit product, calibration telemetry, slop-rejection spot-audit → V9.
- Reject-revert / rollback of run edits → out of scope (record only).
- ADE goal-input / live-run UI → V11.
- In-flight interactive checkpoints (V7 is autonomous-to-terminal then sign-off).
- Any field change to `RunRecord`/`SessionRecord`/`BudgetScope` — frozen.
</user_constraints>

---

## Summary

V7 is pure composition and CLI plumbing on top of shipped O5 code. The `em_loop` coroutine, `EMBoardHandle` cage, `DeterministicEMStub`, `SessionTreeManager`, `Board`, `ReviewerA`, and `ReviewerB` are all importable and functionally correct today. Composition was proven via direct Python execution: the full stack (team config → session-tree → board → handle → em_loop → RunFinal) runs end-to-end in a tempdir, producing a frozen `RunFinal` from a scripted stub in under 100ms.

The three new artifacts are: (1) a `team run` click subcommand that composes the stack and drives `asyncio.run(em_loop(...))`, (2) a `_persist_run_final` helper that writes `.voss/sessions/<root_id>/run-final.json` as a superset JSON, and (3) a `click.prompt` sign-off sequence that appends the decision to the sidecar. The default-roster fallback path is a ~15-line function that builds `TeamConfig` + `SubagentRegistry` from `DEFAULT_ROSTER` without touching the parser.

**Critical open question (RESOLVED, see §Open Questions):** V6 plans 02-05 have not yet been executed. V6-01 wrote RED scaffold tests (now failing), but the implementation plans (V6-02: `domain_inferred` field; V6-03: dual reviewer A+B Board slots; V6-04: `voss review` CLI) are unexecuted. V7 can proceed using the current single-`reviewer` Board slot with `DeterministicReviewerStub` for tests. V7 must NOT attempt to use the `reviewer_a`/`reviewer_b` Board constructor keyword arguments from V6-03 because `Board.from_team_config` does not yet accept them. A secondary gap: `RunFinal` does not contain `evidence_refs`/`diff_summary`/`residual` fields despite the CONTEXT.md description — the sidecar JSON will serialize the actual RunFinal fields plus a `sign_off` key; the CONTEXT's field list was aspirational O5 design rather than the shipped dataclass.

**Primary recommendation:** Implement V7 against the current `Board.from_team_config(team_config, recorder=..., reviewer=DeterministicReviewerStub(...), cwd=...)` signature. The `team run` command should pre-spawn one root board card before calling `em_loop` so `total_cards >= 1` in RunFinal. Use `asyncio.run(em_loop(...))` for async-drive (same pattern as consensus_cmd at cli.py:3575).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CLI entry point | CLI (cli.py) | — | click subcommand in existing team_group |
| Team config loading | CLI (cli.py) | team.py | File parse or default-roster synthesis |
| Session-tree construction | CLI (cli.py) | session_tree.py | Root node created in command scope |
| Board construction | CLI (cli.py) | board/machine.py | from_team_config factory |
| EMBoardHandle construction | CLI (cli.py) | em/handle.py | Constructed with board+registry+team_config |
| em_loop execution | em/loop.py | CLI drives asyncio.run | Pure async logic; CLI is the driver |
| RunFinal persistence | CLI (cli.py) | em/tickets.py | Serialize and write to sidecar path |
| Sign-off prompt | CLI (cli.py) | — | click.prompt; decision appended to sidecar |
| Cage enforcement | em/handle.py | — | No mutation methods; roster check on dispatch |
| Regression verification | tests/harness/em/ | — | Existing O5 tests + new V7 tests |

---

## Standard Stack

### Core (all already in pyproject.toml — no new installs)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| click | ≥8.0 [VERIFIED: used throughout cli.py] | CLI subcommand, `click.prompt`, `CliRunner` | Already the harness CLI framework |
| pytest-asyncio | present [VERIFIED: used in tests/harness/em/] | Async em_loop test support | Existing test pattern |
| dataclasses | stdlib | RunFinal serialization via `dataclasses.asdict` | Stdlib; no deps |
| json | stdlib | sidecar persistence | Stdlib |
| asyncio | stdlib | `asyncio.run(em_loop(...))` | Stdlib async driver |

**Installation:** No new packages. All dependencies are already present.

## Package Legitimacy Audit

No new packages are installed in V7. This section is intentionally empty.

---

## Architecture Patterns

### System Architecture Diagram

```
voss team run "<goal>"
    │
    ├─ load team config ─┬─ .voss/team.voss exists → parse + compile_team
    │                    └─ absent → _default_team_config() (DEFAULT_ROSTER)
    │
    ├─ SessionTreeNode.create_root(cwd, limit=500_000)
    ├─ SessionTreeManager(root, reserve=0, cwd)
    │
    ├─ Board.from_team_config(team_config, recorder=manager, reviewer=stub, cwd)
    ├─ board.spawn_card(risk_tier="med")        ← ensures ≥1 card before loop
    │
    ├─ EMBoardHandle(board, registry, team_config, manager, base_gate, cwd)
    │
    ├─ asyncio.run(em_loop(idea, em_handle=handle, em_agent=DeterministicEMStub,
    │                      roster_descriptions=..., max_iterations=50))
    │
    ├─ RunFinal returned ──→ _persist_run_final(rf, handle, cwd)
    │                           writes .voss/sessions/<root_id>/run-final.json
    │
    ├─ print RunFinal summary
    │
    └─ click.prompt("Approve or reject", type=Choice(['approve','reject']))
           └─ append {"sign_off": {"decision": ..., "ts": ...}} to sidecar JSON
```

### Recommended Project Structure (new files only)

```
voss/harness/cli.py              # +team run subcommand (≈70 lines)
tests/harness/test_team_run_cli.py   # V7-specific CLI + persistence + sign-off tests
```

---

### Pattern 1: `team run` Click Subcommand

**What:** Async click command inside the existing `team_group`; drives `em_loop` via `asyncio.run`.

**When to use:** Any async logic in a sync click command. Mirror of consensus_cmd pattern at cli.py:3575.

```python
# Source: voss/harness/cli.py:3575 (consensus_cmd), :3777 (team_group)
@team_group.command("run")
@click.argument("goal")
@click.option("--cwd", "cwd_str", default=".", help="Working directory.")
@click.option("--max-iterations", default=50, type=int)
def team_run_cmd(goal: str, cwd_str: str, max_iterations: int) -> None:
    """Run the EM org loop end-to-end on a goal."""
    import asyncio
    import json as json_lib
    from pathlib import Path
    # ... build stack ...
    rf = asyncio.run(_team_run_async(goal, cwd, max_iterations))
    # persist + sign-off
```

### Pattern 2: Default-Roster TeamConfig (no .voss/team.voss)

**What:** Build `TeamConfig` + `SubagentRegistry` from `DEFAULT_ROSTER` programmatically, bypassing the parser.

```python
# Source: voss/harness/team.py:48, :588, :634; verified via direct execution
from voss.harness.team import (
    DEFAULT_ROSTER, TeamConfig, TeamCeiling, TeamPolicy, BoardSpec,
    subagent_spec_from_role,
)
from voss.harness.subagents import SubagentRegistry
from voss.ast_nodes import Span

DEFAULT_BUDGET = 500_000
DEFAULT_LATENCY_S = 3600

def _default_team_config() -> tuple[TeamConfig, SubagentRegistry]:
    ceiling = TeamCeiling(budget_tokens=DEFAULT_BUDGET, scope=None, latency_seconds=DEFAULT_LATENCY_S)
    registry = SubagentRegistry()
    for name in DEFAULT_ROSTER:
        spec = subagent_spec_from_role(
            role_name=name,
            role_decl_span=Span(file="<default>", line_start=0, col_start=0, line_end=0, col_end=0),
            kvs={},
            ceiling=ceiling,
            ceiling_ast=None,
            apply_role_defaults=True,
        )
        registry.register(spec)
    config = TeamConfig(
        name="default",
        ceiling=ceiling,
        policy=TeamPolicy(p=None),
        em_agent_id=None,
        roster_ids=frozenset(DEFAULT_ROSTER),
        board=BoardSpec(raw_items=()),
        rituals=(),
    )
    return config, registry
```

**VERIFIED:** Executed directly; produces 7-role registry with model tiers resolved.

### Pattern 3: Full Composition Stack Construction

**What:** Exact construction order: session-tree → board → handle.

```python
# Source: verified via direct execution; mirrors tests/harness/em/conftest.py + board conftest.py
import asyncio, dataclasses
from pathlib import Path
from voss.harness.session_tree import SessionTreeManager, SessionTreeNode
from voss.harness.board.machine import Board
from voss.harness.board.stub import DeterministicReviewerStub
from voss.harness.em.handle import EMBoardHandle
from voss.harness.em.loop import em_loop
from voss.harness.em.stub import DeterministicEMStub
from voss.harness.permissions import PermissionGate

# Step 1: session-tree (V4)
root_node = SessionTreeNode.create_root(cwd=cwd, limit=500_000)
manager = SessionTreeManager(root_node, reserve=0, cwd=cwd)

# Step 2: board (V5) — single-reviewer (pre-V6-03)
reviewer = DeterministicReviewerStub(conf=0.99, verdict="pass")
board = Board.from_team_config(
    team_config,
    recorder=manager,
    reviewer=reviewer,
    cwd=cwd,
    per_card_budget=100_000,
)

# Step 3: spawn root card (so total_cards >= 1)
card = await board.spawn_card(risk_tier="med")

# Step 4: handle (O5)
base_gate = PermissionGate(mode="auto", auto_yes=True)
handle = EMBoardHandle(
    board=board,
    registry=registry,
    team_config=team_config,
    manager=manager,
    base_gate=base_gate,
    cwd=cwd,
)

# Step 5: roster_descriptions from registry
roster_descs = {spec.id: spec.description for spec in registry.entries()}

# Step 6: run loop
rf = await em_loop(
    idea=goal,
    em_handle=handle,
    em_agent=DeterministicEMStub(...),   # or real LLM agent
    roster_descriptions=roster_descs,
    max_iterations=max_iterations,
)
```

### Pattern 4: RunFinal Persistence (superset sidecar)

**What:** Serialize frozen RunFinal to JSON, add sign-off as a superset key. Never mutate the dataclass.

```python
# Source: verified via direct execution
import dataclasses, datetime, json
from pathlib import Path
from voss.harness.em.tickets import RunFinal

def _persist_run_final(
    rf: RunFinal,
    cwd: Path,
    decision: str | None = None,
) -> Path:
    run_dir = cwd / ".voss" / "sessions" / rf.root_id
    run_dir.mkdir(parents=True, exist_ok=True)
    persist_path = run_dir / "run-final.json"

    data = dataclasses.asdict(rf)   # handles frozen slots; tuples become lists

    if decision is not None:
        data["sign_off"] = {
            "decision": decision,
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        }

    persist_path.write_text(json.dumps(data, indent=2))
    persist_path.chmod(0o600)
    return persist_path
```

**Key facts:**
- `dataclasses.asdict(rf)` correctly handles `frozen=True, slots=True` — verified.
- `RunFinal` has no tuple-type fields needing special conversion; `candidates_considered` is on `RoutingRationale` (not RunFinal).
- Write to `.voss/sessions/<root_id>/run-final.json`; `root_id` = `rf.root_id` = `manager._root.id`.
- Initial write (before sign-off): call `_persist_run_final(rf, cwd)`.
- After prompt: call `_persist_run_final(rf, cwd, decision=decision)` (re-writes with sign_off key).

### Pattern 5: Sign-off Prompt

**What:** click.prompt with `type=click.Choice(...)` for testability via CliRunner with `input=`.

```python
# Verified: click.prompt with Choice works with CliRunner(input="approve\n")
import click

decision = click.prompt(
    "Sign off on this run",
    type=click.Choice(["approve", "reject"]),
)
# decision is "approve" or "reject"
_persist_run_final(rf, cwd, decision=decision)
```

**Why `click.prompt` over `click.confirm`:** The CONTEXT gives Claude discretion on this. `click.prompt` with `Choice` is more explicit and testable — `CliRunner().invoke(cmd, input="approve\n")` works cleanly. `click.confirm` would need "y"/"n" inputs and a separate code path for reject.

### Pattern 6: async-drive in sync click command

**What:** The standard harness pattern. `asyncio.run()` in a sync click command body; no event loop conflict in tests because CliRunner runs synchronously.

```python
# Source: cli.py:3575 (consensus_cmd pattern)
result = asyncio.run(run_critique(provider, cfg.default_model, constraints, diff_text))
```

For V7:
```python
rf = asyncio.run(_team_run_async(goal, cwd, max_iterations, team_config, registry))
```

The `_run_turn_cancellable` pattern (cli.py:315) is for agent turns with SIGINT; `asyncio.run` is correct for this non-interactive loop.

### Anti-Patterns to Avoid

- **Mutating RunFinal:** It is `frozen=True, slots=True`. Use `dataclasses.replace(rf, ...)` if you need a modified copy, or add fields to the sidecar JSON dict — never `rf.field = value`.
- **Using `reviewer_a`/`reviewer_b` keyword on `Board.from_team_config`:** V6-03 has not been executed. The current signature only accepts a single `reviewer` parameter. Using the V6-03 API will raise `TypeError`.
- **Calling `compile_team` with a synthesized `TeamDecl`:** The AST nodes (`TeamDecl`, `RosterDecl`, etc.) are complex to construct manually. Use `_default_team_config()` helper (direct construction, no parser) for the default path.
- **Expecting `total_cards >= 1` without pre-spawning:** `em_loop` creates tickets but does not call `board.spawn_card`. The CLI command MUST call `await board.spawn_card(risk_tier="med")` before `em_loop` so `RunFinal.total_cards >= 1`.
- **Expecting `evidence_refs`/`diff_summary`/`residual` in RunFinal:** These fields are NOT in the shipped `RunFinal` dataclass. They appear in `KillRecord` and `RescopeRecord`. The sidecar serializes what RunFinal actually has.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Board construction | Custom board wiring | `Board.from_team_config(...)` | Factory reads BoardSpec + ceiling; handles p_overrides |
| Reviewer stub | Fake ReviewerVerdict logic | `DeterministicReviewerStub` from `voss.harness.board.stub` | Already exists; satisfies `Reviewer` Protocol |
| EM agent stub | Custom async plan() mock | `DeterministicEMStub` from `voss.harness.em.stub` | Zero-LLM; scripted; introspectable via `.calls` |
| JSON serialization | Custom `__dict__` walk | `dataclasses.asdict(rf)` | Handles frozen+slots correctly |
| Async click | `asyncio.get_event_loop().run_until_complete` | `asyncio.run(coro)` | Standard harness pattern; no loop conflict in CliRunner |
| Team config default | Parse a fake .voss string | `_default_team_config()` via direct construction | Avoids grammar dependency |
| Permission gate | Custom permission logic | `PermissionGate(mode="auto", auto_yes=True)` | Already the test/CLI default |

**Key insight:** Every piece of this phase already exists as a tested module. V7 is assembly, not construction.

---

## Runtime State Inventory

> Not a rename/refactor/migration phase. Omit.

---

## Common Pitfalls

### Pitfall 1: Spawning 0 board cards → total_cards == 0
**What goes wrong:** `em_loop` exits immediately (all_cards_terminal = True on empty board) with `total_cards=0`. Acceptance criterion "≥1 card" fails.
**Why it happens:** `em_loop` creates `Ticket` objects (via `handle.create_ticket`) which are NOT board cards. `Board.spawn_card` must be called separately.
**How to avoid:** Call `card = await board.spawn_card(risk_tier="med")` before `asyncio.run(em_loop(...))`. In tests, set `deadline_override=time.monotonic() + short_duration` so the card terminates quickly.
**Warning signs:** `RunFinal.total_cards == 0`; loop exits on iteration 0.

### Pitfall 2: Using V6-03 Board API that doesn't exist yet
**What goes wrong:** `TypeError: Board.from_team_config() got an unexpected keyword argument 'reviewer_a'`
**Why it happens:** V6-03 (dual reviewer slots) has not been executed. The current `Board.from_team_config` signature is `(team_config, *, recorder, reviewer, cwd, clock, parent_node_id, per_card_budget)`.
**How to avoid:** Use the single `reviewer=DeterministicReviewerStub(...)` parameter only.
**Warning signs:** The test files `test_two_source_gate.py` and `test_domain_inferred.py` are already RED for this reason.

### Pitfall 3: RunFinal field gap (evidence_refs / diff_summary / residual missing)
**What goes wrong:** Planner writes code that accesses `rf.evidence_refs` → `AttributeError`.
**Why it happens:** CONTEXT.md listed these as RunFinal fields based on O5's design intent. The shipped `RunFinal` in `tickets.py:112` only has: `root_id`, `idea`, `total_cards`, `done_count`, `blocked_count`, `killed_count`, `rescope_count`, `em_iterations`, `ts`, `kind`.
**How to avoid:** Serialize `dataclasses.asdict(rf)` — this gives exactly the 10 fields above. The sidecar adds `sign_off` as a superset key. No `evidence_refs` in the RunFinal row.
**Warning signs:** `AttributeError: RunFinal object has no attribute 'evidence_refs'`

### Pitfall 4: Async loop conflict in CliRunner tests
**What goes wrong:** `RuntimeError: This event loop is already running` or tests hang.
**Why it happens:** pytest-asyncio creates an event loop; calling `asyncio.run(...)` inside a running loop raises.
**How to avoid:** Use `asyncio.run(coro)` only in the **sync click command** code. For tests that invoke the command via `CliRunner`, the command is called synchronously — `asyncio.run` works fine inside CliRunner because CliRunner does NOT run in an async context. Tests that directly test `em_loop` use `@pytest.mark.asyncio`.
**Warning signs:** Tests pass individually but hang or raise when CliRunner wraps async code.

### Pitfall 5: Span construction for default-roster path
**What goes wrong:** `TypeError: Span.__init__() missing required argument` or wrong positional order.
**Why it happens:** `Span` is a frozen dataclass with 5+ positional fields.
**How to avoid:** Use keyword arguments: `Span(file="<default>", line_start=0, col_start=0, line_end=0, col_end=0)`.
**Warning signs:** Compile-time errors in `_default_team_config`.

### Pitfall 6: _persist_run_final path collision if called twice
**What goes wrong:** The sidecar is written once before sign-off and once after; the sign-off write must re-serialize the full RunFinal dict, not just append.
**How to avoid:** Both calls use `persist_path.write_text(json.dumps(data, indent=2))` — the second call overwrites the first with the sign_off key added.

### Pitfall 7: DEFAULT_ROSTER model-tier resolution requires config
**What goes wrong:** `VossTeamConfigError: model tier 'cheap' is not configured` in environments without a configured model catalog.
**Why it happens:** `subagent_spec_from_role(..., apply_role_defaults=True)` calls `_resolve_model_string(rd.model_tier)` which calls `get_model_tiers()`. In test environments without model configuration, this may raise.
**How to avoid:** For tests, use a `monkeypatch` on `voss.harness.config.get_model_tiers` or use `apply_role_defaults=False` (falls back to empty spec, no model resolution).
**Warning signs:** `VossTeamConfigError: model tier 'cheap' is not configured` in test runs.

---

## Code Examples

### Exact em_loop signature (VERIFIED)

```python
# Source: voss/harness/em/loop.py:88
async def em_loop(
    *,
    idea: str,
    em_handle: EMBoardHandle,
    em_agent: object,               # must expose: async plan(*, idea, snapshot, **) -> EMPlanResponse
    roster_descriptions: dict[str, str] | None = None,
    max_iterations: int = 50,
) -> RunFinal: ...
```

### Exact EMBoardHandle constructor (VERIFIED)

```python
# Source: voss/harness/em/handle.py:82
EMBoardHandle(
    *,
    board: BoardProtocol,           # board/machine.py Board satisfies this
    registry: SubagentRegistry,
    team_config: TeamConfig,
    manager: SessionTreeManager,
    base_gate: PermissionGate,
    cwd: Path,
    subagent_runner: Optional[Callable] = None,  # None for stub path
    renderer: object = None,
    provider: object = None,
    model: str = "",
)
```

### Exact Board.from_team_config signature (VERIFIED — current, pre-V6-03)

```python
# Source: voss/harness/board/machine.py:266
Board.from_team_config(
    team_config: TeamConfig,
    *,
    recorder: SessionTreeManager,
    reviewer: Reviewer,             # single slot — V6-03 not yet executed
    cwd: Path,
    clock: Callable[[], float] = time.monotonic,
    parent_node_id: str | None = None,
    per_card_budget: int = 100_000,
) -> Board
```

### Exact SessionTreeManager constructor (VERIFIED)

```python
# Source: voss/harness/session_tree.py:147
SessionTreeManager(
    root_node: SessionTreeNode,
    *,
    reserve: int,
    cwd: Path,
)
```

### DeterministicEMStub scripted usage (VERIFIED)

```python
# Source: voss/harness/em/stub.py
stub = DeterministicEMStub(scripted=[
    EMPlanResponse(ops=[CreateTicketOp(original_idea="...", worker_role="backend")]),
    EMPlanResponse(ops=[NoopOp(reason="waiting")]),
    # On exhaustion: returns EMPlanResponse(ops=[NoopOp(reason="stub_exhausted")])
])
```

### team_group registration pattern (VERIFIED)

```python
# Source: voss/harness/cli.py:3777
@click.group("team")
def team_group() -> None:
    """Inspect and validate the team cage (VTEAM-10)."""

@team_group.command("run")        # ← V7 adds this
@click.argument("goal")
def team_run_cmd(goal: str) -> None: ...
# team_group is already in AGENT_COMMANDS tuple (cli.py:3877)
# No registration change needed
```

### CliRunner sign-off test pattern (VERIFIED)

```python
# click.prompt Choice is testable via CliRunner input=
from click.testing import CliRunner

result = CliRunner().invoke(root, ["team", "run", "build API", "--cwd", str(tmp_path)],
                            input="approve\n")
assert result.exit_code == 0
```

---

## Open Questions

### Q1: V6 execution status — does V7 depend on unexecuted V6 plans? (RESOLVED)

**What we know:** V6-01 executed (RED scaffolds written). V6-02 through V6-05 NOT yet executed. The RED scaffolds in `tests/harness/board/` (test_domain_inferred.py, test_two_source_gate.py, test_review_cli.py, test_review_sidecar.py, test_verdict.py) are currently failing (13 failures).

**What's unexecuted:**
- V6-02: `ReviewerVerdict.domain_inferred` 7th field + `_ReviewerBOutput.domain_inferred`
- V6-03: `Board.from_team_config(reviewer_a=..., reviewer_b=...)` dual slots + two-source Done gate + `.review.json` sidecar
- V6-04: `voss review` CLI command
- V6-05: (to be checked)

**Impact on V7:** V7 CANNOT use `reviewer_a`/`reviewer_b` Board constructor arguments. V7 CAN use `ReviewerA` and `ReviewerB` directly via the existing `reviewer=` single slot, OR use `DeterministicReviewerStub` for tests.

**Resolution:** V7 uses the current `Board.from_team_config(..., reviewer=DeterministicReviewerStub(conf=0.99, verdict="pass"))` for tests and `reviewer=ReviewerA(...)` for the production path. The CONTEXT says "V6 Reviewer-A/B interface (V6 builds intelligence; V7 injects them)" — the injection is via the single `reviewer=` slot. This is the `ReviewerA` class already in `voss/harness/board/reviewer_a.py` which was shipped as part of O4/V6's partial implementation. V7 does NOT use the two-source Done gate because that is V6-03 which is unexecuted.

**Planner action required:** V7 Wave 0 MUST include a gate that confirms `tests/harness/em/` is green. V7 must NOT run `tests/harness/board/` as part of its acceptance gate (those have 13 pre-existing RED failures from V6 scaffolds). The acceptance criterion "existing O5 em tests pass" refers specifically to `tests/harness/em/`.

### Q2: What is "≥1 card" in acceptance criteria? (RESOLVED)

**Resolution:** "Card" means `board.Card` (a session-tree-backed board card), not `em.Ticket`. `RunFinal.total_cards = len(board.cards())`. The CLI command MUST call `await board.spawn_card(risk_tier="med")` before `em_loop` to ensure `total_cards >= 1`. After `max_iterations` exhaust, the card lands in `Blocked` (via `force_block_all`). Result: `total_cards=1`, `blocked_count=1`, `done_count=0` on the stub path — all-cards-terminal satisfied.

### Q3: RunFinal missing fields (evidence_refs / diff_summary / residual)? (RESOLVED)

**Resolution:** These fields are NOT in the shipped `RunFinal` dataclass. `RunFinal` has 10 fields: `root_id`, `idea`, `total_cards`, `done_count`, `blocked_count`, `killed_count`, `rescope_count`, `em_iterations`, `ts`, `kind`. The CONTEXT.md description was aspirational O5 design. The sidecar `run-final.json` serializes exactly these 10 fields plus a `sign_off` key (superset). V9 consumes the sidecar; this simple shape is stable and sufficient.

### Q4: How does the default ceiling value get chosen? (RESOLVED)

**Resolution:** The default ceiling for `_default_team_config()` is: `TeamCeiling(budget_tokens=500_000, scope=None, latency_seconds=3600)`. The budget is `500_000` tokens (generous for a stub run). The `scope=None` means no glob restriction (appropriate since default-roster roles have their own scope defaults). The `latency_seconds=3600` means cards timeout after 1 hour in production (in stub tests, use `deadline_override`).

### Q5: Async-drive pattern for em_loop? (RESOLVED)

**Resolution:** Use `asyncio.run(coro)` directly in the sync click command. This is the `consensus_cmd` pattern (cli.py:3575). Do NOT use `_run_turn_cancellable` (that wraps an agent turn with SIGINT handling and Textual renderer). For tests, `CliRunner().invoke(...)` runs synchronously; there is no running event loop, so `asyncio.run` works without the thread-pool workaround used by `_run_async_sync`.

### Q6: Where does team file parsing live? (RESOLVED)

**Resolution:** Mirror the `team check` command pattern (cli.py:3786-3815):
```python
from voss import parse
from voss.ast_nodes import TeamDecl
from voss.harness.team import compile_team
p = Path(cwd) / ".voss" / "team.voss"
if p.is_file():
    src = p.read_text(encoding="utf-8")
    program = parse(src if src.endswith("\n") else src + "\n", str(p))
    team_decl = next((d for d in program.body if isinstance(d, TeamDecl)), None)
    config, registry = compile_team(team_decl)
else:
    config, registry = _default_team_config()
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (existing) |
| Config file | `pyproject.toml` (existing) |
| Quick run command | `python3 -m pytest tests/harness/em/ -x -q` |
| Full suite command | `python3 -m pytest tests/harness/em/ tests/harness/test_team_run_cli.py tests/harness/test_team_check_cli.py -q` |

**Do NOT run `tests/harness/board/` as part of V7 gate** — 13 pre-existing RED failures from V6 scaffolds.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VEM-CLI | `voss team run "<goal>"` exits 0 on stub provider | integration | `pytest tests/harness/test_team_run_cli.py::TestTeamRunCLI::test_stub_run_exits_zero` | ❌ Wave 0 |
| VEM-CLI | Run produces ≥1 card + RunFinal | integration | `pytest tests/harness/test_team_run_cli.py::TestTeamRunCLI::test_produces_card_and_run_final` | ❌ Wave 0 |
| VEM-CLI (fallback) | No team file → default roster | integration | `pytest tests/harness/test_team_run_cli.py::TestTeamRunCLI::test_default_roster_fallback` | ❌ Wave 0 |
| VEM-CLI (fallback) | Team file present → override | integration | `pytest tests/harness/test_team_run_cli.py::TestTeamRunCLI::test_team_file_override` | ❌ Wave 0 |
| VEM-PERSIST | run-final.json exists after run | integration | `pytest tests/harness/test_team_run_cli.py::TestTeamRunCLI::test_run_final_persisted` | ❌ Wave 0 |
| VEM-PERSIST | run-final.json contains RunFinal fields | unit | `pytest tests/harness/test_team_run_cli.py::TestRunFinalPersist::test_fields_serialized` | ❌ Wave 0 |
| VEM-PERSIST | run-final.json re-readable without re-run | unit | `pytest tests/harness/test_team_run_cli.py::TestRunFinalPersist::test_rereadable` | ❌ Wave 0 |
| VEM-SIGNOFF | CLI prints RunFinal summary + prompts | integration | `pytest tests/harness/test_team_run_cli.py::TestSignOff::test_prompt_appears` | ❌ Wave 0 |
| VEM-SIGNOFF | Approve recorded in run-final.json | integration | `pytest tests/harness/test_team_run_cli.py::TestSignOff::test_approve_recorded` | ❌ Wave 0 |
| VEM-SIGNOFF | Reject recorded, working tree unchanged | integration | `pytest tests/harness/test_team_run_cli.py::TestSignOff::test_reject_recorded_no_revert` | ❌ Wave 0 |
| verify | Cage: dispatch to undeclared role denied | unit (existing) | `pytest tests/harness/em/test_em_handle_cage.py` | ✅ |
| verify | Cage: no set_ceiling/set_p/extend_budget | unit (existing) | `pytest tests/harness/em/test_em_handle_cage.py::TestCageInvariant1Introspection` | ✅ |
| verify | kill/rescope lineage + routing_rationale recorded | unit (existing) | `pytest tests/harness/em/test_em_handle_dispatch.py tests/harness/em/test_em_lineage.py` | ✅ |
| verify | Existing O5 em tests pass | regression | `pytest tests/harness/em/ -x -q` | ✅ (79/79 green) |
| verify (bookkeeping) | Zero field changes RunRecord/SessionRecord/BudgetScope | schema-freeze | `pytest tests/voss/test_team_backcompat_regression.py -k schema` | ✅ |

### Sampling Rate

- **Per task commit:** `python3 -m pytest tests/harness/em/ -x -q`
- **Per wave merge:** `python3 -m pytest tests/harness/em/ tests/harness/test_team_run_cli.py -q`
- **Phase gate:** Full suite above green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/harness/test_team_run_cli.py` — covers VEM-CLI/PERSIST/SIGNOFF (all new tests)
- [ ] `voss/harness/cli.py` — `@team_group.command("run")` subcommand + `_default_team_config()` helper

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | yes (cage) | EMBoardHandle omissions; roster-check on dispatch |
| V5 Input Validation | yes | `goal` string is user-supplied; passed to em_loop as `idea=` |
| V6 Cryptography | no | — |

### EM Cage Trust Boundary

The `EMBoardHandle` is the primary trust boundary in this phase. V7 verifies that the boundary holds:

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| EM calls `set_ceiling()` / `extend_budget()` | Elevation of Privilege | Methods absent from EMBoardHandle (cage by API surface area) — verified by `test_em_handle_cage.py::TestCageInvariant1Introspection` |
| EM dispatches to an undeclared role | Spoofing / EoP | `dispatch_card` checks `role_id in team_config.roster_ids`; raises `EMCageViolation` — verified by `TestCageInvariant2NonRoster` |
| EM kills / rescopes a Done card | Tampering | `kill_card` / `rescope_card` check `column == "Done"` guard — verified by `TestCageInvariant4DoneCardProtection` |
| Sign-off bypass (no prompt) | Repudiation | `click.prompt` is not optional; CliRunner test with `input=` covers both paths |
| run-final.json path traversal | Tampering | `root_id` is a UUID hex (12 chars); path is `.voss/sessions/<root_id>/run-final.json`. Do NOT accept user-supplied root_id; always derive from `rf.root_id` (from SessionTreeNode). |
| run-final.json world-readable | Information Disclosure | `persist_path.chmod(0o600)` mirrors `_write_node_file` in session_tree.py |
| goal injection into em_loop idea= | Tampering | `idea` is passed as text to the EM stub/LLM; no shell execution; no path traversal. Low risk for stub path. |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| O5 em_loop reachable only in code | `voss team run` CLI composes full stack | V7 | Runnable product |
| RunFinal in-memory only | Persisted to `.voss/sessions/<root_id>/run-final.json` | V7 | V9 audit can read it |
| Fully autonomous (no human gate) | Autonomous-to-terminal + end sign-off | V7 | Human control invariant |
| O5 superseded | V7 is the canonical EM loop implementation | V7 | O5 artifacts retained as reference |

**Deprecated/outdated:**
- O5 designation: superseded by V7. O5 PLANs and SUMMARYs retained for reference; ROADMAP/STATE mark O5 superseded.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Default budget 500_000 tokens is appropriate for default-roster fallback | Pattern 2 | Budget too low → BudgetAllocationError on child allocation; increase to 1_000_000 |
| A2 | V7 tests should NOT include `tests/harness/board/` in their gate | Validation Architecture | If V6 is executed before V7, those tests would be green — include them |
| A3 | `asyncio.run()` in sync click command does not conflict with CliRunner | Pattern 6 | If test framework uses async CliRunner, use `_run_async_sync` instead |

**Note:** Claims about RunFinal fields, Board signature, and em_loop signature are all `[VERIFIED: direct execution]`. No assumed claims on the critical path.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | All harness code | ✓ | 3.13.x | — |
| pytest + pytest-asyncio | All tests | ✓ | present | — |
| click | CLI subcommand | ✓ | present | — |
| voss/harness/em/ (O5) | Core composition | ✓ | shipped | — |
| voss/harness/board/ (V5 partial) | Board construction | ✓ | shipped | — |
| voss/harness/session_tree.py (V4) | SessionTreeManager | ✓ | shipped | — |
| voss/harness/team.py (V3) | compile_team, DEFAULT_ROSTER | ✓ | shipped | — |

**Missing dependencies with no fallback:** None.
**Pre-existing RED tests (not V7's concern):** 13 tests in `tests/harness/board/` from V6 RED scaffolds. These fail before V7 and remain failing — V7 is not responsible for fixing them.

---

## Sources

### Primary (HIGH confidence)

- `voss/harness/em/loop.py` — em_loop exact signature, verified line-by-line
- `voss/harness/em/handle.py` — EMBoardHandle constructor + cage invariants, verified
- `voss/harness/em/tickets.py` — RunFinal dataclass fields, verified
- `voss/harness/em/stub.py` — DeterministicEMStub API, verified
- `voss/harness/board/machine.py` — Board.from_team_config current signature, verified
- `voss/harness/session_tree.py` — SessionTreeManager/SessionTreeNode construction, verified
- `voss/harness/team.py:48` — DEFAULT_ROSTER tuple, verified
- `voss/harness/team.py:588` — compile_team signature, verified
- `voss/harness/cli.py:3777` — team_group + team check pattern, verified
- `voss/harness/cli.py:3575` — asyncio.run pattern in sync click command, verified
- `tests/harness/em/conftest.py` — EMBoardHandle fixture construction pattern, verified
- `tests/harness/board/conftest.py` — DeterministicReviewerStub and build_test_team, verified
- Direct execution proof: full composition stack ran successfully in tempdir

### Secondary (MEDIUM confidence)

- V6-01-PLAN.md, V6-02-PLAN.md, V6-03-PLAN.md — V6 plan structure confirming which code does NOT yet exist
- `tests/harness/board/` RED scaffold tests — confirmed V6-02/03/04 unexecuted
- `tests/harness/test_team_check_cli.py` — CliRunner+team pattern reference

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages already present; no new installs
- Composition wiring: HIGH — full stack executed in Python REPL, produced valid RunFinal
- RunFinal fields: HIGH — inspected `dataclasses.fields(RunFinal)` directly
- V6 readiness gap: HIGH — confirmed via import tests, plan file inspection, and RED test failures
- Architecture: HIGH — em_loop, Board, SessionTreeManager API verified directly
- Sign-off pattern: HIGH — click.prompt Choice with CliRunner tested directly

**Research date:** 2026-06-06
**Valid until:** 2026-07-06 (30 days; all APIs are stable harness code)

---

## RESEARCH COMPLETE

**Phase:** V7 - Engineering Manager Loop (supersedes O5)
**Confidence:** HIGH

### Key Findings

1. **Full composition stack works today.** `SessionTreeManager → Board.from_team_config → EMBoardHandle → em_loop` is proven end-to-end in a tempdir with stub provider. All V4/V5/O5 modules are importable and functionally correct.

2. **V6 plans 02-05 are NOT yet executed** — critical for planner. `Board.from_team_config` currently accepts only a single `reviewer` parameter (pre-V6-03). V7 must use `reviewer=DeterministicReviewerStub(...)` for tests. The 13 RED board test failures are pre-existing V6 scaffolds; V7 acceptance gate must target `tests/harness/em/` only.

3. **RunFinal does not contain evidence_refs/diff_summary/residual.** The CONTEXT.md description was aspirational. The shipped RunFinal has 10 fields. The sidecar adds a `sign_off` superset key. `dataclasses.asdict(rf)` serializes correctly.

4. **Pre-spawn one board card before em_loop.** `em_loop` does not call `board.spawn_card`. The CLI must call `await board.spawn_card(risk_tier="med")` before the loop so `RunFinal.total_cards >= 1`.

5. **Async-drive pattern:** `asyncio.run(em_loop(...))` in a sync click command. Mirror of `consensus_cmd` at cli.py:3575. No `_run_turn_cancellable` needed.

6. **Default-roster fallback is a ~15-line direct construction.** No parser needed. `subagent_spec_from_role(..., apply_role_defaults=True)` fills model/scope/tools from `_ROLE_DEFAULTS`. Watch out: model tier resolution requires `get_model_tiers()` to be configured (use `monkeypatch` in tests).

### File Created

`.planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | No new packages; all code verified |
| Composition wiring | HIGH | Direct execution proof in Python |
| RunFinal serialization | HIGH | `dataclasses.asdict` verified |
| V6 readiness gap | HIGH | Import tests + RED scaffold confirmation |
| Sign-off pattern | HIGH | click.prompt Choice tested with CliRunner |
| Default-roster path | HIGH | Direct construction verified |

### Open Questions

All resolved. See §Open Questions for pinned answers.

### Ready for Planning

Research complete. Planner can now create PLAN.md files for V7.
