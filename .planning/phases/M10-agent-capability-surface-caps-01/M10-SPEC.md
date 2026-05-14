# Phase M10: Agent Capability Surface — Codebase Intelligence (CAPS-01) — Specification

**Created:** 2026-05-14
**Ambiguity score:** 0.14 (gate: ≤ 0.20)
**Requirements:** 7 locked

## Goal

Add a codebase intelligence layer to the Voss harness — polyglot LSP-backed semantic operations (`find_definition`, `find_references`) plus ast-grep-backed structural pattern search, exposed through four user/agent surfaces: harness tools, slash commands, system-context auto-injection, and an M9 TUI side panel. M10 is scoped to codebase intelligence ONLY; the other five capabilities listed in the original CAPS-01 seed (Voss-aware tools, MCP bridge, multi-agent in chat, long-running tasks, skill marketplace) are spun off as M11..M15 follow-on phases.

## Background

The harness has a tool registry (`voss/harness/tools.py` — `ToolEntry`, `make_toolset`), a slash command registry (`voss/harness/slash.py`), a per-session system-context injection path (used by M2 for `.voss/architecture.md` and slated for `VOSS.md` in M8), and an existing-but-unused plugins scaffold (`voss/harness/plugins.py`). Multi-agent infrastructure (`voss/harness/subagents.py`) and runtime spawn/gather primitives (`voss_runtime/agent.py`) exist but are scoped to M12+. There is no LSP client, no ast-grep / tree-sitter integration, no project index, and no `.voss/lsp.yml` config. Other coding agents (Claude Code, Aider) already provide repo-grasping tools; the lack of equivalent surfaces in Voss is the most-visible feature gap vs competitors. Codebase intelligence is rated highest leverage and lowest novelty risk among the six CAPS-01 capabilities (seed line: "highest leverage, lowest novelty risk").

## Requirements

1. **Project index — session-start scan + on-demand refresh**: A persistent project index is built at session start and refreshable via a tool/slash command.
   - Current: No project index exists at the harness level. `.voss-cache/repo.idx` is mentioned in M2 as a "simpler rebuildable file index" but is not a symbol-level index.
   - Target: On every `voss chat` / `voss do` / `voss resume`, a session-start scan walks the repo, populates a symbol+file index under `.voss-cache/code/`, and exposes it to the in-session tools. A `code_refresh` tool and `/refresh` slash command rebuild the index on demand. No background file-watch (that is a separate M14 capability).
   - Acceptance: Launching a session on a fixture repo populates `.voss-cache/code/index.json` with a deterministic schema (modules, symbols, references-by-file) before the first user turn. Calling `code_refresh` after a file write reflects the change in the index. Closing and re-launching `voss chat` re-runs the scan and matches the prior result on an unchanged tree.

2. **Polyglot LSP server registry**: A pluggable LSP client launches one server per supported language on demand, configured via `.voss/lsp.yml`.
   - Current: No LSP client. No `.voss/lsp.yml`. No language-server lifecycle code.
   - Target: M10 ships a minimal LSP client (JSON-RPC 2.0 over stdio) and a server registry that resolves four languages out of the box: Python via `pyright` (or `pylsp` fallback), JS/TS via `typescript-language-server`, Rust via `rust-analyzer`, Go via `gopls`. The registry is config-driven from `.voss/lsp.yml` (per-language `command`, `args`, optional `init_options`); missing servers degrade to ast-grep-only for that language with a logged warning, not a hard error. Servers run lazily — only spun up when a tool that needs them is invoked. Server processes are reaped on session exit.
   - Acceptance: With all four servers installed in the test environment, `find_definition` resolves a known-good symbol in a fixture repo of each language to the correct file + range. With a server intentionally absent, the tool returns a structured "lsp_unavailable" result + falls through to the ast-grep backend (Req 3) instead of crashing. `ps` after session exit shows no orphaned language-server processes.

3. **ast-grep / tree-sitter structural search backend**: An ast-grep-backed structural pattern search runs alongside LSP for pattern queries that LSP cannot express.
   - Current: No ast-grep code. No tree-sitter integration. Existing text search via `shell_run` only.
   - Target: M10 wraps ast-grep CLI as a Python invocation surface for pattern queries (e.g. `code_search("$A.foo($B)")`). Tree-sitter grammars resolved from ast-grep's bundled set; no per-language grammar install required from M10 itself. ast-grep is a soft dependency — installed via the `voss[code]` extra (mirrors the `voss[search]` pattern from M2/M8). When `ast-grep` is not on PATH, `code_search` degrades to a regex fallback over indexed files (Req 1) with a logged limitation note.
   - Acceptance: `code_search("def $NAME($$$)")` against a Python fixture returns the expected function definitions with their ranges. `code_search` with `ast-grep` uninstalled (PATH stripped) returns regex-fallback results and logs a `code_search.fallback=regex` event. The integration test asserts hit-count parity between ast-grep and regex paths on a baseline fixture.

4. **Harness tools — `code_search`, `find_definition`, `find_references`, `code_refresh`**: Four new tools registered in the harness toolset.
   - Current: No code-intel tools exist in `voss/harness/tools.py`. Existing tools are `fs_*`, `git_*`, `shell_run`, `voss_check`.
   - Target: Four tools registered with `ToolEntry` entries — `code_search(pattern, path?, max_results?)`, `find_definition(symbol, path?)`, `find_references(symbol, path?, max_results?)`, `code_refresh(paths?)`. All tools route through the LSP registry (Req 2) and ast-grep backend (Req 3) per their semantics. Tools are `is_mutating=False`. Tool results include source-type tags (`lsp` vs `ast-grep` vs `regex-fallback`) and language for downstream agent reasoning.
   - Acceptance: `voss tools` lists all four tools with their descriptions. An integration test invokes each tool against a Python+JS+Rust+Go fixture set and asserts non-empty results, correct source-type tags, and per-language coverage.

5. **Slash commands — `/symbol`, `/refs`, `/refresh`**: Three new slash commands wired into the existing slash registry.
   - Current: No code-intel slash commands. M8 has reserved `/recall`, `/forget`, `/memory`, `/save`. M9 wires the slash palette + `/save → /snapshot` rename.
   - Target: `/symbol <name>` returns top-N (default 10) symbol matches with file:line and source-type tag; `/refs <symbol>` returns top-N references; `/refresh` triggers a project-index rebuild. Each command has a `--help` line and registers into the M9 palette without naming conflict. None of the three names overlap with M8's reserved set.
   - Acceptance: Each of the three slash commands is registered in `voss/harness/slash.py`, has `--help` output, and is exercised by integration tests. The M8 reserved-name lock (`RESERVED_SLASH_NAMES = ('/recall', '/forget', '/memory', '/save')`) still holds — `/symbol`, `/refs`, `/refresh` are not in that set and do not collide with M9's palette tests.

6. **Auto-injection — `## Project Index` section in system context**: Session-start system context gains a labeled project-index summary.
   - Current: System context contains M2's `.voss/architecture.md` (post-M8: folded into `VOSS.md`). No symbol/index summary auto-injected.
   - Target: After the project-index scan completes (Req 1), a `## Project Index` section is appended to the system context with: total file count by language, top-K modules (default 20) by symbol count, and a compact "entry points" listing if any are detected (`__main__`, `main()`, exported HTTP handlers). Section is bounded to a configurable token budget (default 1500 tokens). Absence of an index (e.g. scan failure) degrades silently — no section, no error.
   - Acceptance: Dumping the system context for a fresh session shows a `## Project Index` section with non-zero counts on a fixture repo. Section size on a 10K-LoC fixture is ≤ 1500 tokens. With the scan disabled via config, no section is emitted and no error surfaces in the session log.

7. **M9 TUI side panel — code intel browser**: A side-panel widget in the M9 TUI displays project index browse + search results.
   - Current: M9's locked region grid reserves the side panel for `SubAgentPanel` (spawn/gather rendering) only. No code-intel panel exists in M9 plans.
   - Target: An additional panel widget — `CodeIntelPanel` — is added to M9's TUI region grid via an amendment to M9 plans BEFORE M10 execute. Display modes: tree-view of modules (idle state), live results pane while `/symbol` or `/refs` runs, file:line excerpt on focus. Coexists with `SubAgentPanel` via mode-switching when both want the side region (resolution: `SubAgentPanel` takes precedence when a spawn is active; `CodeIntelPanel` shows otherwise). M9-02 (or M9-04) is amended to reserve the panel hook + region-share contract — this amendment may re-trigger M9 plan-checker iter 3, accepted risk per user.
   - Acceptance: M9 plan amendment lands and passes plan-checker. `CodeIntelPanel` registered in M9-02 widget inventory. Launching `voss chat` shows the code-intel tree-view in the side region. Triggering `/symbol foo` updates the side panel with results. Spawning a sub-agent during an active code-intel browse switches the region to `SubAgentPanel` and restores the code-intel view on sub-agent exit.

## Boundaries

**In scope (M10):**
- Project index (session-start + on-demand) under `.voss-cache/code/`.
- LSP client + server registry resolving Python, JS/TS, Rust, Go via `.voss/lsp.yml`.
- ast-grep structural-search backend with regex fallback.
- Four new harness tools: `code_search`, `find_definition`, `find_references`, `code_refresh`.
- Three new slash commands: `/symbol`, `/refs`, `/refresh`.
- Auto-injection of `## Project Index` section into system context.
- M9 TUI side-panel amendment + `CodeIntelPanel` widget.
- `.voss/lsp.yml` config surface with defaults for the four headline languages.
- `voss[code]` install extra bundling `ast-grep` + LSP client deps.

**Out of scope:**
- **Voss-aware tools** (`.voss` lint as skill, probable inspector, budget tracer) — spun off as **M11**.
- **MCP bridge** — promoted to its own phase as **M12** (subsumes the existing DIST-03 roadmap candidate).
- **Multi-agent in chat** (expose runtime spawn/gather to user) — **M13**.
- **Long-running / watch tasks** (file watcher, background jobs, bottom-pane status strip) — **M14**.
- **Skill / plugin marketplace** (`voss skill add`, signed manifests, sandbox) — **M15**.
- **File-watch-driven index refresh** — explicitly out; index refresh is session-start + on-demand only. Background file-watch is M14 territory.
- **LSP features beyond search ops** — completion, hover-typed-info, diagnostics, code-actions, formatting, rename. M10 ships definition + references + (optionally) workspace-symbol; everything else is a follow-up.
- **Additional language servers beyond the four headline languages** — Java, C/C++, Ruby, Swift, Kotlin, etc. follow as user demand surfaces; `.voss/lsp.yml` is the extensibility seam but M10 ships only the four defaults.
- **Cross-repo / monorepo-aware search** — M10 scans the single `--cwd`-rooted tree.
- **Symbol-level memory persistence across sessions** — that crosses into M8's territory; M10's index is rebuildable cache only.
- **LSP-driven refactors or batch edits** — read-only operations only.
- **Custom Voss-defined tree-sitter queries beyond ast-grep's built-in language packs**.
- **CodeIntelPanel theming / advanced visual polish** — minimum viable rendering; richer browse UX is a follow-up.

## Constraints

- M9 TUI amendment (Req 7) MUST land and pass plan-checker BEFORE M10 execute starts. M10 plan-phase encodes this as a Wave 0 dependency / blocking gate.
- Refresh policy is session-start + on-demand only. NO background file-watch — coupling to M14 must be avoided to keep M10 ship-independent of M14.
- LSP servers are lazy-launched and reaped on session exit. Long-running server processes must NOT outlive the harness process. Orphan-process audit in acceptance.
- ast-grep is a soft dependency via `voss[code]` extra. Tools must function without ast-grep installed (regex fallback) — no hard import errors.
- Polyglot LSP coverage is the four headline languages; users can extend via `.voss/lsp.yml` but M10 ships only those four defaults. Missing servers degrade per language, not globally.
- Session-start scan latency budget: ≤ 5s on a 10K-LoC repo, ≤ 30s on a 100K-LoC repo. Beyond budget, scan continues asynchronously in the background and surfaces a "partial index" warning until complete.
- Project-index storage location is `.voss-cache/` (rebuildable), NOT `.voss/` (durable) — matches M2's COG-07 convention. Cache is `.gitignore`d.
- All four tools (`code_search`, `find_definition`, `find_references`, `code_refresh`) are `is_mutating=False`. Permission modes `plan`, `edit`, `auto` all allow them.
- Tool results, slash output, and auto-injection content must respect the harness redaction layer — file contents are surfaced, but file-content snippets must run through M1's session-redaction filter before persistence.
- `code_search` and `find_references` results are bounded by `max_results` (default 50). No unbounded list returns to the agent.
- Auto-injection `## Project Index` section is hard-capped at 1500 tokens by default; on overflow, top-K modules are truncated with an explicit "(truncated)" marker.
- No new emit points added to `voss/harness/recorder.py` or the `voss_runtime` baseline files locked by M9 (`probable.py`, `budget.py`, `agent.py`). M10 capabilities consume existing state read-only.
- Backward compat: `voss tools`, `voss sessions`, `voss resume`, slash registry, system-context injection all continue to function for pre-M10 sessions without code-intel data present.

## Acceptance Criteria

- [ ] `M9-XX-PLAN.md` amendment lands reserving `CodeIntelPanel` region-share contract and passes plan-checker. M9-CONTEXT.md or M9-UI-SPEC.md updated to record the amendment.
- [ ] Session start on a fixture repo populates `.voss-cache/code/index.json` before the first user turn. Schema is deterministic across re-runs on an unchanged tree.
- [ ] `code_refresh` (tool or `/refresh` slash) rebuilds the index and reflects post-refresh file changes.
- [ ] `find_definition` on a known-good symbol returns the correct file + range for Python, JS/TS, Rust, and Go fixture repos.
- [ ] `find_references` on a known-good symbol returns ≥ N expected references (N ground-truthed per fixture) for each of the four languages.
- [ ] `code_search("def $NAME($$$)")` on a Python fixture returns expected function definitions.
- [ ] With `ast-grep` removed from PATH, `code_search` returns regex-fallback results AND logs `code_search.fallback=regex`. No `ImportError` or `FileNotFoundError` surfaces to the agent.
- [ ] With a language server (e.g. `gopls`) absent, `find_definition` for a Go symbol returns a structured `lsp_unavailable` result and falls through to ast-grep — does not crash.
- [ ] `ps` after session exit shows no orphan language-server processes spawned by the harness.
- [ ] `voss tools` output lists `code_search`, `find_definition`, `find_references`, `code_refresh` with descriptions.
- [ ] `/symbol`, `/refs`, `/refresh` are registered slash commands with `--help`; none collide with the M8 reserved set or M9 palette tests.
- [ ] System context for a fresh session contains a `## Project Index` section with non-zero counts on a fixture repo; section size on a 10K-LoC fixture is ≤ 1500 tokens.
- [ ] With code-intel scan disabled in config, the `## Project Index` section is absent and no error is logged.
- [ ] Session-start scan latency on a 10K-LoC fixture is ≤ 5s; on a 100K-LoC fixture is ≤ 30s OR a partial-index warning surfaces.
- [ ] `CodeIntelPanel` renders in the M9 TUI side region in idle (tree-view), active-query (results), and focused (file:line excerpt) states.
- [ ] Spawning a sub-agent during an active code-intel browse switches the panel to `SubAgentPanel`; on sub-agent exit, the code-intel view restores.
- [ ] No `class .*Memory` definitions added in `voss/harness/` (M8 invariant preserved). No new emit points added to recorder.py or M9-baselined `voss_runtime/{probable,budget,agent}.py` files (grep-verified hash baseline still passes).

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                                                       |
|--------------------|-------|------|--------|---------------------------------------------------------------------------------------------|
| Goal Clarity       | 0.92  | 0.75 | ✓      | M10 scope locked to codebase intel only; M11..M15 enumerated for the other 5 CAPS-01 caps.   |
| Boundary Clarity   | 0.85  | 0.70 | ✓      | In-scope vs out-of-scope explicit; LSP feature trim (no completion/diagnostics) explicit.   |
| Constraint Clarity | 0.82  | 0.65 | ✓      | M9 amendment dependency, refresh policy, soft ast-grep dep, latency budget, orphan-process rule all locked. |
| Acceptance Criteria| 0.82  | 0.70 | ✓      | 17 pass/fail criteria including the fixture-set polyglot eval bar.                          |
| **Ambiguity**      | 0.14  | ≤0.20| ✓      | Gate passed.                                                                                 |

## Interview Log

| Round | Perspective              | Question summary                                       | Decision locked                                                                                          |
|-------|--------------------------|--------------------------------------------------------|----------------------------------------------------------------------------------------------------------|
| 1     | Simplifier               | Bundle scope reality (6 caps vs phase size)?           | M10 = single capability headliner. Other 5 spun off as M11..M15.                                          |
| 1     | Simplifier               | Pick headliner if option (a)?                          | Codebase intelligence (LSP + ast-grep + project index).                                                  |
| 2     | Researcher               | Codebase intel exposure surface?                       | All four: harness tools, slash commands, auto-injection, M9 TUI side panel.                              |
| 2     | Researcher               | LSP scope — Python-only vs polyglot vs ast-grep-only?  | Polyglot via LSP server registry — Python (pyright), JS/TS (typescript-language-server), Rust (rust-analyzer), Go (gopls). |
| 2     | Researcher               | Project index refresh policy?                          | Session-start scan + on-demand refresh. No file-watch (file-watch is M14).                                |
| 3     | Boundary Keeper          | M9 TUI side panel not specced in M9 — resolve?         | Amend M9 plans before M10 execute; accepts risk of M9 plan-checker iter 3 re-trigger.                     |
| 3     | Boundary Keeper          | ast-grep vs LSP relationship in M10?                   | Both ship — LSP for semantic ops, ast-grep for structural pattern search. Two backends, one tool surface. |
| 3     | Acceptance               | M10 done-bar?                                          | All four falsifiable criteria locked: tools registered + polyglot fixture tests; slash registered; auto-injection section present; LSP registry config-driven. |

---

*Phase: M10-agent-capability-surface-caps-01*
*Spec created: 2026-05-14*
*Next step: `/gsd-discuss-phase M10` — implementation decisions (LSP client lib choice — pygls vs hand-rolled JSON-RPC; ast-grep invocation strategy — subprocess vs python bindings; `.voss/lsp.yml` schema; index schema; `CodeIntelPanel` region-share protocol; redaction integration). Also: schedule the M9 amendment (Req 7) — likely as a new plan `M9-08-PLAN.md` or amendment to `M9-02`, executed BEFORE M10 execute.*
