---
phase: A13-voss-app-agent-swarm-orchestration
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - apps/voss-app/src/swarm/swarmTypes.ts
  - apps/voss-app/src-tauri/src/lib.rs
  - apps/voss-app/src-tauri/tauri.conf.json
autonomous: true
requirements:
  - SWM-04
  - SWM-05
  - SWM-06
  - SWM-11

must_haves:
  truths:
    - "Swarm type contracts exist and are importable by downstream modules"
    - "Rust can atomically write manifest.json and task files to .voss/swarm/"
    - "Rust can poll .voss/swarm/results/ and emit events when new result files appear"
    - "Rust can read arbitrary environment variables for API key injection"
    - "CSP allows outbound HTTPS to api.anthropic.com"
  artifacts:
    - path: "apps/voss-app/src/swarm/swarmTypes.ts"
      provides: "All swarm type definitions: SwarmManifest, SwarmAgent, SubTask, SwarmAgentStatus, TaskFileContent, ResultFileParsed"
      exports: ["SwarmManifest", "SwarmAgent", "SubTask", "SwarmAgentStatus", "TaskFileContent", "ResultFileParsed"]
    - path: "apps/voss-app/src-tauri/src/lib.rs"
      provides: "write_swarm_files, watch_swarm_results, stop_swarm_watcher, get_env_var Tauri commands + SwarmWatchState managed state"
      contains: "write_swarm_files"
    - path: "apps/voss-app/src-tauri/tauri.conf.json"
      provides: "CSP connect-src includes api.anthropic.com"
      contains: "api.anthropic.com"
  key_links:
    - from: "apps/voss-app/src/swarm/swarmTypes.ts"
      to: "apps/voss-app/src-tauri/src/lib.rs"
      via: "Tauri invoke contracts — TS types mirror Rust command signatures"
      pattern: "invoke.*write_swarm_files|invoke.*watch_swarm_results"
---

<objective>
Create the foundational swarm type contracts and Rust infrastructure for file-mediated agent swarm orchestration.

Purpose: Establish the type system, file I/O commands, result watcher, and CSP configuration that all downstream plans depend on. Per D-01/D-04/D-13/D-14, the swarm uses .voss/swarm/ directory with atomic file writes and polling-based result detection.

Output: swarmTypes.ts (shared types), three new Tauri commands (write_swarm_files, watch_swarm_results, stop_swarm_watcher), one utility command (get_env_var), and CSP update.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-CONTEXT.md
@.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-RESEARCH.md

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From apps/voss-app/src-tauri/src/lib.rs (KeymapWatchState pattern — reuse for SwarmWatchState):
```rust
#[derive(Default)]
struct KeymapWatchState {
    stops: Mutex<HashMap<PathBuf, Arc<AtomicBool>>>,
}
// Used as: state: tauri::State<'_, KeymapWatchState>
// Registered via: .manage(KeymapWatchState::default())
```

From apps/voss-app/src-tauri/src/lib.rs (write_context_pins pattern — reuse for write_swarm_files):
```rust
#[tauri::command]
fn write_context_pins(workspace_path: String, pinned_paths: Vec<String>) -> Result<(), String> {
    let voss_dir = Path::new(&workspace_path).join(".voss");
    std::fs::create_dir_all(&voss_dir).map_err(|e| e.to_string())?;
    let target = voss_dir.join("context-pins.json");
    let tmp = voss_dir.join("context-pins.json.tmp");
    // atomic write-then-rename
}
```

From apps/voss-app/src-tauri/src/lib.rs (watch_keymap_overrides pattern — reuse for watch_swarm_results):
```rust
#[tauri::command]
fn watch_keymap_overrides(
    app: tauri::AppHandle,
    state: tauri::State<'_, KeymapWatchState>,
    workspace_path: String,
    // ...
) -> Result<KeymapValidationResult, String> {
    let stop = Arc::new(AtomicBool::new(false));
    let previous = state.stops.lock()...insert(..., Arc::clone(&stop));
    if let Some(previous) = previous { previous.store(true, Ordering::Relaxed); }
    std::thread::spawn(move || {
        while !stop.load(Ordering::Relaxed) {
            std::thread::sleep(Duration::from_millis(500));
            // poll + emit event
        }
    });
}
```

From apps/voss-app/src-tauri/tauri.conf.json (current CSP):
```json
"csp": "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; script-src 'self'; connect-src 'self' ipc: http://ipc.localhost"
```

From apps/voss-app/src-tauri/src/lib.rs (managed state registration):
```rust
.manage(Arc::new(PtyRegistry::default()))
.manage(Mutex::new(GridState::default()))
.manage(KeymapWatchState::default())
```

From apps/voss-app/src-tauri/src/lib.rs (handler registration):
```rust
.invoke_handler(tauri::generate_handler![
    // ... existing commands ...
    write_context_pins,
    // ... more commands ...
])
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create swarm type contracts</name>
  <files>apps/voss-app/src/swarm/swarmTypes.ts</files>
  <read_first>
    apps/voss-app/src/pane/pty-ipc.ts (AgentConfig type at line 42)
    apps/voss-app/src/pane/budgetRegistry.ts (signal store pattern)
    .planning/phases/A13-voss-app-agent-swarm-orchestration/A13-CONTEXT.md (file protocol section)
    .planning/phases/A13-voss-app-agent-swarm-orchestration/A13-SPEC.md (manifest.json and task file formats)
  </read_first>
  <action>
    Create the directory apps/voss-app/src/swarm/ and the file swarmTypes.ts. Export the following types:

    SwarmAgentStatus: union of "pending" | "running" | "complete" | "stuck" | "error". Per D-22, "stuck" means timeout with no result.

    SubTask: the coordinator's output per agent. Fields: id (string, e.g. "agent-1"), cli (string, e.g. "claude"), goal (string), fileScope (string array), excludeScope (string array). Per D-16/D-18.

    SwarmAgent: runtime agent state. Fields: id (string), paneId (string), ptyId (string, the session ID from spawn_agent), cli (string), status (SwarmAgentStatus), taskSummary (string, short description). Per D-08.

    SwarmManifest: persisted swarm state per D-13. Fields: id (string, "swarm-{timestamp}"), goal (string), status ("running" | "complete" | "cancelled"), created (number, epoch ms), agents (SwarmAgent array).

    TaskFileContent: what gets written to each task .md file per D-05. Fields: swarmId (string), agentId (string), cli (string), goal (string), fileScope (string array), excludeScope (string array), sharedContextPath (string).

    ResultFileParsed: parsed from agent result .md files per D-06. Fields: agentId (string), status ("complete" | "error"), filesModified (string array), durationSecs (number or null), summary (string).

    SWARM_DIR: exported const string ".voss/swarm".
    MAX_CONCURRENT_AGENTS: exported const number 6 per D-12.
    SWARM_RESULT_EVENT: exported const string "voss://swarm-result-added".
    SWARM_POLL_MS: exported const number 500.

    All types are plain TypeScript interfaces/types with no runtime dependencies. No SolidJS imports. This file is a pure contract module.
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <acceptance_criteria>
    - File exists at apps/voss-app/src/swarm/swarmTypes.ts
    - Exports SwarmManifest, SwarmAgent, SubTask, SwarmAgentStatus, TaskFileContent, ResultFileParsed, SWARM_DIR, MAX_CONCURRENT_AGENTS, SWARM_RESULT_EVENT, SWARM_POLL_MS
    - tsc --noEmit passes with zero errors
    - No runtime imports (no solid-js, no @tauri-apps)
  </acceptance_criteria>
  <done>All swarm types exported, tsc clean, zero runtime dependencies in the file</done>
</task>

<task type="auto">
  <name>Task 2: Add Rust Tauri commands for swarm file I/O, result watcher, env var access, and CSP update</name>
  <files>apps/voss-app/src-tauri/src/lib.rs, apps/voss-app/src-tauri/tauri.conf.json</files>
  <read_first>
    apps/voss-app/src-tauri/src/lib.rs (full file — read write_context_pins at ~line 398, watch_keymap_overrides at ~line 551, KeymapWatchState at ~line 499, .manage() calls at ~line 755, generate_handler! at ~line 762)
    apps/voss-app/src-tauri/tauri.conf.json (CSP at ~line 29)
    .planning/phases/A13-voss-app-agent-swarm-orchestration/A13-RESEARCH.md (Pattern 2: Rust Polling File Watcher, Pattern 3: Task File Write, Pitfall 1: CSP, Pitfall 3: race, Pitfall 5: backfill)
  </read_first>
  <action>
    A. CSP update in tauri.conf.json: Append "https://api.anthropic.com" to the connect-src directive. The full value becomes: "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; script-src 'self'; connect-src 'self' ipc: http://ipc.localhost https://api.anthropic.com". Per Pitfall 1 from RESEARCH.

    B. Add SwarmWatchState struct (above the existing KeymapWatchState, same section pattern):
       - Derive Default
       - Single field: stops: Mutex<HashMap<String, Arc<AtomicBool>>> (keyed by swarm_id string, not PathBuf)

    C. Add get_env_var Tauri command:
       - Signature: fn get_env_var(name: String) -> Result<String, String>
       - Body: std::env::var(&name).map_err(|e| e.to_string())
       - Per RESEARCH Pitfall 6: needed because ANTHROPIC_API_KEY is not available via import.meta.env in Tauri webview

    D. Add write_swarm_files Tauri command:
       - Signature: fn write_swarm_files(workspace_path: String, manifest_json: String, tasks: Vec<(String, String)>, shared_context: String) -> Result<(), String>
       - Validate workspace_path is not empty
       - Create directories: .voss/swarm/, .voss/swarm/tasks/, .voss/swarm/results/, .voss/swarm/shared/
       - Atomic manifest write: write to manifest.json.tmp, then rename to manifest.json (same as write_context_pins pattern)
       - Write each task file: for each (filename, content) tuple, write to .voss/swarm/tasks/{filename}
       - Write shared/context.md from the shared_context param
       - Per D-04, D-05, D-13

    E. Add watch_swarm_results Tauri command:
       - Signature: fn watch_swarm_results(app: tauri::AppHandle, state: tauri::State<'_, SwarmWatchState>, swarm_id: String, results_dir: String) -> Result<(), String>
       - Cancel any prior watcher for this swarm_id (same pattern as watch_keymap_overrides)
       - Spawn a thread that:
         1. On FIRST iteration (before entering poll loop), does a backfill scan: reads results_dir, emits an event for each existing .result.md file. Per RESEARCH Pitfall 5.
         2. Poll loop: sleep 500ms, read_dir results_dir (graceful continue on error per Pitfall 3), for each .result.md file not in the known set, add to known set and emit event
         3. Event name: "voss://swarm-result-added"
         4. Event payload: JSON object with swarmId (string) and resultFile (string, just the filename)
         5. Stop when the AtomicBool is set to true

    F. Add stop_swarm_watcher Tauri command:
       - Signature: fn stop_swarm_watcher(state: tauri::State<'_, SwarmWatchState>, swarm_id: String) -> Result<(), String>
       - Look up swarm_id in state.stops, set the AtomicBool to true, remove the entry

    G. Register new state and commands:
       - Add .manage(SwarmWatchState::default()) alongside existing .manage() calls
       - Add write_swarm_files, watch_swarm_results, stop_swarm_watcher, get_env_var to the generate_handler![] array

    Place swarm-related commands in their own section with a comment banner: // ---- Swarm orchestration commands (A13) ---- after the context pin section.
  </action>
  <verify>
    <automated>cd apps/voss-app/src-tauri && cargo build 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - cargo build succeeds with zero errors
    - tauri.conf.json connect-src contains "https://api.anthropic.com"
    - lib.rs contains write_swarm_files, watch_swarm_results, stop_swarm_watcher, get_env_var as #[tauri::command] functions
    - SwarmWatchState struct exists with Default derive
    - .manage(SwarmWatchState::default()) is present in the builder chain
    - All four new commands appear in generate_handler![]
    - write_swarm_files creates .voss/swarm/{tasks,results,shared} directories and uses atomic write-then-rename for manifest
    - watch_swarm_results does a backfill scan on first iteration before entering poll loop
  </acceptance_criteria>
  <done>All Rust commands compile, CSP updated, managed state registered, handler array includes all four new commands</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Webview -> Rust IPC | Tauri invoke calls from TS to Rust commands |
| Rust -> Filesystem | write_swarm_files writes to .voss/swarm/ under workspace_path |
| Webview -> api.anthropic.com | CSP now allows outbound HTTPS to Anthropic API |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-A13-01 | Tampering | write_swarm_files workspace_path | mitigate | Validate workspace_path is non-empty; all paths are joined under workspace_path/.voss/swarm/ — no traversal possible via join semantics |
| T-A13-02 | Information Disclosure | get_env_var | accept | Exposes any env var to webview JS; acceptable for local desktop app with no remote access. Only used for ANTHROPIC_API_KEY. |
| T-A13-03 | Spoofing | watch_swarm_results result files | accept | Local filesystem; attacker with local access could forge result files. Acceptable for local developer tool per D-20. |
| T-A13-SC | Tampering | npm installs (Plan 02) | mitigate | Package Legitimacy Audit completed in RESEARCH.md — @anthropic-ai/sdk [VERIFIED], gray-matter [VERIFIED] |
</threat_model>

<verification>
cargo build -p voss-app (or from src-tauri) must succeed.
tsc --noEmit must pass.
CSP line in tauri.conf.json must contain api.anthropic.com.
</verification>

<success_criteria>
All swarm type contracts are importable from src/swarm/swarmTypes.ts. Rust commands write_swarm_files, watch_swarm_results, stop_swarm_watcher, and get_env_var are registered and compile. CSP allows api.anthropic.com. No existing tests regress.
</success_criteria>

<output>
Create `.planning/phases/A13-voss-app-agent-swarm-orchestration/A13-01-SUMMARY.md` when done
</output>
