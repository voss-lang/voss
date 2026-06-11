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
  artifacts:
    - path: "voss/harness/code/semantic_index.py"
      provides: "CodeIndexService (daemon thread, ready Event, is_ready, query) appended to existing module"
      contains: "class CodeIndexService"
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
    - from: "CodeIndexService.ensure_background_build"
      to: "CodeIndex.build"
      via: "threading.Thread(daemon=True)"
      pattern: "daemon=True"
---

<objective>
Make the index build non-blocking and expose it to agents. Add `CodeIndexService` (daemon-thread wrapper with a `threading.Event` readiness gate) to `semantic_index.py`; add a lazy `_get_code_index_service` property to `CodeIntelService`; and register the `code_recall` agent tool via `attach_code_recall_tool` at the `make_toolset` code-tool site (VSEM-03, VSEM-04).

Purpose: Session start never blocks on the seconds-to-minutes embedding cold-load + first build; agents get a concept-query tool (`code_recall`) that RRF-fuses BM25+vector and degrades to BM25-only — distinct from M10's lexical `code_search`.
Output: `CodeIndexService`, the lazy service accessor, and the registered `code_recall` tool. CLI verb is V19-04; injection is V19-05.
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
  class CodeIndex: __init__(cwd); build(); query(query, top_k=5) -> list[Hit]

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
  <action>Append `CodeIndexService` to `semantic_index.py` per PATTERNS: `__init__(self, cwd)` holds one `CodeIndex(cwd)`, a `threading.Event _ready`, `_thread=None`. `ensure_background_build()` — idempotent (return if `_thread is not None`); spawn `threading.Thread(target=self._build_loop, daemon=True)` and start. `_build_loop()` — `try: self._code_index.build()` `except Exception as exc: print(..., file=sys.stderr)` `finally: self._ready.set()` (ALWAYS signal ready, degraded if failed). `is_ready() -> bool` returns `_ready.is_set()`. `query(self, query, top_k=5) -> list[Hit]` — delegate to `self._code_index.query(...)`; if NOT ready, the underlying query already returns BM25-only/degraded hits (never block, never sleep — Pitfall/anti-pattern). The cold sentence-transformers load happens inside `build()` which runs in this daemon thread (Pitfall 2). In `voss/harness/code/service.py`, add `_get_code_index_service(self) -> CodeIndexService` mirroring the `_get_registry` lazy guard exactly (`hasattr(self, "_code_index_service")` / None check), constructing `CodeIndexService(self.cwd)` and calling `ensure_background_build()` once. Do NOT construct CodeIndexService eagerly in `__init__`/`for_cwd` (that would import sentence-transformers on the session thread).</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/code_recall/test_background.py -x -q 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `test_background.py::test_first_roundtrip_not_blocked` passes: the session path returns before `is_ready()` becomes true
    - `test_background.py::test_degraded_before_ready` passes: `query()` before ready returns degraded hits (source marker), not an exception
    - `ensure_background_build()` is idempotent (second call spawns no second thread — source review)
    - `_build_loop` sets `_ready` in a `finally` so a build failure still flips ready (degraded) — source review
    - `_get_code_index_service` uses the same `hasattr`/None guard as `_get_registry` and is the ONLY construction site (no eager construct in for_cwd) — source review
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
  <action>Add `attach_code_recall_tool(tools: dict, *, code_index_service)` to `voss/harness/tools.py`, mirroring `attach_memory_tools` shape (tools.py:159-215). Define an async `code_recall(query: str, top_k: int = 5) -> str` decorated with `@tool(name="code_recall", description=...)` where the description tells the agent: semantic concept search returning file:line-anchored chunk hits (BM25+vector RRF); use for concept queries ("where is retry handled"); for exact-name lookup use `code_search` instead (collision-avoidance copy). Body: `hits = code_index_service.query(query, top_k=top_k)`; format one block per hit — `[code] {path}:{line_start} (score {score:.2f})` derived from `hit.locator`/`hit.line_start`, then the excerpt truncated to 160 chars; `(no hits)` when empty. Register `tools["code_recall"] = ToolEntry(descriptor=code_recall, is_mutating=False, group="code", scope_requirements=("code",))`. Wire it into `make_toolset`: at the existing code-tool registration site (~tools.py:796-832, where `CodeIntelService.for_cwd` is constructed and `code_search`/`find_definition` are registered), obtain the CodeIndexService via the new `_get_code_index_service()` accessor and call `attach_code_recall_tool(result, code_index_service=...)` alongside the existing code tools. Guard with the same optional-import try/except already wrapping `_CodeIntelService` so a missing code service degrades cleanly.</action>
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
- `.venv/bin/python -m pytest tests/code_recall/test_background.py tests/code_recall/test_code_recall_tool.py -q` — green (excluding/including perf)
- Coherence guard: `voss do` / `voss chat` start without added blocking — run `.venv/bin/python -m pytest tests/harness/ -q -k "toolset or packing"` green
</verification>

<success_criteria>
- CodeIndexService daemon build never blocks session start; degraded recall before ready
- code_recall registered (group=code), file:line hits, BM25-only degradation, p95 <500ms
</success_criteria>

<output>
Create `.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-03-SUMMARY.md` when done
</output>
