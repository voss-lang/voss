---
phase: A2-voss-app-pty-pane
plan: 02
type: execute
wave: 2
depends_on: ["A2-01"]
files_modified:
  - crates/voss-app-core/src/pty/mod.rs
  - crates/voss-app-core/src/pty/reader.rs
  - crates/voss-app-core/src/pty/writer.rs
  - crates/voss-app-core/src/pty/foreground.rs
  - crates/voss-app-core/src/pty/commands.rs
  - crates/voss-app-core/src/pty/tests.rs
  - crates/voss-app-core/src/lib.rs
autonomous: true
requirements: [PTY-01, PTY-02, PTY-06, PTY-07]
user_setup: []

must_haves:
  truths:
    - "portable-pty spawns $SHELL with TERM=xterm-256color and COLORTERM=truecolor"
    - "Bytes written via pty_write are echoed back through the Channel (round-trip)"
    - "Shell exit emits a typed Exit event with the real exit code; child is reaped (no zombie)"
    - "pty_pause/pty_resume gate the blocking reader (watermark backpressure honored on the Rust side)"
    - "Foreground process name resolves via tcgetpgrp+libproc (macOS) / procfs (Linux); Windows returns None (stubbed)"
    - "Session IDs are UUID v4; pty_write rejects unknown session, empty payload, and >1MB payload"
  artifacts:
    - path: "crates/voss-app-core/src/pty/mod.rs"
      provides: "PtySession struct (master/writer/slave-held/child/pause_tx) + PtyRegistry"
      contains: "struct PtySession"
    - path: "crates/voss-app-core/src/pty/reader.rs"
      provides: "spawn_blocking PTY read loop with pause/resume + EOF→Exit"
      contains: "spawn_blocking"
    - path: "crates/voss-app-core/src/pty/commands.rs"
      provides: "spawn_pty, pty_write, pty_resize, pty_pause, pty_resume, pty_kill, get_fg_process Tauri commands + PtyEvent enum"
      exports: ["spawn_pty", "pty_write", "pty_resize", "pty_kill"]
    - path: "crates/voss-app-core/src/pty/foreground.rs"
      provides: "platform-conditional foreground process name resolver"
      contains: "tcgetpgrp"
  key_links:
    - from: "crates/voss-app-core/src/pty/commands.rs"
      to: "portable_pty::native_pty_system"
      via: "spawn_pty openpty + CommandBuilder"
      pattern: "native_pty_system|openpty"
    - from: "crates/voss-app-core/src/pty/reader.rs"
      to: "tauri::ipc::Channel"
      via: "on_data.send(PtyEvent::Data)"
      pattern: "\\.send\\("
    - from: "crates/voss-app-core/src/lib.rs"
      to: "pty::commands"
      via: "tauri::generate_handler! registration"
      pattern: "generate_handler"
---

<objective>
Implement the Rust PTY backend in `voss-app-core`: spawn `$SHELL` on a native PTY,
stream output to the frontend over a Tauri `Channel<PtyEvent>`, accept input, resize,
detect shell exit, expose watermark pause/resume, and resolve the foreground process
name for the Variant B header.

Purpose: This is the engine half of the pane. It satisfies PTY-01 (spawn+env), PTY-02
(bidirectional stream — Rust side), the Rust half of PTY-06 (pgid foreground fallback),
and PTY-07 (exit detection + reap). The D-02 flood contract's server-side half
(backpressure pause/resume) lives here; the frontend coalescing half is A2-03.

Output: Fully implemented `pty/` module turning the three red Rust tests from A2-01 green.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/A2-voss-app-pty-pane/A2-CONTEXT.md
@.planning/phases/A2-voss-app-pty-pane/A2-RESEARCH.md
@.planning/phases/A2-voss-app-pty-pane/A2-PATTERNS.md
@.planning/phases/A2-voss-app-pty-pane/A2-VALIDATION.md
@crates/voss-bridge/src/jsonrpc.rs
@crates/voss-bridge/src/framing.rs
@crates/voss-render/src/ndjson.rs

<interfaces>
<!-- Conceptual transfer anchors (A2-PATTERNS.md). These are STRUCTURE analogs, not -->
<!-- copy targets. Read the cited line ranges in the @-referenced source files. -->

PtySession struct shape (A2-PATTERNS.md mod.rs section, mirrors voss-bridge PyBridge child-hold):
  id: uuid::Uuid
  master: Box<dyn portable_pty::MasterPty + Send>
  writer: Mutex<Box<dyn std::io::Write + Send>>
  _slave: Box<dyn portable_pty::SlavePty + Send>   // HELD ALIVE (Pitfall 6, Windows)
  child:  Mutex<Box<dyn portable_pty::Child + Send>>
  pause_tx: tokio::sync::mpsc::Sender<bool>
  shell_name: String
  cwd: std::path::PathBuf

PtyEvent (A2-PATTERNS.md commands.rs section — serde-tagged like ndjson "type" discriminant):
  #[derive(serde::Serialize, Clone)]
  #[serde(tag = "type", rename_all = "snake_case")]
  enum PtyEvent { Data{bytes:Vec<u8>}, Exit{code:i32}, FgProcess{name:String} }

Tauri command signatures (A2-RESEARCH.md Pattern 1 + A2-PATTERNS.md commands.rs):
  spawn_pty(on_data: Channel<PtyEvent>, rows:u16, cols:u16, cwd: Option<String>,
            state: State<'_, PtyRegistry>) -> Result<String, String>   // returns UUID
  pty_write(session_id:String, data:Vec<u8>, state) -> Result<(),String>
  pty_resize(session_id:String, rows:u16, cols:u16, state) -> Result<(),String>
  pty_pause(session_id:String, state) -> Result<(),String>
  pty_resume(session_id:String, state) -> Result<(),String>
  pty_kill(session_id:String, state) -> Result<(),String>
  get_fg_process(session_id:String, state) -> Result<Option<String>,String>

Error convention (A2-PATTERNS.md §Rust Error Convention): internal fns return
  anyhow::Result; #[tauri::command] maps with .map_err(|e| e.to_string()).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: PtySession + spawn/write/resize/backpressure + exit reap</name>
  <files>crates/voss-app-core/src/pty/mod.rs, crates/voss-app-core/src/pty/reader.rs, crates/voss-app-core/src/pty/writer.rs, crates/voss-app-core/src/pty/commands.rs, crates/voss-app-core/src/lib.rs</files>
  <read_first>
    - crates/voss-bridge/src/jsonrpc.rs (PyBridge: spawn → hold child handles → Mutex<Option<..>> → teardown — the lifecycle analog, A2-PATTERNS.md lines 108-156)
    - crates/voss-bridge/src/framing.rs (read-loop EOF/error structure — A2-PATTERNS.md lines 161-204)
    - crates/voss-tools/src/shell_run.rs (input-validation-before-action + spawn pattern — A2-PATTERNS.md lines 210-243)
    - .planning/phases/A2-voss-app-pty-pane/A2-RESEARCH.md "## Pattern 1" (lines 262-338), "## Pattern 2" (lines 342-369), "## Pattern 4" (lines 436-485), Pitfalls 3/4/6 (lines 630-652)
  </read_first>
  <action>
    Implement `PtySession` in `mod.rs` with the struct shape from `<interfaces>`. Keep
    `_slave` as a held field (never dropped before child exit — Pitfall 6). Implement
    `PtyRegistry` as `Default` wrapping `Mutex<HashMap<String, Arc<PtySession>>>` with
    `insert`, `get`, `remove`.

    In `commands.rs` implement `spawn_pty`: call
    `portable_pty::native_pty_system().openpty(PtySize{rows,cols,0,0})`; build
    `CommandBuilder::new(std::env::var("SHELL").unwrap_or_else(|_| "/bin/sh".into()))`;
    `cmd.env("TERM","xterm-256color")`, `cmd.env("COLORTERM","truecolor")`; if `cwd`
    Some, `cmd.cwd(cwd)`. Spawn via `pair.slave.spawn_command(cmd)`. Generate
    `Uuid::new_v4()` session id (security: never sequential). `take_writer()` into the
    session; `try_clone_reader()` for the reader thread. Create the `pause_tx`/`pause_rx`
    `tokio::sync::mpsc::channel::<bool>(8)`. Register the session, then start the reader
    (Task spawns it). Return the UUID string.

    In `reader.rs` implement the read loop in `tokio::task::spawn_blocking` (Pitfall 3 —
    blocking read MUST NOT run on the async executor): 8192-byte buffer; before each
    read, non-blocking `pause_rx.try_recv()`; on `Some(true)` block on
    `pause_rx.blocking_recv()` until `Some(false)` (watermark backpressure, D-02 server
    half); `Ok(0)` ⇒ EOF: call `child.try_wait()`, send `PtyEvent::Exit{code}`, then
    `child.kill()` if still alive and remove the session from the registry (Pitfall 4 —
    no zombie); `Ok(n)` ⇒ `on_data.send(PtyEvent::Data{bytes})`; `Err` ⇒ break + Exit.

    In `writer.rs` implement `pty_write`: validation order copied from shell_run guard
    style — `if data.is_empty() return Err("empty payload")`;
    `if data.len() > 1_048_576 return Err("payload exceeds 1MB limit")`;
    `registry.get(&session_id).ok_or("unknown session")?`; lock the writer mutex,
    `write_all(&data)`, `flush()`, map IO errors to String. Implement `pty_resize`
    (`master.resize(PtySize{rows,cols,0,0})`), `pty_pause`/`pty_resume`
    (`pause_tx.send(true|false)`), `pty_kill` (`child.kill()` + registry remove).

    Wire all command symbols in `lib.rs` `tauri::generate_handler![ ... ]` and the
    `pub use` re-export list (replace the A2-01 placeholder).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && cargo test -p voss-app-core test_pty_spawn_env test_pty_round_trip 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `test_pty_spawn_env` is GREEN: spawning a PTY yields a child whose environment
      contains `TERM=xterm-256color` and `COLORTERM=truecolor` (assert via `env` echoed
      through the round-trip, or by inspecting the CommandBuilder env).
    - `test_pty_round_trip` is GREEN: writing `echo hi\n` via the write path and reading
      the Channel yields output containing `hi`.
    - `cargo build -p voss-app-core` exits 0 with no `spawn_blocking`-missing warnings.
    - `pty_write` returns `Err` for empty payload, for payload > 1_048_576 bytes, and for
      an unknown session id (assert all three in a Rust test).
    - Session id returned by `spawn_pty` parses as a UUID v4.
  </acceptance_criteria>
  <done>$SHELL spawns with correct env, bytes round-trip through the Channel, write is validated, backpressure pause/resume works, EOF reaps the child.</done>
</task>

<task type="auto">
  <name>Task 2: Foreground process detection + Exit event wiring + green tests.rs</name>
  <files>crates/voss-app-core/src/pty/foreground.rs, crates/voss-app-core/src/pty/commands.rs, crates/voss-app-core/src/pty/tests.rs</files>
  <read_first>
    - .planning/phases/A2-voss-app-pty-pane/A2-PATTERNS.md "### crates/voss-app-core/src/pty/foreground.rs" (lines 245-273) — the exact platform-conditional skeleton
    - .planning/phases/A2-voss-app-pty-pane/A2-RESEARCH.md "## Pattern 5" (lines 489-521) and "## Open Questions" item 3 (libproc pgid→pid resolution, lines 808-811)
    - .planning/phases/A2-voss-app-pty-pane/A2-RESEARCH.md "## Open Questions" item 2 (Windows stub, lines 803-806)
    - crates/voss-app-core/src/pty/tests.rs (the three red tests this task turns green)
  </read_first>
  <action>
    Implement `foreground.rs` with three cfg-gated `get_foreground_name(master_fd:
    RawFd) -> Option<String>`:
    - `#[cfg(target_os = "macos")]`: `nix::unistd::tcgetpgrp(master_fd)` → pgid; resolve
      pgid→pid via `libproc::proc_pid::listpids(ProcType::ProcPGRPOnly(pgid as u32))`,
      take the first pid, then `libproc::proc_pid::name(pid)` (RESEARCH OQ-3 — do NOT
      pass pgid directly to `name()`, that is the documented footgun).
    - `#[cfg(target_os = "linux")]`: `tcgetpgrp` → pgid → read
      `/proc/{pgid}/comm`, trim.
    - `#[cfg(not(any(target_os="macos", target_os="linux")))]`: return `None` (Windows
      stub per RESEARCH OQ-2 — explicit, documented gap; add a `// GAP: Windows
      foreground detection — owning future Windows phase` comment).

    Wire `get_fg_process` command to call `get_foreground_name` against the session's
    master fd (`master.as_raw_fd()` via the held master). Ensure the reader's EOF path
    (Task 1) sends `PtyEvent::Exit{code}` with the real `status.exit_code() as i32`
    (signal-killed → code as portable-pty reports it).

    Implement the three tests in `tests.rs` (replace A2-01 panics):
    - `test_pty_spawn_env` / `test_pty_round_trip`: real assertions (covered by Task 1
      logic — these may have gone green there; finalize their bodies here).
    - `test_foreground_pgid`: spawn a PTY, write a long-running command (e.g.
      `sleep 5\n`), allow a brief settle, call the platform `get_foreground_name`, assert
      the resolved name contains `sleep` (on macOS/Linux). On other targets assert it
      returns `None`. Reap the child at test end.
    Use `tempfile`/process cleanup so the test leaves no zombie.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && cargo test -p voss-app-core 2>&1 | tail -15 && cargo test -p voss-app-core 2>&1 | grep -qE 'test result: ok' && echo RUST_GREEN</automated>
  </verify>
  <acceptance_criteria>
    - `cargo test -p voss-app-core` exits 0 — `test_pty_spawn_env`, `test_pty_round_trip`,
      `test_foreground_pgid` all GREEN (the A2-01 red panics are gone).
    - `foreground.rs` contains a `#[cfg(target_os = "macos")]`, a
      `#[cfg(target_os = "linux")]`, and a `#[cfg(not(any(...)))]` branch returning
      `None` with the documented Windows-gap comment.
    - `get_fg_process` is registered in `lib.rs` `generate_handler!`.
    - macOS path uses `listpids`/pgid→pid resolution, NOT `name(pgid)` directly
      (grep: `listpids` present in foreground.rs).
    - No zombie processes after the test run (test reaps children).
  </acceptance_criteria>
  <done>Foreground detection resolves a real command name on macOS/Linux, Windows is an explicit stub, Exit carries the real code, all three Rust tests are green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| webview (untrusted JS) → Tauri command | session_id + byte payloads cross from renderer into native Rust |
| PTY child → reader thread | shell output bytes (incl. escape sequences) enter the process |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A2-03 | Spoofing | PTY session id guessing | mitigate | Session ids are `Uuid::new_v4()` (non-sequential, unguessable) per A2-PATTERNS.md §UUID Session IDs |
| T-A2-04 | Denial of Service | `pty_write` flood from frontend | mitigate | `pty_write` rejects empty payloads and payloads > 1MB; backpressure pause/resume bounds reader memory (A2-RESEARCH §Security Domain V5) |
| T-A2-05 | Elevation of Privilege | Arbitrary command via spawn_pty | accept | A2 spawns only `$SHELL` — no user-controlled command path exists in A2 (A2-RESEARCH §Known Threat Patterns); allowlist deferred to A3+ where pane shell becomes configurable |
| T-A2-06 | Tampering | Malicious VT/OSC escape sequences in PTY output | accept | Rust forwards raw bytes; xterm.js sanitizes VT internally (A2-03 boundary). OSC strings are never eval'd as code on the Rust side |
| T-A2-07 | Denial of Service | Zombie PTY child after pane/app close | mitigate | EOF path calls `try_wait()`+`kill()`; `pty_kill` reaps explicitly (Pitfall 4) |
</threat_model>

<verification>
- `cargo test -p voss-app-core` exits 0; all three A2-01 red tests are now green.
- `cargo build -p voss-app-core` exits 0.
- foreground.rs has all three platform branches; macOS uses pgid→pid resolution.
- `pty_write` validation rejects empty / >1MB / unknown-session (asserted in a test).
- All commands registered in `lib.rs` `generate_handler!`.
</verification>

<success_criteria>
- PTY-01: $SHELL spawns with TERM=xterm-256color + COLORTERM=truecolor.
- PTY-02 (Rust half): bidirectional byte stream over Channel, validated write.
- PTY-06 (Rust half): foreground name resolves via pgid on macOS/Linux.
- PTY-07 (Rust half): EOF emits Exit{code}; child reaped; pty_kill works.
</success_criteria>

<output>
Create `.planning/phases/A2-voss-app-pty-pane/A2-02-SUMMARY.md` when done
</output>
