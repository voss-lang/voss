# Phase T2: Parallel Tools + Multi-Edit Primitive — Pattern Map

**Mapped:** 2026-05-15
**Files analyzed:** 13 (new/modified)
**Analogs found:** 13 / 13 (every new file has an in-tree analog; the codebase is the canonical source — no `RESEARCH.md` fallbacks needed)

T2 is a composition phase, not a build-from-scratch one. Every new tool, every new schema field, every new event has an exact in-tree analog. The planner's job is to copy these patterns verbatim and parameterize for the new shapes.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `voss/harness/agent.py` (rewrite `_run_step_loop`) | controller (scheduler) | event-driven / batch | self (`agent.py:507–598` current serial body) | exact-role refactor |
| `voss/harness/agent.py` (`BatchInvariantError` class) | exception | error surfacing | `voss/harness/sandbox.py:25` `SandboxError(RuntimeError)` | exact |
| `voss/harness/tools.py` (`fs_read_many`) | tool function (read primitive) | bundled request-response | `voss/harness/tools.py:51–61` `fs_read` + `:96–97` truncation marker | exact |
| `voss/harness/tools.py` (`fs_edit_many`) | tool function (mutating primitive) | atomic write + modal | `voss/harness/tools.py:107–128` `fs_edit` | exact (multi-edit variant) |
| `voss/harness/tools.py` (`make_toolset` registration) | registry | classification at registration | `voss/harness/tools.py:196–207` existing entries | exact |
| `voss/harness/session.py` (`BatchRecord` dataclass) | model (schema) | additive schema | T1-01 `IterationRecord` (planned at `session.py:70+`); shape mirrors `RunRecord` (`session.py:70–87`) | exact |
| `voss/harness/session.py` (`IterationRecord.batches` field) | model (schema field) | additive field | T1-01's pre-existing `RunRecord.iterations: list[IterationRecord]` additive pattern | exact |
| `voss/harness/recorder.py` (`begin_batch` / `end_batch`) | service (capture) | event-stream | T1-01 `RunRecorder.begin_iteration` / `end_iteration` (planned); shape mirrors `RunRecorder.observe` (`recorder.py:53–78`) | exact |
| `voss/harness/config.py` (`load_agent_config` / `get_max_parallel_reads`) | utility (config loader) | file → singleton | T1-04 `load_agent_config` / `get_max_iterations` (planned); shape mirrors `load_harness_config` (`config.py:30–39`) | exact |
| `tests/harness/test_step_loop_partition.py` | test (unit, async) | request-response | `tests/harness/test_recorder.py` (sync) + asyncio test idioms in other harness tests | role-match |
| `tests/harness/test_fs_edit_many.py` | test (unit, async + modal mock) | atomic write | `tests/harness/test_recorder.py` + permissions/diff test idioms | role-match |
| `tests/harness/test_fs_read_many.py` | test (unit, async) | bundled read | `tests/harness/test_recorder.py` shape | role-match |
| `tests/harness/test_telemetry_batches.py` | test (event spy) | event capture | T1's planned `test_session_iterations.py` + `redact_tool_args` spy pattern | role-match |
| `tests/harness/test_agent_config.py` (extend) | test (config round-trip) | file ↔ loader | `tests/harness/test_harness_config.py` (existing, exact shape) | exact |
| `tests/perf/test_parallel_read_speedup.py` (NEW DIR) | test (perf benchmark) | stub-timed | none in-tree; pattern locked in RESEARCH.md `Code Example 5` | no analog (greenfield) |

## Pattern Assignments

### `voss/harness/agent.py` — rewrite `_run_step_loop` (controller, event-driven batch)

**Analog:** `voss/harness/agent.py:507–598` (current serial body itself)

**Imports pattern** — preserve everything already at the top of `agent.py:1–34`. Add:
```python
# voss/harness/agent.py — top of file
import asyncio   # already imported at line 10
import time      # already imported at line 11
# new:
from voss_runtime import get_config
```
(`get_config` is already imported at `agent.py:18–23` — no new import.)

**Per-step dispatch body** to factor out of the existing loop (`agent.py:517–597`):
```python
# Source: voss/harness/agent.py:517–597 (current serial body) — refactor into
# _invoke_step_with_gate(step, tools, gate, renderer, recorder) -> str.
# Returns the result string instead of appending to a list; raises only on
# unrecoverable errors (which gather will capture via return_exceptions=True).

async def _invoke_step_with_gate(step, tools, gate, renderer, recorder) -> str:
    entry = tools.get(step.name)
    if entry is None:
        text = f"<error: unknown tool {step.name!r}>"
        renderer.show_tool_call(step.name, step.args, "<unknown tool>", "error")
        telemetry.emit("tool.result", "warn", data={
            "tool": step.name, "ok": False, "error": "unknown_tool",
            "args": telemetry.redact_tool_args(dict(step.args)),
        })
        if recorder is not None:
            recorder.observe(step.name, step.args, "<unknown tool>", ok=False)
        return text
    allowed, why = gate.check(step.name, step.args, is_mutating=entry.is_mutating)
    if not allowed:
        text = f"<denied: {why}>"
        renderer.show_tool_call(step.name, step.args, text, "error")
        telemetry.emit("tool.result", "info", data={
            "tool": step.name, "ok": False, "error": "denied", "why": why,
            "args": telemetry.redact_tool_args(dict(step.args)),
        })
        if recorder is not None:
            recorder.observe(step.name, step.args, text, ok=False)
        return text
    telemetry.emit("tool.call", "info", data={
        "tool": step.name,
        "args": telemetry.redact_tool_args(dict(step.args)),
    })
    renderer.show_tool_call(step.name, step.args, "running…", "pending")
    t0 = time.monotonic()
    try:
        res = await entry.invoke(**step.args)
        text = str(res)
    except Exception as e:  # noqa: BLE001 — preserve existing swallow pattern
        text = f"<error: {e}>"
        renderer.show_tool_call(step.name, step.args, text, "error")
        telemetry.emit("tool.result", "warn", data={
            "tool": step.name, "ok": False,
            "latency_ms": int((time.monotonic() - t0) * 1000),
            "error": str(e)[:300],
        })
        if recorder is not None:
            recorder.observe(step.name, step.args, text, ok=False)
        return text
    renderer.show_tool_call(step.name, step.args, _summarize(text), "ok")
    telemetry.emit("tool.result", "info", data={
        "tool": step.name, "ok": True,
        "latency_ms": int((time.monotonic() - t0) * 1000),
        "summary": _summarize(text, 120),
    })
    if recorder is not None:
        recorder.observe(step.name, step.args, text, ok=True)
    return text
```
The above is a near line-for-line copy of `agent.py:517–597`, with two surgical changes: (1) returns `text` instead of mutating `results`, and (2) drops the outer `for step in plan_steps:` and `continue` keywords.

**Partition scheduler** (the new `_run_step_loop` body):
```python
# Source: locked algorithm in T2-CONTEXT.md D-04 + T2-RESEARCH.md Pattern 1.
# Preserves the existing return contract: list[str] in author order, len(plan.steps).

async def _run_step_loop(
    plan_steps,
    tools: dict[str, ToolEntry],
    permissions: PermissionGate | None,
    renderer: Renderer,
    *,
    recorder: RunRecorder | None = None,
) -> list[str]:
    gate = permissions or PermissionGate(auto_yes=True)
    results: list[str | None] = [None] * len(plan_steps)
    cap = get_config().max_parallel_reads  # T2 adds this field; T1-04 pattern
    batch_index = 0
    i = 0
    while i < len(plan_steps):
        # Collect a run of consecutive read-only steps.
        j = i
        while j < len(plan_steps):
            entry = tools.get(plan_steps[j].name)
            if entry is None or entry.is_mutating:
                break
            j += 1
        if j > i:
            multi_step = (j - i) > 1
            await _dispatch_read_batch(
                steps=plan_steps[i:j],
                step_indices=list(range(i, j)),
                tools=tools, gate=gate, renderer=renderer, recorder=recorder,
                results=results, cap=cap,
                batch_index=batch_index if multi_step else None,
            )
            if multi_step:
                batch_index += 1
            i = j
        else:
            # Mutating singleton at position i.
            await _dispatch_singleton(
                step=plan_steps[i], step_index=i,
                tools=tools, gate=gate, renderer=renderer, recorder=recorder,
                results=results,
            )
            i += 1
    return [r if r is not None else "<error: missing result>" for r in results]
```

**Bounded-gather pattern** (`_dispatch_read_batch`):
```python
# Source: T2-RESEARCH.md Pattern 2; canonical asyncio docs.
# Mirrors voss_runtime/agent.py:109 `await asyncio.gather(*pending, return_exceptions=True)`
# in-tree precedent.

async def _dispatch_read_batch(*, steps, step_indices, tools, gate, renderer,
                               recorder, results, cap, batch_index):
    # Partition invariant: every step in a multi-step batch is non-mutating.
    if len(steps) > 1:
        for s in steps:
            entry = tools.get(s.name)
            if entry is None or entry.is_mutating:
                raise BatchInvariantError(
                    f"step {s.name!r} in multi-step batch is mutating or unregistered"
                )

    sem = asyncio.Semaphore(cap)  # per-batch; GC'd on return (D-17)
    t0 = time.perf_counter()

    if batch_index is not None:
        telemetry.emit("batch.start", "info", data={
            "batch_index": batch_index,
            "step_indices": step_indices,
            "parallel_count": len(steps),
        })
        if recorder is not None:
            recorder.begin_batch(batch_index=batch_index, step_indices=step_indices)

    async def run_one(step, slot):
        async with sem:
            results[slot] = await _invoke_step_with_gate(
                step, tools, gate, renderer, recorder
            )

    coros = [run_one(s, idx) for s, idx in zip(steps, step_indices)]
    outcomes = await asyncio.gather(*coros, return_exceptions=True)

    # Note: _invoke_step_with_gate swallows exceptions already and writes to
    # the slot, so `outcomes` is typically [None, None, ...]. We still pass
    # return_exceptions=True so a BaseException sneaking through (e.g.,
    # CancelledError from outer cancel) is captured rather than silenced.

    # ok/err counts derived from slot contents (the swallowed-exception strings
    # all start with "<error: " or "<denied: " — match those for err_count).
    ok_count = sum(
        1 for idx in step_indices
        if results[idx] is not None
        and not str(results[idx]).startswith(("<error:", "<denied:"))
    )
    err_count = len(step_indices) - ok_count

    if batch_index is not None:
        wall_ms = int((time.perf_counter() - t0) * 1000)
        telemetry.emit("batch.end", "info", data={
            "batch_index": batch_index,
            "wall_clock_ms": wall_ms,
            "ok_count": ok_count,
            "err_count": err_count,
        })
        if recorder is not None:
            recorder.end_batch(wall_clock_ms=wall_ms, ok_count=ok_count, err_count=err_count)
```

**Singleton path** (`_dispatch_singleton`) — same body as `_invoke_step_with_gate`, but writes directly into `results[step_index]` and emits **no** `batch.*` events. Code is identical to the per-step body above — planner can factor a single `_invoke_step_with_gate` and call it from both paths. Source: `agent.py:517–597`.

---

### `voss/harness/agent.py` — `BatchInvariantError`

**Analog:** `voss/harness/sandbox.py:25–26` (`SandboxError`)

**Pattern** (single class, standalone, three lines):
```python
# voss/harness/sandbox.py:25–26
class SandboxError(RuntimeError):
    pass
```

**T2 application** (add near top of `agent.py`, after the imports block at line ~38):
```python
class BatchInvariantError(Exception):
    """Raised when a multi-step batch contains a mutating step.

    Indicates a planner bug or partitioner regression. Surfaces in
    RunRecord.exit_reason = "batch-invariant" (additive enum value joining
    T1's done|max-iter|budget|interrupt).
    """
```

**Rationale (per T2-RESEARCH.md Open Question 2):** Standalone, not a hierarchy. `SandboxError(RuntimeError)` is the closest neighbor and it doesn't introduce a domain root either. YAGNI.

**Exit-reason wiring** — `_run_turn_exec` (`agent.py:305–497` and T1-05's planned while-loop body) needs a sibling `except` clause:
```python
# In _run_turn_exec, parallel to T1-06's planned `except asyncio.CancelledError`:
except BatchInvariantError as e:
    rec.exit_reason = "batch-invariant"  # T1-01's RunRecorder API
    # finalize and re-raise or return TurnResult with appropriate status
```
The exact placement depends on T1-05/T1-06 final shape; planner reads those plans before wiring.

---

### `voss/harness/tools.py` — `fs_read_many` (tool, bundled read)

**Analog:** `voss/harness/tools.py:51–61` (`fs_read`) for error envelopes; `:96–97` for truncation marker.

**Imports pattern** — no new imports needed. `jail_path` already at line 11, `tool` decorator at line 9, `Path` at line 6.

**Error envelope pattern** (copy verbatim):
```python
# voss/harness/tools.py:51–61
@tool(name="fs_read", description="Read a UTF-8 text file from the project. Path must be inside cwd.")
async def fs_read(path: str) -> str:
    p = jail_path(cwd, path)
    if not p.exists():
        return f"<error: not found: {path}>"
    if p.is_dir():
        return f"<error: is a directory: {path}>"
    try:
        return p.read_text()
    except UnicodeDecodeError:
        return f"<error: binary file: {path}>"
```

**Truncation marker** (copy verbatim):
```python
# voss/harness/tools.py:96–97
if len(text) > 4096:
    text = text[:4096] + f"\n<truncated, total {len(out)} bytes>"
```

**T2 application** — `fs_read_many` body (drop into `make_toolset` between existing tools):
```python
@tool(
    name="fs_read_many",
    description=(
        "Read N files as one bundle. Returns sections separated by `=== {path} ===`. "
        "Per-path errors are inline (other paths still readable). Each file capped at 30KB."
    ),
)
async def fs_read_many(paths: list[str]) -> str:
    if not paths:
        return "<no paths requested>"
    sections: list[str] = []
    for path in paths:
        sections.append(f"=== {path} ===\n{_read_one_for_bundle(cwd, path)}\n")
    return "\n".join(sections)
```

Helper `_read_one_for_bundle` lives at module scope (mirrors `_shell_capture` at `tools.py:210`):
```python
def _read_one_for_bundle(cwd: Path, path: str) -> str:
    """Per-slot reader for fs_read_many. Never raises; returns content OR error envelope."""
    try:
        p = jail_path(cwd, path)
    except SandboxError:
        return f"<error: path outside cwd: {path}>"
    if not p.exists():
        return f"<error: not found: {path}>"
    if p.is_dir():
        return f"<error: is a directory: {path}>"
    try:
        text = p.read_text()
    except UnicodeDecodeError:
        return f"<error: binary file: {path}>"
    if len(text) > 30_720:  # 30KB cap (T2-CONTEXT.md D-13)
        text = text[:30_720] + f"\n<truncated, total {len(text)} bytes>"
    return text
```

**Registration** (mirror existing entries at `tools.py:196–207`):
```python
"fs_read_many": ToolEntry(descriptor=fs_read_many, is_mutating=False),
```

---

### `voss/harness/tools.py` — `fs_edit_many` (tool, atomic multi-edit through DiffModal)

**Analog:** `voss/harness/tools.py:107–128` (`fs_edit`)

**Existing single-edit pattern**:
```python
# voss/harness/tools.py:107–128
@tool(
    name="fs_edit",
    description=(
        "Replace exact `old` text with `new` in a file. `old` must appear "
        "exactly once. Returns line count delta."
    ),
)
async def fs_edit(path: str, old: str, new: str) -> str:
    p = jail_path(cwd, path)
    if not p.exists():
        return f"<error: not found: {path}>"
    text = p.read_text()
    count = text.count(old)
    if count == 0:
        return f"<error: `old` not found in {path}>"
    if count > 1:
        return f"<error: `old` matches {count} times, must be unique>"
    new_text = text.replace(old, new, 1)
    p.write_text(new_text)
    delta = new_text.count("\n") - text.count("\n")
    sign = "+" if delta >= 0 else ""
    return f"edited {path} ({sign}{delta} lines)"
```

**Hunk shape** (consumer side) — `voss/harness/tui/widgets/diff_modal.py:21–32`:
```python
@dataclass(frozen=True)
class Hunk:
    file: str
    start: int
    lines: list[str]

@dataclass(frozen=True)
class DiffDecision:
    file: str
    decision: str  # 'accept' | 'reject' | 'skip'
```

**Modal call surface** — `voss/harness/tui/renderer.py:306–323`:
```python
def show_diff_modal(
    self, hunks: list[Hunk], *, timeout_s: float = 300.0
) -> list[DiffDecision]:
    # Blocks on a Future; returns [] on cancel/timeout.
```

**T2 application** — `fs_edit_many` body. Note the **left-to-right propagation** of the working buffer (T2-RESEARCH.md Pitfall 5) and **renderer must be passed in** (the existing `make_toolset(cwd)` only takes cwd; planner extends signature to `make_toolset(cwd, *, renderer=None)` — keep `renderer=None` default and call modal only when renderer is non-None, so the tool stays test-friendly):
```python
@tool(
    name="fs_edit_many",
    description=(
        "Atomically apply N edits to one file. Each `edits` entry is "
        "{old, new}; each `old` must match uniquely in the working buffer. "
        "Routes through the diff modal per hunk. Rejecting any hunk cancels "
        "the whole batch — file unchanged on disk."
    ),
)
async def fs_edit_many(path: str, edits: list[dict]) -> str:
    p = jail_path(cwd, path)
    if not p.exists():
        return f"<error: not found: {path}>"
    if p.is_dir():
        return f"<error: is a directory: {path}>"
    try:
        snapshot = p.read_text()
    except UnicodeDecodeError:
        return f"<error: binary file: {path}>"

    # Phase 1: validate-then-build hunks against the CURRENT working buffer.
    buf = snapshot
    hunks: list[Hunk] = []
    for i, e in enumerate(edits):
        old, new = e.get("old", ""), e.get("new", "")
        if not old:
            return f"<error: batch rejected at index {i}: empty `old`>"
        count = buf.count(old)
        if count == 0:
            return f"<error: batch rejected at index {i}: `old` not found>"
        if count > 1:
            return f"<error: batch rejected at index {i}: `old` matches {count} times>"
        idx = buf.find(old)
        line_start = buf.count("\n", 0, idx) + 1
        old_lines = [f"- {l}" for l in (old.splitlines() or [""])]
        new_lines = [f"+ {l}" for l in (new.splitlines() or [""])]
        hunks.append(Hunk(file=path, start=line_start, lines=old_lines + new_lines))
        buf = buf[:idx] + new + buf[idx + len(old):]

    # Phase 2: show modal (skipped in test if renderer is None).
    if renderer is not None:
        decisions = renderer.show_diff_modal(hunks, timeout_s=300.0)
        if not decisions:
            return "<denied: modal cancelled or timed out>"
        for i, d in enumerate(decisions):
            if d.decision == "reject":
                return f"<denied: hunk {i} rejected>"

    # Phase 3: atomic write.
    p.write_text(buf)
    delta = buf.count("\n") - snapshot.count("\n")
    sign = "+" if delta >= 0 else ""
    return f"edited {path} ({sign}{delta} lines, {len(edits)} hunks)"
```

**Registration** (`tools.py:196–207`):
```python
"fs_edit_many": ToolEntry(descriptor=fs_edit_many, is_mutating=True),
```

**Skip-decision semantics** (T2-RESEARCH.md Open Question 1) — planner picks. Default per research: treat `skip` as **NOT a rejection** (permissive). If user prefers strict (skip = deny), change the inner loop to `if d.decision in ("reject", "skip"):`.

---

### `voss/harness/tools.py` — `make_toolset` signature + registration

**Analog:** `voss/harness/tools.py:44–207` (existing function).

**Existing registration pattern** (copy this exact dict shape):
```python
# voss/harness/tools.py:196–207
return {
    "fs_read": ToolEntry(descriptor=fs_read, is_mutating=False),
    "fs_glob": ToolEntry(descriptor=fs_glob, is_mutating=False),
    "fs_grep": ToolEntry(descriptor=fs_grep, is_mutating=False),
    "fs_write": ToolEntry(descriptor=fs_write, is_mutating=True),
    "fs_edit": ToolEntry(descriptor=fs_edit, is_mutating=True),
    "shell_run": ToolEntry(descriptor=shell_run, is_mutating=True),
    "git_status": ToolEntry(descriptor=git_status, is_mutating=False),
    "git_diff": ToolEntry(descriptor=git_diff, is_mutating=False),
    "voss_check": ToolEntry(descriptor=voss_check, is_mutating=False),
    "record_run": ToolEntry(descriptor=record_run, is_mutating=True),
}
```

**T2 additions** — two new keys:
```python
    "fs_read_many": ToolEntry(descriptor=fs_read_many, is_mutating=False),
    "fs_edit_many": ToolEntry(descriptor=fs_edit_many, is_mutating=True),
```

**Signature extension** — `make_toolset(cwd, *, renderer=None) -> dict[str, ToolEntry]`. Callers in `voss/harness/agent.py:444` and elsewhere pass `renderer` positionally to `_run_step_loop`; planner threads `renderer=renderer` through `make_toolset(...)` at construction time. Search for call sites: `grep -rn "make_toolset(" voss/ voss_runtime/ tests/`.

---

### `voss/harness/session.py` — `BatchRecord` dataclass

**Analog:** `voss/harness/session.py:70–87` (`RunRecord`) for dataclass shape; T1-01's planned `IterationRecord` for the additive pattern.

**Existing dataclass pattern** (copy structure exactly):
```python
# voss/harness/session.py:70–87
@dataclass
class RunRecord:
    id: str
    started_at: str
    ended_at: str
    goal: str = ""
    plan: Optional[dict] = None
    inspected: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    # ... more additive fields
    cost_usd: float = 0.0
```

**T2 `BatchRecord`** (add just above the T1-planned `IterationRecord` definition):
```python
@dataclass
class BatchRecord:
    """One parallel read-batch within an iteration. Singletons emit no BatchRecord."""
    batch_index: int                              # monotonic within iteration
    step_indices: list[int] = field(default_factory=list)
    parallel_count: int = 0
    wall_clock_ms: int = 0
    ok_count: int = 0
    err_count: int = 0
    # Optional started_at/ended_at left to planner discretion (T2-CONTEXT.md
    # Claude's Discretion); if added, defaults to "" string mirroring
    # IterationRecord's started_at/ended_at convention from T1-01.
```

**T1's `IterationRecord` gains a field** (additive, default empty):
```python
# In IterationRecord (from T1-01-PLAN.md):
batches: list[BatchRecord] = field(default_factory=list)
```

**Round-trip guarantee** — `dataclasses.asdict` (used in `session.py:152` `save()`) recursively serializes nested dataclasses to dicts. No custom `to_dict` needed. Old fixtures (no `batches` key) round-trip because `field(default_factory=list)` fills the empty list on load.

---

### `voss/harness/recorder.py` — `begin_batch` / `end_batch`

**Analog:** `voss/harness/recorder.py:53–78` (`RunRecorder.observe`) for capture API shape; T1-01's planned `begin_iteration` / `end_iteration` for nesting pattern.

**Existing capture API** (copy method shape):
```python
# voss/harness/recorder.py:53–78
def observe(self, tool_name: str, args: dict, result: Any, *, ok: bool) -> None:
    if not ok:
        self.failures.append(
            {"tool": tool_name, "error": str(result)[:FAILURE_TRUNC]}
        )
        return
    if tool_name in INSPECT_TOOLS:
        path = args.get("path") or args.get("pattern") or ""
        if path:
            self.inspected.append(path)
    # ... etc
```

**T2 application** — two new methods on `RunRecorder`. They write into the *currently-active* `IterationRecord` (T1-01 establishes `_iterations: list[IterationRecord]` with the last entry being "current"):
```python
def begin_batch(self, *, batch_index: int, step_indices: list[int]) -> BatchRecord:
    """Append a new BatchRecord to the current iteration's batches list."""
    if not self._iterations:
        # Defensive: T1-01 guarantees begin_iteration was called first.
        raise RuntimeError("begin_batch called outside an iteration scope")
    br = BatchRecord(
        batch_index=batch_index,
        step_indices=list(step_indices),
        parallel_count=len(step_indices),
    )
    self._iterations[-1].batches.append(br)
    return br

def end_batch(self, *, wall_clock_ms: int, ok_count: int, err_count: int) -> None:
    """Patch the trailing BatchRecord on the current iteration with totals."""
    if not self._iterations or not self._iterations[-1].batches:
        raise RuntimeError("end_batch called without a matching begin_batch")
    br = self._iterations[-1].batches[-1]
    br.wall_clock_ms = wall_clock_ms
    br.ok_count = ok_count
    br.err_count = err_count
```

`begin_batch` / `end_batch` are no-ops if `recorder is None` at the call site (the scheduler already guards every recorder call with `if recorder is not None:`).

---

### `voss/harness/config.py` — `load_agent_config` / `get_max_parallel_reads`

**Analog:** T1-04's planned `load_agent_config` / `get_max_iterations` (`.planning/phases/T1-iteration-loop-streaming-interrupt/T1-04-PLAN.md`); existing `load_harness_config` (`config.py:30–39`).

**Existing regex pattern**:
```python
# voss/harness/config.py:18–39
_HARNESS_BLOCK = re.compile(r"^\[harness\][^\[]*", re.MULTILINE)
_KV = re.compile(r'^\s*(\w+)\s*=\s*"((?:[^"\\]|\\.)*)"\s*$', re.MULTILINE)


def _parse_harness_section(text: str) -> dict[str, str]:
    m = _HARNESS_BLOCK.search(text)
    if not m:
        return {}
    block = m.group(0)
    return {k: v for k, v in _KV.findall(block)}


def load_harness_config() -> dict[str, str]:
    """Return the `[harness]` section as a dict. Missing file -> {}."""
    p = config_path()
    if not p.exists():
        return {}
    try:
        text = p.read_text()
    except OSError:
        return {}
    return _parse_harness_section(text)
```

**T1-04 establishes the `[agent]` section parser**. T2 piggybacks one more key. The `_KV` regex captures double-quoted string values; for integer values (`max_parallel_reads = 8` without quotes), planner extends `_KV` OR adds a parallel `_KV_INT = re.compile(r'^\s*(\w+)\s*=\s*(\d+)\s*$', re.MULTILINE)`. The cleaner path is **always quote ints in the on-disk file** (`max_parallel_reads = "8"`) and cast at read time — this is what T1-04 does for `max_iterations`. Adopt the same convention.

**T2 application** (added by T1-04, extended by T2 with one more reader):
```python
def get_max_parallel_reads() -> int:
    """Resolve [agent] max_parallel_reads with safe fallback + range validation."""
    from voss_runtime import get_config
    default = get_config().max_parallel_reads  # T2 adds this field to RuntimeConfig
    cfg = load_agent_config()  # T1-04 introduces
    raw = cfg.get("max_parallel_reads")
    if raw is None:
        return default
    try:
        n = int(raw)
    except (TypeError, ValueError):
        import warnings
        warnings.warn(
            f"[agent] max_parallel_reads = {raw!r} is not an integer; "
            f"falling back to default {default}",
            RuntimeWarning,
        )
        return default
    if not (1 <= n <= 32):
        import warnings
        warnings.warn(
            f"[agent] max_parallel_reads = {n} out of range 1–32; "
            f"falling back to default {default}",
            RuntimeWarning,
        )
        return default
    return n
```

**Bootstrapping at `cli.py` boot** (T1-04 establishes the pattern):
```python
# cli.py — call once at startup so get_config() is single source of truth.
from voss_runtime import configure
from voss.harness.config import get_max_iterations, get_max_parallel_reads
configure(
    max_iterations=get_max_iterations(),       # T1-04
    max_parallel_reads=get_max_parallel_reads(),  # T2
)
```

**`voss_runtime/_config.py`** — add field to `RuntimeConfig` (same pattern as T1-04's `max_iterations`):
```python
@dataclass
class RuntimeConfig:
    # ... existing fields ...
    max_iterations: int = 8        # T1-04
    max_parallel_reads: int = 8    # T2 — same default per T2-CONTEXT.md D-15
```

---

### Tests

#### `tests/harness/test_step_loop_partition.py` (NEW)

**Analog:** `tests/harness/test_recorder.py:1–66` (overall shape) + asyncio test idioms (project uses `asyncio_mode = "auto"`, so plain `async def test_*` works).

**Test shape pattern** (from `tests/harness/test_recorder.py:12–27`):
```python
from __future__ import annotations
import pytest
from voss.harness.recorder import RunRecorder


def test_inspect_captures_fs_read() -> None:
    rec = RunRecorder.start()
    rec.observe("fs_read", {"path": "src/a.py"}, "contents", ok=True)
    assert rec.inspected == ["src/a.py"]
```

**T2 application**:
```python
# tests/harness/test_step_loop_partition.py
from __future__ import annotations
import asyncio
import pytest

from voss.harness.agent import _run_step_loop, BatchInvariantError, ToolCall
from voss.harness.tools import ToolEntry
from voss_runtime import tool, configure, reset_config


@pytest.fixture(autouse=True)
def _config():
    reset_config()
    configure(max_parallel_reads=8)
    yield
    reset_config()


async def test_partition_read_write_read_read():
    order: list[str] = []

    @tool(name="read_A")
    async def read_A() -> str:
        order.append("A"); await asyncio.sleep(0); return "a"

    @tool(name="write_B")
    async def write_B() -> str:
        order.append("B"); return "b"

    @tool(name="read_C")
    async def read_C() -> str:
        order.append("C"); await asyncio.sleep(0.01); return "c"

    @tool(name="read_D")
    async def read_D() -> str:
        order.append("D"); await asyncio.sleep(0.01); return "d"

    tools = {
        "read_A": ToolEntry(descriptor=read_A, is_mutating=False),
        "write_B": ToolEntry(descriptor=write_B, is_mutating=True),
        "read_C": ToolEntry(descriptor=read_C, is_mutating=False),
        "read_D": ToolEntry(descriptor=read_D, is_mutating=False),
    }
    steps = [ToolCall(name=n, args={}) for n in ("read_A", "write_B", "read_C", "read_D")]

    results = await _run_step_loop(steps, tools, None, NullRenderer(), recorder=None)

    assert results == ["a", "b", "c", "d"]
    # A finishes before B (author order); B before C/D; C and D may interleave.
    assert order.index("A") < order.index("B") < order.index("C")
    assert order.index("A") < order.index("B") < order.index("D")
```

#### `tests/harness/test_fs_edit_many.py` (NEW)

**Analog:** `tests/harness/test_recorder.py` shape + `tests/harness/test_harness_config.py` `xdg` fixture for tmp_path isolation.

**Fixtures pattern** — mock `renderer.show_diff_modal` returning a list of `DiffDecision`:
```python
class _FakeRenderer:
    def __init__(self, decisions): self._decisions = decisions
    def show_diff_modal(self, hunks, *, timeout_s=300.0):
        return self._decisions
    def show_tool_call(self, *a, **kw): pass  # no-op
```

**Four acceptance fixtures (SPEC PAR-03)**:
1. 3 valid edits → file written with all 3 applied + return string contains `+N lines`
2. edit #2 `old` matches twice → `<error: batch rejected at index 1: ...>`, file byte-for-byte unchanged
3. edit #3 `old` not found → `<error: batch rejected at index 2: ...>`, file unchanged
4. Modal rejects hunk #2 → `<denied: hunk 1 rejected>`, file unchanged

#### `tests/harness/test_fs_read_many.py` (NEW)

**Analog:** test_fs_edit_many shape but read-side; uses `tmp_path` to plant fixture files.

**Four acceptance fixtures (SPEC PAR-04)**:
1. 3 readable paths → bundle has 3 sections in request order
2. 1 missing + 2 readable → missing path slot is `<error: not found: ...>`, other two OK
3. duplicate path in list → both slots filled (no dedup)
4. `paths=[]` → `<no paths requested>`

#### `tests/harness/test_telemetry_batches.py` (NEW)

**Analog:** RESEARCH.md Code Example 6 + existing telemetry-spy patterns.

**Spy pattern** (monkeypatch `telemetry.emit`):
```python
events = []
monkeypatch.setattr(
    "voss.harness.telemetry.emit",
    lambda kind, level, *a, **kw: events.append({"kind": kind, **(kw.get("data") or {})}),
)
```
Assert exactly one `batch.start` + one `batch.end` for a 4-read parallel batch; assert NO batch events for mutating singletons; assert monotonic `batch_index` across multiple batches.

#### `tests/harness/test_agent_config.py` (EXTEND — T1-04 creates it)

**Analog:** `tests/harness/test_harness_config.py` (exact shape, copy verbatim):
```python
# tests/harness/test_harness_config.py:11–14
@pytest.fixture
def xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return tmp_path
```

**T2 extension** — add tests for:
- Default `get_max_parallel_reads() == 8`
- Override via `[agent] max_parallel_reads = "16"` returns `16`
- Out-of-range value (`"100"`) falls back to default with `warnings.warn` (use `pytest.warns(RuntimeWarning)`)
- Non-int value (`"foo"`) falls back with warning
- Both `max_iterations` and `max_parallel_reads` round-trip in the same `[agent]` block

#### `tests/perf/test_parallel_read_speedup.py` (NEW DIR + NEW FILE)

**Analog:** none in-tree. Pattern locked by RESEARCH.md Code Example 5.

Create the directory: `tests/perf/`. No `conftest.py` required (project-wide `asyncio_mode = "auto"` is set in `pyproject.toml`).

Two tests:
- `test_parallel_read_speedup_default_cap` — 6 stub-tools each `await asyncio.sleep(0.05)`, run with `max_parallel_reads=8`, measure via `time.perf_counter`, assert parallel ≤ 60% × serial.
- `test_parallel_read_speedup_cap_1_sanity` — same plan, `max_parallel_reads=1`, assert wall-clock ≥ 250ms (6 × 50ms with slack — exposes any parallelism leak).

---

## Shared Patterns

### Authentication / Authorization (per-step gate)

**Source:** `voss/harness/permissions.py:169–229` (`PermissionGate.check` + `_check_impl`)

**Apply to:** Every batched step AND every singleton. The gate fires identically inside batches and singletons — no T2 change to `PermissionGate`. The partition-time invariant (`BatchInvariantError`) is an **additional** layer, not a replacement.

```python
# voss/harness/permissions.py:169–185 (call site)
def check(self, tool_name: str, args: dict, *, is_mutating: bool = False) -> tuple[bool, str]:
    allowed, why = self._check_impl(tool_name, args, is_mutating=is_mutating)
    if telemetry.enabled():
        telemetry.emit("permission.result", "info", data={
            "tool": tool_name, "allowed": allowed, "why": why,
            "mode": self.mode,
            "args": telemetry.redact_tool_args(dict(args)),
        })
    return allowed, why
```

In T2's `_invoke_step_with_gate`, the gate is called per step (whether inside a batch or singleton). Identical to today.

### Error Envelopes

**Source:** `voss/harness/tools.py:55–61` (`<error: ...>` strings)

**Apply to:** Both new tools (`fs_read_many` per-slot errors, `fs_edit_many` whole-batch errors). Existing prefixes:
- `<error: not found: {path}>`
- `<error: is a directory: {path}>`
- `<error: binary file: {path}>`
- `<error: path outside cwd: {path}>` (new — D-14; follows the same convention)
- `<denied: ...>` (from permission gate / modal rejections)
- `<error: batch rejected at index {i}: {reason}>` (new — SPEC PAR-03)

### Truncation Marker

**Source:** `voss/harness/tools.py:96–97` and `:227`
```python
text = text[:CAP] + f"\n<truncated, total {N} bytes>"
```
**Apply to:** `fs_read_many` per-file 30KB cap. Reuse the exact format string.

### Path Jailing

**Source:** `voss/harness/sandbox.py:29–40` (`jail_path` + `SandboxError`)
```python
def jail_path(cwd: Path, target: str | os.PathLike) -> Path:
    cwd_real = cwd.resolve()
    p = Path(target)
    if not p.is_absolute():
        p = cwd_real / p
    p = p.resolve()
    try:
        p.relative_to(cwd_real)
    except ValueError as e:
        raise SandboxError(f"path escapes cwd: {p}") from e
    return p
```
**Apply to:** Every path argument in `fs_read_many` (per slot) and `fs_edit_many` (single path). `fs_read_many` wraps in `try/except SandboxError` for partial-result semantics; `fs_edit_many` lets the error propagate to the caller (single path = whole-call failure).

### Telemetry Emit

**Source:** `voss/harness/telemetry.py:150–183` (`emit(kind, level, msg=None, *, data=None)`)
```python
def emit(kind: str, level: str, msg: str | None = None, *, data: dict[str, Any] | None = None) -> None:
```
**Apply to:** New `batch.start` / `batch.end` events. Schema is open-ended `data: dict`, so no helper changes needed. Just call:
```python
telemetry.emit("batch.start", "info", data={"batch_index": 0, "step_indices": [...], "parallel_count": 4})
telemetry.emit("batch.end",   "info", data={"batch_index": 0, "wall_clock_ms": 123, "ok_count": 4, "err_count": 0})
```

### Redaction

**Source:** `voss/harness/telemetry.py:87–112` (`redact_tool_args`)

**Apply to:** Per-step `tool.call` / `tool.result` events inside batches (unchanged from today — the existing redaction surface covers `old`, `new`, `content`, `cmd`). No new redaction work for T2; `fs_edit_many.edits` is a list-of-dicts — planner SHOULD audit whether the existing shallow redaction covers nested `old`/`new` inside list items. If not, extend `redact_tool_args` for the `edits` key (treat as a structural extension at the redaction layer, not at the telemetry emit layer).

### Test Fixture Convention (XDG isolation)

**Source:** `tests/harness/test_harness_config.py:11–14`
```python
@pytest.fixture
def xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return tmp_path
```
**Apply to:** `test_agent_config.py` extensions (config-file round-trip tests).

### RuntimeConfig Reset (test isolation)

**Source:** T1-04 plan + existing `voss_runtime` API (`reset_config()` + `configure(**kwargs)`).
```python
@pytest.fixture(autouse=True)
def _config():
    reset_config()
    configure(max_parallel_reads=8)
    yield
    reset_config()
```
**Apply to:** Every test that exercises the scheduler with non-default cap (`test_step_loop_partition.py`, `test_parallel_read_speedup.py`).

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tests/perf/test_parallel_read_speedup.py` | perf benchmark | stub-timed | No `tests/perf/` directory exists. Stub-timed benchmark pattern is greenfield. Use RESEARCH.md Code Example 5 as the canonical shape. |

All other new/modified files have at least one strong in-tree analog.

---

## Metadata

**Analog search scope:**
- `voss/harness/` — all `.py` files (agent, tools, recorder, session, permissions, telemetry, config, sandbox, tui/widgets/diff_modal, tui/renderer)
- `voss_runtime/` — `agent.py`, `_config.py`
- `tests/harness/` — `test_recorder.py`, `test_harness_config.py`, listing of all 35+ test files
- `.planning/phases/T1-iteration-loop-streaming-interrupt/` — `T1-01-PLAN.md` (IterationRecord shape), `T1-04-PLAN.md` (config loader shape)

**Files scanned:** ~15 source files, ~5 test files, ~4 phase-plan documents.

**Pattern extraction date:** 2026-05-15

**Key insight reinforced from RESEARCH.md:** T2 is a *composition* phase. Every primitive (asyncio gather, semaphore, jail_path, error envelopes, truncation markers, redaction, dataclass schema additions, regex config loader, modal call surface, telemetry emit) is already in-tree. Planner must resist the urge to invent new shapes — every new file should be a thin, parameterized copy of the cited analog.

## PATTERN MAPPING COMPLETE
