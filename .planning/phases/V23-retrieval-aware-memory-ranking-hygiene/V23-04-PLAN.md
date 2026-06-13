---
phase: V23-retrieval-aware-memory-ranking-hygiene
plan: 04
type: execute
wave: 3
depends_on: ["V23-02", "V23-03"]
files_modified:
  - voss/harness/memory_store.py
autonomous: true
requirements: [VRNK-03]

must_haves:
  truths:
    - "With rescore enabled, fused scores receive a deterministic recency×frequency boost from telemetry"
    - "With rescore disabled (default), recall output is byte-identical to the pre-V23 path"
    - "Empty telemetry + rescore on = no-op (identical ordering)"
    - "A fixed telemetry fixture produces a deterministic, asserted re-ranking"
  artifacts:
    - path: "voss/harness/memory_store.py"
      provides: "_rescore method + config-gated rescore hook after _rrf_merge in recall()"
      contains: "def _rescore"
  key_links:
    - from: "MemoryStore.recall"
      to: "_rescore"
      via: "config-gated call on _rrf_merge output"
      pattern: "if cfg.get\\(.rescore"
    - from: "MemoryStore._rescore"
      to: "_load_telemetry_compacted"
      via: "boost derived from per-locator count + last_retrieved"
      pattern: "_load_telemetry_compacted"
---

<objective>
Implement VRNK-03 recency×frequency rescore: a config-gated, deterministic multiplicative boost on `_rrf_merge` output, defaulting OFF. The hard gate is the off-path being byte-identical to pre-V23 (no extra sort, no copy when disabled). Empty telemetry + rescore-on must be a no-op.

Purpose: Telemetry (VRNK-01) becomes useful ranking signal — hot memories rise — while the off-by-default contract guarantees zero behavior change for existing installs. Quality eval is deferred to E-track; the V23 bar is determinism + byte-identical off-path.
Output: `_rescore` method + a config-gated hook in `recall()` after `_rrf_merge`.
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
- def recall(...) at line 411 — current final line: return self._rrf_merge([bm25_hits, chroma_hits], top_k=top_k)
- def _load_telemetry_compacted(self) -> dict  # added in V23-02 → {locator: {count, last_retrieved}}
- def _load_memory_config(self) -> dict  # line 205
- class Hit (dataclass) — use dataclasses.replace to produce a boosted copy (score field)
- `import dataclasses`, `import math` (add math if absent — stdlib, no install)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: _rescore method (deterministic recency×frequency boost)</name>
  <read_first>
    - voss/harness/memory_store.py:1-25 (imports — add `import math` if absent), :411-428 (recall body)
    - V23-RESEARCH.md:297-355 (Pattern 3 rescore formula — recommended weights, byte-identical guarantee), :595-599 (Pitfall 5: missing last_retrieved → recency 0.0)
    - V23-CONTEXT.md D-13 (Claude's discretion: multiplicative boost = exp recency decay ~7d half-life + log-scaled frequency, both weight-configurable, bounded so similarity dominates; deterministic under fixture; empty-telemetry no-op; off = byte-identical)
    - V23-RESEARCH.md:656-669 (new [memory] config keys: rescore, rescore_half_life_days 7.0, rescore_w_recency 0.3, rescore_w_freq 0.2, rescore_freq_scale 10.0)
  </read_first>
  <behavior>
    - Empty telemetry → _rescore returns the input list unchanged (no-op identical ordering)
    - Fixed telemetry fixture (e.g. locator A count=10 fresh ts, locator B count=0) → A boosted above B deterministically; the scaffold's deterministic test asserts the exact resulting order
    - Locator with telemetry entry but missing last_retrieved → recency factor 0.0 (no crash, Pitfall 5)
    - boost is bounded in [1.0, 1 + w_recency + w_freq] so similarity ordering dominates
    - Same input + same telemetry → identical output every call (deterministic; tie-break by locator)
  </behavior>
  <action>
    Add `import math` to imports if not present (stdlib; RESEARCH §Standard Stack). Add `_rescore(self, hits: list[Hit], cfg: dict) -> list[Hit]`:
    - Load `telemetry = self._load_telemetry_compacted()`; if empty, `return hits` (no-op — SPEC empty-telemetry constraint).
    - Read weights from cfg with defaults: `rescore_half_life_days` 7.0, `rescore_freq_scale` 10.0, `rescore_w_recency` 0.3, `rescore_w_freq` 0.2 (D-13 recommended).
    - For each hit: look up telemetry[hit.locator]. If absent → boost 1.0. Else: `count = int(entry["count"])`; if `last_retrieved` present, `days_ago = max(0.0, (now - fromisoformat(last_ts)).total_seconds()/86400)` and `recency = exp(-days_ago / max(half_life, 0.001))`, else `recency = 0.0` (Pitfall 5 guard). `freq = log1p(count) / log1p(max(freq_scale, 1.0))`. `boost = 1.0 + w_recency*recency + w_freq*min(freq, 1.0)`. Append `dataclasses.replace(hit, score=hit.score * boost)`.
    - Sort rescored by `(-score, locator)` for deterministic tie-breaking. Return.
    Keep the formula self-contained and pure (no filesystem writes). `now = datetime.now(timezone.utc)` — for the deterministic fixture test the scaffold controls telemetry timestamps relative to now, so determinism holds within a run.
  </action>
  <acceptance_criteria>
    - `grep -c 'def _rescore' voss/harness/memory_store.py` == 1
    - `import math` present: `grep -c '^import math' voss/harness/memory_store.py` >= 1
    - Deterministic + empty-telemetry no-op tests pass: `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "rescore and (deterministic or noop or empty)" -q` GREEN (or `-k rescore` if subnames differ)
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k rescore -q 2>&1 | tail -5</automated>
  </verify>
  <done>_rescore produces deterministic recency×frequency re-ranking; empty telemetry is a no-op; missing last_retrieved handled.</done>
</task>

<task type="auto">
  <name>Task 2: Config-gated rescore hook in recall() + byte-identical off-path</name>
  <read_first>
    - voss/harness/memory_store.py:411-428 (recall body — final _rrf_merge return)
    - V23-RESEARCH.md:299-308 (rescore hook placement after _rrf_merge), :355 (byte-identical guarantee — off path returns _rrf_merge output directly, no extra sort/copy)
    - V23-PATTERNS.md:151-171 (recall() rescore hook comment block), :477-505 (byte-identical test analog test_no_pack_byte_identical)
    - tests/harness/test_agent_packing.py:202-208 (byte-identical assertion pattern)
    - V23-SPEC.md VRNK-03 + VRNK-08 (rescore-off byte-identical is a HARD regression gate)
  </read_first>
  <action>
    In `recall()`, replace the final `return self._rrf_merge(...)` with: compute `fused = self._rrf_merge([bm25_hits, chroma_hits], top_k=top_k)`; then `cfg = self._load_memory_config()`; `if cfg.get("rescore", False): fused = self._rescore(fused, cfg)`; `return fused`. CRITICAL byte-identical guarantee: when `rescore` is False (the default), the code path must produce a result indistinguishable from the pre-V23 `return self._rrf_merge(...)` — no extra sort, no list copy, no Hit mutation. The single added `_load_memory_config()` read and the `if` branch are acceptable since they do not touch `fused` when disabled. The early-return BM25-only branch (chroma is None) keeps its existing `return bm25_hits[:top_k]` and is also rescore-eligible only via this final hook — confirm the chroma-absent path also routes through the hook OR document that rescore is fusion-output-only (RESEARCH places the hook on the fused path; BM25-only degraded path may stay un-rescored — assert the scaffold's byte-identical test covers the default-off case which is what matters for VRNK-08).
    Verify the byte-identical scaffold test (`test_rescore_off_byte_identical`) passes: default-config recall output (locator order + scores + excerpts) equals a captured baseline. This is the hard gate.
  </action>
  <acceptance_criteria>
    - `grep -c 'if cfg.get("rescore"' voss/harness/memory_store.py` >= 1 (hook present)
    - Byte-identical off-path test passes: `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k byte_identical -q` GREEN
    - All VRNK-03 rescore tests GREEN: `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k rescore -q`
    - Existing recall/floor tests stay green: `.venv/bin/python -m pytest tests/harness/test_memory_store.py -q` and `tests/memory/test_retrieval_ranking.py -k floor`
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "rescore or byte_identical or floor" -q tests/harness/test_memory_store.py -q 2>&1 | tail -6</automated>
  </verify>
  <done>Rescore hook config-gated default-off; off-path byte-identical to pre-V23 (hard gate green); all VRNK-03 tests GREEN; no recall/floor regression.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| telemetry sidecar → rescore | compacted counts/timestamps influence ranking scores |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V23-04-01 | Tampering | corrupt last_retrieved crashes datetime.fromisoformat | mitigate | guard `if last_ts:` → recency 0.0 (Pitfall 5); compacted reader already corrupt-line tolerant |
| T-V23-04-02 | Elevation of Privilege | rescore boost overrides similarity ordering (ranking manipulation via inflated counts) | accept | boost bounded [1.0, 1+w_recency+w_freq] so similarity dominates (D-13); rescore default-OFF; manual config opt-in only |
| T-V23-04-SC | Tampering | npm/pip/cargo installs | accept | No installs; math is stdlib (RESEARCH audit) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "rescore or byte_identical" -q` GREEN
- `.venv/bin/python -m pytest tests/harness/test_memory_store.py -q` GREEN
- Off-path byte-identical baseline locked
</verification>

<success_criteria>
VRNK-03 GREEN; deterministic re-ranking under fixture; rescore-off byte-identical (hard gate); empty-telemetry no-op; bounded boost.
</success_criteria>

<output>
Create `.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-04-SUMMARY.md` when done.
</output>
