# Phase A2: voss-app PTY Pane — Research

**Researched:** 2026-05-18
**Domain:** Tauri 2.x IPC + portable-pty (Rust) + xterm.js (Canvas renderer) + Solid.js lifecycle
**Confidence:** MEDIUM — stack is novel combination; individual components are well-documented

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: xterm.js **Canvas renderer** (not WebGL, not DOM). ⚠ See Critical Risk below.
- D-02: PTY output coalesced per animation frame; drop intermediate frames on flood; UI must never freeze. Hard testable contract.
- D-03: 60fps scroll target under normal load; sustained high-throughput keeps UI responsive.
- D-04/05: Multi-line paste → inline non-modal banner on ≥1 newline. Enter sends / Esc cancels / ⌘⇧V bypasses.
- D-06: ⌘C → selection→copy if selection exists, no-selection→SIGINT; configurable.
- D-07: Foreground-command detection = OSC 0/2 title (primary) + OS foreground-pgid poll fallback (tcgetpgrp + libproc macOS / procfs Linux / Windows job-object).
- Stack: Tauri 2.x, Solid, xterm.js, portable-pty (Rust). UI in `apps/voss-app/src/pane/`, PTY backend in `crates/voss-app-core`.
- Q2: Auto-launch `$SHELL` on pane open.
- Q3: Shell exit → `[exited N]` banner + Restart button, pane stays open.
- Env: `TERM=xterm-256color`, `COLORTERM=truecolor`.

### Claude's Discretion
- PTY ↔ webview transport mechanism (Channel vs event stream), encoding (binary vs base64), backpressure strategy.
- Scrollback search implementation — xterm `search` addon vs Rust-side mirrored buffer.
- Resize / SIGWINCH coordination — debounce policy during drag, PTY winsize ioctl timing.
- OSC 8 hyperlink + file-path detection — link activation (⌘+click) and file-path regex.

### Deferred Ideas (OUT OF SCOPE)
- Scrollback persistence across restart (A6).
- Sixel / inline images (L4+).
- Send-to-cell / terminal-output piping (L2).
- Per-pane shell override UI (A8).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PTY-01 | `portable-pty` spawns `$SHELL` with `TERM=xterm-256color`, `COLORTERM=truecolor` | CommandBuilder env API; native_pty_system(); blocking reader thread in tokio::task::spawn_blocking |
| PTY-02 | xterm.js renders PTY; bidirectional stream (stdin/stdout/stderr) | Tauri Channel API; xterm Terminal.write + Terminal.onData; UTF-8 byte transport |
| PTY-03 | 10k-line scrollback, `⌘F` search, `⌘⇧K` clear | @xterm/addon-search 0.16.0; Terminal.clear(); scrollback option |
| PTY-04 | Copy/paste: ⌘C selection-or-interrupt, ⌘V bracketed-paste safety, ⌘⇧V literal | customKeyEventHandler; onData intercept; bracketed-paste detection in onPaste handler |
| PTY-05 | OSC 8 hyperlinks (⌘+click). File-path detection → OS open | linkHandler option; @xterm/addon-web-links 0.12.0; Tauri shell.open |
| PTY-06 | Process indicator: foreground command from OSC 0 header | Terminal.onTitleChange; tcgetpgrp (nix 0.31.3) + libproc 0.14.11 fallback |
| PTY-07 | Shell exit → `[exited N]` banner + Restart | Child.wait() / try_wait() in PTY reader thread; Tauri event to frontend |
| PTY-08 | Alt-screen apps (vim/htop/less/tmux) render correctly | TERM=xterm-256color; xterm.js native alt-screen support; correct mouse reporting |
</phase_requirements>

---

## Summary

Phase A2 delivers a single terminal pane: a Rust `portable-pty` PTY backend piped through Tauri 2.x IPC to an xterm.js frontend in Solid. Three domains require deep attention: (1) the IPC transport — Tauri Channels are the correct mechanism for high-throughput streaming, and the planner must implement watermark-based backpressure on the Rust side; (2) the xterm.js version — a critical conflict exists between the locked D-01 decision (Canvas renderer) and the current npm landscape where `@xterm/addon-canvas@0.7.0` only supports `@xterm/xterm ^5.0.0`, while `@xterm/xterm 6.0.0` has removed the canvas addon entirely. **Pinning `@xterm/xterm` to `5.5.0` is required** to honor D-01; (3) the foreground-process detection (D-07) requires platform-conditional Rust code using `nix::unistd::tcgetpgrp` + `libproc` on macOS and `/proc/$(pty_pid)/stat` on Linux.

The D-02 flood contract (UI never freezes under `yes` or multi-MB `cat`) is met through a combination of Tauri Channel streaming (push model, ordered, binary-capable at ≥1024 bytes via fetch route), a per-animation-frame coalescing write buffer on the frontend, and a watermark-based pause/resume mechanism that signals the Rust reader when the write queue exceeds a high-water mark.

**Primary recommendation:** Pin `@xterm/xterm@5.5.0` + `@xterm/addon-canvas@0.7.0` to honor D-01. Use Tauri `Channel<Vec<u8>>` for Rust→frontend PTY output (push model). Use watermark-based backpressure (HIGH=100KB, LOW=10KB). Implement per-`requestAnimationFrame` coalescing on the frontend write path. Build the PTY reader loop in `tokio::task::spawn_blocking` with a `tokio::sync::mpsc` for sending chunks to the Tauri command handler.

---

## CRITICAL RISK: xterm.js Canvas Renderer vs v6.0.0

**Locked decision D-01 requires the Canvas renderer. The current npm `latest` tag (`@xterm/xterm@6.0.0`) has removed the canvas addon entirely.** [VERIFIED: npm registry + xterm.js GitHub release notes]

| Package | Latest stable | Canvas support |
|---------|--------------|----------------|
| `@xterm/xterm` | 6.0.0 | NO — canvas addon removed |
| `@xterm/xterm` | 5.5.0 | YES — `@xterm/addon-canvas@0.7.0` compatible |
| `@xterm/addon-canvas` | 0.7.0 | peerDeps: `@xterm/xterm ^5.0.0` |
| `@xterm/addon-webgl` | 0.19.0 | Recommended by v6 team |

**Resolution (planner MUST implement):** Pin `@xterm/xterm` to `5.5.0` in `package.json` using an exact version pin (`"@xterm/xterm": "5.5.0"`). Use `@xterm/addon-canvas@0.7.0`. This is the last v5 stable. v5 remains functional; it received fixes through late 2024/early 2025 based on release cadence. This pin must survive `pnpm update` — use an exact pin, not `^5.5.0`.

**Planner flag:** Surface this D-01 vs v6 conflict to the user at Wave 0 as a checkpoint. The user may choose to relax D-01 and adopt WebGL (which works with v6), or accept the v5 pin. Both are valid; the user must decide.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| PTY spawn + lifecycle | Rust (voss-app-core) | — | OS syscall; needs native PTY pair, env inheritance, SIGWINCH |
| PTY byte streaming to UI | Tauri IPC Channel | tokio async runtime | Ordered, high-throughput push from Rust to webview |
| Terminal emulation / rendering | xterm.js (Webview) | — | Full VT sequence parser, alt-screen, mouse reporting |
| Backpressure control | Rust reader thread | Frontend watermark | Rust pauses reads when frontend queue exceeds HIGH watermark |
| Foreground-process detection (OSC) | xterm.js onTitleChange | — | Passive: shells emit OSC 0 title changes |
| Foreground-process detection (poll) | Rust (voss-app-core) | — | tcgetpgrp + libproc; polled on interval when no OSC title |
| Copy/paste intercept | Solid pane component | xterm customKeyEventHandler | ⌘C/⌘V custom logic sits above xterm's default handlers |
| Multi-line paste banner | Solid pane component | — | Non-modal UI element rendered above xterm container |
| Scrollback search UI | Solid pane component | xterm SearchAddon | Addon does regex search; Solid renders the find bar |
| OSC 8 hyperlinks | xterm.js linkHandler | Tauri shell.open | xterm detects links; Tauri opens URL in OS browser |
| File-path detection | xterm.js custom linkProvider | Tauri shell.open | Regex on output text; click opens OS default app |
| Shell exit detection | Rust reader thread | — | Child.try_wait() in read loop; emit exit event via Channel |
| Resize / SIGWINCH | Solid (FitAddon) → Rust | — | FitAddon measures DOM → invoke resize command → PTY ioctl |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard | Source |
|---------|---------|---------|--------------|--------|
| `@xterm/xterm` | **5.5.0** (pinned) | Terminal emulator | Last v5 stable; required for D-01 canvas renderer | [VERIFIED: npm registry] |
| `@xterm/addon-canvas` | 0.7.0 | Canvas renderer (D-01) | Only renderer satisfying D-01; peerDep ^5.0.0 | [VERIFIED: npm registry] |
| `@xterm/addon-fit` | 0.11.0 | Resize to container | Standard fit-to-DOM utility | [VERIFIED: npm registry] |
| `@xterm/addon-search` | 0.16.0 | ⌘F scrollback search | Official search with decorations/regex/caseSensitive | [VERIFIED: npm registry] |
| `@xterm/addon-web-links` | 0.12.0 | URL auto-detection | Official URL linkProvider | [VERIFIED: npm registry] |
| `portable-pty` | 0.9.0 | PTY spawn + I/O | WezTerm's PTY crate; cross-platform; 6.2M downloads | [VERIFIED: crates.io] |
| `nix` | 0.31.3 | tcgetpgrp, SIGINT/SIGWINCH | Safe Unix syscall wrappers; D-07 fallback | [VERIFIED: crates.io] |
| `libproc` | 0.14.11 | macOS process name lookup | Provides proc_pidinfo/PROC_PIDTBSDINFO for pgid→name | [VERIFIED: crates.io] |
| `tauri` | 2.11.2 | App shell + IPC | Locked stack choice | [VERIFIED: crates.io] |
| `@tauri-apps/api` | 2.11.0 | Frontend IPC | Channel, invoke | [VERIFIED: npm registry] |
| `solid-js` | 1.9.13 | UI framework | Locked stack choice | [VERIFIED: npm registry] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `@xterm/addon-serialize` | 0.14.0 | Scrollback serialization | A6 (session persist) — stub in A2 |
| `@xterm/addon-unicode11` | 0.9.0 | Unicode 11 wide chars | Enable if CJK/emoji rendering required in A2 |
| `tokio` | 1.x (workspace) | Async runtime | Already in workspace; use for PTY reader task |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@xterm/addon-canvas` + v5.5 | `@xterm/addon-webgl` + v6.0 | WebGL performs better, v6 is current, but violates D-01; revisit at A3 |
| Tauri Channel | `app.emit` events | Events JSON-only, low throughput, unsuitable for PTY byte stream |
| `nix::tcgetpgrp` poll | procfs only | procfs is Linux-only; nix works on macOS + Linux |
| `tokio::task::spawn_blocking` for PTY reader | raw thread | spawn_blocking integrates with tokio runtime for inter-task channels |

**Installation (frontend):**
```bash
pnpm add @xterm/xterm@5.5.0 @xterm/addon-canvas@0.7.0 @xterm/addon-fit@0.11.0 @xterm/addon-search@0.16.0 @xterm/addon-web-links@0.12.0
```

**Installation (Rust — Cargo.toml additions for voss-app-core):**
```toml
[dependencies]
portable-pty = "0.9.0"
tauri = { version = "2", features = ["wry"] }
nix = { version = "0.31", features = ["signal", "term", "process"] }
tokio = { workspace = true }
serde = { workspace = true }
anyhow = { workspace = true }

[target.'cfg(target_os = "macos")'.dependencies]
libproc = "0.14"
```

---

## Package Legitimacy Audit

> slopcheck was unavailable at research time. All packages below are marked `[ASSUMED]` for age/downloads unless verified via crates.io API directly. The planner must add `checkpoint:human-verify` before install if slopcheck remains unavailable.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `@xterm/xterm` | npm | ~7 yrs (scoped since 2023) | Very high (VSCode uses it) | github.com/xtermjs/xterm.js | [ASSUMED] | Approved — VSCode/JetBrains ship this |
| `@xterm/addon-canvas` | npm | ~2.5 yrs | High | github.com/xtermjs/xterm.js | [ASSUMED] | Approved — same monorepo |
| `@xterm/addon-fit` | npm | ~2.5 yrs | High | github.com/xtermjs/xterm.js | [ASSUMED] | Approved — same monorepo |
| `@xterm/addon-search` | npm | ~2.5 yrs | High | github.com/xtermjs/xterm.js | [ASSUMED] | Approved — same monorepo |
| `@xterm/addon-web-links` | npm | ~2.5 yrs | High | github.com/xtermjs/xterm.js | [ASSUMED] | Approved — same monorepo |
| `portable-pty` | crates.io | ~7 yrs | 6.2M downloads | github.com/wez/wezterm | [ASSUMED] | Approved — WezTerm's own crate |
| `nix` | crates.io | ~10 yrs | Very high | github.com/nix-rust/nix | [ASSUMED] | Approved — standard Unix syscall crate |
| `libproc` | crates.io | ~5 yrs | Moderate | github.com/andrewdavidmackenzie/libproc-rs | [ASSUMED] | Approved — macOS-only, narrow scope |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none identified

*slopcheck was unavailable at research time. All packages above are tagged `[ASSUMED]`. The planner must gate each install behind a `checkpoint:human-verify` task before the install wave.*

---

## Architecture Patterns

### System Architecture Diagram

```
User keystrokes
    │
    ▼
┌────────────────────────────┐
│  Solid PaneComponent       │
│  ┌──────────────────────┐  │
│  │ xterm.js Terminal    │  │
│  │ (Canvas renderer)    │  │
│  │ onData(key) ──────────────────────────────┐
│  │ write(chunk) ◄─────────────────────────┐  │
│  └──────────────────────┘  │              │  │
│  customKeyEventHandler      │              │  │
│  (⌘C / ⌘V intercept)       │              │  │
│  PasteBanner overlay        │              │  │
│  FindBar overlay (⌘F)       │              │  │
└────────────────────────────┘              │  │
                                             │  │
         Tauri invoke('pty_write', data)     │  │
         ─────────────────────────────►      │  │
                                             │  │
┌────────────────────────────────────────────┼──┼─┐
│  Rust voss-app-core                        │  │  │
│                                            │  │  │
│  ┌─────────────────────┐  tokio mpsc       │  │  │
│  │  PTY Reader Thread  │──────────────►Channel.send(bytes)
│  │  (spawn_blocking)   │                   │  │  │
│  │  portable_pty read  │◄──────────────────┘  │  │
│  └─────────────────────┘  (backpressure       │  │
│           │                pause signal)      │  │
│           ▼                                   │  │
│  ┌─────────────────────┐                      │  │
│  │  PTY Writer         │◄─────────────────────┘  │
│  │  take_writer()      │  pty_write command       │
│  └─────────────────────┘                          │
│           │                                        │
│           ▼                                        │
│  ┌─────────────────────────────────────────────┐  │
│  │  portable_pty PTY pair                      │  │
│  │  native_pty_system().openpty(PtySize)        │  │
│  │  slave.spawn_command(CommandBuilder{$SHELL}) │  │
│  └─────────────────────────────────────────────┘  │
│                                                    │
│  ┌─────────────────────┐                          │
│  │  Foreground Poller  │──► invoke 'get_fg_proc' ─► onTitleChange
│  │  tcgetpgrp (nix)    │    (interval, macOS only)             │
│  │  libproc name lookup│                                       │
│  └─────────────────────┘                                       │
└────────────────────────────────────────────────────────────────┘

Frontend coalescing (D-02):
  Rust sends chunks → Channel.onmessage pushes to pendingData[]
  requestAnimationFrame callback: term.write(pendingData.join('')); pendingData = []
```

### Recommended Project Structure

```
apps/voss-app/src/
├── pane/
│   ├── PaneComponent.tsx      # Solid component — xterm mount, lifecycle, signals
│   ├── PasteGuard.tsx         # Multi-line paste banner (D-04/05)
│   ├── FindBar.tsx            # ⌘F search overlay (PTY-03)
│   ├── ExitBanner.tsx         # [exited N] + Restart button (PTY-07)
│   └── pty-ipc.ts             # Tauri invoke/Channel wrappers, backpressure logic
crates/voss-app-core/src/
├── lib.rs                     # Tauri plugin init, command registration
├── pty/
│   ├── mod.rs                 # PtySession struct, spawn, resize, kill
│   ├── reader.rs              # spawn_blocking reader loop → mpsc → Channel
│   ├── writer.rs              # take_writer wrapper + pty_write command
│   ├── foreground.rs          # tcgetpgrp + libproc / procfs / Windows job-object
│   └── commands.rs            # #[tauri::command] spawn_pty, pty_write, pty_resize, pty_kill
```

---

## Pattern 1: Tauri Channel PTY Streaming (Push Model)

**What:** Rust spawns a background task that reads PTY output and pushes chunks through a Tauri `Channel<Vec<u8>>` to the frontend.

**When to use:** Always for PTY→frontend streaming. This is the correct Tauri 2.x pattern for high-throughput ordered streaming.

**Key API facts:**
- `Channel<Vec<u8>>` is valid because `Vec<u8>` implements `Serialize` (serializes as JSON array for payloads <1024 bytes, uses fetch-based route for ≥1024 bytes) [CITED: docs.rs/tauri/latest/tauri/ipc/struct.Channel.html]
- The Channel is passed from the frontend as a parameter to the `spawn_pty` command
- Ordering is guaranteed by the Channel API [CITED: v2.tauri.app/develop/calling-frontend/]

**Example:**
```rust
// Source: Tauri 2.x official docs pattern (adapted for PTY)
use tauri::ipc::Channel;
use tokio::sync::mpsc;

#[tauri::command]
async fn spawn_pty(
    on_data: Channel<Vec<u8>>,
    state: tauri::State<'_, PtyRegistry>,
) -> Result<u32, String> {
    let pty_system = portable_pty::native_pty_system();
    let pair = pty_system.openpty(portable_pty::PtySize {
        rows: 24, cols: 80, pixel_width: 0, pixel_height: 0,
    }).map_err(|e| e.to_string())?;

    let mut cmd = portable_pty::CommandBuilder::new(std::env::var("SHELL").unwrap_or_default());
    cmd.env("TERM", "xterm-256color");
    cmd.env("COLORTERM", "truecolor");

    let child = pair.slave.spawn_command(cmd).map_err(|e| e.to_string())?;
    let mut reader = pair.master.try_clone_reader().map_err(|e| e.to_string())?;

    // Backpressure channel: frontend signals pause/resume
    let (pause_tx, mut pause_rx) = mpsc::channel::<bool>(8);

    tokio::task::spawn_blocking(move || {
        let mut buf = [0u8; 8192];
        loop {
            // Check pause signal (non-blocking)
            if pause_rx.try_recv().ok() == Some(true) {
                // Wait for resume
                while pause_rx.blocking_recv() != Some(false) {}
            }
            match reader.read(&mut buf) {
                Ok(0) => break, // EOF = child exited
                Ok(n) => { let _ = on_data.send(buf[..n].to_vec()); }
                Err(_) => break,
            }
        }
    });
    // ... register session, return session ID
    Ok(0)
}
```

**Frontend coalescing (D-02):**
```typescript
// Source: D-02 pattern — per-animation-frame coalescing
const pendingData: Uint8Array[] = [];
let rafPending = false;

const channel = new Channel<Uint8Array>();
channel.onmessage = (chunk) => {
  pendingData.push(chunk);
  if (!rafPending) {
    rafPending = true;
    requestAnimationFrame(() => {
      const merged = mergeUint8Arrays(pendingData);
      term.write(merged);
      pendingData.length = 0;
      rafPending = false;
    });
  }
};
```

---

## Pattern 2: Watermark Backpressure (D-02 Flood Contract)

**What:** The write callback from xterm.js notifies when data is processed. Track pending byte count; pause PTY reads when queue exceeds HIGH watermark.

**When to use:** Always — this is what makes the D-02 "UI never freezes" contract achievable.

**Example (based on official xterm.js flow control docs):**
```typescript
// Source: xtermjs.org/docs/guides/flowcontrol/ (adapted for Tauri)
const HIGH = 100_000;  // 100KB
const LOW  =  10_000;  // 10KB
let watermark = 0;

channel.onmessage = (chunk: Uint8Array) => {
  watermark += chunk.length;
  term.write(chunk, () => {
    watermark = Math.max(watermark - chunk.length, 0);
    if (watermark < LOW) {
      invoke('pty_resume', { sessionId });
    }
  });
  if (watermark > HIGH) {
    invoke('pty_pause', { sessionId });
  }
};
```

Note: The per-RAF coalescing (Pattern 1) and watermark backpressure (Pattern 2) are **complementary**. RAF coalescing reduces write call frequency under flood; watermark backpressure prevents the write queue from growing unboundedly. Use both.

---

## Pattern 3: xterm.js Solid Lifecycle Integration

**What:** Mount an imperative xterm.js Terminal instance exactly once in `onMount`, clean up in `onCleanup`. Never re-create the Terminal on signal changes.

**Example:**
```typescript
// Source: Solid.js onMount/onCleanup docs + xterm.js Terminal API
import { onMount, onCleanup, createSignal } from 'solid-js';
import { Terminal } from '@xterm/xterm';
import { CanvasAddon } from '@xterm/addon-canvas';
import { FitAddon } from '@xterm/addon-fit';

const PaneComponent = () => {
  let containerRef!: HTMLDivElement;
  let term: Terminal;
  let fitAddon: FitAddon;

  onMount(() => {
    term = new Terminal({
      scrollback: 10_000,
      fontFamily: '"JetBrains Mono", monospace',
      fontSize: 13,
      theme: { background: '#0a0b0e', foreground: '#e8eaf0' },
      allowProposedApi: false,
    });

    fitAddon = new FitAddon();
    const canvasAddon = new CanvasAddon();
    term.loadAddon(fitAddon);
    term.loadAddon(canvasAddon);  // D-01: must load AFTER open()
    term.open(containerRef);
    fitAddon.fit();

    // OSC 0 title → foreground command signal
    term.onTitleChange((title) => setFgProcess(title));

    // Link handler for OSC 8 + custom file-path provider
    term.options.linkHandler = {
      activate: (event, text) => {
        if (event.metaKey) invoke('shell_open', { url: text });
      },
      allowNonHttpProtocols: true,
    };

    // start PTY...
  });

  onCleanup(() => {
    term?.dispose();
    // invoke kill_pty...
  });

  return <div ref={containerRef} style={{ height: '100%', width: '100%' }} />;
};
```

**Key rules:**
- `canvasAddon` must be loaded **after** `term.open(containerRef)` [ASSUMED — xterm.js addon loading order convention]
- Do not store xterm state in Solid signals — keep Terminal instance in local `let` variable
- `fitAddon.fit()` must be called after the terminal is visible (i.e., container is in DOM)

---

## Pattern 4: portable-pty API (Spawn, Resize, Exit Detection)

**What:** Core Rust API for PTY lifecycle. [CITED: docs.rs/portable-pty/latest/portable_pty/]

```rust
use portable_pty::{native_pty_system, CommandBuilder, PtySize};

// Spawn
let pty_system = native_pty_system();
let pair = pty_system.openpty(PtySize { rows: 24, cols: 80, pixel_width: 0, pixel_height: 0 })?;
let mut cmd = CommandBuilder::new("/bin/zsh");
cmd.env("TERM", "xterm-256color");
cmd.env("COLORTERM", "truecolor");
cmd.cwd("/path/to/project");
let mut child = pair.slave.spawn_command(cmd)?;

// Read (blocking — use spawn_blocking)
let mut reader = pair.master.try_clone_reader()?;

// Write
let mut writer = pair.master.take_writer()?;
writer.write_all(input_bytes)?;

// Resize (call after FitAddon measures new cols/rows)
pair.master.resize(PtySize { rows: new_rows, cols: new_cols, pixel_width: 0, pixel_height: 0 })?;

// Exit detection (non-blocking poll in reader loop)
match child.try_wait() {
    Ok(Some(status)) => { /* emit exit event with status.exit_code() */ }
    Ok(None) => { /* still running */ }
    Err(e) => { /* error */ }
}

// Kill (SIGTERM then SIGKILL via ChildKiller)
child.kill()?;
```

**SIGINT for ⌘C (D-06, no-selection case):**
portable-pty does not expose a direct SIGINT-to-foreground-pgid call. The correct approach writes `\x03` (ETX = Ctrl-C) to the PTY master's writer — the kernel TTY driver delivers SIGINT to the foreground process group. This is identical to what physical terminal emulators do. [ASSUMED — standard TTY behavior; no portable-pty-specific docs found for direct signal sending]

```rust
// Writing ETX causes kernel to deliver SIGINT to foreground pgid
writer.write_all(b"\x03")?;
```

For explicit `kill(SIGINT, pgid)` as fallback, use `nix::sys::signal::kill`:
```rust
use nix::{sys::signal::{kill, Signal}, unistd::Pid};
kill(Pid::from_raw(-foreground_pgid), Signal::SIGINT)?;
```

---

## Pattern 5: Foreground Process Detection (D-07)

**What:** Two-tier detection. Primary: `Terminal.onTitleChange` (passive, shell must emit OSC 0). Fallback: poll `tcgetpgrp(master_fd)` + resolve process name.

**Primary (xterm.js):**
```typescript
term.onTitleChange((title: string) => {
  // Shells emit "zsh", "bash", or "vim /path" via OSC 0 in PS1
  setHeaderProcess(title || shellName);
});
```

**Fallback (Rust — macOS):**
```rust
#[cfg(target_os = "macos")]
fn get_foreground_process_name(master_fd: std::os::unix::io::RawFd) -> Option<String> {
    use nix::unistd::tcgetpgrp;
    use nix::unistd::Pid;
    let pgid = tcgetpgrp(master_fd).ok()?;
    // libproc to get process name from pgid
    libproc::proc_pid::name(pgid.as_raw()).ok()
}

#[cfg(target_os = "linux")]
fn get_foreground_process_name(master_fd: std::os::unix::io::RawFd) -> Option<String> {
    use nix::unistd::tcgetpgrp;
    let pgid = tcgetpgrp(master_fd).ok()?;
    std::fs::read_to_string(format!("/proc/{}/comm", pgid.as_raw())).ok()
        .map(|s| s.trim().to_owned())
}
```

Poll interval: 500ms is sufficient; pause polling when OSC title is being received actively. [ASSUMED — polling interval, no official guidance found]

---

## Pattern 6: Resize / SIGWINCH Coordination

**What:** FitAddon measures the container, computes new cols/rows, then invokes a Tauri command that calls `master.resize(PtySize)`. The OS delivers SIGWINCH automatically when the PTY is resized via the ioctl.

**Debounce:** Use 150ms debounce on the ResizeObserver callback before calling `fitAddon.fit()` and invoking `pty_resize`. During active drag, the container size changes continuously; without debounce, hundreds of resize ioctls fire. [CITED: multiple sources recommend 100–200ms debounce for xterm fit]

```typescript
let resizeTimer: ReturnType<typeof setTimeout>;
const observer = new ResizeObserver(() => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    fitAddon.fit();
    invoke('pty_resize', {
      sessionId,
      rows: term.rows,
      cols: term.cols,
    });
  }, 150);
});
observer.observe(containerRef);
```

---

## Pattern 7: Multi-line Paste Intercept (D-04/05)

**What:** Intercept paste before xterm processes it. Detect newlines in clipboard content. Show banner if ≥1 newline; bypass if ⌘⇧V.

**Key challenge:** xterm.js paste handlers are internal and not easily overridable via public API. The correct approach intercepts the `paste` DOM event on the container element BEFORE it reaches xterm. [CITED: xtermjs/xterm.js issue #1803 — paste hook not natively supported]

```typescript
containerRef.addEventListener('paste', (e) => {
  e.preventDefault(); // Stop xterm's own paste handler
  const text = e.clipboardData?.getData('text') ?? '';
  if (text.includes('\n') && !bypassFlag) {
    setPendingPaste(text);
    setShowPasteBanner(true); // Show D-04 banner
  } else {
    sendPasteToTerminal(text);
  }
}, true); // capture phase, before xterm
```

⌘⇧V bypass: In `customKeyEventHandler`, detect ⌘⇧V, set `bypassFlag = true`, let the event fall through to the normal paste path (which will skip the banner check).

**Bracketed paste:** xterm.js implements bracketed paste mode natively — when the running shell enables it (most modern shells do), xterm wraps pasted text in `\x1b[200~...\x1b[201~` automatically. The multi-line banner is an ADDITIONAL safety layer that fires before the bracketed-paste wrapping, for user awareness of what they're sending. [CITED: xterm.js commit 1dbcf70]

---

## Pattern 8: OSC 8 Hyperlinks + File-Path Detection (PTY-05)

**What:** Two link types: (1) explicit OSC 8 links handled by `term.options.linkHandler`; (2) auto-detected URLs + file paths via `@xterm/addon-web-links` + a custom `registerLinkProvider`.

```typescript
// OSC 8 — built into xterm.js
term.options.linkHandler = {
  activate: (_, uri) => { invoke('open_url', { url: uri }); },
  allowNonHttpProtocols: true,  // allows file:// links
};

// File-path detection — custom link provider
// Matches: /absolute/path or ./relative or ~/home
const FILE_PATH_RE = /(\/[^\s'"]+|~\/[^\s'"]+|\.[./][^\s'"]+)/g;
term.registerLinkProvider({
  provideLinks(y, callback) {
    // Implementation: scan line for file paths, return link objects
    // Use term.buffer.active.getLine(y) to get line content
    callback([/* ILink objects */]);
  }
});
```

Tauri shell open: use `@tauri-apps/plugin-shell`'s `open(url)` for URLs; use `invoke('open_path', { path })` backed by `std::process::Command::new("open").arg(path)` on macOS. [ASSUMED — Tauri plugin-shell 2.3.5 is available]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Terminal VT emulation | Custom ANSI parser | `@xterm/xterm` 5.5.0 | Alt-screen, mouse reporting, 256-color — thousands of edge cases |
| PTY spawn / I/O | libc::openpty bindings | `portable-pty` 0.9.0 | Cross-platform (macOS/Linux/Windows ConPTY); battle-tested in WezTerm |
| Terminal resize to DOM | CSS introspection + cols calc | `@xterm/addon-fit` | Font metrics, DPR, scrollbar presence — too many footguns |
| URL detection in output | Regex on raw bytes | `@xterm/addon-web-links` | Handles multi-line URLs, wrapping, OSC 8 |
| Backpressure | setTimeout-based polling | xterm write callback watermark | The right semantic: pauses at xterm processing boundary |
| SIGWINCH delivery | `kill(SIGWINCH, pid)` | PTY ioctl via `master.resize()` | `resize()` triggers kernel SIGWINCH to child automatically |

**Key insight:** The xterm.js + portable-pty combination eliminates ~80% of the hard terminal emulation work. The remaining complexity is in the IPC transport, backpressure, and platform-specific foreground detection.

---

## Common Pitfalls

### Pitfall 1: Pinning xterm v5 vs v6
**What goes wrong:** `pnpm install` or `pnpm update` pulls `@xterm/xterm@6.0.0` (current `latest`). `@xterm/addon-canvas@0.7.0` has `peerDep ^5.0.0`. The build breaks.
**Why it happens:** npm peer dependency resolution may not block installation; it may just warn.
**How to avoid:** Pin `"@xterm/xterm": "5.5.0"` (exact, no `^`) in `package.json`. Add a `pnpm.overrides` entry. Add a Wave 0 CI check that asserts the installed version.
**Warning signs:** `pnpm install` output showing "peer dependency conflict" warnings.

### Pitfall 2: Canvas renderer loaded before `term.open()`
**What goes wrong:** `CanvasAddon` throws or renders blank if loaded before the terminal is opened to a DOM element.
**Why it happens:** Canvas addon needs to know the actual pixel dimensions of the terminal container.
**How to avoid:** Call `term.open(containerRef)` first, then `term.loadAddon(new CanvasAddon())`.
**Warning signs:** Blank terminal div, no output rendered despite data arriving.

### Pitfall 3: PTY reader blocking the tokio runtime
**What goes wrong:** `reader.read()` on the PTY master is blocking. Calling it inside an `async` Tauri command stalls the tokio executor.
**Why it happens:** `portable_pty::MasterPty::try_clone_reader()` returns a `Box<dyn Read + Send>` — synchronous I/O.
**How to avoid:** Always wrap the read loop in `tokio::task::spawn_blocking`.
**Warning signs:** Other Tauri commands become unresponsive while the PTY is active.

### Pitfall 4: Zombie PTY processes
**What goes wrong:** Closing the pane (or app) without calling `child.wait()` or `child.kill()` leaves a zombie shell process.
**Why it happens:** On Unix, a child that exits remains in zombie state until the parent reaps it via wait().
**How to avoid:** When the read loop exits (EOF), call `child.try_wait()` and then `child.kill()` if still running. On pane close, call `pty_kill` command which calls `child.kill()` then the reader thread exits and cleans up.
**Warning signs:** Accumulating zombie shell processes visible in `ps aux`.

### Pitfall 5: DPR / Retina scaling with Canvas renderer
**What goes wrong:** On macOS Retina or high-DPI displays, the canvas renders at 1× DPR, making glyphs blurry.
**Why it happens:** xterm.js should handle this automatically, but if `window.devicePixelRatio` changes (e.g., moving between screens), the canvas may not re-scale.
**How to avoid:** Listen for `window.devicePixelRatio` changes via a `matchMedia` listener. Call `fitAddon.fit()` on change. xterm.js CanvasAddon handles the canvas scaling internally if the terminal is re-fitted. [ASSUMED — specific DPR change handling; the general pattern is established from Tauri DPR issues found in research]
**Warning signs:** Blurry terminal text on Retina displays.

### Pitfall 6: Windows portable-pty — do not drop slave before writing
**What goes wrong:** On Windows, `pair.slave` must be kept alive until the child process exits, or writes to the PTY master fail silently. [CITED: github.com/wez/wezterm/issues/4206]
**Why it happens:** ConPTY behavior differs from Unix PTY — the slave side reference count matters.
**How to avoid:** Store `pair.slave` in the PtySession struct alongside `pair.master`. Drop slave only after child exits.
**Warning signs:** Input to running shell on Windows appears to do nothing.

### Pitfall 7: portable-pty 0.9.0 Windows data corruption
**What goes wrong:** `pty.read()` may return garbage bytes on Windows in certain configurations. [CITED: github.com/wez/wezterm/issues/6783]
**Why it happens:** ConPTY-specific buffering issue in 0.9.0.
**How to avoid:** Test Windows explicitly. If corruption occurs, investigate whether a WezTerm patch release addresses it, or add a Windows-specific sanitization pass. For A2 scope (macOS/Linux primary), flag as known issue for Windows CI.
**Warning signs:** Garbled output on Windows only; macOS/Linux clean.

### Pitfall 8: xterm alt-screen scrollback contamination
**What goes wrong:** When vim/htop exits, the alt-screen restoration can leave artifacts in the normal scrollback buffer (duplicate content). [CITED: github.com/xtermjs/xterm.js/issues/802]
**Why it happens:** xterm.js alt-screen buffer restore behavior.
**How to avoid:** This is a known xterm.js issue with no clean workaround. Ensure `TERM=xterm-256color` is set (not `xterm` or `screen`). For A2, accept this as a known cosmetic issue; it does not affect PTY-08 correctness for vim/htop rendering while active.
**Warning signs:** Scrollback shows duplicated lines after exiting alt-screen app.

### Pitfall 9: ⌘C handler ordering in Tauri webview (macOS)
**What goes wrong:** macOS intercepts ⌘C for "copy" at the system level before xterm.js `customKeyEventHandler` fires.
**Why it happens:** Tauri webview on macOS passes through the standard macOS copy shortcut.
**How to avoid:** In `tauri.conf.json`, configure the webview to handle ⌘C in JavaScript by preventing the default browser behavior for that key combo. Use xterm.js `customKeyEventHandler` which receives the event before the browser copy. Return `false` from `customKeyEventHandler` to suppress xterm processing when the selection→copy path is taken. [ASSUMED — Tauri-specific keyboard handling; the pattern is standard for xterm.js integrations]
**Warning signs:** ⌘C always copies even when no text selected; SIGINT never sent.

---

## Runtime State Inventory

Phase A2 is greenfield — no existing runtime state to migrate.

**Nothing found in any category** — verified by reviewing codebase (only CONCEPT.md + FEATURES.md exist in `apps/voss-app/`). No stored data, no live service config, no OS registrations, no secrets, no build artifacts from A2 scope.

---

## Code Examples

### xterm.js Terminal Initialization (v5.5.0, Canvas)
```typescript
// Source: @xterm/xterm 5.5.0 API + @xterm/addon-canvas 0.7.0
import { Terminal } from '@xterm/xterm';
import { CanvasAddon } from '@xterm/addon-canvas';
import { FitAddon } from '@xterm/addon-fit';
import { SearchAddon } from '@xterm/addon-search';
import { WebLinksAddon } from '@xterm/addon-web-links';

const term = new Terminal({
  scrollback: 10_000,
  fontFamily: '"JetBrains Mono", "SF Mono", monospace',
  fontSize: 13,
  lineHeight: 1.5,
  theme: {
    background:  '#0a0b0e',  // --bg-0
    foreground:  '#e8eaf0',  // --fg-0
    cursor:      '#5a7cff',  // --focus
    selection:   'rgba(90,124,255,0.3)',
  },
  cursorBlink: true,
  macOptionIsMeta: true,
  rightClickSelectsWord: false,
});

const fitAddon    = new FitAddon();
const searchAddon = new SearchAddon();
const webLinks    = new WebLinksAddon();

term.loadAddon(fitAddon);
term.loadAddon(searchAddon);
term.loadAddon(webLinks);

term.open(containerElement);     // MUST come before CanvasAddon
term.loadAddon(new CanvasAddon()); // D-01: Canvas renderer

fitAddon.fit();
```

### portable-pty Spawn (Rust)
```rust
// Source: docs.rs/portable-pty/latest/portable_pty/
use portable_pty::{native_pty_system, CommandBuilder, PtySize};

let pty_system = native_pty_system();
let size = PtySize { rows: 24, cols: 80, pixel_width: 0, pixel_height: 0 };
let pair = pty_system.openpty(size).expect("openpty failed");

let mut cmd = CommandBuilder::new(
    std::env::var("SHELL").unwrap_or_else(|_| "/bin/sh".into())
);
cmd.env("TERM", "xterm-256color");
cmd.env("COLORTERM", "truecolor");
// Do NOT drop pair.slave before child exits (Windows footgun)
let _slave = pair.slave; // keep alive
let child = _slave.spawn_command(cmd).expect("spawn failed");
```

### Tauri Channel Invoke (TypeScript)
```typescript
// Source: v2.tauri.app/develop/calling-frontend/ (Channel pattern)
import { invoke, Channel } from '@tauri-apps/api/core';

const dataChannel = new Channel<number[]>();
dataChannel.onmessage = (bytes) => {
  const u8 = new Uint8Array(bytes);
  // Feed into per-RAF coalescing buffer
  pendingChunks.push(u8);
};

const sessionId: number = await invoke('spawn_pty', {
  onData: dataChannel,
  rows: term.rows,
  cols: term.cols,
});
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| xterm legacy npm (`xterm@5.x`) | `@xterm/xterm` scoped package | Nov 2023 (xterm.js 5.0) | Old `xterm` npm package frozen at 5.3.0; all new releases under `@xterm/*` |
| Canvas renderer built into xterm | `@xterm/addon-canvas` optional addon | xterm.js 5.0 (2023) | Canvas is now opt-in; DOM is default; WebGL via addon |
| Canvas renderer maintained | Canvas renderer **removed** from xterm | xterm.js **6.0.0** (2025) | CRITICAL: Canvas addon v0.7.0 only supports ^5.0.0 |
| Events for PTY streaming in Tauri 1.x | `Channel<T>` in Tauri 2.x | Tauri 2.0 (2024) | Channel is ordered, high-throughput, type-safe |
| Polling-based PTY read (frontend calls read) | Push model via Channel | Tauri 2.x | No polling overhead; reads triggered by data availability |
| `node-pty` in Electron | `portable-pty` in Tauri | Shift to Tauri | Rust native; no Node.js dependency; ConPTY on Windows |

**Deprecated/outdated:**
- `xterm` (unscoped npm): Frozen at 5.3.0 — use `@xterm/xterm` exclusively
- Tauri 1.x `app.emit()` for streaming: JSON-only, unsuitable for PTY bytes — use Channel
- WebGL renderer as D-01 alternative: Not acceptable per locked decision; use Canvas on v5.5

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | CanvasAddon must be loaded after `term.open()` | Pattern 3 | Terminal renders blank; easy to discover in Wave 0 |
| A2 | Writing `\x03` (ETX) to PTY master delivers SIGINT to foreground pgid | Pattern 4 | ⌘C no-selection would fail to interrupt; fallback to nix::kill needed |
| A3 | Tauri webview on macOS does NOT automatically intercept ⌘C before xterm's customKeyEventHandler | Pitfall 9 | D-06 ⌘C=SIGINT would silently fail; testable in Wave 1 |
| A4 | 500ms polling interval for foreground-process fallback is sufficient | Pattern 5 | Header may lag on fast command switches; cosmetic only |
| A5 | `libproc::proc_pid::name(pgid)` returns the process name given a pgid (not pid) | Pattern 5 | Foreground detection broken on macOS; may need pgid→pid resolution first |
| A6 | DPR change listener on `matchMedia` + `fitAddon.fit()` handles Retina rescaling | Pitfall 5 | Blurry text on multi-monitor setups; cosmetic |
| A7 | All listed packages are legitimate (slopcheck unavailable) | Package Audit | Low risk — all are from known official projects |
| A8 | Channel sends Vec<u8> efficiently for chunks ≥1024 bytes via fetch route | Pattern 1 | Large PTY bursts may be slower than expected; measure in D-02 test |

---

## Open Questions

1. **D-01 vs xterm v6 — user decision needed**
   - What we know: `@xterm/addon-canvas` is incompatible with `@xterm/xterm@6.0.0`. Canvas addon was removed in v6.
   - What's unclear: Whether the user wants to maintain the D-01 canvas pin (accept v5 pinning) or relax D-01 to use WebGL with v6.
   - Recommendation: Planner adds a `checkpoint:human-verify` at Wave 0 presenting this tradeoff. WebGL on v6 is the vendor-recommended path; Canvas on v5.5 honors the locked decision but requires a version pin.

2. **Windows foreground process detection**
   - What we know: `tcgetpgrp` is Unix-only. D-07 mentions "Windows job-object equivalent."
   - What's unclear: No concrete implementation found for Windows foreground pgid equivalent via job objects.
   - Recommendation: Stub Windows foreground detection as "shell name only" (no fallback poll) in A2. File as known gap for Windows support phase.

3. **libproc pgid vs pid**
   - What we know: `tcgetpgrp` returns a pgid. `libproc::proc_pid::name()` takes a pid.
   - What's unclear: Whether there is a direct pgid→name API or whether enumerating processes to find matching pgid is required.
   - Recommendation: In Rust implementation, call `libproc::proc_pid::listpids(ProcType::ProcPGRPOnly(pgid))` to resolve pgid to a list of pids, then call `name(pids[0])`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Rust / Cargo | PTY backend build | ✓ | 1.75+ (workspace) | — |
| pnpm | Frontend build | ✓ (workspace uses pnpm) | — | — |
| Tauri CLI | `pnpm tauri dev` | Check A1 deliverable | 2.x | — |
| macOS / Linux | PTY + tcgetpgrp | ✓ (dev machine is Darwin) | — | — |
| Windows | ConPTY support | Not checked | — | Defer Windows PTY bugs to post-A2 |

**Missing dependencies with no fallback:** None blocking for macOS/Linux development.
**Missing dependencies with fallback:** Windows ConPTY pitfalls — defer.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest (frontend) + Rust `#[test]` / cargo-test (backend) + Playwright for Tauri E2E |
| Config file | `vitest.config.ts` (Wave 0 if not present); `src-tauri/Cargo.toml` test config |
| Quick run command | `pnpm vitest run --reporter=dot` (frontend unit) |
| Full suite command | `pnpm vitest run && cargo test -p voss-app-core` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PTY-01 | `$SHELL` spawns with correct env vars | Integration (Rust) | `cargo test -p voss-app-core test_pty_spawn_env` | ❌ Wave 0 |
| PTY-02 | Bidirectional stream: write "echo hi", read "hi\r\n" | Integration (Rust) | `cargo test -p voss-app-core test_pty_round_trip` | ❌ Wave 0 |
| PTY-02 | D-02 flood: `yes` piped — UI stays responsive, input accepted | E2E performance | Manual + Playwright: `yes | head -10000` then measure rAF timing | ❌ Wave 0 |
| PTY-02 | D-02 cat: multi-MB `cat bigfile` — does not freeze | E2E performance | Manual: `cat /dev/urandom | head -c 5000000 | strings` | ❌ Wave 0 |
| PTY-03 | Scrollback holds 10k lines; search finds term in line 9999 | E2E | Playwright: fill 10k lines, ⌘F, assert match | ❌ Wave 0 |
| PTY-03 | `⌘⇧K` clears scrollback | E2E | Playwright: fill lines, invoke clear, assert empty | ❌ Wave 0 |
| PTY-04 | Multi-line paste shows banner | Unit (frontend) | Vitest: simulate paste event with `\n`, assert banner visible | ❌ Wave 0 |
| PTY-04 | ⌘⇧V bypasses banner | Unit (frontend) | Vitest: simulate ⌘⇧V paste, assert no banner | ❌ Wave 0 |
| PTY-04 | ⌘C with selection = copy | E2E | Playwright: select text, ⌘C, assert clipboard | ❌ Wave 0 |
| PTY-04 | ⌘C without selection = SIGINT (^C appears in terminal) | E2E | Playwright: run `sleep 999`, ⌘C, assert `^C` output | ❌ Wave 0 |
| PTY-05 | OSC 8 URL click opens browser (mock) | E2E | Playwright: output `\e]8;;https://example.com\e\\link\e]8;;\e\\`, ⌘+click | ❌ Wave 0 |
| PTY-06 | OSC 0 title update reflected in header | E2E | Playwright: run `printf "\033]0;vim\007"`, assert header text | ❌ Wave 0 |
| PTY-07 | Shell exit → banner shown; Restart works | E2E | Playwright: `exit 0` in shell, assert banner, click Restart, assert shell | ❌ Wave 0 |
| PTY-08 | vim opens, renders, `:q` exits cleanly | E2E (manual) | Manual: `vim test.txt`, confirm alt-screen, confirm cursor, `:q` | Manual |
| PTY-08 | htop renders and responds to `q` | E2E (manual) | Manual: `htop`, confirm colors/TUI, `q` to exit | Manual |

### D-02 Flood Performance Assertion (Hardest Contract)

The D-02 contract ("UI must never freeze") is a **testable performance assertion**:

**Metric:** While `yes` or `cat /dev/urandom | strings` is running in the terminal, the frontend `requestAnimationFrame` callback must still fire within 2× the frame budget (≤33ms for 60fps). Input typed into the terminal (another pane or via Tauri invoke) must be echoed within 200ms.

**How to test:**
1. Start `yes` in the PTY (infinite flood).
2. Measure: in a `requestAnimationFrame` loop, record actual frame deltas. Assert p95 < 33ms.
3. Send keystrokes via `invoke('pty_write')` while flood is active. Assert they appear in output within 200ms.
4. Assertion can be automated as a Tauri E2E test using `Playwright` + a performance measurement page.

**Implementation requirement:** The per-RAF coalescing pattern (Pattern 1) plus watermark backpressure (Pattern 2) are both required to meet this contract. If only one is implemented, the D-02 bar will fail under `cat /dev/urandom`.

### Sampling Rate
- **Per task commit:** `pnpm vitest run --reporter=dot` (unit/frontend, < 10s)
- **Per wave merge:** `pnpm vitest run && cargo test -p voss-app-core` (< 60s)
- **Phase gate:** Full suite green + D-02 performance assertion passed before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `apps/voss-app/src/pane/__tests__/PasteGuard.test.tsx` — covers PTY-04 paste banner
- [ ] `crates/voss-app-core/src/pty/tests.rs` — covers PTY-01, PTY-02 round-trip
- [ ] `vitest.config.ts` — if not delivered by A1
- [ ] Framework install: `pnpm add -D vitest @testing-library/dom` — if not present
- [ ] D-02 performance benchmark script: `scripts/test-flood-perf.ts`

---

## Security Domain

> `security_enforcement` not explicitly set to false; treating as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — (PTY sessions are local-process-scoped) |
| V4 Access Control | partial | PTY commands must only operate on sessions owned by the requesting webview window (session ID ownership check) |
| V5 Input Validation | yes | PTY write command: validate session ID exists; validate byte payload is non-empty; reject oversized payloads (e.g., > 1MB per write) |
| V6 Cryptography | no | — |

### Known Threat Patterns for Tauri + PTY

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Arbitrary command injection via `spawn_pty` | Elevation of privilege | A2 spawns only `$SHELL` — no user-controlled command path in A2. In A3+, validate shell binary against an allowlist. |
| PTY session ID guessing | Spoofing | Use UUID v4 for session IDs, not sequential integers |
| Malicious terminal escape sequences (OSC, CSI injection) | Tampering | xterm.js sanitizes VT sequences internally; do not eval OSC strings from PTY as JavaScript |
| Webview iframe injection via OSC 8 links | Tampering | Validate all URLs against allowed schemes (http, https, mailto, file) before invoking `shell.open` |
| PTY write flood from frontend | Denial of service | Rate-limit `pty_write` calls; max 1MB/s per session on the Rust side [ASSUMED — rate limit value] |

---

## Sources

### Primary (HIGH confidence)
- `docs.rs/tauri/latest/tauri/ipc/struct.Channel.html` — Channel API, binary payload support, fetch-based route for ≥1KB
- `v2.tauri.app/develop/calling-frontend/` — Tauri 2.x IPC mechanisms, Channel vs events comparison
- `docs.rs/portable-pty/latest/portable_pty/` — PtySize, spawn_command, try_clone_reader, take_writer, resize, try_wait, ChildKiller
- `xtermjs.org/docs/guides/flowcontrol/` — Watermark backpressure, write callback pattern
- `xtermjs.org/docs/guides/link-handling/` — OSC 8 linkHandler API
- npm registry — All `@xterm/*` package versions and peer dependencies (verified 2026-05-18)
- crates.io API — portable-pty 0.9.0, nix 0.31.3, libproc 0.14.11, tauri 2.11.2

### Secondary (MEDIUM confidence)
- `github.com/xtermjs/xterm.js/releases/tag/6.0.0` — canvas addon removal confirmed
- `github.com/cockpit-project/cockpit/issues/22509` — canvas deprecation in v6
- `github.com/wez/wezterm/issues/4206` — Windows slave drop footgun
- `github.com/wez/wezterm/issues/6783` — Windows 0.9.0 data corruption
- `github.com/Tnze/tauri-plugin-pty` — Reference implementation (polling model, not Channel)
- `github.com/marc2332/tauri-terminal` — Reference implementation (polling model via commands)

### Tertiary (LOW confidence — flag for validation)
- Foreground polling interval (500ms): no authoritative source; derived from UX judgment
- Windows foreground detection via job-object: no concrete implementation found; marked as known gap
- libproc pgid→pid resolution pattern: inferred from libproc API docs, not verified with running code

---

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM-HIGH — packages verified on registries; peer dep compat matrix confirmed; D-01/v6 conflict fully documented
- Architecture: MEDIUM — Channel push model is correct per Tauri docs; PTY reader pattern is well-established; Solid lifecycle integration is LOW-complexity
- Pitfalls: HIGH — Windows portable-pty issues are confirmed from wezterm GitHub issues; canvas/v6 conflict is confirmed from npm + release notes; other pitfalls are established community knowledge

**Research date:** 2026-05-18
**Valid until:** 2026-08-18 (90 days — Tauri and xterm.js both move fast; re-verify before major version upgrades)
