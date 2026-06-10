---
phase: V18-budget-aware-context-allocator-token-optimization
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/harness/test_context_allocator.py
  - tests/harness/test_agent_packing.py
  - tests/harness/test_savings_ledger.py
  - tests/harness/test_packing_eval_gate.py
autonomous: true
requirements: [VOPT-01, VOPT-02, VOPT-03, VOPT-04, VOPT-05, VOPT-06, VOPT-07, VOPT-08]
must_haves:
  truths:
    - "Every VOPT-01..08 acceptance behavior has a named, currently-RED test that imports the not-yet-existing surface and fails for the right reason (ImportError / NotImplementedError / xfail), never silently passes"
    - "The four V18 test files exist and collect under pytest without collection errors"
    - "Test fixtures construct synthetic IterationRecord-shaped objects (no provider, no live model) so the allocator suite is pure"
  artifacts:
    - path: "tests/harness/test_context_allocator.py"
      provides: "RED unit stubs for VOPT-01/02/03(pure)/04 — named test functions matching the V18-VALIDATION map"
      contains: "test_allocator_pure"
      min_lines: 80
    - path: "tests/harness/test_agent_packing.py"
      provides: "RED integration stubs for VOPT-03(steady-state)/06 via FakeStreamingProvider"
      contains: "test_no_pack_byte_identical"
      min_lines: 40
    - path: "tests/harness/test_savings_ledger.py"
      provides: "RED ledger stubs for VOPT-05 (packed<=original, no-pack==, /cost line, dollar netting)"
      contains: "test_ledger_packed_le_original"
      min_lines: 40
    - path: "tests/harness/test_packing_eval_gate.py"
      provides: "RED eval-gate stubs for VOPT-07 (quality preservation + biting gate)"
      contains: "test_quality_preservation_gate"
      min_lines: 30
  key_links:
    - from: "tests/harness/test_context_allocator.py"
      to: "voss.harness.context_allocator"
      via: "import ContextAllocator, PackingProfile (will fail RED until Plan 02)"
      pattern: "from voss.harness.context_allocator import"
    - from: "tests/harness/test_agent_packing.py"
      to: "voss.harness.agent._run_turn_exec"
      via: "FakeStreamingProvider scripted run asserting on stream_calls[-1]['messages']"
      pattern: "stream_calls"
---

<objective>
Lay the Nyquist RED test scaffold for all eight V18 requirements BEFORE any production code exists. Every acceptance criterion in V18-SPEC.md and every row in the V18-VALIDATION.md per-task map gets a named test function that imports the not-yet-built surface and fails for the right reason. This is the falsifiable contract the rest of the phase satisfies.

Purpose: Without RED tests first, "packed <= original", "byte-identical --no-pack", and "cache-coherent append-only" become assertions of intent rather than enforced invariants. The scaffold makes Plans 02-05 GREEN-by-construction targets.

Output: Four test files under tests/harness/ that collect cleanly and fail (RED) until their production counterparts land in later waves. Each test names the exact symbol/behavior from V18-VALIDATION.md.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-SPEC.md
@.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-RESEARCH.md
@.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-PATTERNS.md
@.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-VALIDATION.md

<interfaces>
<!-- The surfaces these RED tests target. They do NOT exist yet — that is why the tests are RED. -->
<!-- Plan 02 creates voss/harness/context_allocator.py; Plan 03 adds packing_enabled to run_turn; Plan 04 adds the ledger. -->

Planned (Plan 02) — voss/harness/context_allocator.py:
  @dataclass class PackingProfile:
      recent_full_k: int = 8
      digest_cutoff_m: int = 20
      high_water: float = 0.80
      low_water: float = 0.60
      enabled: bool = True
  class ContextAllocator:
      def __init__(self, token_count: Callable[[str], int]): ...   # token_count injected for purity (no agent import cycle)
      def pack(self, iter_records: list, packing_budget: int, profile: PackingProfile) -> list[tuple[dict, dict]]: ...
      def stable_region_hash(self) -> str: ...   # SHA-256 of stable (non-recompacted) replay pairs

Existing — voss/harness/agent.py (VERIFIED):
  def _serialize_iter_for_replay(iter_rec) -> tuple[dict, dict]   # agent.py:431-460, the FULL tier; args redacted via telemetry.redact_tool_args
  def _default_token_count(text: str, *, model: str) -> int        # agent.py:73-80
  async def _run_turn_exec(...) -> TurnResult                       # agent.py:564 — Plan 03 adds packing_enabled: bool = True

Existing — voss/harness/session.py (VERIFIED):
  @dataclass class IterationRecord:                                 # session.py:99-115
      index: int; plan: dict; tool_results: list[dict]
      cache_read_input_tokens: int = 0; prompt_tokens: int = 0

Existing test analogs (VERIFIED to exist):
  tests/harness/test_agent_loop.py        — FakeStreamingProvider + _done_script + _run_turn_exec async harness
  tests/harness/test_cache_tokens.py      — pure SimpleNamespace unit pattern (no fixtures)
  tests/harness/test_cost_slash.py        — fake_ctx fixture + _build_slash_registry + capsys for /cost
  tests/harness/test_harness_config.py    — xdg monkeypatch fixture for path isolation
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Allocator + integration RED stubs (VOPT-01/02/03/04/06)</name>
  <read_first>
    - tests/harness/test_agent_loop.py (FakeStreamingProvider at :76-114, _done_script factory at :152-164, async _run_turn_exec harness at :188-207 — copy these patterns verbatim)
    - tests/harness/test_cache_tokens.py (pure SimpleNamespace unit pattern, no fixtures — the model for allocator-pure tests)
    - voss/harness/agent.py:431-460 (_serialize_iter_for_replay — the FULL-tier reference the byte-identity tests compare against)
    - voss/harness/agent.py:708-716 (the chokepoint for-loop the --no-pack test pins)
    - voss/harness/session.py:99-115 (IterationRecord shape for synthetic fixtures)
    - .planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-VALIDATION.md (per-task map — test names must match)
  </read_first>
  <action>
    Create tests/harness/test_context_allocator.py with these named RED test functions (pure, no @pytest.mark.asyncio, constructing synthetic iters as SimpleNamespace or IterationRecord with index/plan/tool_results):
    - `test_allocator_pure` (VOPT-01): instantiate ContextAllocator(token_count=lambda s: max(len(s)//4,1)), call pack() on 50 synthetic iters with a small budget; assert no provider attribute touched and no filesystem write (pure). Import is `from voss.harness.context_allocator import ContextAllocator, PackingProfile`.
    - `test_pack_50_iters_under_ceiling` (VOPT-01): 50 synthetic iters, packing_budget=10_000; assert summed token_count of rendered pairs <= 10_000.
    - `test_below_threshold_byte_identical` (VOPT-01): with <= recent_full_k iters, assert pack() output equals [ _serialize_iter_for_replay(p) for p in iters ] byte-for-byte (import _serialize_iter_for_replay from voss.harness.agent).
    - `test_tier_boundaries_golden_render` (VOPT-02): 20 iters with default profile; assert the last K render full, K..M render as one-line digests (assert the digest marker substring), >M fold into a single "Earlier work" block; assert the NEWEST iter is full in every case.
    - `test_packed_tokens_never_exceed_full` (VOPT-02): for several history lengths, assert summed packed tokens <= summed full-replay tokens.
    - `test_stable_region_append_only` (VOPT-03 pure): call pack() across simulated turns staying below high_water; assert stable_region_hash() is unchanged turn-over-turn.
    - `test_recompaction_on_high_water` (VOPT-03 pure): drive estimated usage past high_water; assert a recompaction occurs (stable_region_hash changes exactly once at the crossing).
    - `test_eviction_pointer_emitted` (VOPT-04): a folded iter whose tool_results args carry path="foo.py" yields a rendered pointer containing `re-fetch` and `code_search` (substring assertion); assert pointers deduped and capped at 5.
    Then create tests/harness/test_agent_packing.py (integration, @pytest.mark.asyncio, FakeStreamingProvider with stream_calls capture):
    - `test_no_pack_byte_identical` (VOPT-06): run _run_turn_exec twice — once with packing_enabled=False (or VOSS_NO_PACK), once with packing_enabled=True on a run that stays <= recent_full_k iters; assert stream_calls[-1]["messages"] are equal. (Will fail RED: _run_turn_exec has no packing_enabled param yet — Plan 03 adds it.)
    - `test_cached_prefix_unchanged` (VOPT-06): assert messages[0]["content"] (sys_blocks, the T4 prefix) is byte-identical whether packing is on or off.
    - `test_cache_coherence_steady_state` (VOPT-03 integration): scripted 10-iter run with FakeStreamingProvider emitting Usage(cache_read_input_tokens=200); assert returned run.iterations show cache_read_input_tokens > 0 in steady state.
    Mark every test body so it fails for the RIGHT reason: either the import raises ImportError, or use `pytest.importorskip` is FORBIDDEN here (must be RED not skipped) — instead let the import fail, OR wrap the missing-symbol call in an assertion that the symbol exists. Do NOT use xfail(strict=False) anywhere (false-green risk — see project memory gsd-scaffold-fictional-api). If you must xfail, use `@pytest.mark.xfail(strict=True, reason="Plan 0X")` so an accidental XPASS is itself a failure.
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/harness/test_context_allocator.py tests/harness/test_agent_packing.py --collect-only -q` lists every named test above with zero collection errors.
    - `.venv/bin/python -m pytest tests/harness/test_context_allocator.py -q` exits non-zero (RED) — failures are ImportError on `voss.harness.context_allocator` or missing-symbol assertions, NOT collection errors and NOT silent pass.
    - `grep -n "xfail(strict=False)" tests/harness/test_context_allocator.py tests/harness/test_agent_packing.py` returns empty (no false-green xfail).
    - `grep -c "def test_" tests/harness/test_context_allocator.py` returns >= 8.
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_context_allocator.py tests/harness/test_agent_packing.py --collect-only -q 2>&1 | tail -5</automated>
  </verify>
  <done>Both files collect cleanly; allocator suite is RED via ImportError/missing-symbol (not skipped, not green); >= 8 allocator tests + 3 packing tests named per V18-VALIDATION.md; no xfail(strict=False).</done>
</task>

<task type="auto">
  <name>Task 2: Ledger + eval-gate RED stubs (VOPT-05/07)</name>
  <read_first>
    - tests/harness/test_cost_slash.py (fake_ctx fixture at :8-30, _build_slash_registry + registry.lookup("/cost").handler + capsys pattern at :33-44 — copy verbatim)
    - tests/harness/test_harness_config.py (xdg monkeypatch fixture at :12-16 for path isolation)
    - voss/eval/runner.py:272-300 (run_suite signature — the eval-gate tests call this), :100-103 (_append_row JSONL pattern), :355-377 (runs.jsonl row schema: has `success`/`cost_usd`/`judge_verdict`, NOTE: NO prompt_tokens field today)
    - voss/harness/session.py:57-58 (_sessions_dir — ledger path root)
    - .planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-RESEARCH.md (Savings Ledger section + Pitfall 8 eval-temp-dir note + Assumption A9 biting-gate profile)
  </read_first>
  <action>
    Create tests/harness/test_savings_ledger.py (uses tmp_path + fake_ctx-style SimpleNamespace; ledger path = tmp_path/".voss"/"sessions"/"<id>"/"token-savings.jsonl"):
    - `test_ledger_packed_le_original` (VOPT-05): after a (stubbed) ledger write via recorder._append_savings_record, read the JSONL row and assert row["packed_tokens_est"] <= row["original_tokens_est"] and row["saved_tokens_est"] >= 0. Import is `from voss.harness.recorder import _append_savings_record` (RED until Plan 04).
    - `test_no_pack_zero_savings` (VOPT-05): a row written under the no-pack/method="no-pack" path records original_tokens_est == packed_tokens_est and saved_tokens_est == 0.
    - `test_cost_slash_prints_savings_line` (VOPT-05): build a fake_ctx with a populated ledger; invoke registry.lookup("/cost").handler(fake_ctx, [], "/cost"); assert capsys output contains "context packed:" (RED until Plan 04 extends _cost).
    - `test_saved_usd_nets_cache_reads` (VOPT-05 / D-04): assert the dollar estimate function (e.g. recorder.estimate_savings_usd) nets cache reads — for a row with cache_read_tokens > 0, saved_usd_est is strictly less than naive saved_tokens*input_rate, and >= 0; with an unknown model the function returns None (no crash). Import RED until Plan 04.
    Create tests/harness/test_packing_eval_gate.py (calls voss.eval.runner.run_suite with stub=True; toggles VOSS_NO_PACK; reads runs.jsonl):
    - `test_quality_preservation_gate` (VOPT-07): run the golden suite stub once with VOSS_NO_PACK=1 (off) and once without (on); read both runs.jsonl `success` fields; assert success_rate(on) >= success_rate(off) - TOLERANCE (TOLERANCE=0.05). Import the gate helper from the eval-gate module Plan 05 creates (e.g. `from voss.harness.packing_eval import compare_runs` or assert against runs.jsonl directly) — RED until Plan 05.
    - `test_aggressive_profile_fails_gate` (VOPT-07 biting gate): run the suite stub with an over-aggressive profile (recent_full_k=1, digest_cutoff_m=2 injected via monkeypatch/env); assert the gate REJECTS it (success drops below the tolerance OR the gate helper returns failed). This proves the gate bites.
    NOTE for the executor (encode as a test comment): runs.jsonl does NOT carry prompt_tokens (verified runner.py:358-377) — the "mean input tokens drop" metric must be sourced by Plan 05 (either by extending the eval row or reading the persisted SessionRecord iterations). The RED stub asserts on the success-rate gate now and leaves a `# TODO(Plan 05): assert mean input-token reduction once eval row carries tokens` marker so the token metric is not silently dropped.
    Same anti-false-green rules as Task 1: no xfail(strict=False); RED via ImportError/missing-symbol or strict xfail.
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/harness/test_savings_ledger.py tests/harness/test_packing_eval_gate.py --collect-only -q` lists all four named tests with zero collection errors.
    - `.venv/bin/python -m pytest tests/harness/test_savings_ledger.py -q` exits non-zero (RED) via ImportError on recorder._append_savings_record / estimate_savings_usd.
    - `grep -n "prompt_tokens\|mean input-token\|TODO(Plan 05)" tests/harness/test_packing_eval_gate.py` shows the token-metric TODO marker is present (so the VOPT-07 token-reduction half is not lost).
    - `grep -n "xfail(strict=False)" tests/harness/test_savings_ledger.py tests/harness/test_packing_eval_gate.py` returns empty.
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_savings_ledger.py tests/harness/test_packing_eval_gate.py --collect-only -q 2>&1 | tail -5</automated>
  </verify>
  <done>Both files collect; ledger suite RED via ImportError; four tests named per V18-VALIDATION.md; the runs.jsonl-has-no-prompt_tokens reality is captured as an explicit TODO(Plan 05) marker; no xfail(strict=False).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test fixtures → production import | Tests import not-yet-existing symbols; risk is a stub that false-greens (xfail-hidden) instead of failing RED |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V18-01 | Tampering (false-green) | RED test stubs | mitigate | Forbid `xfail(strict=False)`; require RED via ImportError/missing-symbol or `xfail(strict=True)`; grep-gate asserts no `xfail(strict=False)` (project memory gsd-scaffold-fictional-api: fake-API stubs hide as false-green) |
| T-V18-02 | Information disclosure | synthetic fixtures | accept | Fixtures use literal "foo.py"/"ok" strings — no real secrets, no PII; redaction is exercised by Plan 02 full-tier tests, not here |
| T-V18-SC | Tampering | npm/pip/cargo installs | mitigate | V18 adds ZERO new packages (RESEARCH Package Legitimacy Audit: only litellm, already in venv). No install task in this plan; nothing to gate. |
</threat_model>

<verification>
- Both `--collect-only` commands list every named test with zero collection errors.
- Allocator + ledger suites are RED (non-zero exit) for the right reason (ImportError / missing symbol), not skipped, not green.
- No `xfail(strict=False)` anywhere in the four files.
- The `TODO(Plan 05)` token-metric marker is present so the VOPT-07 input-token-reduction half is tracked.
</verification>

<success_criteria>
- Four test files exist under tests/harness/ and collect cleanly.
- >= 8 allocator unit tests + 3 packing integration tests + 4 ledger tests + 2 eval-gate tests, every name matching the V18-VALIDATION.md per-task map.
- The full pre-existing harness suite still collects (no collection breakage introduced): `.venv/bin/python -m pytest tests/harness/ --collect-only -q` succeeds.
</success_criteria>

<output>
Create `.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-01-SUMMARY.md` when done.
</output>
