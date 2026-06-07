---
phase: V9-audit-product-supersedes-o6-reuse-o6-plans
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - tests/harness/audit/test_o6_fixtures.py
  - tests/harness/audit/test_snapshot_loader.py
  - tests/harness/audit/test_audit_report.py
  - tests/harness/audit/test_audit_render.py
  - tests/harness/audit/test_audit_cli.py
  - tests/harness/audit/test_calibration.py
  - tests/harness/audit/test_signoff_forcing.py
autonomous: true
requirements: [VAUD-01, VAUD-02, VAUD-03, VAUD-04, VAUD-05, VAUD-06, VAUD-07, VAUD-08, VAUD-10, VAUD-SIGNOFF, VAUD-CAL]

must_haves:
  truths:
    - "The fixture tree contains .review.json sidecars and a separate run-final.json file"
    - "Loader tests assert the run_id parameter, run-final.json separate read, and sidecar loading"
    - "Five new RED test files exist, each targeting the real V9 surface (no fictional API masked by xfail)"
    - "The existing 37 audit tests remain green after fixture extension"
  artifacts:
    - path: "tests/harness/audit/test_o6_fixtures.py"
      provides: "build_fixture_tree extended with .review.json sidecars + run-final.json"
      contains: "review.json"
    - path: "tests/harness/audit/test_snapshot_loader.py"
      provides: "run_id param + run-final-separate-read + sidecar-load tests"
      contains: "run_id"
    - path: "tests/harness/audit/test_audit_report.py"
      provides: "RED tests for VAUD-02/03/04/05/06/07/10"
    - path: "tests/harness/audit/test_audit_render.py"
      provides: "RED tests for VAUD-08 (markdown/json/determinism/round-trip)"
    - path: "tests/harness/audit/test_audit_cli.py"
      provides: "RED tests for VAUD-01 (exit codes, latest-default, traversal guard)"
    - path: "tests/harness/audit/test_calibration.py"
      provides: "RED tests for VAUD-CAL"
    - path: "tests/harness/audit/test_signoff_forcing.py"
      provides: "RED tests for VAUD-SIGNOFF"
  key_links:
    - from: "tests/harness/audit/test_audit_report.py"
      to: "tests/harness/audit/test_o6_fixtures.py::build_fixture_tree"
      via: "import + fixture_root pytest fixture"
      pattern: "build_fixture_tree"
---

<objective>
Wave 0 RED scaffolds. Lay down the failing test surface for every V9 requirement and extend the existing fixture/loader tests so the downstream implementation waves have a concrete contract to satisfy. This is the BLOCKING foundation: the `load.py` glob-landmine fix (run-final.json + .review.json crash the node glob) must be expressed as a loader test here, and the fixture builder must emit those sidecars + run-final.json so every downstream test has realistic data.

Purpose: Give executors an exact, executable target. No fictional API masked behind `xfail` — every test references the real planned symbols (`load_audit_snapshot(root, run_id=...)`, `build_audit_report`, `render_markdown`/`render_json`, `audit_cmd`, `compute_calibration`, the sign-off forcing function). Tests are expected RED (symbols not yet implemented) except the fixture-extension tests which must be GREEN immediately.
Output: 2 modified test files + 5 new RED test files.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/V9-audit-product-supersedes-o6-reuse-o6-plans/V9-SPEC.md
@.planning/phases/V9-audit-product-supersedes-o6-reuse-o6-plans/V9-VALIDATION.md
@.planning/phases/V9-audit-product-supersedes-o6-reuse-o6-plans/V9-PATTERNS.md

<interfaces>
Planned V9 symbols these RED tests reference (implemented in later waves — do NOT implement here):

voss/harness/audit/load.py (V9-02):
  load_audit_snapshot(root: Path, run_id: str | None = None) -> AuditSnapshot   # run_id param added
  _load_review_sidecars(run_dir: Path) -> dict[str, dict]                       # {node_id: sidecar_dict}
  _load_run_final_file(run_dir: Path) -> dict | None

voss/harness/audit/model.py (V9-02):
  AuditReport(run_id, idea, principles, team_config, snapshot, review_sidecars,
              run_final, signoff_ack, calibration, sections_missing)
  CalibrationReport(total_pairs, false_pass_count, slop_rejection_count,
                    false_pass_rate, slop_rejection_rate, spot_audit_paths)

voss/harness/audit/report.py (V9-03):
  build_audit_report(cwd: Path, run_id: str | None = None,
                     calibration: CalibrationReport | None = None) -> AuditReport

voss/harness/audit/render.py (V9-04):
  render_text(report) -> str ; render_markdown(report) -> str ; render_json(report) -> str

voss/harness/audit/calibration.py (V9-05):
  compute_calibration(sessions_dir: Path, spot_k: int = 3, seed: int | None = None) -> CalibrationReport

voss/harness/cli.py (V9-04 / V9-06):
  audit_cmd  (click command "audit")
  _write_signoff_ack(cwd, root_id, *, killed_count, misroute_count) -> Path

Existing review-sidecar schema (voss/harness/board/review_persistence.py — authoritative):
  {"a_verification": {"test_path_or_rubric": str|None, "result": "pass"|"fail", "notes": str} | None,
   "b_verdict": {"conf": float, "source": "B", "tier": str, "verdict": "pass"|"fail"|"block",
                 "notes": str, "evidence_refs": [str], "domain_inferred": str} | None,
   "final_outcome": "Done" | "Blocked"}

Existing run-final.json schema (voss/harness/cli.py:_persist_run_final — authoritative):
  dataclasses.asdict(RunFinal) → {root_id, idea, total_cards, done_count, blocked_count,
  killed_count, rescope_count, em_iterations, ...} plus optional "sign_off": {decision, ts}
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Extend build_fixture_tree with .review.json sidecars + a separate run-final.json</name>
  <files>tests/harness/audit/test_o6_fixtures.py</files>
  <read_first>
    - tests/harness/audit/test_o6_fixtures.py (the file being modified; `build_fixture_tree` lines 178-326, `_verdict_snapshot` lines 73-87, node builders) — its own self-extension analog
    - voss/harness/board/review_persistence.py (the AUTHORITATIVE `.review.json` sidecar schema: `a_verification`/`b_verdict`/`final_outcome` keys; `b_verdict` is `dataclasses.asdict(verdict_b)` with `domain_inferred`)
    - voss/harness/cli.py:3979-4000 (`_persist_run_final` — the AUTHORITATIVE run-final.json shape and location `.voss/sessions/<root_id>/run-final.json`)
    - V9-PATTERNS.md "tests/harness/audit/ — new test files" section (build_fixture_tree extension excerpt, lines 513-526)
  </read_first>
  <action>
    Extend `build_fixture_tree` to additionally write, into the same `sessions_dir` (`<root>/.voss/sessions/root_aabbcc0001/`):
    (a) Per-node `.review.json` sidecars named `<node_id>.review.json` for the cards that exercise reviewer scenarios — at minimum: `node_ab_block1` (A result="pass", B verdict="block", tier="strong", evidence_refs non-empty, final_outcome="Blocked"), `node_done_0001` (A result="pass", B verdict="pass", final_outcome="Done"), and `node_misroute1` (A result="pass", B verdict="fail" to create a false-pass calibration pair). Match the AUTHORITATIVE sidecar schema exactly (`a_verification`, `b_verdict` with `domain_inferred`, `final_outcome`). Add `node_unsupported.json` style coverage by leaving at least ONE em.ticket node WITHOUT a sidecar (the existing `node_killed_01` has no sidecar — keep it that way to drive the VAUD-03 unsupported-claim test).
    (b) A separate `run-final.json` file (NOT a node JSON — it has no `id` field) at `sessions_dir / "run-final.json"`, containing the run-final superset: `root_id=ROOT_ID`, `idea="fixture idea"`, `total_cards`, `done_count`, `blocked_count`, `killed_count=1`, `rescope_count`, `em_iterations`, and a `sign_off` key `{decision, ts}`.
    Write all new files with `path.write_text(json.dumps(..., indent=2))` then `path.chmod(0o600)` (mirror the node-write loop). Add the new paths to the returned `paths` dict under keys like `node_ab_block_review`, `node_done_review`, `node_misroute_review`, `run_final`. Do NOT change any existing node JSON content or existing returned keys — the 37 existing tests assert on them.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/audit/test_o6_fixtures.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `.venv/bin/python -m pytest tests/harness/audit/test_o6_fixtures.py -x` exits 0 (existing fixture tests still pass; new sidecars/run-final do not break `test_all_scenario_nodes_present` which keys on the 8 node entries).
    - After `build_fixture_tree(tmp)`, `(tmp/".voss/sessions/root_aabbcc0001/run-final.json").exists()` is True and it has NO `"id"` key.
    - At least 3 `*.review.json` files exist in the sessions dir; `node_ab_block1.review.json` has `b_verdict.verdict == "block"` and `a_verification.result == "pass"`.
    - `node_killed_01` has an `em.ticket` transition but NO matching `.review.json` sidecar (drives the unsupported-claim test).
    - The 37 pre-existing audit tests remain green: `.venv/bin/python -m pytest tests/harness/audit/ -x` shows only the new RED tests from later tasks failing, never a regression in existing tests.
  </acceptance_criteria>
  <done>Fixture tree emits .review.json sidecars + a separate run-final.json; existing fixture tests green; one em.ticket node intentionally lacks a sidecar.</done>
</task>

<task type="auto">
  <name>Task 2: Extend test_snapshot_loader.py for run_id param, run-final separate read, sidecar load (glob-landmine RED)</name>
  <files>tests/harness/audit/test_snapshot_loader.py</files>
  <read_first>
    - tests/harness/audit/test_snapshot_loader.py (the file being modified; `fixture_root` fixture lines 27-30, `TestMalformedInput` lines 126-155, `TestNoLiveImports` lines 175-200) — its own self-extension analog
    - voss/harness/audit/load.py:243-343 (current `load_audit_snapshot(root)` — single param, globs `*.json` at line 263 with NO filter; this is the landmine)
    - V9-PATTERNS.md "voss/harness/audit/load.py (modify)" section (the run_id signature, glob filter, _load_run_final_file, _load_review_sidecars excerpts, lines 27-89)
  </read_first>
  <action>
    Add new test classes (expected RED until V9-02 lands):
    (a) `TestLandmineGlobFilter`: build a fixture tree (which now includes run-final.json + .review.json per Task 1), call `load_audit_snapshot(fixture_root)` and assert it does NOT raise `AuditLoadError` (today it WOULD, because run-final.json has no `id`). Assert `snap.run_final` is populated and `len(snap.nodes) == 8` (sidecars + run-final.json excluded from the node count).
    (b) `TestRunIdParameter`: assert `load_audit_snapshot(fixture_root, run_id="root_aabbcc0001")` loads that run; assert `load_audit_snapshot(fixture_root, run_id="does_not_exist")` raises `AuditLoadError`. Also build a SECOND run dir under sessions and assert that `run_id=None` selects the most-recently-modified one (latest-by-mtime), not the alphabetically-first.
    (c) `TestSidecarLoad`: assert `_load_review_sidecars(run_dir)` returns a dict keyed by node_id, with `node_ab_block1` mapping to a dict whose `b_verdict.verdict == "block"`; a corrupt sidecar maps to `{}` (graceful). Import `_load_review_sidecars` from `voss.harness.audit.load`.
    (d) `TestRunFinalSeparateRead`: assert `_load_run_final_file(run_dir)` reads `run-final.json` and returns a dict with `idea == "fixture idea"` and a `sign_off` key; returns `None` when the file is absent.
    Extend `TestNoLiveImports` with `test_calibration_module_has_no_board_imports` (scans `voss.harness.audit.calibration` source for the forbidden `voss.harness.board`/`.em`/`.cli` import strings) — expected RED until calibration.py exists. Use the existing source-text-scan pattern verbatim.
    Do NOT modify or delete existing test methods; the run-final glob behavior change means the old `test_missing_id_field_raises_with_path` must still pass — verify your fixture additions do not break it (it uses a hand-built `noid.json`, unaffected).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/audit/test_snapshot_loader.py -x 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - New tests are collected (no import/collection errors); they FAIL with assertion/attribute errors referencing the not-yet-implemented `run_id` param / `_load_review_sidecars` / `_load_run_final_file` — i.e. genuine RED, not collection failure.
    - Existing loader tests (`TestReadOnly`, `TestMalformedInput`, `TestNoLiveImports` originals, `TestDeterminism`) still pass.
    - No `xfail`/`xskip` markers used to mask the RED (per memory `gsd-scaffold-fictional-api`).
  </acceptance_criteria>
  <done>Loader-test extension expresses the run_id param, glob-landmine fix, sidecar load, and run-final separate read as RED tests; existing loader tests unaffected.</done>
</task>

<task type="auto">
  <name>Task 3: Create the 5 new RED test files for report/render/cli/calibration/signoff</name>
  <files>tests/harness/audit/test_audit_report.py, tests/harness/audit/test_audit_render.py, tests/harness/audit/test_audit_cli.py, tests/harness/audit/test_calibration.py, tests/harness/audit/test_signoff_forcing.py</files>
  <read_first>
    - tests/harness/audit/test_snapshot_loader.py (test-module header + `fixture_root` fixture pattern, lines 1-30; `TestDeterminism` lines 158-172; `TestNoLiveImports` lines 175-200) — the analog for all new test files
    - tests/harness/audit/test_o6_fixtures.py (`build_fixture_tree` and ROOT_ID="root_aabbcc0001", the data your tests assert against)
    - voss/harness/cli.py:2487-2518 (`review_cmd` — the CliRunner-testable command analog) and :2451-2459 (`_latest_root_id`)
    - V9-PATTERNS.md "CLI test pattern" + "Determinism test pattern" + "No-live-imports guard extension" excerpts (lines 528-567)
    - V9-RESEARCH.md §3 (claims-vs-evidence: unsupported = em.ticket present AND sidecar absent or both verdicts null) and §6 (calibration formula: false_pass = A=pass AND B in {fail,block}; slop_rejection = B=block)
  </read_first>
  <action>
    Each file: module docstring + `from __future__ import annotations`, `from tests.harness.audit.test_o6_fixtures import build_fixture_tree`, a `fixture_root` pytest fixture (copy from test_snapshot_loader lines 27-30). All expected RED until their target wave lands. NO xfail masking. Use tmp_path only.

    `test_audit_report.py` (VAUD-02/03/04/05/06/07/10) — import `build_audit_report` from `voss.harness.audit.report`:
      - `test_all_prd_sections_present`: report has idea, principles (non-empty tuple), team_config, snapshot, review_sidecars, run_final, signoff_ack, calibration, sections_missing fields.
      - `test_missing_source_renders_none_not_crash`: build a tree with no run-final.json → `build_audit_report` does not raise; `report.idea == ""` and "Goal" (or the appropriate key) appears in `report.sections_missing`.
      - `test_claims_vs_evidence`: a node with em.ticket but no sidecar (`node_killed_01`) is flagged unsupported; a node with a sidecar has its evidence reachable. Assert against whatever the report exposes for unsupported claims (e.g. a tuple of unsupported node_ids) — name it `unsupported_claims` in the assertion so V9-03 must provide it.
      - `test_budget_section`: `report.snapshot.nodes` each carry an `envelope` with `limit`/`spent`.
      - `test_scope_denials`: extend the fixture in-test (write a node with `rejected_raises=[{"attempted_delta":1000,"reason":"over ceiling","attempted_at":...}]`) and assert the report surfaces it. (V9-02/V9-03 must surface rejected_raises.)
      - `test_reviewer_sections_separate`: `report.review_sidecars["node_ab_block1"]` exposes distinct `a_verification` and `b_verdict`.
      - `test_lineage`: killed card `node_killed_01` and rescope `tk_resc→tk_succ` reachable with routing rationale.
      - `test_residual_risk`: `report` exposes a Leak-6 assessment with `status == "accepted_gap"`.

    `test_audit_render.py` (VAUD-08) — import `render_text, render_markdown, render_json` from `voss.harness.audit.render` and `build_audit_report`:
      - `test_markdown_has_section_headers`: markdown contains a header per PRD §9 section; missing sections render `_none_`.
      - `test_json_round_trips`: `json.loads(render_json(report))` is a dict carrying `run_id`, `idea`, nested snapshot data; document the tuple→list coercion (assert lists, not tuples).
      - `test_determinism`: two `render_json` calls on the same tree produce byte-identical output (sort_keys).
      - `test_text_render_stable`: two `render_text` calls identical.

    `test_audit_cli.py` (VAUD-01) — `from click.testing import CliRunner`, `from voss.harness.cli import audit_cmd`:
      - `test_exits_0_for_latest`: `runner.invoke(audit_cmd, ["--cwd", str(fixture_root)])` exit_code 0.
      - `test_exits_0_for_named_run`: pass the run_id arg.
      - `test_unknown_run_nonzero_with_stderr`: unknown run_id → exit_code != 0 and "unknown" in output.
      - `test_traversal_guard`: run_id "../escape" → exit_code != 0 (rejected before FS touch).
      - `test_format_json`: `--format json` output parses as JSON.
      - `test_deterministic_output`: two invocations on identical data → identical stdout.

    `test_calibration.py` (VAUD-CAL) — import `compute_calibration` and `CalibrationReport`:
      - `test_false_pass_rate`: with the fixture's A=pass/B=fail misroute pair, `report.false_pass_count >= 1` and `0.0 <= false_pass_rate <= 1.0`.
      - `test_slop_rejection_rate`: the A-pass/B-block pair contributes to `slop_rejection_count`.
      - `test_spot_audit_hook_deterministic`: `compute_calibration(sessions_dir, spot_k=2, seed=7)` twice → identical `spot_audit_paths`.
      - `test_zero_pairs_no_div_by_zero`: empty sessions dir → rates 0.0, no exception.

    `test_signoff_forcing.py` (VAUD-SIGNOFF) — import `_write_signoff_ack` from `voss.harness.cli`; use `CliRunner` against `team_run_cmd` with input simulation where feasible, plus a direct unit test of the ack writer:
      - `test_ack_writer_creates_sidecar`: `_write_signoff_ack(tmp, "rootX", killed_count=1, misroute_count=2)` writes `.voss/sessions/rootX/.signoff-ack.json` with those counts and an `ack_ts`; file mode 0o600.
      - `test_ack_is_new_file_not_mutation`: writing the ack does NOT create or modify `run-final.json` or any node JSON.
      - `test_approve_refused_without_ack` (CliRunner against team_run_cmd, simulate a non-"yes" ack input when killed/misroute present): exit_code != 0 with an "acknowledg" message. (Expected RED until V9-06 wires the gate.)
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/audit/test_audit_report.py tests/harness/audit/test_audit_render.py tests/harness/audit/test_audit_cli.py tests/harness/audit/test_calibration.py tests/harness/audit/test_signoff_forcing.py --collect-only 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - All 5 files are COLLECTED without import-time syntax errors (`--collect-only` lists every test; collection of a test that imports a not-yet-existing module is allowed to error ONLY at run time, not collect time — so guard module-level imports of unimplemented symbols inside the test body or use `pytest.importorskip`-free direct imports that fail at call, per the memory note: do NOT mask with xfail).
    - Running the suite shows these tests RED (failing on missing symbols), and the existing 37 audit tests + Task-1/Task-2 additions are unaffected by collection.
    - Each requirement ID (VAUD-01/02/03/04/05/06/07/08/10/SIGNOFF/CAL) has at least one test referencing its real planned symbol.
    - No `xfail`/`skip` markers mask the RED state.
  </acceptance_criteria>
  <done>Five RED test files exist, collectible, each pinned to real V9 symbols and requirement IDs, no xfail masking.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test fixtures → filesystem | All writes confined to pytest `tmp_path`; never the repo `.voss/` |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-V9-01-01 | Tampering | fixture writes escaping tmp_path | mitigate | All fixture writes go under `tmp_path`; existing `TestFixtureBuilderWritesUnderTmpPath` guards this and must stay green |
| T-V9-01-SC | Tampering | npm/pip/cargo installs | accept | Zero new dependencies in this plan; stdlib + pytest only — no install step |
</threat_model>

<verification>
- `.venv/bin/python -m pytest tests/harness/audit/test_o6_fixtures.py tests/harness/audit/test_snapshot_loader.py -x` — fixture extension + existing loader tests green (new RED loader tests fail on missing symbols only).
- `.venv/bin/python -m pytest tests/harness/audit/ --collect-only` — all 7 files collect.
- The 37 pre-existing tests must not regress (standing invariant for the whole phase).
</verification>

<success_criteria>
- Fixture builder emits `.review.json` sidecars + a separate `run-final.json`; one em.ticket node intentionally lacks a sidecar.
- Loader tests express the glob-landmine fix, run_id param, sidecar load, and run-final separate read as RED.
- Five new RED test files exist covering all 11 VAUD IDs, collectible, no xfail masking.
- Existing 37 audit tests remain green.
</success_criteria>

<output>
Create `.planning/phases/V9-audit-product-supersedes-o6-reuse-o6-plans/V9-01-SUMMARY.md` when done.
</output>
