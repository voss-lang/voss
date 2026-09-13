# Phase A2: voss-app PTY Pane - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-17
**Phase:** A2-voss-app-pty-pane
**Areas discussed:** Performance + Renderer, Multi-line Paste Safety, ⌘C Behavior, Process Indicator Strategy

---

## Performance + Renderer

| Option | Description | Selected |
|--------|-------------|----------|
| WebGL renderer + coalesce/drop-to-latest on flood | Fastest; risk of WebGL context-loss handling | |
| Canvas renderer + same flood policy | Slightly lower throughput than WebGL, no context-loss bug class, safer GPU/VM compat | ✓ |
| DOM renderer, accept lower ceiling | Simplest, most compatible, janks under flood/heavy scrollback | |

**User's choice:** Canvas renderer + coalesce-per-frame, drop-to-latest on flood.
**Notes:** Flood non-freeze treated as a hard contract (D-02), testable via `yes` + multi-MB `cat`. Renderer choice to be revisited at A3 when N panes render concurrently.

---

## Multi-line Paste Safety

| Option | Description | Selected |
|--------|-------------|----------|
| Inline non-modal banner on any newline; Enter sends / Esc cancels / ⌘⇧V bypass | Balanced; doesn't block other UI | ✓ |
| Modal dialog on any multi-line paste | Max accident prevention, more friction | |
| Warn only on >N lines OR trailing newline | Least nag, slightly more risk | |

**User's choice:** Inline non-modal banner on any newline; Enter sends / Esc cancels / `⌘⇧V` bypass.
**Notes:** `⌘⇧V` is the universal literal-paste escape hatch.

---

## ⌘C Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Selection → copy; no selection → SIGINT (configurable) | macOS-terminal-like smart default | ✓ |
| ⌘C always SIGINT; copy is ⌘⇧C | tmux/linux convention | |
| ⌘C always copies; interrupt only via Ctrl-C | Most GUI-predictable, breaks ⌘C-interrupt muscle memory | |

**User's choice:** Selection → copy; no selection → SIGINT. Configurable.
**Notes:** Ships with smart default; settings can force either extreme.

---

## Process Indicator Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| OSC 0/2 title primary + OS foreground-pgid poll fallback | Always populated + accurate; more Rust work | ✓ |
| OSC 0/2 title only | Simplest; often empty (default shell configs) | |
| OS foreground-pgid poll only | Consistent across shells; misses app-set custom titles | |

**User's choice:** OSC 0/2 title primary + OS foreground-pgid poll fallback.
**Notes:** Empty header segment considered a defect for the Variant B look — hence the OS-pgid fallback.

---

## Claude's Discretion

Left to researcher/planner (flagged in CONTEXT.md `<decisions>`):
- PTY ↔ webview transport mechanism, encoding, backpressure (must satisfy D-02 flood contract).
- Scrollback search implementation (xterm serialize/search addon vs Rust-mirrored buffer).
- Resize / SIGWINCH coordination (debounce, winsize ioctl timing, reflow).
- OSC 8 hyperlink activation + file-path detection regex (within PTY-05).

## Deferred Ideas

- Scrollback persistence across restart → A6.
- Sixel / inline images → L4+ (FEATURES §L1.4.9).
- Send-to-cell / terminal-output piping → L2.
- Per-pane shell override UI → A8 settings.

All deferrals were boundary clarifications, not scope creep.
