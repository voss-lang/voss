# Phase M14: Long-running Tasks + Watch (CAPS-01e) — Specification

**Created:** 2026-05-18
**Ambiguity score:** 0.16 (gate: ≤ 0.20)
**Requirements:** 5 locked

## Goal

Voss gains a `watchdog`-backed file-watch backend exposed as an `fs_watch` agent tool that emits change events into the recorder stream, plus a `voss watch <command>` CLI that re-runs a command on watched-file change with an opt-in `--daemon` flag — built on the existing T5 background job engine, headless-only this phase.

## Background

T5 already shipped the background job engine: `JobRecord` + `_JOBS` registry (`voss/harness/lifecycle.py`), `shell_run_background`/`shell_monitor`/`shell_signal` tools (`voss/harness/tools.py`), `reap_jobs`/`signal_job`, SIGTERM→SIGKILL reap, 30s/100MB watchdogs, and the `voss jobs` CLI (`cli.py:2118`). M14 does **not** rebuild any of that — it layers file-watch on top.

No `watchdog` dependency exists anywhere in the codebase. `code_refresh(paths)` in `voss/harness/code/service.py:262` is on-demand-only — ROADMAP.md:500 explicitly defers file-watch to M14. No top-level `voss watch` command exists (only an unrelated `logs watch` subcommand). The M9 TUI shell (`voss/harness/tui/app.py` + widgets) has no job status strip.

Per the round-1/2 interview, **this phase is headless-only**: the M9 TUI bottom-pane status strip and the M10 `code_refresh` file-watch hookback are both explicitly deferred to a follow-up phase.

## Requirements

1. **File-watch backend (watchdog)**: A `watchdog`-backed watcher registers on glob patterns and emits coalesced change events.
   - Current: No `watchdog` dependency; zero file-watch capability; `code_refresh` is on-demand only
   - Target: A watchdog-backed watcher registers on glob patterns, coalesces rapid successive changes within a bounded debounce window, and is lifecycle-managed alongside the T5 `_JOBS` registry (reaped on session exit by default)
   - Acceptance: Editing a file matching a registered glob produces exactly one coalesced change event within the debounce window; editing a non-matching file produces zero events

2. **`fs_watch` agent tool + recorder events**: An agent tool registers watchers; change events land in the recorder stream and are readable incrementally.
   - Current: No `fs_watch` tool; the recorder stream carries shell/job output only
   - Target: `fs_watch(globs)` registers a watcher; fs-change events are emitted into the recorder stream; the agent reads incremental events via a cursor (same pattern as T5 `shell_monitor`)
   - Acceptance: One agent turn calls `fs_watch`, a watched file is edited, and a later turn reads the change event via the cursor without re-registering the watcher

3. **`voss watch <command>` CLI re-run on change**: A top-level CLI runs a command and re-executes it on watched-file change.
   - Current: No top-level `voss watch`; only the unrelated `logs watch` subcommand exists
   - Target: `voss watch <command> [--glob ...]` runs the command, re-executes it when a watched file changes, persists across session turns, and uses the T5 job engine for the child process; the shell allowlist still applies to `<command>`
   - Acceptance: `voss watch 'pytest -q'` re-executes the command after a watched file changes; the re-run output is observable; Ctrl-C / session exit reaps the watcher and its child (non-daemon path)

4. **Daemon opt-in survives session exit**: An opt-in flag detaches a watch so it survives session exit; default behavior is unchanged T5 reap.
   - Current: T5 always reaps background jobs on session exit
   - Target: A `--daemon` opt-in flag on `voss watch` detaches the watcher + child so it survives session exit; without the flag, T5 reap semantics apply unchanged
   - Acceptance: A `--daemon` watch is still running after the session exits; an identical non-daemon watch is reaped with T5-parity timing (SIGTERM ≤ 2s, SIGKILL ≤ 5s)

5. **Cross-platform watcher**: The watchdog backend functions on macOS and Linux; Windows is best-effort and non-gating.
   - Current: N/A — no watcher exists
   - Target: The watchdog backend works on macOS and Linux with no platform-specific code path required for those two; Windows is best-effort and documented as non-gating
   - Acceptance: The WATCH-01/WATCH-02 event test passes on macOS and Linux CI; a Windows failure is non-gating and explicitly documented

## Boundaries

**In scope:**
- `watchdog` added as a pinned dependency
- File-watch backend — glob registration, debounce/coalescing, lifecycle-managed with T5 `_JOBS`
- `fs_watch` agent tool + recorder-stream event emission + cursor-based incremental read
- `voss watch <command>` top-level CLI with `--glob` and command re-run on change
- `--daemon` opt-in flag (survives session exit); default = unchanged T5 always-reap
- macOS + Linux verified on CI; Windows best-effort

**Out of scope:**
- M9 TUI bottom-pane status strip — deferred to a follow-up phase (this phase is headless-only; M9 strip is an M9-shell extension)
- M10 `code_refresh` file-watch hookback — deferred (separate wiring phase; the M10 file-watch deferral stays open)
- Re-implementing the T5 background job engine — already shipped; M14 reuses `_JOBS`/lifecycle/reap unchanged
- Distributed task scheduling — ROADMAP out-of-scope
- Cron-like recurring/scheduled tasks — ROADMAP out-of-scope (separate concern)
- Notification delivery (push/email/etc.) — ROADMAP out-of-scope

## Constraints

- File-watch backend MUST use the `watchdog` Python lib (cross-platform), added as a pinned dependency.
- MUST build on the T5 `_JOBS`/lifecycle reap machinery — no fork or duplicate of the background job engine.
- Debounce window MUST be bounded and configurable; the exact value is a discuss-phase HOW decision. The SPEC requirement is falsifiable as "exactly one coalesced event within the window."
- The `--daemon` path MUST NOT regress the T5 always-reap default for non-daemon jobs/watches.
- The shell allowlist (T5 constraint) still applies to `voss watch <command>`.
- Background watches do not inherit the agent's TTY (T5 constraint inherited).

## Acceptance Criteria

- [ ] `watchdog` is added as a pinned dependency and importable
- [ ] Editing a file matching a registered glob yields exactly one coalesced recorder event within the debounce window
- [ ] Editing a file NOT matching any registered glob yields zero events
- [ ] `fs_watch(globs)` registered in one turn; the change event is readable via the cursor in a later turn without re-registration
- [ ] `voss watch 'pytest -q'` re-executes the command when a watched file changes
- [ ] A non-daemon `voss watch` is reaped on session exit (SIGTERM ≤ 2s / SIGKILL ≤ 5s, T5 parity)
- [ ] A `--daemon voss watch` is still running after session exit
- [ ] The WATCH event test is green on macOS and Linux CI; a Windows failure is non-gating and documented
- [ ] The shell allowlist is enforced for `voss watch <command>`

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                              |
|--------------------|-------|------|--------|----------------------------------------------------|
| Goal Clarity       | 0.88  | 0.75 | ✓      | Deliverable set + API shape locked, TUI/M10 deferred |
| Boundary Clarity   | 0.85  | 0.70 | ✓      | T5/M14 non-overlap explicit; 6 out-of-scope items   |
| Constraint Clarity | 0.80  | 0.65 | ✓      | watchdog lib, T5 reuse, daemon-default-safe         |
| Acceptance Criteria| 0.78  | 0.70 | ✓      | 9 pass/fail criteria; debounce numeric → discuss    |
| **Ambiguity**      | 0.16  | ≤0.20| ✓      |                                                    |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective           | Question summary                          | Decision locked                                                                 |
|-------|-----------------------|-------------------------------------------|---------------------------------------------------------------------------------|
| 1     | Researcher            | M14's irreducible new core over T5?       | All four named (file-watch, voss watch, TUI strip, M10 hookback) as M14 vision   |
| 1     | Researcher            | Headless-first vs TUI this phase?          | Headless-only this phase                                                          |
| 1     | Researcher            | Daemon opt-in flag in scope?               | In scope — `--daemon` opt-in ships in M14                                          |
| 2     | Researcher/Simplifier | Which headless deliverables ship now?      | File-watch + `voss watch` + daemon only; TUI strip AND M10 hookback both deferred  |
| 2     | Simplifier            | How does file-watch surface to the agent?  | `fs_watch` tool + recorder events (cursor read), plus `voss watch` CLI            |
| 2     | Simplifier            | Irreducible falsifiable proof?             | Edit→event observed, voss watch re-runs, daemon survives exit, cross-platform CI  |

---

*Phase: M14-long-running-tasks-watch-caps-01e*
*Spec created: 2026-05-18*
*Next step: /gsd:discuss-phase M14 — implementation decisions (debounce ms, fs_watch cursor API, daemon detach mechanism, watchdog backend wiring)*
