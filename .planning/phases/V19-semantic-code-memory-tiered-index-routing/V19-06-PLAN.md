---
phase: V19-semantic-code-memory-tiered-index-routing
plan: 06
type: execute
wave: 3
depends_on: [V19-02, V19-03]
files_modified:
  - voss/harness/config.py
  - voss/harness/code/semantic_index.py
autonomous: true
requirements: [VSEM-07, VSEM-08]
must_haves:
  truths:
    - "With the enrichment profile OFF (default), a full index build performs ZERO LLM provider calls"
    - "With the profile ON, per-chunk summary calls route through the index_enrich router role, never the session model"
    - "Profile ON but no index_enrich configured → enrichment stays disabled (fail-closed, no fallback to session model)"
    - "A tiny enrich_budget_tokens cap aborts the enrichment batch cleanly; the index stays valid and un-enriched chunks are marked"
    - "Enrichment spend appears as a distinct method=enrich row in token-savings.jsonl, surfaced by /cost"
  artifacts:
    - path: "voss/harness/config.py"
      provides: "get_index_enrich_model() + get_code_recall_config() (enrich_profile, enrich_budget_tokens, inject)"
      contains: "get_index_enrich_model"
    - path: "voss/harness/code/semantic_index.py"
      provides: "CodeIndex._run_enrichment (role dispatch, budget cap, ledger row)"
      contains: "_run_enrichment"
  key_links:
    - from: "CodeIndex._run_enrichment"
      to: "model_router.build_provider_for_model via get_index_enrich_model()"
      via: "role-resolved provider, fail-closed"
      pattern: "get_index_enrich_model"
    - from: "CodeIndex._run_enrichment"
      to: "recorder._append_savings_record"
      via: "method=enrich ledger row"
      pattern: "method.*enrich"
---

<objective>
Add the opt-in enrichment path: an `index_enrich` model-router role (config), a `CodeIndex._run_enrichment` that dispatches per-chunk one-line summaries through that role (NEVER the session model), a `enrich_budget_tokens` cap that aborts cleanly mid-batch, and a distinct `method="enrich"` ledger row visible in `/cost` (VSEM-07, VSEM-08).

Purpose: Move index-maintenance spend off the frontier model — the phase's headline token-economics frame. Profile is OFF by default and fail-closed without config (D-06/D-12): zero LLM calls when off.
Output: config accessors + `_run_enrichment`. The `inject` off-switch flag is parsed here (in `get_code_recall_config`) and consumed by V19-05 (Wave 4). This plan is Wave 3 (serialized after V19-03 on semantic_index.py).
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-SPEC.md
@.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-CONTEXT.md
@.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-PATTERNS.md

<interfaces>
voss/harness/config.py:
  _parse_model_tiers_section(text) -> dict ; get_model_tiers() -> dict   # config.py:222-258 (pattern to extend)
  _DEFAULT_MODEL_TIERS: {"strong","cheap","fast"}                        # add index_enrich (absent/None default)
  config_path() ; section-parse pattern (e.g. _parse_net_rate_limits_section config.py:152-207)

voss/harness/model_router.py:
  resolve_key(...)                       # model_router.py:32 — auth/env/keyring (never log)
  find_entry(model_id)                   # model_router.py:151
  build_provider_for_model(...)          # model_router.py:102 — LiteLLMProvider build

voss/harness/recorder.py:
  _append_savings_record(cwd, session_id, record)   # recorder.py:143-161; clamps packed<=original

voss/harness/code/semantic_index.py (V19-02):
  CodeIndex.build(self, session_id: str | None = None) -> None  # add enrichment call site guarded by profile+config; session_id threads to the ledger row (falls back to "index-background" when None)
</interfaces>

<!-- D-06 fail-closed: absent index_enrich config => enrichment unavailable even if enrich_profile=true; NEVER fall back to session model. -->
<!-- Pitfall 7: profile-off MUST produce zero LLM calls — guard ALL enrichment paths behind `if enrich_profile and enrich_model_configured`; no eager provider init. -->
<!-- D-12: enrichment unit = per-chunk one-liner, embedded alongside code text, parallelizable batches. -->
<!-- Ledger note (PATTERNS): _append_savings_record forces saved>=0; send original_tokens_est=0 for enrich rows (cost line, no savings claim). -->
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: index_enrich role + code_recall config section</name>
  <read_first>
    - tests/code_recall/test_enrichment.py (RED tests: test_fail_closed_no_config, and the config-dependent setup for routes/budget/cost tests)
    - voss/harness/config.py (lines 222-258 _parse_model_tiers_section/get_model_tiers; 152-207 a section-parse analog; _DEFAULT_MODEL_TIERS)
    - .planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-PATTERNS.md (config.py section: get_index_enrich_model, get_code_recall_config)
    - .planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-CONTEXT.md (D-06, D-12)
  </read_first>
  <files>voss/harness/config.py</files>
  <action>Extend `config.py`. Add `index_enrich` to the model-tier resolution as a named role: either add `"index_enrich": None` to `_DEFAULT_MODEL_TIERS` or rely on absence so `get_model_tiers().get("index_enrich")` returns None by default. Add `get_index_enrich_model() -> str | None` returning `get_model_tiers().get("index_enrich")` (absent → None = enrichment unavailable, fail-closed per D-06). Add a `[code_recall]` section parser following the existing section-parse pattern (mirror `_parse_model_tiers_section` / the net-rate-limits parser at config.py:152-207): `_parse_code_recall_section(text) -> dict` and `get_code_recall_config() -> dict` returning a merged dict with keys: `enrich_profile: bool` (default False — OFF per VSEM-07), `enrich_budget_tokens: int` (default e.g. 0 = no enrichment / or a documented default cap), `inject: bool` (default True — the V19-05 off-switch reads this). Missing file and missing section both return the defaults (never raise). Document in a docstring/comment the example config: `[models] index_enrich = "ollama/gpt-oss"` (Ollama-local default per D-12) with a Haiku-class alternate noted.</action>
  <verify>
    <automated>.venv/bin/python -c "from voss.harness.config import get_index_enrich_model, get_code_recall_config; c=get_code_recall_config(); print(get_index_enrich_model(), c['enrich_profile'], c['inject'])"</automated>
  </verify>
  <acceptance_criteria>
    - `get_index_enrich_model()` returns None when no `index_enrich` configured (fail-closed default)
    - `get_code_recall_config()` returns `enrich_profile=False`, an `enrich_budget_tokens` int, and `inject=True` by default
    - both accessors return defaults (no raise) when the config file is absent (source review of the read-or-default guard)
    - `grep -n "index_enrich" voss/harness/config.py` shows the role accessor; a comment documents the Ollama-local example (D-12)
  </acceptance_criteria>
  <done>index_enrich role accessor + [code_recall] config section (enrich_profile OFF, enrich_budget_tokens, inject) with fail-closed defaults.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: CodeIndex._run_enrichment — role dispatch, budget cap, ledger row</name>
  <read_first>
    - tests/code_recall/test_enrichment.py (RED tests: test_profile_off_zero_llm, test_routes_index_enrich_role, test_budget_cap_abort, test_cost_ledger_line — read exact stub_provider assertions)
    - tests/code_recall/conftest.py (stub_provider fixture — what it patches and records)
    - voss/harness/code/semantic_index.py (CodeIndex.build from V19-02 — the call site to guard)
    - voss/harness/model_router.py (lines 32 resolve_key; 102 build_provider_for_model; 151 find_entry)
    - voss/harness/recorder.py (lines 143-161 _append_savings_record — record fields + clamping)
    - .planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-RESEARCH.md (Pattern 8 ledger row; Pitfall 7 zero-LLM guard)
  </read_first>
  <files>voss/harness/code/semantic_index.py</files>
  <action>Add `CodeIndex._run_enrichment(self, chunks, *, session_id, cwd)` to `semantic_index.py`. FIRST guard (Pitfall 7 / D-06): read `cfg = get_code_recall_config()` and `enrich_model = get_index_enrich_model()`; if `not cfg["enrich_profile"]` OR `enrich_model is None`, RETURN immediately — zero provider construction, zero LLM calls (fail-closed). Only when both pass: build the enrichment provider via `find_entry(enrich_model)` + `build_provider_for_model(...)` from model_router (NEVER the session model — VSEM-07). For each chunk, send a one-line-summary prompt that WRAPS the chunk text in a fenced context block (prompt-injection mitigation — output is a one-liner stored as metadata, never executed); accumulate `total_enrich_tokens`. Enforce the budget: before/after each chunk check `total_enrich_tokens >= cfg["enrich_budget_tokens"]` → BREAK the loop cleanly (VSEM-08); chunks not yet enriched are marked (e.g. metadata `enriched=False` / left without a summary) and the index remains valid/queryable. Embed produced summaries alongside the chunk's code text (D-12) by upserting them into the summary's chunk metadata/document. After the batch (or on cap-abort), write ONE ledger row via `recorder._append_savings_record(cwd, session_id, {...})` with `method="enrich"`, `original_tokens_est=0` (cost line, no savings claim — avoids the saved>=0 clamp inflating savings per PATTERNS), `enrichment_tokens_used=total_enrich_tokens`, `enrichment_chunks=enriched_count`, `model=enrich_model`, `saved_usd_est=None`, `iter=0`, `ts=<utc iso>`. Wire the call: change the `CodeIndex.build` signature to `build(self, session_id: str | None = None) -> None` (propagated from the V19-02 build signature and the V19-03 `CodeIndexService`/`make_toolset` call site), and AFTER the upsert pass call `self._run_enrichment(changed_chunks, session_id=(session_id or "index-background"), cwd=self._cwd)`. NEVER pass a literal ellipsis or `None` straight through — a `None` session_id would route the ledger row to `.voss/sessions/None/` which `/cost` never reads. Use the explicit `"index-background"` fallback for sessionless background builds so the row still lands at a real, `/cost`-readable path. The internal guard makes `_run_enrichment` a no-op when the profile is off, so the default-off build still does zero LLM calls.</action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/code_recall/test_enrichment.py -x -q 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `test_profile_off_zero_llm` passes: full build with profile off → `stub_provider.call_count == 0`
    - `test_routes_index_enrich_role` passes: profile on → enrichment calls use the index_enrich model, not the session model
    - `test_fail_closed_no_config` passes: profile on but no index_enrich config → zero calls (no session-model fallback)
    - `test_budget_cap_abort` passes: tiny cap → clean break, index still valid/queryable, un-enriched chunks marked
    - `test_cost_ledger_line` passes: with a deterministic `session_id` passed to `build()`, the `method="enrich"` row lands in the session-scoped `token-savings.jsonl` at the SAME path `/cost` reads (assert the row's session-scoped path, not just that some row was appended); a `None` session_id resolves to the `"index-background"` path, never `.voss/sessions/None/`
    - enrichment provider is constructed ONLY inside the post-guard branch (no eager init at __init__/module import) — source review (Pitfall 7)
    - enrichment prompt wraps chunk text in a fenced block and stores only a one-liner as metadata (source review — injection mitigation)
  </acceptance_criteria>
  <done>_run_enrichment routes via index_enrich role with fail-closed guard, budget-cap clean abort, and a method=enrich ledger row; default-off build does zero LLM calls.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| chunk text → enrichment LLM prompt | raw source code crosses into a provider prompt |
| config → enrich model role | operator config selects which model handles index jobs |
| enrichment provider key → process | resolved via auth, must never be logged |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V19-06-01 | Elevation of Privilege | enrichment dispatch when profile off / unconfigured | mitigate | Fail-closed guard: `if not enrich_profile or enrich_model is None: return` BEFORE any provider build; profile-off build = zero LLM calls (VSEM-07, Pitfall 7, instrumented test) |
| T-V19-06-02 | Spoofing | prompt injection via code chunk text | mitigate | Chunk text wrapped in a fenced context block; model output is a one-liner stored as metadata, never executed/eval'd (RESEARCH Security Domain) |
| T-V19-06-03 | Information Disclosure | enrichment provider key leakage | mitigate | Key resolved via existing `resolve_key()` (env/keyring); never logged, never in ledger row or stderr (existing model_router pattern) |
| T-V19-06-04 | Denial of Service | runaway enrichment spend | mitigate | `enrich_budget_tokens` cap aborts the batch cleanly mid-run; spend recorded as a distinct ledger line (VSEM-08) |
| T-V19-06-05 | Tampering | stale enrichment summaries | mitigate | Summaries keyed to chunk ids; re-chunk on file change deletes old ids + their summaries (manifest hash check) — no stale summary survives a content change |
| T-V19-SC | Tampering | npm/pip/cargo installs | accept | No new packages (RESEARCH Package Legitimacy Audit: zero new deps; index_enrich uses existing LiteLLMProvider) |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/code_recall/test_enrichment.py -q` — green
- Coherence guard: default-off `CodeIndex(cwd).build()` issues zero provider calls (instrumented by test_profile_off_zero_llm)
</verification>

<success_criteria>
- index_enrich role + [code_recall] config section, fail-closed defaults, profile OFF
- _run_enrichment: zero LLM when off, routes via index_enrich when on, budget cap clean abort, method=enrich ledger row in /cost
</success_criteria>

<output>
Create `.planning/phases/V19-semantic-code-memory-tiered-index-routing/V19-06-SUMMARY.md` when done
</output>
