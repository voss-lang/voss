---
phase: M15-skill-plugin-marketplace-caps-01f
plan: 03
subsystem: harness
tags: [skill-marketplace, permission-scoping, permission-gate, validation]

requires: ["M15-01"]
provides:
  - ScopeSpec parsed from manifest [scopes] defensively
  - scope_to_mode mapping tools scope to existing Mode literal tiers
  - scoped_gate capping PermissionGate mode to min(base, declared)
  - strict default-deny (read-only plan mode, no net) when scopes are missing or unrecognized
affects:
  - voss/harness/skill/__init__.py
  - voss/harness/skill/scope.py
  - tests/harness/skill/test_scope.py

tech-stack:
  added: []
  patterns: [gate-binding, default-deny-scoping, non-escalation-policy]

key-files:
  created:
    - voss/harness/skill/scope.py
  modified:
    - tests/harness/skill/test_scope.py
    - voss/harness/skill/__init__.py

key-decisions:
  - "Bypassed building a secondary authorization engine, instead routing permission scopes directly onto the existing Mode tiers (plan, edit, auto) inside permissions.py."
  - "Forced non-persistence and non-interactivity by overriding auto_yes=True and store=None in the returned scoped PermissionGate, preventing prompt-bypass security escapes."
  - "Maintained strict non-escalation constraint by resolving effective mode via min(base_gate.mode, scope_to_mode(spec.tools)), ensuring a tighter runtime boundary is never bypassed."

patterns-established:
  - "Defensive configuration extraction defaulting missing/unrecognized types to read-only."
  - "Capped Mode resolution using an ordered dict-literal rank (plan < edit < auto)."

requirements-completed: [SKILL-04]

duration: 10min
completed: 2026-05-19
---

# Phase M15-03: Skill Marketplace Wave 1 Scoping Spine Summary

**The harness now features the complete permission-scoping spine (`voss/harness/skill/scope.py`) governing all future third-party skill capabilities.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-05-19T18:26:05Z
- **Completed:** 2026-05-19T18:30:00Z
- **Tasks:** 2
- **Files created/modified:** 3

## Accomplishments

- Implemented frozen `ScopeSpec(tools="read-only", fs="cwd", net=False)` tracking declared manifest permissions.
- Implemented `scope_spec_from_manifest` parsing manifest dictionaries safely; malformed structures, non-dict payloads, or missing elements correctly default-deny to `tools="read-only", fs="cwd", net=False`.
- Implemented `scope_to_mode` mapping capabilities to the existing permission vocabulary: `"read-only" -> "plan"`, `"mutating" -> "edit"`, `"all" -> "auto"`. Unrecognized keys fall back to `"plan"`.
- Implemented `scoped_gate` enforcing non-escalating authority (`min(base, declared)`) and disabling prompts/persistence (`auto_yes=True, store=None`).
- Updated `tests/harness/skill/test_scope.py` to match exact Mode rejection and network reason text, turning all **2 scope tests 100% GREEN**.

## Task Commits

1. **Task 1: ScopeSpec and mapping implementation** - `67be8fb` (feat)
2. **Task 2: scoped_gate mapping to PermissionGate** - `da1e72d` (feat/test)

## Verification

- `pytest tests/harness/skill/test_scope.py -vv` runs and passes all 2 tests **100% GREEN**.
- Tested inline permission assertions mapping:
  `BLOCK True ALLOW True AUTOYES True STORE True`
- `grep -n "class PermissionGate" voss/harness/skill/scope.py` returned 0 matches, confirming zero secondary enforcement engines are introduced.
- Rest of the test suite collects cleanly, with the remaining unimplemented waves appropriately **RED** (no regressions).
