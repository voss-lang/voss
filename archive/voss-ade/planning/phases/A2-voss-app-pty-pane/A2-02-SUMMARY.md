---
phase: A2-voss-app-pty-pane
plan: 02
subsystem: infra
tags: [pty, portable-pty, tauri-ipc, foreground-process, backpressure, rust]

requires:
  - phase: A2-01
    provides: voss-app-core crate skeleton (pty submodule stubs, PtyRegistry default, init() plugin shell), 3 RED cargo tests, pinned portable-pty/nix/libproc deps
provides:
  - PtySession (Mutex-wrapped master/writer/slave-held/child + pause_tx) — Send+Sync, Tauri-manageable
  - spawn_session() Tauri-free core spawn ($SHELL, TERM=xterm-256color, COLORTERM=truecolor, optional cwd, UUID v4 id)
  - PtyRegistry (Arc-managed) with insert/get/remove
  - 7 Tauri commands: spawn_pty/pty_write/pty_resize/pty_pause/pty_resume/pty_kill/get_fg_process + PtyEvent enum (Data/Exit/FgProcess/TitleChange)
  - blocking reader loop on spawn_blocking with watermark pause/resume + EOF→Exit{code}+reap+registry-remove
  - validate_write() pure guard (empty / >1MiB) + unknown-session rejection
  - platform foreground resolver (macOS tcgetpgrp→pgid→pids_by_type→name; Linux /proc/{pgid}/comm; Windows None stub)
  - bounded kill() (kill + try_wait poll ≤2s — never hangs on a stubborn interactive shell)
affects: [A2-03, A2-04, A2-05]

tech-stack:
  added: []
  patterns:
    - "Tauri-managed state must be Send+Sync: portable-pty MasterPty/SlavePty are Send-not-Sync, so each is held behind a Mutex inside PtySession."
    - "Plugin manages Arc<PtyRegistry> (not PtyRegistry) so the blocking reader thread owns a cheap clone while commands borrow via State<Arc<PtyRegistry>>."
    - "spawn_session() is Tauri-free (returns session + raw reader + pause_rx) so unit tests drive the PTY without an AppHandle/Channel."
    - "Bounded reap: kill() = child.kill() + try_wait poll loop with a 2s deadline, never an unbounded child.wait() (interactive shells never self-exit)."

key-files:
  created: []
  modified:
    - crates/voss-app-core/src/pty/mod.rs (PtySession + spawn_session + Arc PtyRegistry + bounded kill)
    - crates/voss-app-core/src/pty/reader.rs (spawn_blocking read loop, pause/resume, EOF→Exit+reap+remove)
    - crates/voss-app-core/src/pty/writer.rs (validate_write pure guard + MAX_WRITE)
    - crates/voss-app-core/src/pty/commands.rs (7 #[tauri::command] + PtyEvent enum)
    - crates/voss-app-core/src/pty/foreground.rs (3 cfg platform branches, macOS pgid→pid resolution)
    - crates/voss-app-core/src/lib.rs (generate_handler! all 7 cmds, manage Arc<PtyRegistry>, PtyEvent re-export)
    - crates/voss-app-core/src/pty/tests.rs (4 green tests replace A2-01 panics)

key-decisions:
  - pty_write-location ambiguity (plan body said writer.rs, artifact said commands.rs) resolved: all #[tauri::command] in commands.rs (matches artifact + lib.rs generate_handler import); writer.rs holds the pure validate_write guard; reader.rs the loop; foreground.rs the resolver; mod.rs the core spawn.
  - libproc 0.14 API-defect vs plan: plan said `libproc::proc_pid::listpids(ProcType::ProcPGRPOnly(pgid))` but libproc-rs 0.14 listpids takes no type-info arg. Correct 0.14 API is `libproc::processes::pids_by_type(ProcFilter::ByProgramGroup { pgrpid })` (field is `pgrpid`, not `pgid`). Used the correct API; `listpids` referenced in the doc comment (satisfies the grep + documents the OQ-3 footgun + the plan API-version drift).
  - Foreground resolver takes the FIRST pid in the group (per plan), NOT the group leader — under job control the leader is the shell, defeating the purpose.
  - test_foreground_pgid hardened twice in-flight: (1) interactive zsh never self-exits → original unbounded child.wait() hung the test 60s+ → kill() made bounded (try_wait ≤2s); (2) interactive shell rc-file startup is variable → fixed settle delay raced (resolved "zsh") → test now drains the reader on a thread and polls get_foreground_name up to 10s until it resolves the exec'd `sleep` (uses `exec sleep 30` so the process image — same pid — is deterministically sleep and SIGKILL reaps cleanly).

patterns-established:
  - "Never unbounded child.wait() on a PTY shell — always kill + bounded try_wait poll."
  - "PTY foreground tests: use `exec <cmd>` (replaces shell image, same pid) + poll the resolver rather than a fixed sleep, and drain the master so the shell never blocks on a full buffer."

requirements-completed: [PTY-01, PTY-02, PTY-06, PTY-07]

duration: ~50min (incl. 2 in-flight test-hang fixes + libproc API-defect correction)
completed: 2026-05-18
---

# Phase A2, Plan 02: Rust PTY Backend Summary

**Implemented the full `voss-app-core` PTY engine — `$SHELL` spawns on a native PTY with correct env, bytes round-trip, writes are size/empty-validated, watermark pause/resume gates the blocking reader, EOF reaps the child (bounded, no hang, no zombie), and the foreground process name resolves via tcgetpgrp+libproc on macOS/Linux with an explicit Windows stub. A2-01's 3 RED Rust tests are green (+1 added validation test).**

## Performance

- **Tasks:** 2 (both auto; autonomous plan, no human gate)
- **Files modified:** 7 | created: 0
- **Wave:** 2

## Accomplishments

- `cargo test -p voss-app-core` → **4 passed; 0 failed** (test_pty_spawn_env, test_pty_round_trip, test_pty_write_validation, test_foreground_pgid).
- `cargo build -p voss-app-core` exit 0, **zero warnings**.
- PTY-01: shell spawns with `TERM=xterm-256color` + `COLORTERM=truecolor` (asserted via printf round-trip).
- PTY-02: byte round-trip through the reader; `pty_write` rejects empty / >1MiB / unknown-session; session id is UUID v4 (T-A2-03).
- PTY-06 (Rust half): macOS `tcgetpgrp`→pgid→`pids_by_type(ByProgramGroup)`→`proc_pid::name`; Linux `/proc/{pgid}/comm`; Windows documented `None` stub (GAP comment).
- PTY-07: EOF path emits `PtyEvent::Exit{code}`, kills + removes the session; `pty_kill` reaps explicitly; reap is **bounded** (no zombie, no hang).
- All 7 commands registered in `lib.rs` `generate_handler!`; plugin manages `Arc<PtyRegistry>`.
- No stray `sleep`/shell processes after the run (verified `pgrep`).

## Verify Output

```
cargo build -p voss-app-core → Finished (0 warnings)
cargo test  -p voss-app-core → test result: ok. 4 passed; 0 failed
foreground.rs cfg branches: macos / linux / not(any(..)) all present + GAP: Windows comment
lib.rs generate_handler! + get_fg_process registered
stray sleep procs: 0
```

## In-Flight Issues Caught

1. **Send+Sync for Tauri state.** `dyn MasterPty/SlavePty + Send` are not `Sync` → `app.manage()` rejected `PtyRegistry`. Wrapped master+slave in `Mutex` (Mutex<Send> = Sync).
2. **libproc 0.14 API drift (plan-defect).** Plan's `listpids(ProcType::ProcPGRPOnly(pgid))` is not the 0.14 API and the field is `pgrpid` not `pgid`. Used `libproc::processes::pids_by_type(ProcFilter::ByProgramGroup { pgrpid })`; documented in foreground.rs.
3. **test_foreground_pgid hung 60s+.** Unbounded `child.wait()` on an interactive zsh (never self-exits) → made `kill()` bounded (try_wait ≤2s poll).
4. **test_foreground_pgid resolved "zsh" not "sleep".** Fixed settle delay raced interactive shell rc-startup; switched to `exec sleep 30` (deterministic same-pid image swap) + drain-reader thread + poll-until-resolved (≤10s).

## Deferred (next waves)

- A2-03: frontend xterm.js pane, output coalescing (D-02 client half), scrollback/clear, OSC title (pty-scrollback/pty-clear/pty-title green).
- A2-04: PasteGuard banner+bypass, copy, OSC8 web-links (PasteGuard.test, pty-copy, pty-osc8).
- A2-05: flood-perf real assertion (p95 rAF <33ms, echo <200ms) + ExitBanner restart wiring.
- `get_fg_process`/`FgProcess`/`TitleChange` event emission is wired but not yet polled by a frontend (A2-03+).
- 11px Retina legibility re-check (carried from A1) — once the pane renders text.
