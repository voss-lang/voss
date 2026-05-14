# Phase M10: Codebase Intelligence (CAPS-01a) — Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Source:** Interactive `/gsd-discuss-phase M10` (single-batch, context-conservation mode) on top of locked `M10-SPEC.md`.
**Prior dir-name note:** Phase directory is `M10-agent-capability-surface-caps-01/` (pre-rename). ROADMAP renamed the phase to "Codebase Intelligence (CAPS-01a)" after the M10 SPEC scope-cut; the on-disk directory was NOT renamed to keep CONTEXT/SPEC adjacent. Treat the dir name as historical.

<domain>
## Phase Boundary

M10 delivers codebase intelligence ONLY (CAPS-01a). Locked in `M10-SPEC.md`:
polyglot LSP-backed semantic ops (`find_definition`, `find_references`) +
ast-grep structural search backend + project index, exposed via four
harness tools, three slash commands, system-context auto-injection of a
`## Project Index` section, and an M9 TUI `CodeIntelPanel` widget. Other
five CAPS-01 capabilities split to M11–M15.

</domain>

<decisions>
## Implementation Decisions

### LSP client library

- **Use `pygls`** (Python LSP toolkit).
- Rationale: mature, handles JSON-RPC framing + LSP message types. Faster ship vs hand-rolled JSON-RPC. Adds a deliberate dependency, but the surface area we need (client-mode initialize/shutdown/textDocument requests) is well-covered.
- Researcher should validate: pygls client-mode usage patterns (most pygls docs are server-biased), Windows-stdio handling parity, lifecycle (spawn server process, JSON-RPC over stdio, reap on session exit).
- If researcher finds pygls client mode is genuinely under-supported, escalate to user before falling back to hand-rolled — do NOT silently swap.

### ast-grep invocation strategy

- **subprocess invocation of the `ast-grep` CLI binary.**
- Matches SPEC wording ("wraps ast-grep CLI as a Python invocation surface").
- Distribution: `voss[code]` extra brings the binary. First option: pip wheel of `ast-grep-cli` if it exists for all target platforms; fallback: documentation directing the user to `cargo install ast-grep` or `brew install ast-grep`. Cross-platform binary availability is a researcher question — confirm before plan-time.
- Planner: subprocess wrapper has timeout, stdout-as-JSON parsing, structured error handling on non-zero exit + missing binary (regex fallback path per SPEC Req 3).
- Python bindings (`ast-grep-py`) explicitly NOT chosen — performance gain doesn't justify Rust-wheel install cost for v0.2.

### Project index storage

- **SQLite (`.voss-cache/code/index.db`)** — diverges from SPEC Req 1 acceptance line which defaults to `index.json`.
- **SPEC update required:** Req 1 Acceptance criteria + the M10-SPEC Acceptance Criteria list checkbox referencing `index.json` must be amended to `index.db` (SQLite). Planner schedules this as a documentation task in Wave 1 of M10 plans.
- Rationale: SQLite stdlib avoids new deps, supports incremental updates (vs JSON whole-rewrite), gives slash commands a real query layer for filtered lookups. Better scale headroom for the 100K-LoC budget.
- Schema (rough — planner refines): `files(id, path, lang, hash, mtime)`, `symbols(id, file_id, name, kind, line, col, scope_path)`, `references(id, symbol_id, file_id, line, col)`. Single `meta(key, value)` table for index version + scan timestamp.
- `.voss-cache/code/` remains the storage root — `.gitignore`d, rebuildable, matches M2 COG-07.

### M9 amendment for `CodeIntelPanel`

- **Schedule as new plan `M9-08-PLAN.md`** in M9 phase directory. Wave 8 (one beyond the current M9-07 final wave). `depends_on: [M9-07]`.
- M10 Wave 0 has a hard dependency on M9-08 landing + passing plan-checker before M10 execute starts. M10 plan-phase encodes this as a blocking gate; the M10 planner produces a Wave-0 plan that asserts M9-08 status before proceeding.
- M9-08 scope: add `CodeIntelPanel` widget to `voss/harness/tui/widgets/`, declare panel-region-share contract (mode-switch with `SubAgentPanel` per SPEC Req 7), add panel-show/hide bindings, extend `voss/harness/tui/app.py` with the region-share state machine, extend `voss/harness/tui/widgets/__init__.py` exports, add tests covering idle/active/focused render states + the region-share precedence rule.
- Re-trigger of M9 plan-checker is scoped to M9-08 only (other M9 plans frozen). Lower risk than amending M9-02 or M9-04 in place.

### `.voss/lsp.yml` schema (planner's discretion)

- Required keys per language entry: `command` (server binary), `args` (list, default empty).
- Optional: `init_options` (LSP InitializeParams initializationOptions), `root_markers` (workspace-root discovery, defaults to `pyproject.toml` / `package.json` / `Cargo.toml` / `go.mod`), `disabled` (bool, default false).
- Top-level: `default_max_results` (int, default 50), `scan_timeout_ms` (int, default 5000), `partial_index_threshold_ms` (int, default 30000).
- Defaults bundled in `voss/harness/code/lsp_defaults.yml` for the four headline languages; `.voss/lsp.yml` overlays the defaults. Planner finalizes.

### Redaction integration

- Tool results, slash output, and auto-injection content surface file content snippets. M1's session-redaction filter applies BEFORE persistence to session JSON.
- Snippet length: tools cap excerpts at 80 chars per line × 10 lines unless `max_lines` arg overrides; auto-injection `## Project Index` section emits NO raw snippets (top-K module list + symbol counts only).
- Planner: existing `voss/harness/session.py` redaction pipeline is the integration point. Code-intel results route through the same `_redact_payload` (or equivalent — researcher confirms) before being persisted into RunRecord entries.

### CodeIntelPanel region-share protocol (CONTEXT-level lock; widget mechanics in M9-08 plan)

- M9 side region default: `CodeIntelPanel` (tree-view, idle).
- When a `spawn` is active: `SubAgentPanel` takes the region; `CodeIntelPanel` state preserved off-screen.
- When all spawns gather: region restores to `CodeIntelPanel`.
- Active `/symbol` or `/refs` query overrides into a results-pane mode within `CodeIntelPanel`; does NOT bump `SubAgentPanel`.
- User can pin either panel via a keybinding (planner picks key) — pinning suspends the auto-switch until unpinned.

### Server lifecycle + orphan prevention

- LSP servers spawned lazily on first tool invocation per language.
- Server processes registered with a session-scoped lifecycle manager (planner names the module — likely `voss/harness/code/lifecycle.py`).
- On session exit (clean or `SIGINT`), all server processes reaped via `terminate()` → wait → `kill()` fallback after timeout (default 2s).
- Acceptance test in M10 plans: spawn a session, force-quit it, assert no orphan language-server processes remain via `psutil` or platform-specific lookup.

### Soft-dependency degradation contract

- `ast-grep` missing → `code_search` returns regex-fallback results + logs `code_search.fallback=regex` event. NO `ImportError` or `FileNotFoundError` surfaces.
- Language server missing → `find_definition` / `find_references` for that language returns `{ "result": "lsp_unavailable", "language": "...", "fallback": "ast-grep" }` and routes through ast-grep backend.
- Both missing for a language → returns `{ "result": "lsp_unavailable", "fallback": "regex" }`. Tool surface stays consistent for the agent.

### Out of CONTEXT (left to planner's discretion)

- Exact pygls API patterns and message-class usage.
- Subprocess timeout values and ast-grep output parsing.
- SQLite migration strategy if index schema changes between releases.
- Test fixture repo construction for the four languages (planner picks small open-source fixtures or constructs minimal ones).
- Concrete keybindings for panel pin/unpin and slash-command discovery.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase source documents

- `.planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md` — 7 locked requirements (CODE-01..07), 17 falsifiable acceptance criteria. **Authoritative for "what" — diverges from this CONTEXT only on the SQLite-vs-JSON index store (Req 1 acceptance), which this CONTEXT supersedes and the M10 planner must amend in SPEC.**
- `.planning/seeds/agent-capability-surface.md` — Original CAPS-01 seed. Codebase intel is listed as "highest leverage, lowest novelty risk".
- `.planning/notes/voss-agent-unfair-advantage.md` — Thesis. M10 is NOT the unfair-advantage axis (that's M11) but participates by giving the harness real repo grasp on par with Claude Code / Aider.

### Existing harness code the M10 implementation must integrate with

- `voss/harness/tools.py` — `ToolEntry`, `make_toolset(cwd)`. M10 adds four new entries.
- `voss/harness/slash.py` — Slash registry. M10 adds three new commands.
- `voss/harness/session.py` — Session record + redaction pipeline (Req: redaction integration).
- `voss/harness/cli.py` — Entry points for `voss chat`, `voss do`, `voss resume`. M10 hooks into the session-start path for the index scan + auto-injection.
- `voss/harness/render.py` — Existing renderer protocol. `## Project Index` auto-injection surfaces here for `--plain` mode.
- `voss/harness/cognition.py`, `voss/harness/cognition_schemas.py` — M2 layer; auto-injection of `## Project Index` is the same shape as M2's architecture-section injection.
- `voss/harness/permissions.py` — All four M10 tools are `is_mutating=False`; permission tiers `plan`/`edit`/`auto` all allow them.

### M9 dependency files

- `.planning/phases/M9-tui-shell-tui-01/M9-SPEC.md` — Not present; M9 used the express PRD path. Use `M9-CONTEXT.md` + `M9-UI-SPEC.md` as authoritative for M9 decisions.
- `.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md` — M9 user-locked structural decisions (region grid, slash palette, --plain contract).
- `.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md` — M9 visual + interaction contract (region grid, glyph vocab, color palette, keymap, modals).
- `.planning/phases/M9-tui-shell-tui-01/M9-02-PLAN.md` — M9 app shell. `CodeIntelPanel` slots into the widget inventory pattern established here.
- `.planning/phases/M9-tui-shell-tui-01/M9-07-PLAN.md` — M9 final wave (default-flip). M9-08 (CodeIntelPanel) depends on this.

### Library docs to research at plan time

- `pygls` — Python LSP toolkit. Client-mode usage patterns specifically.
- `ast-grep` — CLI invocation, JSON output format, pattern syntax. Especially: ensure the CLI ships pre-built binaries for macOS arm64/x64, Linux x64/arm64, Windows x64 (matches Voss M6 npm wrapper target matrix).
- Python `sqlite3` stdlib — schema migration patterns, FTS5 module for symbol full-text search if needed.

</canonical_refs>

<specifics>
## Specific Ideas

- **M10 Wave 0 = M9-08 dependency assertion.** Planner produces a first wave that does nothing but verify `M9-08-PLAN.md` exists, has passed plan-checker, and has been executed. M10 plans are blocked behind this gate.
- **SPEC patch task.** Planner schedules an explicit task to update `M10-SPEC.md` Req 1 from `index.json` → `index.db` (SQLite). One-line acceptance criterion swap. Treat as a Wave-1 documentation task.
- **Fixture repo set is reusable.** Planner builds tiny Python/JS/TS/Rust/Go fixture repos under `tests/fixtures/code/{python,js,rust,go}/`. Same fixtures reusable by M11 (Voss-aware tools) and future capability phases.
- **Per-language LSP server install hint.** When a server is absent for a language, the tool result includes a `hint` field with the install command (`brew install pyright`, `cargo install rust-analyzer`, etc.) so the agent can surface remediation guidance.
- **Index version pin.** `meta(key='schema_version', value='1')` written on first index build. On session start, if `schema_version` differs from the harness's expected version, the index is rebuilt (not migrated). Safer for v0.2.

</specifics>

<deferred>
## Deferred Ideas

- **File-watch-driven index refresh.** Coupled to M14 (Long-running Tasks + Watch). M10 ships session-start + on-demand only.
- **Cross-repo / monorepo-aware search.** Single `--cwd`-rooted tree only in M10.
- **LSP features beyond search ops** — completion, hover-types, diagnostics, code-actions, formatting, rename. Defer.
- **Additional language servers** beyond Python/JS-TS/Rust/Go. `.voss/lsp.yml` is the extensibility seam; user adds entries as needed. M10 ships only the four defaults.
- **`CodeIntelPanel` theming + advanced visual polish** — minimum viable in M10/M9-08; richer browse UX is a follow-up.
- **Symbol-level memory persistence across sessions** — crosses into M8 territory; M10's index is rebuildable cache only.
- **LSP-driven refactors or batch edits** — read-only operations only in M10.
- **Custom user tree-sitter queries** beyond ast-grep's built-in language packs.

</deferred>

---

*Phase: M10-agent-capability-surface-caps-01 (dir name historical; phase renamed in ROADMAP)*
*Context gathered: 2026-05-14 via interactive `/gsd-discuss-phase M10` (single-batch, context-conservation mode)*
*Next step: `/gsd-plan-phase M10`. Planner should also schedule M9-08-PLAN.md creation as a prerequisite — recommend running `/gsd-plan-phase M9 --research` with explicit M9-08 scope, OR letting M10's Wave 0 plan call out to a separate `/gsd-plan-phase` invocation.*
