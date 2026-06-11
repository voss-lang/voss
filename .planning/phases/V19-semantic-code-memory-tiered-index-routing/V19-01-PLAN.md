---
phase: V19-semantic-code-memory-tiered-index-routing
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - tests/code_recall/__init__.py
  - tests/code_recall/conftest.py
  - tests/code_recall/test_chunker.py
  - tests/code_recall/test_incremental.py
  - tests/code_recall/test_background.py
  - tests/code_recall/test_code_recall_tool.py
  - tests/code_recall/test_recall_cli.py
  - tests/code_recall/test_injection.py
  - tests/code_recall/test_enrichment.py
  - tests/code_recall/test_golden_queries.py
  - voss/harness/memory_store.py
  - pyproject.toml
autonomous: true
requirements: [VSEM-01, VSEM-02, VSEM-03, VSEM-04, VSEM-05, VSEM-06, VSEM-07, VSEM-08]
must_haves:
  truths:
    - "Every VSEM-01..08 has at least one RED (failing) test under tests/code_recall/"
    - "Scaffold imports resolve against the REAL planned module API (no fictional names)"
    - "Hit dataclass carries line_start/line_end so code hits keep file:line through RRF"
    - "pytest recognises the `slow` marker for the golden-query gate"
  artifacts:
    - path: "tests/code_recall/conftest.py"
      provides: "fake_embed_fn, indexed_fixture_repo, chroma_disabled_env, stub_provider fixtures"
      min_lines: 60
    - path: "tests/code_recall/test_chunker.py"
      provides: "VSEM-01 RED tests (symbol-boundary split, derived-cache)"
    - path: "tests/code_recall/test_enrichment.py"
      provides: "VSEM-07/08 RED tests (profile-off zero LLM, role routing, budget cap, ledger)"
    - path: "voss/harness/memory_store.py"
      provides: "Hit dataclass with line_start/line_end optional fields"
      contains: "line_start"
    - path: "pyproject.toml"
      provides: "slow pytest marker registration"
      contains: "slow"
  key_links:
    - from: "tests/code_recall/conftest.py"
      to: "voss.harness.code.semantic_index"
      via: "import CodeIndex, CodeIndexService"
      pattern: "from voss.harness.code.semantic_index import"
    - from: "voss/harness/memory_store.py"
      to: "_rrf_merge"
      via: "dataclasses.replace preserves line_start/line_end"
      pattern: "line_start"
---

<objective>
Wave 0 RED scaffold for V19. Create the full `tests/code_recall/` suite (one RED test file per requirement), the shared fixtures, the `slow` pytest marker, and the ONE shared-contract source change every other plan depends on: extending the `Hit` dataclass with `line_start`/`line_end` so code-chunk hits survive RRF fusion with their file:line locators intact.

Purpose: Establish the Nyquist test floor first (V-track convention: V17-01/V18-01 precedent) so every downstream plan executes against pre-written failing tests, not invented ones. Extending `Hit` here (rather than in the CodeIndex plan) makes it a stable contract Wave 1+ implements against.
Output: 10 test files + conftest, a `Hit` dataclass with two new optional fields, and a registered `slow` marker.
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
@.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-VALIDATION.md

<interfaces>
<!-- Planned module API surface the scaffold MUST import against (no ad-libbed names). -->
<!-- These are the contracts Wave 1+ implements; scaffold pins them so XPASS = real behavior. -->

Planned public API of voss/harness/code/semantic_index.py (Wave 1+):
  module-level: extract_chunks(db_path: Path, file_path: str, content: str) -> list[tuple[int,int,str]]
  module-level: _chunk_id(rel_path: str, seq: int) -> str   # returns "code:<rel_path>:<seq:03d>"
  class CodeIndex:
      def __init__(self, cwd: Path) -> None
      def build(self) -> None                       # full/incremental build into voss_code collection
      def query(self, query: str, top_k: int = 5) -> list[Hit]   # RRF(BM25+vector), degrades to BM25
      def _maybe_semantic(self) -> "SemanticMemory | None"
      def _load_manifest(self) -> dict
      def _run_enrichment(self, chunks, *, session_id, cwd) -> None   # VSEM-07/08
  class CodeIndexService:
      def __init__(self, cwd: Path) -> None
      def ensure_background_build(self) -> None
      def is_ready(self) -> bool
      def query(self, query: str, top_k: int = 5) -> list[Hit]

Existing reusable API (already in tree, import — do not redefine):
  voss.harness.memory_store.MemoryStore._rrf_merge(rankings, *, top_k, k=60) -> list[Hit]   # @staticmethod
  voss.harness.memory_store._bm25_tokenize(text) -> list[str]
  voss.harness.memory_store.Hit  # dataclass extended by THIS plan
  voss_runtime.memory.semantic.SemanticMemory(persist_dir=..., collection_name=...)
  voss.harness.tools.attach_code_recall_tool(tools, *, code_index_service)   # planned, Wave 2 (V19-03)
  voss.harness.config.get_index_enrich_model() -> str | None                  # planned, Wave 2 (V19-06)
  voss.harness.recorder._append_savings_record(cwd, session_id, record)       # existing
</interfaces>

Current Hit dataclass — memory_store.py:40-46:
  fields: source, locator, score, excerpt, session_id=None, ts=None
DefaultEmbeddingFunction fixture pattern — tests/memory/test_semantic.py:4-11
</context>

<tasks>

<task type="auto">
  <name>Task 1: Extend Hit dataclass with line_start/line_end</name>
  <read_first>
    - voss/harness/memory_store.py (read the Hit dataclass at lines 40-46 AND _rrf_merge at 425-440 to confirm dataclasses.replace usage stays valid)
  </read_first>
  <files>voss/harness/memory_store.py</files>
  <action>Add two trailing optional fields to the `Hit` dataclass (currently fields source, locator, score, excerpt, session_id=None, ts=None): `line_start: int | None = None` and `line_end: int | None = None`. Append them AFTER the existing optional fields so positional construction in existing call sites is unaffected. Do NOT change `_rrf_merge` — it dedupes on `hit.locator` and updates via `dataclasses.replace(carrier, score=score)`, both of which carry the new fields through unchanged. Per RESEARCH Open Question 2, this is the chosen approach (extend Hit, no separate CodeHit). Memory hits leave both fields None; code hits populate them.</action>
  <verify>
    <automated>.venv/bin/python -c "from voss.harness.memory_store import Hit; h=Hit(source='code',locator='code:a.py:000',score=1.0,excerpt='x',line_start=1,line_end=4); print(h.line_start,h.line_end)"</automated>
  </verify>
  <acceptance_criteria>
    - `Hit(source=..., locator=..., score=..., excerpt=...)` still constructs with line_start/line_end defaulting to None (source assertion: defaults present)
    - `Hit(..., line_start=1, line_end=4)` constructs and the values round-trip
    - `grep -n "line_start" voss/harness/memory_store.py` shows the field on the Hit dataclass
    - existing memory suite unaffected: `.venv/bin/python -m pytest tests/memory/ -q` passes
  </acceptance_criteria>
  <done>Hit carries line_start/line_end as trailing optional fields; tests/memory/ stays green.</done>
</task>

<task type="auto">
  <name>Task 2: Register slow marker + create test package skeleton with shared fixtures</name>
  <read_first>
    - pyproject.toml (read the [tool.pytest.ini_options] block — locate the `markers` list or confirm none exists)
    - tests/memory/test_semantic.py (lines 4-28 — DefaultEmbeddingFunction monkeypatch + skip-on-missing pattern)
    - tests/memory/__init__.py (package marker convention)
    - voss/harness/code/index.py (lines 107-141 — confirm db schema path .voss-cache/code/index.db and symbols(file_id,name,kind,line) so fixtures build a real M10 index)
  </read_first>
  <files>tests/code_recall/__init__.py, tests/code_recall/conftest.py, pyproject.toml</files>
  <action>Register the `slow` marker in `pyproject.toml` under `[tool.pytest.ini_options]` (add to an existing `markers = [...]` list, or create one) with description "slow: builds a real embedding index; needs HF model cache". Create empty `tests/code_recall/__init__.py`. Create `tests/code_recall/conftest.py` exposing four pytest fixtures: (1) `fake_embed_fn(monkeypatch)` — monkeypatches `SemanticMemory._embedding_function` to return `chromadb.utils.embedding_functions.DefaultEmbeddingFunction()` (ONNX, no network, no MiniLM download); skip the test if chromadb import fails. (2) `indexed_fixture_repo(tmp_path, fake_embed_fn)` — writes 2-3 small `.py` files with known symbol boundaries, calls `voss.harness.code.index.build_index(tmp_path)` to populate the M10 SQLite index at `.voss-cache/code/index.db`, then constructs `CodeIndex(tmp_path).build()` and returns tmp_path. (3) `chroma_disabled_env(monkeypatch)` — forces the chromadb-absent path by monkeypatching `CodeIndex._maybe_semantic` (or SemanticMemory import) to raise ModuleNotFoundError so degradation tests run. (4) `stub_provider(monkeypatch)` — a recording stub with a `.call_count` and `.calls` list, substituted for the enrichment provider build path (`voss.harness.model_router.build_provider_for_model`), used by VSEM-07/08 tests to assert zero/role-correct calls. Import all planned names from the `<interfaces>` block exactly — these MUST resolve against the Wave 1+ module API, not invented names.</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/code_recall/conftest.py --collect-only -q 2>&1 | tail -5; .venv/bin/python -c "import tomllib,pathlib; d=tomllib.loads(pathlib.Path('pyproject.toml').read_text()); print([m for m in d['tool']['pytest']['ini_options'].get('markers',[]) if 'slow' in m])"</automated>
  </verify>
  <acceptance_criteria>
    - `pyproject.toml` `[tool.pytest.ini_options].markers` contains an entry starting with `slow:`
    - `tests/code_recall/__init__.py` exists
    - `conftest.py` defines fixtures named exactly `fake_embed_fn`, `indexed_fixture_repo`, `chroma_disabled_env`, `stub_provider`
    - `grep -n "from voss.harness.code.semantic_index import" tests/code_recall/conftest.py` shows the planned import (CodeIndex / CodeIndexService)
    - pytest collects conftest without ImportError on the test-collection phase (import resolution may xfail at runtime if module not yet built — that is expected RED state, NOT a collection error; if collection errors on missing module, guard the import inside the fixture body so collection succeeds)
  </acceptance_criteria>
  <done>slow marker registered; conftest exposes the four named fixtures; planned imports are pinned to the real module API.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Write RED test files for VSEM-01..08 + golden-query gate</name>
  <read_first>
    - .planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-RESEARCH.md (Validation Architecture → Phase Requirements → Test Map; per-test names are listed there)
    - .planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-PATTERNS.md (test analog sections for test_chunker / test_code_recall_tool)
    - tests/harness/test_agent_packing.py (ToolEntry / ToolDescriptor construction + run-turn fixture pattern for the tool + injection tests)
  </read_first>
  <behavior>
    - test_chunker.py::test_chunks_split_on_symbol_boundaries — multi-symbol fixture file yields one chunk per [symbol_start, next_start) region (VSEM-01)
    - test_chunker.py::test_zero_symbol_file_single_chunk — file with no symbols yields one whole-file chunk (Pitfall 6)
    - test_chunker.py::test_oversize_chunk_split — >800-char region splits into sub-chunks with distinct code:<path>:<seq> ids (Pitfall 5)
    - test_chunker.py::test_derived_cache — rm the chroma dir + rebuild reproduces a working index from repo alone (VSEM-01 acceptance)
    - test_incremental.py::test_only_changed_file_reembeds — touch one file → exactly that file's chunks re-embed (embed-call counter) (VSEM-02)
    - test_incremental.py::test_no_reembed_on_unchanged — unchanged-repo reindex → zero embed calls (VSEM-02)
    - test_background.py::test_first_roundtrip_not_blocked — session-start path returns before is_ready() (VSEM-03)
    - test_background.py::test_degraded_before_ready — query before ready returns degraded hits (source marker), not an error (VSEM-03)
    - test_code_recall_tool.py::test_registration — code_recall in tools dict, group=="code", schema present (VSEM-04)
    - test_code_recall_tool.py::test_degradation — chroma_disabled_env → BM25-only hits, no raise (VSEM-04)
    - test_code_recall_tool.py::test_perf_p95 — p95 <500ms on indexed fixture (VSEM-04) [may carry @pytest.mark.slow]
    - test_recall_cli.py::test_exit_0_labeled — `voss recall <q>` exits 0, hits labeled [code]/[memory] (VSEM-05)
    - test_recall_cli.py::test_json_schema — `--json` output has `source` field per documented schema (VSEM-05); also assert NO secret/key strings appear in JSON (threat T-V19-04)
    - test_injection.py::test_token_cap — injected ## Code Recall section ≤1000 tokens by V18 counter (VSEM-06)
    - test_injection.py::test_evictable — allocator can evict the section (VSEM-06)
    - test_injection.py::test_off_switch — inject=false → zero injection bytes (VSEM-06)
    - test_enrichment.py::test_profile_off_zero_llm — profile off → stub_provider.call_count == 0 over a full build (VSEM-07)
    - test_enrichment.py::test_routes_index_enrich_role — profile on → calls route to index_enrich model, not session model (VSEM-07)
    - test_enrichment.py::test_fail_closed_no_config — profile on but no index_enrich config → enrichment disabled, zero calls (D-06)
    - test_enrichment.py::test_budget_cap_abort — tiny enrich_budget_tokens → clean abort, index valid, un-enriched chunks marked (VSEM-08)
    - test_enrichment.py::test_cost_ledger_line — enrichment writes a method="enrich" row to token-savings.jsonl (VSEM-08)
    - test_golden_queries.py::test_golden_concept_queries — ≥10 (query, expected_file) pairs, expected file in top-5 [@pytest.mark.slow] (quality gate)
  </behavior>
  <files>tests/code_recall/test_chunker.py, tests/code_recall/test_incremental.py, tests/code_recall/test_background.py, tests/code_recall/test_code_recall_tool.py, tests/code_recall/test_recall_cli.py, tests/code_recall/test_injection.py, tests/code_recall/test_enrichment.py, tests/code_recall/test_golden_queries.py</files>
  <action>Write all eight test files with the test functions named in `<behavior>`. Each test asserts REAL expected behavior against the planned module API (import paths/class/function names from the `<interfaces>` block). Tests MUST be genuine RED — failing because the implementation does not exist yet, NOT skipped and NOT `xfail(strict=False)`. Use plain failing asserts or `@pytest.mark.xfail(strict=True)` so an implemented feature flips to XPASS (which strict-xfail reports as a failure, surfacing the green). Per project memory (false-green incidents): never write a scaffold body that fabricates a fake module API to make the import succeed — if the planned symbol does not exist yet, the import error IS the RED signal; guard imports so test COLLECTION still succeeds (import inside the test body or use pytest.importorskip only for the optional chromadb dep, never for the voss modules under test). Mark `test_perf_p95`, `test_code_recall_tool.py` heavy paths, and `test_golden_concept_queries` with `@pytest.mark.slow`. For test_recall_cli use click's CliRunner or subprocess against `voss recall`. For test_enrichment use the `stub_provider` fixture and assert call_count semantics. For golden queries, embed a ~10-15 entry (query, expected_file) list against this Voss repo's known files (e.g. "where do we handle retry backoff" → a known retry/backoff file).</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/code_recall/ -q --co 2>&1 | tail -8; .venv/bin/python -m pytest tests/code_recall/ -q -p no:cacheprovider 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - All eight test files exist and pytest COLLECTS them without collection-time ImportError
    - Running `tests/code_recall/` (excluding slow) shows tests in RED state: failures or strict-xfail, ZERO passes that touch unbuilt modules, ZERO `xfail(strict=False)`
    - `grep -rn "strict=False" tests/code_recall/` returns nothing
    - `grep -rn "from voss.harness.code.semantic_index import" tests/code_recall/` shows planned imports in chunker/incremental/background/tool tests
    - Every VSEM-01..08 maps to ≥1 named test (cross-check against the behavior list)
    - `grep -rn "pytest.mark.slow" tests/code_recall/` shows the golden-query and perf tests marked
  </acceptance_criteria>
  <done>Eight RED test files cover VSEM-01..08 + golden gate; collection succeeds; no strict=False, no fabricated API; all unbuilt-feature tests fail or strict-xfail.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| repo files → test fixtures | fixture repos write/read files under tmp_path only |
| test assertions → CLI `--json` | tests assert the JSON contract that downstream code must honor (no secret leakage) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V19-01-01 | Tampering | Wave-0 scaffold (false-green risk) | mitigate | Tests import REAL planned module API; no `xfail(strict=False)`; strict-xfail flips XPASS→fail; grep gate `strict=False` == 0 (project-memory false-green guard) |
| T-V19-01-02 | Information Disclosure | `voss recall --json` contract test | mitigate | test_json_schema asserts no key/secret-shaped strings in JSON output (locks the contract before impl exists) |
| T-V19-SC | Tampering | npm/pip/cargo installs | accept | No new packages installed this plan (RESEARCH Package Legitimacy Audit: zero new deps); nothing to slopcheck |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/code_recall/ -q --ignore=tests/code_recall/test_golden_queries.py` — collects clean, all RED/strict-xfail
- `.venv/bin/python -m pytest tests/memory/ -q` — green (Hit extension non-breaking)
- `grep -rn "strict=False" tests/code_recall/` — empty
</verification>

<success_criteria>
- Hit dataclass has line_start/line_end; memory suite green
- slow marker registered in pyproject.toml
- 10 files under tests/code_recall/ (init, conftest, 8 test modules) all collecting
- Every VSEM-01..08 covered by ≥1 RED test against the real planned API
</success_criteria>

<output>
Create `.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-01-SUMMARY.md` when done
</output>
