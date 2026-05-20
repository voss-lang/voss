---
phase: M15-skill-plugin-marketplace-caps-01f
plan: 06
subsystem: harness
tags: [skill-marketplace, e2e, fixture, documentation, scope-fence]

requires: ["M15-05"]
provides:
  - GREEN e2e fixture-cycle test (trust→add→list→run→update→remove)
  - committed signature verification guard (stale-sig detection)
  - gate-only confinement documented in README + skill list + doctor
  - scope-fence audit (no forbidden subsystem introduced)
affects:
  - tests/e2e/test_skill_lifecycle.py
  - voss/harness/cli.py

tech-stack:
  added: []
  patterns: [e2e-subprocess-runner, scope-fence-audit]

key-files:
  modified:
    - tests/e2e/test_skill_lifecycle.py
    - voss/harness/cli.py

key-decisions:
  - "e2e test uses subprocess runner (not click.testing.CliRunner) for realistic CLI exercise."
  - "add-before-trust refusal asserted before trust+add — proves trust gate live in e2e path."
  - "skill run assertion checks skill was found and dispatch attempted (not 'unknown skill'), accepts stub output variation."
  - "doctor surfaces 'gate-level only (OS-level sandbox deferred)' when third-party skills installed."

patterns-established:
  - "Committed signature guard: CI test verifies manifest.toml.sig against test_signing_key.pub every run."

requirements-completed: [SKILL-06]

duration: 10min
completed: 2026-05-20
---

# Phase M15-06: E2E Fixture + Documentation Summary

**CI runs the full lifecycle against the shipped signed bundle; the gate-only confinement limitation is documented in three user-visible surfaces.**

## Performance

- **Duration:** 10 min
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Implemented `test_fixture_bundle_e2e` driving the full trust→add→list→run→update→remove cycle against `examples/skills/voss-git-summary/` using the e2e subprocess runner.
- Added `test_committed_signature_verifies` guard — CI catches stale committed signatures.
- Trust gate exercised end-to-end: add-before-trust is refused (exit non-zero), add-after-trust succeeds.
- Added doctor caveat surfacing "gate-level only (OS-level sandbox deferred)" when third-party skills installed.
- Confirmed confinement limitation documented in 3 surfaces: README, `voss skill list`, `voss doctor`.

## Task Commits

1. **Task 1: e2e lifecycle test** — `232e2ea` (refactor)
2. **Task 2: doctor confinement caveat** — `7a31107` (feat)

## Verification

- `pytest tests/e2e/test_skill_lifecycle.py -x -q` — 2/2 GREEN (test_committed_signature_verifies + test_fixture_bundle_e2e)
- `pytest tests/harness/skill/ tests/e2e/test_skill_lifecycle.py -q -m "not live"` — 17/17 GREEN (full SKILL-01..06)
- `pytest tests/harness/test_extensions.py tests/harness/test_recorder.py -x` — no regression
- No `xfail`/unconditional `skip` in test_skill_lifecycle.py

## Scope-Fence Audit

| Pattern | Grep result | Status |
|---------|------------|--------|
| Central registry/search | 0 hits | CLEAN |
| OS sandbox (seccomp/container) | 0 hits | CLEAN |
| GPG (gnupg/gpg) | 0 hits | CLEAN |
| M9 TUI (textual/rich) | 0 hits | CLEAN |
| Parallel manifest system | 0 hits | CLEAN |
| New .voss interpreter | 0 hits | CLEAN |

**No forbidden subsystem was introduced in the M15 phase.**

## Confinement Documentation Surfaces

1. `examples/skills/voss-git-summary/README.md` — "NOT sandboxed (OS-level sandboxing is deferred)"
2. `voss skill list` footer — "scope enforcement applies to harness tool calls only (OS-level sandbox deferred)"
3. `voss doctor` — "gate-level only (OS-level sandbox deferred)" when third-party skills installed
