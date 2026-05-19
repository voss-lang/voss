---
phase: M14-long-running-tasks-watch-caps-01e
plan: 02
type: execute
wave: 2
depends_on: ["M14-01"]
files_modified:
  - voss/harness/lifecycle.py
  - voss/harness/watch/__init__.py
  - voss/harness/watch/backend.py
autonomous: true
requirements: [WATCH-01, WATCH-02, WATCH-05]
user_setup: []

must_haves:
  truths:
    - "Editing a file matching a registered glob produces exactly one coalesced event within the 200ms debounce window"
    - "Editing a file NOT matching any registered glob produces zero events"
    - "_WATCHERS registry holds a WatcherRecord after register_watcher; reap_watchers() stops the Observer and clears it"
    - "_read_log_cursor produces the same [cursor N][status] format that monitor_job produces (shared, not duplicated)"
    - "reset_for_tests() clears _WATCHERS and _WATCH_HANDLE_COUNTERS; reap_all() reaps watchers before jobs"
  artifacts:
    - path: "voss/harness/lifecycle.py"
      provides: "_WATCHERS registry, WatcherRecord, _next_watch_handle, _find_watcher, _watch_dir/_watch_log_path, factored _read_log_cursor, register_watcher, reap_watchers; reap_all/reset_for_tests/_atexit_hook extended"
      contains: "_WATCHERS"
    - path: "voss/harness/watch/backend.py"
      provides: "_GlobHandler(PatternMatchingEventHandler), Debouncer (per-path threading.Timer), _WatchBackend (asyncio.Queue bridge), drain_loop, start_watcher async factory"
      contains: "class Debouncer"
      min_lines: 80
    - path: "voss/harness/watch/__init__.py"
      provides: "watch subpackage marker"
  key_links:
    - from: "voss/harness/lifecycle.py"
      to: "voss/harness/watch/backend.py"
      via: "register_watcher imports start_watcher"
      pattern: "from \\.watch(\\.backend)? import"
    - from: "voss/harness/lifecycle.py:monitor_job"
      to: "voss/harness/lifecycle.py:_read_log_cursor"
      via: "monitor_job becomes a thin wrapper calling _read_log_cursor"
      pattern: "_read_log_cursor\\("
    - from: "voss/harness/watch/backend.py:_GlobHandler"
      to: "Debouncer"
      via: "on_any_event delegates to debouncer"
      pattern: "self\\._debouncer\\.on_event"
---

<objective>
Build the shared M14 spine: the `_WATCHERS` registry + `WatcherRecord` + watch-handle counter in
`lifecycle.py` (D-04), the factored shared byte-cursor reader `_read_log_cursor` so `monitor_job` and
the future `fs_watch_poll` use ONE implementation (D-02), the lifecycle teardown wiring
(`reap_watchers` into `reap_all`, `reset_for_tests`, `_atexit_hook`), and the greenfield
`voss/harness/watch/backend.py` (watchdog Observer + per-path `threading.Timer` debounce + asyncio
bridge, D-01).

Purpose: This is the foundation both M14-03 (fs_watch tools) and M14-04 (voss watch CLI + daemon)
build on. It turns the WATCH-01 and WATCH-02 backend RED tests GREEN.
Output: extended `lifecycle.py`, new `watch/__init__.py`, new `watch/backend.py`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M14-long-running-tasks-watch-caps-01e/M14-CONTEXT.md
@.planning/phases/M14-long-running-tasks-watch-caps-01e/M14-RESEARCH.md
@.planning/phases/M14-long-running-tasks-watch-caps-01e/M14-PATTERNS.md

<interfaces>
<!-- LOCKED resolutions of the 3 RESEARCH Open Questions — bind these exactly. -->
- OQ-1 (LOCKED): add `prefix: str = "bg"` param to lifecycle._next_handle (default keeps existing
  bg-NNN callers byte-identical). Add lifecycle._WATCH_HANDLE_COUNTERS: dict[str,int] and
  lifecycle._next_watch_handle(session_id) -> "watch-NNN" (its own counter — NO collision with bg-NNN).
- OQ-2 (LOCKED, consumed by M14-03): fs_watch + fs_watch_poll are both is_mutating=False.
- OQ-3 (LOCKED, consumed by M14-04): daemon re-exec argv = [sys.executable, "-m",
  "voss.harness.cli", "watch", "--_is-worker", ...]; re-entry guard flag "--_is-worker".

_WATCHERS key type is the SAME as _JOBS: tuple[str, str] = (session_id, handle). Reuse the existing
lifecycle._job_key(session_id, handle) function — do NOT add a new key function.

WatcherRecord field set (Claude's Discretion per D-04; LOCKED here):
  handle: str
  globs: list[str]
  log_path: str
  status: str                 # "watching" | "stopped"
  session_id: str = field(default="_nosession", repr=False, compare=False)
  started_at: str
  observer: Any = field(repr=False, compare=False)        # watchdog Observer (a thread)
  drain_task: asyncio.Task | None = field(default=None, repr=False, compare=False)
  debouncer: Any | None = field(default=None, repr=False, compare=False)

backend.py public contract (M14-03/04 import these):
  async def start_watcher(globs: list[str], watch_root: Path, log_path: Path,
                          loop: asyncio.AbstractEventLoop, debounce_ms: int = 200)
                          -> tuple[Observer, asyncio.Task, Debouncer]
  class Debouncer: def on_event(path, event_type) -> None; def cancel_all() -> None
  class _GlobHandler(PatternMatchingEventHandler)

From voss/harness/lifecycle.py (verified seams, exact line numbers):
  lines 35-40   _JOBS/_HANDLE_COUNTERS declaration block (+ "separate registry" comment) — add _WATCHERS sibling after
  lines 107-118 _job_dir/_log_path (jail_path-based) — model _watch_dir/_watch_log_path
  lines 276-279 _next_handle (currently `return f"bg-{n:03d}"`) — add prefix param
  lines 286-292 _find_job — model _find_watcher
  lines 454-482 monitor_job — EXTRACT byte-cursor block into _read_log_cursor; monitor_job becomes thin wrapper
  lines 395-440 reap_jobs — model reap_watchers (observer.stop()/join() instead of _kill_tree)
  lines 485-519 reap_all — add `await reap_watchers()` BEFORE `await reap_jobs()` (RESEARCH A10)
  lines 524-537 reset_for_tests — extend: stop/join watchers, cancel drain tasks, clear _WATCHERS + _WATCH_HANDLE_COUNTERS
  lines 540-561 _atexit_hook — extend fast-path guard with `and not _WATCHERS`
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Factor _read_log_cursor + add _WATCHERS registry/helpers in lifecycle.py</name>
  <read_first>
    - voss/harness/lifecycle.py (lines 35-40 `_JOBS`/`_HANDLE_COUNTERS` + "separate registry" comment; lines 59-105 `JobRecord` dataclass for the `field(default=..., repr=False, compare=False)` convention; lines 107-118 `_job_dir`/`_log_path`; lines 276-292 `_next_handle`/`_job_key`/`_find_job`; lines 454-482 `monitor_job` — the byte-cursor block to extract)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-PATTERNS.md (lifecycle.py section — exact registry/dataclass/helper/_read_log_cursor extraction shapes with line numbers)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-CONTEXT.md (D-02 shared reader, D-04 sibling registry; RESEARCH Open Question 1 — OQ-1 resolution)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-RESEARCH.md (§ Existing Code Scout — lifecycle.py table; Pattern 4 — exact _read_log_cursor signature)
  </read_first>
  <behavior>
    - Test: test_shared_cursor_reader_format — `_read_log_cursor(log, since_ms, status="watching")` returns
      a string starting `[cursor N][watching]\n` with the same truncation/`<error: ...>`/FileNotFound
      semantics as the pre-existing monitor_job (monitor_job output is the format oracle).
    - Test: monitor_job regression — existing test_lifecycle.py monitor tests stay GREEN (monitor_job is
      now a thin wrapper but byte-for-byte output-equivalent for jobs, including the `exit M` state string
      and `shell.background.reap reason=` suffix).
    - Test: test_watcher_registry_and_reap (partial — registry half) — `_next_watch_handle(sid)` returns
      `watch-001` then `watch-002`; never collides with `_next_handle(sid)` bg-NNN sequence.
    - Test: `_next_handle(sid)` still returns `bg-001` (default prefix unchanged — bg callers untouched).
  </behavior>
  <action>
    In lifecycle.py: (1) Extract the byte-cursor read block from monitor_job (lines ~458-481) into a new
    module-level `_read_log_cursor(log_path: Path, since_ms: int, *, status: str,
    cap_bytes: int = _MONITOR_CAP_BYTES, reap_reason: str | None = None) -> str` returning
    `f"[cursor {cursor}][{status}]\n{text}"` with the existing FileNotFoundError/OSError/truncation/
    reap_reason handling preserved verbatim. Rewrite monitor_job to compute its `state` string
    ("running" | f"exit {code}") then `return _read_log_cursor(Path(rec.log_path), since_ms,
    status=state, reap_reason=rec.reap_reason)`. (2) Add a `prefix: str = "bg"` keyword param to
    `_next_handle` and change its return to `f"{prefix}-{n:03d}"` (default keeps every existing caller
    byte-identical). (3) After the `_JOBS`/`_HANDLE_COUNTERS` block add a documented sibling:
    `_WATCHERS: dict[tuple[str, str], "WatcherRecord"] = {}` and
    `_WATCH_HANDLE_COUNTERS: dict[str, int] = {}` with a comment mirroring the existing "separate
    registry / distinct reap semantics" comment but explaining the Observer-is-a-thread rationale (D-04).
    (4) Add `WatcherRecord` dataclass with the exact field set from <interfaces> (using the
    `field(default=..., repr=False, compare=False)` convention from JobRecord). (5) Add
    `_next_watch_handle(session_id)` using `_WATCH_HANDLE_COUNTERS` (mirror _next_handle body),
    `_find_watcher(handle, session_id=None)` (mirror _find_job against _WATCHERS), and
    `_watch_dir(cwd, session_id)` / `_watch_log_path(cwd, session_id, handle)` (mirror _job_dir/_log_path
    with `.voss-cache/watch` via jail_path). Do NOT modify any T5 job logic beyond the monitor_job
    refactor + the _next_handle default-preserving param.
  </action>
  <verify>
    <automated>python -m pytest tests/harness/test_m14_watch.py::test_shared_cursor_reader_format tests/harness/test_lifecycle.py -q -x && python -c "from voss.harness import lifecycle as L; s='s'; assert L._next_handle(s)=='bg-001'; assert L._next_watch_handle(s)=='watch-001'; assert L._next_watch_handle(s)=='watch-002'; assert L._next_handle(s)=='bg-002'; print('handles ok')"</automated>
  </verify>
  <acceptance_criteria>
    - Test command: `python -m pytest tests/harness/test_m14_watch.py::test_shared_cursor_reader_format -x` PASSES.
    - Test command (regression): `python -m pytest tests/harness/test_lifecycle.py -q -x` stays GREEN (monitor_job wrapper is output-equivalent).
    - Behavior assertion: bg-NNN and watch-NNN counters are independent and never collide (verify command asserts the interleaved sequence).
    - Source assertion: `grep -c '_read_log_cursor' voss/harness/lifecycle.py` >= 2 (definition + monitor_job call site).
    - Source assertion: `grep -v '^#' voss/harness/lifecycle.py | grep -c '_WATCHERS\|_WATCH_HANDLE_COUNTERS'` >= 4.
  </acceptance_criteria>
  <done>_read_log_cursor is the single shared reader (monitor_job is a thin wrapper, T5 monitor tests green); _WATCHERS/_WATCH_HANDLE_COUNTERS/WatcherRecord/_next_watch_handle/_find_watcher/_watch_dir/_watch_log_path exist; bg-/watch- handle namespaces are disjoint.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Build the watch backend (Observer + debounce + asyncio bridge)</name>
  <read_first>
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-RESEARCH.md (Pattern 1 Observer/PatternMatchingEventHandler [CITED]; Pattern 2 per-path threading.Timer Debouncer; Pattern 3 loop.call_soon_threadsafe bridge; § Common Pitfalls 1/2/3/4; § Code Examples WATCH-01; § State of the Art — watchdog 5.0 kwargs mandatory)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-PATTERNS.md (watch/backend.py GREENFIELD section — the contract pattern shapes; `dataclass repr=False/compare=False` shared pattern)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-CONTEXT.md (D-01 debounce 200ms per-path threading.Timer + threading.Lock, Timer/Observer daemon=True)
    - voss/harness/watch/__init__.py (will not exist yet — create it; model: any voss/harness/mcp/__init__.py marker)
  </read_first>
  <behavior>
    - Test: test_debounce_coalesces_rapid_writes — register a watcher on `**/*.py` under tmp_path, write
      ONE matching file, poll-with-retry the log; exactly ONE JSONL event line appears within
      debounce_ms*3+300ms.
    - Test: test_non_matching_glob_no_event — register on `**/*.py`, write a `*.txt` file; after the
      window, ZERO event lines in the log.
    - Test: Debouncer collapses N rapid on_event calls for the same path within the window into ONE
      _fire callback; distinct paths fire independently.
    - Test: interpreter does not hang on exit — Observer and every threading.Timer have daemon=True.
  </behavior>
  <action>
    Create `voss/harness/watch/__init__.py` (one-line docstring marker). Create
    `voss/harness/watch/backend.py` implementing: `_GlobHandler(PatternMatchingEventHandler)` —
    `super().__init__(patterns=globs, ignore_directories=True, case_sensitive=True)` (KEYWORD args —
    watchdog 5.0+ requires kwargs) with `on_any_event(event)` delegating to
    `self._debouncer.on_event(event.src_path, event.event_type)`. `Debouncer` — `dict[str,
    threading.Timer]` + `threading.Lock`; `on_event(path, event_type)` acquires the lock, cancels any
    existing timer for that path, starts a new `threading.Timer(debounce_s, self._fire, ...)` with
    `t.daemon = True` BEFORE `t.start()`; `_fire` pops the timer under the lock then calls the callback;
    `cancel_all()` cancels+clears all timers under the lock. `_WatchBackend` — owns an `asyncio.Queue`,
    a `Debouncer` whose callback is `_on_debounced_event` which does
    `self._loop.call_soon_threadsafe(self._queue.put_nowait, record)` (NEVER call put_nowait directly
    from the timer thread — Pitfall 1); `drain_loop(log_path)` coroutine opens the log append-binary,
    `await asyncio.wait_for(queue.get(), timeout=1.0)` loop, stamps `ts_ms`, writes `json.dumps(record)
    + "\n"` (one JSONL line per coalesced event), breaks on CancelledError. `async def start_watcher(
    globs, watch_root, log_path, loop, debounce_ms=200) -> tuple[Observer, asyncio.Task, Debouncer]`:
    build backend, handler, `Observer()`, set `observer.daemon = True` BEFORE
    `observer.schedule(handler, str(watch_root), recursive=True)` then `observer.start()`, create the
    drain task, return `(observer, drain_task, backend._debouncer)`. Import `Observer` from
    `watchdog.observers` (NOT PollingObserver — Pitfall, anti-pattern).
  </action>
  <verify>
    <automated>python -m pytest tests/harness/test_m14_watch.py::test_debounce_coalesces_rapid_writes tests/harness/test_m14_watch.py::test_non_matching_glob_no_event -q -x</automated>
  </verify>
  <acceptance_criteria>
    - Test command: `python -m pytest tests/harness/test_m14_watch.py::test_debounce_coalesces_rapid_writes -x` PASSES (exactly one coalesced event).
    - Test command: `python -m pytest tests/harness/test_m14_watch.py::test_non_matching_glob_no_event -x` PASSES (zero events for non-matching glob).
    - Source assertion: `grep -c 'call_soon_threadsafe' voss/harness/watch/backend.py` >= 1 (thread→asyncio bridge present; no raw put_nowait from timer thread).
    - Source assertion: `grep -c 'daemon = True\|daemon=True' voss/harness/watch/backend.py` >= 2 (Observer + Timer both daemon — Pitfalls 2/3 mitigated).
    - Source assertion: `grep -c 'PollingObserver' voss/harness/watch/backend.py` == 0 (default event-driven Observer used).
    - Behavior assertion: `python -m pytest tests/harness/test_m14_watch.py -q -x` does not hang the interpreter after completion (daemon threads).
  </acceptance_criteria>
  <done>backend.py provides _GlobHandler/Debouncer/_WatchBackend/drain_loop/start_watcher; WATCH-01 coalesce + non-match tests pass; Observer + Timer daemonized; thread→asyncio bridge via call_soon_threadsafe.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Wire register_watcher + reap_watchers + teardown into lifecycle</name>
  <read_first>
    - voss/harness/lifecycle.py (lines 359-394 `register_job` — the register-front-door shape; lines 395-440 `reap_jobs` — the `for key, rec in list(...): ... .pop(key)` reap frame + `sys.stderr.write` error pattern; lines 485-519 `reap_all`; lines 524-537 `reset_for_tests`; lines 540-561 `_atexit_hook`)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-PATTERNS.md (lifecycle.py reap_watchers/reap_all/reset_for_tests/_atexit_hook patterns; Pattern 6 reap_watchers from RESEARCH; "sys.stderr.write error logging in reap loops" shared pattern)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-RESEARCH.md (Pattern 6 _WATCHERS teardown; § Existing Code Scout — reap_all call sites; A10 — reap_watchers before reap_jobs)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-CONTEXT.md (D-04 teardown added to existing session-exit reap path; reset_for_tests extension)
  </read_first>
  <behavior>
    - Test: test_watcher_registry_and_reap — after `await register_watcher(globs, cwd, session_id=...)`
      `_WATCHERS` has one entry whose `.observer.is_alive()` is True; after `await reap_watchers()` the
      Observer is stopped/joined, the drain task is cancelled, and `_WATCHERS` is empty.
    - Test: reap_all() invokes reap_watchers() BEFORE reap_jobs() (no stray JSONL writes after stop).
    - Test: reset_for_tests() leaves `_WATCHERS` and `_WATCH_HANDLE_COUNTERS` empty and does not hang.
    - Test: existing test_lifecycle.py reap/reset tests stay GREEN (job paths unchanged).
  </behavior>
  <action>
    In lifecycle.py add `async def register_watcher(globs: list[str], cwd: Path, *,
    session_id: str = "_nosession", debounce_ms: int = 200) -> str`: jail the watch root via
    `jail_path(cwd, ".")` (Security — never schedule on a raw user path), compute the recursive watch
    root from the glob set's common ancestor under the jailed cwd, allocate `handle =
    _next_watch_handle(session_id)`, build the log path via `_watch_log_path(cwd, session_id, handle)`,
    `from .watch.backend import start_watcher` and await it with the running loop
    (`asyncio.get_running_loop()`), store a `WatcherRecord(status="watching", ...)` in `_WATCHERS` under
    `_job_key(session_id, handle)`, return the `watch-NNN` handle. Add `async def reap_watchers() ->
    None` mirroring the reap_jobs frame (`for key, rec in list(_WATCHERS.items())`): call
    `rec.debouncer.cancel_all()`, `rec.observer.stop()`, `rec.observer.join(timeout=2.0)` each guarded
    by try/except writing `sys.stderr.write(f"lifecycle.reap_watchers: {exc!r}\n")`; cancel
    `rec.drain_task` if present; set `rec.status = "stopped"`; `_WATCHERS.pop(key, None)`. In `reap_all`
    add `await reap_watchers()` immediately BEFORE the existing `await reap_jobs()` line (RESEARCH A10).
    In `reset_for_tests` add — at the TOP, before the `_JOBS` loop — a watcher cleanup loop
    (cancel_all/stop/join(timeout=2.0)/cancel drain_task each in try/except) then after the existing
    `_HANDLE_COUNTERS.clear()` add `_WATCHERS.clear()` and `_WATCH_HANDLE_COUNTERS.clear()`. In
    `_atexit_hook` change the fast-path guard to also check `and not _WATCHERS`.
  </action>
  <verify>
    <automated>python -m pytest tests/harness/test_m14_watch.py::test_watcher_registry_and_reap tests/harness/test_lifecycle.py -q -x</automated>
  </verify>
  <acceptance_criteria>
    - Test command: `python -m pytest tests/harness/test_m14_watch.py::test_watcher_registry_and_reap -x` PASSES.
    - Test command (regression): `python -m pytest tests/harness/test_lifecycle.py -q -x` stays GREEN.
    - Source assertion: `grep -n 'await reap_watchers()' voss/harness/lifecycle.py` shows it appears in `reap_all` BEFORE the `await reap_jobs()` line (lower line number).
    - Source assertion: `grep -c '_WATCHERS.clear()\|_WATCH_HANDLE_COUNTERS.clear()' voss/harness/lifecycle.py` >= 2 (reset_for_tests extended).
    - Source assertion: `grep -c 'and not _WATCHERS' voss/harness/lifecycle.py` >= 1 (_atexit_hook guard extended).
    - Behavior assertion: jail_path is applied to the watch root — `grep -c 'jail_path' voss/harness/lifecycle.py` increased relative to baseline (watch root jailed; glob cannot escape cwd).
  </acceptance_criteria>
  <done>register_watcher/reap_watchers exist; reap_watchers runs before reap_jobs in reap_all; reset_for_tests + _atexit_hook extended; watcher registry/reap test green; T5 job tests unregressed; watch root jailed to cwd.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User-provided glob/cwd → filesystem | `register_watcher` receives globs + cwd that could reference paths outside the workspace |
| watchdog Observer thread → asyncio loop | Cross-thread data handoff; non-asyncio thread touching asyncio structures |
| Timer thread → log file | Debounced callbacks must not corrupt the JSONL the cursor reader parses |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M14-04 | Tampering | glob/cwd escaping workspace (`../../../etc`) | mitigate | `register_watcher` resolves the watch root via `jail_path(cwd, ".")`; Observer is scheduled on the jailed cwd, never a raw user-supplied path (M14-RESEARCH § Security Domain V4) |
| T-M14-05 | Tampering | concurrent JSONL writes corrupting cursor-read | mitigate | All event writes funnel through one `asyncio.Queue` + a single `drain_loop` coroutine (serialized writes); Observer/Timer threads never write the log directly (Pattern 3) |
| T-M14-06 | Denial of Service | non-daemon Timer/Observer threads hang interpreter exit | mitigate | `observer.daemon = True` before `start()`; every `threading.Timer.daemon = True` before `start()`; `reap_watchers`/`reset_for_tests` stop+join(timeout=2.0) (Pitfalls 2/3) |
| T-M14-07 | Information Disclosure | `.voss-cache/watch/<session>/*.log` readable by other users | accept | Inherits the T5 `.voss-cache/jobs` posture (not explicitly chmodded); low risk in single-user dev scenarios — accepted per M14-RESEARCH § Security Domain |
| T-M14-SC | Tampering | watchdog import surface | mitigate | watchdog pin + legitimacy checkpoint already gated in M14-01 (T-M14-SC); no new package introduced here |
</threat_model>

<verification>
- `python -m pytest tests/harness/test_m14_watch.py::test_shared_cursor_reader_format tests/harness/test_m14_watch.py::test_debounce_coalesces_rapid_writes tests/harness/test_m14_watch.py::test_non_matching_glob_no_event tests/harness/test_m14_watch.py::test_watcher_registry_and_reap -q -x` all PASS
- `python -m pytest tests/harness/test_lifecycle.py -q -x` stays GREEN (T5 unregressed)
- bg-NNN / watch-NNN handle namespaces disjoint
- `await reap_watchers()` precedes `await reap_jobs()` in reap_all
- watch root jailed via jail_path
</verification>

<success_criteria>
- _read_log_cursor is the single shared byte-cursor reader (D-02); monitor_job is a thin wrapper, T5 green
- _WATCHERS/_WATCH_HANDLE_COUNTERS/WatcherRecord sibling registry exists (D-04); bg-/watch- disjoint (OQ-1)
- backend.py debounce coalesces to exactly one event within 200ms (D-01); non-matching glob = zero events
- reap_watchers wired into reap_all (before reap_jobs), reset_for_tests, _atexit_hook
- WATCH-01 + WATCH-02-cursor-format + watcher-registry RED tests now GREEN
</success_criteria>

<output>
Create `.planning/phases/M14-long-running-tasks-watch-caps-01e/M14-02-SUMMARY.md` when done
</output>
