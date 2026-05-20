---
phase: M15-skill-plugin-marketplace-caps-01f
plan: 05
subsystem: harness
tags: [skill-marketplace, adapter, registry, cli, recorder, dispatch]

requires: ["M15-04"]
provides:
  - make_voss_skill_handler — SkillEntry-compatible handler (compile + subprocess under scoped gate)
  - load_voss_skills — discover installed bundles and register as SkillEntry handlers
  - compile_voss_file — public wrapper (no private cross-module coupling)
  - voss skill add/list/remove/update/trust CLI subcommands
  - skill_events + scope_denials audit events in RunRecorder
affects:
  - voss/harness/skill/adapter.py
  - voss/harness/skill_registry.py
  - voss/harness/cli.py
  - voss/harness/recorder.py
  - voss/harness/session.py
  - voss/cli.py
  - tests/harness/skill/test_registry.py

tech-stack:
  added: []
  patterns: [subprocess-confinement, scoped-gate-dispatch, no-builtin-shadowing, audit-events]

key-files:
  created:
    - voss/harness/skill/adapter.py
  modified:
    - voss/harness/skill_registry.py
    - voss/harness/cli.py
    - voss/harness/recorder.py
    - voss/harness/session.py
    - voss/cli.py
    - tests/harness/skill/test_registry.py

key-decisions:
  - "Public compile_voss_file wrapper eliminates private _compile_source cross-module coupling (RESEARCH OQ1, M7 SDK discipline)."
  - "Adapter uses subprocess.run only — no in-process exec of third-party code (T-M15-05-03)."
  - "load_voss_skills runs AFTER built-ins in default_skill_registry; built-in ids win on collision (T-M15-05-02)."
  - "scoped_gate(spec, ctx.gate) confines every third-party dispatch (T-M15-05-01); auto_yes=True, store=None prevents prompt/store bypass (T-M15-05-06)."
  - "RunRecorder extension is additive only — existing observe/finalize paths byte-unchanged."

patterns-established:
  - "VossSkillAdapter: compile .voss to tmpdir → subprocess.run under scoped gate."
  - "load_voss_skills: enumerate enabled bundle manifests with voss_entry → register non-shadowing SkillEntry."
  - "observe_skill_event/observe_scope_denial for audit trail."

requirements-completed: [SKILL-01, SKILL-02, SKILL-03, SKILL-04, SKILL-05]

duration: 15min
completed: 2026-05-20
---

# Phase M15-05: Skill Dispatch + CLI + Audit Summary

**Third-party .voss skills now register, dispatch, and audit through the existing harness — the full headless CLI verb set is wired.**

## Performance

- **Duration:** 15 min
- **Tasks:** 3
- **Files created:** 1
- **Files modified:** 6

## Accomplishments

- Created `adapter.py` with `make_voss_skill_handler` — compiles bundle `.voss` via public `compile_voss_file` and subprocess-runs under `scoped_gate(spec, ctx.gate)`. No in-process exec of third-party code.
- Added public `compile_voss_file` to `voss/cli.py` — thin wrapper over `_compile_source`, removes private cross-module coupling.
- Extended `skill_registry.py` with `load_voss_skills(cwd, registry)` — discovers enabled installed bundles with `voss_entry`, registers `SkillEntry` handlers after built-ins (built-in ids never shadowed).
- Added 5 CLI subcommands to `skill_group`: `add`, `list`, `remove`, `update`, `trust` — all auto-registered via existing `AGENT_COMMANDS`.
- Extended `RunRecorder` with `skill_events` + `scope_denials` lists, `observe_skill_event`/`observe_scope_denial` methods, forwarded in `finalize()` to `RunRecord`.
- Rewrote W0 RED `test_registry.py` tests to exercise adapter + registry directly with proper ctx shape.

## Task Commits

1. **Task 1: compile_voss_file + adapter** — `6d66175` (feat)
2. **Task 2: load_voss_skills + CLI verbs** — `28142ed` (feat)
3. **Task 3: RunRecorder extension** — `281846f` (feat)

## Verification

- `pytest tests/harness/skill/test_registry.py -x` — 3/3 GREEN (test_voss_skill_dispatch, test_unknown_skill_not_found, test_builtin_not_shadowed)
- `pytest tests/harness/skill/ -q -m "not live"` — 15/15 GREEN (SKILL-01..05 all satisfied)
- `pytest tests/harness/test_recorder.py -x` — 14 pass, 1 skip (no regression)
- `pytest tests/harness/test_extensions.py -x` — 4/4 GREEN (no regression)
- `skill_group --help` shows `['add', 'list', 'remove', 'run', 'trust', 'update']`
- `grep "exec(" voss/harness/skill/adapter.py` — 0 matches (no in-process exec)
- `grep "_compile_source" voss/harness/` — 0 matches (no private cross-module import)
- RunRecorder `finalize()` forwards `skill_events` + `scope_denials` into RunRecord (verified inline)
