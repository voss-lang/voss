# Phase V4: Session Tree + Budget Fan-out — Pattern Map

**Mapped:** 2026-06-06
**Files analyzed:** 3 (session_tree.py, subagents.py, cli.py) + 1 test file
**Analogs found:** 5 / 5 — all exact role-match or role+data-flow-match

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `voss/harness/session_tree.py` | model + utility | CRUD + file-I/O | itself (additive delta) | exact |
| `voss/harness/subagents.py` | service | request-response | itself (additive delta) | exact |
| `voss/harness/cli.py` | controller (CLI) | request-response | `principles_group` + `inspect_group` patterns in same file | exact |
| `tests/harness/test_session_tree.py` | test | — | itself (additive delta) | exact |

---

## Pattern Assignments

### `voss/harness/session_tree.py` — additive schema extension (VTREE-08) + export function (VTREE-10)

**Analog:** the file itself; all patterns are already established within it.

#### 1. `SessionTreeNode` dataclass — existing field ordering (lines 47–62)

The fields without defaults come first, fields with defaults (`field(default_factory=...)`) come after. Private internal fields (`_budget`, `_finalized`) use `field(default=None, init=False, repr=False)` and sit last. V4 inserts `scope` and `role` immediately before `_budget`:

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
    # O3 OBRD-01 / R-01+R-03: per-card transition + retry history on the node.
    transitions: list = field(default_factory=list)
    retry_notes: list = field(default_factory=list)
    _budget: Optional[BudgetScope] = field(default=None, init=False, repr=False)
    _finalized: bool = field(default=False, init=False, repr=False)
```

**V4 insertion point:** add `scope: Optional[str] = None` and `role: Optional[str] = None` between `retry_notes` and `_budget`. Both must have `= None` defaults — no `field(default_factory=...)` needed.

#### 2. `_NODE_FIELDS` auto-rebuild pattern (line 86)

```python
_NODE_FIELDS = {f.name for f in dataclasses.fields(SessionTreeNode)}
```

This runs at module load. Once `scope` and `role` are added to the dataclass, `_NODE_FIELDS` automatically includes them — no manual update needed here. However, `to_dict()` will now include them (via `asdict`), which breaks `TestSchemaIsolation.test_node_keys_exact` — that test's `_NODE_JSON_KEYS` set must be updated (see test patterns below).

#### 3. `_hydrate_node` `setdefault` back-compat pattern (lines 89–94)

The established pattern for every additive field: one `setdefault` per new field, placed before `SessionTreeNode(**kept)`:

```python
def _hydrate_node(data: dict) -> SessionTreeNode:
    kept = {k: v for k, v in data.items() if k in _NODE_FIELDS}
    kept.setdefault("rejected_raises", [])
    kept.setdefault("transitions", [])
    kept.setdefault("retry_notes", [])
    return SessionTreeNode(**kept)
```

V4 appends two more lines following this exact pattern:
```python
    kept.setdefault("scope", None)    # V4 VTREE-08: pre-V4 files → null
    kept.setdefault("role", None)     # V4 VTREE-08: pre-V4 files → null
```

#### 4. `_write_node_file` persistence pattern (lines 97–102)

The disk format IS the export format. `export_tree` reads exactly what `_write_node_file` writes:

```python
def _write_node_file(node: SessionTreeNode, cwd: Path) -> Path:
    path = cwd / ".voss" / "sessions" / node.root_id / f"{node.id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(node.to_dict(), indent=2))
    path.chmod(0o600)
    return path
```

`export_tree` mirrors the `glob("*.json")` + `json.loads` + `path.read_text()` sequence already used in the test helper `_load_nodes_from_disk` (test file lines 51–57).

#### 5. `finalize_node` idempotence guard (lines 113–123)

Critical for VTREE-07: `_finalized` is the gate. The `finally` safety net in `run_subagent` relies on this being safe to call multiple times:

```python
def finalize_node(node: SessionTreeNode, *, exit_reason: str, final: str = "", cwd: Path) -> None:
    if node._finalized:
        return                    # ← idempotence gate; safe to call from finally
    if exit_reason not in EXIT_REASONS:
        raise ValueError(...)     # ← EXIT_REASONS validation; "error" not currently present
    node.terminal_state = {"exit_reason": exit_reason, "final": final}
    node.ended_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    node._finalized = True
    _write_node_file(node, cwd)
```

**EXIT_REASONS gap (A4 from RESEARCH):** `"error"` is not in `EXIT_REASONS` (confirmed: `session.py` has `{done, max-iter, budget, interrupt, batch-invariant, timeout, killed}`). Exception paths must use `"interrupt"` OR `"error"` must be added to `EXIT_REASONS` in `session.py`. Planner decides — if adding `"error"`, it is additive (no field change on any record).

#### 6. `allocate_child` pattern for `scope`/`role` kwargs (lines 165–192)

The existing `allocate_child` creates `SessionTreeNode` positionally. V4 extension adds `scope` and `role` as optional kwargs on the method and passes them through to the constructor:

```python
async def allocate_child(self, limit: int) -> SessionTreeNode:
    async with self._lock:
        allocated = sum(c.envelope["limit"] for c in self._children)
        available = (self._root.envelope["limit"] - self._reserve - allocated)
        if limit > available:
            raise BudgetAllocationError(...)
        child_id = uuid.uuid4().hex[:12]
        child = SessionTreeNode(
            id=child_id,
            root_id=self._root.id,
            parent_run_id=self._root.id,
            envelope={"limit": limit, "spent": 0},
            terminal_state=None,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ended_at=None,
            rejected_raises=[],
        )
        self._children.append(child)
        _write_node_file(child, self._cwd)
        child._budget = BudgetScope(token_limit=limit, name=child.id)
        return child
```

V4 adds `*, scope: str | None = None, role: str | None = None` to the signature and passes them in the `SessionTreeNode(...)` constructor call.

---

### `voss/harness/subagents.py` — guard insertion + exception wiring (VTREE-04, VTREE-07)

**Analog:** the file itself; existing `run_subagent` body is the mutation target.

#### 1. Existing `run_subagent` signature + early return (lines 211–227)

The guard insertion point is AFTER the `spec is None` early return and BEFORE `async with scope:`:

```python
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
    node: SessionTreeNode | None = None,
    reserve: int = 0,
) -> str:
    spec = registry.get(agent_id)
    if spec is None:
        return f"<error: unknown subagent {agent_id!r}>"
    spendable = (node.envelope["limit"] - reserve) if node else None
    child_tools = make_toolset(cwd, renderer=renderer)
    scope = (
        node._budget
        if node and node._budget
        else nullcontext()
    )
```

**V4 guard goes here** — between line 227 (early return) and line 228 (spendable assignment). Copy pattern:
```python
    # [VTREE-04] Pre-emptive spend guard: refuse to start a call when envelope exhausted.
    if node is not None and node.envelope["spent"] >= node.envelope["limit"]:
        if not node._finalized:
            finalize_node(node, exit_reason="budget", final="<halted: budget — envelope exhausted>", cwd=cwd)
        return "<halted: budget — envelope exhausted>"
```

#### 2. Existing `try/except BudgetExceededError` block (lines 235–285)

This is the only currently-caught exception path. V4 extends it with two new `except` branches and a `finally`:

```python
    try:
        async with scope:
            if node is not None:
                result = await run_turn(..., token_budget=spendable)
            else:
                result = await run_turn(...)
        if node and result.run and result.run.exit_reason == "budget":
            finalize_node(node, exit_reason="budget", final=result.final, cwd=cwd)
        elif node:
            finalize_node(node, exit_reason="done", final=result.final, cwd=cwd)
        return result.final
    except BudgetExceededError:          # ← already exists; keep unchanged
        if node:
            finalize_node(node, exit_reason="budget", final="<halted: budget>", cwd=cwd)
        return "<halted: budget>"
```

**V4 appends after the `except BudgetExceededError` block:**
```python
    except asyncio.TimeoutError:                        # [NEW V4 — VTREE-07]
        if node:
            finalize_node(node, exit_reason="timeout", final="<halted: timeout>", cwd=cwd)
        raise  # re-raise — caller defines timeout semantics

    except Exception as exc:                            # [NEW V4 — VTREE-07]
        if node:
            finalize_node(node, exit_reason="interrupt", final=f"<error: {exc}>", cwd=cwd)
        raise

    finally:                                            # [safety net — VTREE-07]
        if node and not node._finalized:
            finalize_node(node, exit_reason="interrupt", final="<uncaught>", cwd=cwd)
```

**Note:** `asyncio.TimeoutError` must be caught BEFORE `Exception` because `TimeoutError` is a subclass of `Exception` in Python 3.11+. `asyncio` must be imported — it is not currently imported in `subagents.py` (lines 1–19 show no `asyncio` import). The planner must add `import asyncio` to the imports.

#### 3. `attach_subagent_tool` closure — documented gap (lines 317–329)

The `subagent_run` tool closure calls `run_subagent` without `node=`. This means the guard is bypassed for tool-dispatched subagent calls. V4 documents this gap but does NOT fix it (V5/V7 integration work). No code change needed here in V4.

#### 4. Spend update wiring — missing pattern (post-`run_turn`)

Currently `mutate_envelope` is never called inside `run_subagent` — `spent` stays 0 unless the caller does it. V4 must add the spend update on the normal path, BEFORE the soft-exit check, AFTER `async with scope:` exits:

```python
        # [V4 VTREE-04] Update spent from actual token usage
        if node and result.run is not None:
            tokens_used = (
                (result.run.iteration_total_prompt_tokens or 0)
                + (result.run.iteration_total_completion_tokens or 0)
            )
            if tokens_used > 0:
                mutate_envelope(node, delta=-tokens_used, cwd=cwd)
```

`mutate_envelope` must be imported — it is not currently imported in `subagents.py` (line 18 only imports `finalize_node`). The planner must extend the import: `from .session_tree import finalize_node, mutate_envelope`.

---

### `voss/harness/cli.py` — new `session_group` (VTREE-09)

**Analog:** `principles_group` (lines 3740–3774) — closest match: same file, same pattern shape, most recently added group (added in V3 principles phase).

#### 1. `principles_group` — exact pattern to mirror (lines 3740–3774)

```python
@click.group("principles")
def principles_group() -> None:
    """Inspect the active engineering principles (VPRIN-07)."""


@principles_group.command("show")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False), help="Project root.")
@click.option("--json", "json_mode", is_flag=True, help="Emit machine-readable JSON.")
def principles_show_cmd(cwd_str: str, json_mode: bool) -> None:
    """Show the merged active principles with each one's source."""
    import json as json_lib

    from voss.harness.principles import VossPrinciplesConfigError, resolve_with_sources

    cwd = Path(cwd_str).resolve()
    try:
        items = resolve_with_sources(cwd)
    except VossPrinciplesConfigError as e:
        click.echo(f"<error: {e}>", err=True)
        raise click.exceptions.Exit(1) from e

    if json_mode:
        click.echo(json_lib.dumps(...))
        return

    # text rendering
    for key, text, source in items:
        click.echo(...)
```

Key conventions to mirror:
- Local import inside the command function body (`import json as json_lib`, domain import from `.module`)
- `click.echo(f"<error: {e}>", err=True)` then `raise click.exceptions.Exit(1)` for error path
- `--json` flag with `json_mode: bool` parameter name and `is_flag=True`
- `--cwd` option with `cwd_str` parameter name, `type=click.Path(file_okay=False)`
- `Path(cwd_str).resolve()` pattern for path resolution

#### 2. `inspect_group` — secondary analog (lines 2757–2788)

```python
@click.group("inspect")
def inspect_group() -> None:
    """Inspect persisted run records."""


@inspect_group.command("probable")
@click.argument("session_id_or_name")
@click.option("--decision", "decision_index", type=int, default=None)
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
def inspect_probable_cmd(session_id_or_name: str, decision_index: int | None, cwd_str: str) -> None:
    """Show recorded probable decision sequence."""
    try:
        text = _render_probable_inspect(Path(cwd_str).resolve(), session_id_or_name, decision_index)
    except (FileNotFoundError, ValueError, IndexError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(text)
```

Shows the `@click.argument` pattern (for `root_id`), and `raise click.ClickException(str(exc))` as an alternative error pattern that also writes to stderr and exits 1.

#### 3. `AGENT_COMMANDS` registration (lines 3777–3813)

```python
AGENT_COMMANDS = (
    do_cmd,
    serve_cmd,
    chat_cmd,
    edit_cmd,
    login_cmd,
    logout_cmd,
    doctor_cmd,
    sessions_cmd,
    jobs_cmd,
    watch_cmd,
    inspect_group,
    vdiff_cmd,
    resume_cmd,
    tools_cmd,
    plugins_cmd,
    plugin_group,
    skills_cmd,
    skill_group,
    agents_cmd,
    agent_group,
    memory_group,
    config_cmd,
    mcp_group,
    logs_group,
    eval_cmd,
    consensus_cmd,
    hooks_group,
    capabilities_group,
    principles_group,    # ← append session_group after this
)


def register(group: click.Group) -> None:
    """Attach all agent commands to a click Group."""
    for cmd in AGENT_COMMANDS:
        group.add_command(cmd)
```

`session_group` goes at the end of the tuple, after `principles_group`, following the same append pattern used for every prior group addition.

---

### `tests/harness/test_session_tree.py` — new test classes (VTREE-04/07/08/09/10)

**Analog:** the file itself; new classes must mirror existing class and method conventions exactly.

#### 1. File-level imports + `_NODE_JSON_KEYS` sentinel (lines 1–40)

```python
from __future__ import annotations

import asyncio
import dataclasses
import json
import stat
from pathlib import Path

import pytest

from voss.harness.session import EXIT_REASONS, RunRecord, SessionRecord
from voss.harness.session_tree import (
    BudgetAllocationError,
    BudgetCapRaiseError,
    SessionTreeManager,
    SessionTreeNode,
    finalize_node,
    mutate_envelope,
)

_NODE_JSON_KEYS = frozenset(
    {
        "id",
        "root_id",
        "parent_run_id",
        "envelope",
        "terminal_state",
        "created_at",
        "ended_at",
        "rejected_raises",
        # O3 OBRD-01: per-card transition + retry history (additive).
        "transitions",
        "retry_notes",
    }
)
```

**V4 must add `"scope"` and `"role"` to `_NODE_JSON_KEYS`** or `TestSchemaIsolation.test_node_keys_exact` breaks. Update is intentional (deliberate schema extension signal).

New imports needed for V4 test classes:
- `from unittest.mock import AsyncMock, patch` (for `TestSpendGuard` mock of `run_turn`)
- `from voss.harness.session_tree import SessionTreeNotFoundError, export_tree` (for `TestExport`)
- `from click.testing import CliRunner` (for `TestCLI`)
- `from voss.harness.cli import session_group` (for `TestCLI`)

#### 2. Helper functions pattern (lines 43–57)

```python
def _sessions_tree_dir(cwd: Path, root_id: str) -> Path:
    return cwd / ".voss" / "sessions" / root_id


def _node_path(cwd: Path, root_id: str, node_id: str) -> Path:
    return _sessions_tree_dir(cwd, root_id) / f"{node_id}.json"


def _load_nodes_from_disk(cwd: Path, root_id: str) -> dict[str, dict]:
    tree_dir = _sessions_tree_dir(cwd, root_id)
    nodes: dict[str, dict] = {}
    for path in tree_dir.glob("*.json"):
        data = json.loads(path.read_text())
        nodes[data["id"]] = data
    return nodes
```

`_load_nodes_from_disk` is the `glob("*.json")` aggregation pattern — `export_tree` mirrors this exactly. New test helpers should follow the same module-level function style (no class, no fixture decoration).

#### 3. Async class-based test pattern (lines 60–96, `TestTreePersistence`)

Every async test class: no `@pytest.mark.asyncio` decorator (the `asyncio_mode = "auto"` in `pyproject.toml` handles it). Method signature is `async def test_...(self, tmp_path: Path) -> None:`. Uses `await` directly. No `setUp`/`tearDown` — `tmp_path` fixture provides isolation.

```python
class TestTreePersistence:
    async def test_root_and_children_persist_and_reconstruct(
        self, tmp_path: Path
    ) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=1000)
        mgr = SessionTreeManager(root, reserve=100, cwd=tmp_path)
        n = 3
        children = [await mgr.allocate_child(100) for _ in range(n)]
        # ... assertions
```

#### 4. Sync class-based test pattern (lines 123–149, `TestCapRaiseGuard`)

Sync tests use `def test_...(self, tmp_path: Path) -> None:` — no `async`. Same class structure, same `tmp_path` fixture.

```python
class TestCapRaiseGuard:
    def test_raise_errors(self, tmp_path: Path) -> None:
        root = SessionTreeNode.create_root(cwd=tmp_path, limit=500)
        with pytest.raises(BudgetCapRaiseError):
            mutate_envelope(root, delta=50, cwd=tmp_path)
```

#### 5. `pytest.raises` error path pattern (lines 126–127, 222–228)

```python
with pytest.raises(BudgetCapRaiseError):
    mutate_envelope(root, delta=50, cwd=tmp_path)
```

```python
assert "quit" not in EXIT_REASONS
with pytest.raises(ValueError):
    finalize_node(root, exit_reason="quit", final="", cwd=tmp_path)
```

#### 6. `TestSchemaIsolation.test_node_keys_exact` — the test V4 must update (lines 172–177)

```python
def test_node_keys_exact(self, tmp_path: Path) -> None:
    root = SessionTreeNode.create_root(cwd=tmp_path, limit=100)
    assert set(root.to_dict().keys()) == _NODE_JSON_KEYS
    path = _node_path(tmp_path, root.id, root.id)
    on_disk = json.loads(path.read_text())
    assert set(on_disk.keys()) == _NODE_JSON_KEYS
```

This test passes today. V4's `scope`/`role` addition makes `to_dict()` return two more keys, breaking the assertion. Fix: add `"scope"` and `"role"` to the `_NODE_JSON_KEYS` frozenset at the top of the file. The test body itself does not change.

---

## Shared Patterns

### Exception / error path in Click commands
**Source:** `voss/harness/cli.py` lines 2774–2775 and 3757–3759
**Apply to:** `session_tree_cmd` in the new `session_group`

Two equivalent patterns exist — use the `principles_group` convention (most recent):
```python
click.echo(f"<error: {e}>", err=True)
raise click.exceptions.Exit(1) from e
```

The `inspect_group` alternative: `raise click.ClickException(str(exc)) from exc` also writes to stderr + exits 1 (click handles it). Either is acceptable; `principles_group` pattern is preferred for V4 since it's the most recent addition.

### `asyncio.Lock` allocation guard
**Source:** `voss/harness/session_tree.py` lines 154 + 165–192
**Apply to:** `allocate_child` extension — the lock scope does NOT expand. `scope`/`role` kwargs are set inside the `async with self._lock:` block because the `SessionTreeNode(...)` constructor call and `_write_node_file` are already inside it.

### `tmp_path` fixture for file I/O tests
**Source:** `tests/harness/test_session_tree.py` — used by every test class
**Apply to:** All new test classes (`TestSpendGuard`, `TestAllReasonsFinalize`, `TestSchemaExtension`, `TestExport`, `TestCLI`). `tmp_path` is a built-in pytest fixture that provides a `Path` to a unique temp directory. No import needed.

---

## No Analog Found

All V4 files have existing analogs. However, two new constructs have no direct codebase precedent:

| Construct | Role | Data Flow | Reason |
|-----------|------|-----------|--------|
| `SessionTreeNotFoundError` exception class | model | — | No domain-specific `NotFound` exception exists in `session_tree.py` today; closest is `BudgetAllocationError`/`BudgetCapRaiseError` in same file — copy their minimal class body (`class X(Exception): ...`) |
| `export_tree(root_id, cwd)` pure function | utility | file-I/O | No existing aggregation function in `session_tree.py`; closest analog is `_load_nodes_from_disk` in the test file (lines 51–57) — copy the `glob("*.json")` + `json.loads(path.read_text())` loop, add the not-found guard |

---

## Metadata

**Analog search scope:** `voss/harness/`, `tests/harness/`, `voss/harness/cli.py`
**Files read:** `session_tree.py` (192 lines), `subagents.py` (370 lines), `cli.py` (lines 2754–2803, 3738–3814), `test_session_tree.py` (249 lines)
**Pattern extraction date:** 2026-06-06
