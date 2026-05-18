# Phase O1: Session-Tree Substrate + Budget Fan-out — Pattern Map

**Mapped:** 2026-05-18
**Files analyzed:** 5 (2 new, 3 modified)
**Analogs found:** 5 / 5

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `voss/harness/session_tree.py` (NEW) | model + service | CRUD + file-I/O | `voss/harness/session.py` | role-match (same fixed-field dataclass + `_hydrate`-style unknown-key drop, same `.voss/sessions/` file pattern) |
| `voss/harness/subagents.py` (MODIFY) | service | request-response | `voss/harness/subagents.py` itself | self (surgical addition of `node` kwarg + D-03 try/except boundary) |
| `voss/harness/recorder.py` (READ-ONLY reference) | model | CRUD | — | reference only (D-03 calls `finalize()`; no modification needed) |
| `voss_runtime/budget.py` (READ-ONLY reference) | service | event-driven | — | reference only (composed unchanged per D-02) |
| `tests/harness/test_session_tree.py` (NEW) | test | — | `tests/harness/test_recorder_iterations.py` | exact (class-based pytest, `tmp_path`, no provider, no git; `test_session_redaction.py` for schema-lock style) |

---

## Pattern Assignments

### `voss/harness/session_tree.py` (NEW — model + file-I/O)

**Primary analog:** `voss/harness/session.py`
**Secondary analog:** `voss/harness/recorder.py` (for `RunRecorder.start()` / `finalize()` structure)

---

#### Imports pattern — copy from `voss/harness/session.py` lines 43–55

```python
from __future__ import annotations

import dataclasses
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
```

Add for O1:
```python
import asyncio
from voss_runtime import BudgetScope
from voss_runtime.exceptions import BudgetExceededError
```

**Rationale:** `session.py` lines 43-55 establish the exact import idiom for harness dataclasses. `asyncio` follows the `asyncio.Semaphore` pattern already in `agent.py`. `BudgetScope` / `BudgetExceededError` are the D-02 and D-03 signals.

---

#### Fixed-field dataclass pattern — copy from `voss/harness/session.py` lines 79–175

`SessionRecord` (lines 149–175) and `RunRecord` (lines 116–147) demonstrate the two required conventions:

1. **`@dataclass` with typed fields and `field(default_factory=...)`:**
```python
# session.py lines 149-175
@dataclass
class SessionRecord:
    id: str
    name: str
    cwd: str
    model: str
    started_at: str
    updated_at: str
    total_cost_usd: float = 0.0
    turns: list[dict] = field(default_factory=list)
    runs: list[dict] = field(default_factory=list)
    parent_id: Optional[str] = None
    parent_turn_index: Optional[int] = None

    @classmethod
    def new(cls, *, cwd: Path, model: str, name: str = "") -> "SessionRecord":
        sid = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return cls(
            id=sid,
            name=name or f"session-{sid[:8]}",
            cwd=str(cwd.resolve()),
            model=model,
            started_at=now,
            updated_at=now,
        )
```

**The new `SessionTreeNode` MUST mirror this exact style.** The locked schema is `{id, root_id, parent_run_id, envelope{limit, spent}, terminal_state, created_at, ended_at, rejected_raises}`. The `_budget` field is a runtime-only field that must NOT be persisted — model it like `RunRecorder._iterations` (leading underscore, excluded from `asdict` output via a pop before writing).

2. **`_hydrate` unknown-key drop pattern (session.py lines 184–191):**
```python
# session.py lines 184-191
_SESSION_FIELDS = {f.name for f in dataclasses.fields(SessionRecord)}

def _hydrate(data: dict) -> SessionRecord:
    kept = {k: v for k, v in data.items() if k in _SESSION_FIELDS}
    kept.setdefault("turns", [])
    kept.setdefault("runs", [])
    return SessionRecord(**kept)
```

`session_tree.py` needs an equivalent `_hydrate_node(data: dict) -> SessionTreeNode` using the same pattern — keep only known fields, set list-type defaults, reconstruct. This is what makes node JSON forward-compatible (O6 can write extra fields; the substrate drops them silently).

---

#### Node id generation — copy from `voss/harness/recorder.py` lines 50–54

```python
# recorder.py lines 50-54
@classmethod
def start(cls) -> "RunRecorder":
    return cls(
        id=uuid.uuid4().hex[:12],
        started_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
```

`SessionTreeNode.create_root()` and `SessionTreeNode` child creation both use `uuid.uuid4().hex[:12]` — identical to `RunRecorder.start()` and `SessionRecord.new()`.

---

#### File persistence pattern — copy from `voss/harness/session.py` lines 205–213

```python
# session.py lines 205-213
def save(record: SessionRecord, history: EpisodicMemory) -> Path:
    record.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record.turns = history.last(10_000)
    cwd = Path(record.cwd)
    path = _sessions_dir(cwd) / f"{record.id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(record), indent=2))
    path.chmod(0o600)
    return path
```

The `_write_node_file` function in `session_tree.py` copies this exactly:
- `path.parent.mkdir(parents=True, exist_ok=True)` — creates `.voss/sessions/<root_id>/` directory
- `path.write_text(json.dumps(..., indent=2))` — same serializer, same indent
- `path.chmod(0o600)` — same permission posture (durable state)

**Difference:** path is `.voss/sessions/<node.root_id>/<node.id>.json` (not `<id>.json` at the flat level). Serialization uses `dataclasses.asdict(node)` with a pop of the `_budget` key before writing (mirrors `asdict(record)` but must drop the runtime-only field).

---

#### `asyncio.Lock` for the allocation guard — copy from `voss/harness/agent.py` pattern (referenced in RESEARCH.md line 487)

```python
# agent.py (concurrency pattern, verified in RESEARCH.md)
sem = asyncio.Semaphore(cap)
async with sem:
    results[slot] = await _invoke_step_with_gate(...)
```

`SessionTreeManager._lock = asyncio.Lock()` follows the identical `async with self._lock:` pattern. The lock wraps ONLY the check-and-append in `allocate_child`, not the `run_turn` call.

---

### `voss/harness/subagents.py` (MODIFY — surgical addition)

**Analog:** `voss/harness/subagents.py` itself (self-analog — surgical addition only)

The existing `run_subagent` function (lines 76–103) is the sole modification target. The modification adds:
1. Two new optional kwargs: `node: SessionTreeNode | None = None` and `reserve: int = 0`
2. A `try/except BudgetExceededError` boundary wrapping the `run_turn` call
3. A soft-exit check on `result.run.exit_reason == "budget"` after `run_turn` returns
4. A node-finalize call on both paths

**Existing signature to extend (lines 76–87):**
```python
# subagents.py lines 76-87
async def run_subagent(
    *,
    agent_id: str,
    task: str,
    registry: SubagentRegistry,
    cwd: Path,
    renderer: Renderer,
    provider: Any,
    model: str,
    gate: PermissionGate,
    cognition: Any = None,
) -> str:
```

Add after `cognition: Any = None`:
```python
    node: "SessionTreeNode | None" = None,   # D-01/D-02/D-03: tree node
    reserve: int = 0,                          # D-03: tokens reserved for finalize
```

**Existing body to wrap (lines 88–103):**
```python
# subagents.py lines 88-103
    spec = registry.get(agent_id)
    if spec is None:
        return f"<error: unknown subagent {agent_id!r}>"
    child_tools = make_toolset(cwd, renderer=renderer)
    result = await run_turn(
        agent_task(spec, task),
        tools=child_tools,
        cwd=cwd,
        renderer=renderer,
        model=model,
        provider=provider,
        history=EpisodicMemory(capacity=20),
        permissions=gate,
        cognition=cognition,
    )
    return result.final
```

The `run_turn` call stays unchanged except for the addition of `token_budget=` when `node` is provided. The `try/except` wraps only from the `run_turn` call onward — the early-return guard (`spec is None`) stays outside the boundary.

**CRITICAL constraint from `test_subagent_recursion.py` (lines 23–40):** Adding `node` and `reserve` kwargs is safe — those tests only check for ABSENCE of `depth` / `max_depth` / `MAX_DEPTH` / `DEPTH_LIMIT` / `RECURSION_LIMIT`. Do NOT add any of those names.

---

### `tests/harness/test_session_tree.py` (NEW — test)

**Primary analog:** `tests/harness/test_recorder_iterations.py`
**Secondary analog:** `tests/harness/test_session_redaction.py` (for schema-lock style tests)
**Tertiary analog:** `tests/harness/test_session.py` (for `tmp_path` + file persistence tests)

---

#### Module header pattern — copy from `test_recorder_iterations.py` lines 1–17

```python
# test_recorder_iterations.py lines 1-17
"""T1-01: RunRecorder.begin_iteration / end_iteration + finalize wiring.

Locks the per-iteration capture API. Tests cover behavior, validation, and
finalize forwarding to RunRecord.iterations / iteration_count / exit_reason
/ iteration_total_*_tokens.

No provider, no git. Plan stub is a SimpleNamespace with model_dump.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from voss.harness.recorder import RunRecorder
```

Replace with O1-appropriate docstring and import:
```python
"""O1: SessionTreeNode / SessionTreeManager — tree persistence, budget fan-out, drain finalize.

No provider, no git. Tests cover node creation, allocation invariant, drain finalize,
cap-raise guard, concurrency no-oversell, and schema isolation (redaction invariant).
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from voss.harness.session_tree import (
    BudgetCapRaiseError,
    SessionTreeManager,
    SessionTreeNode,
)
```

---

#### Class-based test structure — copy from `test_recorder_iterations.py` lines 30–130

```python
# test_recorder_iterations.py lines 30-131 (representative structure)
class TestBeginIteration:
    def test_first_call_returns_index_zero_with_started_at(self) -> None:
        rec = RunRecorder.start()
        it = rec.begin_iteration()
        assert it.index == 0
        assert it.started_at != ""
        assert it.ended_at == ""

    def test_two_calls_yield_sequential_indices(self) -> None:
        ...

class TestEndIteration:
    def test_populates_open_iteration(self) -> None:
        ...
    def test_invalid_exit_reason_raises(self) -> None:
        rec = RunRecorder.start()
        rec.begin_iteration()
        with pytest.raises(ValueError):
            rec.end_iteration(..., exit_reason="quit")

class TestFinalizeForwarding:
    def test_finalize_forwards_iterations_and_count(self, tmp_path: Path) -> None:
        ...
```

O1 test class structure (from RESEARCH.md Validation Architecture, lines 699–708):
```
class TestTreePersistence:      # REQ-1
class TestBudgetFanOut:         # REQ-2a, REQ-2b
class TestDrainFinalize:        # REQ-3
class TestNoOpenNodes:          # REQ-3b
class TestCapRaiseGuard:        # REQ-4a, REQ-4b
class TestConcurrency:          # REQ-7 (concurrent no-oversell)
```

---

#### `tmp_path` fixture usage — copy from `test_session.py` lines 13–25

```python
# test_session.py lines 13-25
class TestSessionRoundtrip:
    def test_save_then_list(self, tmp_path: Path) -> None:
        history = EpisodicMemory(capacity=20)
        ...
        path = ss.save(rec, history)
        assert path.exists()
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
```

O1 file-persistence tests must assert:
- Node file exists at `.voss/sessions/<root_id>/<node_id>.json`
- `stat.S_IMODE(path.stat().st_mode) == 0o600`
- `json.loads(path.read_text())` parses without error

---

#### Async test pattern — `asyncio_mode = "auto"` is active (pyproject.toml line 68)

```toml
# pyproject.toml line 68
asyncio_mode = "auto"
```

Tests that call async functions do NOT need `@pytest.mark.asyncio`. They just use `async def test_...`. This is verified by `test_anthropic_stream.py` which uses `@pytest.mark.asyncio` (the older explicit style) — but `asyncio_mode = "auto"` makes the decorator optional. New tests in `test_session_tree.py` should use plain `async def` (no decorator) for concurrency tests:

```python
# Concurrency test pattern (no decorator needed with asyncio_mode=auto)
class TestConcurrency:
    async def test_concurrent_no_oversell(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=900)
        mgr = SessionTreeManager(root, reserve=100, cwd=tmp_path)
        tasks = [mgr.allocate_child(100) for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successes = [r for r in results if isinstance(r, SessionTreeNode)]
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(successes) == 8   # 900 - 100 reserve = 800; 8 × 100 = 800
        assert len(errors) == 2
```

---

#### Schema-lock test style — copy from `test_session_redaction.py` lines 91–117

```python
# test_session_redaction.py lines 91-117
class TestRunRecordRedaction:
    def test_run_record_top_level_keys(self):
        rec = RunRecord(id="t", started_at="t0", ended_at="t1")
        expected = {
            "id", "started_at", "ended_at", "goal", "plan", ...
        }
        assert set(asdict(rec).keys()) == expected
        assert len(dataclasses.fields(RunRecord)) == 21
```

Add a `TestSchemaIsolation` class to `test_session_tree.py` that:
1. Asserts `SessionTreeNode.to_dict()` does NOT include `_budget`
2. Asserts no `SessionTreeNode` field matches any `SessionRecord` or `RunRecord` field (no accidental schema merge)
3. Asserts `test_session_redaction.py`-style: the node file JSON has exactly the expected keys

---

## Shared Patterns

### File persistence (0o600 + json.dumps + mkdir)
**Source:** `voss/harness/session.py` lines 205–213
**Apply to:** `session_tree.py` `_write_node_file()` function

```python
# session.py lines 208-213
path = _sessions_dir(cwd) / f"{record.id}.json"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(asdict(record), indent=2))
path.chmod(0o600)
return path
```

Node variant: path is `cwd / ".voss" / "sessions" / node.root_id / f"{node.id}.json"`. Pop `_budget` from `dataclasses.asdict(node)` before passing to `json.dumps`.

---

### UTC ISO timestamp generation
**Source:** `voss/harness/session.py` line 168 and `voss/harness/recorder.py` line 53
**Apply to:** `session_tree.py` everywhere a timestamp is needed

```python
# session.py line 168 / recorder.py line 53
datetime.now(timezone.utc).isoformat(timespec="seconds")
```

---

### UUID node-id generation
**Source:** `voss/harness/recorder.py` line 52 and `voss/harness/session.py` line 167
**Apply to:** `session_tree.py` `SessionTreeNode.create_root()` and child allocation

```python
# recorder.py line 52
uuid.uuid4().hex[:12]
```

---

### `asyncio.Lock` concurrency primitive
**Source:** `voss/harness/agent.py` (referenced RESEARCH.md line 487; `asyncio.Semaphore` pattern)
**Apply to:** `session_tree.py` `SessionTreeManager.__init__`

```python
self._lock = asyncio.Lock()        # allocation guard only; NOT held during run_turn
```

---

### `from __future__ import annotations`
**Source:** All harness files (session.py line 42, recorder.py line 8, subagents.py line 1)
**Apply to:** Both new files

This is the project-wide Python annotation import — required for forward references in type hints (e.g., `"SessionTreeNode | None"`).

---

### `EXIT_REASONS` membership for `exit_reason="budget"`
**Source:** `voss/harness/session.py` line 74

```python
# session.py line 74
EXIT_REASONS: frozenset[str] = frozenset(
    {"done", "max-iter", "budget", "interrupt", "batch-invariant"}
)
```

`"budget"` is already in `EXIT_REASONS`. `RunRecorder.finalize(cwd, cost_usd, exit_reason="budget")` is valid without schema change. The D-03 boundary calls it exactly as `recorder.finalize(cwd, 0.0, exit_reason="budget")`.

---

### `conftest.py` `isolated_state` autouse fixture
**Source:** `tests/harness/conftest.py` lines 28–31

```python
# conftest.py lines 28-31
@pytest.fixture(autouse=True)
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    return tmp_path
```

This fixture is autouse for ALL `tests/harness/` tests. `test_session_tree.py` gets it automatically — no need to declare it. All file-system tests receive an isolated XDG state.

---

## No Analog Found

No files in this phase are completely without analog.

| File | Note |
|---|---|
| `voss/harness/session_tree.py` | Closest analog is `session.py` but the `SessionTreeManager` class with `asyncio.Lock` + child-allocation invariant is new behavior. RESEARCH.md Pattern 2 (lines 208–241) provides the complete reference implementation. |

---

## Key Constraints for Planner

1. **`test_session_redaction.py` must pass unmodified.** The new `SessionTreeNode` type must NEVER appear as a field on `SessionRecord`, `RunRecord`, or any type serialized by `session.save()`. Keep it at `.voss/sessions/<root_id>/` — a completely separate path.

2. **`test_subagent_recursion.py` must pass unmodified.** Adding `node` and `reserve` kwargs to `run_subagent` is safe. Adding `depth`, `max_depth`, `MAX_DEPTH`, `DEPTH_LIMIT`, or `RECURSION_LIMIT` is NOT safe.

3. **`_budget` must not reach `json.dumps`.** `BudgetScope` is not JSON-serializable. Pop it from `dataclasses.asdict()` output before writing, or use a custom `to_dict()` that excludes it.

4. **Do NOT hold the `asyncio.Lock` during `run_turn`.** Lock scope: check-and-append only. Release before any `await run_turn(...)` call.

5. **Write node file BEFORE `run_turn` (open state).** Write again AFTER finalization (closed state). Two writes, not one.

---

## Metadata

**Analog search scope:** `voss/harness/`, `voss_runtime/`, `tests/harness/`
**Files read:** `session.py`, `recorder.py`, `subagents.py`, `budget.py`, `test_session_redaction.py`, `test_subagent_recursion.py`, `test_recorder_iterations.py`, `test_session.py`, `test_recorder.py`, `test_anthropic_stream.py` (header only), `conftest.py` (header), `pyproject.toml` (asyncio config lines)
**Pattern extraction date:** 2026-05-18
