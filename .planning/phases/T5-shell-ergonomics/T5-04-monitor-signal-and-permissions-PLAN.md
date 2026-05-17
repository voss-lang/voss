---
phase: T5-shell-ergonomics
plan: 04
type: execute
wave: 4
depends_on: [T5-03]
files_modified:
  - voss/harness/tools.py
  - voss/harness/permissions.py
  - voss/harness/tui/permissions_bridge.py
autonomous: true
requirements: [SHELL-03, SHELL-04]
user_setup: []

must_haves:
  truths:
    - "shell_monitor(handle, since_ms=0) is non-blocking and returns [cursor N][running|exit M]\\n<chunk>"
    - "The returned cursor round-trips: passing it back as since_ms resumes exactly past it"
    - "shell_monitor truncates at 30KB with <truncated, N more bytes — re-monitor with cursor M> and a fresh cursor"
    - "shell_signal accepts ONLY INT/TERM; KILL and unknown → <denied: unsupported signal> (D-06)"
    - "edit mode denies shell_run_background and shell_signal; shell_monitor stays allowed (D-12)"
    - "the three new tools route through the same TUI approval bridge with sensible verbs/targets"
  artifacts:
    - path: "voss/harness/tools.py"
      provides: "shell_monitor + shell_signal descriptors + 3 ToolEntry registrations"
      contains: "shell_monitor"
    - path: "voss/harness/permissions.py"
      provides: "SHELL set extended + edit-mode deny for new mutating shell tools"
      contains: "shell_run_background"
  key_links:
    - from: "voss/harness/tools.py shell_signal"
      to: "voss.harness.lifecycle.signal_job"
      via: "from . import lifecycle"
      pattern: "lifecycle.signal_job"
    - from: "voss/harness/permissions.py mode_allows edit branch"
      to: "shell_run_background / shell_signal denial"
      via: "name-set membership check"
      pattern: "shell_run_background"
---

<objective>
Add the read side (`shell_monitor`, SHELL-03) and the control side (`shell_signal`, SHELL-04) of the background-job surface, register all three new tools, close the D-12 edit-mode security gap, and extend the TUI permission bridge so the new tools display correctly.

Purpose: T5-03 produced jobs + a disk log + the in-memory registry. This plan lets the agent OBSERVE that log incrementally across turns (the SC#1 capability) and STOP a job, while ensuring the new mutating shell tools cannot slip through `edit` mode (RESEARCH Security V4 / D-12 — `is_mutating=True` alone does NOT cover them; the edit-mode check is a literal-name check).
Output: `shell_monitor` + `shell_signal` in `tools.py` + 3 registrations; `permissions.py` SHELL set + edit-mode deny; `permissions_bridge.py` verb/target maps.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/T5-shell-ergonomics/T5-CONTEXT.md
@.planning/phases/T5-shell-ergonomics/T5-PATTERNS.md

<interfaces>
From T5-03 (lifecycle):
  _JOBS: dict[str, JobRecord]            # rec.log_path, rec.status, rec.exit_code, rec.proc
  signal_job(handle: str, sig: int) -> bool   # resolves handle, send_signal; False if unknown

shell_monitor(handle, since_ms=0) -> str   (D-03):
  envelope: "[cursor N][running|exit M]\n<chunk bytes, possibly empty>"
  since_ms == 0 → from start of log; since_ms is an OPAQUE BYTE OFFSET internally
  (param name preserved per ROADMAP; no wall-clock map). Returned cursor N is the
  new byte offset; caller passes it back as since_ms=N.
  done signaled by "[exit M]" replacing "[running]".
  30KB chunk cap; if more: append "<truncated, N more bytes — re-monitor with cursor M>"
  and emit a cursor at the truncation point.

shell_signal(handle, signal) -> str   (D-06):
  signal ∈ {"INT","TERM"} only. "INT"→signal.SIGINT, "TERM"→signal.SIGTERM via
  lifecycle.signal_job(handle, sig). "KILL"/anything else → "<denied: unsupported signal>".
  Unknown handle → a clear "<error: unknown handle ...>"-style string (not a crash).
</interfaces>

<existing_patterns>
30KB cap + truncation shape — voss/harness/tools.py:68-70 (fs_read_many):
```python
if len(text) > 30720:
    text = text[:30720] + f"\n<truncated, total {len(text)} bytes>"
return text
```
(T5 shell_monitor uses the D-03 wording instead:
 "<truncated, N more bytes — re-monitor with cursor M>".)

Short-lived read discipline (Pitfall 5, POSIX+Windows safe):
```python
with open(log_path, "rb") as f:
    f.seek(offset)
    chunk = f.read(30720)
```

Denied early-return idiom — voss/harness/tools.py:136 (`return f"<denied: {reason}>"`).

ToolEntry registry — voss/harness/tools.py:360-375. Insert beside
`"shell_run": ToolEntry(descriptor=shell_run, is_mutating=True),` (:367) and the
`"shell_run_background": ... is_mutating=True,` line added by T5-03.

permissions SHELL set — voss/harness/permissions.py:46 (BEFORE `SHELL = {"shell_run"}`).

permissions edit-mode deny — voss/harness/permissions.py:60-63 (BEFORE):
```python
if mode == "edit":
    if tool_name == "shell_run":
        return False, "denied by mode edit"
    return True, "ok"
```

permissions needs_prompt — permissions.py:154-162 edit branch is
`tool_name in WRITE or tool_name in SHELL` → extending the SHELL set auto-enrolls
the new tools into the prompt path (no change needed there).

permissions signature — permissions.py:164-167 special-cases shell_run
(`f"shell_run:{first_arg}"`). Mirror for shell_run_background (per-binary
granularity); shell_signal/shell_monitor fall through to bare tool-name signature.

TUI bridge — voss/harness/tui/permissions_bridge.py:27-44 `_verb_for`/`_short_target`
(pure name→display maps; bridge logic unchanged).
</existing_patterns>

<source_audit_note>
Flag 2 (D-12 deny form) — DECISION: explicit name-set
`tool_name in {"shell_run", "shell_run_background", "shell_signal"}`. Rationale:
the existing check is a literal-name check (not `is_mutating`-filtered); the
explicit set is the smallest, most legible change and is unambiguous to the
plan-checker. `shell_monitor` is deliberately NOT in the set (is_mutating=False,
pure file read — D-12 recommends keeping it allowed in edit mode; it executes
nothing). The alternative `is_mutating and tool_name in SHELL` is equivalent
(shell_monitor is_mutating=False so it stays allowed either way) but less legible
— rejected for clarity, not correctness.
</source_audit_note>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: shell_monitor + shell_signal tools + 3 ToolEntry registrations</name>
  <files>voss/harness/tools.py</files>
  <behavior>
    - shell_monitor(handle, since_ms=0) on a running job returns "[cursor N][running]\n<chunk>" where N == bytes read so far; passing N back as since_ms returns only NEW bytes (cursor round-trips) — test_monitor_cursor_progression.
    - After the job EOFs, shell_monitor returns "[cursor M][exit K]\n<tail>" with K == exit_code; the log stays readable (test_monitor_cursor_progression / test_monitor_across_turns).
    - When >30KB is available past the cursor, the chunk is capped at 30720 and ends with "<truncated, N more bytes — re-monitor with cursor M>" and the [cursor ...] prefix is the truncation offset.
    - shell_monitor is non-blocking: it never awaits process completion; an empty chunk on a still-running job is valid ("[cursor N][running]\n").
    - shell_signal(handle, "INT") and (handle, "TERM") deliver the signal and return an ack; (handle, "KILL") and (handle, "FOO") return exactly "<denied: unsupported signal>" (test_signal_surface); on POSIX a TERM'd job actually exits (test_signal_terminates, posix-skipif).
    - shell_run_background is_mutating=True; shell_monitor is_mutating=False; shell_signal is_mutating=True (registry).
  </behavior>
  <action>
    In voss/harness/tools.py:

    1. `@tool(name="shell_monitor", description="Read incremental output from a background job by handle. since_ms is an opaque byte cursor (0 = from start); pass back the returned cursor to continue. Non-blocking. Returns [cursor N][running|exit M] then the new output.")` `async def shell_monitor(handle: str, since_ms: int = 0) -> str`. Lazy `from . import lifecycle`. `rec = lifecycle._JOBS.get(handle)`; if None → `return f"<error: unknown handle {handle}>"`. Open `rec.log_path` read-only short-lived (the Pitfall-5 discipline in <existing_patterns>): `f.seek(max(0, int(since_ms)))`, `chunk = f.read(30720)`. Determine new cursor = `since_ms + len(chunk)`. Status prefix: if `rec.status == "running"` → `[running]` else `[exit {rec.exit_code}]`. If the file had more bytes past the 30KB read (stat size > new cursor), append `\n<truncated, {remaining} more bytes — re-monitor with cursor {new_cursor}>`. Return `f"[cursor {new_cursor}][{status_token}]\n" + chunk.decode("utf-8", errors="replace")`. Tolerate a missing log file (job registered but no output yet) by treating it as an empty chunk at cursor 0. Pure file read — NO process interaction, NO await on proc.

    2. `@tool(name="shell_signal", description="Send INT or TERM to a background job by handle. Only 'INT' and 'TERM' are accepted (KILL is internal-only).")` `async def shell_signal(handle: str, signal: str) -> str`. New module import `import signal as _signal` (alias to avoid shadowing the param; or accept the param name and reference the stdlib via the alias). Validate: if `signal not in {"INT", "TERM"}` → `return "<denied: unsupported signal>"` (covers KILL and everything else — D-06). Map `{"INT": _signal.SIGINT, "TERM": _signal.SIGTERM}`. Lazy `from . import lifecycle`; `ok = lifecycle.signal_job(handle, sig)`; if not ok → `return f"<error: unknown handle {handle}>"`; else return a short ack like `f"[signal {signal} -> {handle}]"`.

    3. Register all three beside tools.py:367 (shell_run / shell_run_background):
       `"shell_monitor": ToolEntry(descriptor=shell_monitor, is_mutating=False),`  # read-only file read
       `"shell_signal":  ToolEntry(descriptor=shell_signal, is_mutating=True),`
       (shell_run_background was already added by T5-03.) Do NOT add any of these to recorder.VALIDATE_TOOLS (RESEARCH Open-Q3 / D-08 — `[cursor N]` envelope is incompatible with `_parse_exit`'s literal `[exit ` prefix; background jobs are not validation runs; forensic trail is the disk log + `shell.background.reap`).
  </action>
  <verify>
    <automated>python -m pytest "tests/harness/test_t5_shell.py::test_monitor_cursor_progression" "tests/harness/test_t5_shell.py::test_monitor_across_turns" "tests/harness/test_t5_shell.py::test_signal_surface" "tests/harness/test_t5_shell.py::test_signal_terminates" -x -q</automated>
    <requirement>SHELL-03, SHELL-04</requirement>
    <expected>Monitor envelope is "[cursor N][running|exit M]\n<chunk>", cursor round-trips, job observable from a second call; INT/TERM accepted, KILL/unknown → "<denied: unsupported signal>", POSIX TERM exits the job.</expected>
  </verify>
  <done>shell_monitor (non-blocking, cursor round-trip, 30KB D-03 truncation) and shell_signal (INT/TERM only) exist; 3 ToolEntry rows registered with correct is_mutating; recorder.VALIDATE_TOOLS untouched; the four SHELL-03/04 tests green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: D-12 edit-mode security gap + SHELL set + signature + TUI bridge verbs</name>
  <files>voss/harness/permissions.py, voss/harness/tui/permissions_bridge.py</files>
  <behavior>
    - mode_allows("edit", "shell_run_background", True) → (False, "denied by mode edit")
    - mode_allows("edit", "shell_signal", True) → (False, "denied by mode edit")
    - mode_allows("edit", "shell_monitor", False) → (True, "ok")  (read-only, stays allowed — D-12)
    - mode_allows("edit", "shell_run", True) → still (False, ...) (unchanged)
    - mode_allows("plan", "shell_monitor", False) → (True, "ok")  (is_mutating=False → READ tier)
    - SHELL set contains all four shell tools (auto-enrolls them into the edit-mode prompt path at permissions.py:154-162).
    - permissions_bridge._verb_for: shell_run_background→"run", shell_signal→"signal", shell_monitor→"use"; shell_run unchanged.
  </behavior>
  <action>
    In voss/harness/permissions.py:

    1. Line 46: `SHELL = {"shell_run"}` → `SHELL = {"shell_run", "shell_run_background", "shell_monitor", "shell_signal"}` (D-12 / RESEARCH Security V4 — also auto-enrolls the new tools into the `tool_name in SHELL` prompt branch at permissions.py:154-162, no change needed there).

    2. Lines 60-63, the `if mode == "edit":` branch — change `if tool_name == "shell_run":` to the explicit name-set per <source_audit_note> Flag 2 decision:
       `if tool_name in {"shell_run", "shell_run_background", "shell_signal"}:`
       Keep `return False, "denied by mode edit"` and the trailing `return True, "ok"` (so `shell_monitor`, is_mutating=False, stays ALLOWED in edit mode — it executes nothing, D-12). Add a one-line comment: `# D-12: shell_monitor omitted deliberately — read-only, executes nothing`. The `plan` branch is unchanged (it already denies all `is_mutating=True`, and shell_monitor is_mutating=False so plan-mode allows it correctly).

    3. signature (permissions.py:164-167): it special-cases `shell_run` as `f"shell_run:{first_arg}"`. Mirror for `shell_run_background` (per-binary always-allow granularity parity with shell_run — keyed on cmd's first token). `shell_signal`/`shell_monitor` fall through to the existing bare tool-name signature (no special case). Keep the existing `shell_run` branch byte-identical; add the `shell_run_background` case beside it.

    In voss/harness/tui/permissions_bridge.py (additive, keep existing entries):

    4. `_verb_for` (lines 27-32): `if tool_name == "shell_run":` → `if tool_name in {"shell_run", "shell_run_background"}: return "run"`; add `if tool_name == "shell_signal": return "signal"`. Keep the `fs_write/fs_edit → "modify"` and the `return "use"` fallback (shell_monitor → "use", and it won't prompt anyway — read-only).

    5. `_short_target` (lines 35-44): add `shell_run_background` to the `cmd`-extracting branch (`raw = str(args.get("cmd", ""))`); add a `shell_signal` branch extracting the `handle` arg (`raw = str(args.get("handle", ""))`). `shell_monitor` falls through to the generic kwargs join (cosmetic — never prompts).
  </action>
  <verify>
    <automated>python -m pytest "tests/harness/test_t5_shell.py::test_edit_mode_denies_background_and_signal" -x -q && python -c "from voss.harness.permissions import mode_allows, SHELL; assert mode_allows('edit','shell_run_background',True)[0] is False; assert mode_allows('edit','shell_signal',True)[0] is False; assert mode_allows('edit','shell_monitor',False)[0] is True; assert mode_allows('edit','shell_run',True)[0] is False; assert {'shell_run','shell_run_background','shell_monitor','shell_signal'} <= SHELL; print('d12-ok')"