---
phase: V16-managed-docs-prompt-generation
plan: 04
subsystem: harness
tags: [prompts, sha256, hash-guard, str-replace, override]

requires:
  - phase: V16-03
    provides: sync() orchestrator + .voss/sync-state.json manifest + force param
provides:
  - "voss/harness/prompt_override.py load_prompt — project copy w/ ${} str.replace substitution, byte-identical package fallback (R5/D-18)"
  - "reviewer_a/reviewer_b/em prompts resolved through load_prompt at load time (project-tunable)"
  - "prompt-sync hash-guard loop in sync(): edited skip+warn exit 0, --force overwrite, missing-manifest treat-as-edited (R6/D-11/D-16)"
affects: [V17]

tech-stack:
  added: []
  patterns:
    - "runtime prompt substitution = plain str.replace of ${AGENT}/${PROJECT}/${WORKSPACE} — never Jinja at runtime (D-18)"
    - "hash-guard skip never adopts silently: missing manifest entry stays missing until --force (D-11)"

key-files:
  created:
    - voss/harness/prompt_override.py
    - tests/harness/test_prompt_override.py
  modified:
    - voss/sync.py
    - voss/harness/board/reviewer_a.py
    - voss/harness/board/reviewer_b.py
    - voss/harness/em/llm.py
    - tests/cli/test_sync.py
    - pyproject.toml

key-decisions:
  - "Module constants (REVIEWER_A_ROLE_PROMPT etc.) kept as package defaults — tests import/compare them; the USE sites resolve through load_prompt per call, strictly fresher than import-time lookup"
  - "reviewer_a uses self._cwd for the project root; reviewer_b/em use Path.cwd() (no cwd on their seams)"
  - "default_runtime_vars(agent, root) helper: AGENT per prompt role, PROJECT=root.name, WORKSPACE=str(root)"
  - "Skip path preserves the OLD recorded hash in the manifest (drift evidence survives); missing entries stay missing until --force re-adopts"

patterns-established:
  - "Prompt sync renders package template at sync time; ${} placeholders pass through to the file and fill at load time"

requirements-completed: [R5, R6]

duration: 12min
completed: 2026-06-10
---

# Phase V16 Plan 04: Prompt Sync + Override Loader Summary

**Reviewer-A/B + EM prompts sync to .voss/prompts/ as editable .txt with sha256 hash-guard (edited=skip+warn exit 0, --force overwrites, missing manifest=treat-as-edited), and load_prompt prefers the project copy with plain ${} str.replace at load time**

## Performance

- **Duration:** 12 min
- **Started:** 2026-06-10T17:51:00Z
- **Completed:** 2026-06-10T18:03:38Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- `load_prompt(name, *, resource, cwd, runtime_vars)`: project copy at `.voss/prompts/<name>.txt` wins; `${AGENT}/${PROJECT}/${WORKSPACE}` filled via str.replace (D-18 — user edits can contain `{{ }}` safely); absent copy → `render_package_template` byte-identical to today (R5, test-pinned)
- 3 use sites converted: reviewer_a (`self._cwd`), reviewer_b + em (`Path.cwd()`) resolve per call; exported constants preserved (sentinel tests untouched); other 7 prompts untouched
- Prompt loop in `sync()`: render → hash-guard (on-disk sha256 vs manifest) → write/unchanged/skip(edited)/force-overwrite; warnings via stderr name the file; exit 0 (D-15); idempotency preserved (two clean syncs byte-identical)
- Live smoke: 8 written → edit em_system → `skipped (edited)` + warning + exit 0 → `--force` → overwritten
- 9 new tests (4 loader + 5 CLI hash-guard); full regression green (cli, board, em, fence, V16 suites)
- `templates/prompts/*` added to package-data — pre-existing wheel gap (module-level prompt constants could never have rendered from an installed wheel)

## Task Commits

1. **Task 1: prompt_override loader + 3 sites** - `5a0194f` (test) + `96275f2`/`e831ac2` (feat — partially absorbed by concurrent auto-committer, content verified)
2. **Task 2: hash-guard loop** - `92e93c2` (test, absorbed) + `e50f3b6`/`3a291c4` (feat)

## Files Created/Modified
- `voss/harness/prompt_override.py` - load_prompt + default_runtime_vars
- `voss/harness/board/reviewer_a.py` - SubagentSpec role_prompt via load_prompt(cwd=self._cwd)
- `voss/harness/board/reviewer_b.py` - system message via load_prompt at review() time
- `voss/harness/em/llm.py` - system message via load_prompt at em_plan() time
- `voss/sync.py` - _read_manifest (fail-safe, T-V16-10), _PROMPT_TEMPLATES loop with hash-guard
- `tests/harness/test_prompt_override.py` / `tests/cli/test_sync.py` - 9 new tests
- `pyproject.toml` - package-data + templates/prompts/*

## Decisions Made
- Use-site resolution over import-time constants: project copy honored on every call, no reimport needed; constants stay as the package-default reference the existing sentinel tests compare against
- Manifest skip semantics: edited file keeps its old recorded hash (drift evidence), missing entry never auto-added — both paths require explicit --force to re-adopt (D-11 strictly enforced)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] templates/prompts/* absent from package-data**
- **Found during:** Task 2 (flagged forward from V16-02)
- **Issue:** Installed wheels exclude voss/templates/prompts/ — both sync-time prompt rendering AND the pre-existing module-level constants would TemplateNotFound from a wheel
- **Fix:** Added `templates/prompts/*` to `[tool.setuptools.package-data]`
- **Files modified:** pyproject.toml
- **Verification:** entry present; render paths exercised by tests
- **Committed in:** 3a291c4

**2. [Environment] Commits absorbed by concurrent auto-committer (3rd/4th occurrence)**
- **Found during:** Tasks 1 and 2 commits
- **Issue:** 96275f2 (loader + 3 sites), 92e93c2 (tests, bundled w/ unrelated site/ change), e50f3b6 (partial sync.py) committed by the concurrent process before intended commits
- **Fix:** Verified content via git log/diff after each; remaining hunks committed as e831ac2/3a291c4
- **Verification:** all planned files committed; suites green against HEAD
- **Committed in:** 96275f2, 92e93c2, e50f3b6, e831ac2, 3a291c4

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 environment/attribution)
**Impact on plan:** Packaging fix required for wheel correctness. Commit attribution cosmetic only.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- **Phase V16 complete: 4/4 plans, R1–R6 all delivered** (R5/R6 stretch included)
- V17 can rely on `voss sync` as the delivery vehicle for managed agent-coordination docs (label conventions land via these templates)
- Note: reviewer_b/em use Path.cwd() for project-root resolution — if a future harness seam carries cwd explicitly, thread it through load_prompt there

---
*Phase: V16-managed-docs-prompt-generation*
*Completed: 2026-06-10*
