---
phase: V18-budget-aware-context-allocator-token-optimization
plan: 05
type: execute
wave: 5
depends_on: ["V18-04-budget-aware-context-allocator-token-optimization"]
files_modified:
  - voss/harness/packing_eval.py
  - voss/eval/runner.py
  - tests/harness/test_coherence_guard.py
autonomous: true
requirements: [VOPT-07, VOPT-08]
must_haves:
  truths:
    - "An M5 eval variant runs the golden suite packing-on vs packing-off (via VOSS_NO_PACK toggle) and a gate asserts success_rate(on) >= success_rate(off) - tolerance while mean input tokens drop measurably"
    - "The gate BITES: a deliberately over-aggressive profile (recent_full_k=1, digest_cutoff_m=2) that regresses a golden task is REJECTED by the gate, proving it is enforced not decorative"
    - "The mean-input-token reduction is measured from a real token field (eval row carries input_tokens) — not silently dropped because runs.jsonl lacked prompt_tokens"
    - "The V18 diff adds no new search index, embedding store, or vector backend; recorder.py _emit_budget_osc OSC shape is unchanged; the T4 cached prefix is byte-identical under --no-pack; crates/ and frozen schemas are untouched; the full harness suite is green"
  artifacts:
    - path: "voss/harness/packing_eval.py"
      provides: "compare_runs(on_runs, off_runs, tolerance) gate + a driver that runs the golden suite twice toggling VOSS_NO_PACK and returns pass/fail with token deltas"
      contains: "def compare_runs"
      min_lines: 50
    - path: "voss/eval/runner.py"
      provides: "input_tokens figure added to each runs.jsonl row so the VOPT-07 token-reduction metric is measurable"
      contains: "input_tokens"
    - path: "tests/harness/test_coherence_guard.py"
      provides: "VOPT-08 automated guard: no index/embedding dep, budget-OSC frozen, no second budget system"
      contains: "_emit_budget_osc"
      min_lines: 25
  key_links:
    - from: "voss/harness/packing_eval.py compare_runs"
      to: "runs.jsonl success + input_tokens fields"
      via: "success_rate gate + mean input-token delta from two suite runs"
      pattern: "success_rate"
    - from: "voss/harness/packing_eval.py driver"
      to: "voss.eval.runner.run_suite"
      via: "VOSS_NO_PACK toggled between the on/off runs (stub=True for hermetic CI)"
      pattern: "VOSS_NO_PACK"
---

<objective>
Close the phase with the honest-number gate (VOPT-07) and the coherence guard (VOPT-08). The gate runs the golden suite packing-on vs packing-off and rejects any profile that regresses task success beyond a locked tolerance — and it must demonstrably BITE on an over-aggressive profile. The coherence guard proves V18 added no parallel index/budget substrate, kept the OSC shape and T4 prefix intact, left crates/ untouched, and keeps the full suite green.

Purpose: The savings % must be an eval output, not a marketing figure; a gate that cannot fail is decoration. The coherence guard is PRD §9's top risk (voss do/voss chat working every wave, no duplicated substrate).

Output: voss/harness/packing_eval.py gate + an input_tokens field on the eval row + a coherence-guard test, turning the VOPT-07 quality/biting tests GREEN and satisfying the VOPT-08 coherence assertions.
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
<!-- VERIFIED source seams. -->

eval/runner.py VERIFIED:
  :36   SUITE_ROOT = Path("tests/eval")   golden tasks: 01-analyze 02-plan-only 03-approved-edit 04-validation 05-resume 06-fetch-summarize
  :100-103 _append_row(path, row)
  :272-300 run_suite(*, suite="golden", stub=False, live=False, k=1, out=None, ...) -> Path  (writes runs.jsonl + summary.md)
  :355-377 the runs.jsonl row: {task_id, run_idx, success (bool|None), cost_usd, confidence, judge_verdict, duration_s, provider, model, ...}
           IMPORTANT — VERIFIED: the row has NO input/prompt token field today. compare_runs needs one → add `input_tokens` to the row
           (sourced from the run's session record iterations sum of prompt_tokens) so the token-reduction metric is real, not inferred from cost.

VOPT-07 gate contract:
  TOLERANCE = 0.05 (5%)
  pass iff success_rate(on) >= success_rate(off) - TOLERANCE  AND  mean_input_tokens(on) < mean_input_tokens(off)
  biting proof: a regressing profile drops >= 1 golden task → gate returns FAIL

From Plan 02/03: ContextAllocator + PackingProfile; VOSS_NO_PACK disables packing (Plan 03 do_cmd flag + agent honoring the env via config/profile).
From Plan 04: token-savings.jsonl ledger (not required by the gate, but present during a packed run).

VOPT-08 coherence assertions (grep/inspect gates, no new framework):
  - no new index/embedding/vector dep anywhere in the V18 diff (context_allocator.py, agent.py changes, recorder.py changes, packing_eval.py)
  - _emit_budget_osc five-field signature unchanged (frozen)
  - cached prefix (sys_blocks) byte-identical under --no-pack (already asserted by test_cached_prefix_unchanged, Plan 03)
  - crates/ untouched; frozen schemas untouched
  - full harness suite green
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add input_tokens to the eval row (make the token metric real)</name>
  <files>voss/eval/runner.py</files>
  <read_first>
    - voss/eval/runner.py:300-377 (the per-run loop that builds the row dict at :358-377; where cost_usd/confidence are sourced from the SessionRecord/run result — the same place to sum prompt_tokens into input_tokens)
    - voss/harness/session.py:99-115 (IterationRecord.prompt_tokens — the per-iteration field to sum), RunRecord.iterations structure
    - .planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-RESEARCH.md (Quality-Preservation Eval section: "mean input tokens can be read from run iterations sum(prompt_tokens)")
    - tests/harness/test_packing_eval_gate.py (the TODO(Plan 05) marker — this task removes it by making input_tokens available)
  </read_first>
  <action>
    In voss/eval/runner.py, in the per-run row construction (~:358-377), add an `"input_tokens": <int>` field computed as the sum of `prompt_tokens` over the run's IterationRecords (from the SessionRecord/run result already available where cost_usd is computed). If iterations are unavailable for a given run (crash/skip), record `input_tokens: 0` consistently — do not raise. Keep every existing row field byte-identical (additive only); existing eval consumers must not break.
    This is the single change that lets compare_runs (Task 2) measure mean input-token reduction from a real field rather than inferring from cost.
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -c "src=open('voss/eval/runner.py').read(); assert 'input_tokens' in src, 'input_tokens field missing'"` exits 0.
    - `.venv/bin/python -m pytest tests/ -k "eval" -q` exits 0 (existing eval tests still green with the additive field).
    - `grep -n "input_tokens" voss/eval/runner.py` shows the field in the row dict.
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -c "src=open('voss/eval/runner.py').read(); assert 'input_tokens' in src" && .venv/bin/python -m pytest tests/ -k eval -q</automated>
  </verify>
  <done>Each runs.jsonl row carries an additive input_tokens figure (sum of per-iteration prompt_tokens); existing eval row fields unchanged; eval suite green.</done>
</task>

<task type="auto">
  <name>Task 2: packing_eval gate (quality preservation + biting proof)</name>
  <files>voss/harness/packing_eval.py</files>
  <read_first>
    - voss/eval/runner.py:272-300 (run_suite signature — call with suite="golden", stub=True, out=tmp), :355-377 (row schema now incl. input_tokens from Task 1)
    - voss/harness/context_allocator.py + voss/harness/config.py get_packing_profile (Plan 02/03 — how the over-aggressive profile is injected: via [context] override or a monkeypatched profile)
    - .planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-PATTERNS.md (test_packing_eval_gate.py section: run_suite invocation toggling VOSS_NO_PACK; runs.jsonl success-rate read; biting-gate via over-aggressive profile)
    - .planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-RESEARCH.md (Pitfall 8 eval-temp-dir + Assumption A9 biting-gate profile recent_full_k=1/digest_cutoff_m=2; the gate may need K even smaller if a golden task still passes)
    - tests/harness/test_packing_eval_gate.py (test_quality_preservation_gate, test_aggressive_profile_fails_gate — the targets)
  </read_first>
  <action>
    Create voss/harness/packing_eval.py:
    - `_read_runs(path) -> list[dict]`: parse runs.jsonl (json.loads per non-empty line).
    - `_success_rate(rows) -> float`: fraction with success is True (treat None/crash as not-success).
    - `_mean_input_tokens(rows) -> float`: mean of row["input_tokens"] over rows with a numeric value.
    - `compare_runs(on_rows, off_rows, tolerance=0.05) -> dict`: returns {passed: bool, success_on, success_off, mean_tokens_on, mean_tokens_off, token_reduction}; passed iff success_on >= success_off - tolerance AND mean_tokens_on < mean_tokens_off. This is the gate decision (the savings % is an OUTPUT here).
    - `run_packing_gate(*, suite="golden", stub=True, out_dir, profile=None, tolerance=0.05) -> dict`: thin driver that runs run_suite twice — once with VOSS_NO_PACK=1 in the environment (off), once without it (on, optionally with an injected over-aggressive profile) — into out_dir/"off" and out_dir/"on", then returns compare_runs(...). Restore the prior VOSS_NO_PACK env value in a finally block.
    The two RED tests this satisfies: test_quality_preservation_gate asserts run_packing_gate(...)["passed"] is True with the default profile; test_aggressive_profile_fails_gate asserts the gate returns passed=False when run with PackingProfile(recent_full_k=1, digest_cutoff_m=2) (the biting proof). If the stub golden suite does not regress even at K=1 (Assumption A9 risk), make the biting test inject a profile aggressive enough to drop a task, or assert the gate's success-rate clause directly against a synthesized regressed off/on pair — the REQUIREMENT is that a regressing profile is provably rejected, not that K=1 specifically regresses.
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/harness/test_packing_eval_gate.py::test_quality_preservation_gate tests/harness/test_packing_eval_gate.py::test_aggressive_profile_fails_gate -x` exits 0 (gate passes the default profile; gate REJECTS the over-aggressive profile — bites).
    - `.venv/bin/python -c "from voss.harness.packing_eval import compare_runs; r=compare_runs([{'success':True,'input_tokens':5000}],[{'success':True,'input_tokens':9000}]); assert r['passed'] is True; bad=compare_runs([{'success':False,'input_tokens':3000},{'success':True,'input_tokens':3000}],[{'success':True,'input_tokens':9000},{'success':True,'input_tokens':9000}], tolerance=0.05); assert bad['passed'] is False, bad"` exits 0 (gate math: passes when success held + tokens down; fails when success regresses beyond tolerance).
    - `grep -n "VOSS_NO_PACK" voss/harness/packing_eval.py && grep -n "def compare_runs\|def run_packing_gate" voss/harness/packing_eval.py` shows the toggle + gate + driver.
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_packing_eval_gate.py -x -q</automated>
  </verify>
  <done>packing_eval.py runs the golden suite on-vs-off via VOSS_NO_PACK, computes the success-rate + input-token gate, passes the conservative default, and provably REJECTS an over-aggressive regressing profile (the gate bites). The savings % is an eval output.</done>
</task>

<task type="auto">
  <name>Task 3: Coherence guard (VOPT-08) — no duplicated substrate, OSC frozen, full suite green</name>
  <files>tests/harness/test_coherence_guard.py, .planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-VALIDATION.md</files>
  <read_first>
    - voss/harness/context_allocator.py, voss/harness/agent.py, voss/harness/recorder.py, voss/harness/packing_eval.py, voss/harness/config.py, voss/harness/cli.py (the full V18 diff surface — the grep gates scan these)
    - voss/harness/recorder.py:98-127 (_emit_budget_osc frozen five-field shape)
    - .planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-SPEC.md (VOPT-08 acceptance: no new index/embedding/vector dep; recorder budget-OSC shape unchanged; cached-prefix golden byte-identical under --no-pack; crates/ + frozen schemas untouched; full suite green)
    - .planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-VALIDATION.md (Manual-Only: /cost + F3 HUD visual render is the one human-check; everything else automated)
  </read_first>
  <action>
    Create tests/harness/test_coherence_guard.py asserting the VOPT-08 invariants as automated checks:
    - No new retrieval substrate: read each V18-touched harness file, strip comment lines (lines whose stripped form startswith "#"), and assert zero occurrences of the tokens `chromadb`, `faiss`, `annoy`, `embedding`, `sentence_transformers`, `pinecone`, `vectorstore` in the non-comment body (so header prose does not self-invalidate the gate).
    - Budget OSC frozen: assert `list(inspect.signature(recorder._emit_budget_osc).parameters) == ['tokens_used','token_limit','cost_usd','iteration','model']`.
    - No second budget system: assert the module-level function set of recorder.py contains exactly one budget-OSC emitter (no NEW `_emit_*budget*` function beyond the existing one) — the only budget plumbing is the existing agent.py counter + F3 recorder OSC.
    Then update .planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-VALIDATION.md per-task map: replace the placeholder V18-0x-xx rows with the real Plan/Task/test names now that they exist, flip the relevant Status cells to ✅ for covered rows, and set `nyquist_compliant: true` + `wave_0_complete: true` in the frontmatter ONLY IF every VOPT row maps to a passing automated test. The crates/-untouched + frozen-schema invariant is recorded as a SUMMARY note (V18 files_modified across all five plans contain no path under crates/ — verifiable from the plan frontmatter).
    Run the FULL harness suite and require green (PRD §9 top risk); a `voss do`/`voss chat` smoke is the human/wave gate noted in V18-VALIDATION.md Manual-Only.
  </action>
  <acceptance_criteria>
    - `for f in voss/harness/context_allocator.py voss/harness/packing_eval.py; do test "$(grep -v '^[[:space:]]*#' "$f" | grep -Eci 'chromadb|faiss|annoy|embedding|sentence_transformers|pinecone|vectorstore')" = "0" || { echo "FAIL $f"; exit 1; }; done` exits 0 (VOPT-08: no new index/embedding/vector dep).
    - `.venv/bin/python -c "import inspect, voss.harness.recorder as r; assert list(inspect.signature(r._emit_budget_osc).parameters)==['tokens_used','token_limit','cost_usd','iteration','model']"` exits 0 (budget OSC frozen).
    - `.venv/bin/python -m pytest tests/harness/test_coherence_guard.py -x -q` exits 0.
    - `.venv/bin/python -m pytest tests/harness/ -q` exits 0 (FULL harness suite green — the phase regression gate).
    - `.venv/bin/python -m pytest tests/harness/test_context_allocator.py tests/harness/test_agent_packing.py tests/harness/test_savings_ledger.py tests/harness/test_packing_eval_gate.py -q` exits 0 (every V18 test GREEN — VOPT-01..08 covered).
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_coherence_guard.py tests/harness/ -q</automated>
  </verify>
  <done>VOPT-08 guard test asserts no index/embedding dep + frozen budget-OSC shape + no second budget system; full harness suite green; every V18 test GREEN; V18-VALIDATION.md per-task map updated to real test names with nyquist_compliant flipped only on full coverage.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| eval profile → gate verdict | An over-aggressive profile must be provably rejected; a non-biting gate would let a quality-regressing packing ship |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V18-14 | Spoofing (decorative gate) | packing_eval gate | mitigate | test_aggressive_profile_fails_gate proves the gate returns passed=False on a regressing profile; compare_runs math is unit-asserted on a synthesized regressed pair so the bite does not depend on stub-suite luck |
| T-V18-15 | Tampering (duplicated substrate) | V18 diff | mitigate | test_coherence_guard greps the V18 files (comments stripped) for index/embedding/vector tokens → zero; asserts budget-OSC frozen + no second budget emitter (VOPT-08) |
| T-V18-16 | Information disclosure (dishonest savings %) | gate output | mitigate | The savings % is computed as a gate OUTPUT from measured input_tokens (real field from Task 1), not a hardcoded figure; mean-token reduction is required for the gate to pass |
| T-V18-SC | Tampering | npm/pip/cargo installs | accept | No new packages (RESEARCH Package Legitimacy Audit: litellm only, already in venv). packing_eval.py is stdlib + existing imports. No install task. |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/ -q` GREEN (full harness suite — PRD §9 top risk).
- All four V18 test files GREEN (VOPT-01..08 covered).
- VOPT-08 grep gates: zero index/embedding/vector tokens in V18 files (comments stripped); `_emit_budget_osc` signature frozen.
- compare_runs provably fails on a regressing profile (the gate bites); savings % is a measured output.
- Manual-only follow-up (V18-VALIDATION.md): a long `voss do` shows the `/cost` + F3 HUD savings line render.
</verification>

<success_criteria>
- voss/eval/runner.py rows carry input_tokens (additive); existing eval green.
- voss/harness/packing_eval.py: compare_runs gate + VOSS_NO_PACK on/off driver; passes the conservative default, rejects an over-aggressive profile.
- tests/harness/test_coherence_guard.py: no index/embedding dep, frozen budget OSC, no second budget system.
- Full harness suite green; every VOPT-01..08 maps to a passing automated test; V18-VALIDATION.md per-task map updated.
</success_criteria>

<output>
Create `.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-05-SUMMARY.md` when done.
</output>
