---
phase: V12-safety-factory-fallbacks
plan: 01
subsystem: api
tags: [python, pydantic, safety-policy, classifier, cognition, factory-fallback]

# Dependency graph
requires:
  - phase: M2
    provides: strict .voss/*.yml schema pattern (cognition_schemas + _load_yaml)
provides:
  - SafetyConfig strict .voss/safety.yml schema (runbooks/pipelines/factory-only paths+ops/latency/scaffolds) with reference validation
  - safety.py pure classifier (classify/decide) + SafetyActorContext/SafetyClassification/SafetyDecision
  - cognition.load() loads .voss/safety.yml into CognitionBundle.safety (missing → None)
affects: [V12-02, V12-03 (PermissionGate overlay), V12 EM parity, V12 audit]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Strict Pydantic safety schema with @model_validator(mode='after') failing closed on unknown runbook/pipeline refs (T-V12-01)"
    - "Pure deterministic classifier: category precedence paths→operations→latency→scaffolds, first match wins, label 'none' = ordinary path"
    - "Schema in cognition_schemas.py; runtime/classifier types in safety.py re-exporting the config types"

key-files:
  created:
    - voss/harness/safety.py
    - tests/harness/test_safety_policy.py
  modified:
    - voss/harness/cognition_schemas.py
    - voss/harness/cognition.py

key-decisions:
  - "Safety schema lives in cognition_schemas.py (consistent with other configs); safety.py re-exports + adds pure runtime types — satisfies both files_modified"
  - "requires_confirmation set when 'irreversible' in a rule's classes (VSAFE-01 hook for later plans)"
  - "weak_model_scaffolds only fire for rules constraining by role/tier with a matching actor; strong/unconfigured actors exempt"
  - "Did NOT add safety.yml to the init scaffold seed (missing file is valid → None); avoids touching init tests"

patterns-established:
  - "classify(config, tool_name, tool_args, *, tool_meta?, actor?) → SafetyClassification; decide(classification) → SafetyDecision"
  - "arg extraction: _PATH_KEYS (path/file/target/dest) + _CMD_KEYS (cmd/command/argv/script)"

requirements-completed: [VSAFE-02, VSAFE-03, VSAFE-04, VSAFE-06]

# Metrics
duration: 16min
completed: 2026-06-07
---

# Phase V12 Plan 01: Safety Policy Foundation Summary

**Strict `.voss/safety.yml` schema (fail-closed on unknown runbook/pipeline refs) + a pure deterministic classifier routing factory-only paths/operations, latency pipelines, and weak-model scaffolds — no runtime enforcement yet.**

## Performance

- **Duration:** ~16 min
- **Completed:** 2026-06-07
- **Tasks:** 2 (both auto)
- **Files created:** 2 (safety.py, test); **modified:** 2 (cognition_schemas, cognition)

## Accomplishments
- `cognition_schemas.py` — `SafetyConfig` + `SafetyRunbook`/`SafetyPipeline`/`SafetyPathRule`/`SafetyOperationRule`/`SafetyLatencyRule`/`SafetyScaffoldRule`, all `extra="forbid"`. `@model_validator` rejects rules referencing undeclared runbooks/pipelines, naming the missing ref (T-V12-01).
- `safety.py` — pure `classify()` (paths→operations→latency→scaffolds precedence, fnmatch globs/patterns, dangerous classes, actor role/tier) + `decide()`; `SafetyActorContext`/`SafetyClassification`/`SafetyDecision` dataclasses; re-exports the config types.
- `cognition.py` — loads `.voss/safety.yml` into `CognitionBundle.safety`; missing file → `None`, no init failure; bad refs surface in `load_errors`.

## Files Created/Modified
- `voss/harness/safety.py` — classifier + decision types (232 lines)
- `tests/harness/test_safety_policy.py` — 18 tests (242 lines)
- `voss/harness/cognition_schemas.py` — +safety schema
- `voss/harness/cognition.py` — +safety field + loader

## Decisions Made
See `key-decisions` frontmatter. All within plan scope; `.voss/permissions.yml` untouched.

## Deviations from Plan
None - plan executed as written. No new dependencies (pydantic/yaml already in stack).

## Issues Encountered
None.

## Verification
- `.venv/bin/python -m pytest tests/harness/test_safety_policy.py -q` → **18 passed** (schema extra-forbid, unknown runbook/pipeline/scaffold-ref rejection naming the ref, loader missing→None / valid→loaded / bad-ref→load_error, classifier path glob + irreversible confirm, operation tool-filter, latency only-configured, scaffold cheap-match/strong-exempt, no-policy→none, decide routing)
- `.venv/bin/python -m pytest tests/harness/test_cognition_schemas.py tests/harness/test_cognition.py tests/harness/test_permission_rules.py tests/harness/test_permissions.py test_cognition_overflow test_permissions_modes test_repl_cognition -q` → **all green** (permissions behavior unchanged; CognitionBundle field additive)

## Next Phase Readiness
- Classifier + decision types ready for the PermissionGate safety overlay (next plan) — `classify`/`decide` are pure and the gate runs them before mode/prompt shortcuts (auto_yes cannot bypass).
- Audit fields (VSAFE-05) and EM parity (VSAFE-07) consume `SafetyDecision`/`SafetyClassification` in later plans.

---
*Phase: V12-safety-factory-fallbacks*
*Completed: 2026-06-07*
