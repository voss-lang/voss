# M5-04 Summary — Eval Summary + Pearson

## Status

Complete. Wave 3 now has the Markdown summary generator, Pearson correlation helper, and `.voss/.gitignore` regression guard.

## Changed

- Added `voss/eval/summary.py` with `_read_rows`, `_pearson`, and `write_summary`.
- Wired `voss/eval/runner.py` to generate `summary.md` unconditionally after writing `runs.jsonl`; the Plan 03 `ImportError` guard is removed.
- Added Pearson tests for reference matching, null-row dropping, constant-input guards, and empty input.
- Added summary Markdown tests for required sections, per-task rows, and all-null stub cost rendering as `mean cost: n/a`.
- Added `.voss/.gitignore` regression tests proving `eval/` is not ignored while `sessions/` remains ignored.
- Updated `M5-VALIDATION.md` to mark Wave 3 complete.

## Summary Output

`write_summary(jsonl_path, summary_path)` writes:

- run count
- provider/model
- overall success rate
- mean cost
- `conf_corr_r`
- per-task table with runs, pass rate, and mean cost

## Pearson Guards

`_pearson(rows)` returns `(None, n)` for:

- fewer than 2 valid confidence/success pairs
- constant confidence input
- constant success input
- empty input as `(None, 0)`

Otherwise it uses stdlib `statistics.correlation`; no scipy dependency was added.

## Verification

- `pytest -q -m "not slow and not live" tests/eval/test_pearson.py tests/eval/test_summary_md.py tests/eval/test_gitignore.py` → `8 passed`
- `pytest tests/eval -q` → `23 passed, 7 skipped`
