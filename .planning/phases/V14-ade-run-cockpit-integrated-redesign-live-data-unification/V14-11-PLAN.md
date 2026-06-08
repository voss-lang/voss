---
phase: V14-ade-run-cockpit-integrated-redesign-live-data-unification
plan: 11
type: execute
wave: 7
depends_on: ["V14-09"]
files_modified:
  - crates/voss-app-core/src/pty/mod.rs
  - crates/voss-app-core/src/sandbox.rs
  - apps/voss-app/src-tauri/src/lib.rs
  - apps/voss-app/src/org/__tests__/capabilityTier.test.ts
  - apps/voss-app/src/org/capabilityTier.ts
autonomous: true
requirements: [VCKP-13]
must_haves:
  truths:
    - "A managed-launch agent started with scope tests/** cannot write outside it — an out-of-scope write is denied at the OS layer in a test (cargo test)"
    - "Budget-kill terminates the pane at the limit (budget_update PtyEvent -> pty_kill)"
    - "The UI shows the correct tier per CLI: non-hook CLI = tier B (sandbox+budget, no per-tool prompt, no error); hook-capable CLI = tier A; adopted running agent = tier C"
    - "OS scope-sandbox is the CLI-agnostic floor (sandbox-exec on macOS); the permission proxy is per-CLI best-effort on top; never overstate control"
    - "Scope paths are canonicalized/validated before building the sandbox profile (V5); profile starts from deny file-write*, never allow default"
  artifacts:
    - path: "crates/voss-app-core/src/sandbox.rs"
      provides: "Per-run sandbox profile generation + wrapper argv"
      contains: "sandbox-exec"
    - path: "apps/voss-app/src-tauri/src/lib.rs"
      provides: "spawn_managed_agent Tauri command (clone of spawn_agent + sandbox wrap)"
      contains: "spawn_managed_agent"
    - path: "apps/voss-app/src/org/capabilityTier.ts"
      provides: "Pure tier resolver (CLI -> A/B/C)"
  key_links:
    - from: "crates/voss-app-core/src/pty/mod.rs"
      to: "crates/voss-app-core/src/sandbox.rs"
      via: "wrap CommandBuilder argv with the sandbox launcher"
      pattern: "sandbox"
---

<objective>
VCKP-13 (D-13): managed launch + enforcement tiers. Wrap the existing `portable_pty` spawn site so an external CLI launches under an OS scope-sandbox (macOS `sandbox-exec -f profile.sb`; Linux `bwrap` best-effort) — the CLI-agnostic floor that denies out-of-scope writes at the kernel. Add a `spawn_managed_agent` Tauri command (clone of `spawn_agent` + sandbox wrap), budget-kill via the existing `budget_update`→`pty_kill` path, and a pure tier resolver (A = per-tool gate + sandbox + budget; B = sandbox + budget; C = observe-only). The sandbox is the floor; the permission proxy is per-CLI best-effort; tiers are shown honestly (adopt = always C).

Purpose: Recover real enforcement at the launch boundary (mitigation for the adopt external-CLI limit). This is the security floor — has an automated check (cargo test).
Output: sandbox.rs profile generator + wrapper, spawn_managed_agent command, tier resolver + test, sandbox cargo test.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-SPEC.md
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-RESEARCH.md
@.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md

<interfaces>
From crates/voss-app-core/src/pty/mod.rs:189-213: `spawn_command_session_with_env(cmd_binary, cmd_args, env, rows, cols, cwd)` — spawn site; the wrap point is `let mut cmd = CommandBuilder::new(cmd_binary); cmd.args(cmd_args);` (:212-213).
From apps/voss-app/src-tauri/src/lib.rs:183-220: `spawn_agent` — clone verbatim; body is ensure_registry → env_for_embedded_cli → spawn_command_session_with_env → registry.insert → start_reader → register_agent (:202,216). Clone into `spawn_managed_agent`, inserting the sandbox wrap + writing the tier into the registry.
From apps/voss-app/src/pane/pty-ipc.ts:16,122-130,201-205: `budget_update` PtyEvent + `invoke('pty_kill')` — budget-kill path.
From lib.rs:1066: `is_safe_run_id` canonicalization discipline (apply to scope paths — V5).
Sandbox argv (RESEARCH §VCKP-13a): macOS `sandbox-exec -f <profile.sb> <cli> <args...>`; profile.sb `(version 1)(allow default)(deny file-write*)(allow file-write* (subpath "<scope>"))(allow file-write* (subpath "/tmp"))`.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: sandbox.rs — per-run profile generator + wrapper argv + cargo test</name>
  <files>crates/voss-app-core/src/sandbox.rs, crates/voss-app-core/src/pty/mod.rs</files>
  <read_first>
    - crates/voss-app-core/src/pty/mod.rs:189-245 (spawn site + CommandBuilder wrap point :212-213)
    - apps/voss-app/src-tauri/src/lib.rs:1066 (is_safe_run_id canonicalization to mirror for scope paths)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-RESEARCH.md (Keystone-adjacent §VCKP-13a sandbox wrap + profile.sb + Security Domain V5/V12)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md (pty/mod.rs sandbox-wrap pattern)
  </read_first>
  <action>
    Create `crates/voss-app-core/src/sandbox.rs`: `generate_profile(scope_abs: &str) -> String` producing a Seatbelt profile that starts from `(deny file-write*)` and allows only `(subpath "<canonical scope>")` + `/tmp` (V12 — never widen). Canonicalize + validate the scope path first (mirror `is_safe_run_id`; reject traversal — V5). `wrap_argv(cmd_binary, cmd_args, profile_path, platform) -> (String, Vec<String>)` returning the sandboxed argv: macOS → `("sandbox-exec", ["-f", profile_path, cmd_binary, ...cmd_args])`; Linux → `bwrap` argv (best-effort); if no sandbox tool available → return the original argv unchanged and signal tier-downgrade. Add a `wrap` hook in `pty/mod.rs` at the `CommandBuilder` site (:212-213) used only when a managed flag + scope are supplied (the unmanaged path is byte-for-byte unchanged — no regression). Add a `cargo test` in `sandbox.rs`: write a temp file fixture, generate a profile scoped to `tests/**`, and assert (a) the profile denies `file-write*` outside the subpath and (b) on macOS, an actual `sandbox-exec`-wrapped `touch` outside the scope returns non-zero (out-of-scope write denied at the OS layer); gate the OS-exec portion behind `#[cfg(target_os = "macos")]`, keeping the profile-string assertion cross-platform.
  </action>
  <verify>
    <automated>cargo test -p voss-app-core sandbox</automated>
  </verify>
  <acceptance_criteria>
    - `generate_profile` starts from `deny file-write*` and allows only the canonical scope subpath + `/tmp`.
    - Scope paths are canonicalized/validated (traversal rejected).
    - The cargo test asserts an out-of-scope write is denied (OS-exec assertion on macOS; profile-string assertion cross-platform).
    - The unmanaged spawn path in `pty/mod.rs` is unchanged (no regression).
  </acceptance_criteria>
  <done>OS scope-sandbox floor implemented + kernel-denial test green; unmanaged path untouched.</done>
</task>

<task type="auto">
  <name>Task 2: spawn_managed_agent command (clone spawn_agent + sandbox wrap + tier) + budget-kill</name>
  <files>apps/voss-app/src-tauri/src/lib.rs</files>
  <read_first>
    - apps/voss-app/src-tauri/src/lib.rs:183-220 (spawn_agent to clone verbatim)
    - crates/voss-app-core/src/sandbox.rs (task 1 — wrap_argv/generate_profile)
    - apps/voss-app/src/pane/pty-ipc.ts:16,122-130,201-205 (budget_update + pty_kill — budget-kill wiring)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-PATTERNS.md (lib.rs spawn_managed_agent pattern)
  </read_first>
  <action>
    Add `spawn_managed_agent` to `lib.rs` by cloning `spawn_agent` (:183-220) and inserting, before `spawn_command_session_with_env`: write the per-run `profile.sb` (from `sandbox::generate_profile(scope)`), then `sandbox::wrap_argv(...)` to transform `cli_binary`/`cli_args` into the sandboxed argv. Register the resolved capability tier (A/B/C) into the registry alongside the agent. Keep the rest of the body identical (registry insert, start_reader, register_agent — Bridge B sessionId passthrough preserved). Register the new command in the Tauri `invoke_handler`. Budget-kill: ensure the existing `budget_update` PtyEvent path can trigger `pty_kill` at the limit for managed agents (wire the threshold check — coarse/universal tier-C control). If no sandbox tool is available, downgrade to the unmanaged spawn and record the lower tier honestly (never silently claim enforcement).
  </action>
  <verify>
    <automated>cargo build -p voss-app-core && cd apps/voss-app/src-tauri && cargo build 2>&1 | tail -3</automated>
  </verify>
  <acceptance_criteria>
    - `spawn_managed_agent` exists, wraps the CLI argv via `sandbox::wrap_argv`, writes the per-run profile, and records the tier in the registry.
    - The command is registered in the Tauri invoke_handler; the project builds.
    - Budget-kill threshold can terminate a managed pane via `pty_kill`.
    - Sandbox-unavailable path downgrades tier honestly (no false enforcement claim).
  </acceptance_criteria>
  <done>Managed-launch command spawns under the sandbox with an honest tier; budget-kill wired.</done>
</task>

<task type="auto">
  <name>Task 3: capabilityTier.ts pure resolver + test</name>
  <files>apps/voss-app/src/org/capabilityTier.ts, apps/voss-app/src/org/__tests__/capabilityTier.test.ts</files>
  <read_first>
    - apps/voss-app/src/org/model/normalized.ts (CapabilityTier type)
    - apps/voss-app/src/org/boardDerive.ts:1-3 (pure-module header)
    - .planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-SPEC.md (VCKP-13 tier definitions A/B/C)
  </read_first>
  <action>
    Create `capabilityTier.ts` (pure): `resolveTier({cli, managed, hookCapable, adopted}): 'A'|'B'|'C'`. Rules: adopted running agent → always C; managed + hook-capable CLI → A; managed + non-hook CLI → B; unmanaged → C (observe-only). Write `capabilityTier.test.ts`: a non-hook managed CLI → B (no per-tool prompt, no error); a hook-capable managed CLI → A; an adopted running agent → C; assert the resolver never returns A for an adopted agent (no retro-sandbox).
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/org/__tests__/capabilityTier.test.ts</automated>
  </verify>
  <acceptance_criteria>
    - resolveTier: non-hook managed → B; hook-capable managed → A; adopted → C (always).
    - Adopted never resolves to A; unmanaged → C.
    - Pure module (no solid-js import).
  </acceptance_criteria>
  <done>Tier resolver matches the honest A/B/C model; adopt locked to C.</done>
</task>

</tasks>

<verification>
- `cargo test -p voss-app-core sandbox` green (kernel-denial floor).
- `cargo build` (core + src-tauri) succeeds; `npx vitest run src/org/__tests__/capabilityTier.test.ts` green.
- Unmanaged spawn path unchanged; tiers honest (adopt = C).
</verification>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Voss → external CLI process | Voss spawns an untrusted CLI; the PTY stream is the only visibility into an external agent |
| external CLI → filesystem | The CLI's tools write to disk; out-of-scope writes are the primary blast-radius risk |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V14-01 | Tampering/Elevation | external CLI filesystem writes (`pty/mod.rs` spawn) | mitigate | OS sandbox (`sandbox-exec -f profile.sb`, `deny file-write*` + scope subpath) — kernel-enforced, CLI-agnostic (Task 1) |
| T-V14-02 | DoS | runaway agent cost/tokens | mitigate | budget-kill via `budget_update` PtyEvent → `pty_kill` at limit (Task 2) |
| T-V14-03 | Repudiation/spoofed control | tier UI claims gating it lacks | mitigate | honest tier resolver — adopt = C, non-hook = B, never claim per-tool gate on PTY-only agents (Task 3) |
| T-V14-04 | Tampering | path traversal in scope before profile build | mitigate | canonicalize + validate scope (mirror `is_safe_run_id`) before `generate_profile` (Task 1, V5) |
| T-V14-05 | Elevation | sandbox profile too permissive (`allow default` write) | mitigate | profile starts from `deny file-write*`; allow only scope subpath + `/tmp` (Task 1, V12) |
| T-V14-06 | Elevation | CLI runs `--dangerously-skip-permissions` to bypass its own prompt | accept (sandbox covers) | sandbox (tier-A floor) still denies at kernel even if the CLI skips its prompt; never rely on the proxy alone |
| T-V14-SC | Tampering | npm/pip/cargo installs | mitigate | no new packages introduced (RESEARCH Package Legitimacy Audit: none); OS tools ship with macOS/Linux |
</threat_model>

<success_criteria>
Managed launch enforces a kernel-level scope floor (out-of-scope write denied in a cargo test), budget-kills at the limit, and surfaces honest A/B/C tiers (adopt = C); the unmanaged path is unregressed.
</success_criteria>

<output>
Create `.planning/phases/V14-ade-run-cockpit-integrated-redesign-live-data-unification/V14-11-SUMMARY.md` when done.
</output>
