---
phase: M14-long-running-tasks-watch-caps-01e
plan: 03
type: execute
wave: 3
depends_on: ["M14-02"]
files_modified:
  - voss/harness/tools.py
autonomous: true
requirements: [WATCH-02]
user_setup: []

must_haves:
  truths:
    - "An agent turn calls fs_watch(globs) and gets a watch-NNN handle back"
    - "A later turn calls fs_watch_poll(handle, since_ms) and reads the change event via the shared cursor without re-registering"
    - "fs_watch and fs_watch_poll are both classified is_mutating=False (parity with shell_monitor)"
    - "fs_watch_poll returns the same [cursor N][watching|stopped] envelope shell_monitor returns"
  artifacts:
    - path: "voss/harness/tools.py"
      provides: "fs_watch + fs_watch_poll tools in make_toolset; result-dict ToolEntry registration"
      contains: "fs_watch_poll"
  key_links:
    - from: "voss/harness/tools.py:fs_watch"
      to: "voss.harness.lifecycle.register_watcher"
      via: "fs_watch awaits lifecycle.register_watcher"
      pattern: "lifecycle\\.register_watcher"
    - from: "voss/harness/tools.py:fs_watch_poll"
      to: "voss.harness.lifecycle._read_log_cursor"
      via: "fs_watch_poll calls the shared cursor reader via _find_watcher"
      pattern: "_read_log_cursor|_find_watcher"
    - from: "voss/harness/tools.py:result"
      to: "ToolEntry registration"
      via: "fs_watch/fs_watch_poll added to make_toolset result dict"
      pattern: "fs_watch.*ToolEntry"
---

<objective>
Add the `fs_watch` and `fs_watch_poll` agent tools to `make_toolset` (WATCH-02): `fs_watch(globs,
debounce_ms=200)` registers a watcher via the M14-02 `lifecycle.register_watcher` and returns a
`watch-NNN` handle; `fs_watch_poll(handle, since_ms=0)` reads incremental JSONL change events via the
SHARED `_read_log_cursor` (D-02 — no duplicated cursor mechanic), structurally identical to
`shell_monitor`. Both registered `is_mutating=False` (OQ-2 LOCKED).

Purpose: Surfaces the M14-02 watch backend to the agent so a watcher registered in one turn is
readable via cursor in a later turn without re-registration (WATCH-02 acceptance).
Output: extended `voss/harness/tools.py`.
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
<!-- LOCKED: OQ-2 — fs_watch is_mutating=False AND fs_watch_poll is_mutating=False.
     Rationale (PermissionGate): is_mutating drives plan-mode-tier denial. fs_watch writes no
     workspace files (it spawns an Observer thread + appends to .voss-cache JSONL — the same
     non-workspace side-effect class as code_refresh and shell_monitor, both is_mutating=False).
     Marking it True would wrongly deny it in plan mode. LOCKED. -->

Consumed from M14-02 (voss/harness/lifecycle.py — these now exist):
  async def register_watcher(globs, cwd, *, session_id="_nosession", debounce_ms=200) -> str  # "watch-NNN"
  def _find_watcher(handle, session_id=None) -> WatcherRecord | None
  def _read_log_cursor(log_path, since_ms, *, status, ...) -> str
  WatcherRecord.status is "watching" | "stopped"; WatcherRecord.log_path is str

From voss/harness/tools.py (verified seams):
  lines 1-17     import block (jail_path, shell_allowed, split_command, SandboxError from .sandbox)
  lines 171-203  shell_run_background — allowlist-gate + lifecycle.register_job pattern
  lines 205-221  shell_monitor — `from . import lifecycle; return lifecycle.monitor_job(handle, since_ms=, session_id=session_id or "_nosession")` (EXACT model for fs_watch_poll)
  lines 223-243  shell_signal — `<error: unknown handle {handle}>` guard pattern
  lines 511-539  result dict — ToolEntry(descriptor=, is_mutating=); shell_monitor is is_mutating=False (line 518)
  make_toolset closure captures `cwd` and `session_id`; tools use `session_id or "_nosession"`
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add fs_watch + fs_watch_poll tools to make_toolset</name>
  <read_first>
    - voss/harness/tools.py (lines 1-17 imports; lines 171-203 shell_run_background; lines 205-221 shell_monitor — exact thin-wrapper shape; lines 223-243 shell_signal unknown-handle guard; lines 511-539 result dict ToolEntry registration, shell_monitor is_mutating=False at line 518)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-PATTERNS.md (tools.py section — shell_run_background/shell_monitor/shell_signal analogs; "Session ID default" + "Error return format" shared patterns)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-RESEARCH.md (§ Code Examples WATCH-02 fs_watch_poll; § Existing Code Scout tools.py table; Open Question 2 — OQ-2 resolution + PermissionGate rationale)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-CONTEXT.md (D-02 fs_watch_poll reuses the SAME byte-cursor reader; fs_watch returns watch-NNN; non-mutating parity with shell_monitor)
  </read_first>
  <behavior>
    - Test: test_fs_watch_tool_cursor_read — build a toolset, call fs_watch(["**/*.py"]) returns a
      "watch-NNN" string handle; write a matching file; a SEPARATE fs_watch_poll(handle, 0) returns a
      "[cursor N][watching]" envelope containing the changed file's JSONL event; calling fs_watch_poll
      again with the returned cursor reads only NEW events (no re-registration).
    - Test: fs_watch_poll on an unknown handle returns "<error: unknown handle ...>".
    - Test: the cursor envelope shape equals what shell_monitor produces (shared _read_log_cursor).
    - Test: make_toolset()['fs_watch'].is_mutating is False and ['fs_watch_poll'].is_mutating is False.
  </behavior>
  <action>
    In voss/harness/tools.py inside make_toolset (alongside shell_run_background / shell_monitor): add a
    @tool(name="fs_watch", description=...) async fs_watch(globs: list[str], debounce_ms: int = 200)
    -> str that does `from . import lifecycle` then `return await lifecycle.register_watcher(globs,
    cwd, session_id=session_id or "_nosession", debounce_ms=debounce_ms)` — mirror
    shell_run_background's deferred-import + return shape; no shell_allowed gate here (fs_watch takes
    globs, not a command — the allowlist gate belongs to the CLI command path in M14-04, not the tool).
    Add a @tool(name="fs_watch_poll", description="Read incremental file-watch events by handle.
    since_ms is an opaque byte cursor (0 = from start); pass back the returned cursor to continue.
    Non-blocking. Returns [cursor N][watching|stopped] then JSONL event lines.") async
    fs_watch_poll(handle: str, since_ms: int = 0) -> str that does `from . import lifecycle`, looks up
    `rec = lifecycle._find_watcher(handle, session_id=session_id or "_nosession")`, returns
    `f"<error: unknown handle {handle}>"` if rec is None, else returns
    `lifecycle._read_log_cursor(Path(rec.log_path), since_ms, status=rec.status)` — the SAME shared
    reader monitor_job uses (D-02, do not duplicate the cursor logic). In the result dict (lines
    ~511-539) immediately after the "shell_signal" entry add the fs_watch ToolEntry and the
    fs_watch_poll ToolEntry, BOTH with is_mutating=False (OQ-2 LOCKED — parity with the
    shell_monitor is_mutating=False entry at line 518). Do not modify any existing tool or entry.
  </action>
  <verify>
    <automated>python -m pytest tests/harness/test_m14_watch.py::test_fs_watch_tool_cursor_read tests/harness/test_m14_watch.py::test_shared_cursor_reader_format -q -x</automated>
  </verify>
  <acceptance_criteria>
    - Test command: `python -m pytest tests/harness/test_m14_watch.py::test_fs_watch_tool_cursor_read -x` PASSES (register in one call, cursor-read in a later call, no re-registration).
    - Test command (shared-reader): `python -m pytest tests/harness/test_m14_watch.py::test_shared_cursor_reader_format -x` stays GREEN (envelope identical to shell_monitor).
    - Behavior assertion: `python -c "from pathlib import Path; from voss.harness.tools import make_toolset; ts=make_toolset(Path('.'), session_id='s'); print(ts['fs_watch'].is_mutating, ts['fs_watch_poll'].is_mutating)"` prints `False False` (OQ-2).
    - Source assertion: `grep -c 'lifecycle.register_watcher\|lifecycle._read_log_cursor\|lifecycle._find_watcher' voss/harness/tools.py` >= 3 (no duplicated cursor logic — delegates to shared lifecycle primitives).
    - Source assertion: `grep -c 'fs_watch\b' voss/harness/tools.py` >= 3 (tool def + poll def + result entries).
    - Regression: `python -m pytest tests/harness/test_tools.py -q -x` stays GREEN (existing tool classification unchanged).
  </acceptance_criteria>
  <done>fs_watch + fs_watch_poll exist in make_toolset, both is_mutating=False; fs_watch_poll delegates to the shared _read_log_cursor (no duplication); WATCH-02 cursor-read test green; existing tool tests unregressed.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Agent (LLM) → fs_watch tool | The agent supplies arbitrary glob strings to fs_watch |
| Tool → lifecycle registry | fs_watch_poll resolves a caller-supplied handle against _WATCHERS |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M14-08 | Tampering | agent-supplied glob escaping cwd | mitigate | fs_watch passes globs straight to `lifecycle.register_watcher`, which jails the watch root via `jail_path(cwd, ".")` (mitigated upstream in M14-02 T-M14-04); the tool adds no path resolution of its own |
| T-M14-09 | Information Disclosure | fs_watch_poll reading another session's watcher | mitigate | `_find_watcher(handle, session_id=session_id or "_nosession")` scopes the lookup to the make_toolset session; cross-session handle access returns `<error: unknown handle>` |
| T-M14-10 | Elevation of Privilege | fs_watch wrongly denied/allowed by permission tier | mitigate | OQ-2 LOCKED is_mutating=False — matches shell_monitor/code_refresh non-workspace-mutation precedent; documented PermissionGate rationale prevents mis-tiering |
| T-M14-SC | Tampering | watchdog import surface | mitigate | watchdog pin + legitimacy checkpoint already gated in M14-01 (T-M14-SC); no new package here |
</threat_model>

<verification>
- `python -m pytest tests/harness/test_m14_watch.py::test_fs_watch_tool_cursor_read tests/harness/test_m14_watch.py::test_shared_cursor_reader_format -q -x` PASS
- `make_toolset(...)['fs_watch'].is_mutating is False` and `['fs_watch_poll'].is_mutating is False`
- fs_watch_poll delegates to shared `lifecycle._read_log_cursor` (no duplicated cursor logic)
- `python -m pytest tests/harness/test_tools.py -q -x` stays GREEN
</verification>

<success_criteria>
- fs_watch registers a watcher and returns a watch-NNN handle (WATCH-02)
- fs_watch_poll reads incremental JSONL events via the shared cursor in a later turn without re-registration (WATCH-02)
- Both tools is_mutating=False (OQ-2 LOCKED, parity with shell_monitor)
- No cursor-reader duplication (D-02): delegates to lifecycle._read_log_cursor
- Existing tool classification tests unregressed
</success_criteria>

<output>
Create `.planning/phases/M14-long-running-tasks-watch-caps-01e/M14-03-SUMMARY.md` when done
</output>
