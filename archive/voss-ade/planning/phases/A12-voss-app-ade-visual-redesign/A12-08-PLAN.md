---
phase: A12-voss-app-ade-visual-redesign
plan: 08
type: execute
wave: 3
depends_on:
  - A12-03
files_modified:
  - apps/voss-app/src-tauri/src/lib.rs
  - apps/voss-app/src/components/sidebar/GitSection.tsx
  - apps/voss-app/src/components/sidebar/SessionsSection.tsx
  - apps/voss-app/src/components/sidebar/AgentSidebar.tsx
  - apps/voss-app/src/App.tsx
  - apps/voss-app/src/components/sidebar/__tests__/GitSection.test.tsx
autonomous: true
requirements:
  - ADE-08

must_haves:
  truths:
    - "Git section shows recent commits with relative timestamps"
    - "Git section shows 'Not a git repository' for non-git directories"
    - "Sessions section shows agent session start/stop events"
    - "Git log refreshes when window regains focus"
    - "New git_log Tauri command returns commit hash, message, and timestamp"
  artifacts:
    - path: "apps/voss-app/src-tauri/src/lib.rs"
      provides: "git_log Tauri command"
      contains: "git_log"
    - path: "apps/voss-app/src/components/sidebar/GitSection.tsx"
      provides: "Git log section component"
      exports: ["GitSection"]
    - path: "apps/voss-app/src/components/sidebar/__tests__/GitSection.test.tsx"
      provides: "Git section tests"
  key_links:
    - from: "apps/voss-app/src/components/sidebar/GitSection.tsx"
      to: "apps/voss-app/src-tauri/src/lib.rs"
      via: "invoke('git_log', { workspacePath, limit })"
      pattern: "invoke.*git_log"
    - from: "apps/voss-app/src/components/sidebar/AgentSidebar.tsx"
      to: "apps/voss-app/src/components/sidebar/GitSection.tsx"
      via: "GitSection component in GIT section"
      pattern: "<GitSection"
---

<objective>
Add git log display to the sidebar GIT section and finalize the Sessions section with agent session tracking. Create the git_log Tauri backend command. Wire both sections into the sidebar.

Purpose: Git history and agent session tracking complete the sidebar's four sections, providing full project context alongside agent management.
Output: git_log Rust command, GitSection.tsx, SessionsSection integration, tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/A12-voss-app-ade-visual-redesign/A12-CONTEXT.md
@.planning/phases/A12-voss-app-ade-visual-redesign/A12-RESEARCH.md
@.planning/phases/A12-voss-app-ade-visual-redesign/A12-UI-SPEC.md
@.planning/phases/A12-voss-app-ade-visual-redesign/A12-03-SUMMARY.md

<interfaces>
<!-- Existing get_active_agents Tauri command -->
invoke<AgentEntry[]>('get_active_agents', { workspacePath })
AgentEntry = { paneId, sessionId, cliBinary, cliArgs, cwd, status, lastSeen }
- status can be "running" or "stopped"
- This is the data source for Sessions section

<!-- GitCommit structure from RESEARCH -->
struct GitCommit { hash: String, message: String, timestamp_secs: i64 }
- git_log runs `git log --oneline -N --format="%H %ct %s"` via std::process::Command
- Returns empty vec on non-git directories (graceful)

<!-- Sessions section UI-SPEC -->
- Row format: relative timestamp (JetBrains Mono 11px --fg-3) + description (Inter 12px --fg-1)
- Empty state: "No sessions yet"

<!-- Git section UI-SPEC -->
- Source: git log --oneline -10 from project root
- Row format: same as Sessions (timestamp + message)
- Empty state: "Not a git repository"
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add git_log Tauri command and wire Sessions data</name>
  <files>
    apps/voss-app/src-tauri/src/lib.rs,
    apps/voss-app/src/App.tsx
  </files>
  <read_first>
    apps/voss-app/src-tauri/src/lib.rs (imports, existing command pattern, generate_handler),
    apps/voss-app/src/App.tsx (agentConfigByPaneId, fetchAgentConfigs pattern),
    .planning/phases/A12-voss-app-ade-visual-redesign/A12-RESEARCH.md (Finding 4: Tauri commands, Code Examples: git_log Rust)
  </read_first>
  <action>
    1. In lib.rs, add GitCommit struct (with #[derive(Debug, serde::Serialize)]):
       - hash: String
       - message: String
       - timestamp_secs: i64

    2. Add git_log Tauri command:
       #[tauri::command]
       fn git_log(workspace_path: String, limit: usize) -> Result<Vec<GitCommit>, String>
       - Use std::process::Command::new("git") with args ["-C", &workspace_path, "log", &format!("-{limit}"), "--format=%H %ct %s"]
       - Capture output, check status.success()
       - If not success (not a git repo): return Ok(Vec::new()) — graceful empty
       - Parse stdout: each line is "hash timestamp message" (splitn 3 on space)
       - Return parsed commits

    3. Register git_log in tauri::generate_handler![...] (after list_dir)

    4. In App.tsx, add session tracking:
       - Create a derived signal for sessions that reads from activeMounted().agentConfigByPaneId()
       - Use the existing get_active_agents Tauri call which returns status field
       - Create sessionLog: a createSignal of array of { id: string, cliBinary: string, status: string, startedAt: number, description: string }
       - On each agentConfigByPaneId update, diff against previous to detect new entries (started) and removed entries (stopped)
       - Track session events in the sessionLog signal
       - Pass sessionLog to AgentSidebar sessions prop
  </action>
  <verify>
    <automated>cd apps/voss-app && cargo check 2>&1 | tail -5 && npx tsc --noEmit 2>&1 | head -10</automated>
  </verify>
  <acceptance_criteria>
    - GitCommit struct defined with Serialize derive
    - git_log Tauri command compiles and is registered
    - git_log returns empty vec for non-git directories (no error)
    - git_log parses output format "%H %ct %s" correctly
    - App.tsx derives session events from agent config changes
    - Both Rust and TypeScript compile
  </acceptance_criteria>
  <done>git_log Tauri command added. Session tracking derived from agent config changes.</done>
</task>

<task type="auto">
  <name>Task 2: Create GitSection component and wire both sections into sidebar</name>
  <files>
    apps/voss-app/src/components/sidebar/GitSection.tsx,
    apps/voss-app/src/components/sidebar/SessionsSection.tsx,
    apps/voss-app/src/components/sidebar/AgentSidebar.tsx,
    apps/voss-app/src/components/sidebar/__tests__/GitSection.test.tsx
  </files>
  <read_first>
    apps/voss-app/src/components/sidebar/AgentSidebar.tsx,
    apps/voss-app/src/components/sidebar/SessionsSection.tsx,
    .planning/phases/A12-voss-app-ade-visual-redesign/A12-UI-SPEC.md (Git Section, Sessions Section)
  </read_first>
  <action>
    1. Create apps/voss-app/src/components/sidebar/GitSection.tsx:
       Props: workspacePath: string | null

       Component logic:
       - createSignal for commits (GitCommit array, initially empty)
       - createSignal for isGitRepo (boolean, initially true — assume yes until proven otherwise)
       - createEffect: when workspacePath changes (and is not null), invoke('git_log', { workspacePath, limit: 10 }) and set commits. If result is empty, set isGitRepo to false (heuristic; actual git repos can have 0 commits too, but that shows "No commits yet")
       - Refresh on window focus: add event listener for 'focus' on window, re-fetch git_log. Clean up in onCleanup.

       Type GitCommit matching Rust: { hash: string, message: string, timestamp_secs: number }

       Relative timestamp formatting: use a helper function that computes relative time from timestamp_secs * 1000 vs Date.now(). Use Intl.RelativeTimeFormat (per RESEARCH Don't Hand-Roll) or simple math:
       - < 60s: "just now"
       - < 60m: "{n}m ago"
       - < 24h: "{n}h ago"
       - < 7d: "{n}d ago"
       - else: date string

       Render:
       - Each commit as a row: relative timestamp (JetBrains Mono 11px --fg-3) + commit message (Inter 12px --fg-1, truncated with ellipsis)
       - Hover: background var(--bg-2)
       - Empty state (no workspacePath): "No project open"
       - Empty state (workspacePath but not git / no commits): differentiate:
         If isGitRepo false: "Not a git repository"
         If isGitRepo true but 0 commits: "No commits yet"

    2. Update SessionsSection.tsx if needed:
       - Ensure it accepts the session data format from App.tsx task 1
       - Each session row: relative timestamp + "{cliBinary} - {status}" description
       - Ensure empty state "No sessions yet" per UI-SPEC

    3. In AgentSidebar.tsx:
       - Import GitSection from './GitSection'
       - Replace the GIT section placeholder with <GitSection workspacePath={props.workspacePath} />
       - Ensure SessionsSection receives sessions from props (already wired in P2)

    4. Create apps/voss-app/src/components/sidebar/__tests__/GitSection.test.tsx:
       - Test: "renders 'Not a git repository' when no commits" — mock invoke('git_log') to return empty array, render with workspacePath="/non-git", assert "Not a git repository" text
       - Test: "renders commit entries" — mock invoke to return 3 test commits, render, assert 3 rows with commit messages
       - Test: "renders 'No project open' when workspacePath is null" — render with null path, assert "No project open"
       - Test: "formats relative timestamps" — render with a commit from 5 minutes ago, assert "5m ago" text
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run --grep "GitSection" 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - GitSection renders commit list with relative timestamps
    - "Not a git repository" shown for non-git dirs
    - "No commits yet" shown for git dirs with 0 commits
    - "No project open" shown when workspacePath is null
    - Git log refreshes on window focus
    - SessionsSection renders session events with status
    - Both sections integrated into AgentSidebar
    - Tests pass
    - Full suite green
  </acceptance_criteria>
  <done>GitSection and SessionsSection complete. All 4 sidebar sections functional. Tests pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Frontend -> git_log Tauri command | workspace_path crosses to child process execution |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation |
|-----------|----------|-----------|-------------|------------|
| T-A12-08a | Tampering | git_log workspace_path | mitigate | Path passed to git -C; git itself validates the path. The workspace_path comes from the app's own project state, not arbitrary user input. |
| T-A12-08b | Spoofing | git log output injection | mitigate | Parse output server-side in Rust with strict splitn(3, ' ') format; never eval or render as HTML; display as text content only |
| T-A12-SC | Tampering | npm/pip/cargo installs | accept | No package installs in this plan |
</threat_model>

<verification>
cargo check — Rust compiles with git_log.
pnpm --filter voss-app test — all tests green.
</verification>

<success_criteria>
1. git_log Tauri command returns commits with hash, message, timestamp per ADE-08.
2. GitSection shows recent commits with relative timestamps.
3. Non-git directories show fallback message.
4. Sessions section shows agent session events per D-06.
5. Git log refreshes on window focus.
6. All 4 sidebar sections (Agents, Sessions, Files, Git) are functional.
7. All tests pass.
</success_criteria>

<output>
Create `.planning/phases/A12-voss-app-ade-visual-redesign/A12-08-SUMMARY.md` when done
</output>
