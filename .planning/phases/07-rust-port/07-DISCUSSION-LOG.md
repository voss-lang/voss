# Phase 7: rust-port - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-09
**Phase:** 07-rust-port
**Areas discussed:** Bridge framing protocol, Auto-download UX, Status line cadence, Sub-agent parallelism scope (+ Safety follow-up)

---

## Bridge framing protocol

| Option | Description | Selected |
|--------|-------------|----------|
| LSP-style headers | `Content-Length: <n>\r\n\r\n<body>`. Standard in language servers. Robust to embedded newlines. Slightly more parser code. | ✓ |
| Line-delimited JSON (NDJSON) | One JSON object per line. Simpler. Breaks on embedded newlines without escaping. | |
| MessagePack frames | Binary length-prefix. Faster, smaller. Harder to debug. | |

**User's choice:** LSP-style headers (Recommended)
**Notes:** Standard in rust-analyzer, pyright; framing handles tool output and source code with embedded newlines without escape gymnastics. Frame parser must reject negative/missing `Content-Length`, ignore unknown headers for forward compatibility. JSON body keeps the existing `{"v": 1, ...}` versioned envelope.

---

## Auto-download UX

| Option | Description | Selected |
|--------|-------------|----------|
| Prompt [y/N], persist decision | First run asks. Decision saved to `~/.config/voss/config.toml`. Non-TTY refuses with actionable error. SHA256 verified before exec. | ✓ |
| Silent download with stderr notice | No prompt. Downloads on first run, prints status. Faster onboarding. Some users dislike implicit network calls. | |
| Refuse with install instructions | Print install hint, exit 2. Forces explicit install. Cleanest, worst onboarding. | |
| Always fall back to Python harness | Use in-process Python harness if Rust binary missing. Slower cold start. Becomes "refuse" once Python harness is deleted. | |

**User's choice:** Prompt [y/N], persist decision (Recommended)
**Notes:** Privacy default — no implicit network. Persisted decision avoids re-prompt friction. Compiler verbs never trigger auto-download (always Python). SHA mismatch aborts, never execs.

---

## Status line cadence

| Option | Description | Selected |
|--------|-------------|----------|
| End of turn only | Matches current Python. One render after final answer. Simple. | ✓ |
| Live during streaming + end of turn | Updates as tokens arrive. Pinned to bottom row. Higher polish, more state. | |
| Always pinned (turn or idle) | Visible between turns, vim status line style. Most polished, most complex. | |

**User's choice:** End of turn only (Recommended for ship)
**Notes:** Lower scope, faster ship to parity. Raw-mode status line has its own bug surface that doesn't belong in the port. Live streaming and pinned status deferred to a future polish phase.

---

## Sub-agent parallelism scope

| Option | Description | Selected |
|--------|-------------|----------|
| Sequential only in R7, defer parallel to v1.3 | Match Python today. Ship faster. Parallel + dependency tracking is its own design problem. | |
| Add parallelism in R7 as opt-in flag | Schema gains `parallel_with: [step_idx]`. Default sequential, model opts steps into parallel groups. Schema drift risk. | |
| Add parallelism as default in R7 | Inspect step args for read-only tools, fan out automatically. Fastest UX. Highest risk of races and surprising behavior. | ✓ |

**User's choice:** Add parallelism as default in R7
**Notes:** Bold choice — explicit follow-up question on safety rule. Locked into static read-only/mutating classification (see Safety follow-up below). Phase 7's parallel default is **data-driven from the Plan schema**, not from a language-level `gather` keyword (which v1.3 will introduce and join up).

---

## Safety rule (follow-up to Sub-agent parallelism)

| Option | Description | Selected |
|--------|-------------|----------|
| Read-only tools parallel, mutating tools serial | Static rule based on tool's `is_mutating` flag. No model judgment needed. | ✓ |
| All parallel, model declares dependencies | Plan schema gains `depends_on: [step_idx]`. Model reasons about ordering. More flexible, more model error. | |
| All parallel, no ordering enforcement | Just fan everything out. Race conditions surface as bugs. Dangerous. | |
| Cap parallelism N steps, strict ordering only when explicit | Run up to N concurrent tools; preserve plan order otherwise. Compromise. | |

**User's choice:** Read-only tools parallel, mutating tools serial (Recommended)
**Notes:** Read-only set: `fs_read`, `fs_glob`, `fs_grep`, `git_status`, `git_diff`, `voss_check`. Mutating set: `fs_write`, `fs_edit`, `shell_run`. Tool definitions carry explicit `is_mutating: bool` so classification is data-driven, not pattern-matched. When a batch contains both, run read-only group concurrently first (await all), then run mutating steps in plan order. Concurrency cap on read group: 8 (tunable). Permission gate consulted per step before scheduling.

---

## Claude's Discretion

- Crate boundaries inside the workspace (which types live where).
- HTTP client tuning (timeouts, retry backoff).
- Test fixture organization inside each crate.
- Concurrency cap for parallel read group (start at 8).
- Exact `cargo-dist` config knobs.

## Deferred Ideas

- Live streaming status line and always-pinned status — future polish phase.
- Sequential-by-default + parallel-on-explicit-flag — fallback if parallel-default proves error-prone.
- `gather`-style language-level parallel sub-agents — v1.3 (when Voss compiler lowers `gather` keyword).
- Telemetry / usage reporting — off across Phase 7 even when added later.
- Windows distribution — DPAPI, MSIX, scoop. Post-v1.2.
- WASM build of `voss-cli` for browser harness — future milestone.
- MessagePack framing — JSON+LSP is debuggable; not needed at our scale.
- Silent auto-download — explicit prompt is the privacy default; revisit only if onboarding friction is measured.
