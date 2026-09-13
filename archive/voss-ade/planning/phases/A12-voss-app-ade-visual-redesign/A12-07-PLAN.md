---
phase: A12-voss-app-ade-visual-redesign
plan: 07
type: execute
wave: 3
depends_on:
  - A12-03
files_modified:
  - apps/voss-app/src-tauri/src/lib.rs
  - apps/voss-app/src/components/sidebar/FileTree.tsx
  - apps/voss-app/src/components/sidebar/AgentSidebar.tsx
  - apps/voss-app/src/components/sidebar/__tests__/FileTree.test.tsx
autonomous: true
requirements:
  - ADE-07

must_haves:
  truths:
    - "File tree shows project directory structure in sidebar FILES section"
    - "Directories can be expanded and collapsed"
    - "File tree scrolls within its section"
    - "Clicking a file does nothing (read-only per D-05)"
    - "Empty state shows 'No project open' when no project loaded"
    - "New list_dir Tauri command returns directory entries with name, is_dir, children"
  artifacts:
    - path: "apps/voss-app/src-tauri/src/lib.rs"
      provides: "list_dir Tauri command for filesystem listing"
      contains: "list_dir"
    - path: "apps/voss-app/src/components/sidebar/FileTree.tsx"
      provides: "Recursive file tree component"
      exports: ["FileTree"]
  key_links:
    - from: "apps/voss-app/src/components/sidebar/FileTree.tsx"
      to: "apps/voss-app/src-tauri/src/lib.rs"
      via: "invoke('list_dir', { path })"
      pattern: "invoke.*list_dir"
    - from: "apps/voss-app/src/components/sidebar/AgentSidebar.tsx"
      to: "apps/voss-app/src/components/sidebar/FileTree.tsx"
      via: "FileTree component in FILES section"
      pattern: "<FileTree"
---

<objective>
Add a read-only file tree to the sidebar FILES section. Create the list_dir Tauri backend command and the FileTree frontend component. Directories expand/collapse, files are non-interactive.

Purpose: File tree provides project context at a glance — developers can see what files exist without leaving the ADE.
Output: list_dir Rust command, FileTree.tsx component, integration into AgentSidebar.
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
<!-- Existing Tauri command registration pattern (lib.rs lines 628-679) -->
.invoke_handler(tauri::generate_handler![
    ... existing commands ...,
    // new commands added at end
])

<!-- DirEntry structure from RESEARCH -->
struct DirEntry { name: String, is_dir: bool, children: Vec<DirEntry> }
- read_dir_shallow(path, depth) — recursive with depth limit
- Sorted: dirs first, then alphabetical

<!-- FileTree UI-SPEC contract -->
- Tree icons: ▾ expanded dir, ▸ collapsed dir, ● file — JetBrains Mono 11px --fg-3
- Entry labels: Inter 12px --fg-1 for dirs, --fg-2 for files
- Indent per level: 12px
- Initial depth: 2 levels expanded
- Click file: no action (D-05)
- Empty state: "No project open" — Inter 12px --fg-3, centered
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add list_dir Tauri command</name>
  <files>
    apps/voss-app/src-tauri/src/lib.rs
  </files>
  <read_first>
    apps/voss-app/src-tauri/src/lib.rs (lines 1-30 for imports/derives, lines 625-682 for generate_handler registration),
    .planning/phases/A12-voss-app-ade-visual-redesign/A12-RESEARCH.md (Finding 4: Tauri commands, Code Examples: Rust commands)
  </read_first>
  <action>
    1. In lib.rs, add the DirEntry struct before the list_dir command (after the existing command functions, before the run() function). DirEntry needs #[derive(Debug, serde::Serialize)] (serde::Serialize is already used in the file for other structs):
       - name: String
       - is_dir: bool
       - children: Vec<DirEntry> (with #[serde(skip_serializing_if = "Vec::is_empty")])

    2. Add helper function read_dir_shallow(path: &std::path::Path, depth: u32) -> Vec<DirEntry>:
       - If depth == 0, return empty vec
       - Read directory with std::fs::read_dir, filter_map Ok entries
       - For each entry: get name (to_string_lossy), is_dir from file_type
       - Skip hidden files (name starts with '.') and common noise dirs (node_modules, target, .git, __pycache__, .next, dist, build)
       - If is_dir and depth > 1, recurse children
       - Sort: dirs first (b.is_dir.cmp(&a.is_dir)), then alphabetical (a.name.cmp(&b.name))
       - Return entries vec

    3. Add the Tauri command:
       #[tauri::command]
       fn list_dir(path: String) -> Result<Vec<DirEntry>, String>
       - Canonicalize the path first using std::fs::canonicalize to prevent path traversal
       - Call read_dir_shallow with depth 2 (initial 2 levels per UI-SPEC)
       - Return Ok(entries)

    4. Register list_dir in tauri::generate_handler![...] (add after write_context_pins)
  </action>
  <verify>
    <automated>cd apps/voss-app && cargo check 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - DirEntry struct defined with Serialize derive
    - list_dir Tauri command compiles and is registered
    - read_dir_shallow skips hidden files and noise directories
    - Path is canonicalized before read_dir (path traversal mitigation)
    - Depth limited to 2 levels
    - Entries sorted dirs-first then alphabetical
    - cargo check succeeds
  </acceptance_criteria>
  <done>list_dir Tauri command added and registered. Rust compiles.</done>
</task>

<task type="auto">
  <name>Task 2: Create FileTree component and wire into sidebar</name>
  <files>
    apps/voss-app/src/components/sidebar/FileTree.tsx,
    apps/voss-app/src/components/sidebar/AgentSidebar.tsx,
    apps/voss-app/src/components/sidebar/__tests__/FileTree.test.tsx
  </files>
  <read_first>
    apps/voss-app/src/components/sidebar/AgentSidebar.tsx,
    .planning/phases/A12-voss-app-ade-visual-redesign/A12-UI-SPEC.md (File Tree contract),
    .planning/phases/A12-voss-app-ade-visual-redesign/A12-RESEARCH.md (Finding 4)
  </read_first>
  <action>
    1. Create apps/voss-app/src/components/sidebar/FileTree.tsx:
       Type DirEntry matching the Rust struct: { name: string, is_dir: boolean, children?: DirEntry[] }

       Props: projectPath: string | null

       Component logic:
       - createSignal for entries (DirEntry array, initially empty)
       - createSignal for expandedPaths (Set of string paths, initially the first 2 levels per UI-SPEC)
       - createEffect: when projectPath changes (and is not null), invoke('list_dir', { path: projectPath }) and set entries from result. On error, set entries to empty.
       - toggleExpand function: add/remove path from expandedPaths set
       - Lazy expand: when user expands a dir whose children are empty (depth > 2), call invoke('list_dir', { path: fullDirPath }) to load deeper entries. Debounce to avoid rapid-fire calls.

       Render a recursive TreeNode function:
       - Each entry renders as a div with padding-left = depth * 12px per UI-SPEC
       - Dir entry: toggle icon (▾ expanded, ▸ collapsed) in JetBrains Mono 11px --fg-3, dir name in Inter 12px --fg-1, onClick toggles expand
       - File entry: ● icon in JetBrains Mono 11px --fg-3, file name in Inter 12px --fg-2, onClick does nothing per D-05
       - Hover: background var(--bg-2) per UI-SPEC
       - If children exist and dir is expanded, recursively render children

       Empty state: when projectPath is null, render "No project open" in Inter 12px --fg-3, centered. When projectPath exists but entries empty after load, render "Empty directory".

    2. In AgentSidebar.tsx, replace the FILES section placeholder:
       - Import FileTree from './FileTree'
       - Replace the placeholder div in the FILES section with <FileTree projectPath={props.projectPath} />

    3. Create apps/voss-app/src/components/sidebar/__tests__/FileTree.test.tsx:
       - Test: "renders empty state when projectPath is null" — render FileTree with null path, assert "No project open" text visible
       - Test: "renders directory entries" — mock invoke('list_dir') to return test entries, render with projectPath="/test", assert dir and file names visible
       - Test: "clicking dir toggles expand/collapse" — render with mock entries, click a dir, assert children become visible
       - Test: "clicking file does nothing" — render, click a file entry, assert no side effects (no navigation, no error)
  </action>
  <verify>
    <automated>cd apps/voss-app && npx vitest run --grep "FileTree" 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - FileTree renders directory listing from list_dir Tauri command
    - Dirs show ▾/▸ toggle icons, files show ● icon
    - Dirs clickable for expand/collapse, files non-interactive per D-05
    - 12px indent per nesting level
    - Empty state shows "No project open" when projectPath is null
    - FileTree integrated into AgentSidebar FILES section
    - Tests pass
    - Full suite green
  </acceptance_criteria>
  <done>FileTree component renders recursive directory listing. Integrated into sidebar FILES section. Tests pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Frontend -> list_dir Tauri command | Path string crosses to filesystem operation |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation |
|-----------|----------|-----------|-------------|------------|
| T-A12-07 | Tampering | list_dir path traversal | mitigate | Canonicalize path in Rust before read_dir; verify resolved path is under a reasonable root |
| T-A12-SC | Tampering | npm/pip/cargo installs | accept | No package installs in this plan |
</threat_model>

<verification>
cargo check — Rust compiles with list_dir.
pnpm --filter voss-app test — all tests green.
</verification>

<success_criteria>
1. list_dir Tauri command returns DirEntry list sorted dirs-first.
2. FileTree renders directory structure with expand/collapse per D-05.
3. Files are non-interactive (click does nothing).
4. Empty state per UI-SPEC copywriting contract.
5. Path traversal mitigated via canonicalize.
6. All tests pass.
</success_criteria>

<output>
Create `.planning/phases/A12-voss-app-ade-visual-redesign/A12-07-SUMMARY.md` when done
</output>
