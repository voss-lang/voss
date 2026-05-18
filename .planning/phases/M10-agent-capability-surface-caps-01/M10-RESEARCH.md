# Phase M10 Research: Codebase Intelligence (CAPS-01a)

**Date:** 2026-05-18  
**Role:** GSD `gsd-phase-researcher`  
**Confidence:** Medium-high for architecture and validation shape; medium for pygls client mechanics until a spike proves stdio lifecycle against real servers.

## Research Question

What does Voss need to know before planning M10 well?

M10 should be planned as an additive code-intelligence subsystem, not as a rewrite of existing harness cognition, memory, TUI, or tool plumbing. The phase adds a rebuildable symbol/file index, LSP-backed definition/reference queries, ast-grep structural search, slash/tool surfaces, bounded system-context injection, and a TUI panel dependency that must be handled through M9-08 before M10 execute starts.

Graphify note: AGENTS asks for Graphify first, but this repo has no `graphify-out/graph.json`, so `/graphify query` could not run without rebuilding and writing extra graph artifacts. I used SecondBrain + direct source inspection instead.

## User Constraints

- M10 is codebase intelligence only: project index, LSP definition/reference, ast-grep structural search, four harness tools, three slash commands, `## Project Index` system-context injection, and M9 `CodeIntelPanel` integration.
- The phase directory name is historical; ROADMAP renamed M10 to `Codebase Intelligence (CAPS-01a)`.
- M9-08 is a hard prerequisite. The M10 plan should include Wave 0 that only verifies the M9-08 plan exists, passed checker, and executed.
- Use `pygls` for LSP client work unless a spike proves client mode unusable. Do not silently fall back to hand-rolled JSON-RPC.
- Use subprocess invocation of the `ast-grep` binary. Do not use `ast-grep-py` for v0.2.
- Store the project index in SQLite at `.voss-cache/code/index.db`, superseding the SPEC's older `index.json` line. The planner must schedule a SPEC patch task.
- Tool/slash/system-context output can surface file content snippets, so snippets must be bounded and redacted before persistence. Auto-injection must emit no raw snippets.
- LSP servers are lazy-launched per language and reaped on session/process exit. No orphan language-server processes.
- Soft dependency behavior is required: missing ast-grep and missing language servers must degrade to structured fallback results, not crash.
- No background file watcher; refresh is session-start plus on-demand only.
- No cross-repo/monorepo support, no LSP completion/hover/diagnostics/code-actions/rename/formatting, no LSP-driven edits, no symbol-level memory persistence, no custom tree-sitter query system.
- Do not add recorder emit points or alter the M9-baselined runtime files.

## Phase Requirements And Acceptance Map

| Req | Meaning | Planning implications | Acceptance hook |
|---|---|---|---|
| CODE-01 Project index | Build at session start; refresh on demand; cache under `.voss-cache/code/` | New SQLite index builder with deterministic schema/version; wire chat/do/resume start path; tool/slash refresh | Fixture repo creates stable `index.db`; refresh reflects edits; unchanged relaunch is deterministic |
| CODE-02 LSP registry | Four default languages via `.voss/lsp.yml`; lazy server launch | New config loader + registry + pygls-backed adapter; external server install hints | Definition works for Python, JS/TS, Rust, Go with servers installed; missing server returns `lsp_unavailable`; orphan audit |
| CODE-03 ast-grep backend | Structural search with regex fallback | New subprocess wrapper with timeout, `--json=stream` parser, missing-binary fallback | Python pattern fixture returns expected defs; stripped `PATH` logs `code_search.fallback=regex`; parity fixture |
| CODE-04 Harness tools | `code_search`, `find_definition`, `find_references`, `code_refresh` | Add `ToolEntry` registrations as read-only; keep implementation in new code package | `voss tools` lists all four; integration calls each across fixtures |
| CODE-05 Slash commands | `/symbol`, `/refs`, `/refresh` | Register in `_build_slash_registry`; update grouped help and slash matrix tests | Commands have help, run cleanly, no reserved-name collision |
| CODE-06 Auto-injection | `## Project Index` in system context | Compose bounded summary after scan; inject through existing system block path | System prompt contains nonzero counts; <=1500 tokens; disabled scan omits quietly |
| CODE-07 TUI panel | M9 side panel for browse/results | M9-08 owns widget/region-share; M10 consumes panel API and pushes query/index state | Idle/active/focused panel states; SubAgentPanel precedence and restore behavior |

## Standard Stack

Use:

- Python stdlib `sqlite3` for `.voss-cache/code/index.db`; no new DB dependency.
- `pygls>=2.1,<3` in a new `code` optional extra for the LSP transport/client adapter.
- `ast-grep-cli>=0.42,<0.43` in the same `code` optional extra. PyPI currently publishes wheels for the target platform families Voss cares about, including macOS universal2, Linux x86-64/aarch64 manylinux, and Windows x86-64/ARM64.
- External language servers are user/system tools, not bundled Python deps: `pyright` or `pylsp`, `typescript-language-server`, `rust-analyzer`, `gopls`.
- YAML config through existing `pyyaml` + pydantic patterns. Add LSP schema models either in `voss/harness/code/config.py` or in `cognition_schemas.py` only if shared with `.voss/` durable cognition. Prefer local code-intel schemas because `.voss/lsp.yml` is code-intel-specific.

Do not:

- Build JSON-RPC framing by hand unless pygls spike fails.
- Use `ast-grep-py` in M10.
- Store symbol index in durable `.voss/`.
- Add Chroma/vector search or memory classes for symbol persistence.
- Add file-watch infrastructure.

## pygls Finding

Official pygls v2.1.1 docs are mostly language-server focused. Their navigation explicitly leaves Language Clients as "Coming Soon", while the Python API exposes `BaseLanguageClient` and `JsonRPCClient`. The client API documents `initialize`, `shutdown`, `exit`, `text_document_definition`, `text_document_references`, `workspace_symbol`, async variants, and `JsonRPCClient.start_io`.

Recommendation: use pygls, but hide it behind a Voss-owned `LspClientAdapter` interface. The plan should include an early spike test using a fake stdio JSON-RPC server and one real installed server if available. Every downstream tool should depend on Voss result types, not pygls classes.

## ast-grep Finding

Official ast-grep docs support the chosen CLI route:

- Install paths include homebrew, MacPorts, nix-shell, cargo, npm, and pip.
- The binary command can be `ast-grep` or `sg`, but Linux already has an `sg` command, so Voss should invoke `ast-grep`.
- `ast-grep run -p 'pattern' [PATHS]...` is the one-shot search path.
- `--json=stream` emits one JSON object per match; prefer it over pretty arrays for bounded incremental parsing.
- Match objects include text/range/file/lines/replacement/language/metaVariables per the official JSON docs already verified by the orchestrator.

Packaging recommendation: add `ast-grep-cli` to `voss[code]` and still support a missing-binary fallback. PyPI currently has current `ast-grep-cli` wheels for the M6-style platforms, but the wrapper should resolve the executable with `shutil.which("ast-grep")` and emit a structured unavailable/fallback result because platform packaging can drift.

## Architecture Patterns

### Responsibility Map

| Area | Responsibility | Existing analog |
|---|---|---|
| Index | Walk tracked files/fallback tree, hash files, extract symbols cheaply, store deterministic SQLite schema, summarize for context/TUI | `cognition.build_repo_idx()` uses git-first file discovery and `.voss-cache` convention in `voss/harness/cognition.py:304`; `.voss-cache` root helper at `voss/harness/cognition.py:75` |
| LSP | Config load, lazy server launch, initialize/shutdown, definition/reference/workspace-symbol calls, process reap | `lifecycle.register_subprocess()` / `reap_all()` in `voss/harness/lifecycle.py:99` and `:485`; job process-group reap pattern in `:395` |
| ast-grep/regex | Subprocess `ast-grep run --json=stream`; timeout; parse JSONL; fallback regex over indexed files | `_shell_capture()` timeout/envelope style in `voss/harness/tools.py:472`; existing `fs_grep` bounded 200-hit search in `tools.py:343` |
| Tools | Four `ToolEntry` registrations, all `is_mutating=False`, source tags in results | `ToolEntry` at `voss/harness/tools.py:23`; registry return at `tools.py:443` |
| Slash | `/symbol`, `/refs`, `/refresh`; grouped `/help`; palette registration | `SlashRegistry` at `voss/harness/slash.py:21`; `_build_slash_registry()` registration loop at `voss/harness/cli.py:904`; help groups at `cli.py:1687` |
| System context | Bounded `## Project Index` static prefix block | cognition prompt builder at `voss/harness/agent.py:79`; system block composition at `agent.py:290`; CLI load path at `cli.py:1349` |
| M9 panel | `CodeIntelPanel` widget + side-region state machine; SubAgentPanel precedence | side region hidden by default in `styles.tcss:35`; `SubAgentPanel` mount/collapse in `tui/app.py:163`; widget exports in `widgets/__init__.py:24` |
| Redaction | Snippet cap + telemetry/session redaction; no raw snippets in auto-injection | session allowlist guarantee in `session.py:13`; telemetry arg redaction in `telemetry.py:105`; tool execution telemetry uses redaction in `agent.py:1060` |
| Lifecycle | Single process/session close path reaps LSP servers and ast-grep subprocesses | `_run_repl` finally reaps jobs in `cli.py:1547`; lifecycle atexit hook at `lifecycle.py:540` |

### Recommended Module Layout

Add a new package:

```text
voss/harness/code/
├── __init__.py
├── models.py          # CodeLocation, SymbolHit, ReferenceHit, SearchHit, CodeIntelResult
├── config.py          # .voss/lsp.yml + bundled defaults loader
├── index.py           # SQLite schema, build/refresh/query/summarize
├── lsp.py             # Voss-owned adapter interface + pygls implementation
├── lsp_registry.py    # lazy per-language server registry + lifecycle integration
├── ast_grep.py        # CLI wrapper + JSON stream parsing
├── regex_fallback.py  # bounded regex fallback over indexed files
├── service.py         # CodeIntelService orchestration used by tools/slash/TUI
├── context.py         # render_project_index_section(max_tokens=1500)
└── defaults/lsp.yml   # package-data defaults for python/js/ts/rust/go
```

Thin existing-file hooks:

- `voss/harness/tools.py`: import `CodeIntelService` lazily inside `make_toolset()` and register four `ToolEntry`s near other read-only tools.
- `voss/harness/cli.py`: build the service/index during `do_cmd` and `_run_repl`; register slash handlers in `_build_slash_registry`; pass service/context summary to TUI app if renderer is Textual.
- `voss/harness/agent.py`: extend `_compose_system_blocks()` or add a `project_index_text` argument so the section sits in the cached static prefix. Keep the existing cognition/VOSS/prior/loop slices stable.
- `voss/harness/tui/widgets/`: M9-08 adds `code_intel_panel.py` and exports `CodeIntelPanel`.
- `pyproject.toml`: add `code = ["pygls>=2.1,<3", "ast-grep-cli>=0.42,<0.43"]` and package data for `harness/code/defaults/*.yml`.

### Data Model Sketch

SQLite schema should start simple and rebuild on version mismatch:

```sql
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE files (
  id INTEGER PRIMARY KEY,
  path TEXT NOT NULL UNIQUE,
  lang TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  mtime REAL NOT NULL,
  size INTEGER NOT NULL
);
CREATE TABLE symbols (
  id INTEGER PRIMARY KEY,
  file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  kind TEXT NOT NULL,
  line INTEGER NOT NULL,
  col INTEGER NOT NULL,
  scope_path TEXT NOT NULL DEFAULT ''
);
CREATE INDEX idx_symbols_name ON symbols(name);
CREATE INDEX idx_files_lang ON files(lang);
```

References should not be eagerly indexed in M10 unless the implementation can extract them cheaply. `find_references` can query LSP first and ast-grep/regex second. If references are stored, keep them best-effort and invalidate on refresh.

## Don't Hand-Roll

- JSON-RPC framing, request IDs, stdio stream parsing, and LSP message conversion: use pygls behind an adapter.
- AST parsing or tree-sitter grammar loading: use ast-grep CLI.
- File watching: explicitly M14.
- A custom terminal renderer protocol for `CodeIntelPanel`: use Textual widgets and existing `TextualRenderer` private extensions.
- Durable semantic memory for symbols: index is rebuildable cache only.
- New permission semantics: read-only tools should rely on existing `ToolEntry.is_mutating=False` and `mode_allows`.

## Common Pitfalls

1. **SPEC/context index mismatch.** SPEC still says `index.json`; CONTEXT supersedes it with SQLite. Plan a doc patch before implementation.
2. **pygls docs are thin for clients.** Use a spike and adapter isolation. Do not leak pygls classes through tools, slash handlers, or tests.
3. **Blocking session start.** M10 has 5s/30s scan budgets. The planner must distinguish minimal pre-turn summary from full scan completion and define a partial-index warning contract.
4. **Tool count tests will fail.** `tests/harness/test_tools.py:110` pins mutating/read-only counts. Adding four read-only tools requires updating expected counts.
5. **Slash matrix will fail.** `tests/e2e/test_slash_matrix.py:63` asserts every registered slash command is covered. Add rows for `/symbol`, `/refs`, `/refresh`; update grouped help buckets.
6. **Permission READ_ONLY constant is not the source of truth.** `mode_allows()` accepts all non-mutating tools in plan/edit/auto, but tests mention known read-only tool names. Keep `is_mutating=False` authoritative and update tests conservatively.
7. **Telemetry redaction is shallow.** `telemetry.redact_tool_args()` redacts args, not arbitrary result payloads. Snippet-containing tool results must be bounded before `recorder.observe()` sees them.
8. **Session redaction is fixed-field, not content scrub.** Session tests preserve user-typed secret-shaped text by design. Do not claim persisted snippets are scrubbed unless M10 explicitly adds result redaction.
9. **Subprocess orphan risk.** Existing background jobs use process groups on POSIX and atexit reap; LSP servers need the same lifecycle discipline, including Windows-compatible fallback.
10. **Side-region ownership.** Current TUI hides `#side` when no SubAgentPanel exists. CodeIntelPanel changes the default: side region should show CodeIntelPanel unless a spawn is active or user pinning says otherwise.
11. **M9 runtime-surface baseline.** `tests/harness/tui/test_no_new_runtime_hooks.py:20` pins `recorder.py` and `voss_runtime/{probable,budget,agent}.py`. Do not touch those for code intel.
12. **Cache poisoning/path traversal.** All index paths must be relative to `cwd`, normalized, and rejected if they escape. Reuse `jail_path()` patterns; do not trust paths loaded from SQLite without rechecking.

## Code Examples

Recommended tool hook shape in `tools.py`:

```python
service = None

def _code_service():
    nonlocal service
    if service is None:
        from .code.service import CodeIntelService
        service = CodeIntelService.for_cwd(cwd)
    return service

@tool(name="code_search", description="Structural code search using ast-grep with regex fallback.")
async def code_search(pattern: str, path: str = ".", max_results: int = 50) -> str:
    return await _code_service().search(pattern, path=path, max_results=max_results)
```

Then register:

```python
"code_search": ToolEntry(descriptor=code_search, is_mutating=False),
"find_definition": ToolEntry(descriptor=find_definition, is_mutating=False),
"find_references": ToolEntry(descriptor=find_references, is_mutating=False),
"code_refresh": ToolEntry(descriptor=code_refresh, is_mutating=False),
```

Recommended ast-grep command:

```python
argv = [
    "ast-grep", "run",
    "--pattern", pattern,
    "--json=stream",
    "--color", "never",
    "--threads", "0",
    str(search_root),
]
```

Recommended result envelope:

```json
{
  "result": "ok",
  "source": "ast-grep",
  "language": "python",
  "hits": [
    {"file": "src/app.py", "range": {"start": [10, 0], "end": [12, 1]}, "text": "def foo(...)"}
  ],
  "truncated": false
}
```

Missing LSP envelope:

```json
{
  "result": "lsp_unavailable",
  "language": "go",
  "fallback": "ast-grep",
  "hint": "Install gopls and re-run /refresh."
}
```

## Validation Architecture

Plan validation should be layered so failures identify the subsystem, not just the user surface.

1. **Unit layer: index**
   - Tiny temp repos for Python, JS/TS, Rust, Go under `tests/fixtures/code/`.
   - Assert schema version, deterministic file rows, language detection, path normalization, vendored-dir pruning, rebuild-on-version-mismatch, and refresh after edit.
   - Include symlink/path traversal cases: index must not store paths outside cwd.

2. **Unit layer: ast-grep wrapper**
   - Monkeypatch `shutil.which`/subprocess path for missing binary.
   - Feed sample `--json=stream` lines into the parser.
   - Assert timeout, malformed JSON handling, max-results truncation, and regex fallback event `code_search.fallback=regex`.
   - Use one live ast-grep test only when binary is available; skip otherwise unless running the optional `voss[code]` acceptance job.

3. **Unit layer: LSP adapter/registry**
   - Fake stdio server for initialize/shutdown/definition/reference JSON-RPC.
   - Registry tests for lazy launch, per-language singleton, config overlay, missing command, timeout, and cleanup.
   - Real-server tests should be marked optional/acceptance because CI may not have pyright, rust-analyzer, gopls, or typescript-language-server.

4. **Harness tools**
   - Update `tests/harness/test_tools.py` count assertions.
   - Assert all four code tools are `ToolEntry`, `is_mutating=False`, and return source-tagged structured output.
   - Add permission matrix evidence that read-only code tools are allowed in plan/edit/auto.

5. **Slash**
   - Add focused slash handler tests plus `tests/e2e/test_slash_matrix.py` rows.
   - Assert `/symbol --help`, `/refs --help`, `/refresh --help`.
   - Assert `RESERVED_SLASH_NAMES` remains M8-only and code-intel names do not collide.

6. **System-context injection**
   - Capture provider messages as existing VOSS/cognition tests do.
   - Assert `## Project Index` appears after scan, contains counts/modules/entry points, has no raw snippets, and stays under 1500-token approximation.
   - Assert disabled or failed scan emits no section and no traceback.

7. **TUI / CodeIntelPanel**
   - M9-08 should add snapshot or structural Textual tests for idle tree, active results, focused excerpt, hidden/revealed side region, pin/unpin, and SubAgentPanel precedence.
   - M10 should only test integration events: `/symbol` updates panel results; spawn active swaps to SubAgentPanel and restores CodeIntelPanel.

8. **Lifecycle/orphan sampling**
   - Use a fake long-running server process where possible, plus `psutil` process lookup for acceptance.
   - Force session exit and interrupt paths. Assert no registered LSP process remains.
   - Include Windows-compatible branch coverage if process groups are POSIX-only.

9. **Performance sampling**
   - 10K-LoC generated fixture: session-start scan <=5s.
   - 100K-LoC generated fixture: scan <=30s or partial-index warning appears before first turn.
   - Keep performance tests marked `slow` unless cheap enough for default.

10. **Security/regression gates**
   - Preserve runtime-surface hash baseline.
   - Preserve no `class .*Memory` under `voss/harness/`.
   - Run `pytest -q tests/harness/test_session_redaction.py tests/harness/test_telemetry.py`.

## Security And Domain Risks

STRIDE-ish notes:

- **Spoofing:** `.voss/lsp.yml` can name arbitrary commands. Treat LSP servers as local subprocess tools and only launch configured binaries from user environment. Surface install hints; do not auto-install.
- **Tampering:** `index.db` is rebuildable cache and can be user-edited. Never treat DB paths as trusted; normalize and jail every path on read. Rebuild on schema mismatch or corrupt DB.
- **Repudiation:** Emit telemetry for fallback paths and refresh outcomes when `VOSS_LOG=1`, but avoid adding recorder emit points. Use existing telemetry event style.
- **Information disclosure:** Snippets can expose secrets in source files. Cap excerpts at 80 chars x 10 lines, redact telemetry args, do not put raw snippets into `## Project Index`, and document that user/source content can persist in sessions if returned to the agent.
- **Denial of service:** LSP servers and ast-grep can hang or emit huge output. Use timeouts, max-results, output caps, JSON streaming, and lifecycle reap.
- **Elevation of privilege:** `ast-grep` search is read-only if Voss never passes rewrite/update flags. Reject rewrite args entirely in M10. All code tools are read-only and must remain `is_mutating=False`.
- **Supply chain:** `ast-grep-cli` wheels are a binary dependency. Keep it optional in `voss[code]`, pin a compatible range, and fallback cleanly when unavailable.
- **Platform process risk:** POSIX process groups do not map directly to Windows. LSP lifecycle tests must cover terminate/wait/kill fallback without assuming `os.killpg`.

## Assumptions Log

- SQLite FTS is not required for M10. Plain indexed symbol-name queries are enough; FTS can be added later if `/symbol` quality demands it.
- M10 can add a new optional extra without changing default install size materially; `ast-grep-cli` only installs when `voss[code]` is requested.
- Session-start scan can build a minimal file/symbol index synchronously and continue deeper extraction asynchronously if over budget.
- LSP definition/reference calls require file URI + position. For a user-supplied symbol name without position, Voss should first resolve candidate symbols from index/workspace-symbol, then call definition/reference on a selected candidate or return ranked candidates.
- `CodeIntelPanel` mechanics belong in M9-08. M10 should not plan TUI widget internals until M9-08 exists.

## Open Questions

- Should `find_definition(symbol, path?)` return ranked candidates when the symbol is ambiguous, or require `path` for disambiguation? Recommendation: return ranked candidates with `result="ambiguous"` rather than guessing.
- Should `code_refresh(paths?)` refresh partial subtrees in SQLite or rebuild all in v0.2? Recommendation: implement full rebuild first, then add subtree refresh only if cheap.
- Should `.voss/lsp.yml` live under durable `.voss/` even though the index is cache? Recommendation: yes, config is durable project policy; index remains `.voss-cache/code/index.db`.
- Which acceptance environment will install real language servers? Recommendation: make real-server polyglot acceptance a documented optional CI/job gate; default tests use fakes plus graceful-unavailable paths.

## Sources

Local source:

- `.planning/phases/M10-agent-capability-surface-caps-01/M10-CONTEXT.md:11` phase boundary; `:23` pygls decision; `:30` ast-grep decision; `:38` SQLite decision; `:46` M9-08 dependency; `:60` redaction; `:74` lifecycle; `:81` soft degradation; `:145` deferred items.
- `.planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md:17` project index; `:22` LSP; `:27` ast-grep; `:32` tools; `:37` slash; `:42` auto-injection; `:47` TUI panel; `:80` constraints; `:96` acceptance criteria.
- `.planning/ROADMAP.md:24` M10 roadmap row.
- `.planning/REQUIREMENTS.md:37` `.voss-cache/` rebuildable-state requirement.
- `.planning/STATE.md:47` recent T8/M9-adjacent status; `:51` known full-suite blockers.
- `voss/harness/tools.py:23` `ToolEntry`; `:77` `make_toolset`; `:343` `fs_grep`; `:443` registry.
- `voss/harness/slash.py:21` slash registry.
- `voss/harness/cli.py:904` slash registration; `:1035` `do_cmd`; `:1313` `_run_repl`; `:1547` cleanup; `:1687` grouped slash help.
- `voss/harness/agent.py:79` cognition prompt; `:290` system block composition; `:1038` gated tool execution.
- `voss/harness/session.py:13` redaction guarantee; `:205` save path.
- `voss/harness/telemetry.py:105` tool arg redaction.
- `voss/harness/cognition.py:75` cache root; `:304` repo index analog; `:421` language-extension map; `:443` vendored-dir pruning.
- `voss/harness/cognition_schemas.py:1` strict pydantic schema pattern.
- `voss/harness/lifecycle.py:99` subprocess registration; `:395` job reap; `:485` global reap; `:540` atexit hook.
- `voss/harness/render.py:26` renderer protocol; `:59` renderer factory and TUI/plain fallback.
- `voss/harness/tui/app.py:163` side panel mounting; `:177` collapse behavior; `:258` region compose.
- `voss/harness/tui/widgets/sub_agent_panel.py:16` panel widget analog.
- `voss/harness/tui/widgets/__init__.py:24` widget public exports.
- `voss/harness/tui/styles.tcss:35` hidden side region contract.
- `pyproject.toml:26` optional extras pattern.
- `.planning/phases/M9-tui-shell-tui-01/M9-CONTEXT.md:44` slash palette; `:55` plain fallback; `:85` TUI integration refs.
- `.planning/phases/M9-tui-shell-tui-01/M9-UI-SPEC.md:44` region grid; `:145` accent allow-list; `:227` focus model.
- `tests/harness/test_tools.py:73` tool classification tests; `:110` count pin.
- `tests/e2e/test_perm_matrix.py:49` read-only tools allowed in all modes.
- `tests/e2e/test_slash_matrix.py:63` slash registry coverage gate.
- `tests/harness/test_session_redaction.py:27` schema allowlist; `:90` RunRecord redaction.
- `tests/harness/tui/test_no_new_runtime_hooks.py:20` runtime-surface hash baseline.

Official docs and package sources:

- pygls v2.1.1 docs: https://pygls.readthedocs.io/en/latest/ — primarily language-server documentation; Language Clients are marked "Coming Soon"; pygls supports stdio/TCP/websocket and Windows/macOS/Linux.
- pygls client API: https://pygls.readthedocs.io/en/latest/pygls/api-reference/clients.html — documents `BaseLanguageClient` and `JsonRPCClient` client methods, including initialize/shutdown/definition/references/workspace-symbol and `start_io`.
- ast-grep quick start: https://ast-grep.github.io/guide/quick-start.html — documents homebrew, MacPorts, nix-shell, cargo, npm, and pip installs; binary is `ast-grep` or `sg`, with `ast-grep` preferred on Linux because `sg` already exists.
- ast-grep CLI run reference: https://ast-grep.github.io/reference/cli/run.html — documents `ast-grep run --pattern`, `--lang`, and `--json=stream`.
- ast-grep JSON docs from official/Context7 findings supplied by orchestrator: `ast-grep run -p 'pattern' --json` returns a JSON array; `--json=stream` emits one JSON object per match; match objects include text, range, file, lines, replacement fields, language, and metaVariables.
- `ast-grep-cli` PyPI: https://pypi.org/project/ast-grep-cli/ — current 2026-05 package page shows prebuilt wheels for macOS universal2, Linux x86-64/aarch64 manylinux, and Windows x86-64/ARM64 among others.

