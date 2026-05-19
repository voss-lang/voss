---
phase: M14-long-running-tasks-watch-caps-01e
plan: 04
type: execute
wave: 3
depends_on: ["M14-02"]
files_modified:
  - voss/harness/watch/daemon.py
  - voss/harness/cli.py
autonomous: true
requirements: [WATCH-03, WATCH-04, WATCH-05]
user_setup: []

must_haves:
  truths:
    - "voss watch 'pytest -q' runs the command, re-executes it when a watched file changes"
    - "The shell allowlist (shell_allowed + split_command) is enforced on the voss watch <command>"
    - "A non-daemon voss watch is reaped on session exit with T5-parity timing (SIGTERM <=2s / SIGKILL <=5s)"
    - "A voss watch --daemon is still running after the session exits (detached, not in _JOBS/_WATCHERS)"
    - "The daemon worker does not re-enter the detach path (--_is-worker re-entry guard)"
  artifacts:
    - path: "voss/harness/watch/daemon.py"
      provides: "spawn_detached_worker(argv) — start_new_session detach + --_is-worker re-entry guard"
      contains: "start_new_session"
      min_lines: 25
    - path: "voss/harness/cli.py"
      provides: "watch_cmd top-level click command + AGENT_COMMANDS registration"
      contains: "watch_cmd"
  key_links:
    - from: "voss/harness/cli.py:watch_cmd"
      to: "voss.harness.sandbox.shell_allowed"
      via: "allowlist gate before spawning the child"
      pattern: "shell_allowed|split_command"
    - from: "voss/harness/cli.py:watch_cmd"
      to: "voss.harness.watch.daemon.spawn_detached_worker"
      via: "--daemon path re-spawns detached"
      pattern: "spawn_detached_worker"
    - from: "voss/harness/cli.py:AGENT_COMMANDS"
      to: "watch_cmd"
      via: "watch_cmd appended after jobs_cmd"
      pattern: "watch_cmd"
---

<objective>
Add the top-level `voss watch <command>` CLI (WATCH-03) and the `--daemon` detach path (WATCH-04).
Non-daemon: in-process watchdog Observer (via M14-02 `register_watcher`) + child via T5
`register_job`, TERM-prior-child-then-respawn on change, reaped by the unchanged T5 path on session
exit. `--daemon`: re-spawn self detached via `voss/harness/watch/daemon.py:spawn_detached_worker`
(`start_new_session=True`, stdio DEVNULL, NOT registered in `_JOBS`/`_WATCHERS`) so it survives
session exit. Shell allowlist (`shell_allowed` + `split_command`) gates `<command>` (D-03).

Purpose: Delivers the operator-facing `voss watch` deliverable and the genuine daemon survival that
only a detached subprocess can satisfy (an in-process Observer thread dies with the Python process).
Output: new `voss/harness/watch/daemon.py`, extended `voss/harness/cli.py`.
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
<!-- LOCKED: OQ-3 — daemon re-exec argv = [sys.executable, "-m", "voss.harness.cli", "watch",
     "--_is-worker", <surviving original args>]. The re-entry guard flag is "--_is-worker"
     (Pitfall 5: strip --daemon, add --_is-worker before re-exec; worker path skips detach).
     Using `[sys.executable, "-m", "voss.harness.cli", ...]` makes the worker independent of
     whether `voss` is on PATH (RESEARCH Open Question 3 recommendation). LOCKED. -->

Consumed from M14-02 (voss/harness/lifecycle.py):
  async def register_watcher(globs, cwd, *, session_id="_nosession", debounce_ms=200) -> str
  async def reap_watchers() -> None        # wired into reap_all already
  register_job(*, cmd, argv, cwd, session_id, ...) -> str | Future   # T5, unchanged (lines 359-394)
  signal_job(handle, sig, *, session_id=None) -> bool                # T5, unchanged (lines 443-451)
  _kill_tree(proc, sig, *, use_process_group=True) -> None           # T5, unchanged (lines 151-169)

From voss/harness/sandbox.py: shell_allowed(cmd) -> (bool, reason); split_command(cmd) -> list[str];
  SandboxError (the exact T5 allowlist gate used by shell_run_background tools.py:171-203)

From voss/harness/cli.py (verified seams):
  lines 2115-2175  jobs_cmd — @click.command("jobs") + --cwd + cwd=Path(cwd_str).resolve() pattern (model for watch_cmd)
  lines 2878-2902  AGENT_COMMANDS tuple — `jobs_cmd,` at line 2886; add `watch_cmd,` immediately after
  lines 2839-2875  logs_group / `logs watch` — a GROUP subcommand; watch_cmd is a standalone
                   @click.command("watch") peer of jobs_cmd — NO namespace collision
  lines 2905-2908  register(group) — iterates AGENT_COMMANDS; no change needed

watchdog._spawn_job precedent (lifecycle.py:330-356): start_new_session=(os.name=="posix")
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Build the daemon detach worker (start_new_session + re-entry guard)</name>
  <read_first>
    - voss/harness/lifecycle.py (lines 330-356 _spawn_job — the `start_new_session=(os.name=="posix")` precedent; lines 151-169 _kill_tree — the `os.name == "posix"` platform-guard idiom to reuse)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-RESEARCH.md (Pattern 5 daemon detach via start_new_session=True [CITED]; § Code Examples WATCH-04; § Common Pitfall 5 double-daemon re-entry; Open Question 3 — OQ-3 argv shape; Assumption A5/A7)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-PATTERNS.md (watch/daemon.py PARTIAL-analog section — _spawn_job adaptation, re-entry guard contract, _kill_tree platform guard reuse)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-CONTEXT.md (D-03 HYBRID daemon: detached subprocess NOT registered in _JOBS/_WATCHERS, no proc.wait(), strip --daemon + add re-entry guard before re-exec)
  </read_first>
  <behavior>
    - Test (unit, part of test_daemon_watch_survives_exit setup): spawn_detached_worker returns an int
      PID; the spawned process is in a new session (os.getsid(pid) != os.getsid(0) on POSIX); the
      parent does NOT block on it (function returns immediately, no proc.wait()).
    - Test: argv reshaping strips "--daemon" and injects "--_is-worker" exactly once; the worker
      command is [sys.executable, "-m", "voss.harness.cli", "watch", "--_is-worker", ...].
    - Test: a worker invocation containing "--_is-worker" is NOT re-detached (re-entry guard).
  </behavior>
  <action>
    Create voss/harness/watch/daemon.py with `spawn_detached_worker(original_argv: list[str]) -> int`:
    build `worker_argv = [sys.executable, "-m", "voss.harness.cli", "watch"]` plus the original watch
    arguments with every "--daemon" removed, then append "--_is-worker" (OQ-3 LOCKED shape). Call
    `subprocess.Popen(worker_argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True)` (synchronous Popen — the
    detach path does NOT supervise the child) and return `proc.pid`; intentionally DO NOT call
    proc.wait() (comment why — D-03 immediate detach). Add `is_worker_invocation(argv: list[str]) ->
    bool` returning whether "--_is-worker" is present (used by the CLI re-entry guard). Mirror the
    `os.name == "posix"` platform idiom from _kill_tree where a POSIX/Windows split is needed
    (start_new_session is accepted on both but only setsid()s on POSIX — document the Windows
    best-effort caveat per WATCH-05). No registration in _JOBS/_WATCHERS anywhere in this module.
  </action>
  <verify>
    <automated>python -m pytest tests/harness/test_m14_watch.py::test_daemon_watch_survives_exit -q -x</automated>
  </verify>
  <acceptance_criteria>
    - Test command: `python -m pytest tests/harness/test_m14_watch.py::test_daemon_watch_survives_exit -x` PASSES (daemon still running after parent exit; PID killed in fixture teardown).
    - Source assertion: `grep -c 'start_new_session=True' voss/harness/watch/daemon.py` == 1.
    - Source assertion: `grep -c 'proc.wait()' voss/harness/watch/daemon.py` == 0 (no blocking — detach immediate; a `# proc.wait() intentionally NOT called` comment is allowed since the grep gate filters comments).
    - Source assertion: `grep -v '^#' voss/harness/watch/daemon.py | grep -c '_is-worker'` >= 2 (injected into argv + checked by is_worker_invocation).
    - Source assertion: `grep -c 'sys.executable.*-m.*voss.harness.cli' voss/harness/watch/daemon.py` >= 1 (OQ-3 argv shape).
    - Negative assertion: `grep -c 'register_job\|register_watcher\|_JOBS\|_WATCHERS' voss/harness/watch/daemon.py` == 0 (daemon worker is NOT registered — D-03).
  </acceptance_criteria>
  <done>daemon.py provides spawn_detached_worker (start_new_session, DEVNULL stdio, no proc.wait, not registered) + is_worker_invocation re-entry guard with the OQ-3 argv shape; daemon-survives-exit test green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add voss watch CLI command (allowlist + re-run + non-daemon reap + daemon dispatch)</name>
  <read_first>
    - voss/harness/cli.py (lines 2115-2175 jobs_cmd — @click.command + --cwd + cwd=Path(cwd_str).resolve() entry convention; lines 2839-2875 logs_group/`logs watch` — confirm watch_cmd is a standalone peer, no collision; lines 2878-2902 AGENT_COMMANDS — jobs_cmd at line 2886; lines 2905-2908 register())
    - voss/harness/tools.py (lines 171-203 shell_run_background — the exact `ok, reason = shell_allowed(cmd); if not ok: return f"<denied: {reason}>"; try: argv = split_command(cmd) except SandboxError` gate to copy for watch_cmd)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-RESEARCH.md (Pattern 7 voss watch CLI placement [CITED jobs_cmd]; § Code Examples — register_job for the child; D-03 re-run = TERM prior child then re-spawn via register_job; § Existing Code Scout cli.py table)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-PATTERNS.md (cli.py section — jobs_cmd Click pattern, AGENT_COMMANDS insertion point, logs watch non-collision)
    - .planning/phases/M14-long-running-tasks-watch-caps-01e/M14-CONTEXT.md (D-03 hybrid daemon full text; shell allowlist still applies; voss watch sibling of voss jobs; SCOPE FENCE — no TUI, no M10 hookback)
  </read_first>
  <behavior>
    - Test: test_voss_watch_reruns_on_change — `voss watch 'pytest -q' --glob '**/*.py' --cwd <tmp>`
      (non-daemon, bounded/one-shot test mode) runs the command once, then re-executes it after a
      matching file changes; the re-run is observable (second invocation recorded).
    - Test: test_watch_command_allowlist — `voss watch '<disallowed pipeline/chain>'` is rejected via
      shell_allowed and the child is NOT spawned (denied message; exit non-zero).
    - Test: test_nondaemon_watch_reaped_on_exit — a non-daemon voss watch child is reaped on session
      exit with T5 parity (SIGTERM <=2s, SIGKILL <=5s) via the unchanged reap_jobs/reap_all path.
    - Test: re-run on change TERMs the prior child before re-spawning (no orphan accumulation).
  </behavior>
  <action>
    In voss/harness/cli.py add a standalone `@click.command("watch")` `watch_cmd` (peer of jobs_cmd —
    NOT attached to logs_group) with options: `@click.argument("command")`, `@click.option("--glob",
    "globs", multiple=True, default=("**/*",))`, `@click.option("--cwd", "cwd_str", default=".",
    type=click.Path(file_okay=False))`, `@click.option("--daemon", "daemon_mode", is_flag=True)`,
    `@click.option("--debounce-ms", default=200, type=int)`, plus a hidden
    `@click.option("--_is-worker", "is_worker", is_flag=True, hidden=True)`. Entry: `cwd =
    Path(cwd_str).resolve()` (jobs_cmd convention). FIRST gate the command:
    `from .sandbox import shell_allowed, split_command, SandboxError` (or reuse the existing cli import
    site), `ok, reason = shell_allowed(command); if not ok:` echo `<denied: {reason}>` and
    `raise SystemExit(1)`; `try: argv = split_command(command) except SandboxError as e:` echo
    `<denied: {e}>` + exit 1 (copy the shell_run_background gate exactly — WATCH-03 allowlist). Then:
    if `daemon_mode` and not `is_worker`: `from .watch.daemon import spawn_detached_worker`, call it
    with the reconstructed original argv, echo the detached PID, return immediately (the parent does
    NOT run the Observer — WATCH-04). Otherwise (non-daemon OR worker): run the in-process path —
    `await lifecycle.register_watcher(list(globs), cwd, session_id=..., debounce_ms=debounce_ms)` to
    start the Observer, spawn the child once via `await lifecycle.register_job(cmd=command, argv=argv,
    cwd=cwd, session_id=...)`, then on each debounced change: `lifecycle.signal_job(prior_handle,
    SIGTERM, session_id=...)` (or `_kill_tree`) the prior child then re-spawn via register_job (D-03
    TERM-prior-then-respawn — reuse T5, do not hand-roll). The non-daemon child + watcher are reaped by
    the unchanged `lifecycle.reap_all()`/`reap_jobs()` path on session exit (no new reap code).
    Make the watch loop test-bounded (honor an iteration/SIGINT exit so tests are deterministic — do
    NOT add a `pytest --watch`-style flag). Append `watch_cmd,` to the AGENT_COMMANDS tuple
    immediately after `jobs_cmd,` (line ~2886). Do NOT touch logs_group or any other command.
  </action>
  <verify>
    <automated>python -m pytest tests/harness/test_m14_watch.py::test_voss_watch_reruns_on_change tests/harness/test_m14_watch.py::test_watch_command_allowlist tests/harness/test_m14_watch.py::test_nondaemon_watch_reaped_on_exit -q -x</automated>
  </verify>
  <acceptance_criteria>
    - Test command: `python -m pytest tests/harness/test_m14_watch.py::test_voss_watch_reruns_on_change -x` PASSES (re-executes on change).
    - Test command: `python -m pytest tests/harness/test_m14_watch.py::test_watch_command_allowlist -x` PASSES (disallowed command denied, child not spawned).
    - Test command: `python -m pytest tests/harness/test_m14_watch.py::test_nondaemon_watch_reaped_on_exit -x` PASSES (T5-parity reap).
    - Behavior assertion: `python -c "from voss.harness.cli import AGENT_COMMANDS; n=[c.name for c in AGENT_COMMANDS]; print('watch' in n and n.index('watch')==n.index('jobs')+1)"` prints True (watch_cmd registered immediately after jobs_cmd).
    - Source assertion: `grep -c 'shell_allowed\|split_command' voss/harness/cli.py` increased vs baseline (allowlist gate present in watch_cmd — WATCH-03).
    - Source assertion: `grep -c 'spawn_detached_worker' voss/harness/cli.py` >= 1 (--daemon dispatch wired — WATCH-04).
    - Regression: `python -c "from click.testing import CliRunner; from voss.harness.cli import logs_group; print('watch' in logs_group.commands)"` prints True AND the top-level `watch` is a separate command (no namespace collision with `logs watch`).
    - Scope-fence: `grep -ci 'tui\|code_refresh\|status.strip' voss/harness/cli.py` shows no NEW M9-TUI/M10 wiring added by watch_cmd (diff scoped to the watch command only).
  </acceptance_criteria>
  <done>watch_cmd is a top-level command (after jobs_cmd) enforcing the shell allowlist, re-running the command on change via T5 register_job/signal_job, reaped by the unchanged T5 path (non-daemon), dispatching to spawn_detached_worker for --daemon; WATCH-03 + WATCH-04 non-daemon tests green; no TUI/M10 creep.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Operator CLI arg → subprocess | `voss watch <command>` argument becomes an executed child process |
| Operator CLI arg → glob/cwd | `--glob` / `--cwd` could reference paths outside the workspace |
| Parent process → detached daemon | The daemon worker inherits the parent environment and outlives it |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M14-11 | Tampering | command injection via `voss watch <command>` | mitigate | `shell_allowed(command)` + `split_command(command)` gate FIRST (copied verbatim from shell_run_background tools.py:171-203); pipelines/chaining/substitution rejected; child run via exec argv, never `/bin/sh -c` |
| T-M14-12 | Tampering | `--glob`/`--cwd` escaping workspace | mitigate | watch root jailed via `jail_path(cwd, ".")` in `lifecycle.register_watcher` (M14-02 T-M14-04); CLI does no raw path scheduling |
| T-M14-13 | Information Disclosure | detached daemon inheriting sensitive env (e.g. ANTHROPIC_API_KEY) | mitigate | `spawn_detached_worker` redirects stdio to DEVNULL; document that the daemon worker only needs watch+command args — note in M14-04-SUMMARY that env sanitization (stripping provider keys) is the chosen mitigation and is applied in spawn_detached_worker if the worker does not require them (M14-RESEARCH § Security Domain Information Disclosure row) |
| T-M14-14 | Denial of Service | `--daemon` watch has no session-bound stop handle | accept | Documented limitation (SPEC: daemon survival in scope, management surface out of scope). M14-04-SUMMARY records: user kills PID manually; `voss watch --list/--stop` is a backlog item (M14-CONTEXT Deferred Ideas) |
| T-M14-15 | Denial of Service | re-run accumulating orphan children | mitigate | Each re-run TERMs the prior child via T5 `signal_job`/`_kill_tree` before re-spawning (D-03); non-daemon children reaped by unchanged `reap_jobs` on exit |
| T-M14-SC | Tampering | watchdog import surface | mitigate | watchdog pin + legitimacy checkpoint already gated in M14-01 (T-M14-SC); no new package here |
</threat_model>

<verification>
- `python -m pytest tests/harness/test_m14_watch.py::test_voss_watch_reruns_on_change tests/harness/test_m14_watch.py::test_watch_command_allowlist tests/harness/test_m14_watch.py::test_nondaemon_watch_reaped_on_exit tests/harness/test_m14_watch.py::test_daemon_watch_survives_exit -q -x` all PASS
- `voss watch` registered as a top-level command immediately after `jobs_cmd` in AGENT_COMMANDS
- shell allowlist enforced before any child spawn (WATCH-03)
- non-daemon child reaped by the unchanged T5 path; --daemon dispatches to spawn_detached_worker (not registered)
- no `pytest --watch` flag; no TUI/M10 wiring added (SCOPE FENCE)
</verification>

<success_criteria>
- voss watch <command> runs + re-executes on watched-file change (WATCH-03)
- Shell allowlist enforced on <command> (WATCH-03)
- Non-daemon voss watch reaped on session exit with T5 parity (WATCH-04)
- voss watch --daemon survives session exit, detached, not registered (WATCH-04)
- --_is-worker re-entry guard prevents double-daemon spawn (OQ-3)
- watch_cmd is a top-level peer of jobs_cmd; no logs-watch collision; no TUI/M10 scope creep
</success_criteria>

<output>
Create `.planning/phases/M14-long-running-tasks-watch-caps-01e/M14-04-SUMMARY.md` when done
</output>
