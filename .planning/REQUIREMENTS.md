# Requirements: Voss v0.1 Harness MVP

**Defined:** 2026-05-10
**Core Value:** A developer can give Voss a repo task and get bounded, inspectable, resumable AI coding work, while the most important agent logic is expressible as compiler-checkable `.voss` workflows instead of prompt soup.
**Source:** `.vscode/voss_v_0_1_scope_lock.md`

## v0.1 Requirements

### Scope Lock

- [ ] **SCOPE-01**: Planning docs state that Voss v0.1 ships as an AI-native coding harness with `.voss` as the workflow control layer.
- [ ] **SCOPE-02**: Roadmap uses M-prefixed phases (`M0` through `M5`) that match the v0.1 scope-lock document.
- [ ] **SCOPE-03**: Planning docs clearly preserve compiler verbs separately from harness verbs.
- [ ] **SCOPE-04**: Planning docs explicitly defer Rust, MCP bridge, tree-sitter, VSCode marketplace, Linguist upstream, and full telemetry until after the Python harness proves real usage.

### CLI Harness

- [ ] **CLIH-01**: `voss` launches an interactive harness REPL.
- [ ] **CLIH-02**: `voss chat` launches the same REPL explicitly.
- [ ] **CLIH-03**: `voss do "<task>"` runs a one-shot natural-language agent task.
- [ ] **CLIH-04**: `voss edit <path>` starts a scoped edit session for a requested path.
- [ ] **CLIH-05**: `voss resume [id]` resumes a saved harness session.
- [ ] **CLIH-06**: `voss sessions` lists saved sessions.
- [ ] **CLIH-07**: `voss tools` lists registered harness tools.
- [ ] **CLIH-08**: `voss doctor` diagnoses setup.
- [ ] **CLIH-09**: `voss config` opens or reports harness configuration.
- [ ] **CLIH-10**: `voss run <file.voss>` remains reserved for `.voss` programs and does not collide with natural-language task execution.

### Project Cognition

- [ ] **COG-01**: Voss creates and maintains `.voss/project.json`.
- [ ] **COG-02**: Voss creates or updates `.voss/architecture.md` from repo analysis.
- [ ] **COG-03**: Voss stores constraints, permissions, and validation config under `.voss/constraints.yml`, `.voss/permissions.yml`, and `.voss/validation.yml`.
- [ ] **COG-04**: Voss stores plans under `.voss/plans/`.
- [ ] **COG-05**: Voss stores sessions under `.voss/sessions/`.
- [ ] **COG-06**: Voss stores decisions under `.voss/decisions/`.
- [ ] **COG-07**: Voss uses `.voss-cache/` only for rebuildable state such as repo indexes, generated harness artifacts, and temporary files.
- [ ] **COG-08**: Every agent run records task goal, plan, inspected files, changed files, avoided files, assumptions, decisions, risks, validation commands, failures, final diff summary, and follow-up recommendations.

### Controlled Execution

- [ ] **CTRL-01**: Harness exposes `fs_read`, `fs_glob`, `fs_grep`, `fs_write`, and `fs_edit`.
- [ ] **CTRL-02**: Harness exposes `shell_run` with shell allowlist and timeout controls.
- [ ] **CTRL-03**: Harness exposes `git_status` and `git_diff`.
- [ ] **CTRL-04**: Harness exposes `voss_check`.
- [ ] **CTRL-05**: Execution modes `plan`, `edit`, and `auto` are available and permissioned.
- [ ] **CTRL-06**: Tool execution is jailed to `--cwd`.
- [ ] **CTRL-07**: Risky operations require permission prompts with deny, allow once, and allow always choices.
- [ ] **CTRL-08**: Voss shows a diff preview before applying edits.
- [ ] **CTRL-09**: Session payloads never include provider API keys or equivalent secrets.

### Language Control Layer

- [ ] **LANG-01**: `.voss` is positioned and implemented as an AI workflow control language, not a general Python replacement.
- [ ] **LANG-02**: Parser/analyzer/codegen preserve `probable<T>` and confidence gates.
- [ ] **LANG-03**: Parser/analyzer/codegen preserve `ctx(budget: N tokens)`.
- [ ] **LANG-04**: Parser/analyzer/codegen preserve `within budget(...) { } fallback { }`.
- [ ] **LANG-05**: Parser/analyzer/codegen preserve `match similar(...)`.
- [ ] **LANG-06**: Parser/analyzer/codegen preserve `agent`, `spawn`, and `gather`.
- [ ] **LANG-07**: Parser/analyzer/codegen preserve `memory.episodic`, `memory.semantic`, and `memory.working`.
- [ ] **LANG-08**: Parser/analyzer/codegen preserve `@tool`, `prompt`, `try/catch`, and `use`.
- [ ] **LANG-09**: `voss check samples/classify.voss`, `samples/support.voss`, and `samples/research.voss` pass.
- [ ] **LANG-10**: At least one representative sample runs through `voss run` and demonstrates that `.voss` makes AI workflow code materially shorter and readable.

### Dogfood

- [ ] **DOG-01**: `voss/harness/agent/loop.voss` exists.
- [ ] **DOG-02**: `voss/harness/agent/router.voss` exists.
- [ ] **DOG-03**: `voss/harness/agent/planner.voss` exists.
- [ ] **DOG-04**: `voss/harness/agent/executor.voss` exists.
- [ ] **DOG-05**: `voss/harness/agent/reviewer.voss` exists.
- [ ] **DOG-06**: `voss check voss/harness/agent/` is a CI gate.
- [ ] **DOG-07**: Bare `voss` can boot through compiled harness logic once the dogfood loop is enabled.
- [ ] **DOG-08**: Compiled harness artifacts cache under `.voss-cache/harness/`.

### Eval and Distribution Prep

- [ ] **EVAL-01**: Golden repo tasks exist for the canonical v0.1 demo workflow.
- [ ] **EVAL-02**: Evaluation tracks success rate.
- [ ] **EVAL-03**: Evaluation tracks mean cost.
- [ ] **EVAL-04**: Evaluation tracks confidence correlation against successful and failed runs.
- [ ] **EVAL-05**: Package install polish is verified after the Python harness loop works.

### npm Distribution

- [ ] **NPM-01**: An npm package named `voss` (or `@voss/cli`) is publishable and installable via `npm i -g voss` / `npx voss`.
- [ ] **NPM-02**: The npm package vendors a pinned Python interpreter + the v0.1 voss wheel per supported platform (darwin-arm64, darwin-x64, linux-x64, linux-arm64, win32-x64) via postinstall or per-platform optionalDependencies.
- [ ] **NPM-03**: The `voss` bin shim forwards all CLI arguments to the vendored `python -m voss.cli`, preserving exit codes, stdin/stdout/stderr, and signal forwarding.
- [ ] **NPM-04**: A packaging smoke test verifies that, in a fresh Node project, `npm install voss` then `npx voss --help`, `npx voss doctor`, `npx voss check <sample.voss>`, and `npx voss compile <sample.voss>` all exit 0.
- [ ] **NPM-05**: README primary install path is `npm i -g voss`; `pip install voss` is listed as the secondary path. v0.1 framing remains "Python harness; Rust shell later" — npm wrapper is distribution, not reimplementation.

### SDK Polish

Promoted from v0.2 candidate to formal M7 phase on 2026-05-13. Closes the
four public-API-shaped holes identified during the 2026-05-12 SDK contract
pass (`docs/sdk.md`) plus a stable provider registration entry point.
Embedders currently work around these by reaching into private paths
(`voss.harness.render`, `voss.harness.session`, `voss_runtime.providers`);
M7 promotes the missing names so private-path drift stops binding callers.

- [ ] **SDK-01**: Promote a `Renderer` protocol + `NullRenderer` implementation
  into `voss.harness.__all__`. Embedders that want silent or custom rendering
  currently import from the private `voss.harness.render` module.
- [ ] **SDK-02**: Add a `tool_entry_from_callable(fn, *, is_mutating, name=None,
  description=None)` factory to `voss.harness.__all__`. Wraps a plain Python
  callable as a `ToolEntry` without forcing embedders to author descriptors
  by hand.
- [ ] **SDK-03**: Promote a read-only session view type (`SessionView` / similar)
  that exposes session id, cwd, runs (timestamps, cost, confidence) without
  binding callers to the on-disk `SessionRecord` / `RunRecord` schema. The
  internal schema stays free to change; the embedder view stays stable.
- [ ] **SDK-04**: Add `RuntimeConfig.from_toml(path)` plus a `RuntimeConfig.default()`
  that resolves `~/.config/voss/config.toml` and env overrides, so embedders
  share the harness config file rather than reconstructing it field by field.
- [ ] **SDK-05**: Document and stabilize the provider registration entry point
  (`voss_runtime.providers.register`) so third-party providers can be added
  without reaching into the private `voss_runtime.providers` submodule.

## Future Requirements

### Deferred Distribution

- **DIST-01**: Rust harness shell for startup performance and single-binary distribution.
- **DIST-02**: Homebrew distribution after Python harness usage is proven.
- **DIST-03**: MCP bridge after the harness product loop is proven.

### Deferred Editor and Ecosystem

- **EDIT-01**: Tree-sitter grammar.
- **EDIT-02**: VSCode marketplace release.
- **LING-01**: GitHub Linguist upstream PR.

### Deferred Product Surface

- **TEAM-01**: Cloud sync.
- **TEAM-02**: Team collaboration.
- **TEAM-03**: Account system.
- **WEB-01**: Web UI.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full Python language parity | v0.1 is a harness plus AI workflow control layer, not a Python replacement |
| Native LLVM/Wasm compilation | Python target is sufficient for current AI workflow ecosystem |
| TypeScript target | Defer until Python-targeted control layer proves usage |
| Package manager | Use Python packaging and repo-local state first |
| Debugger or full LSP | Generated Python, diagnostics, and harness validation are enough for v0.1 |
| Distributed or multi-machine agents | Local bounded execution first |
| Fine-tuning or training loops | v0.1 is inference and workflow control only |
| Cloud sync, teams, accounts, marketplace | Not needed for the repo-centric MVP |
| Web UI or split-pane TUI | CLI-first product surface |
| Windows support | Defer until core loop works |
| Broad OSS launch campaign | Behavior must be proven first |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SCOPE-01..04 | M0 | Pending |
| CLIH-01..10 | M1 | Pending |
| CTRL-01..09 | M1 | Pending |
| COG-01..08 | M2 | Pending |
| LANG-01..10 | M3 | Pending |
| DOG-01..08 | M4 | Pending |
| EVAL-01..05 | M5 | Pending |
| NPM-01..05 | M6 | Pending |
| SDK-01..05 | M7 | Pending |

**Coverage:**
- v0.1 requirements: 64 total (54 original + 5 NPM-* M6 + 5 SDK-* M7)
- Mapped to phases: 64
- Unmapped: 0

---
*Requirements defined: 2026-05-10*
*Last updated: 2026-05-13 — promoted SDK-01..05 from v0.2 candidate to M7 SDK Polish phase*
