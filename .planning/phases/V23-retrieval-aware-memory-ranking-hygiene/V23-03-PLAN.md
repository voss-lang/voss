---
phase: V23-retrieval-aware-memory-ranking-hygiene
plan: 03
type: execute
wave: 2
depends_on: ["V23-02"]
files_modified:
  - voss/harness/memory_store.py
autonomous: true
requirements: [VRNK-02]

must_haves:
  truths:
    - "A query matching nothing returns 0 hits (not top_k nearest-anything) with floors default-on"
    - "Chroma hits below similarity 0.25 are dropped before RRF fusion"
    - "BM25 hits below 10% of the query's top BM25 score are dropped before RRF fusion"
    - "Setting chroma_floor=0 and bm25_floor_ratio=0 restores pre-V23 fill behavior"
    - "Tiny-corpus token-overlap rescue path still functions under the relative floor"
  artifacts:
    - path: "voss/harness/memory_store.py"
      provides: "pre-fusion floor logic in _bm25_recall and _chroma_recall tails"
      contains: "bm25_floor_ratio"
  key_links:
    - from: "MemoryStore._bm25_recall"
      to: "_load_memory_config"
      via: "read bm25_floor_ratio before return"
      pattern: "bm25_floor_ratio"
    - from: "MemoryStore._chroma_recall"
      to: "_load_memory_config"
      via: "read chroma_floor before return"
      pattern: "chroma_floor"
---

<objective>
Implement VRNK-02 pre-fusion quality floors: each retriever drops low-quality hits BEFORE `_rrf_merge`, so junk no longer fills `top_k`. Chroma floor = absolute similarity 0.25 (D-04); BM25 floor = relative-to-top ratio 0.1 (D-05). Default-on, config-overridable under `[memory]`, with a disable knob restoring pre-V23 fill.

Purpose: Low-relevance hits burn injected tokens (works against V18's ceiling). Floors apply per-retriever per-store pre-fusion only (D-06) — a post-fusion floor would punish BM25-only degraded installs.
Output: floor logic inserted at the tails of `_bm25_recall` and `_chroma_recall`; `_rrf_merge` (staticmethod) untouched.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-SPEC.md
@.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-CONTEXT.md
@.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-PATTERNS.md

<interfaces>
From voss/harness/memory_store.py (confirmed):
- @staticmethod def _rrf_merge(rankings, *, top_k, k=60) -> list[Hit]  # line 431 — NEVER read config here (staticmethod)
- def _chroma_recall(self, chroma, query, *, top_k, source) -> list[Hit]  # line 447; chroma score = max(0.0, 1.0 - float(dist)) at ~line 470; return at ~483
- def _bm25_recall(self, ...) -> list[Hit]  # line 530; token-overlap rescue at ~555; ranked.sort + return at ~575-576
- def _load_memory_config(self) -> dict  # line 205 — call in instance methods only
- def recall(...)  # line 411 — calls _rrf_merge over the two floored lists
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: BM25 relative-to-top floor at _bm25_recall tail</name>
  <read_first>
    - voss/harness/memory_store.py:530-576 (_bm25_recall full body — token-overlap rescue at ~555, ranked.sort + return at ~575)
    - V23-RESEARCH.md:262-293 (Pattern 2 floors — BM25 floor position + key property), :589-593 (Pitfall 4: BM25 relative floor with zero-score corpus)
    - V23-PATTERNS.md:173-186 (BM25 floor insertion code), :594-600 (config key access pattern)
    - V23-CONTEXT.md D-05 (relative-to-top ratio 0.1; preserve tiny-corpus token-overlap rescue), D-06 (per-retriever pre-fusion only)
  </read_first>
  <behavior>
    - Query with one strong + several weak BM25 matches → weak matches below 10% of top score dropped
    - bm25_floor_ratio=0 in config → all positive-score rows retained (pre-V23 fill)
    - Empty ranked list → returns empty (no crash)
    - All-zero / zero-top scores → floor NOT applied (guard top_score > 0) so no accidental pass-everything; existing score-≤-0 filter already removes 0-score rows upstream
    - Tiny-corpus token-overlap rescue rows (positive integer scores) participate correctly in the relative comparison
  </behavior>
  <action>
    Insert the floor immediately before the existing `return [hit for _, hit in ranked[:top_k]]` at the tail of `_bm25_recall` (~line 576). Read `cfg = self._load_memory_config()` and `bm25_floor_ratio = float(cfg.get("bm25_floor_ratio", 0.1))`. Apply ONLY when `ranked and ranked[0][0] > 0 and bm25_floor_ratio > 0` (Pitfall 4 guard — relative floor with zero top would pass everything). When applied: `top_score = ranked[0][0]`; keep `(s, h)` pairs where `s >= top_score * bm25_floor_ratio`. Default 0.1 = keep ≥10% of top. Do not alter the upstream token-overlap rescue (~line 555) — it produces positive scores that survive the relative comparison naturally (D-05). Disable knob: `bm25_floor_ratio=0` skips the filter.
  </action>
  <acceptance_criteria>
    - `grep -c 'bm25_floor_ratio' voss/harness/memory_store.py` >= 1, inside _bm25_recall (not in _rrf_merge)
    - Floor guarded by `ranked[0][0] > 0` (grep: `grep -n 'ranked\[0\]\[0\] > 0' voss/harness/memory_store.py` returns a line)
    - BM25 floor tests pass: `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "floor and bm25" -q` GREEN (or `-k floor` if bm25 not a separate keyword)
    - `_rrf_merge` body unchanged (grep: no `_load_memory_config` call between `def _rrf_merge` and the next `def`)
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k floor -q 2>&1 | tail -5</automated>
  </verify>
  <done>BM25 relative-to-top floor applied pre-fusion with zero-top guard; disable knob works; token-overlap rescue intact.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Chroma absolute similarity floor at _chroma_recall tail + no-match returns 0</name>
  <read_first>
    - voss/harness/memory_store.py:447-483 (_chroma_recall — score = max(0.0, 1.0 - float(dist)) at ~470, return at ~483)
    - V23-RESEARCH.md:280-293 (chroma floor position + score mapping), :583-587 (Pitfall 3: DefaultEmbeddingFunction — tests use chroma_disabled_env)
    - V23-PATTERNS.md:188-201 (chroma floor insertion code)
    - V23-CONTEXT.md D-04 (absolute similarity, default 0.25; froots 0.45 rejected), D-06 (pre-fusion per-retriever)
    - V23-SPEC.md VRNK-02 acceptance (no-match query → 0 hits, not top_k nearest-anything)
  </read_first>
  <behavior>
    - Chroma hits with score (= 1 - distance) < 0.25 dropped before return
    - chroma_floor=0 → all chroma nearest neighbors retained (pre-V23)
    - A query matching nothing → both retrievers floor to empty → recall returns 0 hits (the no-match acceptance criterion)
    - chroma absent (chroma_disabled_env) → floor code never reached; BM25-only path still respects its own floor
  </behavior>
  <action>
    Insert the floor immediately before the `return out` at the tail of `_chroma_recall` (~line 483). Read `cfg = self._load_memory_config()` and `chroma_floor = float(cfg.get("chroma_floor", 0.25))`. When `chroma_floor > 0`, keep only `h` in `out` where `h.score >= chroma_floor` (score is already the `max(0.0, 1.0 - dist)` similarity). Default 0.25 (D-04 — NOT froots' 0.45). Disable knob: `chroma_floor=0` retains all. Confirm the combined effect: with both floors on, a junk query that produces no BM25 hits above floor and no chroma hits above floor yields 0 fused hits (VRNK-02 no-match acceptance — the floor tests in the scaffold assert this). Do not touch `_rrf_merge`.
  </action>
  <acceptance_criteria>
    - `grep -c 'chroma_floor' voss/harness/memory_store.py` >= 1, inside _chroma_recall
    - No-match-returns-zero test passes: `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "no_match or floor" -q` GREEN
    - Disable-knob test passes: floors=0 restores fill (covered under `-k floor`)
    - All VRNK-02 floor tests GREEN: `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k floor -q`
    - Existing memory store/recall tests stay green: `.venv/bin/python -m pytest tests/harness/test_memory_store.py -q`
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k floor -q tests/harness/test_memory_store.py -q 2>&1 | tail -6</automated>
  </verify>
  <done>Chroma absolute floor applied pre-fusion; no-match query returns 0 hits; disable knob restores fill; existing recall tests green; all VRNK-02 tests GREEN.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| config.yml → floor values | operator-set float thresholds read from local [memory] config |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V23-03-01 | Tampering | malformed config value (non-float chroma_floor) | mitigate | float(cfg.get(..., default)) with default fallback; _load_memory_config already returns {} on parse failure |
| T-V23-03-02 | Denial of Service | over-aggressive floor returns 0 hits for valid queries | accept | conservative defaults (0.25 / 0.1) chosen per D-04/D-05; disable knob (=0) documented; quality eval deferred to E-track |
| T-V23-03-SC | Tampering | npm/pip/cargo installs | accept | No installs; zero new packages (RESEARCH audit) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k floor -q` GREEN
- `.venv/bin/python -m pytest tests/harness/test_memory_store.py -q` GREEN (no recall regression)
- `_rrf_merge` staticmethod body unchanged (no config read inside it)
</verification>

<success_criteria>
VRNK-02 GREEN; floors pre-fusion per-retriever; no-match → 0 hits; disable knob restores fill; BM25-only degradation respects BM25 floor; _rrf_merge untouched.
</success_criteria>

<output>
Create `.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-03-SUMMARY.md` when done.
</output>
