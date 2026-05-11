---
phase: M4
plan: 05
type: execute
wave: 4
depends_on: [M4-02, M4-03, M4-04]
files_modified:
  - .github/workflows/ci.yml
  - README.md
  - voss/harness/diagnostics.py
  - tests/harness/test_doctor.py
autonomous: true
requirements:
  - DOG-06
tags:
  - ci
  - docs
  - doctor
  - wave-4

must_haves:
  truths:
    - "`.github/workflows/ci.yml` contains a step running `python -m voss.cli check voss/harness/agent/`, inserted AFTER `pip install -e \".[dev]\"` and BEFORE `pytest`. The step uses GH Actions default behavior: non-zero exit fails CI (DOG-06 gate)."
    - "`README.md` install section contains the one-liner `voss compile voss/harness/agent/` framed as the eager-compile prerequisite for `VOSS_HARNESS=compiled` users (D-16)."
    - "`voss/harness/diagnostics.py:run_all_checks` includes a `check_harness_cache(cwd)` row that returns `Check(name=\"harness cache\", result=WARN if stale else OK, fix=\"voss compile voss/harness/agent/\")`. The row is INFORMATIONAL ONLY — `aggregate_exit_code` at lines 194-198 treats WARN as exit 0; never blocking (D-16)."
    - "`check_harness_cache(cwd)` returns OK when the source dir `voss/harness/agent/` does not exist in the target cwd (no harness sources to track)."
    - "`check_harness_cache(cwd)` returns WARN with the canonical fix text when `assert_fresh` raises `StaleHarnessCacheError`."
    - "`check_harness_cache(cwd)` returns OK with detail `\".voss-cache/harness/ fresh\"` when `assert_fresh` succeeds."
    - "`tests/harness/test_doctor.py` is extended (or created) with `test_doctor_reports_harness_cache_row(tmp_path)` asserting the new row appears by name in `run_all_checks` output."
    - "CI step grep is satisfied: `grep -F \"voss.cli check voss/harness/agent/\" .github/workflows/ci.yml` returns at least 1 match."
    - "Install-doc grep is satisfied: `grep -F \"voss compile voss/harness/agent/\" README.md` returns at least 1 match."
  artifacts:
    - path: ".github/workflows/ci.yml"
      provides: "DOG-06 CI gate — voss check voss/harness/agent/ step in the stub job"
      contains: "voss.cli check voss/harness/agent/"
    - path: "README.md"
      provides: "D-16 install-time integration — eager-compile one-liner in install section"
      contains: "voss compile voss/harness/agent/"
    - path: "voss/harness/diagnostics.py"
      provides: "D-16 doctor integration — check_harness_cache row in run_all_checks (informational, WARN never blocks)"
      contains: "check_harness_cache"
    - path: "tests/harness/test_doctor.py"
      provides: "Wave-4 sentinel: assert harness-cache row appears in run_all_checks output"
      contains: "harness cache"
  key_links:
    - from: ".github/workflows/ci.yml stub job"
      to: "voss/cli.py:check dir mode (M4-02)"
      via: "subprocess `python -m voss.cli check voss/harness/agent/` in the runner cwd (repo root)"
      pattern: "voss.cli check voss/harness/agent/"
    - from: "voss/harness/diagnostics.py:check_harness_cache"
      to: "voss/harness/cache.py:assert_fresh"
      via: "try/except StaleHarnessCacheError → WARN; else OK"
      pattern: "assert_fresh"
    - from: "voss/harness/diagnostics.py:run_all_checks"
      to: "voss/harness/diagnostics.py:check_harness_cache"
      via: "appended after check_project_dirs in the existing ordered list"
      pattern: "check_harness_cache(cwd)"
---

<objective>
Land the M4 Wave-4 polish that closes DOG-06 (the CI gate is the real gate, not just the dir-walk command) and D-16 (install-time eager-compile + doctor freshness row).

Three small changes:

1. **CI gate** (`.github/workflows/ci.yml`): Add one step `voss check voss/harness/agent/` in the existing `stub` job, between `pip install -e ".[dev]"` and `pytest`. This is THE gate for DOG-06 — without this step, `voss check` is just a CLI capability; with it, regressions in the `.voss` files break CI.

2. **README install one-liner** (D-16): Append `voss compile voss/harness/agent/` to the README install section as the eager-compile step. Framed as: "if you want to opt into `VOSS_HARNESS=compiled`, run this after `pip install -e .` to populate the cache".

3. **Doctor cache-freshness row** (D-16): Add `check_harness_cache(cwd)` to `voss/harness/diagnostics.py` and insert it into the `run_all_checks` ordered list. Informational only — WARN on stale, OK on fresh or missing. `aggregate_exit_code` at lines 194-198 treats WARN as exit 0; row never blocks `voss doctor`.

Purpose: Closes the M4 success bar by making DOG-06 a real CI gate (not just a CLI capability) and operationalizing D-16 (developers see cache staleness in `voss doctor` output and have the eager-compile one-liner in install instructions). The doctor row mirrors `check_project_dirs` at diagnostics.py:158-178 exactly.

Output:
- `.github/workflows/ci.yml` — +~2 LOC (one named step).
- `README.md` — +~3 LOC (one-liner + brief framing sentence).
- `voss/harness/diagnostics.py` — +~15 LOC (`check_harness_cache` function + insertion in `run_all_checks`).
- `tests/harness/test_doctor.py` — +~5 LOC (one assert; may need to create the file if it doesn't yet exist).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/M4-voss-authored-harness-loop/M4-CONTEXT.md
@.planning/phases/M4-voss-authored-harness-loop/M4-RESEARCH.md
@.planning/phases/M4-voss-authored-harness-loop/M4-PATTERNS.md
@.planning/phases/M4-voss-authored-harness-loop/M4-VALIDATION.md
@.planning/phases/M4-voss-authored-harness-loop/M4-02-PLAN.md
@.planning/phases/M4-voss-authored-harness-loop/M4-03-PLAN.md
@.planning/phases/M4-voss-authored-harness-loop/M4-04-PLAN.md
@.github/workflows/ci.yml
@README.md
@voss/harness/diagnostics.py
@voss/harness/cache.py

<interfaces>
<!-- Key contracts extracted from the tree + M4-02/03/04 outputs. -->

From .github/workflows/ci.yml (current shape; lines 14-26):
```yaml
jobs:
  stub:
    if: github.event_name == 'push' || github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pytest -q -m "not live" --cov=voss_runtime --cov-report=term-missing
```

Target insertion point: between `pip install -e ".[dev]"` and the `pytest` line. New step is a named step (with `name:` field) for CI log readability.

From voss/harness/diagnostics.py (the analog at lines 158-178):
```python
def check_project_dirs(cwd: Path) -> Check:
    voss_dir = cwd / ".voss"
    cache_dir = cwd / ".voss-cache"
    failures: list[str] = []
    for d in (voss_dir, cache_dir):
        ...
    if failures:
        return Check("project dirs", CheckResult.WARN, detail="; ".join(failures), fix="...")
    return Check("project dirs", CheckResult.OK, detail=".voss/, .voss-cache/ creatable")
```

`run_all_checks` at lines 181-191 returns a `list[Check]`. M4-PATTERNS.md insertion: append `check_harness_cache(cwd)` after `check_project_dirs(cwd)` in the list.

`aggregate_exit_code` at 194-198 treats WARN as exit 0 (verified). D-16 informational invariant holds.

From voss/harness/cache.py (M4-02):
- `HARNESS_AGENT_DIR = "voss/harness/agent"` constant.
- `assert_fresh(project_root)` raises `StaleHarnessCacheError` on stale/missing/version-mismatch.
- The lazy-import dance `from . import cache as harness_cache` inside `check_harness_cache` avoids the circular (cache.py imports `from .diagnostics import StaleHarnessCacheError`).

From voss/harness/diagnostics.py (M4-02):
- `StaleHarnessCacheError` class already added by M4-02 Task 1.

From README.md (current shape — read the file before editing):
- Has an "Installation" section with `pip install -e .` or `pip install voss` style instructions.
- Append to that section a paragraph + the one-liner code block.

From tests/harness/test_doctor.py (read whether it exists):
- If exists, follow its style. If not, create with minimal pytest plain-`def` shape importing `run_all_checks` from `voss.harness.diagnostics`.

D-10 canonical fix-text (cross-referenced from M4-02):
- The doctor row's `fix=` field is the same suggestion text as the `StaleHarnessCacheError` message: `"voss compile voss/harness/agent/"` (verb + arg only, not the full sentence — `fix` is a short command suggestion per existing `check_*` rows).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: CI gate + README install one-liner</name>
  <files>.github/workflows/ci.yml, README.md</files>
  <read_first>
    - .github/workflows/ci.yml (entire — confirm exact line numbers of `pip install -e ".[dev]"` and the `pytest` step; structure is stable per M4-RESEARCH §"Pattern: CI gate insertion")
    - README.md (entire — find the install section; M4-RESEARCH §"README.md (MODIFY) — Wave 4 D-16" frames the one-liner)
    - M4-RESEARCH.md §"Pattern: CI gate insertion" (lines ~970-976)
    - M4-PATTERNS.md §".github/workflows/ci.yml (MODIFY) — Wave 4" and §"README.md (MODIFY) — Wave 4 D-16"
    - M4-VALIDATION.md rows `ci-gate` and `install-doc` for the exact grep contracts
  </read_first>
  <action>
    Edit `.github/workflows/ci.yml`. Locate the `stub` job's steps list (lines 14-26 region). Between the `pip install -e ".[dev]"` step and the `pytest` step, insert a new step. The step uses YAML `name:` + `run:` form. The name is `"voss check harness sources (M4 DOG-06)"`. The run command is `python -m voss.cli check voss/harness/agent/`. Indentation matches the surrounding steps (6 spaces for `- name:`/`- run:` if those siblings use that indent). The step relies on GH Actions default behavior — exit non-zero fails the job. Verify after editing by re-reading the ci.yml region.

    Edit `README.md`. Locate the install section (search for `pip install` or `Installation` heading). Append a short paragraph framing the eager-compile step: explain that `voss compile voss/harness/agent/` populates the compiled-harness cache and is required if the developer wants to opt into `VOSS_HARNESS=compiled`; without it, the default Python path works unchanged. Follow with a fenced code block containing the literal one-liner `voss compile voss/harness/agent/`. Keep the framing brief (2-3 sentences). Decision references: D-16 (install-time integration; informational only); D-08 (env-flag default is `python` — install one-liner is optional, not required).
  </action>
  <verify>
    <automated>grep -F "voss.cli check voss/harness/agent/" .github/workflows/ci.yml && grep -F "voss compile voss/harness/agent/" README.md</automated>
  </verify>
  <acceptance_criteria>
    - `grep -F "voss.cli check voss/harness/agent/" .github/workflows/ci.yml` returns at least 1 match (M4-VALIDATION row `ci-gate`).
    - `grep -F "voss compile voss/harness/agent/" README.md` returns at least 1 match (M4-VALIDATION row `install-doc`).
    - The CI step is positioned between `pip install -e ".[dev]"` and `pytest`: verify by reading the file and confirming the line order.
    - The CI step has a `name:` field for readability: `grep -n "voss check harness sources" .github/workflows/ci.yml` returns 1 match.
    - YAML validity: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` exits 0 (no YAML syntax errors).
    - README install paragraph is brief (no exhaustive prose) and the one-liner is in a fenced code block — verify by reading the relevant section.
  </acceptance_criteria>
  <done>CI step + README one-liner land; both greps pass; YAML still parses; no existing CI steps removed.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Doctor cache-freshness row + test</name>
  <files>voss/harness/diagnostics.py, tests/harness/test_doctor.py</files>
  <read_first>
    - voss/harness/diagnostics.py (entire — confirm structure: Check dataclass at 27-32, CheckResult enum at 21-25, existing `check_*` functions at 35-178, `run_all_checks` at 181-191, `aggregate_exit_code` at 194-198, `StaleHarnessCacheError` class added by M4-02)
    - voss/harness/cache.py (M4-02 — HARNESS_AGENT_DIR constant, assert_fresh function)
    - tests/harness/test_doctor.py if it exists (otherwise locate similar doctor tests via `ls tests/harness/`)
    - M4-RESEARCH.md §"`voss doctor` reporting for harness-cache freshness — extends M2's cognition rows" (Claude's Discretion section ~line 73)
    - M4-PATTERNS.md §"voss/harness/diagnostics.py (MODIFY) — Wave 1 + Wave 4" (the doctor-row part of this is Wave 4; the exception class part was Wave 1)
    - M4-VALIDATION.md row `doctor-cache-row` for the test contract
  </read_first>
  <behavior>
    - `check_harness_cache(cwd: Path) -> Check`:
        - If `cwd / "voss/harness/agent"` does not exist → return `Check(name="harness cache", result=CheckResult.OK, detail="no harness sources")`.
        - Else lazy-import `from . import cache as harness_cache` (avoids the circular with diagnostics.py importing cache.py and vice versa).
        - Wrap `harness_cache.assert_fresh(cwd)` in try/except `StaleHarnessCacheError`:
            - On `StaleHarnessCacheError`: return `Check(name="harness cache", result=CheckResult.WARN, detail="stale — compiled artifacts out of sync with .voss sources", fix="voss compile voss/harness/agent/")`.
            - On success (no raise): return `Check(name="harness cache", result=CheckResult.OK, detail=".voss-cache/harness/ fresh")`.
    - `run_all_checks(cwd)` returned list now includes the `check_harness_cache(cwd)` entry, appended after `check_project_dirs(cwd)`.
    - `aggregate_exit_code(checks)` continues to treat the new WARN as exit 0 (verify by reading lines 194-198; no change needed).
    - Test `test_doctor_reports_harness_cache_row(tmp_path)`:
        - Calls `run_all_checks(tmp_path)`.
        - Extracts `names = [c.name for c in results]`.
        - Asserts `"harness cache" in names`.
        - Optionally asserts `results[names.index("harness cache")].result is CheckResult.OK` (because tmp_path has no harness sources → OK with `"no harness sources"` detail).
        - Does NOT assert WARN/OK on a populated tmp_path — that's covered by the cache-freshness tests in M4-02; this test is purely the row-existence sentinel per M4-VALIDATION row `doctor-cache-row`.
    - Existing doctor tests (if any in `tests/harness/test_doctor.py` or elsewhere) continue to pass.
  </behavior>
  <action>
    Edit `voss/harness/diagnostics.py`. Add `def check_harness_cache(cwd: Path) -> Check:` near the existing `check_project_dirs` function (after it, keeping the file's section ordering coherent). Body per the behavior section: existence guard on `cwd / "voss/harness/agent"` → OK with `"no harness sources"`; otherwise lazy-import `from . import cache as harness_cache` and try `harness_cache.assert_fresh(cwd)`, returning WARN on `StaleHarnessCacheError` (caught by name; class is in this same module) or OK on success. Use `CheckResult.WARN` and `CheckResult.OK` enum members per the existing pattern. Use the canonical fix text `"voss compile voss/harness/agent/"` exactly.

    Edit `voss/harness/diagnostics.py` `run_all_checks` (lines 181-191). Insert `check_harness_cache(cwd)` at the end of the returned list, after the existing `check_project_dirs(cwd)`. Preserve the order of pre-existing checks. Maintain the function's existing return type `list[Check]`.

    Edit (or create) `tests/harness/test_doctor.py`. If the file exists, append a single new test `test_doctor_reports_harness_cache_row(tmp_path)`. If it does not exist, create the file with a brief module docstring (`"""Doctor-row sentinel tests."""`), import `run_all_checks` and `CheckResult` from `voss.harness.diagnostics`, and define just the one test. Body per behavior: call `run_all_checks(tmp_path)`; extract names; assert `"harness cache" in names`; optionally verify the OK status on a bare tmp_path (no harness sources). Keep the test small — its purpose is row-existence verification per M4-VALIDATION row `doctor-cache-row`. Do NOT duplicate the stale/fresh assertions already covered by `tests/harness/test_cache_freshness.py`.

    Decision references: D-16 (doctor reports cache freshness; informational only, never blocking); Pitfall 4 (the freshness check doesn't import the compiled cache — it just calls `assert_fresh`, which is safe to invoke in a doctor context).
  </action>
  <verify>
    <automated>pytest tests/harness/test_doctor.py tests/harness/test_cache_freshness.py tests/harness/ -q -m "not live"</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/harness/test_doctor.py -q` exits 0 with at least 1 passed (the new row-existence test).
    - `pytest tests/harness/ -q -m "not live"` exits 0 (full harness suite green; cache-freshness tests still pass — `check_harness_cache` does not interfere with them).
    - `grep -n 'def check_harness_cache' voss/harness/diagnostics.py` returns 1 match.
    - `grep -n 'check_harness_cache(cwd)' voss/harness/diagnostics.py` returns at least 2 matches (definition + insertion in run_all_checks).
    - `grep -F '"harness cache"' voss/harness/diagnostics.py` returns at least 2 matches (the OK + WARN + no-sources branches all use the same name).
    - `python -c "from voss.harness.diagnostics import run_all_checks; import pathlib, tempfile; cwd = pathlib.Path(tempfile.mkdtemp()); names = [c.name for c in run_all_checks(cwd)]; assert 'harness cache' in names, names; print('OK')"` prints `OK`.
    - `python -c "from voss.harness.diagnostics import run_all_checks, aggregate_exit_code; import pathlib, tempfile; cwd = pathlib.Path(tempfile.mkdtemp()); checks = run_all_checks(cwd); print(aggregate_exit_code(checks))"` prints `0` (WARN does NOT block — confirmed D-16 invariant; the no-sources branch returns OK anyway, but if a future test populates the dir without compiling, the resulting WARN must still exit 0).
  </acceptance_criteria>
  <done>check_harness_cache row added to run_all_checks; row name + canonical fix text wired; existence sentinel test passes; full harness suite green; aggregate_exit_code unchanged (WARN never blocks).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `voss doctor` invocation reading `.voss-cache/` | Read-only; calls `assert_fresh` which only reads `_manifest.json` + source `.voss` files. No import of compiled `.py` artifacts (Pitfall 4 safe-by-construction in this context). |
| CI step running `voss check voss/harness/agent/` | GH Actions runner cwd is repo root; `voss check` is static-only (M3 D-03; emit_indexes=False preserved by M4-02 dir-walk). |
| README install one-liner | Pure docs; no executable surface. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M4-W4-ci-gate-bypass | Repudiation | CI step misconfigured (e.g. typo in command) | mitigate | M4-VALIDATION row `ci-gate` greps the literal `voss.cli check voss/harness/agent/` string in ci.yml. YAML validity check in Task 1 acceptance prevents broken YAML. |
| T-M4-W4-doctor-blocks | Availability | `check_harness_cache` accidentally returning FAIL or causing aggregate_exit_code != 0 | mitigate | Returns only OK or WARN per behavior section. `aggregate_exit_code` (lines 194-198) treats WARN as exit 0; verified by acceptance criterion that calls `aggregate_exit_code` on a tmp_path. D-16 informational-only invariant preserved. |
| T-M4-W4-doctor-rce | Tampering / RCE | Doctor row triggering dynamic import of a stale `loop.py` | accept | `check_harness_cache` calls `assert_fresh` only (read manifest + sha sources). It does NOT call `_resolve_run_turn` or any `importlib.util.spec_from_file_location` for the compiled cache. No RCE surface. |
| T-M4-W4-readme-trust | Spoofing | README one-liner copied without context could mislead | accept | Doc framing explicitly says the eager-compile is for `VOSS_HARNESS=compiled` users; default Python path needs no compile step. |
| T-M4-W4-ci-leak | Information Disclosure | CI step output leaking source contents | accept | `voss check` prints diagnostics with file paths + line/col + severity + message. All sources are repo-controlled. No secrets in `.voss` files. |
</threat_model>

<verification>
After both tasks land:
1. `pytest tests/harness/test_doctor.py tests/harness/test_cache_freshness.py tests/harness/ -q -m "not live"` exits 0.
2. `grep -F "voss.cli check voss/harness/agent/" .github/workflows/ci.yml` returns at least 1 match.
3. `grep -F "voss compile voss/harness/agent/" README.md` returns at least 1 match.
4. `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` exits 0.
5. Full final M4 suite: `pytest tests/harness/ tests/codegen/test_use_alias.py tests/codegen/test_await_use_import.py tests/parser/test_use_alias.py -q -m "not live"` exits 0.
6. M4-VALIDATION rows `ci-gate`, `install-doc`, `doctor-cache-row` flip from ❌ to ✓.
7. All M4 phase success criteria from ROADMAP §"Phase M4: Voss-authored Harness Loop" satisfied:
    (1) `voss/harness/agent/*.voss` exists and models the harness loop ✓ (M4-03).
    (2) `voss check voss/harness/agent/` passes in CI ✓ (M4-02 capability + M4-05 CI step).
    (3) Compiled harness artifacts cache under `.voss-cache/harness/` ✓ (M4-02 + M4-03).
    (4) Bare `voss` can boot through compiled harness logic ✓ (M4-03 + M4-04).
</verification>

<success_criteria>
- CI step `python -m voss.cli check voss/harness/agent/` lives in `.github/workflows/ci.yml` between install and pytest.
- README install section contains the eager-compile one-liner with brief framing.
- `voss/harness/diagnostics.py` exposes `check_harness_cache` and includes it in `run_all_checks`.
- Doctor row is informational (WARN never blocks; OK or no-sources also pass).
- `tests/harness/test_doctor.py` has at least the row-existence sentinel.
- Full M4 test suite green; full DOG-01..DOG-08 coverage verified across plans:
    - DOG-01..DOG-05: M4-03 (file existence + parse).
    - DOG-06: M4-02 (dir walk) + M4-05 (CI gate).
    - DOG-07: M4-03 (boot dispatch) + M4-04 (subprocess smoke).
    - DOG-08: M4-02 (cache module + manifest) + M4-03 (compile produces artifacts).
</success_criteria>

<output>
After completion, create `.planning/phases/M4-voss-authored-harness-loop/M4-05-SUMMARY.md` documenting:
- Exact insertion point of the CI step (line number after edits).
- README section where the one-liner landed.
- `check_harness_cache` body + behavior under all three branches (no-sources/stale/fresh).
- Full M4 phase wrap-up:
    - All 8 DOG requirements traced to passing tests / grep contracts.
    - All 16 D-XX decisions implemented or noted as do-not-delete guards (D-09 parity oracle stays).
    - All M4-VALIDATION rows flipped from ❌ to ✓.
- Pointer to STATE.md update: M4 status flips from "context gathered — ready to plan" to "executing" → "complete" after all 5 plans land.
</output>
