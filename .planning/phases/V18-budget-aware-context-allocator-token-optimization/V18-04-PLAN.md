---
phase: V18-budget-aware-context-allocator-token-optimization
plan: 04
type: execute
wave: 4
depends_on: ["V18-03-budget-aware-context-allocator-token-optimization"]
files_modified:
  - voss/harness/recorder.py
  - voss/harness/agent.py
  - voss/harness/cli.py
autonomous: true
requirements: [VOPT-05]
must_haves:
  truths:
    - "Each assembled turn appends one JSONL record to .voss/sessions/<id>/token-savings.jsonl with packed_tokens_est <= original_tokens_est ALWAYS (clamped; never phantom savings)"
    - "Under --no-pack the ledger records original_tokens_est == packed_tokens_est and saved_tokens_est == 0"
    - "The estimated $ saved nets prompt-cache reads (cache_read_input_token_cost from litellm) so it is not inflated; an unknown model yields saved_usd_est=null with no crash; the $ is labeled an estimate"
    - "/cost prints one honest line `context packed: ~X→~Y (−Z%) ~$… saved` sourced from the session ledger; figures are labeled estimates with no cumulative hero number"
    - "The savings line reuses the F3 _emit_context_osc surface additively (savings field added to the free-form payload); _emit_budget_osc's five-field shape is byte-unchanged"
  artifacts:
    - path: "voss/harness/recorder.py"
      provides: "_append_savings_record (JSONL append) + estimate_savings_usd (cache-netted $) + additive savings field on _emit_context_osc"
      contains: "_append_savings_record"
    - path: "voss/harness/agent.py"
      provides: "post-assembly call computing original_tokens_est (full replay) vs packed_tokens_est (packed) and writing the ledger row per iteration"
      contains: "_append_savings_record"
    - path: "voss/harness/cli.py"
      provides: "/cost reads the session ledger and prints the savings line"
      contains: "context packed"
  key_links:
    - from: "voss/harness/agent.py (post-assembly)"
      to: "recorder._append_savings_record"
      via: "writes {iter, original_tokens_est, packed_tokens_est, method, cache_read_tokens, saved_tokens_est, saved_usd_est, model, ts}"
      pattern: "_append_savings_record"
    - from: "voss/harness/cli.py _cost"
      to: ".voss/sessions/<id>/token-savings.jsonl"
      via: "read ledger rows from ctx.record.id + ctx.cwd, aggregate, echo savings line"
      pattern: "token-savings.jsonl"
    - from: "voss/harness/recorder.estimate_savings_usd"
      to: "litellm.model_cost"
      via: "input_cost_per_token + cache_read_input_token_cost netting; None on unknown model"
      pattern: "cache_read_input_token_cost"
---

<objective>
Make the savings falsifiable (VOPT-05, D-01..D-04): persist one honest JSONL record per assembled turn to the session-scoped `token-savings.jsonl`, enforce `packed <= original` as a hard invariant before write, net the dollar estimate against prompt-cache reads so it is never inflated, and surface one labeled line in `/cost` and the F3 context OSC. No new HUD, no cumulative hero number.

Purpose: Without the ledger and its invariants, any "saved N%" claim is unverifiable; the netting and the packed<=original clamp are what keep the numbers honest rather than marketing.

Output: recorder.py ledger + dollar helper, agent.py per-turn ledger write, cli.py `/cost` savings line — turning the VOPT-05 ledger/no-pack/cost-line/dollar-netting tests GREEN.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-SPEC.md
@.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-RESEARCH.md
@.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-PATTERNS.md
@.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-CONTEXT.md

<interfaces>
<!-- VERIFIED source seams. -->

recorder.py VERIFIED:
  :98-127  _emit_budget_osc(*, tokens_used, token_limit, cost_usd, iteration, model)  — FROZEN five-field shape; DO NOT change
  :130-140 _emit_context_osc(payload: dict)  — free-form dict; additive savings field OK (non-TTY guarded)

session.py VERIFIED:
  :57-58 _sessions_dir(cwd) -> (cwd/".voss"/"sessions").resolve()   — ledger root; ledger = _sessions_dir(cwd)/<id>/"token-savings.jsonl"

eval/runner.py VERIFIED (the JSONL-append analog to COPY):
  :100-103 _append_row(path, row): path.parent.mkdir(parents=True, exist_ok=True); with path.open("a") as fh: fh.write(json.dumps(row, sort_keys=True)+"\n")

agent.py VERIFIED:
  :713 the if/else seam (Plan 03) — original_tokens_est = tokens of the FULL-replay list (the else-branch output); packed_tokens_est = tokens of the packed list (the if-branch output). Compute BOTH at the seam so the delta is exact.
  :791 cache_read for this iter (IterationRecord.cache_read_input_tokens)
  :73-80 _default_token_count(text, *, model)  — the estimator for both figures

litellm.model_cost VERIFIED (LITELLM_LOCAL_MODEL_COST_MAP=true):
  model_cost["claude-opus-4-8"] = {input_cost_per_token: 5e-6, cache_read_input_token_cost: 5e-7, cache_creation_input_token_cost: 6.25e-6, ...}
  key fallback: model_cost.get(model) or model_cost.get(f"anthropic.{model}"); None if neither

cli.py VERIFIED:
  :881-918 _cost handler; flat-total echo at :912-918 — savings line appends AFTER this block; reads ctx.record.id + ctx.cwd

JSONL record schema (D-02/D-03/D-04):
  {iter:int, original_tokens_est:int, packed_tokens_est:int (<=original), method:str ("full"|"tiered-K{k}-M{m}"|"no-pack"),
   cache_read_tokens:int, saved_tokens_est:int (>=0), saved_usd_est:float|None (~, cache-netted), model:str, ts:str(ISO)}
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: recorder ledger write + cache-netted dollar estimate</name>
  <files>voss/harness/recorder.py</files>
  <read_first>
    - voss/eval/runner.py:100-103 (_append_row — copy this JSONL-append body verbatim for _append_savings_record)
    - voss/harness/session.py:57-58 (_sessions_dir — ledger path root; ledger is a SUBDIRECTORY <id>/token-savings.jsonl, NOT the flat <id>.json — PATTERNS critical note 5)
    - voss/harness/recorder.py:98-140 (_emit_budget_osc frozen shape; _emit_context_osc free-form payload to extend additively)
    - .planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-RESEARCH.md (Dollar netting formula + Pitfall 3 double-counting + Pitfall 6 litellm key mismatch + Pitfall 4 packed>original fallback)
    - tests/harness/test_savings_ledger.py (test_ledger_packed_le_original, test_no_pack_zero_savings, test_saved_usd_nets_cache_reads — the targets)
  </read_first>
  <behavior>
    - _append_savings_record(cwd, session_id, row): clamps packed_tokens_est to <= original_tokens_est and saved_tokens_est = max(original-packed, 0) BEFORE writing (Pitfall 4 hard invariant — phantom savings impossible by construction); writes one JSON line to _sessions_dir(cwd)/session_id/"token-savings.jsonl" via the _append_row body.
    - estimate_savings_usd(saved_tokens, cache_read_tokens, model): looks up litellm.model_cost.get(model) or .get(f"anthropic.{model}"); returns None if neither (no crash, ledger records null). Otherwise gross = saved_tokens*input_rate; cache_reduction = cache_read_tokens*(input_rate - cache_read_rate); returns max(gross - cache_reduction, 0.0). Never negative, never inflated by ignoring cache reads.
    - no-pack path: a row with method="no-pack" has original==packed and saved_tokens_est==0 (and saved_usd_est==0.0 or None).
  </behavior>
  <action>
    In voss/harness/recorder.py:
    - Add `_append_savings_record(cwd, session_id, row: dict)`: compute the ledger path via `from voss.harness.session import _sessions_dir` → `_sessions_dir(Path(cwd)) / str(session_id) / "token-savings.jsonl"`; clamp `row["packed_tokens_est"] = min(row["packed_tokens_est"], row["original_tokens_est"])` and `row["saved_tokens_est"] = max(row["original_tokens_est"] - row["packed_tokens_est"], 0)`; then mkdir parents + append `json.dumps(row, sort_keys=True)+"\n"` (the runner.py:100-103 body).
    - Add `estimate_savings_usd(saved_tokens, cache_read_tokens, model) -> float | None` per <behavior>, using the already-available litellm import (import litellm lazily if not present at module top; mirror agent.py:49-52). Read both input_cost_per_token and cache_read_input_token_cost (Pitfall 3). dict.get with None fallback (no exec, no format-string injection — Security V5).
    - Add a `savings` key into the `_emit_context_osc` payload at its call sites is NOT done here (that is the agent wiring in Task 2); here only ensure `_emit_context_osc` still accepts a free-form dict (it already does — no signature change). Leave `_emit_budget_osc` byte-unchanged.
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/harness/test_savings_ledger.py::test_ledger_packed_le_original tests/harness/test_savings_ledger.py::test_no_pack_zero_savings tests/harness/test_savings_ledger.py::test_saved_usd_nets_cache_reads -x` exits 0.
    - `.venv/bin/python -c "from voss.harness.recorder import estimate_savings_usd; v=estimate_savings_usd(1000, 800, 'claude-opus-4-8'); naive=1000*5e-6; assert v is not None and 0 <= v < naive, (v,naive); assert estimate_savings_usd(1000,0,'no-such-model') is None"` exits 0 (cache-netted, below naive, None on unknown model).
    - `.venv/bin/python -c "import ast; t=ast.parse(open('voss/harness/recorder.py').read()); src=open('voss/harness/recorder.py').read(); assert 'cache_read_input_token_cost' in src and 'def _append_savings_record' in src and 'def estimate_savings_usd' in src"` exits 0.
    - `grep -n "def _emit_budget_osc" voss/harness/recorder.py && .venv/bin/python -c "import inspect,voss.harness.recorder as r; sig=inspect.signature(r._emit_budget_osc); assert list(sig.parameters)==['tokens_used','token_limit','cost_usd','iteration','model'], list(sig.parameters)"` exits 0 (budget OSC shape frozen — VOPT-08).
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_savings_ledger.py -k "packed_le_original or no_pack_zero_savings or saved_usd_nets_cache_reads" -x -q</automated>
  </verify>
  <done>_append_savings_record writes to the <id> subdirectory with packed<=original clamped; estimate_savings_usd nets cache reads and returns None on unknown model; _emit_budget_osc signature unchanged (VOPT-08).</done>
</task>

<task type="auto">
  <name>Task 2: agent.py per-turn ledger write (original vs packed) + additive context-OSC savings field</name>
  <files>voss/harness/agent.py</files>
  <read_first>
    - voss/harness/agent.py:708-720 (the if/else seam from Plan 03 — both branches' outputs are available here to size original vs packed)
    - voss/harness/agent.py:73-80 (_default_token_count — size both message lists), :791 (cache_read for this iter), :920-995 (where the iteration record is finalized / where to place the post-assembly ledger write so cache_read is known)
    - voss/harness/recorder.py (_append_savings_record + estimate_savings_usd from Task 1; _emit_context_osc free-form payload)
    - .planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-RESEARCH.md (Savings Ledger section + Pitfall 8 eval-temp-dir: ledger lives/dies with the temp fixture, no special handling)
  </read_first>
  <action>
    In voss/harness/agent.py, at/after the seam (:713) compute `original_tokens_est` = sum of _default_token_count over the FULL-replay message contents (the else-branch rendering — render it for measurement even when packing is on; this is the honest baseline) and `packed_tokens_est` = sum over the actually-assembled replay contents (packed when on; identical to original when off). Determine `method`: "no-pack" when packing disabled, else f"tiered-K{profile.recent_full_k}-M{profile.digest_cutoff_m}", or "full" when the no-op-below-threshold path returned the verbatim full replay.
    After the iteration's usage is known (cache_read_input_tokens available, ~:791-940), build the row {iter:index, original_tokens_est, packed_tokens_est, method, cache_read_tokens, saved_tokens_est (recorder clamps), saved_usd_est: recorder.estimate_savings_usd(original-packed, cache_read, model), model, ts: ISO-now} and call `recorder._append_savings_record(cwd, session_id, row)`. Guard the whole block so a ledger failure never crashes the turn (try/except logging only — mirror the _default_token_count never-crash posture).
    Additively emit the savings on the existing F3 surface: when _emit_context_osc is already called for this iteration (F4 path), add a `"savings": {"original": original_tokens_est, "packed": packed_tokens_est, "pct": round(...)}` key to its payload dict. If no _emit_context_osc call exists on this path, do NOT add a new always-on emit (keep it additive to the existing surface, D-01 — no new HUD). Leave _emit_budget_osc calls untouched.
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/harness/test_savings_ledger.py -x -q` exits 0 (all ledger tests GREEN including the integration write).
    - `.venv/bin/python -m pytest tests/harness/test_agent_packing.py -x -q` exits 0 (ledger write did not disturb byte-identity/coherence).
    - `grep -n "_append_savings_record\|original_tokens_est\|packed_tokens_est" voss/harness/agent.py` shows the per-turn write wired.
    - `.venv/bin/python -m pytest tests/harness/test_recorder_iterations.py -q` exits 0 (recorder regression clean).
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_savings_ledger.py tests/harness/test_agent_packing.py -x -q</automated>
  </verify>
  <done>Per-turn ledger row written with exact original-vs-packed estimates and cache-netted $; ledger failures never crash a turn; savings emitted additively on the existing context OSC (no new HUD); budget OSC + byte-identity + coherence untouched.</done>
</task>

<task type="auto">
  <name>Task 3: /cost savings line from the session ledger</name>
  <files>voss/harness/cli.py</files>
  <read_first>
    - voss/harness/cli.py:881-918 (_cost handler; the flat-total echo at :912-918 — append the savings line AFTER it)
    - tests/harness/test_cost_slash.py:8-44 (fake_ctx fixture shape: record.id, record.cwd/ctx.cwd; _build_slash_registry + registry.lookup("/cost").handler + capsys)
    - voss/harness/session.py:57-58 (_sessions_dir — recompute the ledger path from ctx.record.id + ctx.cwd)
    - .planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-CONTEXT.md (D-01/D-03/D-04 wording: `context packed: X→Y (−Z%)` + `~$` suffix, labeled estimates, no cumulative hero number)
  </read_first>
  <action>
    In voss/harness/cli.py _cost (:881), after the existing flat-total echo block (:912-918), add: compute the ledger path `_sessions_dir(Path(ctx.cwd or ctx.record.cwd)) / str(ctx.record.id) / "token-savings.jsonl"`; if it exists, read rows (json.loads per non-empty line), sum original_tokens_est and packed_tokens_est across the session, compute pct = round((1 - packed/original)*100) when original>0 else 0, sum saved_usd_est skipping None; echo one line: `context packed: ~{original:,}→~{packed:,} tokens (−{pct}%)  ~${usd:.4f} saved` (the `~` labels these as estimates per D-03; omit the `~$…` clause when every saved_usd_est is None). If the ledger is absent or empty, print nothing extra (short runs / no packing → silent, matching "feels like nothing changed"). Guard with try/except so a malformed ledger never breaks /cost.
  </action>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/harness/test_savings_ledger.py::test_cost_slash_prints_savings_line -x` exits 0.
    - `grep -n "context packed:" voss/harness/cli.py` shows the line; `grep -n "token-savings.jsonl" voss/harness/cli.py` shows the ledger read.
    - `.venv/bin/python -m pytest tests/harness/test_cost_slash.py -q` exits 0 (existing /cost behavior — flat total, --by-model, --by-tool — still green; savings line is additive).
  </acceptance_criteria>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_savings_ledger.py::test_cost_slash_prints_savings_line tests/harness/test_cost_slash.py -q</automated>
  </verify>
  <done>/cost reads the session ledger and prints one labeled `context packed: ~X→~Y (−Z%) ~$… saved` line (silent when no ledger); existing /cost flags unaffected; estimate labeling + no-hero-number honored.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| session_id → ledger path | Untrusted-ish id used in a filesystem path; the dollar estimate must net cache billing to avoid an inflated public figure |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V18-10 | Tampering (path traversal) | ledger path from session_id | mitigate | Path built via _sessions_dir(cwd).resolve()/str(session_id)/... — the SAME traversal-safe convention as the existing flat session JSON; session ids are pre-existing UUIDs (Security V5). No user-controlled raw path concatenation. |
| T-V18-11 | Spoofing (phantom savings) | ledger row | mitigate | packed clamped <= original and saved = max(original-packed,0) in _append_savings_record BEFORE write; test_ledger_packed_le_original + test_no_pack_zero_savings assert the invariant; impossible to record packed>original or savings>original |
| T-V18-12 | Information disclosure (inflated $) | estimate_savings_usd | mitigate | Nets cache_read_input_token_cost (Pitfall 3); $ labeled `~estimate`; clamped >= 0; unknown model → null (no fabricated figure) |
| T-V18-13 | Information disclosure (secret in ledger) | row fields | mitigate | The row carries only integer token counts, a method string, a model string, and a timestamp — NO message content, NO tool args/results. Redaction in the message chain (T-V18-03) is upstream; the ledger never re-introduces detail. |
| T-V18-SC | Tampering | npm/pip/cargo installs | accept | No new packages; litellm already in venv. No install task. |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/test_savings_ledger.py tests/harness/test_agent_packing.py tests/harness/test_cost_slash.py tests/harness/test_recorder_iterations.py -q` GREEN.
- `_emit_budget_osc` five-field signature unchanged (VOPT-08 OSC-shape gate from Task 1).
- Ledger row has packed<=original always; --no-pack ⇒ original==packed; $ nets cache reads and is null on unknown model.
- /cost prints the labeled savings line; silent when no ledger.
</verification>

<success_criteria>
- recorder.py: _append_savings_record (clamped, subdirectory path) + estimate_savings_usd (cache-netted, None-safe).
- agent.py: per-turn ledger write with exact original-vs-packed; additive context-OSC savings; never crashes a turn.
- cli.py: /cost savings line from the session ledger, labeled estimates, no hero number.
- All VOPT-05 tests GREEN; budget OSC shape frozen; byte-identity/coherence regressions clean.
</success_criteria>

<output>
Create `.planning/phases/V18-budget-aware-context-allocator-token-optimization/V18-04-SUMMARY.md` when done.
</output>
