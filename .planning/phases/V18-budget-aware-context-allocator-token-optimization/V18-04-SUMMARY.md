---
phase: V18-budget-aware-context-allocator-token-optimization
plan: 04
status: complete
date: 2026-06-10
commits:
  - 865e4d6 feat(V18-04): falsifiable savings ledger — JSONL rows, cache-netted $, /cost line
requirements: [VOPT-05]
---

# V18-04 Summary — Savings Ledger

## What landed

- **recorder.py**: `_append_savings_record(cwd, session_id, record)` — clamps `packed_tokens_est <= original_tokens_est` and `saved_tokens_est = max(diff, 0)` BEFORE write; appends sorted-keys JSONL to `_sessions_dir(cwd)/<id>/token-savings.jsonl` (subdirectory convention, RESEARCH A7). `estimate_savings_usd(saved, cache_read, model)` — litellm lookup with `anthropic.` fallback, nets `cache_read_tokens * (input_rate - cache_read_rate)` off the gross, clamped >= 0, None on unknown model, never raises. `_emit_budget_osc` untouched (five-field signature verified frozen).
- **agent.py**: at the seam, packing-on branch renders the full replay for measurement only (`_orig_est`) vs the packed estimate (`_packed_est`); method = `no-pack` / `full` / `tiered-K{k}-M{m}`. One ledger row per assembled turn written right after usage extraction (common to all three iteration-end paths), guarded `session_id is not None` + try/except (best-effort, never crashes). `_savings_osc` dict added additively to the context-OSC payload at all 3 `_emit_context_osc` sites (`{**snapshot, "savings": ...}`).
- **cli.py**: `/cost` default path appends `context packed: ~X→~Y tokens (−Z%)  ~$… saved` aggregated from the session ledger; `~$` clause omitted when every `saved_usd_est` is null; silent when ledger absent/empty; try/except so a malformed ledger never breaks /cost.

## Verification

- `test_savings_ledger.py` 4/4, `test_agent_packing.py` 3/3, `test_cost_slash.py` 2/2, `test_recorder_iterations.py` all green (17 total).
- Netting check: `estimate_savings_usd(1000, 800, 'claude-opus-4-8')` = 0.0014 < naive 0.005; unknown model → None.
- Budget-OSC inspect gate: `['tokens_used','token_limit','cost_usd','iteration','model']` unchanged (VOPT-08).
