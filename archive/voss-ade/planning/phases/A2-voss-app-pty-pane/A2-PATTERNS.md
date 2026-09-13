# Phase A2: voss-app PTY Pane — Pattern Map

**Mapped:** 2026-05-18
**Files analyzed:** 12 (new files A2 will create)
**Analogs found:** 0 direct code analogs (new stack) / 12 total
**Conceptual transfers identified:** 5 (from existing Rust crates + Python harness)

---

## Greenfield Determination

`apps/voss-app/` currently contains only `CONCEPT.md` and `FEATURES.md` — no source code.
The existing `crates/` are a CLI/agent spike (Rust + tokio + clap + serde_json) with NO Tauri, NO Solid/TSX, and NO xterm.js code. Every A2 file is a greenfile on a novel stack.

However, five **conceptual transfer patterns** exist in the existing Rust crates and Python harness that the planner MUST mirror:

| Pattern | Source | Transfer target in A2 |
|---------|--------|----------------------|
| Child-process lifecycle (spawn → piped stdio → wait → kill) | `crates/voss-bridge/src/jsonrpc.rs` (PyBridge) | `crates/voss-app-core/src/pty/mod.rs` (PtySession) |
| Async byte-stream framing (read/write loops, tokio async I/O) | `crates/voss-bridge/src/framing.rs` | `crates/voss-app-core/src/pty/reader.rs` |
| spawn_blocking for blocking I/O in tokio runtime | implicit in all crates using tokio::process | `crates/voss-app-core/src/pty/reader.rs` (PTY read is blocking) |
| Event type discriminants ("type" field in NDJSON events) | `crates/voss-render/src/ndjson.rs` (NdjsonRender) | `crates/voss-app-core/src/pty/commands.rs` (Channel event structs) |
| Workspace Cargo conventions (serde, anyhow, uuid, tokio workspace deps) | `Cargo.toml` workspace | `crates/voss-app-core/Cargo.toml` |

---

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `crates/voss-app-core/Cargo.toml` | config | — | `Cargo.toml` (workspace deps) | conceptual-transfer |
| `crates/voss-app-core/src/lib.rs` | config | — | `crates/voss-agent/src/lib.rs` | conceptual-transfer |
| `crates/voss-app-core/src/pty/mod.rs` | service | event-driven | `crates/voss-bridge/src/jsonrpc.rs` (PyBridge) | conceptual-transfer |
| `crates/voss-app-core/src/pty/reader.rs` | service | streaming | `crates/voss-bridge/src/framing.rs` | conceptual-transfer |
| `crates/voss-app-core/src/pty/writer.rs` | service | request-response | `crates/voss-tools/src/shell_run.rs` (ShellRun) | conceptual-transfer |
| `crates/voss-app-core/src/pty/foreground.rs` | utility | request-response | `crates/voss-tools/src/shell_run.rs` (platform conditional) | conceptual-transfer |
| `crates/voss-app-core/src/pty/commands.rs` | controller | request-response | `crates/voss-render/src/ndjson.rs` (event type pattern) | conceptual-transfer |
| `apps/voss-app/src/pane/PaneComponent.tsx` | component | event-driven | GREENFILE — no analog (new stack) | none |
| `apps/voss-app/src/pane/pty-ipc.ts` | service | streaming | GREENFILE — no analog (new stack) | none |
| `apps/voss-app/src/pane/PasteGuard.tsx` | component | request-response | GREENFILE — no analog (new stack) | none |
| `apps/voss-app/src/pane/FindBar.tsx` | component | request-response | GREENFILE — no analog (new stack) | none |
| `apps/voss-app/src/pane/ExitBanner.tsx` | component | event-driven | GREENFILE — no analog (new stack) | none |

---

## Pattern Assignments

### `crates/voss-app-core/Cargo.toml` (config)

**Analog:** `/Users/benjaminmarks/Projects/Voss/Cargo.toml` (workspace root)

**Workspace dep pattern** (lines 6–40 of workspace Cargo.toml):
```toml
# Inherit workspace deps — do NOT re-pin versions already in [workspace.dependencies]
[dependencies]
tauri = { version = "2", features = ["wry"] }
portable-pty = "0.9.0"
nix = { version = "0.31", features = ["signal", "term", "process"] }
tokio = { workspace = true }          # <-- workspace = true for shared deps
serde = { workspace = true }
anyhow = { workspace = true }
uuid = { workspace = true }

[target.'cfg(target_os = "macos")'.dependencies]
libproc = "0.14"                      # macOS-only; must be gated

[package]
edition = "2021"                      # matches workspace.package.edition
rust-version = "1.75"                 # matches workspace.package.rust-version
```

**Key rule:** All deps already in the workspace `[workspace.dependencies]` (tokio, serde, anyhow, uuid, etc.) MUST use `{ workspace = true }`. Only Tauri-specific and PTY-specific deps get explicit versions.

---

### `crates/voss-app-core/src/lib.rs` (config — plugin registration)

**Analog:** `/Users/benjaminmarks/Projects/Voss/crates/voss-agent/src/lib.rs` (lines 1–14)

The existing pattern is a flat `pub mod` + `pub use` re-export file. Apply the same structure:

```rust
//! voss-app-core — Tauri plugin: PTY lifecycle, IPC commands.

pub mod pty;

pub use pty::commands::{spawn_pty, pty_write, pty_resize, pty_kill, get_fg_process};
pub use pty::mod_::PtyRegistry;

// Tauri plugin init — registers all #[tauri::command] handlers
pub fn init<R: tauri::Runtime>() -> tauri::plugin::TauriPlugin<R> {
    tauri::plugin::Builder::new("voss-app-core")
        .invoke_handler(tauri::generate_handler![
            spawn_pty, pty_write, pty_resize, pty_kill, get_fg_process,
        ])
        .setup(|app, _| {
            app.manage(PtyRegistry::default());
            Ok(())
        })
        .build()
}
```

---

### `crates/voss-app-core/src/pty/mod.rs` (service — session struct)

**Analog:** `/Users/benjaminmarks/Projects/Voss/crates/voss-bridge/src/jsonrpc.rs` — PyBridge struct

The PyBridge is the closest structural analog: it spawns a child process, holds handles to its stdin/stdout, and dispatches requests. The PtySession is the same pattern but for a PTY instead of piped stdio.

**PyBridge struct pattern** (lines 17–28 of jsonrpc.rs):
```rust
pub struct PyBridge {
    python: PathBuf,
    child: Mutex<Option<BridgeChild>>,   // child held alive; Mutex for shared access
    next_id: AtomicU64,                  // session ID generation
}

struct BridgeChild {
    _child: Child,          // held alive (not dropped) until session ends
    stdin: ChildStdin,
    stdout: BufReader<ChildStdout>,
}
```

**Transfer to PtySession:**
```rust
// Mirror of PyBridge's child-hold pattern, adapted for PTY
pub struct PtySession {
    pub id: uuid::Uuid,
    master: Box<dyn portable_pty::MasterPty + Send>,
    writer: Mutex<Box<dyn std::io::Write + Send>>,
    _slave: Box<dyn portable_pty::SlavePty + Send>,  // kept alive (Windows footgun)
    child: Mutex<Box<dyn portable_pty::Child + Send>>,
    pause_tx: tokio::sync::mpsc::Sender<bool>,
    shell_name: String,
    cwd: std::path::PathBuf,
}
```

**PyBridge child lifecycle pattern** (lines 63–83 of jsonrpc.rs):
```rust
// ensure_started() lazy-init: check if None, spawn child, store handles
let mut child = Command::new(&self.python)
    .args(["-m", "voss.bridge_server"])
    .stdin(std::process::Stdio::piped())
    .stdout(std::process::Stdio::piped())
    .stderr(std::process::Stdio::inherit())
    .spawn()?;
let stdin = child.stdin.take().expect("stdin piped");
let stdout = BufReader::new(child.stdout.take().expect("stdout piped"));
```

This `.take()` on stdin/stdout is the same pattern needed for PTY writer (`take_writer()`) and reader (`try_clone_reader()`).

---

### `crates/voss-app-core/src/pty/reader.rs` (service — streaming reader loop)

**Analog:** `/Users/benjaminmarks/Projects/Voss/crates/voss-bridge/src/framing.rs` — async read loop

The framing module demonstrates the correct read-loop structure: read from async source, parse/accumulate bytes, handle EOF and errors.

**Framing read loop pattern** (lines 15–59 of framing.rs):
```rust
pub async fn read_frame<R: AsyncBufRead + Unpin>(r: &mut R) -> io::Result<Vec<u8>> {
    loop {
        let mut line = String::new();
        let n = r.read_line(&mut line).await?;
        if n == 0 {
            return Err(io::Error::new(io::ErrorKind::UnexpectedEof, "eof while reading headers"));
        }
        // ... process bytes ...
    }
    let mut body = vec![0u8; n as usize];
    r.read_exact(&mut body).await?;
    Ok(body)
}
```

**Transfer to PTY reader — key differences:**
- PTY read is BLOCKING (`Box<dyn Read + Send>`), not async. Must use `tokio::task::spawn_blocking`.
- EOF means child exited — emit exit event instead of returning error.
- No framing — raw bytes forwarded directly to Channel.

```rust
// Pattern: spawn_blocking wrapping a blocking read loop (no direct analog in codebase)
tokio::task::spawn_blocking(move || {
    let mut buf = [0u8; 8192];
    loop {
        // Check backpressure pause signal (non-blocking try_recv)
        if pause_rx.try_recv().ok() == Some(true) {
            while pause_rx.blocking_recv() != Some(false) {}
        }
        match reader.read(&mut buf) {
            Ok(0) => break,   // EOF = child exited
            Ok(n) => { let _ = on_data.send(buf[..n].to_vec()); }
            Err(_) => break,
        }
    }
    // EOF reached — emit exit event
});
```

---

### `crates/voss-app-core/src/pty/writer.rs` (service — request-response write)

**Analog:** `/Users/benjaminmarks/Projects/Voss/crates/voss-tools/src/shell_run.rs` — ShellRun tool

The ShellRun tool demonstrates the pattern of writing input to a child process and handling errors gracefully. The PTY writer is simpler (no wait, no output collection — fire and forget write).

**ShellRun spawn + write pattern** (lines 57–80 of shell_run.rs):
```rust
async fn invoke(&self, args: Value) -> anyhow::Result<String> {
    let args: ShellRunArgs = serde_json::from_value(args)?;
    // ... sandbox check ...
    let mut cmd = Command::new("sh");
    cmd.arg("-c").arg(&args.cmd)
       .current_dir(&self.cwd)
       .stdout(Stdio::piped())
       .stderr(Stdio::piped());
    let child = match cmd.spawn() {
        Ok(c) => c,
        Err(e) => return Ok(format!("<error: {e}>")),
    };
    // ... wait and collect output ...
}
```

**Transfer to pty_write command:** The error-return-as-string pattern (`Ok(format!("<error: {e}>"))`) should NOT be used for PTY write — the PTY write command returns `Result<(), String>` and should surface errors to the caller.

**Payload validation to copy from ShellRun:**
```rust
// ShellRun: `if let Err(e) = shell_allowed(...)` — guard before action
// PTY write: validate session_id exists + payload non-empty + payload <= 1MB
if payload.is_empty() { return Err("empty payload".into()); }
if payload.len() > 1_048_576 { return Err("payload exceeds 1MB limit".into()); }
let session = registry.get(&session_id).ok_or("unknown session")?;
```

---

### `crates/voss-app-core/src/pty/foreground.rs` (utility — platform-conditional)

**No direct analog.** This is new Rust using `nix` + `libproc` APIs not present anywhere in the codebase.

**Platform-conditional structure to use** (compiler-gate pattern common in the codebase):
```rust
#[cfg(target_os = "macos")]
pub fn get_foreground_name(master_fd: std::os::unix::io::RawFd) -> Option<String> {
    use nix::unistd::tcgetpgrp;
    let pgid = tcgetpgrp(master_fd).ok()?;
    // libproc: pgid → pid list → name
    // libproc::proc_pid::listpids(ProcType::ProcPGRPOnly(pgid)) → pids[0]
    // libproc::proc_pid::name(pids[0])
    libproc::proc_pid::name(pgid.as_raw()).ok()  // may need pgid→pid resolution
}

#[cfg(target_os = "linux")]
pub fn get_foreground_name(master_fd: std::os::unix::io::RawFd) -> Option<String> {
    use nix::unistd::tcgetpgrp;
    let pgid = tcgetpgrp(master_fd).ok()?;
    std::fs::read_to_string(format!("/proc/{}/comm", pgid.as_raw())).ok()
        .map(|s| s.trim().to_owned())
}

#[cfg(not(any(target_os = "macos", target_os = "linux")))]
pub fn get_foreground_name(_master_fd: std::os::unix::io::RawFd) -> Option<String> {
    None  // Windows: stub per open question OQ-2
}
```

---

### `crates/voss-app-core/src/pty/commands.rs` (controller — Tauri command handlers)

**Analog:** `/Users/benjaminmarks/Projects/Voss/crates/voss-render/src/ndjson.rs` — NdjsonRender event type pattern

The NdjsonRender shows how to structure typed event objects with a `"type"` discriminant field and emit them through a write channel. The Tauri Channel serves the same role as the NDJSON stdout sink.

**NdjsonRender emit pattern** (lines 26–33 of ndjson.rs):
```rust
fn emit(&mut self, mut value: serde_json::Value) {
    if let Some(obj) = value.as_object_mut() {
        obj.insert("v".to_string(), json!(PROTOCOL_VERSION));  // version field
    }
    let _ = writeln!(self.out, "{}", serde_json::to_string(&value).unwrap());
    let _ = self.out.flush();
}
```

**Event type pattern from ndjson.rs** (lines 36–114, each `impl Render` method):
```rust
// Tool events have a type discriminant + payload fields
self.emit(json!({"type": "tool", "name": name, "state": state.as_str()}));
self.emit(json!({"type": "status", "model": model, "tokens": tokens}));
```

**Transfer to PTY Channel events:**
```rust
// Use serde-tagged enum instead of raw JSON (type-safe Channel<PtyEvent>)
#[derive(serde::Serialize, Clone)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum PtyEvent {
    Data { bytes: Vec<u8> },                    // raw PTY output
    Exit { code: i32 },                         // shell exited
    FgProcess { name: String },                 // foreground process poll result
    TitleChange { title: String },              // OSC 0 forwarded (if needed)
}
```

**Tauri command registration pattern** (no existing analog — use RESEARCH.md Pattern 1):
```rust
#[tauri::command]
pub async fn spawn_pty(
    on_data: tauri::ipc::Channel<PtyEvent>,
    rows: u16,
    cols: u16,
    state: tauri::State<'_, PtyRegistry>,
) -> Result<String, String> {
    // ... spawn PTY, start reader thread, return session UUID
}

#[tauri::command]
pub async fn pty_write(
    session_id: String,
    data: Vec<u8>,
    state: tauri::State<'_, PtyRegistry>,
) -> Result<(), String> {
    // validate + write to PTY writer
}

#[tauri::command]
pub async fn pty_resize(
    session_id: String,
    rows: u16,
    cols: u16,
    state: tauri::State<'_, PtyRegistry>,
) -> Result<(), String> {
    // call master.resize(PtySize { rows, cols, ... })
}
```

---

### `apps/voss-app/src/pane/PaneComponent.tsx` (component — event-driven)

**GREENFILE — no analog (new stack)**

No Solid/TSX components exist anywhere in the codebase. The planner must build from RESEARCH.md Pattern 3 (Solid lifecycle) and the UI-SPEC.md component inventory.

**Key patterns from RESEARCH.md (concrete excerpts to copy):**

**Solid lifecycle — onMount/onCleanup** (RESEARCH.md lines 385–427):
```typescript
import { onMount, onCleanup, createSignal } from 'solid-js';
import { Terminal } from '@xterm/xterm';
import { CanvasAddon } from '@xterm/addon-canvas';
import { FitAddon } from '@xterm/addon-fit';

const PaneComponent = () => {
  let containerRef!: HTMLDivElement;
  let term: Terminal;
  let fitAddon: FitAddon;

  onMount(() => {
    term = new Terminal({ scrollback: 10_000, ... });
    fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.loadAddon(new SearchAddon());
    term.open(containerRef);          // MUST come before CanvasAddon
    term.loadAddon(new CanvasAddon()); // D-01: Canvas AFTER open()
    fitAddon.fit();
  });

  onCleanup(() => { term?.dispose(); });

  return <div ref={containerRef} style={{ height: '100%', width: '100%' }} />;
};
```

**xterm Terminal init contract** (UI-SPEC.md lines 228–262 — verbatim theme):
```typescript
new Terminal({
  scrollback: 10_000,
  fontFamily: '"JetBrains Mono", "SF Mono", "Menlo", ui-monospace, monospace',
  fontSize: 13,
  lineHeight: 1.5,
  theme: {
    background: '#0a0b0e', foreground: '#e8eaf0', cursor: '#5a7cff',
    cursorAccent: '#0a0b0e',
    selectionBackground: 'rgba(122, 162, 255, 0.30)',
    black: '#0a0b0e', brightBlack: '#444a5a',
    red: '#e87b7b', brightRed: '#e87b7b',
    green: '#6fd28f', brightGreen: '#6fd28f',
    yellow: '#e8b86c', brightYellow: '#e8b86c',
    blue: '#7aa2ff', brightBlue: '#7aa2ff',
    magenta: '#c084d4', brightMagenta: '#c084d4',
    cyan: '#6cc7d4', brightCyan: '#6cc7d4',
    white: '#aab0c0', brightWhite: '#e8eaf0',
  },
  cursorBlink: true, macOptionIsMeta: true,
  rightClickSelectsWord: false, allowProposedApi: false,
})
```

**ResizeObserver debounce pattern** (RESEARCH.md lines 532–545):
```typescript
let resizeTimer: ReturnType<typeof setTimeout>;
const observer = new ResizeObserver(() => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    fitAddon.fit();
    invoke('pty_resize', { sessionId, rows: term.rows, cols: term.cols });
  }, 150);  // 150ms debounce
});
observer.observe(containerRef);
```

**⌘C / paste intercept** (RESEARCH.md lines 556–568):
```typescript
// Paste intercept — capture phase, before xterm
containerRef.addEventListener('paste', (e) => {
  e.preventDefault();
  const text = e.clipboardData?.getData('text') ?? '';
  if (text.includes('\n') && !bypassFlag) {
    setPendingPaste(text); setShowPasteBanner(true);
  } else { sendPasteToTerminal(text); }
}, true);
```

---

### `apps/voss-app/src/pane/pty-ipc.ts` (service — streaming/backpressure)

**GREENFILE — no analog (new stack)**

This file wraps Tauri Channel invoke and implements the D-02 flood contract.

**Per-RAF coalescing pattern** (RESEARCH.md lines 323–338):
```typescript
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

**Watermark backpressure pattern** (RESEARCH.md lines 350–368):
```typescript
const HIGH = 100_000;  // 100KB
const LOW  =  10_000;  // 10KB
let watermark = 0;

channel.onmessage = (chunk: Uint8Array) => {
  watermark += chunk.length;
  term.write(chunk, () => {
    watermark = Math.max(watermark - chunk.length, 0);
    if (watermark < LOW) invoke('pty_resume', { sessionId });
  });
  if (watermark > HIGH) invoke('pty_pause', { sessionId });
};
```

**Tauri Channel invoke pattern** (RESEARCH.md lines 744–758):
```typescript
import { invoke, Channel } from '@tauri-apps/api/core';

const dataChannel = new Channel<number[]>();
const sessionId: string = await invoke('spawn_pty', {
  onData: dataChannel, rows: term.rows, cols: term.cols,
});
```

---

### `apps/voss-app/src/pane/PasteGuard.tsx` (component — request-response)

**GREENFILE — no analog (new stack)**

No Solid overlay/banner components exist. Build from UI-SPEC.md §5.

**Exact copy contract from UI-SPEC.md lines 354–388:**
- Placement: `position: absolute; bottom: 0; left: 0; right: 0` (adjusts to `bottom: 28px` if exit banner also visible)
- Height: 56px fixed
- Background: `--bg-3` (`#1f232e`)
- Border-top: 1px solid `--accent-magenta` (`#c084d4`)
- Row 1 (28px): `⏵` glyph + preview text (truncated) + `(N lines)` badge
- Row 2 (28px): `Send ⏎` button + `Discard Esc` button + right-aligned `⌘⇧V skips this`
- Transition: none (instant appear/dismiss per motion contract)

**Signal interface:**
```typescript
// Props from PaneComponent
interface PasteGuardProps {
  pendingText: string;       // full clipboard text
  onSend: () => void;        // writes to PTY + dismisses
  onDiscard: () => void;     // clears + dismisses
}
```

---

### `apps/voss-app/src/pane/FindBar.tsx` (component — request-response)

**GREENFILE — no analog (new stack)**

Build from UI-SPEC.md §8.

**Exact copy contract from UI-SPEC.md lines 440–468:**
- Placement: `position: absolute; top: 22px; right: 0` (below header)
- Width: 280px fixed; Height: 32px
- Background: `--bg-3`; Border: 1px `--border-bright` on bottom + left; no radius
- Slots: search input + `↑` prev + `↓` next + `✕` close
- Input background: `--bg-2`; placeholder `Find…` (U+2026)
- Match decorations: current `rgba(90,124,255,0.35)`; other matches `rgba(90,124,255,0.15)`
- Dismiss: Escape or click `✕`

**SearchAddon integration:**
```typescript
import { SearchAddon } from '@xterm/addon-search';
// findNext / findPrevious with decorations
searchAddon.findNext(query, {
  decorations: {
    matchBackground: 'rgba(90,124,255,0.15)',
    matchBorder: 'rgba(90,124,255,0.35)',
    matchOverviewRuler: 'rgba(90,124,255,0.35)',
    activeMatchBackground: 'rgba(90,124,255,0.35)',
    activeMatchBorder: 'rgba(90,124,255,0.35)',
    activeMatchColorOverviewRuler: 'rgba(90,124,255,0.35)',
  }
});
```

---

### `apps/voss-app/src/pane/ExitBanner.tsx` (component — event-driven)

**GREENFILE — no analog (new stack)**

Build from UI-SPEC.md §4.

**Exact copy contract from UI-SPEC.md lines 296–336:**
- Placement: `position: absolute; bottom: 0; left: 0; right: 0`
- Height: 28px fixed
- Background: `--bg-3` (`#1f232e`); border-top: 1px `--border`
- Status dot color: `--accent-green` (exit 0) | `--accent-amber` (exit 1–127) | `--accent-red` (exit > 127)
- Exit message: exactly `[exited N]` — `--fg-1` for 0, `--accent-amber` for non-zero
- Restart button: `--bg-2` bg, `--accent-blue` text, 1px `--border`, no radius; min-width 64px, height 22px
- Transition: none (instant)

**Signal interface:**
```typescript
interface ExitBannerProps {
  exitCode: number;
  onRestart: () => void;
}
```

---

## Shared Patterns

### Rust Error Convention
**Source:** Every crate in `crates/` uses `anyhow::Result` internally; Tauri commands expose `Result<T, String>`.
**Apply to:** All `crates/voss-app-core/src/pty/*.rs` files.

```rust
// Internal Rust functions: anyhow
fn spawn_shell(cwd: &Path) -> anyhow::Result<PtySession> { ... }

// Tauri commands: map to String error for IPC serialization
#[tauri::command]
pub async fn spawn_pty(...) -> Result<String, String> {
    spawn_shell(&cwd).map_err(|e| e.to_string())
}
```

### Workspace Dep Reuse
**Source:** `Cargo.toml` lines 18–40 (workspace.dependencies).
**Apply to:** `crates/voss-app-core/Cargo.toml`.

The following deps are already in the workspace and MUST use `{ workspace = true }`:
`tokio`, `serde`, `serde_json`, `anyhow`, `uuid`, `tracing`, `thiserror`

### UUID Session IDs
**Source:** `Cargo.toml` workspace deps: `uuid = { version = "1", features = ["v4", "serde"] }`.
**Apply to:** `crates/voss-app-core/src/pty/commands.rs` — session IDs.

Session IDs must be UUID v4 (not sequential integers) per the security threat model:
```rust
use uuid::Uuid;
let session_id = Uuid::new_v4().to_string();
```

### NDJSON Event Type Discriminant
**Source:** `crates/voss-render/src/ndjson.rs` (lines 35–114) — every event has a `"type"` field.
**Apply to:** `crates/voss-app-core/src/pty/commands.rs` — `PtyEvent` enum.

Use `#[serde(tag = "type")]` on the Channel event enum so the frontend can switch on `event.type`.

### Tailwind + CSS Custom Properties Token Convention
**Source:** `.planning/sketches/themes/default.css` (canonical — no code file exists yet).
**Apply to:** All `.tsx` component files in `apps/voss-app/src/pane/`.

Do NOT hardcode hex values in TSX. Reference `var(--bg-3)` etc. The token file must be imported/available globally before any component renders.

### No Transition / Instant State
**Source:** UI-SPEC.md §11 motion contract.
**Apply to:** All banner components (`PasteGuard.tsx`, `ExitBanner.tsx`, `FindBar.tsx`).

```css
/* Explicitly set on all overlay elements */
transition: none;
```

---

## No Analog Found

All 12 files are greenfield. The table below clarifies the reason per file tier:

| File | Role | Reason for No Analog |
|------|------|---------------------|
| `crates/voss-app-core/Cargo.toml` | config | Tauri crate, not in workspace yet |
| `crates/voss-app-core/src/lib.rs` | config | Tauri plugin init — no Tauri in codebase |
| `crates/voss-app-core/src/pty/mod.rs` | service | `portable-pty` not used anywhere in codebase |
| `crates/voss-app-core/src/pty/reader.rs` | service | Blocking PTY read via `spawn_blocking` — no existing pattern |
| `crates/voss-app-core/src/pty/writer.rs` | service | PTY writer — no existing pattern |
| `crates/voss-app-core/src/pty/foreground.rs` | utility | `nix::tcgetpgrp` + `libproc` — no existing platform-conditional code |
| `crates/voss-app-core/src/pty/commands.rs` | controller | Tauri `#[tauri::command]` macro — not used anywhere |
| `apps/voss-app/src/pane/PaneComponent.tsx` | component | No TSX/Solid anywhere in codebase |
| `apps/voss-app/src/pane/pty-ipc.ts` | service | No TypeScript anywhere in codebase |
| `apps/voss-app/src/pane/PasteGuard.tsx` | component | No TSX/Solid anywhere in codebase |
| `apps/voss-app/src/pane/FindBar.tsx` | component | No TSX/Solid anywhere in codebase |
| `apps/voss-app/src/pane/ExitBanner.tsx` | component | No TSX/Solid anywhere in codebase |

---

## Conceptual Transfer Summary

The following existing files provide the strongest conceptual grounding for the planner. These are NOT direct code analogs but contain transferable patterns:

| Source File | Pattern to Transfer | Target File |
|-------------|---------------------|-------------|
| `crates/voss-bridge/src/jsonrpc.rs` | Child-process lifecycle: spawn → hold handles → lazy-init → call → teardown | `pty/mod.rs` (PtySession) |
| `crates/voss-bridge/src/framing.rs` | Byte-stream read loop: read → accumulate → handle EOF → handle error | `pty/reader.rs` |
| `crates/voss-render/src/ndjson.rs` | Typed event discriminants via `"type"` field | `pty/commands.rs` (PtyEvent enum) |
| `crates/voss-tools/src/shell_run.rs` | Input validation before action; platform `Command` spawn; error-as-string return | `pty/writer.rs`, `pty/commands.rs` |
| `Cargo.toml` (workspace) | `{ workspace = true }` dep inheritance; edition/rust-version conventions | `crates/voss-app-core/Cargo.toml` |

---

## Metadata

**Analog search scope:** `crates/` (all 7 crates, all `.rs` files), `apps/voss-app/` (only CONCEPT.md + FEATURES.md), `voss/harness/` (Python, conceptual only)
**Files scanned:** ~45 Rust source files, 1 Python file (recorder.py), workspace Cargo.toml
**Pattern extraction date:** 2026-05-18
**Stack note:** This is a full-stack greenfield (Tauri 2.x + Solid + xterm.js + portable-pty). The planner must treat RESEARCH.md patterns as primary guidance for all TSX and IPC files. The 5 conceptual transfer patterns above are supplements for Rust file structure only.
