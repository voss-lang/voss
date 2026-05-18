# Phase A2: voss-app PTY Pane - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver **one working terminal pane**: an xterm.js frontend bound to a native PTY via `portable-pty` (Rust, in `crates/voss-app-core`), with full TTY support, scrollback, copy/paste, and OSC sequence handling. This is the foundational pane every later A-phase composes.

**In scope:** single pane lifecycle, PTY spawn/stream/resize, xterm rendering, scrollback (buffer + search + clear), copy/paste with multi-line safety, OSC 0/2 title + OSC 8 hyperlinks, foreground-command detection for the Variant B header, shell-exit banner.

**Out of scope (other phases):** multi-pane / splits / grid (A3) · layout presets (A4) · scrollback *persistence* across restart (A6 — A2 only needs in-session buffer + search + clear) · status bar (A9, stubbed here) · Tauri shell scaffold (A1 — assumed to exist).
</domain>

<decisions>
## Implementation Decisions

### Performance + Renderer
- **D-01:** Use the **xterm.js Canvas renderer** (not WebGL, not DOM). Rationale: avoids the WebGL context-loss bug class across GPUs/VMs; throughput is sufficient for a single pane. Revisit renderer choice at A3 when N panes render concurrently.
- **D-02:** Flood policy: PTY output is **coalesced per animation frame**; on flood (`yes`, `cat bigfile`) render the latest state and **drop intermediate frames** — the UI must never freeze or block. This is a hard performance contract, not best-effort.
- **D-03:** Performance bar: 60fps scroll target under normal load; sustained high-throughput output must keep the UI responsive (input still accepted, other future panes unaffected).

### Multi-line Paste Safety (PTY-04 bracketed-paste)
- **D-04:** Any paste containing **≥1 newline** shows an **inline non-modal banner** with a content preview. Non-blocking — does not gate other UI.
- **D-05:** Banner controls: `Enter` sends the paste, `Esc` cancels it, `⌘⇧V` bypasses the banner entirely (literal paste, no prompt). Single-line pastes never prompt.

### ⌘C Behavior (PTY-04)
- **D-06:** Default: **text selected → ⌘C copies; no selection → ⌘C sends SIGINT**. Behavior is **configurable** (settings can force always-copy or always-interrupt). Ships with the smart default.

### Foreground-Command Detection (PTY-06, Variant B header)
- **D-07:** Detection strategy: **OSC 0 / OSC 2 title is primary**; when the shell emits no title, **fall back to polling the PTY foreground process group** (`tcgetpgrp` + libproc on macOS / procfs on Linux / Windows job-object equivalent) to resolve the running command name. Header segment is always populated and accurate. Accepts the extra Rust work over the simpler OSC-only path.

### Claude's Discretion (left to researcher/planner)
- **PTY ↔ webview transport** — mechanism (Tauri channel vs event stream), encoding (binary vs base64), and backpressure strategy. Must satisfy the D-02 flood contract; otherwise planner's call.
- **Scrollback search implementation** — xterm `serialize`/`search` addon vs a Rust-side mirrored buffer. A2 needs working in-session `⌘F` search + `⌘⇧K` clear over a 10k-line (configurable) buffer; the mechanism is open.
- **Resize / SIGWINCH coordination** — debounce policy during drag, PTY winsize ioctl timing, scrollback reflow. Planner decides; correctness (apps see correct cols/rows) is the only hard requirement.
- **OSC 8 hyperlink + file-path detection** — link activation (`⌘+click`) and the file-path regex/heuristic for "open in OS" are planner's call within PTY-05.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope + requirements
- `.planning/ROADMAP.md` → "Phase A2 — voss-app PTY Pane" — PTY-01..08, proposed success criteria, cross-cutting constraints.

### Product concept + locked cross-phase decisions
- `apps/voss-app/CONCEPT.md` §6 (locked stack: Tauri + Solid + xterm.js + portable-pty), §10 (decisions log — Q2 auto-`$SHELL`, Q3 exit banner, Q6 no cost meter in L1).
- `apps/voss-app/FEATURES.md` §L1.4 (PTY Pane feature detail: scrollback, copy/paste, process indicator, exit behavior, hyperlinks) and §L1.1.2 (theme tokens).

### Design / aesthetic
- `.planning/sketches/001-voss-grid-shell/index.html` — Variant B (Minimal Tile, winner) pane chrome: 22px header, glyph-prefix lines (`❯` user, `⏵` output), inset-shadow focus, mono, color hierarchy.
- `.planning/sketches/001-voss-grid-shell/README.md` + `.planning/sketches/MANIFEST.md` — locked design decisions (header conventions, focus model). ⚠ Unpackaged — `/gsd:sketch --wrap-up` would formalize as a findings skill (not blocking).
- `.planning/sketches/themes/default.css` — canonical Variant B CSS token set.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Greenfield** — `apps/voss-app/` currently holds only `CONCEPT.md` + `FEATURES.md`. No app code exists yet.
- A2 assumes **A1 (Tauri + Solid shell)** delivered: empty window, titlebar, Variant B theme tokens wired, `crates/voss-app-core` crate scaffolded (empty).

### Established Patterns
- Variant B aesthetic tokens are the canonical visual contract (sketch 001 + `themes/default.css`). Pane chrome must match — no re-exploration.
- Monorepo layout (CONCEPT §8): UI in `apps/voss-app/src/pane/`, PTY backend in `crates/voss-app-core`, typed protocol in `crates/voss-app-ipc` (populated as A-phases land).

### Integration Points
- A2's PTY pane component becomes the unit A3 (grid engine) tiles into a binary-split tree. Keep the pane self-contained: a pane owns its PTY, xterm instance, scrollback, and header — no grid awareness in A2.
- Shell-exit banner (Q3) and auto-`$SHELL` spawn (Q2) are locked cross-phase decisions — implement, don't re-decide.
</code_context>

<specifics>
## Specific Ideas

- Performance contract is explicit and testable: a `yes` flood and a multi-MB `cat` must keep the pane scrollable and input-responsive. Treat as an acceptance test, not a nicety (D-02).
- `⌘⇧V` is the universal "I know what I'm doing" paste escape hatch (D-05) — consistent with the bypass affordance elsewhere in the app.
- Header truthfulness matters for the Variant B look — an empty foreground-command segment is considered a defect, hence the OS-pgid fallback (D-07).
</specifics>

<deferred>
## Deferred Ideas

- **Scrollback persistence across restart** — belongs to A6 (Session Persist). A2 keeps scrollback in-session only.
- **Sixel / inline images** — FEATURES §L1.4.9 marks L4+. Out of A2.
- **Send-to-cell / terminal-output piping** — L2 (Voss substrate) feature. Out of A2.
- **Per-pane shell override UI** — settings surface is A8; A2 uses `$SHELL` per Q2.

None of these were scope creep — all surfaced as boundary clarifications and correctly routed to their owning phases.
</deferred>

---

*Phase: A2-voss-app-pty-pane*
*Context gathered: 2026-05-17*
