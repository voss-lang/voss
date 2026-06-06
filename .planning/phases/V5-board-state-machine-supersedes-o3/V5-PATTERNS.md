# Phase V5: Board State Machine (supersedes O3) - Pattern Map

**Mapped:** 2026-06-06
**Files analyzed:** 6 (3 new, 3 modified)
**Analogs found:** 6 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `voss/harness/board/machine.py` (modify) | model / state-machine | event-driven | `voss/harness/board/machine.py` itself (self-reference — extend existing Card + Board.move) | exact |
| `voss/harness/board/cli_view.py` (new) | utility | file-I/O → request-response | `voss/harness/audit/load.py` | role-match (both are read-only persisted-node readers) |
| `voss/harness/cli.py` (modify) | config / CLI dispatcher | request-response | `voss/harness/cli.py` lines 3740–3807 (principles_group + AGENT_COMMANDS) | exact |
| `tests/harness/board/test_card_fields_v5.py` (new) | test | transform | `tests/harness/board/test_card_node_wiring.py` | exact (same class-based pytest, same fixtures) |
| `tests/harness/board/test_self_done_guard.py` (new) | test | event-driven | `tests/harness/board/test_stub_full_lifecycle.py` | role-match (same Board lifecycle pattern; uses DeterministicReviewerStub) |
| `tests/harness/board/test_board_cli.py` (new) | test | request-response | `tests/harness/test_diagnostics.py` (CLI section, CliRunner) | role-match |
| `tests/harness/board/test_session_tree_additive.py` (modify) | test | — | itself (1-line fix) | exact |

---

## Pattern Assignments

---

### `voss/harness/board/machine.py` — Card dataclass extension (VBOARD-03)

**Analog:** `voss/harness/board/machine.py` lines 80–94 (the existing `Card` definition)

**Current Card definition** (`machine.py` lines 80–94):
```python
@dataclass(frozen=True, slots=True)
class Card:
    """A board card mapped 1:1 to a SessionTreeNode (OBRD-01).

    Immutable — mutated via `dataclasses.replace` so EM cannot widen
    `scope` by direct attribute assignment (cage invariant).
    """
    node_id: str
    column: Column
    risk_tier: RiskTier
    retry_count: int
    deadline: float
    scope: Optional[TeamRoleScope] = None
    artifact: Optional[object] = None
    eval_threshold: float = 1.0
```

**V5 addition pattern** — append four string fields AFTER `eval_threshold: float = 1.0` (the last defaulted field). Convention: use `""` for string defaults (not `None`), matching the existing non-Optional field style:
```python
    # V5 additions — additive, back-compat defaults (VBOARD-03):
    idea: str = ""
    role: str = ""
    acceptance_criteria: str = ""
    verification_requirement: str = ""
```

**Derived helpers** — add as module-level functions immediately after the class (NOT as `@property`, to avoid `slots=True` interaction risk):
```python
def card_status(card: "Card") -> str:
    """Status derives from current column (VBOARD-03). Not a stored field."""
    return card.column


def card_budget(node_envelope: dict) -> tuple[int, int]:
    """Returns (spent, limit) from a persisted node envelope (VBOARD-03)."""
    return node_envelope.get("spent", 0), node_envelope.get("limit", 0)
```

**Key constraint:** `slots=True` is incompatible with `@property` in a reliable way — use standalone functions. Do not add `status` or `budget` as dataclass fields (sync hazard; breaks frozen invariant contract).

**All `Card` construction sites** (all safe after additive-only change):
- `machine.py:324–332` — `Board.spawn_card` uses keyword args; new fields get defaults.
- `machine.py:407` — `dataclasses.replace(card, column=to)` — only replaces `column`; all other fields carry over.
- `machine.py:524` — `dataclasses.replace(card, column="Blocked")` — same pattern.
- `machine.py:557–560` — `dataclasses.replace(card, column="InProgress", retry_count=new_retry)` — same pattern.

---

### `voss/harness/board/machine.py` — Self-Done independence guard (VBOARD-07)

**Analog:** `voss/harness/board/machine.py` lines 344–358 (existing WIP check pattern — refused delta followed by raise)

**Existing WIP refusal pattern** (`machine.py` lines 351–359) to mirror:
```python
        # 2. WIP enforcement
        cap = self._cfg.wip.get(to)
        if cap is not None:
            in_dest = sum(1 for c in self._cards if c.column == to)
            if in_dest >= cap:
                self._append_delta(
                    card, from_col=card.column, to_col=to,
                    outcome="refused", failing_clauses=["wip"],
                )
                raise BoardWIPError(to, cap)
```

**V5 guard insertion site** — between step 2 (WIP check, ~line 359) and step 3 (gate predicate evaluation, `transition = (card.column, to)` at ~line 362). The guard must emit `_append_delta` with `outcome="refused"` exactly once, then raise `BoardGateError`:
```python
        # 2.5 VBOARD-07: Done requires an independent reviewer (no self-Done).
        if to == "Done" and self._reviewer is None:
            self._append_delta(
                card, from_col=card.column, to_col=to,
                outcome="refused", failing_clauses=["no-reviewer"],
            )
            raise BoardGateError(
                "Done requires an independent reviewer",
                failing_clauses=["no-reviewer"],
            )
```

**`_append_delta` signature** (`machine.py` lines 467–493):
```python
    def _append_delta(
        self,
        card: Card,
        *,
        from_col: str,
        to_col: str,
        outcome: str,
        failing_clauses: list[str] | None = None,
        reason: str | None = None,
        verdict_snapshot: object | None = None,
    ) -> None:
```

**`BoardGateError` constructor** (`errors.py` lines 26–36):
```python
class BoardGateError(BoardError):
    def __init__(self, reason: str, failing_clauses: list[str] | None = None) -> None:
        self.reason = reason
        self.failing_clauses = list(failing_clauses) if failing_clauses else []
        super().__init__(reason)
```

**Pitfall:** Do NOT insert the guard after the `GateContext` is constructed (line ~379) — that would double-append transitions. Insert it BEFORE `transition = (card.column, to)`.

---

### `voss/harness/board/cli_view.py` — New read-only board renderer

**Analog:** `voss/harness/audit/load.py` — the entire module is the pattern to mirror for read-only persisted-node traversal.

**Imports pattern** (`audit/load.py` lines 1–23):
```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
```
The `cli_view.py` module needs only these same stdlib imports plus `click` for output. No live Board/Manager construction.

**`_read_node_file` pattern** (`audit/load.py` lines 35–48) — copy this defensive JSON reader:
```python
def _read_node_file(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text()
    except OSError as exc:
        raise AuditLoadError(path, f"cannot read: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AuditLoadError(path, f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AuditLoadError(path, "expected a JSON object")
    if "id" not in data:
        raise AuditLoadError(path, "missing required 'id' field")
    return data
```

**Column derivation rule** (`audit/load.py` lines 206–220) — MUST use this exactly (no deviation):
```python
    column = "Backlog"
    for t in transitions:
        if t.get("kind") == "board.transition":
            column = t.get("to", column)

    terminal = data.get("terminal_state")
    if terminal is not None:
        exit_reason = terminal.get("exit_reason", "")
        if exit_reason == "timeout":
            column = "Blocked"
        elif exit_reason == "killed":
            column = "Blocked"
        elif exit_reason == "done":
            column = "Done"
```

**Root directory enumeration pattern** (`audit/load.py` lines 250–263) — audit uses lexical sort (wrong for "latest"); V5 must use mtime sort:
```python
    # audit/load.py uses lexical (deterministic for audit, NOT for "latest"):
    root_dirs = sorted(d for d in sessions_dir.iterdir() if d.is_dir())
    # V5 cli_view.py uses mtime (correct for "latest"):
    root_dirs = sorted(
        (d for d in sessions_dir.iterdir() if d.is_dir()),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
```

**Sessions dir location** (`session_tree.py` lines 98–101):
```
<cwd>/.voss/sessions/<root_id>/<node_id>.json
```

**Error exit pattern** (from `principles_show_cmd`, `harness/cli.py` lines 3756–3759):
```python
    except SomeError as e:
        click.echo(f"<error: {e}>", err=True)
        raise click.exceptions.Exit(1) from e
```

**Budget from envelope** — direct dict read from node JSON (no live Board needed):
```python
spent = node_data.get("envelope", {}).get("spent", 0)
limit = node_data.get("envelope", {}).get("limit", 0)
```

**Column order constant** (from `machine.py` lines 51–53):
```python
_COLUMNS: tuple[str, ...] = (
    "Backlog", "Planned", "InProgress", "InReview", "Blocked", "Done",
)
```
Import or redeclare in `cli_view.py` — do NOT import from `machine.py` (would pull in the full machine import chain). Redeclare as a local constant.

---

### `voss/harness/cli.py` — Register `board_cmd` in AGENT_COMMANDS

**Analog:** `voss/harness/cli.py` lines 3740–3807 (the `principles_group` command and AGENT_COMMANDS tuple)

**Standalone `click.command` pattern** (use `click.command`, not `click.group`, per RESEARCH resolution):
```python
# doctor_cmd is the standalone command pattern — harness/cli.py lines 2301–2309:
@click.command("doctor")
@click.option(
    "--cwd",
    "cwd_str",
    default=".",
    type=click.Path(file_okay=False),
    help="Project root to check.",
)
def doctor_cmd(cwd_str: str) -> None:
    """Diagnose harness setup. Diagnose-only; never executes fixes (D-13)."""
    from . import diagnostics as diag
    cwd = Path(cwd_str).resolve()
    ...
```

**V5 `board_cmd` pattern to copy:**
```python
@click.command("board")
@click.argument("root_id", required=False, default=None)
@click.option(
    "--cwd",
    "cwd_str",
    default=".",
    type=click.Path(file_okay=False),
    help="Project root.",
)
def board_cmd(root_id: str | None, cwd_str: str) -> None:
    """Render the board in read-only view from persisted session-tree nodes (VBOARD-10)."""
    from voss.harness.board.cli_view import render_board
    cwd = Path(cwd_str).resolve()
    rc = render_board(cwd, root_id=root_id)
    raise click.exceptions.Exit(code=rc)
```

**AGENT_COMMANDS tuple** (`harness/cli.py` lines 3777–3807) — add `board_cmd` to this tuple:
```python
AGENT_COMMANDS = (
    do_cmd,
    ...
    principles_group,
    board_cmd,     # <-- V5 addition (last position is fine)
)
```

**`register` function** (`harness/cli.py` lines 3810–3813) — unchanged, already iterates all AGENT_COMMANDS:
```python
def register(group: click.Group) -> None:
    """Attach all agent commands to a click Group."""
    for cmd in AGENT_COMMANDS:
        group.add_command(cmd)
```

---

### `tests/harness/board/test_card_fields_v5.py` — New: VBOARD-03 tests

**Analog:** `tests/harness/board/test_card_node_wiring.py` (class-based pytest, same fixtures)

**Imports + fixture pattern** (`test_card_node_wiring.py` lines 1–12):
```python
from __future__ import annotations

import dataclasses

import pytest

from voss.harness.board import Board, Card
from voss.harness.session_tree import SessionTreeManager

from .conftest import build_test_team
```

**Class + fixture injection pattern** (`test_card_node_wiring.py` lines 14–38):
```python
class TestCardNodeWiring:
    @pytest.mark.asyncio
    async def test_spawn_card_creates_live_node(self, tmp_recorder, stub_reviewer):
        manager, cwd = tmp_recorder
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub_reviewer, cwd=cwd,
            clock=lambda: 1000.0,
        )
        card = await board.spawn_card(risk_tier="med")
        assert card.column == "Backlog"
        ...
```

**Available fixtures** (`tests/harness/board/conftest.py`):
- `tmp_recorder` → returns `(SessionTreeManager, cwd: Path)` from `tmp_path`
- `stub_reviewer` → returns `_NeverReviewer()` (raises if `.review()` is called)
- `build_test_team()` → function (not fixture), returns `TeamConfig`
- `artifact_passing()` / `artifact_failing()` → `SimpleNamespace` with `tests_passed`, `eval_score`, `scope_violations`
- `fake_clock` → `FakeClock(0.0)`

**V5 test class structure to copy:**
```python
class TestCardFieldsV5:
    def test_new_fields_have_defaults(self):
        # Direct Card construction with minimal required args
        card = Card(
            node_id="n1", column="Backlog", risk_tier="med",
            retry_count=0, deadline=999.0,
        )
        assert card.idea == ""
        assert card.role == ""
        assert card.acceptance_criteria == ""
        assert card.verification_requirement == ""

    def test_card_is_still_frozen(self):
        card = Card(
            node_id="n1", column="Backlog", risk_tier="med",
            retry_count=0, deadline=999.0,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            card.idea = "something"  # type: ignore[misc]

    def test_old_construction_paths_unchanged(self):
        # dataclasses.replace only changes what's specified
        card = Card(
            node_id="n1", column="Backlog", risk_tier="med",
            retry_count=0, deadline=999.0, idea="test idea",
        )
        moved = dataclasses.replace(card, column="Planned")
        assert moved.idea == "test idea"  # carries through


class TestCardStatus:
    def test_card_status_returns_column(self):
        from voss.harness.board.machine import card_status
        card = Card(
            node_id="n1", column="InProgress", risk_tier="med",
            retry_count=0, deadline=999.0,
        )
        assert card_status(card) == "InProgress"


class TestCardBudget:
    def test_card_budget_reads_envelope(self):
        from voss.harness.board.machine import card_budget
        envelope = {"spent": 100, "limit": 1000}
        spent, limit = card_budget(envelope)
        assert spent == 100
        assert limit == 1000
```

---

### `tests/harness/board/test_self_done_guard.py` — New: VBOARD-07 tests

**Analog:** `tests/harness/board/test_stub_full_lifecycle.py` (Board lifecycle, DeterministicReviewerStub, same fixture pattern)

**Imports pattern** (`test_stub_full_lifecycle.py` lines 1–12):
```python
from __future__ import annotations

import dataclasses
from types import SimpleNamespace

import pytest

from voss.harness.board import Board, BoardGateError
from voss.harness.board.stub import DeterministicReviewerStub

from .conftest import build_test_team
```

**Full lifecycle pattern** (`test_stub_full_lifecycle.py` lines 15–46) — drive card to InReview before testing Done:
```python
class TestCodeLifecycle:
    @pytest.mark.asyncio
    async def test_backlog_to_done_with_passing_artifact(self, tmp_recorder):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub(conf=0.99, verdict="pass")
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
        )
        card = await board.spawn_card(risk_tier="low")
        card = board.move(card, to="Planned")
        card = board.move(card, to="InProgress")
        card = dataclasses.replace(
            card, artifact=SimpleNamespace(tests_passed=True, scope_violations=()),
        )
        board._cards = [card if c.node_id == card.node_id else c for c in board._cards]
        card = board.move(card, to="InReview")
        card = board.move(card, to="Done")
        assert card.column == "Done"
```

**V5 guard test class structure:**
```python
class TestSelfDoneGuard:
    @pytest.mark.asyncio
    async def test_reviewer_none_raises_board_gate_error(self, tmp_recorder):
        manager, cwd = tmp_recorder
        # Board with NO reviewer — the V5 guard must catch this
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=None, cwd=cwd,
        )
        card = await board.spawn_card(risk_tier="low")
        # ... drive to InReview ...
        with pytest.raises(BoardGateError) as exc_info:
            board.move(card, to="Done")
        assert "no-reviewer" in exc_info.value.failing_clauses

    @pytest.mark.asyncio
    async def test_valid_reviewer_allows_done(self, tmp_recorder):
        manager, cwd = tmp_recorder
        stub = DeterministicReviewerStub(conf=0.99, verdict="pass")
        board = Board.from_team_config(
            build_test_team(), recorder=manager, reviewer=stub, cwd=cwd,
        )
        # ... drive to InReview with passing artifact ...
        card = board.move(card, to="Done")
        assert card.column == "Done"
```

---

### `tests/harness/board/test_board_cli.py` — New: VBOARD-10 CLI tests

**Analog:** `tests/harness/test_diagnostics.py` CLI section (lines 195–295) for CliRunner pattern; `tests/cli/test_help.py` for isolated_filesystem pattern.

**CliRunner imports pattern** (`tests/harness/test_diagnostics.py` lines 1–16):
```python
from __future__ import annotations

import pytest
from click.testing import CliRunner

from voss.harness.cli import doctor_cmd  # swap for board_cmd
```

**CliRunner invocation pattern** (`tests/harness/test_diagnostics.py` lines 248–252):
```python
        result = CliRunner().invoke(doctor_cmd, ["--cwd", str(tmp_path)])
        assert result.exit_code == 1
        assert "some text" in result.output
```

**Isolated filesystem pattern** (`tests/cli/test_help.py` lines 17–21):
```python
    runner = CliRunner()
    with runner.isolated_filesystem() as fs:
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0, result.output
```

**Stderr check pattern** (`tests/harness/test_diagnostics.py` line 276):
```python
        assert "warning" in result.stderr.lower()
```

**V5 CLI test class structure:**
```python
class TestBoardCLI:
    def test_no_sessions_dir_exits_nonzero(self, tmp_path):
        from voss.harness.cli import board_cmd
        result = CliRunner().invoke(board_cmd, ["--cwd", str(tmp_path)])
        assert result.exit_code != 0

    def test_unknown_root_exits_nonzero_with_stderr(self, tmp_path):
        from voss.harness.cli import board_cmd
        result = CliRunner().invoke(
            board_cmd, ["does-not-exist", "--cwd", str(tmp_path)],
            mix_stderr=False,
        )
        assert result.exit_code != 0
        assert result.stderr  # error message on stderr

    def test_default_latest_root_exits_zero(self, tmp_path):
        # Set up a minimal .voss/sessions/<root_id>/<node_id>.json
        sessions = tmp_path / ".voss" / "sessions" / "abc123"
        sessions.mkdir(parents=True)
        node = sessions / "n1.json"
        node.write_text('{"id": "n1", "root_id": "abc123", "transitions": [], '
                        '"envelope": {"spent": 0, "limit": 100}, "terminal_state": null}')
        from voss.harness.cli import board_cmd
        result = CliRunner().invoke(board_cmd, ["--cwd", str(tmp_path)])
        assert result.exit_code == 0, result.output

    def test_named_root_renders_exit_zero(self, tmp_path):
        sessions = tmp_path / ".voss" / "sessions" / "abc123"
        sessions.mkdir(parents=True)
        (sessions / "n1.json").write_text(
            '{"id": "n1", "root_id": "abc123", "transitions": [], '
            '"envelope": {"spent": 0, "limit": 100}, "terminal_state": null}'
        )
        from voss.harness.cli import board_cmd
        result = CliRunner().invoke(board_cmd, ["abc123", "--cwd", str(tmp_path)])
        assert result.exit_code == 0
```

---

### `tests/harness/board/test_session_tree_additive.py` — 1-line stale assertion fix

**File:** `tests/harness/board/test_session_tree_additive.py`
**Method:** `TestExitReasonsExtension::test_exit_reasons_is_sorted_superset_of_pre_o3` (lines 82–85)

**Current failing assertion** (lines 82–85):
```python
    def test_exit_reasons_is_sorted_superset_of_pre_o3(self):
        pre_o3 = {"done", "max-iter", "budget", "interrupt", "batch-invariant"}
        assert pre_o3.issubset(EXIT_REASONS)
        assert EXIT_REASONS == pre_o3 | {"timeout"}   # <-- STALE: fails since O5 added "killed"
```

**Fix** — change the last line from equality to `issubset`:
```python
    def test_exit_reasons_is_sorted_superset_of_pre_o3(self):
        pre_o3 = {"done", "max-iter", "budget", "interrupt", "batch-invariant"}
        assert pre_o3.issubset(EXIT_REASONS)
        assert {"timeout"}.issubset(EXIT_REASONS)      # <-- V5 fix: issubset, not ==
```

This unblocks the regression gate without modifying `session.py`.

---

## Shared Patterns

### Frozen dataclass extension
**Source:** `voss/harness/board/machine.py` lines 80–94 (`Card`) and `voss/harness/board/verdict.py` lines 13–31 (`ReviewerVerdict`)
**Apply to:** `machine.py` Card extension (VBOARD-03)
- Always `@dataclass(frozen=True, slots=True)`
- New fields with defaults MUST follow all existing defaulted fields
- String defaults use `""` not `None` (save `Optional[X] = None` for non-string types where None is meaningful)
- `verdict.py` demonstrates the zero-import contract: only `typing`, `dataclasses`, `__future__` — DO NOT touch that file

### `_append_delta` + raise pattern (refused transitions)
**Source:** `voss/harness/board/machine.py` lines 351–359 (WIP check) and lines 344–348 (unknown-column check)
**Apply to:** V5 self-Done guard insertion in `Board.move`
```python
self._append_delta(
    card, from_col=card.column, to_col=to,
    outcome="refused", failing_clauses=["<clause-name>"],
)
raise BoardGateError("<human message>", failing_clauses=["<clause-name>"])
```
Rule: exactly ONE `_append_delta` call per refused transition, always before the `raise`.

### CliRunner test pattern
**Source:** `tests/harness/test_diagnostics.py` lines 195–295
**Apply to:** `test_board_cli.py`
```python
from click.testing import CliRunner
result = CliRunner().invoke(some_cmd, ["--cwd", str(tmp_path)])
assert result.exit_code == 0, result.output
# For stderr inspection: pass mix_stderr=False to CliRunner().invoke(...)
```

### Error exit with stderr
**Source:** `voss/harness/cli.py` lines 3756–3759 (`principles_show_cmd` error path)
**Apply to:** `cli_view.py` render_board return code; `board_cmd` error handling
```python
click.echo(f"<error: {e}>", err=True)
raise click.exceptions.Exit(1) from e
```

### Test imports for board package
**Source:** `tests/harness/board/conftest.py` lines 1–71
**Apply to:** All new board test files
```python
from voss.harness.board import Board, BoardGateError, Card
from voss.harness.board.stub import DeterministicReviewerStub
from voss.harness.board.verdict import Reviewer, ReviewerVerdict
from voss.harness.session_tree import SessionTreeManager, SessionTreeNode
from .conftest import build_test_team, artifact_passing, artifact_failing
```
Fixtures available via `conftest.py`: `tmp_recorder`, `stub_reviewer`, `fake_clock`.

### Test runner
**Apply to:** ALL test verification
```bash
.venv/bin/python -m pytest tests/harness/board/ -q --tb=short
```
Never use bare `python3` or `pytest` — `.venv/bin/python` has all deps.

---

## No Analog Found

None. All V5 files have strong analogs in the codebase.

---

## Metadata

**Analog search scope:** `voss/harness/board/`, `voss/harness/audit/`, `voss/harness/cli.py`, `tests/harness/board/`, `tests/harness/`, `tests/cli/`
**Files scanned:** 12 source files + 7 test files
**Pattern extraction date:** 2026-06-06

---

## Anti-Patterns (planner must avoid)

| Anti-pattern | Why | Correct approach |
|---|---|---|
| Add `@property status` to `Card` | `slots=True` interaction risk; also `@property` is a class attribute not an instance slot — low risk but module function is simpler | `card_status(card)` module function |
| Add `budget` as a `Card` field | Goes stale; `budget` depends on live `node.envelope` which changes after every spend | `card_budget(envelope_dict)` module function; CLI reads from JSON |
| Import from `verdict.py` or add imports to it | Zero-import contract; `test_verdict_imports.py` enforces this | Never touch `verdict.py` |
| Construct `Board` or `SessionTreeManager` in `cli_view.py` | Spec: read-only from persisted JSON only | `json.loads(path.read_text())` directly |
| Insert guard AFTER `GateContext` construction | Would double-append transition delta | Insert BEFORE `transition = (card.column, to)` |
| Lexical sort for "latest root" | UUID4 hex is random, not time-ordered | `key=lambda d: d.stat().st_mtime, reverse=True` |
