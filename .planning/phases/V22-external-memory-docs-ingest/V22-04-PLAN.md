---
phase: V22-external-memory-docs-ingest
plan: 04
type: execute
wave: 3
depends_on: [V22-03]
files_modified:
  - voss/harness/cli.py
autonomous: true
requirements: [VXMEM-07]
must_haves:
  truths:
    - "voss recall fuses external-source hits via RRF and renders [<name>] in plain output"
    - "voss recall --json carries the corpus name in the source field for every hit"
    - "voss recall --refresh rebuilds external sources synchronously alongside the code index"
    - "code/memory labels still resolve correctly after the _recall_hit_fields schema change"
    - "chromadb-absent recall degrades to BM25-only without error"
  artifacts:
    - path: "voss/harness/cli.py"
      provides: "recall_cmd external fan-out + _recall_hit_fields source passthrough"
      contains: "ExternalRecallService"
  key_links:
    - from: "voss/harness/cli.py:recall_cmd"
      to: "MemoryStore._rrf_merge"
      via: "_rrf_merge([code_hits, mem_hits, *external_hits_per_source])"
      pattern: "_rrf_merge\\(\\[code_hits, mem_hits"
    - from: "voss/harness/cli.py:_recall_hit_fields"
      to: "hit.source"
      via: "pass hit.source directly (no code/memory normalization)"
      pattern: "hit.source"
---

<objective>
Wire external-source hits into the `voss recall` CLI surface (VXMEM-07, surface 1 of 2): extend `recall_cmd`'s `_rrf_merge` fan-out to include every declared external source, fix `_recall_hit_fields` to pass `hit.source` directly (was hardcoding "code"/"memory" — RESEARCH Pitfall 4 / Open Question 3), and make `--refresh` rebuild external sources synchronously (D-18).

Purpose: One owner of `cli.py` in this phase. Serialized into its own wave so no other plan edits `cli.py` concurrently.
Output: GREEN `test_recall_cli.py` (4 tests incl. the code/memory regression guard).
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V22-external-memory-docs-ingest/V22-RESEARCH.md

<interfaces>
Implemented in V22-03: `ExternalRecallService(cwd, session_id=None)` with `.build_all()`, `.query_all(query, top_k) -> list[list[Hit]]`.
Existing (cli.py): `recall_cmd` (L4805-4858), `_recall_hit_fields(hit)` (L4786-4802), `_redact_recall_text`, `MemoryStore._rrf_merge` (static), `CodeIndex` import.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Fix _recall_hit_fields to pass hit.source directly (with code-path locator handling)</name>
  <read_first>
    - voss/harness/cli.py:4786-4802 (_recall_hit_fields — current code/memory normalization to replace)
    - .planning/phases/V22-external-memory-docs-ingest/V22-RESEARCH.md Pitfall 4 (~L656-661), Open Question 3 (~L936-939), Assumption A4
    - tests/external_recall/test_recall_cli.py (test_json_source_field + test_code_memory_labels_still_resolve)
  </read_first>
  <files>voss/harness/cli.py</files>
  <behavior>
    - test_json_source_field: an external hit with source="docs" yields `"source": "docs"` in --json output (NOT "memory")
    - test_code_memory_labels_still_resolve: a code hit still reports source="code" with a parsed path + line fields; a memory hit reports source="memory" with path=None — the schema change is non-breaking for the existing two labels
  </behavior>
  <action>
    Change `_recall_hit_fields` to set `"source": hit.source` directly (per RESEARCH Pitfall 4 / A4). Preserve the code-locator path parsing: when `(hit.source or "").startswith("code")`, keep splitting the `code:<rel>:<seq>` locator into `path` and surfacing `line_start`/`line_end`; for all other sources (memory, external `<name>`), set `path=None`, `line_start=None`, `line_end=None` (external locators are `<name>:<rel>:<seq>` and display via `hit.locator`, like memory). Keep the `_redact_recall_text` excerpt redaction (T-V19-04 — do not weaken it). This is a minor `--json` schema change (the `source` field now carries the true corpus name); note it in the SUMMARY for the CHANGELOG.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest "tests/external_recall/test_recall_cli.py::test_json_source_field" "tests/external_recall/test_recall_cli.py::test_code_memory_labels_still_resolve" -x -q</automated>
  </verify>
  <acceptance_criteria>
    Both named tests pass. `_recall_hit_fields` returns `hit.source` verbatim (grep: `grep -c '"source": hit.source' voss/harness/cli.py` ≥ 1). Existing recall tests still green: `.venv/bin/python -m pytest tests/ -k "recall" -q` (no V19 regression).
  </acceptance_criteria>
  <done>_recall_hit_fields passes hit.source directly; code locators still parse to path:line; memory/external use locator display; excerpt redaction preserved; both tests GREEN.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Extend recall_cmd fan-out to external sources + --refresh rebuild</name>
  <read_first>
    - voss/harness/cli.py:4805-4858 (recall_cmd — current 2-corpus fan-out + --refresh + plain/json render)
    - .planning/phases/V22-external-memory-docs-ingest/V22-RESEARCH.md Q6 (~L365-394, fan-out shape), Open Question 2 (--refresh synchronous build)
    - tests/external_recall/test_recall_cli.py (test_plain_labeled_hits, test_degradation_no_chromadb)
  </read_first>
  <files>voss/harness/cli.py</files>
  <behavior>
    - test_plain_labeled_hits: `voss recall <q>` over the fixture vault prints a `[<name>]` line for an external hit (alongside [code]/[memory])
    - test_degradation_no_chromadb: with chromadb disabled, recall still returns external hits (BM25) and exits 0 (no error)
  </behavior>
  <action>
    In `recall_cmd`: construct an `ExternalRecallService(cwd)` (import from `voss.harness.recall.external_index`). On `--refresh` (D-18): call `ext_svc.build_all()` synchronously alongside the existing `code_index.build()`. Otherwise call `ext_svc.ensure_background_build()` then query (degrade-until-ready is acceptable for a one-shot CLI — `query_all` returns BM25 before ready). Collect `external_hits_per_source = ext_svc.query_all(query_str, top_k=recall_k)` (a `list[list[Hit]]`). Extend the fusion to `MemoryStore._rrf_merge([code_hits, mem_hits, *external_hits_per_source], top_k=top_k)` (Q6). Wrap the external query in try/except (broad) so a misconfigured source never kills code/memory recall — mirror the existing `mem_hits` guard. In the plain-render loop (L4850-4858): the existing `if fields["source"] == "code"` branch handles code path:line; the `else` branch already displays `hit.locator` — confirm external `<name>` hits flow through the `else` branch and render `[<name>] <locator> (score ...)`. No change needed to the per-source `[{fields['source']}]` label since it now reads the true source.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/external_recall/test_recall_cli.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    `.venv/bin/python -m pytest tests/external_recall/test_recall_cli.py -x -q` passes all 4. Fan-out uses the spread form (grep: `grep -c "external_hits_per_source" voss/harness/cli.py` ≥ 1). `--refresh` calls `build_all()` (grep: `grep -c "build_all()" voss/harness/cli.py` ≥ 1). External query failure does not abort recall (guarded).
  </acceptance_criteria>
  <done>recall_cmd fuses external sources via N-way _rrf_merge, --refresh rebuilds them synchronously, external hits render [<name>] in plain + carry source in --json, degrades cleanly without chromadb; 4 CLI tests GREEN.</done>
</task>

</tasks>

<verification>
- `.venv/bin/python -m pytest tests/external_recall/test_recall_cli.py -q` → 4 GREEN
- `.venv/bin/python -m pytest tests/ -k "recall" -q` → no V19/F2 recall regressions
- `--json` source field carries true corpus name; `--refresh` rebuilds external sources
</verification>

<success_criteria>
`voss recall` (surface 1 of VXMEM-07's two surfaces) fuses and labels external-source hits, with a non-breaking schema fix verified by the code/memory regression guard. `cli.py` edited by this plan only.
</success_criteria>

<output>
Create `.planning/phases/V22-external-memory-docs-ingest/V22-04-SUMMARY.md` when done.
</output>
