---
phase: M5
plan: 04
type: execute
wave: 3
depends_on:
  - M5-03
files_modified:
  - voss/eval/summary.py
  - tests/eval/test_pearson.py
  - tests/eval/test_summary_md.py
  - tests/eval/test_gitignore.py
autonomous: true
requirements:
  - EVAL-02
  - EVAL-03
  - EVAL-04
must_haves:
  truths:
    - "`from voss.eval.summary import write_summary, _pearson` works."
    - "summary.md aggregates JSONL into: overall success rate, per-task success rate, mean cost overall + per-task, Pearson r (conf_corr_r), provider/model, run count."
    - "Pearson r is computed via stdlib `statistics.correlation` (no scipy)."
    - "_pearson returns `(None, n)` when fewer than 2 valid pairs or when all confidences/successes are constant."
    - "`.voss/.gitignore` (written by `write_voss_gitignore`) does NOT add `eval/` — eval reports stay git-tracked."
  artifacts:
    - path: "voss/eval/summary.py"
      provides: "Markdown generator + Pearson aggregator"
      exports: ["write_summary", "_pearson", "_read_rows"]
      contains: "from statistics import correlation"
    - path: "tests/eval/test_pearson.py"
      provides: "Pearson reference: matches statistics.correlation; drops null rows; constant-input guarded to None"
    - path: "tests/eval/test_summary_md.py"
      provides: "Generated summary.md contains required sections"
    - path: "tests/eval/test_gitignore.py"
      provides: "Regression guard: .voss/.gitignore content does NOT include eval/"
  key_links:
    - from: "voss/eval/summary.py"
      to: "stdlib statistics.correlation"
      via: "_pearson calls statistics.correlation on (confidence, success_01) pairs"
      pattern: "statistics\\.correlation"
    - from: "voss/eval/runner.py:run_suite"
      to: "voss/eval/summary.py:write_summary"
      via: "run_suite calls write_summary(jsonl_path, out / 'summary.md') after the row-write loop"
      pattern: "write_summary"
    - from: "tests/eval/test_gitignore.py"
      to: "voss/harness/cognition.py:write_voss_gitignore (line 581)"
      via: "test asserts written .gitignore content"
      pattern: "eval/"
---

<objective>
Land the Markdown summary generator and the Pearson r aggregator that aggregates a `runs.jsonl` file into a human-readable `summary.md`. Also pin the `.voss/.gitignore` regression: M2 D-09 must continue to ignore `sessions/` ONLY — never `eval/` — because eval reports are durable project knowledge (D-03).

Purpose: EVAL-04 is satisfied by the `conf_corr_r` line in `summary.md`. EVAL-02 (success rate) and EVAL-03 (mean cost) are surfaced in the same file. Plan 03's `run_suite` already calls `write_summary(...)` (guarded by ImportError until this plan lands); after this plan, remove that guard.

Output: `voss/eval/summary.py` (~80 LOC, stdlib + json + statistics only), three pytest files pinning Pearson computation, Markdown shape, and the `.voss/.gitignore` regression.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md
@.planning/phases/M5-eval-and-distribution-prep/M5-RESEARCH.md
@.planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md
@.planning/phases/M5-eval-and-distribution-prep/M5-03-PLAN.md
@voss/harness/cognition.py

<interfaces>
<!-- Existing .voss/.gitignore writer — voss/harness/cognition.py:575-582 -->
# def write_voss_gitignore(cwd: Path) -> bool:
#     target = voss_dir(cwd) / ".gitignore"
#     voss_dir(cwd).mkdir(parents=True, exist_ok=True)
#     if target.exists():
#         return False
#     target.write_text("# voss session state and rebuildable cache\nsessions/\n")
#     return True

<!-- stdlib Pearson — statistics.correlation (python 3.10+; pyproject pins 3.11+) -->
# from statistics import correlation
# r = correlation([0.9, 0.7, 0.3], [1.0, 1.0, 0.0])

<!-- D-04 JSONL row keys (15) — see Plan 03 -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: voss/eval/summary.py — write_summary + _pearson + tests</name>
  <files>voss/eval/summary.py, tests/eval/test_pearson.py, tests/eval/test_summary_md.py</files>
  <read_first>
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"voss/eval/summary.py" (lines 652-738) — exact target shape
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"tests/eval/test_pearson.py" (lines 1120-1163) — three test cases
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"tests/eval/test_summary_md.py" (lines 1172-1206) — required-sections assert
    - .planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md §D-02, D-15 — summary contents + Pearson reporting
    - .planning/phases/M5-eval-and-distribution-prep/M5-RESEARCH.md §"Pattern 5" + §Assumption A6 — constant-input guard
    - .planning/phases/M5-eval-and-distribution-prep/M5-VALIDATION.md rows `pearson-correlation`, `markdown-summary-shape`
    - voss/harness/recorder.py — dict aggregation style for the per-task table
  </read_first>
  <behavior>
    - `from voss.eval.summary import write_summary, _pearson, _read_rows` works.
    - `_pearson(rows)` returns `(None, 0)` when rows is empty.
    - `_pearson(rows)` returns `(None, k)` when fewer than 2 rows have BOTH confidence and success non-null.
    - `_pearson(rows)` returns `(None, k)` when all confidences are identical OR all successes are identical (guards against StatisticsError per RESEARCH Assumption A6).
    - `_pearson(rows)` otherwise returns `(r, n)` where `r == statistics.correlation([conf_i], [1.0 if success_i else 0.0])` over the n valid rows.
    - `write_summary(jsonl_path, summary_path)` reads the JSONL file (one JSON object per line, skipping blank lines), aggregates, and writes a Markdown file containing the following exact substrings (M5-VALIDATION row `markdown-summary-shape`):
      - `overall success rate` (case-sensitive)
      - `mean cost`
      - `conf_corr_r` (exact field name — pinned grep target)
      - Per-task table header `| task | runs | pass rate | mean cost |`
      - Each unique `task_id` from the JSONL appearing as `` `<task_id>` `` (backtick-quoted) in the per-task table
    - `write_summary` returns the summary path (`summary_path`).
    - `mean cost` line displays `n/a` when all rows have `cost_usd = None` (stub-mode case per CONTEXT D-11).
  </behavior>
  <action>
    Create `voss/eval/summary.py` per M5-PATTERNS.md lines 666-738:

    Module docstring `"""Markdown summary generator + Pearson r aggregator (M5 D-15, EVAL-04)."""`.

    Imports (stdlib only):
    - `from __future__ import annotations`
    - `import json`, `import statistics`
    - `from collections import defaultdict`
    - `from pathlib import Path`

    Function `_read_rows(jsonl_path: Path) -> list[dict]`:
    - Read text; split lines; for each non-blank line, `json.loads(line)`. Return list.

    Function `_pearson(rows: list[dict]) -> tuple[float | None, int]`:
    - Build `pairs = [(r["confidence"], 1.0 if r["success"] else 0.0) for r in rows if r["confidence"] is not None and r["success"] is not None]`. Treat `success` as truthy/falsy — explicit Python boolean.
    - If `len(pairs) < 2`: return `(None, len(pairs))`.
    - `confs, succs = zip(*pairs)`.
    - If `len(set(confs)) < 2 or len(set(succs)) < 2`: return `(None, len(pairs))` — statistics.correlation raises on constant input (RESEARCH Assumption A6); guard returns None.
    - Else: return `(statistics.correlation(confs, succs), len(pairs))`.

    Function `write_summary(jsonl_path: Path, summary_path: Path) -> Path`:
    - `rows = _read_rows(jsonl_path)`.
    - `by_task: defaultdict(list)`; for each row, append to `by_task[row["task_id"]]`.
    - `total = len(rows)`; `scored = [r for r in rows if r["success"] is not None]`; `passes = sum(1 for r in scored if r["success"])`; `overall_rate = passes / len(scored) if scored else 0.0`.
    - `costs = [r["cost_usd"] for r in rows if r["cost_usd"] is not None]`; `mean_cost = sum(costs) / len(costs) if costs else None`.
    - `r, n = _pearson(rows)`.
    - `provider = rows[0]["provider"] if rows else "n/a"`; `model = rows[0]["model"] if rows else "n/a"`.
    - Compose the Markdown body per M5-PATTERNS.md lines 712-735:
      - Header line: `# voss eval — {jsonl_path.parent.name}`.
      - Bulleted top section:
        - `- runs: {total}`
        - `- provider: \`{provider}\` · model: \`{model}\``
        - `- overall success rate: {overall_rate:.0%} ({passes}/{len(scored)})`
        - `- mean cost: {('$%.4f' % mean_cost) if mean_cost is not None else 'n/a'}`
        - `- conf_corr_r: {('%.3f' % r) if r is not None else 'n/a'} (n={n})`
      - `## Per-task` section with Markdown table headers `| task | runs | pass rate | mean cost |` and the alignment row `|------|-----:|----------:|----------:|`.
      - For each `tid in sorted(by_task)`: compute `tp` (passes), `len(ts)` (scored), `tmc` (per-task mean cost or None); append `| \`{tid}\` | {len(trs)} | {rate} | {cost_s} |` where `rate = f"{tp/len(ts):.0%}" if ts else "n/a"` and `cost_s = f"${tmc:.4f}" if tmc is not None else "n/a"`.
    - `summary_path.write_text("\n".join(lines) + "\n")`; return `summary_path`.

    **No scipy.** Pearson via stdlib only (RESEARCH §"Don't Hand-Roll" + Standard Stack lines 34).

    **Update Plan 03 cross-cut:** Remove the `try/ImportError: pass` guard around `from .summary import write_summary; write_summary(jsonl_path, out / "summary.md")` in `voss/eval/runner.py:run_suite` (introduced in Plan 03 to keep the stub smoke working pre-Plan-04). After this plan merges, summary generation is unconditional.

    Create `tests/eval/test_pearson.py` per M5-PATTERNS.md lines 1124-1163:
    - `import pytest`, `import statistics`, `from voss.eval.summary import _pearson`.
    - `test_pearson_matches_reference`: 4-row fixture with mixed confidences and successes; assert returned r matches `statistics.correlation(...)` via `pytest.approx`; assert n == 4.
    - `test_pearson_drops_null_rows`: 3-row fixture where one row has `confidence=None` and another has `success=None`; assert returned n == 1, r is None (n < 2).
    - `test_pearson_constant_returns_none`: 2-row fixture with identical confidences (e.g., both 0.5); assert r is None (constant-input guard).
    - Add a fourth test `test_pearson_empty_returns_none_zero`: empty list → `(None, 0)`.

    Create `tests/eval/test_summary_md.py` per M5-PATTERNS.md lines 1183-1206:
    - `_write_rows(path, rows)` helper writes `\n`.join(json.dumps(r) for r in rows).
    - `test_summary_has_required_sections(tmp_path)`: write 2 rows (one pass, one fail) to a temp jsonl; call `write_summary(jsonl, tmp_path/"summary.md")`; read the returned file; assert all required substrings present:
      - `"overall success rate"`
      - `"mean cost"`
      - `"conf_corr_r"`
      - `"01-analyze"` and `"02-plan-only"` (verifying per-task lines)
      - `"| task | runs | pass rate | mean cost |"`
    - Add a second test `test_summary_handles_all_null_cost(tmp_path)`: 2 rows with `cost_usd=None`; written summary contains `"mean cost: n/a"` exactly.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest -q -m "not slow and not live" tests/eval/test_pearson.py tests/eval/test_summary_md.py</automated>
  </verify>
  <done>
    `voss/eval/summary.py` exists with `_read_rows`, `_pearson`, `write_summary` exports. Pearson matches stdlib statistics.correlation. Constant-input + empty + null-row guards return (None, k). summary.md contains all required substrings (overall success rate, mean cost, conf_corr_r, per-task table). The ImportError guard in `voss/eval/runner.py` introduced in Plan 03 is removed.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: .voss/.gitignore regression guard — eval/ NOT ignored</name>
  <files>tests/eval/test_gitignore.py</files>
  <read_first>
    - voss/harness/cognition.py:575-582 — `write_voss_gitignore` writes `"# voss session state and rebuildable cache\nsessions/\n"`.
    - .planning/phases/M5-eval-and-distribution-prep/M5-CONTEXT.md §D-03 — eval reports durable; `.voss/.gitignore` must NOT add `eval/`.
    - .planning/phases/M2-project-cognition/M2-CONTEXT.md §D-09 — `.voss/.gitignore` content carry-forward decision (sessions/ only).
    - .planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md §"tests/eval/test_gitignore.py" (lines 1232-1249).
    - .planning/phases/M5-eval-and-distribution-prep/M5-VALIDATION.md row `voss-eval-gitignore`.
  </read_first>
  <behavior>
    - `write_voss_gitignore(tmp_path)` writes `.voss/.gitignore` containing `sessions/`.
    - The written content does NOT contain `eval/` (regression guard against accidentally adding it).
    - The written content continues to contain `sessions/` (M2 D-09 regression guard).
  </behavior>
  <action>
    Create `tests/eval/test_gitignore.py` per M5-PATTERNS.md lines 1232-1249:
    - Module docstring: `"""M5 D-03 / M2 D-09: .voss/.gitignore does NOT add eval/; .voss/eval/<ts>/ stays git-tracked."""`.
    - Import: `from pathlib import Path`; `from voss.harness.cognition import write_voss_gitignore`.
    - `test_voss_gitignore_does_not_ignore_eval(tmp_path)`: call `write_voss_gitignore(tmp_path)`; read `tmp_path / ".voss" / ".gitignore"`; assert the literal substring `"eval/"` is NOT in the content. Strengthen the check with `assert "eval" not in [line.strip() for line in content.splitlines() if not line.startswith("#")]` to permit `eval` appearing inside a comment but never as a pattern line.
    - `test_voss_gitignore_still_ignores_sessions(tmp_path)`: call `write_voss_gitignore(tmp_path)`; read; assert `"sessions/"` is IN the content (M2 D-09 regression guard).
    - This test is keyword-matchable as `pytest -k eval_tracked` per M5-VALIDATION row.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest -q -m "not slow and not live" tests/eval/test_gitignore.py</automated>
  </verify>
  <done>
    `tests/eval/test_gitignore.py` exists and both tests pass. Regression guard in place — any future edit to `voss/harness/cognition.py:write_voss_gitignore` that adds `eval/` will fail the first test.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| runs.jsonl → summary.md | Aggregator reads JSONL written by run_suite; passes through to Markdown without re-interpreting raw model output |
| .voss/.gitignore content → git index | A typo adding `eval/` would silently drop eval artifacts from git, losing the v0.1 quality baseline |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M5-04-pearson-wrong | T (Tampering) | _pearson | mitigate | `test_pearson_matches_reference` compares against `statistics.correlation` directly; `test_pearson_drops_null_rows` and `test_pearson_constant_returns_none` pin the guards. No silent zero on constant input. |
| T-M5-04-eval-gitignored | I (Info Disclosure) | .voss/.gitignore | mitigate | `test_voss_gitignore_does_not_ignore_eval` regression-guards the cognition.py:581 string literal. If a future developer extends the gitignore to "sessions/\neval/\n", this test fails loudly. |
| T-M5-04-summary-untrusted-spread | I (Info Disclosure) | write_summary | mitigate | write_summary reads only the D-04 allowlist fields from each row; never spreads `row` into a Markdown template. Rationale strings from judge are NOT interpolated into summary.md (only counts, rates, costs, the Pearson r number). |
</threat_model>

<verification>
- `pytest -q -m "not slow and not live" tests/eval/test_pearson.py tests/eval/test_summary_md.py tests/eval/test_gitignore.py` passes.
- `from voss.eval.summary import write_summary, _pearson` works.
- `voss/eval/runner.py` no longer wraps `from .summary import write_summary` in try/ImportError.
- No new top-level dependencies (stdlib only).
</verification>

<success_criteria>
1. `voss/eval/summary.py` exists with write_summary + _pearson exports.
2. Pearson r uses stdlib `statistics.correlation`; no scipy.
3. _pearson returns (None, k) on empty, n<2, or constant-input cases.
4. summary.md includes all required sections (overall rate, mean cost, conf_corr_r, per-task table).
5. .voss/.gitignore regression test passes (eval/ NOT in content; sessions/ remains).
6. Plan 03's ImportError guard around `from .summary import write_summary` is removed.
</success_criteria>

<output>
After completion, create `.planning/phases/M5-eval-and-distribution-prep/M5-04-SUMMARY.md` summarizing: write_summary section list, _pearson guard conditions (n<2, constant-input), the explicit removal of Plan 03's ImportError guard, and the gitignore regression-guard rationale.
</output>
