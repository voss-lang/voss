# Phase M14: Long-running Tasks + Watch (CAPS-01e) - Context

**Gathered:** 2026-05-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Headless file-watch capability layered on the T5 background job engine: a `watchdog`-backed watcher, an `fs_watch` agent tool emitting recorder events, a `voss watch <command>` CLI that re-runs on change, and a `--daemon` opt-in that genuinely survives session exit. No TUI, no M10 hookback this phase.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**5 requirements are locked.** See `M14-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `M14-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- `watchdog` added as a pinned dependency
- File-watch backend — glob registration, debounce/coalescing, lifecycle-managed with T5 `_JOBS`
- `fs_watch` agent tool + recorder-stream event emission + cursor-based incremental read
- `voss watch <command>` top-level CLI with `--glob` and command re-run on change
- `--daemon` opt-in flag (survives session exit); default = unchanged T5 always-reap
- macOS + Linux verified on CI; Windows best-effort

**Out of scope (from SPEC.md):**
- M9 TUI bottom-pane status strip — deferred (M9-shell extension; headless-only this phase)
- M10 `code_refresh` file-watch hookback — deferred (separate wiring phase; M10 deferral stays open)
- Re-implementing the T5 background job engine — reuse `_JOBS`/lifecycle/reap unchanged
- Distributed task scheduling — ROADMAP out-of-scope
- Cron-like recurring/scheduled tasks — ROADMAP out-of-scope
- Notification delivery (push/email) — ROADMAP out-of-scope

</spec_lock>

<decisions>
## Implementation Decisions

### File-watch backend
- **D-01 (auto-resolved):** Debounce/coalescing window defaults to **200ms**, configurable via `fs_watch(globs, debounce_ms=200)`. Rationale: editor saves emit modify+modify+close storms; 200ms is the watchdog-ecosystem norm balancing responsiveness vs. event-storm collapse. SPEC WATCH-01 acceptance ("exactly one coalesced event within the window") is satisfied by collapsing all events for a given path within `debounce_ms` of the first into one.
- **D-04 (confirmed):** Live watchers live in a **new sibling `_WATCHERS` registry** in `lifecycle.py`, parallel to `_JOBS` — NOT shoehorned into `JobRecord`. Rationale: the watchdog `Observer` is a thread with no pid/proc; `JobRecord` requires `pid`. This mirrors the existing lifecycle.py precedent (the in-code comment already justifies `_JOBS` being separate from `_SUBPROCESSES` "because background jobs have distinct reap semantics" — watchers are even more distinct: thread not process, stopped via `Observer.stop()`/`join()` not signals). `_WATCHERS` gets its own teardown pass added to the existing session-exit reap path.

### fs_watch tool + recorder events
- **D-02 (auto-resolved):** Cursor API is an **exact mirror of `shell_monitor`/`monitor_job`**. Change events are appended as JSONL lines to `.voss-cache/watch/<session_id>/<handle>.log` (parallels T5's `.voss-cache/jobs/<session>/<handle>.log`). A `fs_watch_poll(handle, since_ms=0)` tool reuses the `monitor_job` opaque-byte-cursor reader verbatim (`[cursor N][running] <new lines>`). No new cursor mechanic invented. Planner should factor the byte-cursor log reader so `fs_watch_poll` and `shell_monitor` share it rather than copy it.
- `fs_watch(globs)` registers the watcher and returns a `watch-NNN` handle (mirror T5 `_next_handle` per-session counter). Tool is read-only/non-mutating (parity with `shell_monitor` classification; subject to T5 permission-tier rules).

### voss watch CLI + daemon
- **D-03 (confirmed): Hybrid daemon detach.** Non-daemon `voss watch <command>` = in-process watchdog `Observer` + child spawned via T5 `register_job`; reaped on session exit by the unchanged T5 path. `voss watch --daemon <command>` = re-spawn self as a **detached worker subprocess** (`start_new_session=True` / new process group, no inherited TTY — reuse T5's `use_process_group` infra) that is **NOT** registered in `_JOBS`/`_WATCHERS`, so the session-exit reap pass cannot touch it. Only `--daemon` pays the subprocess-detach cost; non-daemon stays cheap in-process. This is the only path that genuinely satisfies WATCH-04 (an in-process Observer thread dies with the Python process regardless of any flag).
- **Re-run on change:** before each re-execution the watcher TERMs the prior child (reuse `signal_job`/`_kill_tree` semantics) then re-spawns via `register_job`'s argv path. Shell allowlist (`shell_allowed` + `split_command`) applies to `<command>` exactly as in `shell_run_background`.
- CLI placement: new top-level `voss watch` subcommand (argparse subparser, sibling of `voss jobs` at `cli.py:2118`), distinct from the existing unrelated `logs watch` subcommand at `cli.py:2844`.

### Claude's Discretion
- Exact `_WATCHERS` record dataclass field set, the shared byte-cursor reader's module location, debounce timer implementation (per-path timer vs. single sweep), and detached-worker re-exec argv shape — all planner/researcher territory, constrained by the decisions above.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked requirements
- `.planning/phases/M14-long-running-tasks-watch-caps-01e/M14-SPEC.md` — Locked requirements (WATCH-01..05), boundaries, acceptance criteria. MUST read before planning.

### Phase definition & deferral provenance
- `.planning/ROADMAP.md` §"Phase M14: Long-running Tasks + Watch (CAPS-01e)" (~line 615) — goal, headline deliverables, cross-cutting constraints, out-of-scope
- `.planning/ROADMAP.md` line ~500 — "Project index … No file-watch (deferred to M14)" (the M10 deferral M14's WATCH-01 unblocks but does NOT wire this phase)
- `.planning/ROADMAP.md` line ~958 — "This is the headless half of M14 (file-watch). M14 layers `watchdog` on top" (T5↔M14 split provenance)
- `.planning/REQUIREMENTS.md` line ~1473 — `M14 | WATCH-01..0N | TBD by M14-SPEC.md` (now satisfied by SPEC.md)

### T5 reuse anchors (the engine M14 builds on, do not modify)
- `voss/harness/lifecycle.py` — `_JOBS` registry, `JobRecord`, `register_job`, `reap_jobs`, `signal_job`, `monitor_job`, `_kill_tree`, `use_process_group`/`start_new_session` infra, the "separate registry / distinct reap semantics" precedent comment
- `voss/harness/tools.py` ~line 180–250 — `shell_run_background`/`shell_monitor`/`shell_signal` (allowlist gate + cursor-read patterns to mirror for `fs_watch`/`fs_watch_poll`)
- `voss/harness/cli.py:2118` `jobs_cmd` — `voss jobs` subparser pattern to mirror for `voss watch`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lifecycle.register_job(...)` (proc and argv paths): spawn + supervise the `voss watch` child and its re-runs without new process plumbing.
- `lifecycle.monitor_job(handle, since_ms)`: opaque byte-cursor log reader — factor shared, drive both `shell_monitor` and the new `fs_watch_poll`.
- `lifecycle.signal_job` / `_kill_tree` / `use_process_group`: TERM-prior-child-before-re-run, and the detached-worker process-group basis for `--daemon`.
- `shell_allowed` + `split_command` (tools.py): identical allowlist gate for `voss watch <command>`.
- `_next_handle` per-session counter + `.voss-cache/<kind>/<session>/<handle>.log` layout: reuse for `watch-NNN` + `.voss-cache/watch/...`.

### Established Patterns
- "Separate registry per distinct reap semantics" (lifecycle.py comment) — directly licenses the `_WATCHERS` sibling registry (D-04).
- Cursor returned as opaque `since_ms` byte offset, non-blocking poll — `fs_watch_poll` must not invent a different contract (D-02).
- Background work reaped on session exit unless explicitly escaping the registry — `--daemon` escapes by not registering (D-03).

### Integration Points
- New `_WATCHERS` teardown call added to the existing session-exit reap path alongside `reap_jobs()`.
- New `fs_watch` / `fs_watch_poll` registered in the toolset factory next to `shell_run_background` et al. (same permission classification as `shell_monitor`).
- New `voss watch` argparse subparser registered next to `jobs_cmd` in `cli.py`.

</code_context>

<specifics>
## Specific Ideas

- `fs_watch_poll` and `shell_monitor` must share one byte-cursor reader, not duplicate it (explicit user-grounded simplicity constraint from the cursor-API decision).
- TUI status strip and M10 `code_refresh` hookback are M14's eventual vision but are explicitly OUT for this phase — do not let the planner pull them in.

</specifics>

<deferred>
## Deferred Ideas

- **M9 TUI bottom-pane status strip** (running jobs / last-tick / recent errors) — future phase; requires M9 shell extension. Captured in SPEC out-of-scope.
- **M10 `code_refresh` file-watch hookback** (live index updates subscribing to fs_watch events) — future wiring phase; the M10 file-watch deferral stays open. WATCH-01 makes it *possible* but does not implement it.
- **Daemon management surface** (list/stop detached daemons across sessions) — not in M14; only the `--daemon` spawn + survival is in scope. Note for roadmap backlog if a `voss watch --list/--stop` need surfaces.

None of the above were folded — discussion stayed within the SPEC boundary.

</deferred>

---

*Phase: M14-long-running-tasks-watch-caps-01e*
*Context gathered: 2026-05-18*
