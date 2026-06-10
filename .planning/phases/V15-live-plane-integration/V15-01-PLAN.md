---
phase: V15-live-plane-integration
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/voss-app/src-tauri/src/lib.rs
  - crates/voss-app-core/src/sidecar.rs
  - apps/voss-app/src/org/live/sidecarClient.ts
  - apps/voss-app/src/org/live/__tests__/sidecarCommand.test.ts
autonomous: true
requirements: [VLIVE-01]
must_haves:
  truths:
    - "Invoking start_voss_serve twice for the same cwd yields one server process (same port/pid)"
    - "Two different cwds yield two separate server processes"
    - "A stale map entry (pid() == None after reap) triggers a fresh spawn, not a dead handshake"
    - "After app exit, kill -0 <pid> fails for every spawned server (no orphan)"
    - "The cwd is canonicalized and rejected if it escapes allowed workspace roots before any spawn"
  artifacts:
    - path: "apps/voss-app/src-tauri/src/lib.rs"
      provides: "start_voss_serve Tauri command + VossServeMap managed state + generate_handler registration"
      contains: "async fn start_voss_serve"
    - path: "apps/voss-app/src/org/live/sidecarClient.ts"
      provides: "Frontend invoke wrapper returning the typed ServeHandshake {port, token}"
      exports: ["startVossServe", "ServeHandshake"]
    - path: "crates/voss-app-core/src/sidecar.rs"
      provides: "reuse_if_alive + cwd_validation gated cargo tests (test module extension only; spawn impl frozen)"
      contains: "fn reuse"
  key_links:
    - from: "apps/voss-app/src/org/live/sidecarClient.ts"
      to: "start_voss_serve (Tauri command)"
      via: "invoke('start_voss_serve', { cwd })"
      pattern: "invoke.*start_voss_serve"
    - from: "apps/voss-app/src-tauri/src/lib.rs"
      to: "voss_app_core::sidecar::spawn_voss_serve"
      via: "command body calls spawn_voss_serve(&python, cwd)"
      pattern: "spawn_voss_serve"
---

<objective>
Expose the proven `voss serve` sidecar (`crates/voss-app-core/src/sidecar.rs`, commit `de93b4d`) as a Tauri command with per-workspace managed lifecycle. This is the phase keystone: every downstream plan (client construction, live SSE, structured pane, attach, lifecycle) needs a real `{port, token}` handshake in the webview, and only the Tauri side can spawn the server (V14 Pitfall 4 — the webview launcher imports node:child_process).

Purpose: Resolve V14 Pitfall 4 and give the frontend a single `startVossServe(cwd)` entry that lazily spawns one server per workspace cwd, reuses it if alive, and reaps all on app exit.
Output: `start_voss_serve` Tauri command + `VossServeMap` managed state + a typed frontend invoke wrapper (`sidecarClient.ts`), plus gated cargo tests proving reuse-if-alive and cwd validation.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/phases/V15-live-plane-integration/V15-SPEC.md
@.planning/phases/V15-live-plane-integration/V15-SPIKE-sidecar.md
@.planning/phases/V15-live-plane-integration/V15-RESEARCH.md
@.planning/phases/V15-live-plane-integration/V15-PATTERNS.md

<interfaces>
<!-- Contracts the executor needs. Extracted from codebase — no exploration required. -->

From crates/voss-app-core/src/sidecar.rs (FROZEN spawn impl — extend ONLY the test module):
```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServeHandshake { pub port: u16, pub token: String }   // lowercase fields — no IPC rename needed

pub struct VossServe { child: Child, pub handshake: ServeHandshake }
impl VossServe {
    pub fn pid(&self) -> Option<u32>           // None after the child is reaped — the reuse-if-alive sentinel
    pub async fn shutdown(mut self)            // start_kill + wait
}
pub fn python_path() -> String                 // VOSS_PYTHON > repo .venv/bin/python > python3
pub async fn spawn_voss_serve(python: &str, cwd: &std::path::Path) -> anyhow::Result<VossServe>
// existing gated test: spike_spawn_handshake_authed_request_and_reap (runs only when VOSS_SIDECAR_SPIKE=1)
```

From apps/voss-app/src-tauri/src/lib.rs (existing patterns to MIRROR):
```rust
use std::collections::{HashMap, HashSet};   // line 1 — HashMap already imported
use std::sync::{Arc, Mutex};                // Mutex already imported
type Reg<'a> = tauri::State<'a, Arc<PtyRegistry>>;            // type-alias pattern (line 127)
type AgentDb<'a> = tauri::State<'a, Mutex<Option<Connection>>>;
// .manage() chain at lines 1302-1306; generate_handler![ … ] at lines 1307-1370 (spawn_agent line 1316, run_decision line 1369)
// All commands return Result<T, String> via .map_err(|e| e.to_string()); lock poison → .map_err(|_| "lock poisoned".to_string())
```
</interfaces>
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| webview → Tauri command | `cwd` string crosses from the (lower-trust) webview into a process-spawn argument |
| Tauri child → loopback HTTP | spawned `voss serve` binds `127.0.0.1:<port>`; token is the only auth |
| app process → child process | child lifetime owned by `kill_on_drop` + managed-state map entry |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V15-01 | Tampering | `start_voss_serve(cwd)` | mitigate | Canonicalize `cwd` (`std::fs::canonicalize`) and reject if it is not a directory / escapes the workspace roots before calling `spawn_voss_serve`; return `Err("invalid workspace path")`. Mirrors the `is_safe_run_id` validation discipline (V5). |
| T-V15-02 | Denial of Service | orphan child after crash | mitigate | `kill_on_drop` (already in sidecar.rs) + reuse-if-alive `pid()` check removes stale entries; all map entries dropped on app exit reap their children. Cargo test `reuse_if_alive` proves stale-entry respawn. |
| T-V15-10 | Information Disclosure | handshake token in logs | mitigate | Never log the `token` field; the frontend wrapper returns it in-memory only. The command's `Err` strings carry stderr tails but NOT the token. |
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Tauri start_voss_serve command + managed state + cwd validation</name>
  <files>apps/voss-app/src-tauri/src/lib.rs, crates/voss-app-core/src/sidecar.rs</files>
  <read_first>
    - apps/voss-app/src-tauri/src/lib.rs (read lines 1-30 for the use block, 122-235 for the spawn_agent command + type-alias pattern, 1297-1373 for the .manage() chain and generate_handler! list — you are extending all three)
    - crates/voss-app-core/src/sidecar.rs (read in full — you ADD a cwd-validation helper at module scope and EXTEND the #[cfg(test)] mod tests at line 133; the spawn/handshake/reap impl is FROZEN and must stay byte-unchanged)
    - .planning/phases/V15-live-plane-integration/V15-PATTERNS.md (the lib.rs section gives the exact managed-state type alias, command body, .manage() line, and generate_handler! entry)
    - .planning/phases/V15-live-plane-integration/V15-RESEARCH.md (Pitfall 2 — VossServe is not Sync, use Mutex<HashMap>; Pitfall 5 — pid() returns None after reap; Pitfall 7 — ServeHandshake needs no serde rename)
  </read_first>
  <action>
    In `crates/voss-app-core/src/sidecar.rs`, add a public module-scope helper `pub fn validate_workspace_cwd(cwd: &str, allowed_roots: &[std::path::PathBuf]) -> Result<std::path::PathBuf, String>` that canonicalizes `cwd`, returns `Err("workspace path does not exist")` if canonicalize fails, returns `Err("workspace path is not a directory")` if not a dir, and returns `Err("workspace path is outside allowed roots")` if the canonical path is not equal-to or a descendant of any allowed root. When `allowed_roots` is empty, accept any existing directory (single-user local default per RESEARCH security domain V5). Do NOT touch `spawn_voss_serve`, `python_path`, `ServeHandshake`, or `VossServe` — those are frozen (T-V15-01).

    In `apps/voss-app/src-tauri/src/lib.rs`: (a) extend the `voss_app_core::sidecar` use to import `{spawn_voss_serve, python_path, ServeHandshake, VossServe, validate_workspace_cwd}`; (b) add the type alias `type VossServeMap<'a> = tauri::State<'a, Mutex<HashMap<String, VossServe>>>;` next to the existing `Reg`/`AgentDb` aliases; (c) add `async fn start_voss_serve(cwd: String, state: VossServeMap<'_>) -> Result<ServeHandshake, String>` — validate `cwd` via `validate_workspace_cwd(&cwd, &[])` first (T-V15-01); under a scoped lock, if `map.get(&cwd)` exists AND `serve.pid().is_some()` return `Ok(serve.handshake.clone())`, else drop the stale entry; outside the lock call `spawn_voss_serve(&python_path(), <canonical path>).await.map_err(|e| e.to_string())?`, clone the handshake, insert the `VossServe` into the map keyed by the ORIGINAL `cwd` string, and return the handshake (Pitfall 5). Use `.map_err(|_| "lock poisoned".to_string())` for lock acquisition; never hold the lock across the `.await` (T-V15-02). Never log `token` (T-V15-10); (d) add `.manage(Mutex::new(HashMap::<String, VossServe>::new()))` to the builder chain near line 1306; (e) add `start_voss_serve` to the `generate_handler!` list near line 1369.

    The command is `#[tauri::command]`; do not add the on_data Channel arg (this command has no streaming). Follow the `spawn_agent` async-command structure for everything else.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss/apps/voss-app/src-tauri && cargo build 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - `lib.rs` contains `async fn start_voss_serve` and `type VossServeMap`
    - `lib.rs` `.manage(` chain contains `Mutex::new(HashMap::<String, VossServe>::new())`
    - `generate_handler!` list contains the identifier `start_voss_serve`
    - `sidecar.rs` contains `pub fn validate_workspace_cwd`
    - `sidecar.rs` `spawn_voss_serve`/`python_path`/`ServeHandshake`/`VossServe` bodies are unchanged (only additions: the validate helper + test cases) — verify via `git diff crates/voss-app-core/src/sidecar.rs` showing no edits inside the existing fns
    - `cargo build` for the src-tauri crate exits 0
    - The command body acquires no lock across `.await` (manual read: lock scope closes before `spawn_voss_serve(...).await`)
  </acceptance_criteria>
  <done>The Tauri command compiles, holds a per-cwd `Mutex<HashMap<String, VossServe>>`, validates cwd before spawn, reuses live servers, respawns stale ones, and returns the serializable handshake.</done>
</task>

<task type="auto">
  <name>Task 2: Gated cargo reuse/validation tests + typed frontend invoke wrapper</name>
  <files>crates/voss-app-core/src/sidecar.rs, apps/voss-app/src/org/live/sidecarClient.ts, apps/voss-app/src/org/live/__tests__/sidecarCommand.test.ts</files>
  <read_first>
    - crates/voss-app-core/src/sidecar.rs (the #[cfg(test)] mod tests at line 133 — mirror the existing `spike_spawn_handshake_authed_request_and_reap` gate pattern at lines 177-181 for the new cases)
    - apps/voss-app/src/org/live/sseClient.ts (read in full — the module-level signal + exported-function + JSDoc style your new sidecarClient.ts mirrors; this is the closest analog in the same directory)
    - apps/voss-app/src/org/live/__tests__/sseClient.test.ts (the vitest structure — describe/it/afterEach reset, how invoke is mocked via vi.mock('@tauri-apps/api/core'))
    - .planning/phases/V15-live-plane-integration/V15-VALIDATION.md (the VLIVE-01 rows in the per-task map and the sidecarCommand.test.ts Wave-0 entry)
  </read_first>
  <action>
    Extend `crates/voss-app-core/src/sidecar.rs` `#[cfg(test)] mod tests` with two cases, BOTH gated behind `VOSS_SIDECAR_SPIKE=1` exactly like the existing spike test (early `eprintln! + return` when the env var is not `"1"`): (1) `reuse_if_alive` — spawn into a fresh tempdir, record `pid()`, simulate the reuse-if-alive branch by asserting that a second `spawn_voss_serve` for a DIFFERENT tempdir yields a DIFFERENT pid, and that after `shutdown()` a `VossServe`'s `pid()` returns `None` (proving the stale-entry sentinel); (2) `cwd_validation` (NOT gated — pure, no spawn) — assert `validate_workspace_cwd("/definitely/not/a/real/path/xyz", &[])` is `Err`, `validate_workspace_cwd(<a real existing tempdir>, &[])` is `Ok`, and `validate_workspace_cwd(<tempdir A>, &[<tempdir B>])` is `Err` (outside roots). Use `std::env::temp_dir()` / the `tempfile` crate if already a dev-dependency, else `std::env::temp_dir()` with a unique subdir.

    Create `apps/voss-app/src/org/live/sidecarClient.ts`: export `interface ServeHandshake { port: number; token: string }` and `async function startVossServe(cwd: string): Promise<ServeHandshake>` that calls `invoke<ServeHandshake>('start_voss_serve', { cwd })` (import `invoke` from `@tauri-apps/api/core`). Keep it a thin, side-effect-free wrapper — no signals, no client construction (that is Plan 02). Add a JSDoc note that the returned token is in-memory only and must never be logged (T-V15-10).

    Create `apps/voss-app/src/org/live/__tests__/sidecarCommand.test.ts`: `vi.mock('@tauri-apps/api/core')`, assert `startVossServe('/some/cwd')` calls `invoke` with `('start_voss_serve', { cwd: '/some/cwd' })` and returns the mocked `{port, token}` shape; assert the wrapper does not stringify/log the token (spy on console).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && cargo test -p voss-app-core sidecar::tests::cwd_validation 2>&1 | tail -8 && cd apps/voss-app && npx --no vitest run src/org/live/__tests__/sidecarCommand.test.ts 2>&1 | tail -12</automated>
  </verify>
  <acceptance_criteria>
    - `cargo test -p voss-app-core sidecar::tests::cwd_validation` exits 0 (the non-gated validation test runs and passes)
    - `VOSS_SIDECAR_SPIKE=1 cargo test -p voss-app-core sidecar::tests::reuse_if_alive` exits 0 (gated test runs when the env var is set)
    - Without the env var, `reuse_if_alive` prints the skip line and does not spawn (mirrors the existing spike test)
    - `sidecarClient.ts` exports `startVossServe` and `ServeHandshake`
    - `sidecarCommand.test.ts` passes: asserts `invoke('start_voss_serve', { cwd })` and the no-token-log behavior
    - `npx --no vitest run src/org/live/__tests__/sidecarCommand.test.ts` exits 0
  </acceptance_criteria>
  <done>The reuse-if-alive and cwd-validation behaviors are proven by cargo tests; the frontend has a typed, tested `startVossServe(cwd)` entry that all downstream plans consume.</done>
</task>

</tasks>

<verification>
- `cd apps/voss-app/src-tauri && cargo build` exits 0
- `cargo test -p voss-app-core sidecar::tests::cwd_validation` exits 0
- `VOSS_SIDECAR_SPIKE=1 cargo test -p voss-app-core sidecar` exits 0 (spike + reuse_if_alive)
- `cd apps/voss-app && npx --no vitest run src/org/live/__tests__/sidecarCommand.test.ts` exits 0
- `git diff crates/voss-app-core/src/sidecar.rs` shows additions only (validate helper + tests); no edits inside `spawn_voss_serve`/`python_path`/`ServeHandshake`/`VossServe`
</verification>

<success_criteria>
- `start_voss_serve` is callable from the webview via `startVossServe(cwd)` and returns `{port, token}`
- Same-cwd double invoke reuses one server; different cwds spawn two; stale (`pid()==None`) entries respawn (cargo-proven)
- `cwd` is canonicalized + validated before any spawn (T-V15-01)
- No token is logged anywhere (T-V15-10)
- The frozen `crates/voss-app-core` spawn implementation is byte-unchanged (only the validate helper + tests are added)
</success_criteria>

<output>
Create `.planning/phases/V15-live-plane-integration/V15-01-SUMMARY.md` when done
</output>
