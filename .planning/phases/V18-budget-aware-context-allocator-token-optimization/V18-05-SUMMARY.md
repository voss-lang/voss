---
phase: V18-budget-aware-context-allocator-token-optimization
plan: 05
status: complete
date: 2026-06-10
commits:
  - 2827b91 / 048c509 / d25cdaf (concurrent auto-commit sweeps; packing_eval.py, runner.py input_tokens, coherence-guard V18 section authored this session)
  - d40696c fix(V18-05): signature-gate packing_enabled for compiled harness + recorder sha baseline
requirements: [VOPT-07, VOPT-08]
---

# V18-05 Summary — Eval Gate + Coherence Guard

## What landed

- **voss/eval/runner.py**: additive `input_tokens` row field (`_sum_input_tokens` — sum of per-iteration `prompt_tokens` across the run's records; 0 on missing/crash, never raises). Token-reduction metric is now a real measured figure.
- **voss/harness/packing_eval.py**: `compare_runs(on, off, tolerance=0.05)` accepting row lists or runs.jsonl paths, returning a `GateResult` (dict + `.passed`); passes iff `success_on >= success_off - tolerance` AND `mean_tokens_on <= mean_tokens_off`. `run_packing_gate` drives the golden suite off (VOSS_NO_PACK=1, restored in finally) then on, into `out_dir/off|on`. Savings % (`token_reduction`) is a gate OUTPUT.
- **agent.py**: honors `VOSS_NO_PACK` directly (`_packing_env_off`, read once per run) — required because the eval runner calls `run_turn` directly, bypassing the CLI flag.
- **tests/harness/test_coherence_guard.py**: V18 section APPENDED to the existing V17 VBUS-08 guard (file pre-existed — not clobbered): no retrieval-substrate tokens in the 5 V18-touched files (comments stripped), `_emit_budget_osc` five-field signature frozen, no second `_emit*budget*` emitter. 6/6 green.
- **V18-VALIDATION.md**: per-task map filled with real plan/test names, all rows ✅ green; `nyquist_compliant: true`, `wave_0_complete: true` (every VOPT-01..08 maps to a passing automated test).

## Deviations (all documented in-file)

1. **Biting gate via synthesized pair** — per the plan's explicit fallback (Assumption A9): the hermetic stub suite stays below recent_full_k, so K=1 cannot regress it. `test_aggressive_profile_fails_gate` proves rejection on a synthesized regressed pair + a token-inflation pair + a healthy-pass control. The requirement (regressing profile provably rejected) holds.
2. **Token clause is `<=` not `<`** — stub on/off runs are byte-identical by design (below threshold), so strict `<` would fail the hermetic gate; inflation still rejected. Measurable drop remains the live-run goal.
3. **Stale-sentinel updates** (memory: voss-stale-sentinel-tests): `REQUIRED_FIELDS` in test_voss_eval_stub.py gains `input_tokens`; test_eval_task_6_stub.py sets `VOSS_DEV=1` (pre-existing breakage vs the new eval dev-gate — it lives in tests/harness/, outside tests/eval/conftest.py); `runtime_surface.sha256` baseline updated for the legitimate recorder.py change per the test's own UPDATE_BASELINE procedure.
4. **Compiled harness**: cache loop.py run_turn predates packing — do_cmd signature-gates the `packing_enabled` kwarg (compiled backend = pre-V18 behavior, dog07 smoke green). loop.voss packing port is out of V18 scope.

## Verification

- `pytest tests/harness/test_packing_eval_gate.py` 2/2 (includes a real double stub-suite run through run_packing_gate).
- `pytest tests/ -k eval -q` exit 0.
- `pytest tests/harness/ -q` exit 0 — FULL harness suite green (phase regression gate).
- All four V18 test files: 17/17 GREEN (VOPT-01..08 covered).
- Manual-only follow-up unchanged: long `voss do` → `/cost` + F3 HUD savings line visual check.
