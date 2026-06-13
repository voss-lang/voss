---
phase: V22-external-memory-docs-ingest
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - voss/harness/recall/__init__.py
  - voss/harness/recall/external_index.py
  - tests/external_recall/__init__.py
  - tests/external_recall/conftest.py
  - tests/external_recall/test_config.py
  - tests/external_recall/test_chunker.py
  - tests/external_recall/test_incremental.py
  - tests/external_recall/test_background.py
  - tests/external_recall/test_recall_cli.py
  - tests/external_recall/test_agent_tool.py
  - tests/external_recall/test_golden_queries.py
  - tests/fixtures/recall_vault/getting-started.md
  - tests/fixtures/recall_vault/api-reference.md
  - tests/fixtures/recall_vault/concepts/chunking.md
  - tests/fixtures/recall_vault/changelog.md
autonomous: true
requirements: [VXMEM-01, VXMEM-02, VXMEM-03, VXMEM-04, VXMEM-05, VXMEM-06, VXMEM-07, VXMEM-08]
must_haves:
  truths:
    - "pytest COLLECTS tests/external_recall/ without collection errors (deferred imports)"
    - "All 23 VALIDATION tests exist and are RED (ImportError/AttributeError or assertion-fail, not collection-fail)"
    - "Fixture vault is committed with deterministic per-file vocabulary"
    - "voss/harness/recall package exists and exports the three planned symbols (signatures only)"
  artifacts:
    - path: "voss/harness/recall/external_index.py"
      provides: "ExternalSourceIndex, ExternalRecallService, extract_md_chunks contracts (skeleton)"
      contains: "class ExternalSourceIndex"
    - path: "tests/external_recall/conftest.py"
      provides: "fake_embed_fn, fixture_vault_path, indexed_fixture_vault, chroma_disabled_env"
      contains: "def fake_embed_fn"
    - path: "tests/fixtures/recall_vault/getting-started.md"
      provides: "fixture corpus file with preamble + headings"
      contains: "## Installation"
  key_links:
    - from: "tests/external_recall/conftest.py"
      to: "voss.harness.recall.external_index"
      via: "deferred import inside fixture bodies (RED signal until W1+)"
      pattern: "from voss.harness.recall.external_index import"
---

<objective>
Lay down the Wave 0 RED scaffold for V22: the new `voss/harness/recall/` package skeleton, all eight `tests/external_recall/` test files (23 requirement-keyed tests from V22-VALIDATION.md, written RED), the shared `conftest.py`, and the committed fixture markdown vault. This plan creates ONLY new files — no shared production files touched — so it runs first with zero conflict.

Purpose: Establish the test contract and module interface so every later wave turns specific tests GREEN. Pytest collection must succeed even though the implementation is absent (defer module imports into test/fixture bodies, mirroring V19's `tests/code_recall/conftest.py`).
Output: Package skeleton with class/function signatures (NotImplementedError bodies), 8 RED test files, fixture vault.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V22-external-memory-docs-ingest/V22-SPEC.md
@.planning/phases/V22-external-memory-docs-ingest/V22-CONTEXT.md
@.planning/phases/V22-external-memory-docs-ingest/V22-RESEARCH.md
@.planning/phases/V22-external-memory-docs-ingest/V22-VALIDATION.md

<interfaces>
<!-- Contracts this plan DEFINES. Later waves implement against these exact signatures. -->

voss/harness/recall/external_index.py (skeleton — signatures only, bodies raise NotImplementedError):

```python
def extract_md_chunks(content: str) -> list[tuple[int, int, str]]: ...
    # returns (start_line, end_line, chunk_text) regions on markdown heading boundaries

class ExternalSourceIndex:
    def __init__(self, cwd: Path, source: dict) -> None: ...  # source = {name, path, glob}
    def build(self) -> None: ...
    def query(self, query: str, top_k: int = 5) -> list[Hit]: ...
    def _bm25_query(self, query: str, top_k: int) -> list[Hit]: ...

class ExternalRecallService:
    def __init__(self, cwd: Path, session_id: str | None = None) -> None: ...
    def ensure_background_build(self) -> None: ...
    def is_ready(self) -> bool: ...
    def build_all(self) -> None: ...                       # synchronous build of every source (--refresh path)
    def query_all(self, query: str, top_k: int = 5) -> list[list[Hit]]: ...  # one Hit list per source
```

config.py (DEFINED here as a test contract; IMPLEMENTED in V22-02):
```python
def get_recall_sources() -> list[dict]: ...  # ordered [{name, path, glob}]; raises ValueError on reserved/duplicate names
```

Existing reused contracts (already in codebase — do NOT redefine):
- voss/harness/memory_store.py: `Hit(source, locator, score, excerpt, session_id, ts, line_start, line_end)`; `MemoryStore._rrf_merge(rankings: list[list[Hit]], *, top_k, k=60)` (static)
- voss/harness/code/semantic_index.py: `_split_oversize(start, end, lines, max_chars=800)`, `_file_hash(content)`, `_effective_embedding_model()` — module-level, importable
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create recall package skeleton with signature-only contracts</name>
  <read_first>
    - voss/harness/code/semantic_index.py (the analog being ported — class shape, module-level helpers, Pitfall comments)
    - voss/harness/memory_store.py:41-54 (Hit dataclass — DO NOT redefine; import it)
  </read_first>
  <files>voss/harness/recall/__init__.py, voss/harness/recall/external_index.py</files>
  <action>
    Create the `voss/harness/recall/` package. `__init__.py` exports `ExternalSourceIndex`, `ExternalRecallService`, `extract_md_chunks` from `external_index`.

    In `external_index.py`, declare the exact signatures from the `<interfaces>` block above. Bodies raise `NotImplementedError("V22-02/03")` (this is the RED contract; later waves fill them). At module top, import the verbatim-reuse helpers so the import path is pinned now: `from voss.harness.code.semantic_index import _split_oversize, _file_hash, _effective_embedding_model` and `from voss.harness.memory_store import Hit, MemoryStore, _bm25_tokenize`. Do NOT import `sentence_transformers`/`chromadb` at module scope (Pitfall 2 — cold-load must stay lazy inside `_maybe_semantic`). Set `_MAX_CHUNK_CHARS = 800` reuse via the imported `_split_oversize` default (do not redefine the constant unless needed for a local reference).

    Add module docstring noting this mirrors `code/semantic_index.py` with heading-boundary chunking (D-06) and per-source isolation under `.voss-cache/recall/<name>/` (D-05). NO fenced implementation logic beyond signatures.
  </action>
  <verify>
    <automated>.venv/bin/python -c "from voss.harness.recall.external_index import ExternalSourceIndex, ExternalRecallService, extract_md_chunks; print('ok')"</automated>
  </verify>
  <acceptance_criteria>
    `.venv/bin/python -c "from voss.harness.recall import ExternalSourceIndex, ExternalRecallService, extract_md_chunks"` exits 0. Calling `extract_md_chunks("x")` raises NotImplementedError (RED). No top-level import of chromadb/sentence_transformers (grep: `grep -v '^#' voss/harness/recall/external_index.py | grep -c 'import chromadb\|import sentence_transformers'` returns 0).
  </acceptance_criteria>
  <done>Package importable; three symbols exported; bodies RED via NotImplementedError; reuse helpers imported at module top; no eager embedding-lib import.</done>
</task>

<task type="auto">
  <name>Task 2: Commit the fixture vault with deterministic per-file vocabulary</name>
  <read_first>
    - .planning/phases/V22-external-memory-docs-ingest/V22-RESEARCH.md (Fixture Vault Design section ~L852-880 — required filenames, headings, golden-query keywords)
    - .planning/phases/V22-external-memory-docs-ingest/V22-VALIDATION.md (Wave 0 Requirements — fixture file list)
  </read_first>
  <files>tests/fixtures/recall_vault/getting-started.md, tests/fixtures/recall_vault/api-reference.md, tests/fixtures/recall_vault/concepts/chunking.md, tests/fixtures/recall_vault/changelog.md</files>
  <action>
    Write the committed fixture markdown corpus per the RESEARCH Fixture Vault Design. Each file MUST have distinct vocabulary so golden queries discriminate:
    - `getting-started.md`: preamble paragraph (before first heading) + `## Installation`, `## Configuration`, `## First Steps`. Keywords: installation, quickstart, setup.
    - `api-reference.md`: `## Overview` + nested `### GET /users`, `### POST /notes`. Keywords: endpoint, authentication, rate limit.
    - `concepts/chunking.md`: `# Chunking Algorithm` + `## ATX Headings` + `## Oversize Guard`. Keywords: chunk, boundary, embedding, heading. Include at least one section whose body exceeds 800 chars (to exercise oversize subsplit in `test_oversize_subsplit`) AND a fenced code block containing a `# comment` line (to exercise `test_code_fence_heading_ignored`).
    - `changelog.md`: `# v2.0` + `## Breaking Changes` + `## New Features` + `# v1.9`. Keywords: 2026, release, breaking change.

    Also create one non-markdown decoy: `tests/fixtures/recall_vault/notes.txt` containing distinctive text, so `test_non_md_skipped` can assert it is NOT ingested. (Add to files_modified note: this is a 5th data file under the fixture dir.)
  </action>
  <verify>
    <automated>.venv/bin/python -c "from pathlib import Path; r=Path('tests/fixtures/recall_vault'); assert (r/'getting-started.md').exists() and (r/'concepts/chunking.md').exists() and (r/'notes.txt').exists(); print('ok')"</automated>
  </verify>
  <acceptance_criteria>
    All four `.md` files + `concepts/` subdir + `notes.txt` decoy exist. `concepts/chunking.md` contains a fenced code block with a `#`-prefixed line AND a section body >800 chars. `getting-started.md` has text before its first `#` heading (preamble).
  </acceptance_criteria>
  <done>Fixture vault committed; deterministic vocab per file; oversize section + code-fence-with-hash + preamble + non-md decoy all present.</done>
</task>

<task type="auto">
  <name>Task 3: Write all 8 RED test files + conftest binding the 23 VALIDATION tests</name>
  <read_first>
    - tests/code_recall/conftest.py (the exact fixture pattern to mirror: fake_embed_fn, indexed_fixture_repo, chroma_disabled_env, deferred imports)
    - .planning/phases/V22-external-memory-docs-ingest/V22-VALIDATION.md (Per-Task Verification Map — every test name + req binding)
  </read_first>
  <files>tests/external_recall/__init__.py, tests/external_recall/conftest.py, tests/external_recall/test_config.py, tests/external_recall/test_chunker.py, tests/external_recall/test_incremental.py, tests/external_recall/test_background.py, tests/external_recall/test_recall_cli.py, tests/external_recall/test_agent_tool.py, tests/external_recall/test_golden_queries.py</files>
  <action>
    Create `__init__.py` (empty) and `conftest.py` mirroring `tests/code_recall/conftest.py`: copy `fake_embed_fn` and `chroma_disabled_env` verbatim; add `fixture_vault_path` (returns `Path(__file__).parent.parent / "fixtures" / "recall_vault"`) and `indexed_fixture_vault` (copies the fixture vault into `tmp_path`, declares a single `[[recall.sources]]` source pointing at it, builds via `ExternalSourceIndex(...).build()` — deferred import inside the fixture body so collection succeeds RED). Provide a helper to write a temp `config.toml` with given `[[recall.sources]]` entries (used by config tests) honoring `XDG_CONFIG_HOME` monkeypatch.

    Write the 8 test files with EXACTLY the test function names from V22-VALIDATION.md Per-Task Verification Map (bind each to its req):
    - test_config.py: `test_parse_two_sources`, `test_no_section_zero_sources` [VXMEM-01]; `test_reserved_name_rejected`, `test_duplicate_name_rejected` [VXMEM-02]
    - test_chunker.py: `test_heading_boundary_split`, `test_headingless_one_chunk`, `test_oversize_subsplit`, `test_non_md_skipped`, `test_code_fence_heading_ignored` [VXMEM-04]
    - test_incremental.py: `test_derived_cache_rm_safe`, `test_manifest_has_hash_per_file` [VXMEM-03]; `test_touch_one_file_reembeds_only_it`, `test_unchanged_zero_embeds`, `test_deleted_file_purges_chunks` [VXMEM-05]
    - test_background.py: `test_session_does_not_block`, `test_degraded_before_ready`, `test_source_files_readonly` [VXMEM-06]
    - test_recall_cli.py: `test_plain_labeled_hits`, `test_json_source_field`, `test_degradation_no_chromadb` [VXMEM-07]; PLUS `test_code_memory_labels_still_resolve` (regression guard for the `_recall_hit_fields` schema change, per RESEARCH Open Question 3 / Pitfall 4)
    - test_agent_tool.py: `test_agent_gets_external_hits` [VXMEM-07]
    - test_golden_queries.py: a parametrized golden gate (~10 queries from RESEARCH L869-879) `test_golden_query` + a `test_golden_query_bm25` variant under `chroma_disabled_env` [VXMEM-08]

    All module imports of `voss.harness.recall.external_index` and `voss.harness.config.get_recall_sources` MUST be deferred into test/fixture bodies (NOT module top) so pytest COLLECTION passes while the implementation is RED — the runtime NotImplementedError/AttributeError IS the RED signal. For embed-counter tests, wrap `SemanticMemory._collection.upsert` (or the embedding function) with a call counter via monkeypatch. Use `.txt` decoy for `test_non_md_skipped`.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/external_recall/ --collect-only -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    `.venv/bin/python -m pytest tests/external_recall/ --collect-only -q` reports 23+ collected tests with ZERO collection errors. Running `.venv/bin/python -m pytest tests/external_recall/test_config.py -q` shows the tests RED (fail/error), NOT collection failure. All test function names match V22-VALIDATION.md exactly (grep each name).
  </acceptance_criteria>
  <done>8 test files + conftest + __init__ created; 23 VALIDATION tests present by exact name + the code/memory-label regression guard; collection green; tests RED via deferred-import runtime errors.</done>
</task>

</tasks>

<verification>
- `.venv/bin/python -m pytest tests/external_recall/ --collect-only -q` → 0 collection errors, 23+ tests
- Package imports clean: `.venv/bin/python -c "import voss.harness.recall.external_index"`
- Fixture vault committed and structurally complete (oversize section, code-fence-with-hash, preamble, .txt decoy)
- No eager chromadb/sentence_transformers import in external_index.py
</verification>

<success_criteria>
Wave 0 RED scaffold complete: every later wave has a concrete failing test to turn GREEN. No shared production file (cli.py/tools.py/config.py) touched — zero conflict with later waves.
</success_criteria>

<output>
Create `.planning/phases/V22-external-memory-docs-ingest/V22-01-SUMMARY.md` when done.
</output>
