---
phase: V19-semantic-code-memory-tiered-index-routing
plan: 03
type: execute
wave: 2
depends_on: [V19-02]
files_modified:
  - voss/harness/code/semantic_index.py
  - voss/harness/code/service.py
  - voss/harness/tools.py
autonomous: true
requirements: [VSEM-03, VSEM-04]
must_haves:
  truths:
    - "First session prompt round-trip completes without blocking on the index build (daemon thread)"
    - "Recall before the index is ready returns degraded BM25/lexical hits with a source marker, never an error"
    - "code_recall is registered in the tool registry (group=code, scope=code) with a valid schema"
    - "code_recall hits carry file:line locators, score, excerpt; chroma-absent installs return BM25-only without error"
    - "Recall p95 <500ms on an indexed ~10K LoC fixture"
    - "An agent fs_write/fs_edit/fs_edit_many to an indexed code file fires an off-thread targeted re-hash of exactly that file (D-13 trigger #2); the write path never blocks"
  artifacts:
    - path: "voss/harness/code/semantic_index.py"
      provides: "CodeIndexService (daemon thread, ready Event, is_ready, query, queue_rehash, session_id) appended to existing module"
      contains: "queue_rehash"
    - path: "voss/harness/tools.py"
      provides: "attach_code_recall_tool + code_recall registration at make_toolset code-tool site"
      contains: "attach_code_recall_tool"
    - path: "voss/harness/code/service.py"
      provides: "lazy _get_code_index_service property on CodeIntelService"
      contains: "_get_code_index_service"
  key_links:
    - from: "voss/harness/tools.py make_toolset"
      to: "CodeIndexService"
      via: "attach_code_recall_tool(result, code_index_service=...)"
      pattern: "attach_code_recall_tool"
    - from: "voss/harness/tools.py fs_write/fs_edit/fs_edit_many return path"
      to: "CodeIndexService.queue_rehash"
      via: "is_ready-guarded off-thread targeted re-hash (D-13 trigger #2)"
      pattern: "queue_rehash"
    - from: "CodeIndexService.ensure_background_build"
      to: "CodeIndex.build"
      via: "threading.Thread(daemon=True)"
      pattern: "daemon=True"
---

<objective>
Make the index build non-blocking and expose it to agents. Add `CodeIndexService` (daemon-thread wrapper with a `threading.Event` readiness gate, plus a `queue_rehash` off-thread targeted re-hash) to `semantic_index.py`; add a lazy `_get_code_index_service` property to `CodeIntelService`; register the `code_recall` agent tool via `attach_code_recall_tool` at the `make_toolset` code-tool site (VSEM-03, VSEM-04); and hook the `fs_write`/`fs_edit`/`fs_edit_many` success paths to fire a targeted re-hash of the written path (D-13 reindex trigger #2).

Purpose: Session start never blocks on the seconds-to-minutes embedding cold-load + first build; agents get a concept-query tool (`code_recall`) that RRF-fuses BM25+vector and degrades to BM25-only — distinct from M10's lexical `code_search`.
Output: `CodeIndexService` (with `queue_rehash`), the lazy service accessor, the registered `code_recall` tool, and the fs-mutation re-hash hook (D-13 trigger #2). CLI verb is V19-04; injection is V19-05.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-SPEC.md
@.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-RESEARCH.md
@.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-PATTERNS.md

<interfaces>
voss/harness/code/semantic_index.py (from V19-02):
  class CodeIndex: __init__(cwd); build(session_id: str | None = None) -> None; query(query, top_k=5) -> list[Hit]; queue_rehash(path: str | Path) -> None  # queue_rehash added by THIS plan

voss/harness/code/service.py:
  class CodeIntelService: __init__(cwd, session_id=None); for_cwd(cls, cwd, session_id=None, renderer=None)
  # lazy property convention at service.py:117-119 (_get_registry / hasattr guard)

voss/harness/tools.py:
  attach_memory_tools(tools, *, store, session_id)        # shape to mirror — tools.py:159-215
  make_toolset(...)                                        # tools.py:218; code tools registered ~tools.py:796-832
  ToolEntry(descriptor=..., is_mutating=False, group=..., scope_requirements=(...))
  @tool(name=..., description=...) decorator
  CAPABILITY_GROUPS includes "code"
</interfaces>

<!-- Pitfall 2: sentence-transformers cold-load (4.86s) MUST happen inside the daemon thread, never on session thread. -->
<!-- Pitfall 3: one PersistentClient per process — CodeIndexService holds ONE CodeIndex (one SemanticMemory). -->
<!-- Anti-pattern: never sleep/block waiting on is_ready(); not-ready → degraded BM25 immediately. -->
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: CodeIndexService daemon wrapper + lazy service accessor</name>
  <read_first>
    - tests/code_recall/test_background.py (RED tests: test_first_roundtrip_not_blocked, test_degraded_before_ready)
    - voss/harness/code/semantic_index.py (the CodeIndex from V19-02 — build/query)
    - voss/harness/code/service.py (lines 20-32 CodeIntelService/for_cwd; 117-119 _get_registry lazy pattern to mirror)
    - .planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-PATTERNS.md (daemon-thread CodeIndexService block; service.py lazy-property section)
  </read_first>
  <files>voss/harness/code/semantic_index.py, voss/harness/code/service.py</files>
  <action>Append `CodeIndexService` to `semantic_index.py` per PATTERNS: `__init__(self, cwd, session_id: str | None = None)` holds one `CodeIndex(cwd)`, a `threading.Event _ready`, `_thread=None`, and stores `self._session_id = session_id` (threaded to the enrichment ledger row in V19-06; default `None`). `ensure_background_build()` — idempotent (return if `_thread is not None`); spawn `threading.Thread(target=self._build_loop, daemon=True)` and start. `_build_loop()` — `try: self._code_index.build(session_id=self._session_id)` `except Exception as exc: print(..., file=sys.stderr)` `finally: self._ready.set()` (ALWAYS signal ready, degraded if failed). Pass `session_id` THROUGH to `build()` — never let it reach `build()` as a literal ellipsis; a sessionless background build resolves the `"index-background"` fallback inside V19-06's enrichment ledger write (NOT a `None` write path). `is_ready() -> bool` returns `_ready.is_set()`. `query(self, query, top_k=5) -> list[Hit]` — delegate to `self._code_index.query(...)`; if NOT ready, the underlying query already returns BM25-only/degraded hits (never block, never sleep — Pitfall/anti-pattern). Add `queue_rehash(self, path) -> None` — if NOT `is_ready()`, return immediately (the in-flight full build already covers the file); otherwise spawn a short `threading.Thread(target=..., daemon=True)` that calls `self._code_index.build(session_id=self._session_id)` (the manifest hash-skip in V19-02 re-embeds ONLY the changed path, so a targeted re-hash of the written file is exactly its chunks; never block the caller). The cold sentence-transformers load happens inside `build()` which runs in this daemon thread (Pitfall 2). In `voss/harness/code/service.py`, add `_get_code_index_service(self) -> CodeIndexService` mirroring the `_get_registry` lazy guard exactly (`hasattr(self, "_code_index_service")` / None check), constructing `CodeIndexService(self.cwd, session_id=self.session_id)` (thread the CodeIntelService session_id through) and calling `ensure_background_build()` once. Do NOT construct CodeIndexService eagerly in `__init__`/`for_cwd` (that would import sentence-transformers on the session thread).</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/code_recall/test_background.py -x -q 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `test_background.py::test_first_roundtrip_not_blocked` passes: the session path returns before `is_ready()` becomes true
    - `test_background.py::test_degraded_before_ready` passes: `query()` before ready returns degraded hits (source marker), not an exception
    - `ensure_background_build()` is idempotent (second call spawns no second thread — source review)
    - `_build_loop` sets `_ready` in a `finally` so a build failure still flips ready (degraded) — source review
    - `_get_code_index_service` uses the same `hasattr`/None guard as `_get_registry` and is the ONLY construction site (no eager construct in for_cwd), and threads `session_id=self.session_id` into the `CodeIndexService(...)` constructor — source review
    - `queue_rehash(path)` returns immediately when not ready and otherwise re-hashes off-thread (daemon, never blocks the caller); `build` is always called with `session_id=self._session_id` (never a literal ellipsis) — source review
  </acceptance_criteria>
  <done>Daemon-thread CodeIndexService with readiness Event; lazy accessor on CodeIntelService; background RED tests green; no session-thread cold-load.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Register code_recall agent tool</name>
  <read_first>
    - tests/code_recall/test_code_recall_tool.py (RED tests: test_registration, test_degradation, test_perf_p95)
    - voss/harness/tools.py (lines 159-215 attach_memory_tools to mirror; 218 make_toolset; ~796-832 code-tool registration block + CodeIntelService construction site; 28 CAPABILITY_GROUPS; 64 ToolEntry)
    - .planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-RESEARCH.md (Code Examples → attach_code_recall_tool pattern)
  </read_first>
  <files>voss/harness/tools.py</files>
  <action>Add `attach_code_recall_tool(tools: dict, *, code_index_service)` to `voss/harness/tools.py`, mirroring `attach_memory_tools` shape (tools.py:159-215). Define an async `code_recall(query: str, top_k: int = 5) -> str` decorated with `@tool(name="code_recall", description=...)` where the description tells the agent: semantic concept search returning file:line-anchored chunk hits (BM25+vector RRF); use for concept queries ("where is retry handled"); for exact-name lookup use `code_search` instead (collision-avoidance copy). Body: `hits = code_index_service.query(query, top_k=top_k)`; format one block per hit — `[code] {path}:{line_start} (score {score:.2f})` derived from `hit.locator`/`hit.line_start`, then the excerpt truncated to 160 chars; `(no hits)` when empty. Register `tools["code_recall"] = ToolEntry(descriptor=code_recall, is_mutating=False, group="code", scope_requirements=("code",))`. Wire it into `make_toolset`: at the existing code-tool registration site (~tools.py:796-832, where `CodeIntelService.for_cwd` is constructed and `code_search`/`find_definition` are registered), obtain the CodeIndexService via the new `_get_code_index_service()` accessor (which already threads the session's `session_id` into the service, so background/targeted builds write the enrichment ledger row to the `/cost`-readable session path — never `.voss/sessions/None/`) and call `attach_code_recall_tool(result, code_index_service=...)` alongside the existing code tools. Guard with the same optional-import try/except already wrapping `_CodeIntelService` so a missing code service degrades cleanly.</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/code_recall/test_code_recall_tool.py -x -q -m "not slow" 2>&1 | tail -15; .venv/bin/python -m pytest tests/code_recall/test_code_recall_tool.py::test_perf_p95 -x -q 2>&1 | tail -8</automated>
  </verify>
  <acceptance_criteria>
    - `test_code_recall_tool.py::test_registration` passes: `code_recall` in tools, `group=="code"`, `scope_requirements==("code",)`, descriptor schema present
    - `test_code_recall_tool.py::test_degradation` passes: under `chroma_disabled_env`, code_recall returns BM25-only output without raising
    - `test_code_recall_tool.py::test_perf_p95` passes: p95 <500ms on the indexed fixture
    - `code_recall` description explicitly distinguishes itself from `code_search` (source review — collision-avoidance per VSEM-04)
    - `grep -n "attach_code_recall_tool" voss/harness/tools.py` shows both the def and the make_toolset call site
  </acceptance_criteria>
  <done>code_recall registered at the make_toolset code-tool site; registration/degradation/perf RED tests green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Targeted re-hash on agent file mutation (D-13 trigger #2)</name>
  <read_first>
    - tests/code_recall/test_incremental.py (RED test: test_targeted_rehash_on_fs_write — added to the V19-01 scaffold)
    - voss/harness/tools.py (the `fs_write` / `fs_edit` / `fs_edit_many` tool definitions and their return paths; the `_get_code_index_service` accessor wired in Task 2)
    - .planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-CONTEXT.md (D-13 — three reindex triggers; trigger #2 is THIS task)
  </read_first>
  <files>voss/harness/tools.py</files>
  <action>Implement D-13 reindex trigger #2 (targeted re-hash on agent file mutation). At the SUCCESS return path of the `fs_write`, `fs_edit`, and `fs_edit_many` tools in `voss/harness/tools.py`, after the write has been applied, fire a targeted re-hash of the written path(s) via the CodeIndexService obtained from the same `_get_code_index_service()` accessor used in Task 2. Guard with `is_ready()` — if the service is not yet ready, do NOTHING (the in-flight full build already covers the file; D-13 trigger #1). When ready, call `code_index_service.queue_rehash(path)` for each written path (for `fs_edit_many`, iterate the mutated paths). `queue_rehash` already spawns its own daemon thread, so the tool return path is NOT blocked — the mutation result returns to the agent immediately while the re-hash runs off-thread. Only re-hash paths whose suffix is in `LANGUAGE_EXTS` (skip non-code writes — no wasted embed work). Reuse the same optional-import try/except guarding the code service so a build without the code subsystem degrades to a no-op (never raise from the write path). Do NOT add a per-recall sweep and do NOT add a watch daemon (D-13: M14 owns watch; per-recall sweep would break p95 <500ms).</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/code_recall/test_incremental.py::test_targeted_rehash_on_fs_write -x -q 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `test_incremental.py::test_targeted_rehash_on_fs_write` passes: an `fs_write` to an indexed `.py` file triggers a re-embed of EXACTLY that file's chunks (embed-call counter scoped to the written path), with no other file re-embedded
    - the re-hash is fired only when `is_ready()` is true (not-ready writes are a no-op — covered by the in-flight build) — source review
    - the `fs_write`/`fs_edit`/`fs_edit_many` return path is NOT blocked on the re-hash (it runs via `queue_rehash`'s daemon thread) — source review
    - non-code writes (suffix not in `LANGUAGE_EXTS`) do not trigger a re-hash — source review
    - `grep -n "queue_rehash" voss/harness/tools.py` shows the call wired into the fs_write/fs_edit return path(s)
  </acceptance_criteria>
  <done>fs_write/fs_edit/fs_edit_many success paths fire an off-thread targeted re-hash of the written code path via queue_rehash (D-13 trigger #2); only that file's chunks re-embed; write path never blocks.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| agent → code_recall tool | untrusted query string crosses into BM25/Chroma query |
| daemon thread → session thread | background build writes Chroma; session reads via query |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V19-03-01 | Denial of Service | session-start cold-load blocking | mitigate | Build runs in daemon thread; query never sleeps/blocks on is_ready(); not-ready → immediate degraded BM25 (VSEM-03) |
| T-V19-03-02 | Tampering | concurrent Chroma write (daemon) + read (tool) | mitigate | One CodeIndex (one SemanticMemory/PersistentClient) per process held by CodeIndexService — no second client to same path (Pitfall 3, journal_mode=DELETE) |
| T-V19-03-03 | Information Disclosure | code_recall tool output | mitigate | Output is file:line + score + 160-char excerpt of repo source the agent already has read scope to; no secrets synthesized; excerpt is raw source, never executed (ASVS V5) |
| T-V19-SC | Tampering | npm/pip/cargo installs | accept | No new packages (RESEARCH Package Legitimacy Audit: zero new deps) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/code_recall/test_background.py tests/code_recall/test_code_recall_tool.py tests/code_recall/test_incremental.py::test_targeted_rehash_on_fs_write -q` — green (excluding/including perf)
- Coherence guard: `voss do` / `voss chat` start without added blocking — run `.venv/bin/python -m pytest tests/harness/ -q -k "toolset or packing"` green
</verification>

<success_criteria>
- CodeIndexService daemon build never blocks session start; degraded recall before ready
- code_recall registered (group=code), file:line hits, BM25-only degradation, p95 <500ms
- fs_write/fs_edit/fs_edit_many fire an off-thread targeted re-hash of the written code path (D-13 trigger #2); write path never blocks; only the changed file re-embeds
</success_criteria>

<output>
Create `.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-03-SUMMARY.md` when done
</output>
