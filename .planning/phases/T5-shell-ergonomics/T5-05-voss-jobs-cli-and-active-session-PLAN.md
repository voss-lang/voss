---
phase: T5-shell-ergonomics
plan: 05
type: execute
wave: 5
depends_on: [T5-03, T5-04]
files_modified:
  - voss/harness/cli.py
autonomous: true
requirements: [SHELL-05]
user_setup: []

must_haves:
  truths:
    - "A job spawned via the real make_toolset->shell_run_background path lands under <record.id>/, not _nosession/ — the cross-process contract holds end-to-end"
    - "voss jobs (a SEPARATE OS process) lists the current session's jobs by reading *.meta.json sidecars — never in-memory _JOBS"
    - "Default render is an aligned HANDLE PID STATUS RUNTIME CMD table; --json emits one JobRecord dict per line"
    - "voss chat writes .voss-cache/jobs/.active-session on REPL start and removes it on ALL non-crash exits via try/finally (A4)"
    - "voss jobs reads .active-session, falling back to newest-mtime jobs dir if absent"
    - "--keep-logs at voss chat entry skips the session jobs-dir cleanup on exit; default false reaps it"
    - "voss jobs cross-checks psutil.pid_exists so it never claims false liveness after a crash"
    - "jail_path is imported in cli.py (no NameError)"
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "make_toolset session_id wiring (1314+1071) + jail_path import + jobs_cmd + AGENT_COMMANDS + --keep-logs + .active-session try/finally lifecycle + reap_jobs on exit"
      contains: "def jobs_cmd"
  key_links:
    - from: "voss/harness/cli.py _run_repl / do_cmd make_toolset call"
      to: "shell_run_background -> register_job(session_id=record.id)"
      via: "session_id=record.id / session_id=do_record.id kwarg"
      pattern: "session_id=record\\.id"
    - from: "voss/harness/cli.py"
      to: "voss.harness.sandbox.jail_path"
      via: "from .sandbox import jail_path"
      pattern: "from \\.sandbox import jail_path"
    - from: "voss/harness/cli.py jobs_cmd"
      to: ".voss-cache/jobs/<active_session>/*.meta.json"
      via: "tolerant glob + json.loads (swallow OSError/JSONDecodeError)"
      pattern: "\\.meta\\.json"
    - from: "voss/harness/cli.py _run_repl"
      to: ".voss-cache/jobs/.active-session"
      via: "write on start, remove in try/finally (all non-crash exits)"
      pattern: "\\.active-session"
    - from: "voss/harness/cli.py REPL finally"
      to: "voss.harness.lifecycle.reap_jobs"
      via: "explicit call in finally honoring --keep-logs"
      pattern: "reap_jobs"
---

<objective>
Ship `voss jobs` (SHELL-05): a click subcommand that, from a SEPARATE OS process, lists the current `voss chat` session's background jobs by reading the on-disk `<handle>.meta.json` sidecars (in-memory `_JOBS` is invisible to it — the headline cross-process constraint). Wire the `.active-session` pointer write/remove and the `--keep-logs` flag into `voss chat`, and fire `reap_jobs()` on clean REPL exit so the session jobs-dir is cleaned deterministically.

Purpose: Without this the agent (and the human) cannot see what background work is in flight. The cross-process design (D-11, A4) is the load-bearing risk RESEARCH flagged: `voss jobs` is a fresh click invocation, not the running chat — it MUST read disk, never the heap. This plan ALSO closes the cross-process contract end-to-end: Task 1 wires the real `record.id` into `make_toolset` at the production call sites (cli.py:1314 `voss chat` + cli.py:1071 `voss do`) so `shell_run_background` sidecars land under `<record.id>/` (NOT `_nosession/`) — without it `voss jobs` would always be empty in real use even though every unit test passes (the exact false-green the gate caught).
Output: make_toolset `session_id` production wiring + `jail_path` import + `jobs_cmd` + `AGENT_COMMANDS` entry + `--keep-logs` + `.active-session` try/finally lifecycle + explicit `reap_jobs()` on exit, all in `voss/harness/cli.py` (3 tasks).
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
  reap_jobs() -> None      # async; SIGTERM@0 -> SIGKILL@5s, emits shell.background.reap
  JobRecord sidecar schema (D-11, written by T5-03 atomically on every transition):
    {handle, pid, started_at, cmd, log_path, status, exit_code, runtime_ms}
  Sidecar path: .voss-cache/jobs/<session_id>/<handle>.meta.json

D-09: <session_id> == SessionRecord.id == record.id (uuid.uuid4().hex[:12]).
  Confirmed in-use at cli.py:1358 (MemoryStore(...).bind(session_id=record.id))
  and cli.py:1445 (session_id=record.id passed to run_turn).

M14 contract (do NOT break): `voss jobs --json` shape IS M14's data contract.
  Keep it the JobRecord dict verbatim (D-11 / CONTEXT discretion) — no field
  renames, no extra keys beyond the 8 D-11 fields.
</interfaces>

<existing_patterns>
sessions_cmd (closest session-scoped list+render verb) — voss/harness/cli.py:1592-1611:
```python
@click.command("sessions")
@click.option("--all", "--global", "include_legacy", is_flag=True, help="...")
def sessions_cmd(include_legacy: bool) -> None:
    """List saved agent sessions ..."""
    cwd = Path.cwd()
    records = session_store.list_sessions(cwd=cwd, include_legacy=include_legacy)
    if not records:
        click.echo("(no sessions)")
        return
    for r in records:
        click.echo(f"  {r.id[:8]}  {r.updated_at}  {r.model:<28}  {r.first_task()}")
```

Aligned-column idiom — voss/harness/cli.py:1537-1540 (doctor_cmd):
```python
name_width = max(len(c.name) for c in results) + 2
for c in results:
    click.echo(f"  {click.style(g, fg=color)}  {c.name:<{name_width}} {c.detail}")
```

Tolerant directory-of-JSON read — voss/harness/session.py:217-223:
```python
for p in dir_path.glob("*.json"):
    try:
        data = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        continue
```
(PermissionError ⊂ OSError so it is already swallowed; on Windows add a single
retry on PermissionError per RESEARCH Pitfall 5 — one extra read attempt only.)

AGENT_COMMANDS tuple — voss/harness/cli.py:1989-2009 (ends `eval_cmd,`).
register(group) at cli.py:2012-2015 iterates the tuple — no other wiring.

chat_cmd option stack + signature — voss/harness/cli.py:1148-1219. The flag goes
beside the existing options (e.g. after the `--auth` option at :1178-1184),
threaded through `chat_cmd(...)` params into the `_run_repl(...)` call at
cli.py:1209-1218 (which currently passes cwd/json_mode/plain/mode/history/
record/provider/auth_detail).

_run_repl signature + REPL clean-exit — voss/harness/cli.py:1299-1311 (params),
cli.py:1343-1360 (ctx built; record.id available — confirms D-09), and the
clean-exit block cli.py:1391-1405:
```python
while True:
    try:
        line = input("▌ ")
    except (EOFError, KeyboardInterrupt):
        click.echo()
        try:
            conventions.run_on_clean_exit(ctx, history=ctx.history,
                                          record=record, memory_store=ctx.memory_store)
        except Exception as exc:  # noqa: BLE001
            click.echo(f"conventions extraction skipped: {exc}", err=True)
        return
```
(No existing reap_all caller outside lifecycle.py — REPL has no explicit reap;
this plan adds the explicit reap_jobs() call here so cleanup is ordered.)

Sandbox jailing for the .voss-cache path — voss/harness/sandbox.py:95-101
(jail_path + mkdir parents; reuse rather than hand-rolling the path).
</existing_patterns>

<source_audit_note>
make_toolset session_id policy (BLOCKER 1 resolution) — DECISION pinned in
Task 1: the additive keyword-only `session_id` kwarg lands in T5-03 (tools.py);
the PRODUCTION wiring is owned + verified HERE (T5-05 Task 1), not deferred as an
unplanned one-liner. Of the 6 make_toolset call sites: cli.py:1314 (`voss chat`
_run_repl) and cli.py:1071 (`voss do`) pass the real `record.id`/`do_record.id`;
cli.py:1686 (tools_cmd), cli.py:1710 (_extension_context), subagents.py:91, and
eval/runner.py:127/149/185 DELIBERATELY accept the `_nosession` fallback
(documented, the two cli.py ones with inline comments; subagents/eval are
document-only and out of this plan's files_modified). A toolset-path test asserts
a job spawned via make_toolset->shell_run_background lands under `<session_id>/`.

Flag 3 (.active-session pointer, A4) — DECISION: pointer file
`.voss-cache/jobs/.active-session` containing `record.id`, written by `_run_repl`
on REPL start (right after `ctx`/`record` are bound, cli.py:1343-1360) and
removed in a `try/finally` wrapping the REPL loop (WARNING 2 resolution — the
finally runs on EOF, /exit, normal return, AND exception-bubble exits, not only
the `except (EOFError, KeyboardInterrupt):` branch). `voss jobs` reads the
pointer; if absent or unreadable, fall back to the newest-mtime
`.voss-cache/jobs/<dir>/`. Rationale: explicit + race-free; CONTEXT defers
cross-session inventory so single-active-session is the contract (RESEARCH
Open-Q1 recommendation (a)). The pointer is a NEW small contract not in CONTEXT
(CONTEXT only locked the dir layout) — pinned here.

Flag 4 reaffirmed: the explicit `reap_jobs()` call lives in the `finally:` so the
session jobs-dir cleanup is deterministic and ordered BEFORE process exit on all
non-crash paths (the atexit piggyback from T5-03 is the crash-safety net, not the
primary path). `--keep-logs=False` -> remove `.voss-cache/jobs/<session_id>/`
after reap; `True` -> skip the rm. RESIDUAL (WARNING 2, acknowledged): a hard
SIGKILL of the chat process leaves a stale pointer + sidecars — covered by
`voss jobs` newest-mtime fallback + atexit reap net; post-crash sweep is out of
T5 scope (M14 territory, RESEARCH Runtime State Inventory).
</source_audit_note>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Production session_id wiring for make_toolset (closes the cross-process contract)</name>
  <files>voss/harness/cli.py</files>
  <behavior>
    - A background job spawned through the REAL toolset path (make_toolset -> shell_run_background -> register_job) during a `voss chat`/`_run_repl` session writes its sidecar under `.voss-cache/jobs/<record.id>/`, NOT `.voss-cache/jobs/_nosession/`.
    - `voss jobs` (which reads `.active-session` == `record.id`) therefore finds that job — the cross-process contract holds end-to-end (this is the false-green the gate caught: prior tests called register_job(session_id=...) directly and never exercised make_toolset->shell_run_background with the real record.id).
    - `voss do` (cli.py:1071, has `do_record`) likewise spawns under `<do_record.id>/`.
    - The other 4 make_toolset call sites deliberately accept the `_nosession` fallback (documented policy, asserted by a source-inspection check that those sites do NOT pass session_id).
  </behavior>
  <action>
    T5-03 Task 3 added the additive keyword-only `session_id: str | None = None` parameter to `make_toolset` (tools.py) + closure capture + `_nosession` fallback. THIS task wires the real session id at the production call sites in voss/harness/cli.py. There are exactly 6 `make_toolset` call sites (grep-verified: cli.py:1071, cli.py:1314, cli.py:1686, cli.py:1710; subagents.py:91; eval/runner.py:127/149/185). Per-site policy DECISION (pin this, do not leave implicit):

    1. cli.py:1314 (`_run_repl`, the `voss chat` interactive REPL) — `record` is already in `_run_repl`'s signature/scope (cli.py:1305; `record.id` used at cli.py:1358). Change `tools = make_toolset(cwd, renderer=renderer, net=_get_net_session())` to `tools = make_toolset(cwd, renderer=renderer, net=_get_net_session(), session_id=record.id)`. THIS is the headline fix — it makes shell_run_background sidecars land under `<record.id>/` so `voss jobs` (reading `.active-session=record.id`) finds them.

    2. cli.py:1071 (`do_cmd`, `voss do` single-shot) — `do_record` is in scope (`do_record.id` used at cli.py:1099/1116). Change to `make_toolset(cwd, renderer=renderer, net=_get_net_session(), session_id=do_record.id)` for consistency (a bg job in `voss do` is rare and reaped at process exit anyway, but a correct session dir keeps `voss jobs` honest if it is used).

    3. cli.py:1686 (`tools_cmd`) — DELIBERATELY NOT wired: it only lists tool metadata and never invokes a tool; no session exists. Accept the `_nosession` fallback. Add an inline `# T5: no session_id — tools_cmd never invokes tools (deliberate _nosession)` comment.

    4. cli.py:1710 (`_extension_context`) — DELIBERATELY NOT wired: extension/skill listing context, not a live agent loop. Accept `_nosession`. Add an inline `# T5: deliberate _nosession — not a live session loop` comment.

    5. subagents.py:91 — DELIBERATELY NOT wired (and OUT OF THIS PLAN'S files_modified — do NOT edit subagents.py). Subagent background jobs are an edge case out of T5 scope; the parent session owns job inventory. Document this decision here in the plan only (no code change). Add the rationale to the SUMMARY.

    6. eval/runner.py:127/149/185 — DELIBERATELY NOT wired (and OUT OF THIS PLAN'S files_modified — do NOT edit eval/runner.py). Hermetic eval runs in isolated temp repos and never inspects `voss jobs`. Document-only.

    So this task edits ONLY cli.py:1314 and cli.py:1071. Do NOT add `session_id=` to the other cli.py sites (1686, 1710); leave them on the fallback with the explanatory comments.

    Add the test in tests/harness/test_t5_shell.py — `test_toolset_path_uses_real_session_id`: build `make_toolset(tmp_path, session_id="sess-abc")`, invoke the `shell_run_background` descriptor with a trivial allowlisted command (e.g. `echo hi` via the deterministic emitter or a short `python3 -c`), then assert a sidecar appeared under `tmp_path/.voss-cache/jobs/sess-abc/` and NOT under `.../jobs/_nosession/`. This exercises make_toolset->shell_run_background->register_job with a real session id (the path the unit-level tests bypassed). Also add a source-inspection guard asserting cli.py `_run_repl` source contains `session_id=record.id` and `do_cmd` source contains `session_id=do_record.id`.
  </action>
  <verify>
    <automated>python -m pytest "tests/harness/test_t5_shell.py::test_toolset_path_uses_real_session_id" -x -q && python -c "import inspect; from voss.harness import cli; r=inspect.getsource(cli._run_repl); d=inspect.getsource(cli.do_cmd); assert 'session_id=record.id' in r, 'chat REPL not wired'; assert 'session_id=do_record.id' in d, 'do_cmd not wired'; print('toolset-session-wired')"</automated>
    <requirement>SHELL-02, SHELL-05 (D-09/D-11 cross-process contract)</requirement>
    <expected>A job spawned via make_toolset->shell_run_background with a real session id lands under `<session_id>/` (never `_nosession/`); cli.py:1314 passes `session_id=record.id` and cli.py:1071 passes `session_id=do_record.id`; the other cli.py call sites deliberately omit it.</expected>
  </verify>
  <done>cli.py:1314 + cli.py:1071 pass the real session id into make_toolset; the toolset-path test proves sidecars land under `<record.id>/`; the 4 deliberate-`_nosession` sites are documented (2 with inline comments, 2 document-only out-of-files); the headline cross-process contract is verified end-to-end, not just at the direct register_job level.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: jobs_cmd (table + --json, cross-process sidecar read) + jail_path import + AGENT_COMMANDS</name>
  <files>voss/harness/cli.py</files>
  <behavior>
    - With a pre-seeded `tmp_path/.voss-cache/jobs/<sid>/bg-001.meta.json` and a `.active-session` pointer containing `<sid>`, `CliRunner().invoke(jobs_cmd, ["--cwd", str(tmp_path)])` prints an aligned table with header `HANDLE  PID  STATUS  RUNTIME  CMD` and one data row for bg-001 (test_voss_jobs_reads_sidecar) — proving the read works from a separate invocation with NO live session.
    - `jobs_cmd --json` emits exactly one JSON object per line; each parses to the 8 D-11 keys verbatim (M14 contract).
    - No sidecars / no active session / missing dir -> a friendly "(no background jobs)" line, exit 0 (mirrors sessions_cmd "(no sessions)").
    - A corrupt/partially-written `.meta.json` is skipped silently (tolerant read), not a crash.
    - STATUS reflects pid liveness: if the sidecar says "running" but `psutil.pid_exists(pid)` is False, render the last-known status without claiming live (e.g. "running?" or "stale") — never falsely assert liveness (RESEARCH Runtime State Inventory / A6).
  </behavior>
  <action>
    In voss/harness/cli.py:

    0. IMPORT (BLOCKER fix — cli.py has NO sandbox import; grep-verified): add `from .sandbox import jail_path` to the cli.py import block if not already present. Both this task and Task 3 use `jail_path`; without the import every `jail_path(...)` call raises NameError at runtime. Add it once, at the top with the other `from .` imports (match existing import ordering/style).

    1. Add a `jobs_cmd` click command (mirror the sessions_cmd shape at cli.py:1592-1611):
      `@click.command("jobs")`
      `@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))`
      `@click.option("--json", "json_mode", is_flag=True, help="One JSON record per line.")`
      `def jobs_cmd(cwd_str: str, json_mode: bool) -> None:` docstring "List background jobs for the current session."

    Resolve the active session (Flag 3): `cache = jail_path(Path(cwd_str).resolve(), ".voss-cache") / "jobs"`. Read `cache/".active-session"`; if it exists and is non-empty use its stripped content as `sid`; else pick the newest-mtime subdir of `cache` (skip the `.active-session` file itself and any non-dir); if none -> echo "(no background jobs)" and return.

    Glob `cache/<sid>/*.meta.json` with the tolerant idiom COPIED from session.py:217-223 (swallow `(OSError, json.JSONDecodeError)`; on Windows retry-once on PermissionError — PermissionError is a subclass of OSError so the swallow already covers it, the retry is the only addition). Collect the parsed dicts. Keep only the 8 D-11 keys when emitting `--json` (defensive — tolerate forward-compat extra keys on read, emit verbatim).

    Liveness cross-check (A6): `import psutil`; for each record, if `status == "running"` and not `psutil.pid_exists(int(rec["pid"]))`, mark the displayed status as stale (do NOT mutate the sidecar — display only). Guard psutil errors.

    Render:
      - `--json`: `click.echo(json.dumps(rec))` one per line (JobRecord dict verbatim — M14 contract; do NOT add/rename fields).
      - default: aligned table. Header `HANDLE  PID  STATUS  RUNTIME  CMD`. Use the doctor_cmd `max(len(...))`/`f"{x:<{w}}"` alignment idiom (cli.py:1537-1540). RUNTIME = `runtime_ms` rendered human (e.g. `12.3s`). CMD column: ellipsis-truncate at `shutil.get_terminal_size((80, 24)).columns - 50` (degrade to 80 when not a TTY), no wrap (CONTEXT discretion).
      - empty -> `click.echo("(no background jobs)")`.

    Register: append `jobs_cmd,` to the `AGENT_COMMANDS` tuple at cli.py:1989-2009 (after `eval_cmd,`). `register(group)` iterates the tuple — no other wiring needed.
  </action>
  <verify>
    <automated>python -m pytest "tests/harness/test_t5_shell.py::test_voss_jobs_reads_sidecar" -x -q && python -c "from voss.harness.cli import jobs_cmd, AGENT_COMMANDS; from voss.harness.sandbox import jail_path; import voss.harness.cli as c, inspect; assert jobs_cmd in AGENT_COMMANDS; assert 'from .sandbox import jail_path' in inspect.getsource(c) or hasattr(c,'jail_path'); print('jobs-registered+jailpath-imported')"</automated>
    <requirement>SHELL-05</requirement>
    <expected>jobs_cmd reads pre-seeded sidecars from a separate CliRunner invocation (no live session), renders the aligned table and one-JSON-per-line --json with the 8 D-11 keys verbatim; `jail_path` is importable in cli.py (no NameError); registered in AGENT_COMMANDS; corrupt sidecar skipped; empty -> "(no background jobs)".</expected>
  </verify>
  <done>`jail_path` imported in cli.py; `voss jobs` lists the active session's jobs from disk sidecars (table + --json), pid-liveness cross-checked, registered in AGENT_COMMANDS; cross-process test green; --json shape is the verbatim D-11 dict (M14-stable).</done>
</task>

<task type="auto">
  <name>Task 3: --keep-logs flag + .active-session lifecycle + explicit reap_jobs on REPL exit</name>
  <files>voss/harness/cli.py</files>
  <action>
    In voss/harness/cli.py (Task 2 already added `from .sandbox import jail_path` — reuse it; if Task 2's import is absent for any reason, add it):

    1. Add `@click.option("--keep-logs", "keep_logs", is_flag=True, default=False, help="Keep background-job logs/sidecars on session exit (default: reap them).")` to the `chat_cmd` option stack (beside the `--auth` option, cli.py:1178-1184). Add `keep_logs: bool` to the `chat_cmd(...)` signature (cli.py:1185-1194) and thread it into the `_run_repl(...)` call (cli.py:1209-1218) as `keep_logs=keep_logs`. Add `keep_logs: bool = False` to the `_run_repl` signature (cli.py:1299-1311) — keyword-only, defaulted, so existing `_run_repl` callers (resume/edit paths) need no change.

    2. `.active-session` write (Flag 3): in `_run_repl`, right after `ctx` is built and `record` is bound (cli.py:1343-1360, where `record.id` is already used at :1358), compute `jobs_root = jail_path(cwd, ".voss-cache") / "jobs"`, `jobs_root.mkdir(parents=True, exist_ok=True)`, and write `(jobs_root / ".active-session").write_text(record.id)`. Wrap in a best-effort try/except (must NOT crash REPL boot — same discipline as the cognition drift guard at cli.py:1381-1389).

    3. `.active-session` remove + explicit reap (Flag 3 / Flag 4) — use a `try/finally` so the cleanup runs on ALL `_run_repl` exits, not only EOF/KeyboardInterrupt (WARNING 2 fix): wrap the `while True:` REPL loop in `try:` and put a `finally:` after it whose body is a best-effort try/except that:
       a. runs `asyncio.run(lifecycle.reap_jobs())` (lazy `from . import lifecycle`; reuse the asyncio-run/new-loop fallback discipline modeled in lifecycle._atexit_hook if a running loop is detected — the REPL exit path is synchronous so `asyncio.run` is the primary path);
       b. if `not keep_logs`: `shutil.rmtree(jail_path(cwd, ".voss-cache") / "jobs" / record.id, ignore_errors=True)` AND remove the `.active-session` pointer file; if `keep_logs`: leave the dir, still remove the `.active-session` pointer (the session is no longer active even if logs are kept).
       The `finally:` guarantees pointer removal + reap on slash `/exit`, normal `return`, and exception-bubble paths — closing the WARNING 2 stale-pointer gap. Keep the existing `except (EOFError, KeyboardInterrupt):` -> `conventions.run_on_clean_exit(...)` + `return` behavior byte-identical INSIDE the new `try:` (the conventions call stays where it is; only the loop gets wrapped so the `finally:` is reached after the `return`). Wrap the finally body so a reap/cleanup failure can never crash the exit (mirror the `conventions extraction skipped` guard at cli.py:1403-1404 — `click.echo(f"job reap skipped: {exc}", err=True)`).

    RESIDUAL acknowledged (WARNING 2): a hard `SIGKILL` of the chat process (no Python unwinding) still leaves a stale `.active-session` + sidecars. This is the documented crash residual — `voss jobs`'s newest-mtime fallback (Task 2) + the atexit `reap_all`->`reap_jobs` net (T5-03) cover it; a post-crash sweep is explicitly out of T5 scope (M14 territory, per RESEARCH Runtime State Inventory). State this in the SUMMARY.

    Do NOT touch the resume/edit `_run_repl` callers' argument lists (the new param is keyword-only with a default). Do NOT change reap_all or the atexit hook (T5-03 owns those; this explicit call is the ordered primary path, atexit remains the crash net).
  </action>
  <verify>
    <automated>python -m pytest tests/harness/test_t5_shell.py -q -m "not live" && python -c "import inspect; from voss.harness import cli; s=inspect.getsource(cli._run_repl); assert '.active-session' in s and 'reap_jobs' in s and 'finally' in s, 'missing active-session/reap/finally wiring'; c=inspect.getsource(cli.chat_cmd); assert 'keep_logs' in c, 'missing --keep-logs thread'; print('repl-wiring-ok')"</automated>
    <requirement>SHELL-05 (D-11 active-session + D-02 --keep-logs)</requirement>
    <expected>_run_repl writes .active-session on start and removes it + reaps jobs in a `finally:` (covering EOF, /exit, return, exception paths — WARNING 2 closed); chat_cmd threads keep_logs; full non-live T5 suite green; no regression in existing cli-driven tests.</expected>
  </verify>
  <done>`--keep-logs` flows chat_cmd -> _run_repl; `.active-session` written on start and removed in a `try/finally` (all non-crash exits, not just EOF — WARNING 2 closed); `reap_jobs()` fires explicitly on exit; `--keep-logs` controls the jobs-dir cleanup; hard-kill residual documented; existing _run_repl callers untouched (keyword-only default).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| separate `voss jobs` process → on-disk sidecars | cross-process read of attacker-influenceable JSON written by another process |
| chat session → `.active-session` pointer | session-scoping contract for the inventory command |
| post-crash residue | stale sidecars with status="running" that no process will update |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T5-05a | Tampering / DoS | corrupt or partially-written `.meta.json` crashing `voss jobs` | mitigate | Tolerant glob+`json.loads` swallowing `(OSError, json.JSONDecodeError)` (session.py:217-223 idiom); atomic temp→`.replace()` writer (T5-03) means readers never see partial JSON; Windows PermissionError retry-once (Pitfall 5). |
| T-T5-05b | Spoofing (false liveness) | sidecar says "running" after a host crash | mitigate | `psutil.pid_exists` cross-check at render time — `voss jobs` shows last-known status, never asserts liveness it cannot verify (RESEARCH Runtime State Inventory / A6). |
| T-T5-05c | Info disclosure | PID shown in `voss jobs` output | accept | D-01 scopes PID-hiding to the LLM tool boundary only; `voss jobs` is human-facing (HANDLE PID STATUS ... is the locked D-04 column set); sidecar-on-disk carrying PID is by design. |
| T-T5-05d | DoS | orphaned jobs after a non-clean crash | accept | Documented residual (RESEARCH Runtime State Inventory) — explicit reap on clean exit + atexit net cover the normal paths; post-crash sweep is explicitly out of T5 scope (M14 territory). |
</threat_model>

<verification>
- `pytest tests/harness/test_t5_shell.py::test_voss_jobs_reads_sidecar -x -q` green (cross-process realism: pre-seeded sidecar + CliRunner, no live session).
- `pytest -q` full suite green before `/gsd:verify-work`.
- Manual smoke (VALIDATION manual-only): Terminal A `voss chat` + 60s bg job; Terminal B `voss jobs` shows handle/PID/RUNNING.
- `--json` output parses to the verbatim 8-key D-11 dict (M14 contract intact).
</verification>

<success_criteria>
- `voss jobs` lists the active session's jobs from disk sidecars only (separate process; `_JOBS` never touched).
- Aligned table + `--json` (one D-11 dict per line, M14-stable); pid-liveness honest.
- `.active-session` written on REPL start, removed on clean exit; newest-mtime fallback.
- `--keep-logs` at `voss chat` controls jobs-dir cleanup; default reaps.
- Explicit `reap_jobs()` on clean exit; existing `_run_repl` callers unbroken.
</success_criteria>

<output>
Create `.planning/phases/T5-shell-ergonomics/T5-05-SUMMARY.md` when done.
</output>
