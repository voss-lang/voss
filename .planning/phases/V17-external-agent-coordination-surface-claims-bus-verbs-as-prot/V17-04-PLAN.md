---
phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot
plan: 04
type: execute
wave: 2
depends_on: [V17-01]
files_modified:
  - apps/voss-app/src/pane/slugRegistry.ts
  - apps/voss-app/src/pane/slugRegistry.test.ts
  - apps/voss-app/src/pane/pty-ipc.ts
  - apps/voss-app/src-tauri/src/lib.rs   # incl. a #[cfg(test)] mod for the owned-env builder unit test (Task 3)
autonomous: true
requirements: [VBUS-03]

must_haves:
  truths:
    - "Every pane spawn mints a readable slug (claude-1 / pane-3) before any agent runs (D-11: ALL panes, not just managed; D-12: readable slug)"
    - "spawn_agent, spawn_managed_agent, and spawn_pty inject VOSS_AGENT_ID into the child process env"
    - "Slug registered in-memory per paneId at spawn; exported for A6 to persist in pane config when A6 ships (best-effort, D-13 — no pane config file in this plan)"
    - "Slug minting distinguishes agent CLIs (<cli>-<n>) from plain shells (pane-<n>) (D-12)"
  artifacts:
    - path: "apps/voss-app/src/pane/slugRegistry.ts"
      provides: "mintSlug + registerSlug/unregisterSlug module signal"
      contains: "mintSlug"
    - path: "apps/voss-app/src-tauri/src/lib.rs"
      provides: "VOSS_AGENT_ID env injection at three spawn call sites"
      contains: "VOSS_AGENT_ID"
  key_links:
    - from: "apps/voss-app/src/pane/pty-ipc.ts"
      to: "spawn_agent / spawn_managed_agent / spawn_pty Tauri commands"
      via: "vossAgentId invoke parameter"
      pattern: "vossAgentId"
    - from: "apps/voss-app/src-tauri/src/lib.rs"
      to: "spawn_command_session_with_env env slice"
      via: "owned (String,String) tuple carrying VOSS_AGENT_ID"
      pattern: "VOSS_AGENT_ID"
---

<objective>
Inject `VOSS_AGENT_ID` into ALL panes at spawn (D-11): mint a readable slug in TypeScript (`claude-1` / `pane-3`, D-12), pass it as a Tauri command parameter, and append it to the env slice at the three Rust spawn call sites (`spawn_agent`, `spawn_managed_agent`, `spawn_pty`). Persist the slug in pane config for best-effort restore stability (D-13). `VOSS_SERVER_PORT`/`VOSS_SERVER_TOKEN` injection is deferred to the V15-gated bus wave (RESEARCH Open Question 1) — this plan ships only `VOSS_AGENT_ID`.

Purpose: VBUS-03 — claims verbs (V17-03) resolve identity from this env var; tier-C agents are covered by construction.
Output: `slugRegistry.ts` (new), `pty-ipc.ts` + `lib.rs` modified.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-RESEARCH.md
@.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-PATTERNS.md

<interfaces>
<!-- Analog signatures (extracted in PATTERNS.md) -->
apps/voss-app/src/pane/adoptionRegistry.ts: createSignal module pattern (registerAdoption/unregisterAdoption/__resetAdoptions)
apps/voss-app/src/pane/agentPaneRegistry.ts: AGENT_CLIS = new Set(['claude','codex','gemini','opencode','aider']); inferRole(cliBinary)
apps/voss-app/src/pane/pty-ipc.ts:
  AgentConfig { cliBinary, cliArgs, sessionId, managed?, scope?, tier?, budgetUsd? }
  spawnAgent(o) -> invoke('spawn_agent', { onData, rows, cols, cwd, cliBinary, cliArgs, sessionId, paneId, workspacePath })
  spawnManagedAgent(...) ; spawn(...) [plain PTY]
apps/voss-app/src-tauri/src/lib.rs:
  env_for_embedded_cli(cli_binary, cli_args) -> Vec<(&'static str, &'static str)>   # STATIC lifetime — slug can't go here
  spawn_agent (line ~203), spawn_managed_agent (line ~262), spawn_pty (line ~487)
  spawn_command_session_with_env(cli_binary, cli_args, env: &[(&str,&str)], rows, cols, cwd)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: slugRegistry.ts — mint + register + persist signal</name>
  <files>apps/voss-app/src/pane/slugRegistry.ts, apps/voss-app/src/pane/slugRegistry.test.ts</files>
  <behavior>
    - mintSlug('claude') -> 'claude-1', then mintSlug('claude') -> 'claude-2'
    - mintSlug('/usr/local/bin/codex') -> 'codex-1' (basename + lowercased)
    - mintSlug('bash') -> 'pane-1' (non-agent CLI gets pane- prefix)
    - mintSlug(undefined) -> 'pane-2' (plain shell)
    - registerSlug(paneId, slug) then slugByPaneId()[paneId] === slug
    - unregisterSlug(paneId) removes it; __resetSlugs() clears all + resets counter for tests
  </behavior>
  <read_first>
    - apps/voss-app/src/pane/adoptionRegistry.ts (the module-signal pattern to copy exactly)
    - apps/voss-app/src/pane/agentPaneRegistry.ts (AGENT_CLIS set + inferRole basename/lowercase logic to reuse for prefix decision)
    - apps/voss-app/src/pane/slugRegistry.test.ts (write this test first — RED)
  </read_first>
  <action>Create `apps/voss-app/src/pane/slugRegistry.ts` mirroring `adoptionRegistry.ts`: a `createSignal<Record<string, string>>({})` for slugByPaneId, `registerSlug(paneId, slug)`, `unregisterSlug(paneId)`, exported `slugByPaneId`, and `__resetSlugs()` test-only reset that also resets the counter. Add a module-level `let _counter = 0` and `mintSlug(cliBinary?: string): string`: derive basename via `cliBinary?.trim().toLowerCase().split('/').pop()`, use the AGENT_CLIS set (import from agentPaneRegistry, or replicate the set if importing creates a cycle) to choose prefix — agent CLI -> `<name>-<n>`, else (or undefined) -> `pane-<n>`; increment `_counter` once per mint and use it as `<n>`. Write `slugRegistry.test.ts` first asserting all behaviors above (vitest). D-12 format: `<cli>-<n>` / `pane-<n>`.</action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run src/pane/slugRegistry.test.ts</automated>
  </verify>
  <acceptance_criteria>
    - slugRegistry.test.ts passes all six behavior cases
    - mintSlug returns `claude-1`/`claude-2` for repeated agent CLIs and `pane-<n>` for non-agent/undefined
    - `grep -c 'mintSlug' apps/voss-app/src/pane/slugRegistry.ts` >= 1
    - `cd apps/voss-app && npx tsc --noEmit` clean for the new file
  </acceptance_criteria>
  <done>slugRegistry mints D-12-format slugs and exposes a persistable signal; vitest GREEN.</done>
</task>

<task type="auto">
  <name>Task 2: Pass slug through pty-ipc.ts to Tauri spawn commands</name>
  <files>apps/voss-app/src/pane/pty-ipc.ts</files>
  <read_first>
    - apps/voss-app/src/pane/pty-ipc.ts (lines ~42-54 AgentConfig; ~194-243 spawnAgent/spawnManagedAgent/spawn invoke calls)
    - apps/voss-app/src/pane/slugRegistry.ts (mintSlug — caller mints then passes)
    - apps/voss-app/src/pane/adoptionRegistry.ts (how paneId flows for registration)
  </read_first>
  <action>Add `vossAgentId?: string` to the `AgentConfig` interface and to the `o` parameter objects of `spawnAgent`, `spawnManagedAgent`, and the plain `spawn` method. In each `invoke(...)` call object, add `vossAgentId: o.vossAgentId ?? null` (serde camelCase crosses to Rust as `voss_agent_id` — match the V14 AgentEntry camelCase IPC lesson). The slug is minted by the caller (spawn orchestration) via `mintSlug` and passed in; if a caller does not yet pass one, `null` is sent and Rust treats it as no-injection (graceful). Register the minted slug against paneId via `registerSlug` at the spawn site if that wiring is co-located here; otherwise document the registration hook for the spawn orchestrator. Do NOT modify spawn logic beyond threading the new optional field. Keep tsc clean.</action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'vossAgentId' apps/voss-app/src/pane/pty-ipc.ts` >= 4 (interface + three invoke calls)
    - `cd apps/voss-app && npx tsc --noEmit` exits 0
    - The three invoke objects each pass `vossAgentId: o.vossAgentId ?? null`
  </acceptance_criteria>
  <done>All three spawn paths forward vossAgentId to Tauri as camelCase; tsc clean.</done>
</task>

<task type="auto">
  <name>Task 3: Inject VOSS_AGENT_ID into env at the three Rust spawn call sites</name>
  <files>apps/voss-app/src-tauri/src/lib.rs</files>
  <read_first>
    - apps/voss-app/src-tauri/src/lib.rs (lines ~168-181 env_for_embedded_cli STATIC return; ~203-212 spawn_agent call site; ~262 spawn_managed_agent; ~480-492 spawn_pty)
    - .planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-RESEARCH.md (Pattern 6 + Pitfall 3 static-lifetime mismatch — owned Vec at call site)
    - .planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-PATTERNS.md (lib.rs modified-call pattern: build Vec<(String,String)> then borrow refs)
  </read_first>
  <action>Add a `voss_agent_id: Option<String>` parameter to the `spawn_agent`, `spawn_managed_agent`, and `spawn_pty` Tauri commands (Tauri maps the camelCase `vossAgentId` from JS). Do NOT change `env_for_embedded_cli`'s static return type (Pitfall 3). At each call site: collect `env_for_embedded_cli(...)` into an owned `Vec<(String,String)>`, push `("VOSS_AGENT_ID".to_string(), slug.clone())` when `voss_agent_id` is Some, then build `let env_refs: Vec<(&str,&str)> = full_env.iter().map(|(k,v)| (k.as_str(), v.as_str())).collect();` and pass `&env_refs` to `spawn_command_session_with_env`. For `spawn_pty` (currently `spawn_session` with NO env), switch to `spawn_command_session_with_env` with the default shell binary/args and only the agent-id env entry (per PATTERNS.md guidance) — or the cleanest equivalent that preserves plain-shell behavior while injecting the var. Keep `spawn_command_session_managed`'s unmanaged sibling functions byte-unchanged where not on these three paths (VBUS-08 — do NOT modify sandbox.rs). Factor the env-building into a small pure helper, e.g. `fn build_env_with_agent_id(base: Vec<(String,String)>, voss_agent_id: Option<String>) -> Vec<(String,String)>` (or the cleanest equivalent the three call sites can share), so it is unit-testable without a live PTY. Add a `#[cfg(test)] mod tests` in lib.rs with a unit test for the camelCase IPC round-trip outcome (TS `vossAgentId` -> Rust `voss_agent_id` -> `VOSS_AGENT_ID` env): assert that for `Some("claude-1")` the returned env Vec contains `("VOSS_AGENT_ID".to_string(), "claude-1".to_string())`, and that for `None` no entry with key `"VOSS_AGENT_ID"` is present. This guards against the silent-None-injection failure (V14 AgentEntry camelCase lesson — a serde rename mismatch would surface here as a missing env entry). Run cargo to confirm borrow-checker passes and the unit test is green.</action>
  <verify>
    <automated>cargo build -p voss-app 2>&1 | tail -5 || cargo test -p voss-app-core 2>&1 | tail -5</automated>
    <automated>cargo test -p voss-app build_env_with_agent_id 2>&1 | tail -5 || cargo test -p voss-app-core build_env_with_agent_id 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - The crate compiles (cargo build/test exits 0) with the new `voss_agent_id` params and owned-env call sites
    - `grep -c 'VOSS_AGENT_ID' apps/voss-app/src-tauri/src/lib.rs` >= 1
    - `git diff --stat crates/voss-app-core/src/sandbox.rs` shows zero changes (VBUS-08)
    - All three commands (spawn_agent, spawn_managed_agent, spawn_pty) accept `voss_agent_id: Option<String>` (source assertion in summary)
    - A Rust unit test for the owned-env builder passes: `Some(slug)` yields `("VOSS_AGENT_ID", slug)` in the env slice, `None` yields no `VOSS_AGENT_ID` entry (guards the camelCase IPC round-trip vs silent-None injection — V14 lesson)
  </acceptance_criteria>
  <done>Three spawn commands inject VOSS_AGENT_ID via owned env; crate compiles; sandbox.rs untouched.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| webview JS -> Tauri command | vossAgentId slug string crosses the IPC boundary into the child process env |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V17-09 | Spoofing | slug value chosen by webview | accept | Advisory identity (SEED-001); slug is best-effort, spoofable, accepted by design |
| T-V17-10 | Tampering | env injection altering unrelated vars | mitigate | Only VOSS_AGENT_ID is appended; env_for_embedded_cli static set untouched; no other env keys added |
</threat_model>

<verification>
- `cd apps/voss-app && npx vitest run src/pane/slugRegistry.test.ts && npx tsc --noEmit` GREEN.
- `cargo build -p voss-app` (or `cargo test -p voss-app-core`) exits 0.
- Rust owned-env builder unit test GREEN: `Some(slug)` -> `("VOSS_AGENT_ID", slug)` present; `None` -> absent (camelCase IPC round-trip guard).
- `git diff --stat crates/voss-app-core/src/sandbox.rs` empty.
- Manual-only (VALIDATION.md): launch an agent in the running app, run `env | grep VOSS_AGENT_ID` in the pane.
</verification>

<success_criteria>
All panes receive a readable VOSS_AGENT_ID at spawn (D-11/D-12); persisted for restore (D-13 best-effort); claims verbs can resolve identity. sandbox.rs unchanged.
</success_criteria>

<output>
Create `.planning/phases/V17-external-agent-coordination-surface-claims-bus-verbs-as-prot/V17-04-SUMMARY.md` when done.
</output>
