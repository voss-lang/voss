---
phase: V23-retrieval-aware-memory-ranking-hygiene
plan: 06
type: execute
wave: 5
depends_on: ["V23-05", "V23-02"]
files_modified:
  - voss/harness/memory_store.py
  - voss/harness/agent.py
  - voss/harness/cli.py
autonomous: true
requirements: [VRNK-06]

must_haves:
  truths:
    - "Pinned memory text appears in the assembled agent context for a query that would never recall it"
    - "Pinned block rides the V18 variable region as a non-evictable fixed-cost item (not the FOLD-only stable region)"
    - "Pin tier capped at ~500 tok total, ~200 tok soft cap per item; overflow keeps newest-pinned and warns"
    - "Pinned files survive an over-quota purge"
  artifacts:
    - path: "voss/harness/memory_store.py"
      provides: "pinned_memory_text renderer (full text per pin, per-item + tier token caps)"
      contains: "pin_cap_tokens"
    - path: "voss/harness/agent.py"
      provides: "pinned_memory_text param threaded through _compose_system_blocks + run_turn"
      contains: "pinned_memory_text"
    - path: "voss/harness/cli.py"
      provides: "_pinned_memory_kwargs signature-guard splat at run_turn call sites"
      contains: "pinned_memory_text"
  key_links:
    - from: "voss/harness/agent.py::_compose_system_blocks"
      to: "variable region block list"
      via: "pinned_memory_text added in same slot as code_recall_text"
      pattern: "pinned_memory_text"
    - from: "voss/harness/cli.py"
      to: "run_turn"
      via: "inspect.signature-guarded kwarg splat"
      pattern: "_pinned_memory_kwargs"
---

<objective>
Implement VRNK-06 pinned tier: operator-pinned memories always inject into agent context (without competing through recall), prepended inside the existing V18/V19 variable region as a non-evictable fixed-cost item (D-07 — NOT the FOLD-only stable region), capped at ~500 tok tier / ~200 tok per item with newest-wins overflow + warning (D-08). Pinned files are already eviction-exempt (V23-05).

Purpose: A must-never-miss convention can simply lose the ranking today. Pins guarantee presence with honest token accounting inside the existing ceiling (no new region type, no second budget).
Output: pin-text renderer on MemoryStore; `pinned_memory_text` param threaded through agent.py compose/run_turn; signature-guarded kwarg splat at cli.py run_turn call sites (compiled-loop compat).
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
From voss/harness/agent.py (confirmed):
- def _default_token_count(text, *, model) -> int  # line 83 — pin cap accounting
- def _compose_system_blocks(*, voss_md_block, cognition_text, principles_text="", project_index_text="", code_recall_text="", prior_context_text, loop_system) -> list[dict]  # line 373; code_recall_text added to block tuple at ~396
- async def run_turn(..., code_recall_text: str = "", ...)  # line 505; threads code_recall_text=... into _compose_system_blocks at ~577

From voss/harness/cli.py (confirmed):
- def _code_recall_kwargs(run_turn_fn, cwd, task_text, session_id=None) -> dict  # line 841 — inspect.signature guard idiom to COPY
- run_turn call sites: do_cmd ~1938 region, chat run_turn sites (use _code_recall_kwargs splat pattern)

From voss/harness/memory_store.py:
- def _load_pins(self) -> set[str]  # V23-05
- _pins_path / .pins.json schema {"pins":[{locator, pinned_at}]}  # V23-05
- text retrieval for a locator: derive from the source file (notes/conventions/decisions); reuse existing read helpers — full body per pin (D-08, no excerpt truncation)

V18 constraint: stable region = FOLD-only (memory: voss V18). Pin block → VARIABLE region (same slot as code_recall_text).
Compiled loop.voss run_turn may lack the new param → signature-guard splat (memory: voss V18 compiled loop.py gotcha).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Pinned-text renderer on MemoryStore (full text, token caps, overflow warn)</name>
  <read_first>
    - voss/harness/memory_store.py — _load_pins (V23-05), _pins_path schema, existing source-file read paths + _locator_from_path:628
    - voss/harness/agent.py:83 (_default_token_count — import + use for cap accounting)
    - V23-RESEARCH.md:474-509 (Pattern 6 pinned tier — .pins.json format, pin load, token accounting), :660-669 (config keys: pin_cap_tokens 500, pin_item_cap_tokens 200)
    - V23-PATTERNS.md:573-576 (V18 stable-region constraint — variable region only)
    - V23-CONTEXT.md D-07 (non-evictable allocator item, variable region, cap inside ceiling), D-08 (full text, per-item ~200 tok soft cap, tier ~500 tok), D-09 (global pins project-priority on overflow — STUB the global path; wire post-V21)
  </read_first>
  <behavior>
    - render_pinned_memory_text() returns a single text block containing the FULL body of each pinned memory (no 200-char excerpt truncation — D-08)
    - Per-item soft cap ~200 tok (pin_item_cap_tokens): an over-long single pin is soft-capped per item
    - Tier cap ~500 tok total (pin_cap_tokens): when combined pinned bodies exceed the cap, keep newest-pinned (by pinned_at desc), drop oldest, and emit a stderr/log warning
    - No pins → returns "" (empty → no kwarg injected downstream)
    - Token counting via _default_token_count (same counter V18/V19 use)
    - Project-store path implemented now; global-store pin fusion (D-09 project-priority overflow) STUBBED with a clear TODO + the V21-gated xfail test from V23-01 stays xfail until V21 merges
  </behavior>
  <action>
    In voss/harness/memory_store.py add `render_pinned_memory_text(self, *, model: str) -> str` (or similar): load pins via `_load_pins()` (and the pinned_at ordering from `.pins.json`); for each pinned locator resolve its full memory body from the source file (reuse the store's existing locator→file→text read path; do NOT truncate — D-08); soft-cap each item to `pin_item_cap_tokens` (default 200, from `_load_memory_config()`) using `_default_token_count` (import `from voss.harness.agent import _default_token_count`); accumulate under the `pin_cap_tokens` tier cap (default 500), keeping newest-pinned (pinned_at desc) on overflow and printing one warning to stderr naming the dropped count (D-08 overflow). Return the assembled block (e.g. a labeled "Pinned memory:" prefix consistent with code_recall_text style) or "" when no pins. Read both config keys via `_load_memory_config()` with inline defaults. For D-09 global-store handling: add a code comment marking where post-V21 the global store's pins would be merged with project-priority-on-overflow, but implement only the project store now (the V23-01 xfail global test remains xfail).
  </action>
  <acceptance_criteria>
    - `grep -c 'pin_cap_tokens\|pin_item_cap_tokens' voss/harness/memory_store.py` >= 2
    - Pin cap overflow + always-inject tests pass: `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "pin and (cap or overflow or inject)" -q` GREEN (or `-k pin`)
    - Renderer returns full body (no `[:200]` excerpt slice in the pin path)
    - Imports _default_token_count (grep: `grep -c '_default_token_count' voss/harness/memory_store.py` >= 1)
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k pin -q 2>&1 | tail -5</automated>
  </verify>
  <done>Pin-text renderer emits full pinned bodies under per-item + tier caps with newest-wins overflow warning; global path stubbed; pin cap/inject tests GREEN.</done>
</task>

<task type="auto">
  <name>Task 2: Thread pinned_memory_text through agent.py compose + run_turn</name>
  <read_first>
    - voss/harness/agent.py:373-407 (_compose_system_blocks — code_recall_text param + block-tuple insertion at ~396), :505-577 (run_turn — code_recall_text param at ~522, passed to _compose_system_blocks at ~577), :614-681 (the _run_turn_exec layer if present — code_recall_text at ~614/681)
    - V23-RESEARCH.md:501-507 (D-07 injection site = system-prompt composition, not inside recall())
    - V23-PATTERNS.md:380-424 (agent.py pinned block injection — same slot as code_recall_text, signature-guard idiom)
    - V23-CONTEXT.md D-07 (variable region, non-evictable — code_recall_text rides the same evictable tuple per the V19-05 comment at agent.py:396; the pin block must NOT be folded/evicted: place it so the packer treats it as fixed-cost. If the existing code_recall_text slot is evictable, pin text needs a non-evictable placement — read the compose block construction carefully and place pinned_memory_text where the packer keeps it whole)
  </read_first>
  <action>
    In voss/harness/agent.py: add `pinned_memory_text: str = ""` parameter to `_compose_system_blocks` (mirror the `code_recall_text` parameter position) and add it to the system-block list. CRITICAL per D-07: the pin block is non-evictable — code_recall_text currently rides the evictable variable-region tuple (comment at ~396). Place `pinned_memory_text` so the packer treats it as a fixed-cost item the packer places first and never digests/folds/evicts (a separate non-evictable block, NOT appended to the evictable code_recall tuple). If the compose layer cannot express non-evictability directly, place it as its own block ahead of the evictable region and confirm via the always-inject test that it survives. Add `pinned_memory_text: str = ""` to `run_turn` (and `_run_turn_exec` if that layer threads code_recall_text) and pass it into `_compose_system_blocks(pinned_memory_text=pinned_memory_text, ...)`. Do not change call sites in this task beyond the signature additions — cli.py wiring is Task 3. Match existing style; surgical additions only.
  </action>
  <acceptance_criteria>
    - `grep -c 'pinned_memory_text' voss/harness/agent.py` >= 3 (compose param, compose block use, run_turn param + pass-through)
    - Always-inject test passes (pin present in assembled context for a non-matching query): `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k "pin and inject" -q` GREEN (or `-k pin`)
    - Existing agent packing tests stay green: `.venv/bin/python -m pytest tests/harness/test_agent_packing.py -q`
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k pin -q tests/harness/test_agent_packing.py -q 2>&1 | tail -6</automated>
  </verify>
  <done>pinned_memory_text threaded through compose + run_turn as a non-evictable variable-region block; always-inject test GREEN; packing suite green.</done>
</task>

<task type="auto">
  <name>Task 3: Signature-guarded pin kwarg splat at cli.py run_turn call sites</name>
  <read_first>
    - voss/harness/cli.py:841-853 (_code_recall_kwargs — inspect.signature guard idiom to COPY), run_turn call sites near :1938 (do_cmd) and chat run_turn sites that already splat `**_code_recall_kwargs(...)`
    - V23-PATTERNS.md:400-412 (_pinned_memory_kwargs analog — same inspect.signature guard checking for "pinned_memory_text")
    - V23-CONTEXT.md D-07; memory: voss V18 compiled loop.py gotcha (compiled loop.voss run_turn lacks the new param → guard prevents TypeError; renders only when accepted)
  </read_first>
  <action>
    In voss/harness/cli.py add `_pinned_memory_kwargs(run_turn_fn, store, *, model) -> dict` copying the `_code_recall_kwargs` inspect.signature idiom: return `{}` if `"pinned_memory_text"` is not in the run_turn signature (compiled loop.voss compat — memory: V18 gotcha); else render via `store.render_pinned_memory_text(model=model)` and return `{"pinned_memory_text": text}` only if text is non-empty. At each run_turn call site that already splats `**_code_recall_kwargs(...)`, add `**_pinned_memory_kwargs(run_turn, do_memory_store_or_equivalent, model=model)` alongside it (do_cmd ~1938 uses `MemoryStore(cwd).bind(...)` — reuse that store instance; chat sites likewise). Do NOT record telemetry here (pins do not go through recall). ALSO (per the V23-02 deferred note): if the post-V21 global-store auto-injection site is now present in this tree, wire `global_store._record_telemetry(global_hits)` there and un-xfail the V21-gated global test from V23-01; if V21 is still not merged (no global_store at the attach site), leave the xfail in place and note it in the SUMMARY.
  </action>
  <acceptance_criteria>
    - `grep -c '_pinned_memory_kwargs' voss/harness/cli.py` >= 2 (def + ≥1 call-site splat)
    - Guard returns {} when param absent (grep: `grep -n 'pinned_memory_text. not in' voss/harness/cli.py` or equivalent inspect.signature check present)
    - `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k pin -q` GREEN
    - cli recall path still no-touch for telemetry: `grep -c '_record_telemetry' voss/harness/cli.py` is 0 OR (if V21 global site present) only at the global auto-injection site, never at recall_cmd
    - No regression in harness cli: `.venv/bin/python -m pytest tests/harness/ -k "cli or packing" -q`
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k pin -q 2>&1 | tail -5 && grep -c '_pinned_memory_kwargs' voss/harness/cli.py</automated>
  </verify>
  <done>Pin kwarg splatted at run_turn sites behind a signature guard (compiled-loop safe); pins inject in live composition; recall_cmd stays telemetry-free; all VRNK-06 tests GREEN.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| .pins.json → injected agent context | committed pin file controls always-injected text reaching the model prompt |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V23-06-01 | Information disclosure | committed .pins.json text leaks into the agent prompt + git history | accept | pins are explicit operator curation (D-02); operator controls what is pinned; committed-by-design |
| T-V23-06-02 | Denial of Service | unbounded pin text floods the context ceiling | mitigate | per-item 200-tok + tier 500-tok caps with newest-wins overflow drop + warning (D-08) |
| T-V23-06-03 | Tampering | compiled loop.voss run_turn lacks param → TypeError crash | mitigate | inspect.signature guard returns {} when param absent (V18 compiled-loop gotcha) |
| T-V23-06-SC | Tampering | npm/pip/cargo installs | accept | No installs; zero new packages (RESEARCH audit) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/memory/test_retrieval_ranking.py -k pin -q` GREEN
- `.venv/bin/python -m pytest tests/harness/test_agent_packing.py -q` and `tests/harness/ -k cli` GREEN
- Pin survives over-quota eviction (covered by V23-05 exemption + this plan's inject test)
</verification>

<success_criteria>
VRNK-06 GREEN; pinned text always injected in the variable region (non-evictable, capped, overflow-warned); compiled-loop safe; project store wired, global path stubbed pending V21.
</success_criteria>

<output>
Create `.planning/phases/V23-retrieval-aware-memory-ranking-hygiene/V23-06-SUMMARY.md` when done.
</output>
