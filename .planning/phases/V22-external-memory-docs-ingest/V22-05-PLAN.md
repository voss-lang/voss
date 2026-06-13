---
phase: V22-external-memory-docs-ingest
plan: 05
type: execute
wave: 4
depends_on: [V22-04]
files_modified:
  - voss/harness/tools.py
autonomous: true
requirements: [VXMEM-07, VXMEM-08]
must_haves:
  truths:
    - "The agent recall tool returns external-source hits alongside memory hits, [<name>]-labeled"
    - "ExternalRecallService is spawned (background, non-blocking) from make_toolset alongside CodeIndexService"
    - "The golden-query gate over the committed fixture vault passes (~10 queries land their expected [<name>] hit in top-5)"
    - "The golden gate passes with chromadb uninstalled (BM25 degradation)"
  artifacts:
    - path: "voss/harness/tools.py"
      provides: "memory_recall external fan-out + ExternalRecallService spawn in make_toolset"
      contains: "ExternalRecallService"
  key_links:
    - from: "voss/harness/tools.py:make_toolset"
      to: "ExternalRecallService.ensure_background_build"
      via: "spawn beside CodeIndexService (non-blocking session start)"
      pattern: "ensure_background_build"
    - from: "voss/harness/tools.py:memory_recall"
      to: "MemoryStore._rrf_merge"
      via: "fuse store.recall with external query_all (Option B — agent gets external hits without a new tool)"
      pattern: "_rrf_merge"
---

<objective>
Wire external-source hits into the agent recall surface (VXMEM-07, surface 2 of 2) and land the golden-query gate (VXMEM-08).

**Planner decision (RESEARCH Open Question 1 — Option B chosen):** Extend the existing `memory_recall` tool inside `attach_memory_tools` to fan out to external sources and fuse via `_rrf_merge`, rather than adding a separate `attach_external_recall_tool`. Rationale: the SPEC acceptance test `test_agent_gets_external_hits` requires external hits to come back from the recall verb the agent ALREADY calls — Option B satisfies "both surfaces" without the agent needing to know to invoke a new tool. The `[<name>]` label already works because `memory_recall`'s formatter prints `[{h.source}]` (tools.py:L190) and external Hits carry `source=<name>`.

Purpose: Last wave; sole owner of `tools.py`. Closes VXMEM-07's second surface and the VXMEM-08 end-to-end gate.
Output: GREEN `test_agent_tool.py` (1 test) + `test_golden_queries.py` (golden gate, with + without chromadb).
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V22-external-memory-docs-ingest/V22-RESEARCH.md

<interfaces>
Implemented in V22-03: `ExternalRecallService(cwd, session_id=None)` with `.ensure_background_build()`, `.query_all(query, top_k) -> list[list[Hit]]`.
Existing (tools.py): `attach_memory_tools(tools, *, store, session_id)` (L159-215) registering `memory_recall` (L168-194, formatter at L190 prints `[{h.source}]`); `make_toolset(cwd, *, renderer, net, session_id)` (L261); CodeIndexService spawn block (L898-916); `attach_code_recall_tool` (L218-258, the parallel pattern).
Reuse: `MemoryStore._rrf_merge([...], top_k=top_k)` (static).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Spawn ExternalRecallService in make_toolset + fan out memory_recall to external hits</name>
  <read_first>
    - voss/harness/tools.py:159-215 (attach_memory_tools / memory_recall — Option B extension target; the [{h.source}] formatter)
    - voss/harness/tools.py:898-918 (make_toolset CodeIndexService spawn — the parallel spawn site to add beside)
    - .planning/phases/V22-external-memory-docs-ingest/V22-RESEARCH.md Q1 (~L132-154, Option B), Q2 (~L156-185, spawn site), Open Question 1
    - tests/external_recall/test_agent_tool.py (test_agent_gets_external_hits)
  </read_first>
  <files>voss/harness/tools.py</files>
  <behavior>
    - test_agent_gets_external_hits: calling the agent `memory_recall` tool (with an ExternalRecallService bound and a populated fixture vault) returns output containing an external `[<name>]` hit alongside memory hits, and never raises
  </behavior>
  <action>
    **Spawn (Q2/D-18):** In `make_toolset`, after the CodeIndexService block (~L916), construct `ExternalRecallService(cwd, session_id=session_id)` inside a try/except (broad → None on failure, mirror the `_code_index_service` guard) and call `.ensure_background_build()` (no-op when zero sources declared — D-17 off-switch). Import lazily at top of the function or module-guarded like `_CodeIntelService` to keep session start non-blocking (Pitfall 2: the embedding cold-load stays inside the daemon).

    **Fan-out (Q1 Option B):** Extend `attach_memory_tools` to accept an optional keyword `external_service=None`. Inside `memory_recall`, after computing `hits = store.recall(...)`, if `external_service is not None` fan out `ext = external_service.query_all(query, top_k=top_k)` (guarded by try/except so external failure never breaks the turn — return memory hits alone on error), then `hits = MemoryStore._rrf_merge([hits, *ext], top_k=top_k)`. The existing `[{h.source}] {h.locator} (score ...)` formatter at L190 already renders `[<name>]` for external Hits — no formatter change. Keep `memory_remember` untouched.

    **Pass-through:** At the three `attach_memory_tools` call sites (do_cmd L1939, chat via _build_chat_ctx L2249, _extension_context L3466 — all in cli.py) the external service must reach `attach_memory_tools`. Since those sites are in cli.py and this plan owns only tools.py: make `external_service` an OPTIONAL kwarg defaulting to None (backward-compatible — existing call sites keep working untouched), and ALSO have `make_toolset` pass its constructed `external_service` when it calls `attach_memory_tools`. If `make_toolset` does not itself call `attach_memory_tools` (verify — the memory tools may be attached only at the cli.py sites), then expose the constructed service on the returned toolset/context in a way the test can bind it, and document in the SUMMARY that the cli.py call sites need the kwarg threaded in a follow-up (do NOT edit cli.py here — wave serialization). Prefer the path where `test_agent_gets_external_hits` constructs `attach_memory_tools(tools, store=..., session_id=..., external_service=ExternalRecallService(...))` directly — which the optional kwarg fully supports without any cli.py edit.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/external_recall/test_agent_tool.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    `.venv/bin/python -m pytest tests/external_recall/test_agent_tool.py -x -q` passes. `attach_memory_tools` accepts `external_service` (grep: `grep -c "external_service" voss/harness/tools.py` ≥ 2). `make_toolset` calls `ensure_background_build` for the external service (grep: `grep -c "ExternalRecallService" voss/harness/tools.py` ≥ 1). Existing tool tests green: `.venv/bin/python -m pytest tests/ -k "tool or toolset" -q` (no regression; kwarg is optional/backward-compatible).
  </acceptance_criteria>
  <done>memory_recall fuses external hits via _rrf_merge (Option B), [<name>] labels via existing formatter, ExternalRecallService spawned non-blocking from make_toolset, external_service kwarg optional+backward-compatible; agent-tool test GREEN.</done>
</task>

<task type="auto">
  <name>Task 2: Land the golden-query gate over the committed fixture vault (with + without chromadb)</name>
  <read_first>
    - tests/external_recall/test_golden_queries.py (the RED golden gate from V22-01)
    - tests/external_recall/conftest.py (indexed_fixture_vault, fake_embed_fn, chroma_disabled_env)
    - .planning/phases/V22-external-memory-docs-ingest/V22-RESEARCH.md Fixture Vault Design + golden queries (~L852-880)
  </read_first>
  <files>voss/harness/tools.py</files>
  <behavior>
    - test_golden_query (parametrized ~10 queries): each query returns its expected source file's `[<name>]` hit within top-5 of the fused result
    - test_golden_query_bm25: the same gate under chroma_disabled_env passes via BM25 degradation (no network, no OpenAI key)
  </behavior>
  <action>
    This task is GREEN-by-construction once Task 1 + V22-02/03 land — the golden gate exercises the full stack (chunk → index → query_all → RRF). Run the gate; if any of the ~10 queries miss top-5, the fix is in the FIXTURE VOCABULARY (tests/fixtures/recall_vault — owned by V22-01) or query phrasing, NOT a scope reduction. If a fixture-vocabulary adjustment is needed, note it precisely in the SUMMARY (the fixture files are V22-01-owned; a small vocab tweak there is acceptable as a golden-gate fix, but record it). The chromadb-absent variant must pass via BM25 — confirm `query_all` returns BM25 hits when `_maybe_semantic` is unavailable (V22-03 behavior). No new production code expected here beyond what Task 1 added; this task is the end-to-end VXMEM-08 proof.

    Do NOT add a `slow` marker (already registered, per VALIDATION). Do NOT require an OpenAI key (local sentence-transformers default / DefaultEmbeddingFunction in tests).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/external_recall/test_golden_queries.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    `.venv/bin/python -m pytest tests/external_recall/test_golden_queries.py -x -q` passes (all ~10 golden queries + the bm25 variant). The bm25 variant passes with chromadb disabled (no error, BM25 hits). Runs with no `OPENAI_API_KEY` set.
  </acceptance_criteria>
  <done>Golden-query gate GREEN over the committed fixture vault, with and without chromadb, no network/key; VXMEM-08 proven end-to-end.</done>
</task>

</tasks>

<verification>
- `.venv/bin/python -m pytest tests/external_recall/ -q` → FULL phase suite GREEN (all 23+ tests)
- `.venv/bin/python -m pytest tests/external_recall/ tests/code_recall/ tests/memory/ -q` → no cross-suite regression (per VALIDATION per-wave command)
- `.venv/bin/python -m pytest tests/external_recall/test_golden_queries.py -k "bm25" -q` → BM25 degradation gate GREEN
</verification>

<success_criteria>
Both VXMEM-07 surfaces are wired (CLI in V22-04, agent tool here via Option B) and the VXMEM-08 golden gate passes with and without chromadb. `tools.py` edited by this plan only. The full `tests/external_recall/` suite is GREEN.
</success_criteria>

<output>
Create `.planning/phases/V22-external-memory-docs-ingest/V22-05-SUMMARY.md` when done.
</output>
