---
phase: V19-semantic-code-memory-tiered-index-routing
plan: 06
subsystem: code-intel
tags: [enrichment, model-router, tiered-routing, cost-ledger, fail-closed]
requires:
  - "V19-02 (CodeIndex.build)"
  - "V19-03 (CodeIndexService session_id threading)"
provides:
  - "config: get_index_enrich_model() (fail-closed None) + get_code_recall_config() (enrich_profile/enrich_budget_tokens/inject)"
  - "CodeIndex._run_enrichment: index_enrich role dispatch, budget-cap clean abort, method=enrich ledger row"
affects: [V19-05]
tech-stack:
  added: []
  patterns:
    - "fail-closed guard BEFORE any provider construction: not enrich_profile or model is None → return (Pitfall 7/D-06)"
    - "catalog find_by_id → fallback bare ModelEntry (litellm-routable id, env-key via litellm)"
    - "ledger row original_tokens_est=0 so the saved>=0 clamp can't fabricate savings (cost line)"
key-files:
  created: []
  modified:
    - voss/harness/config.py
    - voss/harness/code/semantic_index.py
key-decisions:
  - "enrich_budget_tokens default 0 = no spend allowed even with profile on (cap pre-checked per chunk)"
  - "provider resolved via model_router MODULE attribute (build_provider_for_model) so the stub_provider fixture and future instrumentation intercept"
  - "token accounting = conservative (len(prompt)+len(summary))//4 estimate — stub/offline providers expose no usage; real usage wiring can replace later without contract change"
  - "summaries embedded as doc suffix `\\n\\n# summary: ...` + metadata {enriched, summary}; un-enriched chunks left untouched (the 'marked' state = absence of summary)"
  - "per-chunk failures swallowed (enrichment never breaks a build); ledger row written once per batch incl. cap-aborts"
requirements-completed: [VSEM-07, VSEM-08]
duration: 15 min
completed: 2026-06-12
---

# Phase V19 Plan 06: Enrichment Role + Cost Guardrails Summary

Opt-in, fail-closed enrichment: `index_enrich` model-tier role + `[code_recall]` config section in config.py; `CodeIndex._run_enrichment` dispatches per-chunk one-line summaries through that role (never the session model), pre-checks `enrich_budget_tokens` per chunk for a clean mid-batch abort, embeds summaries alongside chunk text, and writes a distinct `method="enrich"` row to the session-scoped token-savings ledger `/cost` reads.

- Duration: ~15 min (commits 3e86fc1 + edc0b25, 2026-06-12)
- Tasks: 2/2 (config accessors · _run_enrichment)
- Files: 2 modified

## Verification Log (acceptance gates)

- `test_enrichment.py` 5/5: profile-off zero provider calls · routes only via `test-enrich-model` · fail-closed on missing config · tiny-cap clean abort with valid index · `method=="enrich"` row at `.voss/sessions/test-session/token-savings.jsonl` — PASS
- defaults runtime-verified: `get_index_enrich_model()` → None, `get_code_recall_config()` → {False, 0, True}; parsed config round-trips {True, 123, False} — PASS
- provider constructed ONLY post-guard; prompt fences chunk text; output stored as metadata one-liner — source review PASS
- full non-golden suite: only V19-05's injection×3 remain RED; `tests/memory/` 12 green — PASS

## Deviations from Plan

- **[Rule 1 - interface mismatch] find_entry needs (groups, provider_id, model_id)** — plan sketched `find_entry(enrich_model)`; the role config carries no provider_id. Used `find_by_id(load_catalog(), enrich_model)` first-hit with a bare litellm-routable `ModelEntry` fallback (offline/no-catalog path), so `"ollama/gpt-oss"`-style ids work without catalog presence.
- **[Noted] session_id fallback** — `build()` call site passes `session_id or "index-background"` per plan; no `None` ledger path possible.

**Total deviations:** 1 auto-fixed, 1 per-plan note. **Impact:** none.

## Next Phase Readiness

V19-05 (final, Wave 4) consumes `get_code_recall_config()["inject"]`; its injection trio is the only RED left. Phase Nyquist sign-off (V19-VALIDATION.md flip) happens there.

## Self-Check: PASSED
