---
phase: V9-audit-product-supersedes-o6-reuse-o6-plans
plan: 01
type: execute
status: complete
wave: 0
---

# V9-01 Summary — Wave 0 RED Scaffolds

## Outcome

RED test surface laid down for every V9 requirement. Fixture/loader tests
extended. Final audit-suite state: **40 passed, 34 RED**, zero regressions in
pre-existing tests.

| File | Change | Tests |
|---|---|---|
| `tests/harness/audit/test_o6_fixtures.py` | +`.review.json` sidecars (3) + separate `run-final.json`; `NODE_KEYS` const | GREEN |
| `tests/harness/audit/test_snapshot_loader.py` | +4 RED classes (landmine/run_id/sidecar/run-final) + calibration no-imports guard | 3 GREEN (landmine), 8 RED |
| `tests/harness/audit/test_audit_report.py` (new) | VAUD-02/03/04/05/06/07/10 | 8 RED |
| `tests/harness/audit/test_audit_render.py` (new) | VAUD-08 | 4 RED |
| `tests/harness/audit/test_audit_cli.py` (new) | VAUD-01 | 6 RED |
| `tests/harness/audit/test_calibration.py` (new) | VAUD-CAL | 5 RED |
| `tests/harness/audit/test_signoff_forcing.py` (new) | VAUD-SIGNOFF | 3 RED |

All RED tests fail on genuine missing symbols (ImportError / ModuleNotFoundError
/ TypeError / AttributeError) or unimplemented behavior — no `xfail`/`skip`
masking (per memory `gsd-scaffold-fictional-api`). V9-symbol imports live inside
test bodies so `--collect-only` is clean (26 new tests collect without error).

## Deviation: load.py glob-filter pulled forward (user-approved)

**Plan defect found.** The plan deferred the `load.py` glob-landmine fix to
V9-02 ("do NOT implement here") while simultaneously requiring the 37
pre-existing audit tests stay green. These are contradictory: once
`build_fixture_tree` emits `run-final.json` + `*.review.json` into the run dir,
the unfiltered `tree_dir.glob("*.json")` at `load.py:263` reads them as nodes,
trips the required-`id` check, and breaks **14 pre-existing loader tests** that
call `load_audit_snapshot(fixture_root)`.

**Resolution (user chose "Pull glob-filter forward"):** applied the 2-line
filter already specified in V9-PATTERNS.md lines 38-42:

```python
node_files = [
    p for p in sorted(tree_dir.glob("*.json"))
    if p.name != "run-final.json" and not p.name.endswith(".review.json")
]
```

Effect: the 14 loader tests stay green; `TestLandmineGlobFilter` (3 tests) goes
GREEN (landmine fixed, `run_final` already populated via the root `em.run_final`
transition); the genuinely-unimplemented symbols (`run_id` param,
`_load_review_sidecars`, `_load_run_final_file`) remain RED for V9-02.

**Scope note for V9-02:** the glob filter is now done. V9-02 still owns the
`run_id` parameter, latest-by-mtime fallback, `_load_review_sidecars`,
`_load_run_final_file`, and the `AuditNode.rejected_raises` field (asserted RED
by `test_scope_denials`).

## Other necessary adaptations (existing fixture tests)

Adding non-node keys (`*_review`, `run_final`) to `build_fixture_tree`'s
returned dict broke 4 existing assertions that iterate the dict and read
`["id"]`. Adapted minimally:

- `test_all_scenario_nodes_present`: exact `==` → subset check (`expected <= keys`).
- `test_all_files_are_valid_json`, `test_fixture_ids_are_deterministic`,
  `test_nodes_sorted_by_id`: scoped to `NODE_KEYS` (skip sidecar/run-final keys).

The 8 node entries and all existing node JSON content are unchanged.

## Verification

- `pytest tests/harness/audit/test_o6_fixtures.py tests/harness/audit/test_snapshot_loader.py` — fixture + landmine + originals green; 8 loader RED on missing symbols.
- `pytest tests/harness/audit/ --collect-only` — all 7 files collect (no syntax/import-time errors).
- `pytest tests/harness/audit/` — 40 passed, 34 RED. No pre-existing test regressed.

## Notes

- Broader `tests/harness/` failures observed (`test_no_new_runtime_hooks`
  drift on `recorder.py`; `test_recall_eval`/`test_slash_recall` OpenAI 401s)
  are **pre-existing and unrelated** — `load.py` is not in the runtime-surface
  baseline; `recorder.py` was not touched; the 401s are missing-API-key env.
- A repo auto-commit hook committed the work across `f80e4c6` (fixtures) and
  `8d7ee67` (loader fix + 5 new files); working tree is clean.
