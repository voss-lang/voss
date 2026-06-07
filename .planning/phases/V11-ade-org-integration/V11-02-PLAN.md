---
phase: V11-ade-org-integration
plan: 02
type: execute
wave: 1
depends_on: ["01"]
files_modified:
  - apps/voss-app/src-tauri/src/lib.rs
  - apps/voss-app/src/org/orgStore.ts
  - apps/voss-app/src/org/decisionActions.ts
autonomous: true
requirements: [VADE-01, VADE-02, VADE-03, VADE-04, VADE-05, VADE-06, VADE-07, VADE-08, VADE-09, VADE-10]
user_setup: []
must_haves:
  truths:
    - "A single aggregate Tauri command load_run(run_id, cwd, cli_binary) returns typed RunData for a valid run"
    - "enumerate_runs returns only V4+ session-tree subdirectories, never legacy flat .json session records"
    - "run_decision shells the voss CLI and returns captured stdout/stderr/exit code"
    - "Invalid/missing run_id yields an error (not a crash or path traversal); run-final.json absence is tolerated"
    - "The frontend store wraps the commands and exposes runData/loadError/loading signals"
  artifacts:
    - path: "apps/voss-app/src-tauri/src/lib.rs"
      provides: "load_run, enumerate_runs, run_decision commands + handler registration"
      contains: "fn load_run"
    - path: "apps/voss-app/src/org/orgStore.ts"
      provides: "createSignal(runData) + loadRun/enumerateRuns/refresh wrappers"
      exports: ["runData", "loadRun", "enumerateRuns"]
    - path: "apps/voss-app/src/org/decisionActions.ts"
      provides: "buildDecisionCommand + runDecision invoke wrapper (D-07/D-08)"
      exports: ["runDecision", "buildDecisionCommand"]
  key_links:
    - from: "apps/voss-app/src/org/orgStore.ts"
      to: "load_run / enumerate_runs (Rust)"
      via: "invoke('load_run') / invoke('enumerate_runs')"
      pattern: "invoke<.*>\\('load_run'"
    - from: "apps/voss-app/src-tauri/src/lib.rs"
      to: "voss audit --format json subprocess"
      via: "std::process::Command"
      pattern: "Command::new"
---

<objective>
Build the CLI-JSON data layer (VADE-DATA): the aggregate `load_run` Tauri command (D-01), the `enumerate_runs` discovery command with the dual-layout filter (D-03), and the `run_decision` command that shells the voss CLI and captures stdout/stderr/exit code (D-08). Add the SolidJS store wrappers and the decision-action wrapper. This is the single data path; no `.voss/sessions` parsing happens in the frontend.

Purpose: Wave 1 — every panel renders from `RunData` produced here; the view shell and decision flow consume these wrappers.
Output: 3 Tauri commands in `lib.rs` (registered), `orgStore.ts`, `decisionActions.ts`, an `enumerate_runs` cargo test.

**D-01 deviation note (verified):** D-01 listed `voss board` as a subprocess source for `load_run`. `voss board` has NO JSON output (verified — `board_cmd` in `voss/harness/cli.py` only renders text; no `--format json`/`--json` flag). `load_run` therefore reads the run-directory node files directly in Rust (enumerate `<root_id>/*.json`, exclude `.review.json`, derive column/risk per the verified algorithm) per RESEARCH Open-Question-2 resolution. This achieves D-01's intent (all run data via one aggregate command) via direct file read rather than shelling `voss board`. `voss audit --format json` IS still shelled for the audit section.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V11-ade-org-integration/V11-SPEC.md
@.planning/phases/V11-ade-org-integration/V11-RESEARCH.md
@.planning/phases/V11-ade-org-integration/V11-PATTERNS.md
@.planning/phases/V11-ade-org-integration/V11-01-SUMMARY.md

<interfaces>
<!-- From src/org/types.ts (Plan 01). orgStore + decisionActions import these. -->
RunData { run_id, session_tree {root_id, nodes: SessionTreeNode[]}, review: Record<string,ReviewSidecar>, audit: AuditReport|null, run_final: RunFinal|null }
RunEntry { run_id: string, mtime_secs: number, has_run_final: boolean }
DecisionResult { success: boolean, stdout: string, stderr: string, exit_code: number }

<!-- VERIFIED Rust analogs in lib.rs (PATTERNS.md): -->
<!-- git_log (lib.rs ~936-971): std::process::Command::new(bin).args([...]).output(); non-success → Ok(empty) graceful degradation -->
<!-- read_dir_shallow (lib.rs ~884-920): std::fs::read_dir; filter_map(e.ok); filter is_dir; sort -->
<!-- spawn_agent (lib.rs ~183): accepts cli_binary: String from frontend (macOS PATH not inherited) -->
<!-- get_theme_overrides (lib.rs ~61-78): read_to_string → match Ok/Err fallback; serde_json::from_str → match fallback -->
<!-- handler registration: tauri::generate_handler![ ... ] in run() (~lib.rs 983-1042) -->

<!-- VERIFIED decision CLI surface (cli.py — IMPORTANT, differs from earlier assumptions): -->
<!-- The ONLY non-interactive run-level write path is: voss audit <run_id> --cwd <path> --approve -->
<!--   stdout "approve: permitted for <run_id>" (exit 0) OR "approve refused: ..." (exit 1, err). -->
<!-- There is NO standalone `voss approve/reject/unblock <card>` command. -->
<!-- `voss team run` sign-off uses interactive click.prompt (NOT shellable non-interactively). -->
<!-- audit JSON read path: voss audit <run_id> --cwd <path> --format json -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: load_run + enumerate_runs Tauri commands + dual-layout cargo test</name>
  <files>apps/voss-app/src-tauri/src/lib.rs</files>
  <read_first>
    - apps/voss-app/src-tauri/src/lib.rs (git_log, read_dir_shallow, spawn_agent cli_binary param, get_theme_overrides read/parse fallback, the existing `#[cfg(test)] mod tests` block ~line 222, generate_handler! registration)
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md ("src-tauri/src/lib.rs" section — exact subprocess + read_dir + traversal-guard + registration patterns)
    - .planning/phases/V11-ade-org-integration/V11-RESEARCH.md (Code Examples: load_run skeleton, enumerate_runs; Pitfalls 1/2/5/7; Open Questions 1+2 — read node files directly in Rust, accept cli_binary, pass --cwd)
  </read_first>
  <action>
    Add `#[derive(serde::Serialize, serde::Deserialize)] struct RunData` (fields: run_id, session_tree, review, audit, run_final — use `serde_json::Value` for the JSON payloads per RESEARCH skeleton) and `RunEntry { run_id, mtime_secs: u64, has_run_final: bool }`. Implement `#[tauri::command] fn load_run(run_id: String, cwd: String, cli_binary: String) -> Result<RunData, String>`: FIRST reject `run_id` containing `/`, `\\`, or `..` (return Err) — path traversal guard before any FS access (T-V11-03, mirror audit_cmd cli.py:2571). Then: (a) read the `<cwd>/.voss/sessions/<run_id>/` node `.json` files directly (glob, exclude `*.review.json`) into a `session_tree` value `{root_id, nodes:[...]}` using the read-then-fallback pattern (per Open Q2 — direct Rust read, no `voss session tree` subprocess); (b) read `*.review.json` sidecars into a `review` map keyed by node id; (c) shell `cli_binary` with args `["audit", &run_id, "--cwd", &cwd, "--format", "json"]` via `std::process::Command` (NOT shell string — command injection guard T-V11-04), parse stdout to `audit` value, graceful-degrade to null on non-success; (d) read `run-final.json` if present, else `run_final: null` (Pitfall 5: optional). Implement `#[tauri::command] fn enumerate_runs(cwd: String) -> Vec<RunEntry>`: read_dir `<cwd>/.voss/sessions/`, filter to `is_dir()` ONLY (Pitfall 1: flat `.json` files are legacy SessionRecords, NOT runs), require at least one `.json` node file inside, build RunEntry with dir mtime + has_run_final, sort by mtime_secs descending; return `Vec::new()` on missing dir. Register all in `generate_handler![]`. In the existing `mod tests`, add a cargo test `enumerate_runs_filters_flat_session_files`: create a tempdir `.voss/sessions/` with one subdir containing a node `.json` AND one flat `<id>.json` file; assert `enumerate_runs` returns exactly the subdir run_id and excludes the flat file. Add a second test `load_run_rejects_traversal`: assert `load_run("../etc", ..., ...)` returns Err.
  </action>
  <verify>
    <automated>cd apps/voss-app && cargo test --manifest-path src-tauri/Cargo.toml enumerate_runs_filters_flat_session_files load_run_rejects_traversal</automated>
  </verify>
  <done>load_run + enumerate_runs compile and are registered in generate_handler!; the dual-layout filter test passes (only subdir returned); the traversal guard test passes.</done>
</task>

<task type="auto">
  <name>Task 2: run_decision Tauri command (shell CLI, capture stdout/stderr/exit)</name>
  <files>apps/voss-app/src-tauri/src/lib.rs</files>
  <read_first>
    - apps/voss-app/src-tauri/src/lib.rs (git_log Command::output() pattern; spawn_agent cli_binary; is_voss_cli_binary helper ~line 146)
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md ("run_decision stdout/stderr capture pattern")
    - .planning/phases/V11-ade-org-integration/V11-RESEARCH.md (Security Domain: command injection mitigation = Command::arg not shell; D-08 capture requirement)
    - voss/harness/cli.py (audit_cmd lines 2554-2620 — the real `--approve` write path: stdout "approve: permitted for <run_id>" or "approve refused" exit 1)
  </read_first>
  <action>
    Add `#[derive(serde::Serialize)] struct DecisionResult { success: bool, stdout: String, stderr: String, exit_code: i32 }`. Implement `#[tauri::command] fn run_decision(cli_binary: String, cwd: String, args: Vec<String>) -> Result<DecisionResult, String>`: validate `cli_binary` via the existing `is_voss_cli_binary` helper (reuse it — do not invent a new check); reject any arg containing `..` or path separators when it is a run_id-shaped arg (validate the run_id positional, T-V11-03); run `std::process::Command::new(&cli_binary).args(&args).current_dir(&cwd).output()` — pass args as a vector, NEVER interpolate into a shell string (T-V11-04). Return `DecisionResult { success: output.status.success(), stdout, stderr (from_utf8_lossy), exit_code: output.status.code().unwrap_or(-1) }`. Register `run_decision` in `generate_handler![]`. Add a cargo test `run_decision_captures_nonzero_exit` that runs a trivially-failing command (e.g. `cli_binary` = a path to `/bin/sh`-style false, or assert the struct shape via a command that exits non-zero) confirming `success=false` and `exit_code != 0` are captured. NOTE: the real decision command this wraps is `voss audit <run_id> --cwd <cwd> --approve` (the sole non-interactive write path verified in cli.py); the frontend builds the `args` vector — see Task 3.
  </action>
  <verify>
    <automated>cd apps/voss-app && cargo test --manifest-path src-tauri/Cargo.toml run_decision_captures_nonzero_exit</automated>
  </verify>
  <done>run_decision compiles, is registered, uses Command::args (no shell string), validates cli_binary + run_id arg, and the capture test proves stdout/stderr/exit are returned.</done>
</task>

<task type="auto">
  <name>Task 3: orgStore.ts + decisionActions.ts frontend wrappers</name>
  <files>apps/voss-app/src/org/orgStore.ts, apps/voss-app/src/org/decisionActions.ts</files>
  <read_first>
    - apps/voss-app/src/grid/sync.ts (invoke wrapper + serialize JSON.parse/stringify proxy-strip pattern)
    - .planning/phases/V11-ade-org-integration/V11-PATTERNS.md ("src/org/orgStore.ts" + "src/org/decisionActions.ts" sections — exact signal + invoke patterns)
    - apps/voss-app/src/org/types.ts (RunData, RunEntry, DecisionResult from Plan 01)
    - .planning/phases/V11-ade-org-integration/V11-CONTEXT.md (D-07 exact CLI command shown; D-08 capture + auto-refresh)
  </read_first>
  <action>
    `orgStore.ts`: export `createSignal` signals `runData: RunData|null`, `runEntries: RunEntry[]`, `loadError: string|null`, `loading: boolean`, `currentRunId: string|null`. Export `loadRun(runId, cwd, cliBinary)` — sets loading, `invoke<RunData>('load_run', {runId, cwd, cliBinary})`, runs `assertRunData` from guards.ts on the result (D-02 boundary validation), setRunData on success / setLoadError on throw, clears loading in finally. Export `enumerateRuns(cwd)` → `invoke<RunEntry[]>('enumerate_runs', {cwd})` and stores into runEntries. Export `refreshRun(cwd, cliBinary)` that re-calls loadRun with currentRunId (D-08 auto-refresh). `decisionActions.ts`: define `type DecisionAction = 'approve'`. Export `buildDecisionArgs(action, runId): string[]` returning `['audit', runId, '--approve']` (the VERIFIED real write path — NOT a fictional `approve <card>` command). Export `buildDecisionCommand(action, runId, cwd): string` returning the literal display string `voss audit <runId> --cwd <cwd> --approve` for the D-07 confirmation dialog. Export `runDecision(cliBinary, cwd, action, runId): Promise<DecisionResult>` → `invoke<DecisionResult>('run_decision', {cliBinary, cwd, args: buildDecisionArgs(action, runId)})`. Add a code comment noting reject/unblock/per-card sign-off have no non-interactive CLI surface in V7/V9 — only run-level `--approve` exists — so the Blocked panel (Plan 07) surfaces approve as the actionable decision and renders reject/unblock as disabled-with-explanation until a harness command exists (this preserves the one-write-path invariant without inventing harness behavior).
  </action>
  <verify>
    <automated>cd apps/voss-app && npx tsc --noEmit && grep -q "audit" src/org/decisionActions.ts && grep -q "assertRunData\|isRunData" src/org/orgStore.ts</automated>
  </verify>
  <done>orgStore + decisionActions compile; orgStore validates load_run output via the guard; buildDecisionCommand shows the literal verified CLI command; tsc --noEmit clean.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| frontend → Rust command args | run_id, cwd, cli_binary, decision args cross from untrusted JS into FS + subprocess |
| Rust → voss subprocess | shelling the CLI is the sole write path (one-write-path invariant) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V11-03 | Tampering | path traversal via run_id in load_run / run_decision | mitigate | reject run_id containing `/`,`\\`,`..` before any FS access (mirror audit_cmd cli.py:2571) |
| T-V11-04 | Tampering | command injection via args to subprocess | mitigate | std::process::Command::args(vector) — never shell string interpolation (mirror git_log) |
| T-V11-05 | Elevation of Privilege | app writing run decisions directly | mitigate | run_decision shells the CLI only; no app-side FS writes to .voss/sessions — CLI is sole write path (SPEC) |
| T-V11-06 | Spoofing | arbitrary binary passed as cli_binary | mitigate | validate via existing is_voss_cli_binary helper before exec |
| T-V11-SC | Tampering | npm/pip/cargo installs | mitigate | No new packages (RESEARCH audit empty); serde/tauri/std already in workspace |
</threat_model>

<verification>
- `cd apps/voss-app && cargo test --manifest-path src-tauri/Cargo.toml` green (incl. dual-layout filter + traversal + capture tests).
- `cd apps/voss-app && npx tsc --noEmit` green.
- `grep -c "load_run\|enumerate_runs\|run_decision" src-tauri/src/lib.rs` shows all three registered in generate_handler!.
</verification>

<success_criteria>
- Aggregate load_run returns typed RunData; invalid run_id → Err (no crash, no traversal).
- enumerate_runs returns only V4+ subdirs (dual-layout test green).
- run_decision shells the CLI and captures stdout/stderr/exit; one-write-path invariant intact.
- Store + decision wrappers compile and validate at the boundary.
- No new dependencies; existing cargo tests still green.
</success_criteria>

<output>
Create `.planning/phases/V11-ade-org-integration/V11-02-SUMMARY.md` when done.
</output>
