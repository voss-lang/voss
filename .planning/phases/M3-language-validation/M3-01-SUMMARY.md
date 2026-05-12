---
phase: M3
plan: 01
status: complete
date: 2026-05-11
---

# M3-01 Summary — D-03 static-only check + sentinel

## Change locations

### voss/analyzer.py (line range 479-508)
`_visit_match_stmt` restructured. Order:
1. Scrutinee inference (`self._infer_expr(match.scrutinee)`).
2. Per-case loop: collect `similar_pairs`, walk `case.body` for static validation.
3. Empty short-circuit: `if not similar_pairs: return`.
4. Compute `threshold` and `match_id` (shared by both branches).
5. **NEW D-03 guard** (line 493): `if not self.emit_indexes:` → append `{"match_id", "threshold", "cases": []}` row and return. Inline comment `# D-03: static-only check — skip embedding build, keep static signature validation.`.
6. Live path unchanged: allocate `SemanticMatcherIndexBuilder` lazily, call `build_cases`, append full row.

### voss/diagnostics.py (line 42)
`AnalysisResult.match_entries: tuple[dict, ...] = ()` added so plan verify commands (`r.match_entries`) work and downstream M3 waves can introspect static-check output without reaching into the analyzer instance. Default `()` keeps backward compatibility.

### voss/analyzer.py (line 437-441)
`analyze_program` return now passes `match_entries=tuple(self._match_entries)` to `AnalysisResult`.

### tests/examples/test_check_speed.py (NEW)
Single test `test_check_does_not_load_hf_encoder`. Module docstring, `CHECK_CEILING_SECONDS = 2.0` carry-forward constant for M3-06, `REPO_ROOT` helper.

## Sentinel test signature and assertions

```python
def test_check_does_not_load_hf_encoder() -> None:
    from voss import analyze, parse
    src = (REPO_ROOT / "samples" / "support.voss").read_text()
    program = parse(src, file="samples/support.voss")
    result = analyze(program, source_path="samples/support.voss", emit_indexes=False)
    assert result.ok, [d.message for d in result.diagnostics]
    offenders = sorted(k for k in sys.modules if "sentence_transformers" in k)
    assert offenders == [], f"D-03 violated: sentence_transformers loaded: {offenders}"
```

- Case-sensitive substring match against `sys.modules` keys.
- Runs in-process; pytest collection itself does not import `sentence_transformers`.
- File-alphabetical order places it before live-example tests that may trigger HF loads.

## Wall-clock measurements (`samples/support.voss`)

| Run | Before (baseline pre-fix) | After (D-03) |
|-----|---------------------------|--------------|
| Cold | ~8.9s (loaded HF encoder) | 1.68s |
| Warm | ~8.9s (re-loaded each invocation) | **1.18s** |

Warm wall-clock is well under the 2.0s acceptance ceiling. Cold start drops because process never touches `voss_runtime.semantic.SemanticMatcher` (no HF model load, no torch import).

## emit_indexes=True path unchanged

Confirmed via:
- `pytest tests/analyzer/ -q` → 29 passed (all pre-existing tests use the live builder via `FakeIndexBuilder` or real path).
- `pytest tests/codegen/ -q` → green (codegen path uses `emit_indexes=True`).
- `pytest tests/cli/test_check.py -q` → green.
- Per-row shape for `emit_indexes=True` retains real `cases` from `build_cases`; `_emit_program_index` gate at analyzer.py:435 is untouched.

## Scope note

Plan `files_modified` listed only `voss/analyzer.py` + `tests/examples/test_check_speed.py`. To satisfy the Task 1 `<verify><automated>` assertion `len(r.match_entries) >= 1`, `AnalysisResult` needed a public `match_entries` field. Single-line additive change to `voss/diagnostics.py` (new field with default `()`). No behavior change for any caller that does not opt in to read it.

## M3-06 hand-off

- **File to extend**: `tests/examples/test_check_speed.py`.
- **Constant already in place**: `CHECK_CEILING_SECONDS = 2.0` (module-level, used by the wall-clock gate `test_check_speed_under_ceiling` that lands in M3-06).
- **Pattern**: add parametrized `pytest.mark.parametrize` over the three M3 samples; subprocess-invoke `voss check`, measure wall-clock, assert under ceiling. Sentinel test stays untouched.

## Acceptance criteria — all met

- `grep -c "if not self.emit_indexes" voss/analyzer.py` → 1 ✓
- `grep -n "D-03" voss/analyzer.py` → line 493 ✓
- `pytest tests/analyzer/ -q` → 29 passed ✓
- Warm `time python3 -m voss.cli check samples/support.voss` → 1.18s < 2s ✓
- `r.match_entries` populated with `cases=[]` rows when `emit_indexes=False` ✓
- `sentence_transformers` absent from `sys.modules` after `emit_indexes=False` analyze ✓
- Sentinel test passes, including isolated `-p no:cacheprovider` run ✓
- `CHECK_CEILING_SECONDS = 2.0` in place, `test_check_speed_under_ceiling` absent (M3-06's job) ✓
