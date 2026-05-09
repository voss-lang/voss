---
phase: 07
slug: rust-port
milestone: v1.2
status: planned
depends_on:
  - milestone v1.1 H1-H5 close (Python harness feature-complete + eval suite green)
  - .planning/CODEX-OAUTH-PLAN.md Phase A complete (Codex wire fixtures captured) before R8 starts
reference:
  - .planning/RUST-PORT-PLAN.md
  - .planning/HARNESS-PLAN.md
  - .planning/CODEX-OAUTH-PLAN.md
requirements:
  - RUST-01..32
---

# Phase 07 — Rust Harness Shell

## Intent

Replace the Python harness shell (`voss/harness/`) with a Rust binary
(`crates/voss-cli/`) at functional parity, ship it as a single static install
across macOS arm64/x86_64 and Linux x86_64/arm64, and keep the Python
compiler reachable through a stable JSON-RPC bridge.

The Voss compiler (`voss/parser.py`, `voss/analyzer.py`, `voss/codegen.py`)
and the runtime (`voss_runtime/*`) stay Python forever. They are out of scope
for this phase except where they receive **non-breaking additions** to
support the bridge contract (e.g. ensuring `voss check --json` and
`voss compile --json` exist and emit a versioned envelope).

## Why this phase exists

The Python harness ships and works (v1.1 milestone). Two structural problems
make it unsuitable for distribution at scale:

1. **Cold start.** Importing pydantic + click + rich + httpx + lark costs
   ~700ms before the first byte of any agent verb. For one-shot
   `voss do "<task>"` invocations this dominates perceived latency.
2. **Distribution.** `pip install voss` requires Python 3.11+ on PATH,
   arch-matched wheels (we already hit Rosetta arm64 mismatches twice), and
   a working venv. Single-binary distribution via PyInstaller is fragile and
   ~80MB. Reference harnesses (Codex CLI: Rust, Pi CLI: Rust, Claude Code:
   Bun-compiled Node) are all compiled, ≤15MB, and install in one command.

A Rust port of the harness shell — with the compiler reached over a long-
lived JSON-RPC bridge so Python startup is paid once per session, not per
call — closes both gaps without forcing a compiler rewrite.

## Phase scope

In:

- New Cargo workspace at repo root, 7 crates: `voss-cli` (binary),
  `voss-agent`, `voss-providers`, `voss-auth`, `voss-tools`, `voss-render`,
  `voss-bridge`.
- New Python module `voss/bridge_server.py` (~80 LOC) — JSON-RPC over stdio
  server that exposes the existing compiler verbs to Rust.
- Re-export of compiler `--json` flags on `check` and `compile` if not
  already present (additive only).
- Distribution pipeline via `cargo-dist`, brew tap, and a Python dispatcher
  in `voss.cli:main` that detects + auto-downloads the matching `voss-cli`
  binary on first agent verb invocation.

Out (deferred):

- Native compilation of the Voss compiler / runtime to Rust.
- Voss-the-language port to a non-Python target.
- Windows distribution.
- IDE / editor integration.
- Embedded WASM build of `voss-cli` for browser harnesses.

## Plan order

Each plan ends with the Rust workspace compiling, all prior plans' tests
passing, and a runnable demo. Waves are sequential.

| Wave | Plan id | Plan | RUST IDs |
|------|---------|------|----------|
| R1   | 07-01   | Workspace skeleton, all 7 crates stubbed, `voss-bridge` round-trip for `voss ast` | RUST-01..04 |
| R2   | 07-02   | `voss-auth`: Keychain + file discovery, refresh both Anthropic + Codex, doctor verb parity | RUST-05..08 |
| R3   | 07-03   | Anthropic OAuth provider: preamble, tool-use translation, refresh-on-401, live smoke | RUST-09..12 |
| R4   | 07-04   | Sandbox + 9 tools (fs_*, shell_run, git_*, voss_*) | RUST-13..16 |
| R5   | 07-05   | Renderer (Tty/Plain/Ndjson) + permission gate (interactive + persisted) | RUST-17..20 |
| R6   | 07-06   | Sessions: list/resume/save, JSON wire-compat with Python | RUST-21..23 |
| R7   | 07-07   | `run_turn` parity, chat REPL, slash commands, status line | RUST-24..27 |
| R8   | 07-08   | Codex OAuth provider with full Codex CLI wire format | RUST-28..30 |
| R9   | 07-09   | Distribution: signed binaries, brew tap, pip dispatcher | RUST-31..32 |

## Cross-cutting constraints

- The Rust binary **never** imports or links libpython. Python interaction
  is `std::process::Command` only.
- The Voss compiler and runtime are read-only across this phase. Allowed
  additive changes: `voss/bridge_server.py` (new), `--json` flags on
  read-only compiler verbs (additive only).
- Schema drift between Rust serde structs and Python pydantic models is a
  CI failure. Snapshot tests enforce equivalence at every release.
- Anthropic and OpenAI request bodies are snapshot-tested per provider;
  live smokes are opt-in (`--live` / nightly) and never default in CI.
- `voss/harness/` (Python) stays in the repo across this phase. It is the
  fallback path that v1.2 keeps green and ships alongside the Rust binary,
  removed only after one release of Rust-as-default with no rollbacks.
- Test parity is non-negotiable: every test in `tests/harness/` must have a
  Rust integration equivalent and pass before deletion of any Python file.

## Success criteria (phase-level)

1. `voss --version` returns in ≤50ms cold on macOS arm64.
2. Every Python harness test has a passing Rust integration equivalent.
3. Parity suite confirms byte-identical output between Python and Rust
   binaries for `--help`, `doctor`, `sessions`, and `--json` agent verbs.
4. Live smokes pass against Anthropic OAuth and Codex OAuth subscriptions.
5. `brew install voss/tap/voss` produces a working install where agent
   verbs work without Python on PATH.
6. `pip install voss` continues to work and auto-downloads the matching
   `voss-cli` binary on first agent verb invocation.
7. `voss/harness/` is deletable without breaking any user-visible feature.

Detailed design, crate-by-crate API surface, dependency picks, and risk
register live in `.planning/RUST-PORT-PLAN.md`.
