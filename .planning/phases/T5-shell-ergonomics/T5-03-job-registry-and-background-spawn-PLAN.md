---
phase: T5-shell-ergonomics
plan: 03
type: execute
wave: 3
depends_on: [T5-01, T5-02]
files_modified:
  - voss/harness/lifecycle.py
  - voss/harness/tools.py
autonomous: true
requirements: [SHELL-02]
user_setup: []

must_haves:
  truths:
    - "shell_run_background(cmd) spawns a detached allowlisted process and returns bg-NNN with NO PID in the string (D-01)"
    - "The handle counter is session-scoped, monotonic, zero-padded to 3 digits"
    - "stdout+stderr merge to .voss-cache/jobs/<session_id>/<handle>.log (D-02)"
    - "A <handle>.meta.json sidecar is written atomically on every state transition (D-11)"
    - "One supervisor asyncio task per job does pump + 30s-no-output watchdog + 100MB RSS poll, race-free"
    - "On session exit reap_jobs SIGTERMs at t≈0 and SIGKILLs the process GROUP at t=5s (SC#2 verbatim) and emits shell.background.reap"
    - "_JOBS, _atexit_hook, reap_all, reset_for_tests are EXTENDED not duplicated — no second atexit hook"
  artifacts:
    - path: "voss/harness/lifecycle.py"
      provides: "JobRecord dataclass, register_job, reap_jobs, the supervisor task, _tree_rss_bytes, atomic .meta.json sidecar, _JOBS reap wiring"
      contains: "def register_job"
    - path: "voss/harness/tools.py"
      provides: "shell_run_background tool descriptor + ToolEntry registration"
      contains: "shell_run_background"
  key_links:
    - from: "voss/harness/tools.py shell_run_background"
      to: "voss.harness.lifecycle.register_job"
      via: "from . import lifecycle"
      pattern: "lifecycle.register_job"
    - from: "voss/harness/lifecycle.py supervisor task"
      to: ".voss-cache/jobs/<session_id>/<handle>.log + .meta.json"
      via: "unbuffered append + atomic temp→.replace()"
      pattern: "\\.replace\\("
    - from: "voss/harness/lifecycle.py reap_jobs"
      to: "telemetry.emit shell.background.reap"
      via: "lazy import inside fn"
      pattern: "shell.background.reap"
---

<objective>
Build the T5 core: the `JobRecord` dataclass, the `_JOBS`-backed `register_job`/`reap_jobs`/`signal_job` lifecycle API, the single per-job supervisor task (stdout→disk pump fused with the 30s-no-output watchdog and 100MB RSS poll), the atomic `.meta.json` sidecar, `start_new_session=True` + `os.killpg` tree-kill, the `shell.background.reap` telemetry emit, and the `shell_run_background` tool + its `ToolEntry` registration (SHELL-02).

Purpose: This is the headless engine of T5. Long builds/test-runs run detached, output streams to an inspectable disk tail, runaway processes die on watchdog or session exit, and the cross-process `voss jobs` (T5-05) reads the sidecar this plan writes.
Output: `lifecycle.py` gains `JobRecord` + registry API + supervisor + sidecar + tree-kill + reap telemetry; `tools.py` gains `shell_run_background` + registration.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/T5-shell-ergonomics/T5-CONTEXT.md
@.planning/phases/T5-shell-ergonomics/T5-RESEARCH.md
@.planning/phases/T5-shell-ergonomics/T5-PATTERNS.md

<interfaces>
JobRecord schema (D-01/D-11 — the sidecar IS this dataclass serialized):
  handle: str            # "bg-NNN", zero-padded 3, monotonic per session
  pid: int               # internal + on-disk; NEVER in a tool-return string (D-01)
  started_at: str        # ISO8601 (datetime.now(timezone.utc).isoformat(timespec="seconds"))
  cmd: str               # the raw command string
  log_path: str          # absolute path to <handle>.log
  status: str            # "running" | "done" | "killed"
  exit_code: int | None  # None while running
  runtime_ms: int        # updated on transitions
  # non-serialized runtime fields (NOT in asdict for the sidecar):
  #   proc: asyncio.subprocess.Process
  #   task: asyncio.Task  (the supervisor — strong ref, prevents GC per Pitfall 6)

register_job(*, cmd, argv, cwd, session_id) -> str
  # mints bg-NNN (session counter), creates log+meta dirs, spawns proc with
  # start_new_session=True, writes first .meta.json (status="running"),
  # creates+stores the supervisor asyncio.Task on the record, returns "bg-NNN".

reap_jobs() -> None
  # for each running job: killpg SIGTERM at t≈0, wait_for(5.0), killpg SIGKILL
  # at t=5s; cancel supervisor task; emit shell.background.reap reason="session_exit".

signal_job(handle: str, sig: int) -> bool          # used by T5-04 shell_signal

_tree_rss_bytes(pid: int) -> int                   # psutil tree-sum; monkeypatched in tests
</interfaces>

<existing_patterns>
Allowlist-then-spawn prologue — COPY VERBATIM from voss/harness/tools.py:134-147:
```python
ok, reason = shell_allowed(cmd)
if not ok:
    return f"<denied: {reason}>"
try:
    argv = split_command(cmd)
except SandboxError as e:
    return f"<denied: {e}>"
```
(shell_run then does create_subprocess_exec + wait_for(communicate(), timeout=30.0)
at tools.py:148-152 — shell_run_background DIVERGES here: no communicate, no
wait_for; it delegates to lifecycle.register_job and returns the bare slug.)

Reap-with-deadline ladder — COPY the shape from voss/harness/lifecycle.py:42-63
(terminate → wait_for(_TERM_DEADLINE_S=5.0) → kill → wait, each guarded). For T5
use os.killpg(os.getpgid(proc.pid), signal.SIGTERM/SIGKILL) instead of bare
proc.terminate()/proc.kill() because start_new_session put the job in its own
process group (kills grandchildren too — RESEARCH Anti-Pattern resolution).

Atomic sidecar write — COPY VERBATIM from voss/harness/sandbox.py:99-101:
```python
tmp = target.with_suffix(target.suffix + ".tmp")
tmp.write_text(text)
tmp.replace(target)
```
plus the .voss-cache jailing from sandbox.py:95-98 (jail_path + mkdir parents).

Additive dataclass + tolerant _hydrate — voss/harness/session.py:146-189
(@dataclass, classmethod new(), `_FIELDS = {f.name for f in fields(...)}`,
`_hydrate` keeps only known keys). Mirror so the sidecar schema can evolve for M14.

Supervisor task skeleton ([ASSUMED] — RESEARCH §Pattern 2, quote then refine):
```python
async def _supervise(rec: "JobRecord", no_output_deadline_s: float = 30.0) -> None:
    proc = rec.proc
    last_rss_poll = 0.0
    with open(rec.log_path, "ab", buffering=0) as fh:   # unbuffered append (Pitfall 2/6)
        while True:
            try:
                chunk = await asyncio.wait_for(
                    proc.stdout.read(65536), timeout=no_output_deadline_s)
            except asyncio.TimeoutError:
                _kill_tree(proc); rec.status = "killed"
                _emit_reap(rec, signal="KILL", reason="watchdog_no_output"); break
            if not chunk:
                await proc.wait()
                rec.status = "done"; rec.exit_code = proc.returncode; break
            fh.write(chunk)
            now = time.monotonic()
            if now - last_rss_poll >= 1.0:
                last_rss_poll = now
                if _tree_rss_bytes(rec.pid) > 100 * 1024 * 1024:
                    _kill_tree(proc); rec.status = "killed"
                    _emit_reap(rec, signal="KILL", reason="watchdog_mem"); break
    _write_meta(rec)
```
Key invariants the executor MUST preserve: ONE task (pump+watchdog are the SAME
wait_for); strong ref via rec.task in _JOBS; 64KB reads (StreamReader limit,
Pitfall 2); unbuffered append so same-process shell_monitor sees bytes (Pitfall 6);
_write_meta on EVERY transition.

Telemetry flat-dict call site — voss/harness/permissions.py:182-193 form:
```python
from . import telemetry  # lazy import inside fn (permissions.py:180 precedent)
telemetry.emit("shell.background.reap", "info",
    data={"handle": rec.handle, "pid": rec.pid, "signal": sig,
          "exit_code": rec.exit_code, "runtime_ms": runtime_ms, "reason": reason})
```

reset_for_tests / _atexit_hook / reap_all extension points (declared/extended in
T5-01 for _JOBS dict; this plan adds the reap behavior):
  - lifecycle.py:75-77 reset_for_tests — now clears _JOBS (T5-01); ADD: cancel
    each live rec.task before clearing.
  - lifecycle.py:80-82 _atexit_hook guard `if not _SUBPROCESSES and not _SESSIONS:`
    → extend to `... and not _JOBS:`.
  - lifecycle.py:38-72 reap_all — after the existing _SUBPROCESSES/_SESSIONS
    drain, call `await reap_jobs()` (so atexit reaps jobs too — single hook).
</existing_patterns>

<source_audit_note>
RESEARCH Open-Q2 / Flag 4 / SC#2 verbatim (ROADMAP.md:928-929):
"Orphaned background jobs get SIGTERM within 2s, SIGKILL at 5s on session exit."
PINNED reading (do NOT silently reuse reap_all's behavior without this pinning):
SIGTERM is issued at t≈0 (the "within 2s" clause is a LATENCY CEILING on issuing
SIGTERM, not a SIGTERM→SIGKILL gap), then wait_for(timeout=5.0), then SIGKILL at
t=5s hard deadline. Reuse the existing `_TERM_DEADLINE_S = 5.0` constant unchanged.
The escalation test asserts SIGTERM≈t0 and SIGKILL at ~5s (4.5..6.5 bound, mirrors
test_lifecycle.py:56).
</source_audit_note>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: JobRecord + register_job + supervisor task + atomic sidecar + tree-RSS probe</name>
  <files>voss/harness/lifecycle.py</files>
  <behavior>
    - register_job mints bg-001 for the first job in a session, bg-002 next; counter is per-session, zero-padded to 3 (test_handle_counter).
    - register_job spawns with start_new_session=True, creates `.voss-cache/jobs/<session_id>/`, writes `<handle>.meta.json` with status="running" before returning the handle.
    - The supervisor pumps stdout+stderr (merged) into `<handle>.log` unbuffered; a concurrent short-lived reader sees bytes immediately (backs T5-04 shell_monitor).
    - On natural EOF: status="done", exit_code=proc.returncode, final .meta.json written.
    - With injected `no_output_deadline_s=0.3`: a silent child is killed (tree), status="killed", `shell.background.reap` emitted with reason="watchdog_no_output" (test_no_output_watchdog).
    - With `_tree_rss_bytes` monkeypatched to return >100MB: child killed (tree), reason="watchdog_mem", no real allocation (test_rss_watchdog).
    - JobRecord serializes to the D-11 dict ({handle,pid,started_at,cmd,log_path,status,exit_code,runtime_ms}); proc/task are NOT in the serialized form; tolerant `_hydrate` keeps only known keys.
  </behavior>
  <action>
    In voss/harness/lifecycle.py add (imports first: `import json`, `import os`, `import signal`, `import time`, `import uuid` as needed, `from dataclasses import dataclass, field, asdict`, `from datetime import datetime, timezone`, `from pathlib import Path`, `import psutil`; mirror the import discipline already in the file):

    1. `@dataclass class JobRecord` with the D-11 serialized fields plus non-init/non-serialized runtime fields `proc` and `task` (use `field(default=None, repr=False, compare=False)` and EXCLUDE them from the sidecar — define an explicit `to_meta() -> dict` returning only the 8 D-11 keys rather than bare `asdict`, since `asdict` would choke on the Process/Task). Add `_JOB_FIELDS = {...8 keys...}` and a tolerant `_hydrate_job(data: dict) -> JobRecord` mirroring session.py:184-188 (for T5-05 / forward-compat). A module-level `_HANDLE_COUNTERS: dict[str, int] = {}` keyed by session_id provides the monotonic per-session counter; `reset_for_tests` (Task 3) must also clear it.

    2. `_meta_path(rec)` / `_log_path(session_id, handle)` helpers that jail under `.voss-cache/jobs/<session_id>/` using the sandbox jailing idiom (sandbox.py:95-101 — `jail_path` + `mkdir(parents=True, exist_ok=True)`). `_write_meta(rec)`: serialize `rec.to_meta()` to JSON and write via the atomic temp→`.replace()` idiom (sandbox.py:99-101) so the out-of-process `voss jobs` always reads complete JSON.

    3. `_tree_rss_bytes(pid: int) -> int`: `psutil.Process(pid)`; sum `memory_info().rss` of the process plus `children(recursive=True)`; tolerate `psutil.NoSuchProcess`/`psutil.AccessDenied` by returning 0. This is the function tests monkeypatch — keep it a clean module-level function (RESEARCH §Don't-Hand-Roll: do not hand-roll /proc).

    4. `_kill_tree(proc, sig)`: `os.killpg(os.getpgid(proc.pid), sig)` guarded by ProcessLookupError/PermissionError; on non-POSIX (`os.name != "posix"`) fall back to `proc.send_signal(sig)` / `proc.kill()` (Windows TerminateProcess — documented degradation, RESEARCH Q4/Pitfall 4; not a code fix).

    5. `async def _supervise(rec, no_output_deadline_s: float = 30.0)`: quote the RESEARCH §Pattern 2 skeleton from `<existing_patterns>` and refine — ONE task, same `wait_for` is both pump and no-output watchdog, 64KB reads, unbuffered append, `_write_meta(rec)` on every transition, `_emit_reap` on watchdog kills. Compute `runtime_ms` from `started_at`/monotonic at each transition.

    6. `async def register_job(*, cmd, argv, cwd, session_id) -> str`: increment `_HANDLE_COUNTERS[session_id]`, format `bg-{n:03d}`, build log/meta dirs, `await asyncio.create_subprocess_exec(*argv, cwd=str(cwd), stdout=PIPE, stderr=STDOUT, start_new_session=(os.name=="posix"))`, construct JobRecord (status="running"), `_write_meta`, create the supervisor task `rec.task = asyncio.create_task(_supervise(rec))`, store `_JOBS[handle] = rec` (strong ref — Pitfall 6), return the handle string ONLY (no PID — D-01).

    7. `_emit_reap(rec, *, signal, reason, exit_code=None, runtime_ms)`: lazy `from . import telemetry` (permissions.py:180 precedent), `telemetry.emit("shell.background.reap", "info", data={...8 keys per D-08...})`. reason ∈ {session_exit, watchdog_no_output, watchdog_mem, explicit_signal}.

    Do NOT add the `voss jobs` CLI, `shell_monitor`, `shell_signal`, or any permissions change here — those are T5-04/T5-05.
  </action>
  <verify>
    <automated>python -m pytest "tests/harness/test_t5_shell.py::test_handle_counter" "tests/harness/test_t5_shell.py::test_no_output_watchdog" "tests/harness/test_t5_shell.py::test_rss_watchdog" tests/harness/test_lifecycle.py -x -q</automated>
    <requirement>SHELL-02, SC#3</requirement>
    <expected>Handle counter is monotonic+zero-padded per session; the no-output watchdog kills a silent child with a 0.3s injected deadline and emits reason="watchdog_no_output"; the monkeypatched RSS probe triggers reason="watchdog_mem" with no real allocation; existing test_lifecycle.py stays green (reap_all/_SUBPROCESSES untouched in behavior).</expected>
  </verify>
  <done>JobRecord + register_job + _supervise + _tree_rss_bytes + atomic _write_meta exist; counter/watchdog/RSS tests green; test_lifecycle.py unbroken.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: reap_jobs (SC#2 timing) + signal_job + atexit/reap_all/reset_for_tests wiring</name>
  <files>voss/harness/lifecycle.py</files>
  <behavior>
    - reap_jobs sends SIGTERM (process group) at t≈0 to every running job, waits up to 5.0s, sends SIGKILL at t=5s; a SIG_IGN-SIGTERM child is killed in the 4.5..6.5s window (test_reap_jobs_escalation, mirrors test_lifecycle.py:56).
    - reap_jobs emits `shell.background.reap` with reason="session_exit" per reaped job; cancels the supervisor task.
    - signal_job(handle, sig) resolves the JobRecord and calls proc.send_signal(sig); returns False for an unknown handle (used by T5-04).
    - reap_all now also drains _JOBS (atexit reaps jobs — single hook, no second atexit).
    - reset_for_tests cancels every live rec.task then clears _JOBS and _HANDLE_COUNTERS (no cross-test leakage).
  </behavior>
  <action>
    In voss/harness/lifecycle.py:

    1. `async def reap_jobs() -> None`: iterate `list(_JOBS.values())` whose status is "running"/proc alive. For each: COPY the kill-ladder shape from lifecycle.py:42-63 but use `_kill_tree(proc, signal.SIGTERM)` at t≈0, then `await asyncio.wait_for(proc.wait(), timeout=_TERM_DEADLINE_S)` (reuse the EXISTING `_TERM_DEADLINE_S = 5.0` — do NOT introduce a 2s constant; see <source_audit_note>), on TimeoutError `_kill_tree(proc, signal.SIGKILL)` then `await proc.wait()`. Each guard mirrors the existing `ProcessLookupError`/`sys.stderr.write` discipline (lifecycle.py:44-63). Compute `runtime_ms`, set `rec.status="killed"` (or "done" if it exited cleanly within the deadline), `_write_meta(rec)`, cancel `rec.task` (guard `asyncio.CancelledError`), `_emit_reap(rec, signal="TERM"|"KILL", reason="session_exit", ...)`. Finally clear the reaped entries from `_JOBS`.

    2. `def signal_job(handle: str, sig: int) -> bool`: `rec = _JOBS.get(handle)`; if None return False; `rec.proc.send_signal(sig)` guarded by ProcessLookupError (return True even if already gone — the intent was delivered); on success leave status as-is (the supervisor records the eventual exit). Returns True iff the handle resolved. (T5-04's `shell_signal` maps INT/TERM→signal numbers and calls this; KILL is NOT exposed here — internal-only via reap, D-06.)

    3. Extend `reap_all` (lifecycle.py:38-72): after the existing `_SESSIONS` aclose loop and before `_SUBPROCESSES.clear()/_SESSIONS.clear()`, add `await reap_jobs()`. Do NOT register a second atexit hook (CONTEXT: T5 piggybacks). Extend `_atexit_hook` guard (lifecycle.py:81) to `if not _SUBPROCESSES and not _SESSIONS and not _JOBS:`.

    4. Extend `reset_for_tests` (lifecycle.py:75-77): before clearing, iterate `_JOBS.values()` and `if rec.task is not None: rec.task.cancel()`; then `_JOBS.clear()` and `_HANDLE_COUNTERS.clear()` (T5-01 added the bare `_JOBS.clear()`; this completes it). Wrap task cancel in a swallow guard (must not raise during test teardown).

    Keep all existing `reap_all`/`_SUBPROCESSES`/`register_subprocess`/`register_session` behavior byte-identical except the two additive insertions above.
  </action>
  <verify>
    <automated>python -m pytest "tests/harness/test_t5_shell.py::test_reap_jobs_escalation" tests/harness/test_lifecycle.py -x -q</automated>
    <requirement>SHELL-02, SC#2</requirement>
    <expected>SIG_IGN-SIGTERM job is SIGKILLed in the 4.5..6.5s window with SIGTERM at t≈0 (SC#2 verbatim); reap emits reason="session_exit"; existing test_lifecycle.py (reap_all SIGTERM<1s + SIGKILL 4.5..6.5s) still green — proving the additive reap_jobs call did not regress _SUBPROCESSES reaping.</expected>
  </verify>
  <done>reap_jobs honors SC#2 timing via the unchanged 5.0s deadline; signal_job resolves handles; atexit/reap_all/reset_for_tests extended (single hook); test_lifecycle.py unbroken.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: shell_run_background tool + ToolEntry registration</name>
  <files>voss/harness/tools.py</files>
  <behavior>
    - shell_run_background("echo hi") returns exactly "bg-001" (or next counter) — a bare slug, NO PID, NO bracket envelope (D-01: shell_run_background returns just the slug; the [cursor]/[exit] envelope belongs to shell_monitor).
    - A denied command (metachar/deny-token) returns "<denied: ...>" BEFORE any spawn (allowlist parity, D-05) — reuses shell_allowed verbatim, sandbox.py untouched.
    - The returned string contains no digits matching the OS PID (test_background_returns_handle asserts no PID leak).
    - Registered in the toolset as ToolEntry(is_mutating=True) so it is serialized and never in a parallel read batch (T2 PAR-02).
  </behavior>
  <action>
    In voss/harness/tools.py, beside `shell_run` (which ends at tools.py:158): add `@tool(name="shell_run_background", description="Run an allowlisted command in the background; returns a bg-NNN handle. Use shell_monitor(handle) to read incremental output and shell_signal(handle, 'INT'|'TERM') to stop it. Background jobs are reaped on session exit.")` `async def shell_run_background(cmd: str) -> str`. COPY the allowlist-then-spawn prologue VERBATIM from tools.py:134-140 (shell_allowed → `<denied>`; split_command → `<denied>`). Then DIVERGE from shell_run: do NOT create_subprocess_exec / wait_for here — instead resolve the session_id and delegate to lifecycle.

    Session id source (D-09): add an optional keyword-only `session_id: str | None = None` parameter to `make_toolset` (tools.py:73-78 signature — additive, default None, keyword-only so all 6 existing call sites keep working unchanged). Capture it in the `make_toolset` closure exactly as `cwd` is captured, and reference it inside `shell_run_background`. When `session_id` is None, fall back to the stable per-process default `"_nosession"` so bare-toolset unit tests still work. THIS PLAN owns ONLY the additive kwarg + closure capture + the `_nosession` fallback. The production wiring that passes the REAL `record.id` into `make_toolset` at the `voss chat` REPL (cli.py:1314) and `voss do` (cli.py:1071), plus the explicit deliberate-`_nosession` policy for the other 4 call sites, is a PLANNED + TEST-VERIFIED step — see T5-05 Task 1 (`make_toolset` session_id wiring). Do NOT leave the production wiring as an unplanned "one-liner"; T5-05 Task 1 is the place it is implemented and asserted (a job spawned via the toolset must land under `<record.id>/`, never `_nosession/`).

    Lazy `from . import lifecycle` inside the function (mirrors permissions.py:180 lazy-import precedent). `handle = await lifecycle.register_job(cmd=cmd, argv=argv, cwd=cwd, session_id=session_id or "_nosession")`. `return handle` — the bare slug only (D-01).

    Register in the toolset dict beside `"shell_run": ToolEntry(descriptor=shell_run, is_mutating=True),` at tools.py:367: add `"shell_run_background": ToolEntry(descriptor=shell_run_background, is_mutating=True),`. Do NOT add shell_monitor/shell_signal entries here (T5-04). Do NOT add anything to recorder.VALIDATE_TOOLS (RESEARCH Open-Q3 / D-08 — envelope is incompatible with `_parse_exit`; the disk log + reap event are the forensic trail).
  </action>
  <verify>
    <automated>python -m pytest "tests/harness/test_t5_shell.py::test_background_returns_handle" -x -q</automated>
    <requirement>SHELL-02</requirement>
    <expected>shell_run_background returns "bg-NNN" with no PID substring and no bracket envelope; a denied command short-circuits to "<denied: ...>" before any spawn; tool is registered is_mutating=True.</expected>
  </verify>
  <done>`shell_run_background` exists, gated by shell_allowed verbatim (sandbox.py untouched), returns the bare slug, registered is_mutating=True; PID never in the return; `make_toolset` has the additive keyword-only `session_id` param + closure capture + `_nosession` fallback; test_background_returns_handle green. (Production `record.id` wiring + per-call-site policy is owned and verified by T5-05 Task 1 — not deferred as an unplanned one-liner.)</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| agent → subprocess spawn | LLM-supplied `cmd` crosses into process execution |
| in-process _JOBS → on-disk sidecar | cross-process truth channel for `voss jobs` |
| child process tree → host resources | runaway memory / no-output / orphan grandchildren |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T5-03a | Tampering/EoP | `cmd` injection via metachars | mitigate | `shell_allowed()` reused VERBATIM before any spawn (D-05); `create_subprocess_exec` (no `/bin/sh`); sandbox.py NOT edited. |
| T-T5-03b | DoS | runaway / forkbomb background process | mitigate | 30s-no-output + 100MB-RSS supervisor watchdog; `start_new_session`+`os.killpg` tree-kill (grandchildren die); reap on session exit (SC#2). |
| T-T5-03c | Info disclosure | PID leak to the model enabling targeted signals | mitigate | D-01: only `bg-NNN` crosses the tool boundary; PID lives only on the JobRecord + on-disk sidecar (human-facing). test_background_returns_handle asserts no PID in the string. |
| T-T5-03d | DoS | orphan after host crash keeps consuming resources | accept | Documented limitation (RESEARCH Runtime State Inventory): POSIX reparents to init; out of T5 scope. `voss jobs` (T5-05) `pid_exists`-checks so it never claims false liveness. |
</threat_model>

<verification>
- `pytest tests/harness/test_t5_shell.py -k "handle_counter or watchdog or background_returns or reap_jobs_escalation" tests/harness/test_lifecycle.py -x -q` all green.
- `pytest -q -m "not live"` (wave merge) green — no regression in lifecycle/shell suites.
- SC#2: SIGTERM at t≈0, SIGKILL at ~5s (verbatim ROADMAP:928-929).
- No `4096`/recorder/permissions change in this plan (scoped to T5-02/T5-04).
</verification>

<success_criteria>
- shell_run_background spawns detached, returns bare `bg-NNN`, PID never in the string.
- One supervisor task per job (pump + no-output watchdog + RSS poll, race-free).
- Atomic `.meta.json` sidecar on every transition; merged stdout+stderr → `<handle>.log`.
- reap_jobs honors SC#2 timing reusing `_TERM_DEADLINE_S=5.0`; emits `shell.background.reap`.
- Single atexit hook; reset_for_tests cancels supervisor tasks + clears `_JOBS`/counters.
- test_lifecycle.py unbroken (additive only).
</success_criteria>

<output>
Create `.planning/phases/T5-shell-ergonomics/T5-03-SUMMARY.md` when done.
</output>
