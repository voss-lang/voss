# Phase BOS4: Decision Ledger Runtime - Pattern Map

**Mapped:** 2026-06-20
**Files analyzed:** 4 (2 new, 2 modified)
**Analogs found:** 4 / 4

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `voss/harness/bos_decisions.py` | service / ledger writer | append-only I/O + record builder | `voss/harness/bos_ledger.py` (writer) + `voss/harness/bos_events.py` (builders) | exact (writer) + role-match (builders) |
| `voss/harness/permissions.py` | middleware / gate | request-response | `voss/harness/permissions.py` itself — hook point is `_prompt` return path (lines 442-456) | self-modification |
| `voss/harness/swarm_runtime.py` | service / orchestrator | event-driven | `voss/harness/swarm_runtime.py` itself — hook point is `store.mark_assigned` call (line 165) | self-modification |
| `tests/harness/test_bos_decision_ledger.py` | test | append-only I/O + record build | `tests/harness/test_bos_event_ledger.py` | exact |

---

## Pattern Assignments

### `voss/harness/bos_decisions.py` (new — ledger writer + record builders)

**Primary analog:** `voss/harness/bos_ledger.py`
**Secondary analog:** `voss/harness/bos_events.py` (builder/envelope style)

---

**Imports pattern** (`voss/harness/bos_ledger.py` lines 1-13):
```python
"""Local append-only BOS decision ledger.

Inline emission: decision records are written AT gate/operator decision time
(D-R01). This is a deliberate break from BOS3's pure projection layer
(bos_events.py); decisions carry the frozen state they were made against.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import portalocker

_LOCK_TIMEOUT_S = 10.0
```

**Ledger path helper** (`voss/harness/bos_ledger.py` lines 18-22):
```python
def ledger_path(cwd: Path) -> Path:
    """Return the canonical local BOS event ledger path for a project cwd."""
    return Path(cwd).resolve() / ".voss" / "bos" / "events.jsonl"
```
Copy this verbatim; change the function name to `decisions_ledger_path` and the last segment from `events.jsonl` to `decisions.jsonl`.

**Append-many core: portalocker lock + dedup-by-id + 0o600** (`voss/harness/bos_ledger.py` lines 40-64):
```python
def append_many(self, events: list[dict[str, Any]]) -> int:
    """Append events in order, skipping already-seen `event_id` values."""

    if not events:
        return 0

    self.path.parent.mkdir(parents=True, exist_ok=True)
    with portalocker.Lock(
        str(self.path),
        mode="a+",
        flags=portalocker.LOCK_EX | portalocker.LOCK_NB,
        timeout=_LOCK_TIMEOUT_S,
    ) as f:
        f.seek(0)
        seen = _read_event_ids(f)
        appended = 0
        for event in events:
            event_id = _event_id(event)
            if event_id in seen:
                continue
            f.write(json.dumps(event, sort_keys=True) + "\n")
            seen.add(event_id)
            appended += 1
    self.path.chmod(0o600)
    return appended
```
Copy verbatim. Replace `_event_id` / `_read_event_ids` with `_decision_id` / `_read_decision_ids` that read `decision_id` instead of `event_id`.

**Torn-line-tolerant replay reader** (`voss/harness/bos_ledger.py` lines 66-98):
```python
def read_events(
    self,
    *,
    trace_id: str | None = None,
    event_type: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """Replay events in append order, optionally filtering by top-level fields.

    A torn trailing line is ignored so an interrupted writer does not make
    the whole ledger unreadable.
    """
    if not self.path.exists():
        return []
    out: list[dict[str, Any]] = []
    with self.path.open("r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                break        # <-- torn-line tolerance: stop at first bad line
            ...
            out.append(event)
    return out
```
Copy verbatim for `read_decisions`; replace filter kwargs with `decision_type: str | None = None` as the only useful filter for decisions.

**Dedup key helper** (`voss/harness/bos_ledger.py` lines 123-143):
```python
def _event_id(event: dict[str, Any]) -> str:
    event_id = event.get("event_id")
    if not event_id:
        raise ValueError("BOS ledger event missing event_id")
    return str(event_id)


def _read_event_ids(f: Any) -> set[str]:
    seen: set[str] = set()
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            break
        event_id = event.get("event_id")
        if event_id:
            seen.add(str(event_id))
    return seen
```
Copy verbatim; rename to `_decision_id` / `_read_decision_ids`; change the `.get` key from `"event_id"` to `"decision_id"`; change the `ValueError` message to `"BOS decision record missing decision_id"`.

**`as_of` tail-read helper** (new — no existing analog; derive from `read_events` open pattern):

The `as_of` field (D-R05) needs the last appended `event_id` from `.voss/bos/events.jsonl`. Implement as a cheap tail scan (do NOT call `BosEventLedger.read_events` — that would load the whole ledger):
```python
def _read_last_event_id(events_path: Path) -> str | None:
    """Return the event_id of the last complete line in the BOS3 ledger.

    Reads the file line-by-line to handle large ledgers without loading all
    records into memory. A torn trailing line is skipped (same tolerance as
    bos_ledger.read_events). Returns None if the file is absent or empty.
    """
    if not events_path.exists():
        return None
    last: str | None = None
    with events_path.open("r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                break
            eid = rec.get("event_id")
            if eid:
                last = str(eid)
    return last
```
This is the pattern for `as_of` assembly at emission time (D-R05): `event_seq` is the position of the last event (count lines before breaking), `snapshot_id` may be None.

**Envelope / builder shape** (`voss/harness/bos_events.py` lines 60-89, the `_envelope` helper):
```python
def _envelope(
    *,
    event_id: str,
    event_type: str,
    ...
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": BOS_SCHEMA_VERSION,
        "event_id": event_id,
        ...
        "payload": payload,
    }
```
BOS4's builder functions (`build_task_to_agent_record`, `build_permission_verdict_record`) follow the same keyword-only builder pattern returning a flat `dict[str, Any]` — one builder per `decision_type`. The outer dict keys are the envelope fields from `contracts/decision-ledger.schema.json` (`decision_id`, `decision_type`, `created_at`, `as_of`, `feature_snapshot`, `entity_ref`, `autonomy_band`, `recommended_action`, `human_verdict`, `actual_action`, `rationale`, `payload`).

**`_now_iso` util** (`voss/harness/bos_events.py` lines 27-28):
```python
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
```
Copy verbatim — use for `created_at` and `verdict_at`.

**Module-level convenience wrappers** (`voss/harness/bos_ledger.py` lines 101-120):
```python
def append_event(cwd: Path, event: dict[str, Any]) -> bool:
    return BosEventLedger(cwd).append_event(event)

def append_many(cwd: Path, events: list[dict[str, Any]]) -> int:
    return BosEventLedger(cwd).append_many(events)

def read_events(cwd: Path, ...) -> list[dict[str, Any]]:
    return BosEventLedger(cwd).read_events(...)
```
Mirror as `append_decision` / `append_decisions` / `read_decisions` module-level fns delegating to `BosDecisionLedger`.

---

### `voss/harness/permissions.py` (modify — emit verdict decision record from `_prompt`)

**Analog:** `voss/harness/permissions.py` itself — the hook point is the return path of `_prompt` (lines 442-456).

**Hook point — `_prompt` verdict return** (`permissions.py` lines 442-456):
```python
def _prompt(self, tool_name: str, args: dict) -> tuple[bool, str]:
    if self.prompt_fn is None and not sys.stdin.isatty():
        return False, "non-interactive denial"
    prompt = self.prompt_fn or _interactive_prompt
    choice = prompt(tool_name, args)
    if choice == "a":
        return True, "allowed once"       # <-- D-R04: human_verdict = approve
    if choice == "A":
        if self.store is not None:
            self.store.remember(self.signature(tool_name, args))
        return True, "allowed always"     # <-- D-R04: human_verdict = approve
    return False, "denied"               # <-- D-R04: human_verdict = dismiss
```
Emit a decision record immediately before each `return` in `_prompt` that follows a human answer (after `choice = prompt(...)` is resolved). Do NOT emit from `_check_impl` paths that short-circuit before reaching `_prompt` — those are auto-allows, not human decisions (D-R04).

**What to pass to the builder at emit time** (from `_prompt` context):
- `tool_name`, `args` — available as parameters
- `is_mutating` — must be threaded through from `_check_impl` call site (lines 260-350) if needed for `feature_snapshot`; alternatively accept an optional `feature_extras: dict | None = None` kwarg on `_prompt`.
- `self.mode` — available for `feature_snapshot.mode`
- `self.signature(tool_name, args)` — for `feature_snapshot.signature`
- `cwd` — needed for the ledger path; `PermissionGate` currently has no `cwd` field; either add it or accept it as a kwarg to the emit call / via a `cwd: Path | None = None` field on the gate.

**Gateway condition** (D-R04): emit ONLY when control reaches `choice = prompt(...)` — the human was actually shown a prompt. If `prompt_fn is None and not sys.stdin.isatty()`, the gate short-circuits and returns `False, "non-interactive denial"` without a human; no emit there.

---

### `voss/harness/swarm_runtime.py` (modify — emit `task_to_agent` at assignment seam)

**Analog:** `voss/harness/swarm_runtime.py` itself — the hook point is line 165, immediately after `store.mark_assigned`.

**Hook point — role↔task pairing seam** (`swarm_runtime.py` lines 117-167, key lines 165-167):
```python
store.mark_assigned(swarm_id, task.id)   # line 165 — THIS is the assignment moment

argv = resolve_agent_argv(role, cwd=mw.path, task_text=task.goal)
```
Emit a `task_to_agent` decision record immediately after `store.mark_assigned` (line 165) and before `resolve_agent_argv`. At this moment all of: `swarm_id`, `role.name`, `role.agent`, `role.model`, `task.id`, `task.goal`, `swarm.roster`, `repo_root` are in scope.

**What to pass to the builder** (from `run_cli_member` parameters, lines 117-127):
```python
async def run_cli_member(
    store: SwarmStore,
    repo_root: Path,
    swarm_id: str,
    role: Role,       # role.name, role.agent, role.model
    task: Task,       # task.id, task.goal
    *,
    spawn_fn: SpawnFn,
    on_event: EventHook = None,
    context: str = "",
) -> MemberResult:
```
- `entity_ref`: `{task_id: task.id, swarm_id: swarm_id}`
- `feature_snapshot` (D-R06 `task_to_agent`): `{goal: task.goal, roster: [r.name for r in swarm.roster], available_models: [r.model for r in swarm.roster], cwd: str(repo_root)}`
- `payload` (`TaskToAgentPayload`): `{decision_type: "task_to_agent", task_id: task.id, chosen_agent_id: role.agent, candidate_agents: [role.agent]}`
- `cwd` for the ledger path: use `repo_root`

**Roster access**: `store.get(swarm_id)` returns the `Swarm` object (including `.roster`). It is already called implicitly by `run_cli_swarm` (line 288) but NOT in `run_cli_member`. A cheap `store.get(swarm_id)` call at the emit point is the cleanest way to get roster names for `feature_snapshot`.

---

### `tests/harness/test_bos_decision_ledger.py` (new — regression-gate tests)

**Analog:** `tests/harness/test_bos_event_ledger.py`

**File-header + imports pattern** (`test_bos_event_ledger.py` lines 1-23):
```python
"""BOS3: local append-only BOS event ledger."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from voss.harness.bos_ledger import BosEventLedger, append_event, read_events
...

REPO = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO / ".planning" / "schemas" / "bos-events.schema.json"
INGEST_TIME = "2026-06-20T12:00:00+00:00"
```
Mirror for decisions: change `SCHEMA_PATH` to point to `contracts/decision-ledger.schema.json` (note: this is in `contracts/`, not `.planning/schemas/`). Import from `voss.harness.bos_decisions`.

**Schema validator fixture** (`test_bos_event_ledger.py` lines 27-31):
```python
@pytest.fixture(scope="module")
def validator() -> jsonschema.Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)
```
Copy verbatim — same pattern for decisions.

**Append + replay + schema-validate test** (`test_bos_event_ledger.py` lines 62-91):
```python
def test_projected_events_append_and_replay_with_filters(
    validator: jsonschema.Draft202012Validator,
    tmp_path: Path,
) -> None:
    ledger = BosEventLedger(tmp_path)
    events = _projected_session_events(tmp_path)

    assert ledger.append_many(events) == len(events)

    assert ledger.path == tmp_path / ".voss" / "bos" / "events.jsonl"
    replayed = ledger.read_events()
    assert [event["event_id"] for event in replayed] == [
        event["event_id"] for event in events
    ]
    for event in replayed:
        validator.validate(event)
    ...
```
Mirror: build 2 decision records (one `task_to_agent`, one permission verdict), append both, assert replay order, assert each passes `validator.validate(record)` against `contracts/decision-ledger.schema.json`.

**Dedup noop test** (`test_bos_event_ledger.py` lines 94-103):
```python
def test_duplicate_event_id_is_noop_and_preserves_file_bytes(tmp_path: Path) -> None:
    event = _projected_session_events(tmp_path)[0]

    assert append_event(tmp_path, event) is True
    before = (tmp_path / ".voss" / "bos" / "events.jsonl").read_bytes()

    assert append_event(tmp_path, dict(event)) is False
    after = (tmp_path / ".voss" / "bos" / "events.jsonl").read_bytes()

    assert after == before
```
Copy verbatim; swap key from `event_id` to `decision_id`; path segment to `decisions.jsonl`.

**Torn-line tolerance test** (`test_bos_event_ledger.py` lines 106-112):
```python
def test_read_events_tolerates_torn_trailing_line(tmp_path: Path) -> None:
    event = _projected_session_events(tmp_path)[0]
    ledger_path = tmp_path / ".voss" / "bos" / "events.jsonl"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_text(json.dumps(event, sort_keys=True) + "\n{\"event_id\":")

    assert read_events(tmp_path) == [event]
```
Copy verbatim; torn suffix uses `"decision_id":` to match the key being parsed.

---

## Shared Patterns

### Portalocker exclusive lock with non-blocking flag + 10s timeout
**Source:** `voss/harness/bos_ledger.py` lines 47-52
**Apply to:** `BosDecisionLedger.append_many` in `bos_decisions.py`
```python
with portalocker.Lock(
    str(self.path),
    mode="a+",
    flags=portalocker.LOCK_EX | portalocker.LOCK_NB,
    timeout=_LOCK_TIMEOUT_S,
) as f:
```

### 0o600 permissions after write
**Source:** `voss/harness/bos_ledger.py` line 63
**Apply to:** `BosDecisionLedger.append_many` — call `self.path.chmod(0o600)` immediately after the `portalocker.Lock` context manager exits.
```python
self.path.chmod(0o600)
```

### Torn-line break-on-JSONDecodeError
**Source:** `voss/harness/bos_ledger.py` lines 88-90 and `_read_event_ids` lines 137-139
**Apply to:** `read_decisions` AND `_read_decision_ids` in `bos_decisions.py`
```python
try:
    event = json.loads(line)
except json.JSONDecodeError:
    break   # <-- stop at first unparseable line; do NOT skip and continue
```

### `sort_keys=True` on write
**Source:** `voss/harness/bos_ledger.py` line 60
**Apply to:** every `f.write(json.dumps(...))` in `BosDecisionLedger`
```python
f.write(json.dumps(decision, sort_keys=True) + "\n")
```

### `_now_iso()` for timestamps
**Source:** `voss/harness/bos_events.py` lines 27-28
**Apply to:** `created_at` and `human_verdict.verdict_at` fields in all builders
```python
from datetime import datetime, timezone

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
```

### `path.parent.mkdir(parents=True, exist_ok=True)` before first write
**Source:** `voss/harness/bos_ledger.py` line 46
**Apply to:** `BosDecisionLedger.append_many` — ensures `.voss/bos/` exists before the ledger is created.

### jsonschema validator fixture (module scope)
**Source:** `tests/harness/test_bos_event_ledger.py` lines 27-31
**Apply to:** `tests/harness/test_bos_decision_ledger.py` — use `scope="module"`, point `SCHEMA_PATH` to `contracts/decision-ledger.schema.json`.

---

## No Analog Found

None — all four files have close analogs.

---

## Key Notes for Planner

### `as_of` tail-read (D-R05)
There is NO existing helper that reads the tail of `events.jsonl` cheaply. The `BosEventLedger.read_events` method loads all events into memory. `bos_decisions.py` must implement its own `_read_last_event_id(events_path)` (see pattern above) that scans lines without accumulating them, returning the final valid `event_id` as `as_of.snapshot_id` (and the line count as `as_of.event_seq`). This function is called inside `BosDecisionLedger.append_many` (or a `build_*_record` helper) under the portalocker lock to ensure the pointer is coherent with any concurrent event append.

### Permission gate hook placement (D-R04)
The ONLY human-facing surface in `PermissionGate` is `_prompt` (lines 442-456). The emit call goes after `choice = prompt(tool_name, args)` resolves and before the `return`. The three auto-allow paths (`needs = False` at line 345, `remembered` at line 348, `mode_allows` denial at line 316) must NOT emit — they are not human decisions.

### Swarm assignment hook placement (D-R02)
The assignment seam in `swarm_runtime.py` is line 165 (`store.mark_assigned(swarm_id, task.id)`). Emit immediately after this line. Both `role` (with `.name`, `.agent`, `.model`) and `task` (with `.id`, `.goal`) are in scope. To populate `feature_snapshot.roster`, call `store.get(swarm_id).roster` — a cheap in-memory lookup via `SwarmStore._swarms[swarm_id]` (see `swarm_store.py` line 288).

### Schema required fields
Every emitted record must carry ALL of: `decision_id`, `decision_type`, `created_at`, `as_of`, `feature_snapshot`, `entity_ref`, `autonomy_band`, `recommended_action`, `human_verdict`, `actual_action`, `rationale`, `payload` (see `contracts/decision-ledger.schema.json` lines 174-187). Pre-BOS9: `recommended_action` = `{}` (empty object satisfies `"type": "object"`), `autonomy_band` = `""` or the current runtime band string.

---

## Metadata

**Analog search scope:** `voss/harness/`, `tests/harness/`, `contracts/`
**Files read:** 8 (bos_ledger.py, bos_events.py, permissions.py, swarm_runtime.py, swarm_store.py, test_bos_event_ledger.py, test_bos_event_projection.py, decision-ledger.schema.json)
**Pattern extraction date:** 2026-06-20
