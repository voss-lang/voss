---
phase: A2-voss-app-pty-pane
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/voss-app/package.json
  - apps/voss-app/vitest.config.ts
  - apps/voss-app/src/pane/__tests__/PasteGuard.test.tsx
  - apps/voss-app/scripts/test-flood-perf.ts
  - apps/voss-app/e2e/pty.spec.ts
  - apps/voss-app/playwright.config.ts
  - crates/voss-app-core/Cargo.toml
  - crates/voss-app-core/src/lib.rs
  - crates/voss-app-core/src/pty/mod.rs
  - crates/voss-app-core/src/pty/tests.rs
  - Cargo.toml
autonomous: false
requirements: [PTY-01, PTY-02, PTY-03, PTY-04, PTY-05, PTY-06, PTY-07, PTY-08]
user_setup: []

must_haves:
  truths:
    - "All test commands from A2-VALIDATION.md exist and execute (red is acceptable; missing is not)"
    - "@xterm/xterm is pinned to exactly 5.5.0 (no caret/tilde) and the pin is enforced by a check"
    - "voss-app-core crate is a workspace member and compiles with an empty PtyRegistry"
    - "User has confirmed the D-01 canvas-pin-vs-v6 tradeoff at the Wave 0 checkpoint"
    - "All [ASSUMED] npm + crate packages verified legitimate before any install"
  artifacts:
    - path: "crates/voss-app-core/Cargo.toml"
      provides: "voss-app-core crate manifest with pinned + workspace deps"
      contains: "portable-pty"
    - path: "crates/voss-app-core/src/lib.rs"
      provides: "Tauri plugin init + PtyRegistry skeleton"
      contains: "pub mod pty"
    - path: "crates/voss-app-core/src/pty/tests.rs"
      provides: "Red Rust tests for PTY-01 spawn-env, PTY-02 round-trip, PTY-06 pgid"
      contains: "test_pty_spawn_env"
    - path: "apps/voss-app/scripts/test-flood-perf.ts"
      provides: "D-02 flood performance harness scaffold (red)"
      min_lines: 20
    - path: "apps/voss-app/src/pane/__tests__/PasteGuard.test.tsx"
      provides: "Red Vitest tests for PTY-04 paste banner + bypass"
      contains: "PasteGuard"
    - path: "apps/voss-app/package.json"
      provides: "Pinned xterm deps + vitest/playwright devDeps"
      contains: "\"@xterm/xterm\": \"5.5.0\""
  key_links:
    - from: "Cargo.toml"
      to: "crates/voss-app-core"
      via: "workspace members array"
      pattern: "voss-app-core"
    - from: "apps/voss-app/package.json"
      to: "@xterm/xterm@5.5.0"
      via: "exact version pin + pnpm.overrides"
      pattern: "\"@xterm/xterm\""
---

<objective>
Wave 0 foundation: create every test file referenced by A2-VALIDATION.md (as red/failing
scaffolds), pin the xterm.js v5 dependency set per D-01a, scaffold the `voss-app-core`
Rust crate as a workspace member, and resolve the D-01-vs-xterm-v6 user decision before
any feature work begins.

Purpose: Per A2-VALIDATION.md, no feature task may depend on a missing test. This plan
makes the Nyquist contract satisfiable — every PTY-0N requirement gets a real automated
command that exists (failing) before A2-02..05 implement against it. It also closes the
single hard upstream conflict (Canvas renderer removed in xterm v6) via an explicit user
checkpoint, and gates all [ASSUMED] package installs behind legitimacy verification.

Output: Compiling empty `voss-app-core` crate, pinned `package.json`, red test suite
across Vitest/cargo-test/Playwright, flood-perf harness scaffold, user-confirmed D-01 path.
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
@apps/voss-app/CONCEPT.md

<interfaces>
<!-- Workspace Cargo conventions the executor MUST mirror (A2-PATTERNS.md §Cargo.toml). -->
<!-- Source: /Users/benjaminmarks/Projects/Voss/Cargo.toml -->

[workspace] members currently:
  crates/voss-cli, voss-agent, voss-providers, voss-auth, voss-tools, voss-render, voss-bridge
  → ADD "crates/voss-app-core"

[workspace.package]: edition = "2021", rust-version = "1.75"

[workspace.dependencies] already define (use `{ workspace = true }`, do NOT re-pin):
  tokio (features=["full"]), serde (features=["derive"]), serde_json, anyhow,
  thiserror, tracing, uuid (features=["v4","serde"]), tempfile (dev)

NEW explicit-version deps (NOT in workspace — pin in voss-app-core/Cargo.toml):
  tauri = { version = "2", features = ["wry"] }
  portable-pty = "0.9.0"
  nix = { version = "0.31", features = ["signal", "term", "process"] }
  [target.'cfg(target_os = "macos")'.dependencies] libproc = "0.14"

PtyRegistry skeleton (A2-PATTERNS.md lib.rs analog — voss-agent/src/lib.rs flat pub mod + pub use):
  pub mod pty; pub use pty::... ; tauri::plugin::Builder::new("voss-app-core")
</interfaces>
</context>

<tasks>

<task type="checkpoint:human-verify" gate="blocking-human">
  <name>Task 0: D-01 canvas-pin vs xterm-v6 decision + package legitimacy gate</name>
  <read_first>
    - .planning/phases/A2-voss-app-pty-pane/A2-RESEARCH.md "## CRITICAL RISK: xterm.js Canvas Renderer vs v6.0.0" (lines 66-81) and "## Open Questions" item 1
    - .planning/phases/A2-voss-app-pty-pane/A2-RESEARCH.md "## Package Legitimacy Audit" (lines 159-177)
    - .planning/phases/A2-voss-app-pty-pane/A2-CONTEXT.md D-01a (locked: pin v5.5.0)
  </read_first>
  <what-built>
    Two blocking gates presented together before ANY install:

    GATE A — D-01 vs xterm v6 (RESEARCH Open Question 1):
    CONTEXT D-01a already locks the decision to pin `@xterm/xterm@5.5.0` +
    `@xterm/addon-canvas@0.7.0` (user explicitly chose v5 pin over WebGL/v6 post-research).
    RESEARCH asks the planner to surface the tradeoff one final time at Wave 0. Restate:
    - Path locked: v5.5.0 exact pin + Canvas addon. Cost: frozen on v5 line, tracked
      migration debt (see Deferred Ideas in objective of A2-04).
    - Alternative the user already declined: WebGL addon + v6 (vendor-recommended).

    GATE B — Package legitimacy (slopcheck was unavailable at research time; all packages
    `[ASSUMED]`). Packages requiring verification before install:
    - npm: @xterm/xterm@5.5.0, @xterm/addon-canvas@0.7.0, @xterm/addon-fit@0.11.0,
      @xterm/addon-search@0.16.0, @xterm/addon-web-links@0.12.0
    - crates: portable-pty@0.9.0, nix@0.31.3, libproc@0.14.11
  </what-built>
  <how-to-verify>
    GATE A: Confirm the v5.5.0 canvas pin path (re-affirm D-01a) OR direct a change to
      WebGL+v6 (would require a CONTEXT.md amendment — out of this plan's scope).
    GATE B: For each [ASSUMED] package, verify legitimacy:
      1. Visit https://www.npmjs.com/package/@xterm/xterm (and each @xterm/* addon) —
         confirm publisher is the xtermjs org, repo github.com/xtermjs/xterm.js.
      2. Visit https://crates.io/crates/portable-pty , /nix , /libproc — confirm
         repos: github.com/wez/wezterm , github.com/nix-rust/nix ,
         github.com/andrewdavidmackenzie/libproc-rs.
      3. Confirm none are typosquats and download counts are non-trivial.
  </how-to-verify>
  <acceptance_criteria>
    - User types "approved" affirming the v5.5.0 canvas pin (GATE A) AND that all 8
      packages are legitimate (GATE B), OR describes the required change.
    - This checkpoint is NEVER auto-approved (workflow.auto_advance ignored) — it is the
      `T-A2-SC` supply-chain mitigation.
  </acceptance_criteria>
  <resume-signal>Type "approved" (both gates) or describe required changes</resume-signal>
</task>

<task type="auto">
  <name>Task 1: Scaffold voss-app-core crate + workspace registration</name>
  <files>Cargo.toml, crates/voss-app-core/Cargo.toml, crates/voss-app-core/src/lib.rs, crates/voss-app-core/src/pty/mod.rs</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/Cargo.toml (workspace members + [workspace.dependencies] — the exact list this task extends)
    - .planning/phases/A2-voss-app-pty-pane/A2-PATTERNS.md "### crates/voss-app-core/Cargo.toml" (lines 48-73) and "### crates/voss-app-core/src/lib.rs" (lines 76-102)
    - crates/voss-agent/src/lib.rs (the flat `pub mod` + `pub use` re-export analog)
  </read_first>
  <action>
    Add `"crates/voss-app-core"` to the workspace `members` array in the root
    `/Users/benjaminmarks/Projects/Voss/Cargo.toml` (do NOT touch any other workspace
    field). Create `crates/voss-app-core/Cargo.toml`: `[package]` name `voss-app-core`,
    `edition.workspace = true` (or literal `edition = "2021"` to match
    `[workspace.package]`), `rust-version` matching workspace. `[dependencies]`: pin
    `tauri = { version = "2", features = ["wry"] }`, `portable-pty = "0.9.0"`,
    `nix = { version = "0.31", features = ["signal", "term", "process"] }`; use
    `{ workspace = true }` for `tokio`, `serde`, `serde_json`, `anyhow`, `thiserror`,
    `uuid`. Add `tempfile = { workspace = true }` under `[dev-dependencies]`. Add
    `[target.'cfg(target_os = "macos")'.dependencies]` with `libproc = "0.14"`.

    Create `src/lib.rs` mirroring the voss-agent flat-module analog: `pub mod pty;`,
    a `pub use` re-exporting the (not-yet-implemented) command symbols, and an
    `init<R: tauri::Runtime>()` returning a `tauri::plugin::TauriPlugin<R>` via
    `tauri::plugin::Builder::new("voss-app-core")` that manages `PtyRegistry::default()`
    in `.setup`. Create `src/pty/mod.rs` declaring submodules
    (`pub mod commands; pub mod reader; pub mod writer; pub mod foreground;
    #[cfg(test)] mod tests;`) and a minimal `#[derive(Default)] pub struct PtyRegistry`
    holding a `Mutex<HashMap<String, ...>>`-shaped field (stub fields acceptable this
    plan; A2-02 fills the session type). Add empty stub files for `commands.rs`,
    `reader.rs`, `writer.rs`, `foreground.rs` containing only a module doc comment so the
    crate compiles. NO PTY logic in this plan.
  </action>
  <verify>
    <automated>cargo build -p voss-app-core 2>&1 | tail -5 && cargo metadata --format-version 1 2>/dev/null | grep -q '"name":"voss-app-core"' && echo CRATE_REGISTERED</automated>
  </verify>
  <acceptance_criteria>
    - `cargo build -p voss-app-core` exits 0.
    - `cargo metadata` lists `voss-app-core` as a workspace package.
    - `crates/voss-app-core/Cargo.toml` contains the literal strings `portable-pty`,
      `tauri`, and `workspace = true` (for tokio/serde at minimum).
    - Root `Cargo.toml` `members` array contains `"crates/voss-app-core"`.
  </acceptance_criteria>
  <done>voss-app-core compiles as an empty workspace crate with a Tauri plugin init shell and empty pty submodules.</done>
</task>

<task type="auto">
  <name>Task 2: Pin frontend deps + create red test scaffolds (Vitest, Playwright, flood-perf, Rust)</name>
  <files>apps/voss-app/package.json, apps/voss-app/vitest.config.ts, apps/voss-app/playwright.config.ts, apps/voss-app/src/pane/__tests__/PasteGuard.test.tsx, apps/voss-app/scripts/test-flood-perf.ts, apps/voss-app/e2e/pty.spec.ts, crates/voss-app-core/src/pty/tests.rs</files>
  <read_first>
    - .planning/phases/A2-voss-app-pty-pane/A2-VALIDATION.md "## Per-Task Verification Map" (lines 40-59) and "## Wave 0 Requirements" (lines 77-85) — the exact command strings each scaffold must satisfy
    - .planning/phases/A2-voss-app-pty-pane/A2-RESEARCH.md "## Standard Stack" installation block (lines 138-156) — exact package versions
    - .planning/phases/A2-voss-app-pty-pane/A2-RESEARCH.md "### D-02 Flood Performance Assertion" (lines 861-873) — metric the perf harness asserts
    - .planning/phases/A2-voss-app-pty-pane/A2-PATTERNS.md "### apps/voss-app/src/pane/PasteGuard.tsx" (lines 490-513) — the PasteGuard signal interface the test targets
  </read_first>
  <action>
    Create/extend `apps/voss-app/package.json`. `dependencies` MUST use EXACT pins (no
    `^`/`~`): `"@xterm/xterm": "5.5.0"`, `"@xterm/addon-canvas": "0.7.0"`,
    `"@xterm/addon-fit": "0.11.0"`, `"@xterm/addon-search": "0.16.0"`,
    `"@xterm/addon-web-links": "0.12.0"`, `"@tauri-apps/api": "2.11.0"`,
    `"solid-js": "1.9.13"`. Add a `pnpm.overrides` block forcing `"@xterm/xterm": "5.5.0"`
    so `pnpm update` cannot bump it (Pitfall 1). `devDependencies`: `vitest`,
    `@testing-library/dom`, `@playwright/test`, `tsx`, `jsdom`. Add an npm script
    `"check:xterm-pin"` that fails non-zero if the resolved `@xterm/xterm` version is not
    exactly `5.5.0` (read `node_modules/@xterm/xterm/package.json` version; if
    node_modules absent, assert the `package.json` declared value is the literal
    `"5.5.0"` — pin gate must work pre-install). Run `pnpm install` after writing
    package.json (legitimacy already approved in Task 0).

    Create `vitest.config.ts` (jsdom environment, include
    `src/**/__tests__/**/*.test.tsx`) and `playwright.config.ts` (testDir `e2e/`).

    Create RED scaffolds — each MUST be a real runnable test that FAILS for "not
    implemented", never `test.skip`:
    - `src/pane/__tests__/PasteGuard.test.tsx`: import the (future) `PasteGuard`
      component; two tests — "multi-line paste shows banner" and "⌘⇧V bypasses banner" —
      each currently `expect(false).toBe(true)` with a `// RED: PTY-04 — A2-04`
      comment, asserting the documented `PasteGuardProps` shape.
    - `e2e/pty.spec.ts`: Playwright specs named to satisfy the VALIDATION command
      strings — `pty-scrollback`, `pty-clear`, `pty-copy`, `pty-sigint`, `pty-osc8`,
      `pty-title`, `pty-exit-restart` — each a `test()` that currently
      `expect(false).toBeTruthy()` with `// RED: <PTY-id> — <owning plan>` comments.
    - `scripts/test-flood-perf.ts`: a `tsx`-runnable script exporting a `main()` that
      currently `process.exit(1)` with a printed `RED: D-02 flood-perf not implemented`
      banner; document (in comments) the p95<33ms rAF + <200ms echo assertion it will
      enforce in A2-05. Accept a `--cat` flag arg (parsed, unused yet).
    - `crates/voss-app-core/src/pty/tests.rs`: `#[test]` functions
      `test_pty_spawn_env`, `test_pty_round_trip`, `test_foreground_pgid` each
      `panic!("RED: <PTY-id> not implemented — A2-02")`. Wire `mod tests;` (already
      declared cfg(test) in Task 1) so `cargo test -p voss-app-core` discovers them.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app && grep -q '"@xterm/xterm": "5.5.0"' package.json && test -f vitest.config.ts && test -f playwright.config.ts && test -f src/pane/__tests__/PasteGuard.test.tsx && test -f scripts/test-flood-perf.ts && test -f e2e/pty.spec.ts && test -f /Users/benjaminmarks/Projects/Voss/crates/voss-app-core/src/pty/tests.rs && grep -q test_pty_spawn_env /Users/benjaminmarks/Projects/Voss/crates/voss-app-core/src/pty/tests.rs && echo SCAFFOLDS_PRESENT && cargo test -p voss-app-core 2>&1 | grep -q -E 'FAILED|panicked' && echo RUST_TESTS_RED</automated>
  </verify>
  <acceptance_criteria>
    - `package.json` contains the literal `"@xterm/xterm": "5.5.0"` (exact, no caret) and
      a `pnpm.overrides` entry for it.
    - All six scaffold files exist at the exact paths in A2-VALIDATION.md Wave 0 list.
    - `cargo test -p voss-app-core` runs and the three named tests FAIL (red), proving
      they are discovered, not skipped.
    - `pnpm vitest run PasteGuard --reporter=dot` runs and fails red (not "no tests
      found").
    - No test file uses `.skip`, `.todo`, or watch-mode flags.
  </acceptance_criteria>
  <done>Every A2-VALIDATION.md command resolves to a real failing test/script; xterm v5 pin is enforced by a check that survives pnpm update.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| npm / crates.io → build | Third-party packages enter the build; slopcheck unavailable, all `[ASSUMED]` |
| developer machine → workspace | Crate added to shared workspace build graph |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A2-SC | Tampering | npm + crates.io installs (8 [ASSUMED] packages) | mitigate | Task 0 GATE B blocking-human checkpoint verifies each package on npmjs.com / crates.io against its known official repo before any install; never auto-approved |
| T-A2-01 | Tampering | `@xterm/xterm` version drift via `pnpm update` to v6 | mitigate | Exact `5.5.0` pin + `pnpm.overrides` + `check:xterm-pin` script that fails the build if resolved version ≠ 5.5.0 |
| T-A2-02 | Denial of Service | Skipped/empty test scaffolds masking unimplemented security paths | mitigate | All scaffolds are red (assert-fail/panic), never `.skip`; Rust verify greps for actual FAILED/panicked output |
</threat_model>

<verification>
- `cargo build -p voss-app-core` exits 0; `voss-app-core` appears in `cargo metadata`.
- `cargo test -p voss-app-core` discovers and FAILS the three red Rust tests.
- `apps/voss-app/package.json` pins `@xterm/xterm` to exact `5.5.0` with `pnpm.overrides`.
- All six A2-VALIDATION.md Wave 0 files exist and are red (not skipped).
- Task 0 checkpoint approved (D-01 path + package legitimacy).
</verification>

<success_criteria>
- voss-app-core is a compiling workspace member with empty pty submodules + plugin init.
- Frontend deps pinned per D-01a; pin enforced by `check:xterm-pin`.
- Every PTY-0N requirement has an existing failing automated command.
- D-01-vs-v6 and supply-chain gates resolved by the user.
</success_criteria>

<output>
Create `.planning/phases/A2-voss-app-pty-pane/A2-01-SUMMARY.md` when done
</output>
