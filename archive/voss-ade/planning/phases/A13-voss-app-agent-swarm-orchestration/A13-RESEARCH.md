# Phase A13: Agent Swarm Orchestration — Research

**Researched:** 2026-05-23
**Domain:** File-mediated multi-agent coordination in Tauri/SolidJS/Rust
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

| ID | Decision |
|----|----------|
| D-01 | File-mediated communication — `.voss/swarm/` directory |
| D-02 | Single coordinator pattern (not peer-to-peer) |
| D-03 | Coordinator is a single Opus LLM call (not a full agent) |
| D-04 | `.voss/swarm/` directory convention; gitignored; scoped to workspace |
| D-05 | Task files are markdown (not JSON) — agents understand markdown better |
| D-06 | Result files are markdown with structured frontmatter |
| D-07 | Fan-out/fan-in (not pipeline) |
| D-08 | Swarm agents appear in sidebar AGENTS section with "swarm" group indicator |
| D-09 | User can stop individual swarm agents or entire swarm from sidebar |
| D-10 | Swarm layout preset auto-applied when swarm launches |
| D-11 | Coordinator prompt uses project CLAUDE.md / .voss context |
| D-12 | Max 6 concurrent agents per swarm (user can override) |
| D-13 | Swarm state persisted in `.voss/swarm/manifest.json` |
| D-14 | Completion detection: fs.watch on `.voss/swarm/results/` (primary) |
| D-15 | Swarm launch via sidebar button + launch modal Swarm tab |
| D-16 | Coordinator picks agents (user gives goal only) |
| D-17 | Task decomposition uses single Opus call with codebase context |
| D-18 | Subtasks include goal + file scope boundaries |
| D-19 | Agent receives task via CLI positional arg |
| D-20 | Scope boundaries are instruction-only (soft enforcement) |
| D-21 | Completion: fs.watch on result files (primary), PTY exit (fallback) |
| D-22 | Failure: timeout + notify user; no auto-retry |

### Claude's Discretion

Per CONTEXT.md (unlisted areas): SwarmController split between TypeScript and Rust is at
Claude's discretion. Coordinator prompt structure, swarm state signal design, and timeout
duration are at Claude's discretion.

### Deferred Ideas (OUT OF SCOPE)

- Agent-to-agent direct messaging (peer-to-peer)
- `.voss` language `team{}` execution (O2)
- Recursive sub-swarms
- Cross-workspace swarms
- Budget enforcement across swarm agents (O1)
- Auto-retry on failure
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SWM-01 | User can launch a swarm from sidebar with a natural language goal | D-15: sidebar button + Swarm tab in modal; `AgentLaunchModal` extensible via new tab type |
| SWM-02 | Coordinator decomposes goal into 2-6 subtasks automatically | D-03/D-17: single Opus LLM call; `@anthropic-ai/sdk` available on npm |
| SWM-03 | Each subtask spawns a dedicated agent pane with task context | D-19: existing `spawn_agent` Tauri command accepts `cliArgs` positional arg |
| SWM-04 | Agents read task assignments from `.voss/swarm/tasks/` files | D-05: markdown task files; write from Rust or TS |
| SWM-05 | Agents write results to `.voss/swarm/results/` files | D-06: result frontmatter format; agents instructed via task file |
| SWM-06 | Host detects agent completion via result file creation + PTY idle | D-21: Rust polling watcher (existing `watch_keymap_overrides` pattern) + `on_exit` from PtyTransport |
| SWM-07 | Coordinator synthesizes all results into a summary for the user | Fan-in via second Anthropic API call or simple concatenation |
| SWM-08 | Sidebar shows swarm status (pending/running/complete per agent) | D-08: extend `AgentSidebarProps` with `swarmGroup` field on `AgentEntry` |
| SWM-09 | User can stop individual agents or entire swarm from sidebar | D-09: extend `AgentContextMenu` with "Stop swarm" option; `pty_kill` Tauri command already exists |
| SWM-10 | Swarm layout preset auto-applied when swarm launches | D-10: `applyPreset('swarm')` via `gridController.applyPreset` already in `GridRoot` |
| SWM-11 | Swarm state persisted in `.voss/swarm/manifest.json` | D-13: atomic write-then-rename pattern, same as `write_context_pins` |
| SWM-12 | Swarm resumable after app restart | manifest.json contains all state needed to resume |
</phase_requirements>

---

## Summary

Phase A13 adds a file-mediated multi-agent swarm orchestrator to the Voss ADE. The core
design — single coordinator LLM call → write task files → spawn N agents → watch for result
files — maps cleanly onto existing codebase primitives. The `spawn_agent` Tauri command is
already fully wired and accepts arbitrary `cliBinary`/`cliArgs`; task injection is a
positional CLI argument. The existing Rust file-watch pattern (polling loop with `AtomicBool`
stop signal, emitting Tauri events) used in `watch_keymap_overrides` is the right pattern
for result watching. The coordinator LLM call should be made from the TypeScript side using
`@anthropic-ai/sdk` — not from Rust — because the app has no HTTP client dep in Rust and
adding one would require Cargo + CSP changes; the Tauri IPC channel + TypeScript is the
natural integration point.

The `swarm` layout preset already exists in `layoutPresets.ts` and arranges up to 4×4 panes
in a near-square grid. `AgentLaunchModal` uses a typed `CliTab` union and a `CLI_TABS` array
that just needs a new `'swarm'` entry. The sidebar `AgentEntry` type needs a `swarmId`/
`swarmStatus` field added to both the type and the computation in `agentListForSidebar`. The
`AgentContextMenu` gets a "Stop swarm" menu item when `swarmId` is present.

The main new infrastructure is: (1) a `SwarmController` TypeScript module that manages swarm
lifecycle, (2) a Rust `watch_swarm_results` command following the `watch_keymap_overrides`
polling pattern, and (3) a new `swarm_results_changed` Tauri event that the frontend listens
to for status updates.

**Primary recommendation:** Keep all swarm business logic in TypeScript (`SwarmController`).
Rust provides only the file watcher (reusing the established polling pattern) and file I/O
commands. The Anthropic API call is TypeScript-side via `@anthropic-ai/sdk`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Coordinator LLM call (goal decomposition) | TypeScript (frontend) | — | `@anthropic-ai/sdk` is a JS library; Rust has no HTTP client dep; avoids CSP/CORS issue |
| Task file writing | Rust (Tauri command) | — | File I/O outside webview requires Rust; existing pattern `write_context_pins` |
| Result file watching | Rust (Tauri command) | — | `watch_keymap_overrides` polling pattern; no `notify` dep needed |
| Agent spawning | Rust (existing `spawn_agent`) | — | PTY + agent registry already in Rust |
| Swarm state management | TypeScript (SwarmController) | — | Reactive SolidJS signals; Rust holds only manifest bytes |
| Manifest persistence | Rust (Tauri command) | — | Atomic write-then-rename, same as `write_context_pins` |
| Sidebar swarm UI | TypeScript (SolidJS) | — | Extends existing `AgentSidebar`/`AgentItem` components |
| Swarm launch modal tab | TypeScript (SolidJS) | — | Extends existing `AgentLaunchModal` |
| Layout preset application | TypeScript (existing `applyPreset`) | — | `layoutPresets.ts` `buildSwarm` already exists |
| Fan-in synthesis | TypeScript (SwarmController) | — | Same as coordinator: `@anthropic-ai/sdk` or simple string join |
| Timeout / stuck detection | TypeScript (SwarmController) | — | `setTimeout` is sufficient; no Rust timer needed |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@anthropic-ai/sdk` | 0.98.0 (latest) | Coordinator LLM call (Opus) | Official Anthropic TypeScript SDK — already on npm, Anthropic-maintained |
| `gray-matter` | 4.0.3 | Parse YAML frontmatter from result `.md` files | Mature (10+ years), used by Jekyll/Gatsby ecosystem; handles `---` frontmatter cleanly |

**Neither library is currently in `apps/voss-app/package.json`. Both need to be added.**

### Supporting (already in-repo, no install needed)

| Item | Where | Purpose |
|------|-------|---------|
| `spawn_agent` Tauri command | `src-tauri/src/lib.rs:148` | Spawn each swarm agent pane |
| `pty_kill` Tauri command | `src-tauri/src/lib.rs:293` | Stop individual agents or whole swarm |
| `applyPreset('swarm')` | `src/grid/layoutPresets.ts:55` | Auto-apply swarm grid layout |
| `write_context_pins` pattern | `src-tauri/src/lib.rs:398` | Atomic file write pattern for manifest |
| `watch_keymap_overrides` pattern | `src-tauri/src/lib.rs:551` | Polling file watcher with `AtomicBool` stop |
| `AgentLaunchModal` | `src/components/modal/AgentLaunchModal.tsx` | Add Swarm tab |
| `AgentSidebar` + `AgentItem` | `src/components/sidebar/` | Add swarm group display |
| `AgentContextMenu` | `src/components/sidebar/AgentContextMenu.tsx` | Add "Stop swarm" action |
| `showToast` | `src/command-palette/toast` | Swarm completion / stuck notifications |
| `budgetRegistry` / `agentPaneRegistry` | `src/pane/` | Existing per-pane signal stores (pattern for SwarmRegistry) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@anthropic-ai/sdk` (TS side) | `reqwest` Rust HTTP client | Rust path requires new Cargo dep + CSP `connect-src` change + no existing Rust Anthropic integration; TS SDK is one install |
| `gray-matter` for frontmatter parsing | Hand-rolled regex | `gray-matter` handles edge cases (multi-line strings, special chars in YAML); 3 lines vs. brittle regex |
| Polling file watcher (Rust) | `notify` crate | `notify` requires new Cargo dep; polling at 500ms is acceptable for swarm completion (not real-time typing); matches existing `watch_keymap_overrides` precedent — zero new deps |
| `@tauri-apps/plugin-fs` (JS watch) | Rust polling watcher | Plugin-fs adds a new Tauri plugin with capabilities config changes; Rust polling avoids that entirely and already exists as a pattern |

**Installation:**

```bash
cd apps/voss-app && npm install @anthropic-ai/sdk gray-matter
```

---

## Package Legitimacy Audit

> Packages newly installed by this phase.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `@anthropic-ai/sdk` | npm | ~2.3 yrs (2023-01-31) | Very high (official Anthropic SDK) | github.com/anthropics/anthropic-sdk-typescript | [VERIFIED: official Anthropic repository, maintainers zak-anthropic/dylanc-anthropic] | Approved |
| `gray-matter` | npm | ~11 yrs (2014-01-28) | Very high (Jekyll/Gatsby ecosystem staple) | github.com/jonschlinkert/gray-matter | [VERIFIED: npm registry, 10+ yr history] | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none

**Packages flagged as suspicious [SUS]:** none

*slopcheck CLI did not support the `install <pkg> --json` invocation in this environment (requires a local dependency manifest, not a package name). Packages were verified against npm registry and official source repositories instead. Both packages are `[VERIFIED]` via official source attribution.*

---

## Architecture Patterns

### System Architecture Diagram

```
[Sidebar "Swarm" button]
        |
        v
[SwarmLaunchPanel (modal tab)]
   user enters: goal text
        |
        v
[SwarmController.launch(goal, workspacePath)]
        |
        +---> [Coordinator LLM call]
        |     @anthropic-ai/sdk, single Opus call
        |     input: goal + repo file tree + CLAUDE.md excerpt
        |     output: JSON subtask array
        |
        +---> [writeSwarmFiles (Tauri)]
        |     writes manifest.json + tasks/agent-N.task.md
        |
        +---> [spawn_agent x N (existing Tauri command)]
        |     cliBinary: 'claude'/'codex'/...
        |     cliArgs: ["--dangerously-skip-permissions", <task positional>]
        |     returns: ptyId per agent
        |
        +---> [watch_swarm_results (new Rust Tauri command)]
              polls .voss/swarm/results/ at 500ms
              emits 'voss://swarm-result-added' event per new file
                        |
                        v
              [SwarmController event listener]
              updates SwarmRegistry signal (per-agent status)
                        |
                        +-- [sidebar re-renders] (reactive)
                        |
                        +-- [all agents done?]
                              |
                              v
                        [fan-in synthesis]
                        optional second LLM call or concat
                              |
                              v
                        [showToast("Swarm complete")]
```

### Recommended Project Structure

```
src/
├── swarm/
│   ├── SwarmController.ts      # Lifecycle: launch, watch, cancel, synthesize
│   ├── swarmRegistry.ts        # Reactive signal store: swarm state by swarmId
│   ├── swarmTypes.ts           # SwarmManifest, SwarmAgent, SubTask types
│   └── __tests__/
│       └── SwarmController.test.ts
apps/voss-app/src-tauri/src/
└── lib.rs                      # +write_swarm_files, +watch_swarm_results, +stop_swarm_watcher
```

### Pattern 1: Coordinator Prompt Design

**What:** Single `messages.create` call to `claude-opus-4-5` that receives goal + tree and
outputs a JSON array of subtasks.

**When to use:** Every swarm launch.

**Key insight:** Ask for structured JSON output directly. Claude reliably produces JSON when
the prompt ends with "Respond with ONLY a JSON array, no other text."

```typescript
// Source: @anthropic-ai/sdk docs + empirical Claude prompt engineering patterns
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic(); // reads ANTHROPIC_API_KEY from env

async function coordinatorDecompose(
  goal: string,
  repoTree: string,
  claudeMd: string,
): Promise<SubTask[]> {
  const msg = await client.messages.create({
    model: 'claude-opus-4-5',
    max_tokens: 2048,
    messages: [
      {
        role: 'user',
        content: `You are a coordinator for a parallel agent swarm working on a software project.

Project context (CLAUDE.md):
${claudeMd}

Repository structure:
${repoTree}

Goal: ${goal}

Decompose this goal into 2-6 parallel subtasks. Each subtask should be independently
executable by a CLI AI agent (claude, codex, or opencode).

Respond with ONLY a JSON array in this exact shape, no other text:
[
  {
    "id": "agent-1",
    "cli": "claude",
    "goal": "...",
    "fileScope": ["src/auth/", "src/auth/service.ts"],
    "excludeScope": ["src/auth/tests/"]
  }
]`,
      },
    ],
  });

  const text = msg.content[0].type === 'text' ? msg.content[0].text : '';
  return JSON.parse(text) as SubTask[];
}
```

### Pattern 2: Rust Polling File Watcher (result detection)

**What:** Reuse the exact `watch_keymap_overrides` polling pattern — spawn a thread, poll
file system at 500ms, emit a Tauri event when new files appear.

**When to use:** After swarm is launched; stop when swarm is cancelled or all results in.

```rust
// Source: apps/voss-app/src-tauri/src/lib.rs:551 (watch_keymap_overrides pattern)
// Adapted for swarm result directory watching

#[tauri::command]
fn watch_swarm_results(
    app: tauri::AppHandle,
    state: tauri::State<'_, SwarmWatchState>,
    swarm_id: String,
    results_dir: String,
) -> Result<(), String> {
    let results_path = PathBuf::from(results_dir);
    let stop = Arc::new(AtomicBool::new(false));

    // Cancel any prior watcher for this swarm_id
    let previous = state.stops.lock()
        .map_err(|_| "swarm watch lock poisoned".to_string())?
        .insert(swarm_id.clone(), Arc::clone(&stop));
    if let Some(prev) = previous {
        prev.store(true, Ordering::Relaxed);
    }

    std::thread::spawn(move || {
        let mut known: std::collections::HashSet<String> = std::collections::HashSet::new();
        while !stop.load(Ordering::Relaxed) {
            std::thread::sleep(Duration::from_millis(500));
            let Ok(rd) = std::fs::read_dir(&results_path) else { continue };
            for entry in rd.flatten() {
                let name = entry.file_name().to_string_lossy().into_owned();
                if name.ends_with(".result.md") && !known.contains(&name) {
                    known.insert(name.clone());
                    let _ = app.emit("voss://swarm-result-added", serde_json::json!({
                        "swarmId": swarm_id,
                        "resultFile": name,
                    }));
                }
            }
        }
    });

    Ok(())
}
```

### Pattern 3: Task File Write (atomic, from Rust)

**What:** Write task files + manifest atomically. Follow the `write_context_pins`
write-then-rename pattern.

```rust
// Source: apps/voss-app/src-tauri/src/lib.rs:398 (write_context_pins pattern)
#[tauri::command]
fn write_swarm_files(
    workspace_path: String,
    manifest: serde_json::Value,
    tasks: Vec<(String, String)>, // (filename, content)
) -> Result<(), String> {
    let swarm_dir = Path::new(&workspace_path).join(".voss").join("swarm");
    std::fs::create_dir_all(swarm_dir.join("tasks")).map_err(|e| e.to_string())?;
    std::fs::create_dir_all(swarm_dir.join("results")).map_err(|e| e.to_string())?;
    std::fs::create_dir_all(swarm_dir.join("shared")).map_err(|e| e.to_string())?;

    // Atomic manifest write
    let manifest_target = swarm_dir.join("manifest.json");
    let manifest_tmp = swarm_dir.join("manifest.json.tmp");
    let json = serde_json::to_string_pretty(&manifest).map_err(|e| e.to_string())?;
    std::fs::write(&manifest_tmp, json).map_err(|e| e.to_string())?;
    std::fs::rename(&manifest_tmp, &manifest_target).map_err(|e| e.to_string())?;

    // Write task files
    for (filename, content) in &tasks {
        std::fs::write(swarm_dir.join("tasks").join(filename), content)
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}
```

### Pattern 4: Agent Spawn with Task Positional Arg (D-19)

**What:** Pass task path as CLI positional argument to any agent CLI.

**When to use:** After task files are written.

```typescript
// Source: apps/voss-app/src/pane/pty-ipc.ts:167 (spawnAgent)
// The task becomes a positional arg at the end of cliArgs

function buildTaskArg(workspacePath: string, agentId: string): string {
  const taskPath = `.voss/swarm/tasks/${agentId}.task.md`;
  return `Read '${taskPath}' and follow the instructions exactly.`;
}

// Usage in SwarmController:
await transport.spawnAgent({
  rows: 40,
  cols: 120,
  cwd: workspacePath,
  paneId: newPaneId,
  workspacePath,
  cliBinary: subtask.cli,
  cliArgs: [
    '--dangerously-skip-permissions',      // claude: auto-approve
    buildTaskArg(workspacePath, subtask.id),
  ],
  sessionId: crypto.randomUUID(),
});
```

### Pattern 5: SwarmRegistry (SolidJS reactive signal store)

**What:** Mirror of `budgetRegistry.ts` and `agentPaneRegistry.ts` — module-level reactive
signal, written by `SwarmController`, read by `agentListForSidebar` in `App.tsx`.

```typescript
// Source: apps/voss-app/src/pane/budgetRegistry.ts (pattern)
import { createSignal } from 'solid-js';

export type SwarmAgentStatus = 'pending' | 'running' | 'complete' | 'stuck';

export type SwarmEntry = {
  swarmId: string;
  goal: string;
  agentPaneId: string;
  agentId: string;
  cli: string;
  status: SwarmAgentStatus;
};

const [swarmByPaneId, setSwarmByPaneId] = createSignal<Record<string, SwarmEntry>>({});

export function registerSwarmAgent(paneId: string, entry: SwarmEntry): void {
  setSwarmByPaneId((prev) => ({ ...prev, [paneId]: entry }));
}

export function updateSwarmAgentStatus(paneId: string, status: SwarmAgentStatus): void {
  setSwarmByPaneId((prev) => {
    const e = prev[paneId];
    if (!e || e.status === status) return prev;
    return { ...prev, [paneId]: { ...e, status } };
  });
}

export function unregisterSwarmAgents(swarmId: string): void {
  setSwarmByPaneId((prev) => {
    const next = { ...prev };
    for (const [k, v] of Object.entries(next)) {
      if (v.swarmId === swarmId) delete next[k];
    }
    return next;
  });
}

export { swarmByPaneId };
```

### Pattern 6: Sidebar Swarm Group Display

**What:** Extend `AgentEntry` type (in `App.tsx`) with `swarmId?` and `swarmStatus?`.
In `AgentSidebar`, group swarm agents under a header row showing `"Swarm: {goal} (N/M
complete)"`.

**Key change:** `agentListForSidebar` memo in `App.tsx` merges `swarmByPaneId()` into
each entry. The sidebar groups by `swarmId` and renders a group header above each cluster.

### Anti-Patterns to Avoid

- **Polling PTY output for task completion signals:** The CONTEXT explicitly chooses
  file-based completion (D-21). Do not parse Claude's stdout for markers. File creation
  is reliable and OS-agnostic.
- **Making the Anthropic API call from Rust:** Adds `reqwest` dep, requires CSP changes
  (`connect-src` must allow `api.anthropic.com`), and diverges from the established TS-side
  invocation pattern. Use `@anthropic-ai/sdk` from TypeScript instead.
- **Using `@tauri-apps/plugin-fs` for watching:** Introduces a new Tauri plugin with
  capability JSON changes. The existing Rust polling pattern in `watch_keymap_overrides`
  achieves the same result with zero new deps.
- **Storing swarm agents separately from the main agent list:** All swarm agents are
  regular `spawn_agent` panes — they appear in the agent registry and `agentPaneById`.
  SwarmRegistry is an *overlay* that adds `swarmId`/`swarmStatus` metadata, not a
  replacement list.
- **Calling `applyPreset('swarm')` directly from SwarmController:** The controller doesn't
  own `gridController`. Pass it a callback or emit an event; `App.tsx` owns the controller
  reference and calls `ctrl.applyPreset('swarm')`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Anthropic API calls | Custom `fetch()` wrapper | `@anthropic-ai/sdk` | Auth, retry, streaming, type safety — the SDK handles all of this |
| YAML frontmatter parsing from result files | Regex against `---` blocks | `gray-matter` | Handles multi-line strings, quoted values, nested YAML — fragile regex is a maintenance trap |
| File watching from TypeScript | `fs.watch()` Node.js API | Rust polling watcher | In Tauri, `fs.watch` from the webview is not available without `plugin-fs`; Rust polling is already proven in this codebase |
| Streaming completion detection | Poll for `process.exit` | fs.watch on result files | PTY exit is used as *fallback* only (D-21) — result file is more reliable because an agent can exit non-zero and still have written results |

---

## Common Pitfalls

### Pitfall 1: CSP blocks `api.anthropic.com`

**What goes wrong:** The Anthropic SDK fetch call is rejected by Tauri's CSP because
`connect-src` in `tauri.conf.json` only allows `'self' ipc: http://ipc.localhost`.

**Why it happens:** Tauri's webview enforces the CSP on all outbound connections from
the frontend JavaScript context.

**How to avoid:** Add `https://api.anthropic.com` to `connect-src` in `tauri.conf.json`
before making any Anthropic SDK calls. This is a **required Wave 0 step**.

```json
"connect-src": "\"self\" ipc: http://ipc.localhost https://api.anthropic.com"
```

**Warning signs:** `Content Security Policy` error in the Tauri webview dev console when
`client.messages.create()` is called.

### Pitfall 2: Solid proxy objects in swarm state

**What goes wrong:** Passing SolidJS reactive proxy objects to `structuredClone()` or
`JSON.stringify()` for manifest serialization fails with `DataCloneError`.

**Why it happens:** Memory `voss-app-solid-produce-no-structuredclone` — this is a
known project pitfall. SolidJS store proxies are not serializable.

**How to avoid:** Serialize swarm entries using `JSON.parse(JSON.stringify(...))` only
on plain objects derived from signal reads (not the signals themselves). Write-through
to manifest.json uses only plain values extracted from the signal, not the reactive proxy.

### Pitfall 3: Race between fs.watch and agent spawn

**What goes wrong:** If the Rust watcher is started before the `results/` directory is
created, `read_dir` returns an error on the first polls and the watcher silently misses
results from fast agents.

**Why it happens:** `write_swarm_files` creates the directory, but if the watcher starts
before the write completes, the directory may not exist yet.

**How to avoid:** Start the watcher *after* `write_swarm_files` returns successfully
(await the Tauri invoke). The watcher uses `let Ok(rd) = read_dir(...) else { continue }`
gracefully handling missing directory.

### Pitfall 4: Claude CLI positional arg quoting

**What goes wrong:** The task instruction string passed as a positional arg to `claude`
contains single quotes, breaking the shell command that `spawn_command_session` builds.

**Why it happens:** `spawn_command_session` uses `cli_binary` + `cli_args` — if the arg
contains special chars, the PTY shell may misparse it.

**How to avoid:** Use the task file *path* in the positional arg (not the full content).
Instruct: `"Read .voss/swarm/tasks/agent-1.task.md and follow the instructions."` — this
is a safe ASCII string with no quotes. All rich content lives in the file.

### Pitfall 5: Agent writes result before SwarmController listener is registered

**What goes wrong:** A very fast agent (or a resumed swarm) writes its result before the
Tauri event listener in TypeScript is attached via `listen('voss://swarm-result-added', ...)`.

**Why it happens:** `listen()` is async; there is a brief gap between watcher start and
listener attachment.

**How to avoid:** On watcher start, do an initial scan of the `results/` directory and
process any pre-existing `.result.md` files immediately (before the polling loop begins).
The Rust watcher should emit one event per already-existing file before entering the poll
loop (backfill pass on first iteration).

### Pitfall 6: `ANTHROPIC_API_KEY` not available in Tauri webview env

**What goes wrong:** `new Anthropic()` reads `process.env.ANTHROPIC_API_KEY` — but in a
Tauri webview this env var is not automatically available; `process.env` is a Node.js
concept that Vite replaces at build time.

**Why it happens:** Vite does not inject arbitrary env vars unless explicitly configured
with `import.meta.env.VITE_*` or `define`.

**How to avoid:** The Anthropic SDK also supports passing the key directly:
`new Anthropic({ apiKey: ... })`. Read the key from an OS keychain or a `.voss/` config
file via a Tauri command, then inject it: `new Anthropic({ apiKey })`. Do NOT hardcode or
commit the key. A simpler alternative: read it from `process.env` via a new Rust Tauri
command `get_env_var('ANTHROPIC_API_KEY')` that calls `std::env::var`.

**Warning signs:** `AuthenticationError` from the Anthropic SDK on first call. Check that
the key is present and non-empty before calling `coordinatorDecompose`.

---

## Code Examples

### Spawn Agent — Existing Interface (verified from source)

```typescript
// Source: apps/voss-app/src/pane/pty-ipc.ts:167
// spawnAgent accepts: rows, cols, cwd, paneId, workspacePath, cliBinary, cliArgs, sessionId
await transport.spawnAgent({
  rows: 40, cols: 120,
  cwd: workspacePath,
  paneId: 'pane-xyz',
  workspacePath,
  cliBinary: 'claude',
  cliArgs: ['--dangerously-skip-permissions', 'Read .voss/swarm/tasks/agent-1.task.md and follow the instructions.'],
  sessionId: crypto.randomUUID(),
});
```

### Apply Swarm Preset — Existing Interface

```typescript
// Source: apps/voss-app/src/grid/layoutPresets.ts:55
// applyPreset('swarm') arranges panes in a near-square grid up to 4×4
// Called via: gridController.applyPreset('swarm')
// In App.tsx: ctrl.applyPreset(preset) at line 463 (onLayoutSelect)
```

### Stop Agent — Existing Tauri Command

```typescript
// Source: apps/voss-app/src-tauri/src/lib.rs:293
// pty_kill takes sessionId (the pty_id returned by spawn_agent, NOT paneId)
await invoke('pty_kill', { sessionId: ptyId });
```

### Tauri Event Listener Pattern

```typescript
// Source: apps/voss-app/src/command-palette/keymapStorage.ts (watchWorkspaceKeymap pattern)
import { listen } from '@tauri-apps/api/event';

const unlisten = await listen<{ swarmId: string; resultFile: string }>(
  'voss://swarm-result-added',
  (event) => {
    const { swarmId, resultFile } = event.payload;
    handleResultFile(swarmId, resultFile);
  }
);
// Call unlisten() to stop listening
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual fetch() for Anthropic API | `@anthropic-ai/sdk` (official) | 2023 | Auto-auth, types, retry |
| Hardcoded `claude-2` model | `claude-opus-4-5` for complex reasoning | 2024–2025 | Better decomposition quality |
| Node.js `fs.watch` | OS-native watchers via `notify` crate | 2019+ | `notify` is more reliable but a new dep; polling at 500ms is acceptable for swarm completion |

**Deprecated/outdated:**

- Using `process.env.ANTHROPIC_API_KEY` directly in Tauri webview: does not work as
  expected — requires Vite `define` or a Tauri `get_env_var` command.
- `claude-2`/`claude-3-opus` model names: current model ID for Opus is `claude-opus-4-5`
  (verify at build time — model IDs rotate; use `claude-opus-4-5` or the SDK's latest
  alias). [ASSUMED — verify model ID at implementation time]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `claude-opus-4-5` is the correct model ID for the Coordinator call | Standard Stack, Code Examples | Wrong model ID causes API error; verify against Anthropic docs at implementation time |
| A2 | `claude --dangerously-skip-permissions` flag exists and auto-approves tool use | Pattern 4 | Agent blocks on permission prompts, defeating swarm automation; verify against current claude CLI version |
| A3 | `codex` CLI accepts a positional task argument in the same form as `claude` | Pattern 4, SWM-03 | Codex agents would not receive task; scope to claude-only initially if unverified |
| A4 | `opencode` CLI accepts the same positional arg pattern | Pattern 4 | Same as A3 |
| A5 | The Anthropic SDK reads `ANTHROPIC_API_KEY` from the process environment in Tauri's webview context | Pitfall 6 | Auth failure on first Anthropic call; use explicit `apiKey` constructor argument |

---

## Open Questions

1. **Where does `ANTHROPIC_API_KEY` come from in production?**
   - What we know: Tauri webview `process.env` is not the OS environment; the SDK needs an API key.
   - What's unclear: Should the user paste the key into a settings screen (A9 settings)? Read from `~/.config/voss-app/settings.json`? Read from OS keychain?
   - Recommendation: Add a Tauri command `get_env_var(name: String)` that calls `std::env::var`. The app was launched from the OS shell and inherits env vars. This is the simplest path for the first implementation. A settings UI can be added later.

2. **Does the `codex` CLI accept positional task args?**
   - What we know: `claude` accepts a positional prompt argument. The existing `AgentLaunchModal` passes a task via the last positional arg (`cliArgs` array, task at end).
   - What's unclear: `codex` CLI's exact arg interface — it may require `--prompt` or similar.
   - Recommendation: For A13, limit coordinator to picking `claude` only (safe bet). Add codex/opencode support in a follow-on phase once the arg interface is confirmed.

3. **Should synthesis be a second LLM call or a simple concatenation?**
   - What we know: SWM-07 says "coordinator synthesizes all results into a summary."
   - What's unclear: Is a simple summary concat + toast sufficient, or does the user expect a second Opus call?
   - Recommendation: Start with concatenation displayed in a sidebar ACTIVITY entry + toast. A second LLM call can be added in Wave 3 without blocking Wave 1/2 delivery.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `claude` CLI | Agent spawn (SWM-03) | [ASSUMED: yes — existing A12 code uses it] | unknown | — |
| `ANTHROPIC_API_KEY` env var | Coordinator LLM call | [ASSUMED: user has it set] | — | Add `get_env_var` Tauri command |
| `@anthropic-ai/sdk` | SwarmController.ts | Not yet installed | 0.98.0 on npm | — |
| `gray-matter` | Result file parsing | Not yet installed | 4.0.3 on npm | Hand-roll simple frontmatter parser |
| Rust `notify` crate | File watching | Not needed — polling pattern used | — | — |
| `@tauri-apps/plugin-fs` | File watching | Not needed — Rust polling used | — | — |

**Missing dependencies with no fallback:**

- `@anthropic-ai/sdk` — must be installed before coordinator can make any LLM call
- `https://api.anthropic.com` in CSP `connect-src` — must be added before coordinator
  can reach the API; blocks all swarm launches until added

**Missing dependencies with fallback:**

- `gray-matter` — can be replaced by a 10-line frontmatter parser if licensing is a concern

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | vitest 4.1.6 |
| Config file | `apps/voss-app/vitest.config.ts` |
| Quick run command | `cd apps/voss-app && npx vitest run src/swarm` |
| Full suite command | `cd apps/voss-app && npx vitest run` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SWM-01 | Launch modal renders Swarm tab | unit | `npx vitest run src/components/modal/__tests__/AgentLaunchModal.test.tsx` | Wave 0 |
| SWM-02 | Coordinator parses Opus JSON output into SubTask[] | unit | `npx vitest run src/swarm/__tests__/SwarmController.test.ts -t "coordinator"` | Wave 0 |
| SWM-03 | Each subtask generates a spawn_agent call | unit (mocked invoke) | `npx vitest run src/swarm/__tests__/SwarmController.test.ts -t "spawn"` | Wave 0 |
| SWM-04 | Task files contain correct frontmatter + goal + scope | unit | `npx vitest run src/swarm/__tests__/SwarmController.test.ts -t "task files"` | Wave 0 |
| SWM-05 | Result file frontmatter is parsed correctly | unit | `npx vitest run src/swarm/__tests__/SwarmController.test.ts -t "result parse"` | Wave 0 |
| SWM-06 | PTY exit event updates agent status to 'complete' | unit | `npx vitest run src/swarm/__tests__/SwarmController.test.ts -t "exit fallback"` | Wave 0 |
| SWM-07 | Fan-in produces a summary string | unit | `npx vitest run src/swarm/__tests__/SwarmController.test.ts -t "fan-in"` | Wave 0 |
| SWM-08 | Sidebar renders swarm group header | unit | `npx vitest run src/components/sidebar/__tests__/AgentSidebar.test.tsx` | Exists — extend |
| SWM-09 | "Stop swarm" context menu action kills all agents | unit | `npx vitest run src/components/sidebar/__tests__/AgentSidebar.test.tsx -t "stop swarm"` | Wave 0 |
| SWM-10 | `applyPreset('swarm')` called on launch | unit | `npx vitest run src/swarm/__tests__/SwarmController.test.ts -t "preset"` | Wave 0 |
| SWM-11 | manifest.json written with correct shape | unit (mock write_swarm_files) | `npx vitest run src/swarm/__tests__/SwarmController.test.ts -t "manifest"` | Wave 0 |
| SWM-12 | Resuming from manifest re-registers swarm agents | unit | `npx vitest run src/swarm/__tests__/SwarmController.test.ts -t "resume"` | Wave 0 |

### Sampling Rate

- **Per task commit:** `cd apps/voss-app && npx vitest run src/swarm`
- **Per wave merge:** `cd apps/voss-app && npx vitest run`
- **Phase gate:** Full vitest suite + `cargo test -p voss-app-core` + `npx tsc --noEmit` green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `src/swarm/__tests__/SwarmController.test.ts` — covers SWM-02 through SWM-12
- [ ] `src/swarm/swarmTypes.ts` — shared types used by tests and implementation
- [ ] `src/components/modal/__tests__/AgentLaunchModal.test.tsx` — extend for SWM-01 Swarm tab

*(Existing `AgentSidebar.test.tsx` should be extended, not replaced)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (Anthropic API key) | Key from env var via `get_env_var` Tauri command; never included in CSP-exposed JS bundle |
| V3 Session Management | no | — |
| V4 Access Control | yes (file write to `.voss/swarm/`) | Scoped to workspace path; Rust validates path is under workspace |
| V5 Input Validation | yes (goal text → LLM prompt, file paths from LLM output) | Sanitize LLM-returned file paths before writing to disk; reject paths with `..` traversal |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LLM prompt injection via goal field | Tampering | Escape user goal before interpolating into coordinator prompt; do not execute LLM output as code |
| Path traversal in LLM-returned `fileScope` | Tampering | Validate that all paths from coordinator output start with workspace root; reject `../` sequences |
| API key exfiltration from bundle | Information Disclosure | Never bundle key into frontend JS; use `get_env_var` Tauri command; key never appears in `import.meta.env` at build time |
| Malicious agent CLI writes to arbitrary filesystem paths | Elevation of Privilege | Soft scope enforcement only (D-20) — this is accepted risk per design; document as limitation |
| Swarm result file injection | Spoofing | Result files are written by agents in the project directory; attacker with local filesystem access could forge results — accept for local tool |

---

## Sources

### Primary (HIGH confidence)

- `apps/voss-app/src-tauri/src/lib.rs` — `spawn_agent`, `pty_kill`, `write_context_pins`, `watch_keymap_overrides` patterns verified directly from source
- `apps/voss-app/src/pane/pty-ipc.ts` — `spawnAgent` interface, `AgentConfig` type, `PtyEvent` types verified from source
- `apps/voss-app/src/grid/layoutPresets.ts` — `buildSwarm`, `applyPreset`, `LayoutPreset` union verified from source
- `apps/voss-app/src/components/modal/AgentLaunchModal.tsx` — tab structure, `CLI_TABS`, `AgentLaunchConfig` verified from source
- `apps/voss-app/src/components/sidebar/AgentSidebar.tsx` — `AgentSidebarProps`, section structure verified from source
- `apps/voss-app/src/App.tsx` — `agentListForSidebar`, `handleLaunchAgent`, `gridController` access pattern verified from source
- `apps/voss-app/src/pane/budgetRegistry.ts` — signal store pattern for `swarmRegistry` verified from source
- `apps/voss-app/src-tauri/Cargo.toml` — no `reqwest` dep confirmed; Rust HTTP client not available
- `apps/voss-app/src-tauri/tauri.conf.json` — CSP `connect-src` restriction confirmed; `api.anthropic.com` not listed

### Secondary (MEDIUM confidence)

- `npm view @anthropic-ai/sdk` — version 0.98.0, official Anthropic maintainers, published 2023-01-31 [VERIFIED: npm registry]
- `npm view gray-matter` — version 4.0.3, published 2014-01-28, widely used [VERIFIED: npm registry]
- `npm view @tauri-apps/plugin-fs` — version 2.5.1 available [VERIFIED: npm registry]; not used (Rust polling preferred)

### Tertiary (LOW confidence)

- `claude-opus-4-5` model ID [ASSUMED — verify against Anthropic docs at implementation time]
- `claude --dangerously-skip-permissions` flag syntax [ASSUMED — verify against claude CLI `--help`]
- Codex/OpenCode positional arg interface [ASSUMED — verify before adding multi-CLI support]

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all libraries verified via npm registry; existing codebase integration points verified from source
- Architecture: HIGH — all patterns derived from existing source code, not assumed
- Pitfalls: HIGH — CSP pitfall verified from `tauri.conf.json`; Solid proxy pitfall from project memory; others derived from code reading
- LLM model IDs: LOW — model names rotate; must verify at implementation time

**Research date:** 2026-05-23
**Valid until:** 2026-06-23 (30 days; stable libraries; model IDs may need re-verification sooner)
