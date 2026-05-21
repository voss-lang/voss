---
phase: F2-hybrid-semantic-search
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/memory_store.py
  - tests/harness/test_memory_store.py
autonomous: true
requirements: [FSRCH-01, FSRCH-03, FSRCH-04]

must_haves:
  truths:
    - "MemoryStore has a deterministic symbol-aware BM25 tokenizer"
    - "BM25 corpus construction preserves per-turn and per-ledger JSONL granularity"
    - "BM25-only recall preserves source filtering and tombstone filtering"
    - "Empty or no-match BM25 queries return []"
  artifacts:
    - path: "voss/harness/memory_store.py"
      provides: "Private BM25 tokenizer, corpus builder, and lexical recall helpers"
      contains: ["_bm25_tokenize", "_bm25_corpus", "_bm25_recall"]
    - path: "tests/harness/test_memory_store.py"
      provides: "Tokenizer and BM25 fallback regression coverage"
      contains: ["bm25", "getUserById", "parse_config_file", "tombstone"]
  key_links:
    - from: "MemoryStore.recall"
      to: "MemoryStore._bm25_recall"
      via: "Chroma-disabled fallback path"
      pattern: "_bm25_recall(query"
---

<objective>
Replace the naive `_keyword_scan()` lexical fallback with a BM25 lexical retriever that is symbol-aware, source-filtered, tombstone-safe, and still returns the existing `Hit` shape.

This plan intentionally does not wire vector fusion yet. It creates the lexical substrate that Plan 02 will merge with Chroma using Reciprocal Rank Fusion.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/F2-hybrid-semantic-search/F2-CONTEXT.md
@.planning/phases/F2-hybrid-semantic-search/F2-RESEARCH.md
@.planning/phases/F2-hybrid-semantic-search/F2-PATTERNS.md
@.planning/phases/F2-hybrid-semantic-search/F2-VALIDATION.md

<interfaces>
`MemoryStore.recall(query, top_k=5, source=None) -> list[Hit]` is the public entry point.

`Hit` fields are fixed: `source`, `locator`, `score`, `excerpt`, `session_id`, `ts`.

Existing locator helpers are fixed:
- `make_id("turn", session_id, seq=turn_idx)` produces `turn:<session>:NNN`.
- `_locator_from_path()` reconstructs file-backed locators.
- `_load_tombstones()` returns composite IDs that must never be returned.
</interfaces>
</context>

<threat_model>
| Threat | Severity | Mitigation |
|---|---|---|
| Tombstoned memory resurfaces through the new lexical path | medium | Build BM25 corpus after `_load_tombstones()` and exclude tombstoned locators before ranking |
| Symbol tokenizer leaks into public API or persisted state | low | Keep helpers private in `memory_store.py`; no new files under `.voss/` or `.voss-cache/` |
| Query with no lexical match returns arbitrary zero-score hits | medium | Drop scores `<= 0` before sorting and returning |
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Add symbol-aware tokenizer tests</name>
  <files>
    tests/harness/test_memory_store.py
  </files>
  <read_first>
    tests/harness/test_memory_store.py
    voss/harness/memory_store.py
    .planning/phases/F2-hybrid-semantic-search/F2-RESEARCH.md
  </read_first>
  <action>
    Add tests that import the private tokenizer from `voss.harness.memory_store` and assert deterministic tokens for these cases: `getUserById` includes `get`, `user`, `by`, `id`; `parse_config_file` includes `parse`, `config`, `file`; `voss.harness.memory_store` includes `voss`, `harness`, `memory`, `store`; and empty punctuation-only input returns `[]`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && PYTHONPATH=. pytest tests/harness/test_memory_store.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `tests/harness/test_memory_store.py` contains a test name including `tokenize`
    - The tokenizer test asserts tokens for `getUserById`
    - The tokenizer test asserts tokens for `parse_config_file`
    - The tokenizer test asserts punctuation-only input returns `[]`
  </acceptance_criteria>
  <done>Tokenizer regression tests exist and initially fail until `_bm25_tokenize` is implemented.</done>
</task>

<task type="auto">
  <name>Task 2: Implement BM25 tokenizer and corpus builder</name>
  <files>
    voss/harness/memory_store.py
  </files>
  <read_first>
    voss/harness/memory_store.py
    tests/harness/test_memory_store.py
    .planning/phases/F2-hybrid-semantic-search/F2-PATTERNS.md
  </read_first>
  <action>
    Add `import re` and `from rank_bm25 import BM25Okapi` to `memory_store.py`. Add private helper `_bm25_tokenize(text: str) -> list[str]` near the recall helpers. It must split camel/Pascal boundaries with the pattern `([a-z0-9])([A-Z])`, replace underscores, hyphens, dots, slashes, and non-word punctuation with spaces, lowercase, and return non-empty whitespace tokens.

    Add a private candidate representation local to `memory_store.py` using either a private dataclass or `tuple[Hit, str]`. Add `MemoryStore._bm25_corpus(source: str | None) -> list[tuple[Hit, str]]`. It must iterate the same `_SOURCES` as `_keyword_scan()`, respect the existing plural/singular source filter, skip tombstoned locators, read `turns` and `ledgers` JSONL line-by-line, and read decisions/conventions/notes whole-file. Reuse `make_id()` and `_locator_from_path()` for locators and preserve `session_id`/`ts` where `_scan_jsonl()` currently does.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && PYTHONPATH=. pytest tests/harness/test_memory_store.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `voss/harness/memory_store.py` contains `def _bm25_tokenize(text: str) -> list[str]`
    - `voss/harness/memory_store.py` contains `def _bm25_corpus(` or `def _bm25_corpus(self,`
    - `rank_bm25 import BM25Okapi` appears in `memory_store.py`
    - The corpus builder handles `src == "turns"` and `src == "ledgers"` without calling the old `_scan_jsonl()` scoring path
    - Tokenizer tests pass
  </acceptance_criteria>
  <done>BM25 tokenization and corpus construction exist and preserve MemoryStore locator/source semantics.</done>
</task>

<task type="auto">
  <name>Task 3: Replace keyword fallback with BM25-only recall</name>
  <files>
    voss/harness/memory_store.py
    tests/harness/test_memory_store.py
    tests/harness/test_chroma_unavailable.py
  </files>
  <read_first>
    voss/harness/memory_store.py
    tests/harness/test_memory_store.py
    tests/harness/test_chroma_unavailable.py
    tests/harness/conftest.py
  </read_first>
  <action>
    Add `MemoryStore._bm25_recall(query: str, *, top_k: int, source: str | None) -> list[Hit]`. It must tokenize the query, return `[]` for no tokens, build the BM25 corpus, return `[]` for empty corpus, instantiate `BM25Okapi(tokenized_corpus)`, call `get_scores(tokenized_query)`, assign each returned hit its BM25 score, drop scores `<= 0`, sort descending by score, and return at most `top_k`.

    Update `recall()` so that when Chroma is unavailable or throws, it calls `_bm25_recall()` instead of `_keyword_scan()`. Remove `_keyword_scan()` and `_scan_jsonl()` once their behavior is covered by `_bm25_corpus()` and `_bm25_recall()`. Update test wording in `test_chroma_unavailable.py` from keyword fallback to BM25 fallback where comments/docstrings mention the old path.

    Add tests in `test_memory_store.py` for BM25-only source filtering and tombstone filtering. Force Chroma unavailable by monkeypatching `MemoryStore._maybe_chroma` to return `None`. For tombstones, write a matching turn, call `forget()` for its locator, then assert `recall()` does not return that locator.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && PYTHONPATH=. pytest tests/harness/test_memory_store.py tests/harness/test_chroma_unavailable.py -q</automated>
  </verify>
  <acceptance_criteria>
    - `voss/harness/memory_store.py` contains `def _bm25_recall(`
    - `voss/harness/memory_store.py` no longer contains `def _keyword_scan(`
    - `voss/harness/memory_store.py` no longer contains `def _scan_jsonl(`
    - Chroma-disabled recall test still returns a list and matches seeded text
    - A BM25 source-filter test asserts every hit for `source="turns"` has `h.source == "turn"`
    - A tombstone test asserts a forgotten locator is absent from recall results
  </acceptance_criteria>
  <done>Naive keyword fallback is removed; BM25 is the lexical fallback and passes source/tombstone regressions.</done>
</task>

</tasks>

<verification>
Run:
- `cd /Users/benjaminmarks/Projects/Voss && PYTHONPATH=. pytest tests/harness/test_memory_store.py tests/harness/test_chroma_unavailable.py -q`
- `cd /Users/benjaminmarks/Projects/Voss && python -c "from rank_bm25 import BM25Okapi; print(BM25Okapi.__name__)"`
</verification>

<success_criteria>
- `MemoryStore.recall()` works with Chroma disabled through BM25.
- Source filters and tombstone filters behave as before.
- Symbol-aware tokenizer is covered by unit tests.
- No public API, slash command, or on-disk memory format changes are introduced.
</success_criteria>
