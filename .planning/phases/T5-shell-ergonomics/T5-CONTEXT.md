# Phase T5: Shell Ergonomics — Context

**Gathered:** 2026-05-16
**Status:** Ready for planning
**SPEC:** None — requirements drawn from ROADMAP.md T5 (SHELL-01..SHELL-05 proposed)

<domain>
## Phase Boundary

Real builds and test runs survive the shell tool. Long-running tasks don't block the agent. Phase delivers five surface changes:

- **SHELL-01:** `shell_run` default output cap raised 4KB → 30KB.
- **SHELL-02:** New `shell_run_background(cmd) -> handle` — detached process reaped on session exit.
- **SHELL-03:** New `shell_monitor(handle, since_ms=0) -> chunk` — incremental stream.
- **SHELL-04:** New `shell_signal(handle, signal="INT"|"TERM")`.
- **SHELL-05:** `voss jobs` CLI lists running background processes for current session.

This phase is the **headless half** of M14 (file-watch). M14 layers `watchdog` library on top. T5 owns: process lifetime, output capture, monitor surface, signal delivery, CLI inventory. T5 does NOT own: file-watch triggers, dev-server lifecycle helpers, TUI status-strip integration.

</domain>

<decisions>
## Implementation Decisions

### Handle shape (D-01)

`shell_run_background` returns a session-scoped slug `bg-NNN` where NNN is a monotonic counter starting at `001`, zero-padded to 3 digits. Counter resets per session (handles do NOT survive session restart — orphans get reaped per locked Success Criteria #2). Raw PID stays an internal field of the in-memory JobRecord (`{handle, pid, started_at, cmd, log_path, status, exit_code}`); never returned to the LLM.

Rationale: human-readable in tool result envelopes (`tool.result` text) and `voss jobs` table; LLM-friendly to round-trip through `tool.call(handle="bg-001")`; collision-free within a session; PID-hidden surface keeps OS detail off the agent.

### Output buffer model (D-02)

Background stdout + stderr are merged and written to a single disk tail file:

```
.voss-cache/jobs/<session_id>/<handle>.log
```

Matches existing `shell_run` stdout-stderr-merged behavior (tools.py:144 `stderr=subprocess.STDOUT`). Session-id directory keeps multi-session inventory partitioned. Files are reaped on session exit (unless `--keep-logs` flag at `voss chat` entry point — researcher confirms exact flag location). No in-memory ring buffer.

Rationale: survives crash for forensic inspection; aligns with `.voss-cache/` convention (M2/M4 precedent); `shell_monitor` reads via byte cursor (no IO complexity beyond `seek/read`); 100MB RSS cap (Success Criteria #3) is about subprocess memory, NOT log size — log file is allowed to grow.

### Monitor semantics (D-03)

`shell_monitor(handle, since_ms=0)` is **non-blocking**. Returns immediately with whatever output is currently available past the cursor. Tool result envelope shape (string, to match `shell_run` style):

```
[cursor N][running|exit M]
<chunk bytes, possibly empty>
```

- `since_ms=0` means "from start of log".
- `since_ms` is reinterpreted internally as **opaque byte offset cursor** — the locked param name (`since_ms`) is preserved per ROADMAP, but no wall-clock timestamp→offset map is maintained. Documented in the tool description.
- Returned `cursor N` is the new byte offset; caller passes it back as `since_ms=N` on the next call.
- `done` is signaled by `[exit M]` in the prefix instead of `[running]`. Once `done`, the log file remains readable until session exit.
- Chunk truncation: same 30KB cap as SHELL-01's raised `shell_run` cap. If more bytes available, append `<truncated, N more bytes — re-monitor with cursor M>` and emit a new cursor at the truncation point.

Rationale: simplest possible cursor model; no sidecar `.idx` file; iteration loop polls between turns rather than burning a turn on a blocking wait; per-turn cost bounded.

### `voss jobs` CLI output (D-04)

Default: aligned human-readable table — columns `HANDLE  PID  STATUS  RUNTIME  CMD`. Truncate `CMD` column at terminal width.

`--json` flag: emit one JSON record per line (`{handle, pid, status, runtime_ms, cmd, log_path, exit_code|null}`). Matches existing `/cost` and `voss check` ergonomics.

`voss jobs` is **session-scoped** — only lists jobs from the current session. Cross-session inventory deferred to a future phase (no use case yet).

### Allowlist parity (D-05)

`shell_run_background` reuses `shell_allowed()` from `voss/harness/sandbox.py` verbatim. One source of truth.

Background-specific risk (orphan damage, runaway processes, mem blowup) is handled by:
- Lifecycle reap (SIGTERM 2s → SIGKILL 5s on session exit, per Success Criteria #2). Reuses existing `voss/harness/lifecycle.py` (already implements this pattern for MCP subprocesses + net sessions).
- 100MB RSS cap + 30s no-output watchdog (Success Criteria #3) — exact enforcement mechanism deferred to researcher (psutil polling vs `resource.setrlimit` cross-platform tradeoff).

NOT handled by allowlist narrowing (no second list to drift).

### Signal surface (D-06)

`shell_signal(handle, signal)` accepts ONLY `"INT"` and `"TERM"` per locked ROADMAP surface. `"KILL"` is an internal-only escalation owned by lifecycle reap. Unknown signal values return `<denied: unsupported signal>` envelope.

Mapping: `"INT"` → `signal.SIGINT`, `"TERM"` → `signal.SIGTERM`. Sent via `proc.send_signal(...)` on the asyncio.subprocess.Process referenced by the JobRecord.

### `shell_run` cap raise (D-07)

`shell_run` truncation constant raised 4096 → 30720 (4KB → 30KB). Same `<truncated, total N bytes>` envelope. Single-line constant change at `voss/harness/tools.py:156` area. No new code path; existing 30s timeout preserved.

### Telemetry shape (D-08)

Reuse existing `tool.call` / `tool.result` events for `shell_run_background`, `shell_monitor`, `shell_signal` invocations (they are tools, recorder already handles them). Add ONE new flat-dict event:

- `shell.background.reap` — emitted by lifecycle reap when a background job is terminated. `data: {handle, pid, signal, exit_code, runtime_ms, reason: "session_exit"|"watchdog_no_output"|"watchdog_mem"|"explicit_signal"}`.

NO new event for start/normal-exit (the `tool.result` envelope already carries that signal). Flat data dict per T4 D-05 precedent.

### Session-id source (D-09)

`<session_id>` directory name is the existing `SessionRecord.session_id` (UUID4) already minted at `voss chat` start. Background jobs partition cleanly across concurrent sessions.

### Post-research ratification (D-10..D-12, locked 2026-05-16)

These three were NOT in the original discussion — surfaced by RESEARCH.md as planner-blocking and ratified by the user before planning.

- **D-10 RSS cap mechanism:** Add `psutil >= 5.9,<8` as a runtime dependency (first new runtime dep since the harness was built). `resource.setrlimit(RLIMIT_RSS)` is a confirmed no-op on macOS/Darwin, so psutil polling is the only cross-platform mechanism. Enforcement: 1s poll tick, `psutil.Process(pid).children(recursive=True)` RSS tree-sum vs 100MB. Honors Success Criteria #3 on Linux + macOS + Windows. Package legitimacy: top-100 PyPI, 352M dl/mo, 16-yr history — planner adds a human-verify checkpoint for the dependency addition (slopcheck was unavailable at research time).

- **D-11 `voss jobs` cross-process architecture:** `voss jobs` runs as a SEPARATE OS process from the `voss chat` session that owns the jobs — in-memory `_JOBS` is invisible to it. Mandatory design: each job writes a per-job `<handle>.meta.json` sidecar in `.voss-cache/jobs/<session_id>/` updated on every state transition (start, exit, signal, reap). `voss chat` writes `.voss-cache/jobs/.active-session` containing the current `session_id`. `voss jobs` reads `.active-session` → scans that session dir's `*.meta.json`. JobRecord gains disk persistence (the sidecar IS the JobRecord serialized). Sidecar schema = JobRecord dict verbatim (`{handle, pid, started_at, cmd, log_path, status, exit_code, runtime_ms}`).

- **D-12 Edit-mode permission (security):** `permissions.py:61` hard-denies `shell_run` by literal name in `edit` mode. Extend `mode_allows` so `edit` mode ALSO denies `shell_run_background` and `shell_signal` (consistent invariant: edit mode = no shell execution of any kind). Closes the is_mutating=True slip-through. `shell_monitor` is read-only (pure file read) — planner decides if it stays allowed in edit mode (recommend: allow, it executes nothing).

### Claude's Discretion

These were not explicitly asked but are implementation-natural:

- Exact lifecycle integration: extend `voss/harness/lifecycle.py` `_SUBPROCESSES` registry with a parallel `_JOBS` dict keyed by handle, OR reuse the same registry tagged by source. Recommend separate registry — different reap semantics (timed watchdog vs reap-on-exit-only).
- 100MB RSS / 30s no-output enforcement mechanism: psutil polling on a 1s tick vs `resource.setrlimit` (Linux only; macOS ignores RLIMIT_RSS). Researcher recommends psutil polling for cross-platform parity.
- `voss jobs --json` field naming: stick to the JobRecord dict shape verbatim (`{handle, pid, status, runtime_ms, cmd, log_path, exit_code}`) so the recorder, CLI, and tool envelope share one schema.
- Multi-line `CMD` truncation in human table: ellipsis at `terminal_width - 50` (room for fixed columns), no wrap.
- `shell_run_background` is_mutating classification: TRUE (matches `shell_run` per M1 D-06 ToolEntry pattern). Implies it runs serialized — never inside a parallel read batch (T2 PAR-02 invariant holds automatically).
- `--keep-logs` flag location: at `voss chat` entry, not per-tool. Defaults to false. When true, skip the `rm -rf .voss-cache/jobs/<session_id>/` on session exit.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase artifacts (locked)

- `.planning/ROADMAP.md` §"Phase T5 — Shell Ergonomics" — phase goal, SHELL-01..05 proposed requirements, success criteria, cross-cutting constraints (allowlist, no TTY inheritance, M14 layering).

### Codebase anchors (read before touching)

- `voss/harness/tools.py:127-160` — current `shell_run` impl (allowlist gate, asyncio.create_subprocess_exec, 30s timeout, 4KB truncation). SHELL-01 modifies line 156 area; SHELL-02 mirrors structure for backgrounded variant.
- `voss/harness/tools.py:332` area — `ToolEntry(descriptor=shell_run, is_mutating=True)` registration. Three new tools register here.
- `voss/harness/lifecycle.py` — full file. `register_subprocess`, `reap_all` (SIGTERM 5s deadline → SIGKILL), `_atexit_hook`. SHELL-02..04 extend this with a parallel `_JOBS` registry + watchdog tasks.
- `voss/harness/sandbox.py` — `shell_allowed()` + `split_command()` allowlist gate; reused verbatim by SHELL-02 (D-05).
- `voss/harness/permissions.py:46` — `SHELL = {"shell_run"}` permission group. New tools join this group.
- `voss/harness/tui/permissions_bridge.py:28-36` — TUI-side approval bridge for shell tools. New tools route through same surface.
- `voss/harness/session.py` — `SessionRecord.session_id` is the `<session_id>` path component for `.voss-cache/jobs/<session_id>/`.
- `voss/harness/recorder.py:22` — `VALIDATE_TOOLS = {"shell_run", "voss_check"}` constant; new tools may need recorder awareness (researcher confirms).
- `voss/harness/cognition.py:678` — current cognition text referencing `shell_run` in deny lists; new tools may need similar guidance.
- `voss/harness/cli.py` — entry point for `voss jobs` subcommand (D-04) + `--keep-logs` flag (D-02 Claude's Discretion).

### Cross-phase context

- `.planning/phases/M14-long-running-tasks-watch-caps-01e/` — M14 phase layers `watchdog` file-watch on top of T5's background infra. T5 must leave hooks (or at least not preclude) M14's bottom-pane TUI status strip + dev-server lifecycle layer.
- `.planning/phases/T1-iteration-loop-streaming-interrupt/T1-CONTEXT.md` — additive-dataclass pattern for any T5-side RunRecord / IterationRecord extensions.
- `.planning/phases/T2-parallel-tools-multi-edit/T2-CONTEXT.md` — `ToolEntry.is_mutating` invariant; partition-time enforcement means `shell_run_background` (is_mutating=True) is never in a parallel read batch.
- `.planning/phases/T4-prompt-caching-cost-truthfulness/T4-CONTEXT.md` D-05 — flat telemetry data-dict precedent for `shell.background.reap` (D-08).

### External protocol

- Python `asyncio.subprocess.Process` docs — `terminate`, `kill`, `send_signal`, `wait`, `returncode` semantics (already used by lifecycle.py).
- `psutil.Process(pid).memory_info().rss` — cross-platform RSS read for the 100MB cap. Pin minimum psutil version at planning time (researcher).
- POSIX signal numbers — `SIGINT=2`, `SIGTERM=15`, `SIGKILL=9`. Windows signal mapping (researcher confirms behavior — `send_signal(SIGTERM)` falls back to `TerminateProcess`).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`shell_allowed()`** in `voss/harness/sandbox.py` — single allowlist gate, reused verbatim by SHELL-02 (D-05).
- **`split_command()`** in `voss/harness/sandbox.py` — argv splitter, reused for SHELL-02.
- **`register_subprocess()` + `reap_all()`** in `voss/harness/lifecycle.py:30-72` — SIGTERM-with-deadline-then-SIGKILL pattern. SHELL-02..04 extend with a `_JOBS` registry that uses the same reap shape but adds watchdog timers.
- **`atexit.register(_atexit_hook)`** in `voss/harness/lifecycle.py:101` — already fires on interpreter shutdown; T5 piggybacks (no new atexit hook).
- **`SessionRecord.session_id`** — minted at `voss chat` start; used as the partition key for `.voss-cache/jobs/<session_id>/`.
- **`@tool(name=..., description=...)` decorator + `ToolEntry(descriptor, is_mutating=True)` registration** — three new tools follow this verbatim.

### Established Patterns

- **Allowlist-then-exec** — `shell_run` gates on `shell_allowed()` BEFORE any subprocess spawn. Background variant gates identically before forking.
- **String tool envelopes** — `shell_run` returns `[exit N]\n<text>`. Background variant returns `[cursor N][running|exit M]\n<chunk>` (D-03). Match existing prefix-bracket convention.
- **Asyncio subprocess** — `create_subprocess_exec(*argv, stdout=PIPE, stderr=STDOUT)`. Background variant uses the same call but does NOT `wait_for(communicate())`; instead, streams via `proc.stdout.read()` chunks into the disk tail file (a background asyncio task per job).
- **30s timeout via `wait_for`** — for foreground `shell_run`. Background watchdog uses an analogous `asyncio.wait_for` on a `proc.stdout` read with `no_output_deadline_s=30.0`.
- **Reap-on-exit registry** — `_SUBPROCESSES` list; T5 adds `_JOBS: dict[handle, JobRecord]`.
- **Flat telemetry dicts** — `tool.call` / `tool.result` for tool invocations; `shell.background.reap` for lifecycle reap (D-08).

### Integration Points

- `voss/harness/tools.py` — three new tool descriptors + registrations.
- `voss/harness/lifecycle.py` — `_JOBS` registry, `register_job`, `reap_jobs` (separate from `reap_all` for distinct watchdog semantics).
- `voss/harness/sandbox.py` — unchanged (allowlist reused).
- `voss/harness/permissions.py` — `SHELL` set extended.
- `voss/harness/tui/permissions_bridge.py` — approval prompt extended for new tools.
- `voss/harness/cli.py` — `voss jobs` subcommand + `--keep-logs` flag.
- `voss/harness/recorder.py` — potentially extend `VALIDATE_TOOLS` (researcher confirms).
- `voss/harness/cognition.py` — update guidance text mentioning shell tools.

### Anti-patterns to Avoid

- **Reusing `_SUBPROCESSES` for jobs** — different lifecycle (jobs may exceed 5s reap deadline; jobs may be explicitly signaled mid-life; jobs have watchdog timers). Separate registry.
- **TTY inheritance** — `create_subprocess_exec` defaults are correct (no TTY); do NOT add `start_new_session=True` without verifying signal propagation.
- **Per-binary timeout overrides** — rejected in Area 4 (config drift, complexity).
- **Wall-clock `since_ms` semantics** — rejected in Area 3 (sidecar `.idx` file complexity, per-flush IO).

</code_context>

<specifics>
## Specific Ideas

- **Handle slug `bg-NNN` reads well in `tool.call`/`tool.result` recorder logs** — `bg-007` is a stable string the agent can quote back accurately, unlike a 36-char UUID or a 5-digit PID that may collide cross-session.
- **Disk-only buffer matches Voss's "inspectable" core value** — `.voss-cache/jobs/<session_id>/<handle>.log` is a single `tail -f`-able artifact for the human; no in-memory state to dump.
- **Non-blocking monitor + opaque cursor is the laziest correct surface** — no background poller, no sidecar index, no timer juggling. The LLM does the polling implicitly through tool turns.
- **Same allowlist + lifecycle watchdog over stricter allowlist** — orphan blast radius is bounded by reap (5s SIGTERM→SIGKILL), not by enumerating "background-safe" binaries. Two-list maintenance is a known anti-pattern (T3 D-15 single-source-of-truth precedent).
- **`shell.background.reap` is the only NEW telemetry event** — start/normal-exit ride existing `tool.call`/`tool.result`; reap is the lifecycle event that has no tool envelope.

</specifics>

<deferred>
## Deferred Ideas

- **Cross-session `voss jobs` inventory** — listing jobs from prior sessions. No use case yet. Future phase if forensics on resume becomes a recurring need.
- **`--keep-logs` per-tool override** — keep specific handles' logs even when global `--keep-logs` is false. Defer until someone asks.
- **`shell_signal` HUP / USR1 / USR2 support** — ROADMAP locks INT/TERM only. Custom signals are an advanced use case (e.g., dev-server hot reload). M14 territory if surfaced there.
- **TUI bottom-pane status strip for running jobs** — explicitly M14, not T5. T5 leaves the data shape (`voss jobs --json`) intact for M14 to consume.
- **In-memory ring buffer mirror** — rejected in D-02. Revisit if `shell_monitor` latency on log-file reads becomes a measurable hot spot (unlikely under typical agent turn cadence).
- **Per-binary runtime override (`pytest=300s`)** — rejected in D-05 ("Same allowlist + per-binary timeout"). Adds config drift. Revisit if real workloads regularly hit the 30s no-output watchdog on legitimate long-running operations.
- **Adopting `subprocess` `creationflags=DETACHED_PROCESS` on Windows** — researcher confirms whether `asyncio.create_subprocess_exec` already gives correct detach semantics on Windows for our reap pattern; otherwise add as Windows-only branch.
- **`shell_run_background` cmd interpolation / templating** — out of scope. Allowlist gates raw command string; no Voss-side templating.
- **Job priority / nice / cpuset** — out of scope for v0.2. Revisit when multi-tenant agent workloads emerge.

</deferred>

---

*Phase: T5-shell-ergonomics*
*Context gathered: 2026-05-16 via /gsd:discuss-phase T5*
*Next step: /gsd:plan-phase T5 — research and plan*
