---
phase: V18-budget-aware-context-allocator-token-optimization
plan: 02
type: execute
wave: 2
depends_on: ["V18-01-budget-aware-context-allocator-token-optimization"]
files_modified:
  - voss/harness/context_allocator.py
autonomous: true
requirements: [VOPT-01, VOPT-02, VOPT-03, VOPT-04]
must_haves:
  truths:
    - "ContextAllocator.pack() is a pure function of (iter_records, packing_budget, profile) — no provider call, no filesystem access, token estimation injected as a callable"
    - "The FULL tier calls agent._serialize_iter_for_replay directly (no re-implementation), so the newest K iterations replay byte-identically to pre-V18"
    - "With <= recent_full_k iterations pack() output equals the verbatim full-replay list (no-op below threshold)"
    - "Older iterations render as one-line structural digests (K..M) and a single folded 'Earlier work' block (>M); the newest iteration is always full"
    - "Total estimated tokens are strictly <= full replay and the stable region is append-only across turns until the high-water mark is crossed (hysteresis), at which point one recompaction fires"
    - "Folded iterations whose tool_results referenced files/symbols emit a deduped, capped re-fetch pointer naming code_search/find_definition — structural text only, no async retrieval call"
  artifacts:
    - path: "voss/harness/context_allocator.py"
      provides: "Pure ContextAllocator class + PackingProfile dataclass + tiered render + hysteresis + eviction pointers"
      exports: ["ContextAllocator", "PackingProfile"]
      contains: "class ContextAllocator"
      min_lines: 140
  key_links:
    - from: "voss/harness/context_allocator.py"
      to: "voss.harness.agent._serialize_iter_for_replay"
      via: "FULL tier delegates to the existing renderer (preserves telemetry.redact_tool_args + 400-char cap)"
      pattern: "_serialize_iter_for_replay"
    - from: "voss/harness/context_allocator.py"
      to: "injected token_count callable"
      via: "estimation at every tier boundary; no second tokenizer"
      pattern: "self._token_count"
---

<objective>
Build the pure `ContextAllocator` (VOPT-01): a provider-free, filesystem-free packer that renders the variable replay region under a token ceiling using three age tiers (VOPT-02), holds a stable append-only packing across turns with hysteresis-gated recompaction (VOPT-03 pure mechanics), and emits machine-actionable re-fetch pointers for folded detail (VOPT-04). No agent.py wiring in this plan — the allocator is a standalone, unit-tested module.

Purpose: Isolating the allocator as a pure module makes the load-bearing invariants (packed <= full, byte-identical below threshold, stable-region append-only) unit-provable without a live provider, and prevents the cache-coherence logic from tangling with the agent loop.

Output: `voss/harness/context_allocator.py` turning the RED allocator tests from Plan 01 GREEN.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-SPEC.md
@.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-RESEARCH.md
@.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-PATTERNS.md

<interfaces>
<!-- Targets the RED tests in tests/harness/test_context_allocator.py (Plan 01). -->

To CREATE — voss/harness/context_allocator.py:
  @dataclass class PackingProfile:
      recent_full_k: int = 8      # conservative default: last 8 iters full
      digest_cutoff_m: int = 20   # iters 8..20 digest; >20 fold
      high_water: float = 0.80    # recompact when est usage >= 80% of packing_budget
      low_water: float = 0.60     # hold until <= 60%
      enabled: bool = True
  class ContextAllocator:
      def __init__(self, token_count): ...                 # token_count: Callable[[str], int], injected (no agent import cycle)
      def pack(self, iter_records, packing_budget, profile) -> list[tuple[dict, dict]]: ...
      def stable_region_hash(self) -> str: ...             # SHA-256 of stable (non-recompacted) pairs

REUSE read-only — voss/harness/agent.py (VERIFIED line numbers):
  _serialize_iter_for_replay(iter_rec) -> tuple[dict,dict]   # :431-460 — FULL tier; redacts args via telemetry.redact_tool_args; 400-char cap at :454-455
  _build_iter_rider digest line format                        # :418-427 — "Iter {i}: {steps} steps, {tools} tools, {snippet[:60]}"
  _default_token_count(text, *, model)                        # :73-80 — NOTE: do NOT import this directly into the allocator; the caller (Plan 03) injects a partial so the allocator stays pure/testable

REUSE read-only — IterationRecord shape (session.py:99-115):
  index: int; plan: dict; tool_results: list[dict]; cache_read_input_tokens: int
  tool_results entries are dicts with keys name/args/result; args is a dict carrying e.g. path/file/pattern/symbol
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: PackingProfile + tiered render (FULL / DIGEST / FOLD) with eviction pointers</name>
  <read_first>
    - voss/harness/agent.py:431-460 (_serialize_iter_for_replay — the FULL tier; call it directly, do NOT re-implement; note telemetry.redact_tool_args at :453 and the 400-char caps)
    - voss/harness/agent.py:413-428 (_build_iter_rider digest line format to mirror for the DIGEST tier)
    - voss/harness/session.py:99-115 (IterationRecord fields: index/plan/tool_results)
    - voss/harness/code/service.py (CodeIntelService.search/find_definition signatures — the pointer text names these tools; NO call, just hint text)
    - .planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-PATTERNS.md (context_allocator.py section: imports pattern, digest-tier copy, eviction-pointer extraction at PATTERNS lines 127-141)
    - tests/harness/test_context_allocator.py (the RED tests this task turns GREEN — match their expected substrings)
  </read_first>
  <behavior>
    - FULL tier: for the last `recent_full_k` iters, render via agent._serialize_iter_for_replay — output byte-identical to pre-V18.
    - DIGEST tier (iters recent_full_k .. digest_cutoff_m): one (assistant, user) pair carrying counts + first/last tool names + snippet[:120]; assistant content includes the literal "[digest]" marker so test_tier_boundaries_golden_render can assert it.
    - FOLD tier (older than digest_cutoff_m): a SINGLE (assistant, user) pair summarizing the index range + union of tool names; if any folded iter's tool_results args carry path/file or pattern/symbol, append re-fetch pointers (each containing "re-fetch" + 'code_search("<path>")' or 'find_definition("<symbol>")'), deduped via dict.fromkeys, capped at 5.
    - NEWEST iter is always in the FULL tier regardless of count.
    - packed total tokens (via injected token_count) is strictly <= full-replay total for any input; degenerate short histories never exceed full (Pitfall 4 — if a tier would inflate, prefer full rendering for that span).
  </behavior>
  <action>
    Create voss/harness/context_allocator.py. Module header: `from __future__ import annotations`, stdlib only (`hashlib`, `json`, `dataclasses.dataclass/field`, `typing.Any/Callable`). NO provider import, NO pathlib/os/open, NO direct `_default_token_count` import (accept a `token_count` callable in __init__ for purity — Plan 03 injects `functools.partial(_default_token_count, model=model)`).
    Define `PackingProfile` dataclass with the defaults in <interfaces>. Define `ContextAllocator.__init__(self, token_count)` storing `self._token_count = token_count` and initializing stable-region state to empty.
    Implement the FULL tier by importing and calling `from voss.harness.agent import _serialize_iter_for_replay` ONLY inside the render method (lazy import is acceptable to avoid a top-level cycle; document why). Do not re-implement its body — RESEARCH Pitfall 2 and the byte-identity test depend on delegation.
    Implement `_render_iter_digest(iter_rec) -> tuple[dict,dict]` mirroring the agent.py:418-427 line format (step_count, tool_count, snippet from final_when_done or rationale, replace newlines, cap 120), assistant content prefixed `[digest] Iter {index}:`.
    Implement `_render_fold_summary(iter_recs) -> list[tuple[dict,dict]]` producing the single folded pair + eviction pointers extracted from tr["args"]["path"|"file"|"pattern"|"symbol"] (PATTERNS lines 127-141), deduped + capped at 5; return [] for empty input.
    Implement `_build_eviction_pointer(tr) -> str | None` returning `'↻ re-fetch via code_search("<path>")'` when a path is present, else `'↻ re-fetch via find_definition("<symbol>")'` when a symbol is present, else None.
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/harness/test_context_allocator.py -k "tier_boundaries_golden_render or eviction_pointer or below_threshold_byte_identical" -x` exits 0.
    - `.venv/bin/python -c "import ast,sys; src=open('voss/harness/context_allocator.py').read(); t=ast.parse(src); mods=[n.module for n in ast.walk(t) if isinstance(n,ast.ImportFrom)]; assert not any(m and ('provider' in m or m in ('os','pathlib') ) for m in mods), mods"` exits 0 (no provider/os/pathlib import at module level).
    - `grep -n "_serialize_iter_for_replay" voss/harness/context_allocator.py` shows the FULL tier delegates (does not re-implement).
    - `grep -Ec "chromadb|faiss|annoy|embedding|sentence_transformers|numpy" voss/harness/context_allocator.py` returns 0 (VOPT-04: no index/embedding/vector dependency).
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_context_allocator.py -k "tier_boundaries_golden_render or eviction_pointer or below_threshold_byte_identical" -x -q</automated>
  </verify>
  <done>Tiered render GREEN for the three tier/eviction/byte-identity tests; FULL tier delegates to _serialize_iter_for_replay; no provider/os/pathlib/embedding imports; eviction pointers deduped + capped at 5.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: pack() budget fitting + hysteresis stable-region (VOPT-01/03 pure)</name>
  <read_first>
    - voss/harness/context_allocator.py (the module from Task 1 — extend it)
    - voss/harness/agent.py:73-80 (_default_token_count contract — the injected callable mirrors this signature minus the keyword model, which Plan 03 binds)
    - .planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-RESEARCH.md (Pattern 3 hysteresis: high-water recompact / low-water hold; stable_region_hash = SHA-256 of serialized stable pairs; Pitfall 1 per-turn-rewrite-defeats-cache)
    - .planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-PATTERNS.md (stable-region hysteresis hash snippet at PATTERNS lines 119-125)
    - tests/harness/test_context_allocator.py (test_pack_50_iters_under_ceiling, test_packed_tokens_never_exceed_full, test_stable_region_append_only, test_recompaction_on_high_water, test_allocator_pure — match their expectations)
  </read_first>
  <behavior>
    - pack(iter_records, packing_budget, profile): when len(iter_records) <= profile.recent_full_k, return the verbatim full-replay list (FULL for all) — byte-identical, no digest/fold overhead.
    - Otherwise assemble FULL (last K) + DIGEST (K..M) + FOLD (>M), estimating each pair's tokens via self._token_count; drop oldest digest/fold content as needed so the summed estimate <= packing_budget; the newest iter is never dropped.
    - Hysteresis: the allocator carries `self._stable_pairs` across calls within one run. On each pack(): if estimated usage < profile.high_water * packing_budget, EXTEND the stable region append-only (keep prior boundaries, append newly-full iters) and do NOT recompute boundaries. If estimated usage >= high_water * packing_budget, RECOMPACT (recompute tiers from scratch) and reset the stable region; hold the new boundaries until usage <= low_water.
    - stable_region_hash() returns SHA-256 of json.dumps(stable pairs, sort_keys=True) — unchanged turn-over-turn while below high_water, changes exactly once on a high-water crossing.
    - pack() touches no provider and no filesystem (test_allocator_pure asserts this).
  </behavior>
  <action>
    Extend voss/harness/context_allocator.py. Implement `pack(self, iter_records, packing_budget, profile)`:
    - Early return the full-replay list when len(iter_records) <= profile.recent_full_k.
    - Build tier spans by index position; render FULL via the delegated renderer, DIGEST via _render_iter_digest, FOLD via _render_fold_summary.
    - Greedily fit: estimate total via sum(self._token_count(m["content"]) for pair in pairs for m in pair); if over packing_budget, shrink from the oldest end (move more iters into the single fold, then trim the fold's eviction block) until <= budget; never trim the newest full iter.
    - Maintain `self._stable_pairs` and `self._recompactions` (int counter). Implement the high/low-water hysteresis exactly as in <behavior>. Compute the high-water test against the rendered estimate, not the raw budget.
    - Implement `stable_region_hash()` per PATTERNS lines 119-125.
    Keep everything pure: no `open`, no `Path`, no `requests`/provider. The only inputs are the args and self state.
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/harness/test_context_allocator.py -x -q` exits 0 (ALL allocator unit tests GREEN, including pure/ceiling/append-only/recompaction).
    - `.venv/bin/python -m pytest tests/harness/test_context_allocator.py::test_allocator_pure tests/harness/test_context_allocator.py::test_pack_50_iters_under_ceiling tests/harness/test_context_allocator.py::test_packed_tokens_never_exceed_full -x` exits 0.
    - `.venv/bin/python -m pytest tests/harness/test_context_allocator.py::test_stable_region_append_only tests/harness/test_context_allocator.py::test_recompaction_on_high_water -x` exits 0 (hysteresis proven: stable hash unchanged below high-water, one recompaction at the crossing).
    - `grep -Ec "open\(|pathlib|import os\b|requests|provider" voss/harness/context_allocator.py` returns 0.
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_context_allocator.py -x -q</automated>
  </verify>
  <done>Entire allocator unit suite GREEN; pack() respects the ceiling, returns byte-identical below threshold, and the stable-region hash is append-only with exactly one recompaction at the high-water crossing; module is pure (no fs/provider).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| iter_records → rendered replay | Tool-result args may contain secrets; the FULL tier must preserve T4's redaction so packing never re-leaks what redaction stripped |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V18-03 | Information disclosure (secret re-leak) | FULL/DIGEST/FOLD renderers | mitigate | FULL tier delegates to agent._serialize_iter_for_replay which calls telemetry.redact_tool_args (agent.py:453); DIGEST/FOLD emit only counts, tool NAMES, paths, and snippet[:120] from plan rationale/final_when_done — never raw `result` strings or unredacted args. Eviction pointers carry only the path/symbol identifier, not file contents. |
| T-V18-04 | Tampering (phantom savings) | pack() budget fitting | mitigate | pack() guarantees packed <= full by construction (Pitfall 4 fallback to full rendering when a tier would inflate); the never-exceed-full invariant is unit-asserted (test_packed_tokens_never_exceed_full) |
| T-V18-05 | Tampering (cache defeat) | hysteresis stable region | mitigate | Stable region is append-only below high-water (Pitfall 1); recompaction only at threshold; stable_region_hash unit-asserted unchanged turn-over-turn so per-turn rewriting that would defeat T4 caching is caught |
| T-V18-SC | Tampering | npm/pip/cargo installs | accept | No new packages (RESEARCH Package Legitimacy Audit: litellm only, already in venv); allocator is stdlib-only. No install task. |
</threat_model>

<verification>
- Full allocator unit suite GREEN: `.venv/bin/python -m pytest tests/harness/test_context_allocator.py -x -q`.
- Module is pure: no `open`/`pathlib`/`os`/`provider`/embedding imports (grep gates above).
- FULL tier delegates to `_serialize_iter_for_replay` (redaction preserved); DIGEST/FOLD never emit raw `result` strings.
- Stable-region hash is append-only below high-water; exactly one recompaction at the crossing.
</verification>

<success_criteria>
- `voss/harness/context_allocator.py` exists, >= 140 lines, exports `ContextAllocator` + `PackingProfile`.
- All allocator unit tests from Plan 01 are GREEN.
- No provider, no filesystem, no index/embedding/vector dependency anywhere in the module.
- The newest iteration is always rendered full; packed <= full for every input; below-threshold output is byte-identical to the verbatim full replay.
</success_criteria>

<output>
Create `.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-02-SUMMARY.md` when done.
</output>
