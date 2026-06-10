---
phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot
plan: 07
subsystem: testing
tags: [docs, coherence-guard, agents-md, handoff]

# Dependency graph
requires:
  - phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot (plan 03)
    provides: shipped claims verbs whose --help the doc test asserts
  - phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot (plan 04)
    provides: VOSS_AGENT_ID injection semantics documented
provides:
  - docs/agent-coordination.md — verbs, 0/1/2/124 exit contract, env vars, label vocabulary, pre-edit guard example
  - V16 handoff note (.planning/phases/V16-managed-docs-prompt-generation/V17-COORDINATION-HANDOFF.md) with condensation checklist + coherence confirmation
  - VBUS-08 phase-end verification record (guard green, 147 cargo tests, swarm/+sandbox.rs diff-empty)
affects: [V16, V17-05, V17-06]

# Tech tracking
tech-stack:
  added: []
  patterns: [docs/ bare-heading no-frontmatter style, handoff-note-instead-of-template-edit boundary]

key-files:
  created:
    - docs/agent-coordination.md
    - .planning/phases/V16-managed-docs-prompt-generation/V17-COORDINATION-HANDOFF.md
  modified:
    - tests/harness/test_coordination_doc.py

key-decisions:
  - "Bus --help test keeps a per-test xfail(strict=False, V15-gated) instead of the module mark — doc + claims tests assert directly now, bus portion XPASSes when V17-06 ships"
  - "Bus verbs documented from the locked SPEC contract pre-implementation, flagged 'requires voss serve (V15)' in both doc and handoff"
  - "Doc includes the T-V17-18 mitigation line: no secrets in bus messages (journal is plaintext)"

patterns-established: []

requirements-completed: [VBUS-07, VBUS-08]

# Metrics
duration: 8min
completed: 2026-06-10
---

# Phase V17 Plan 07: Coordination Doc + Coherence Gate Summary

**docs/agent-coordination.md documents the full coordination vocabulary with a V16 AGENTS.md handoff, and the VBUS-08 phase-end gate is green: swarm/ + sandbox.rs byte-unchanged, 147 cargo tests pass, zero parallel substrate**

## Performance

- **Duration:** ~8 min
- **Completed:** 2026-06-10
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Doc covers: env vars (VOSS_AGENT_ID always; PORT/TOKEN V15-gated), all five claims verbs with flags/TTL/idempotency, all three bus verbs from the SPEC contract, exit codes 0/1/2/124, the four conventional labels, a runnable pre-edit guard snippet, and the no-secrets caveat
- V16 handoff note lists exactly what to condense into the managed AGENTS.md section, names docs/agent-coordination.md as source of truth, and records that V17 touched no AGENTS.md template
- VBUS-08 verified post-phase: coherence guard 3/3; `cargo test -p voss-app-core` 147 passed including the 4 sandbox.rs tests unmodified; `git diff --stat` empty for both swarm/ and sandbox.rs (last touches pre-date V17: A13-01, V14-11); no fs-watcher dep beyond the pre-V17 watchdog baseline
- Full V17 test surface: 19 passed + 5 xfail — the xfails are exactly the V15-gated bus set (4 bus scaffold tests + the bus --help portion)

## Task Commits

1. **Task 1: doc + handoff note** - `e5ca299` (docs)
2. **Task 2: coherence verification + confirmation line** - `90bc5b2` (chore)

## Files Created/Modified
- `docs/agent-coordination.md` - coordination conventions for agent consumption
- `.planning/phases/V16-managed-docs-prompt-generation/V17-COORDINATION-HANDOFF.md` - V16 folding instructions + guard confirmation
- `tests/harness/test_coordination_doc.py` - module xfail removed; bus portion per-test gated

## Decisions Made
See frontmatter key-decisions.

## Deviations from Plan

None of substance. One alignment fix: V17-01's bus --help test used pytest.fail on ImportError (would have failed the now-ungated module); converted to the per-test xfail the plan's own acceptance language describes ("XPASSes the bus portion once V17-06 ships").

## Issues Encountered
None.

## User Setup Required
None.

## Next Phase Readiness
- V17 executable waves complete: 01 (scaffold), 02 (engine), 03 (verbs), 04 (identity), 07 (doc + gate). Remaining: V17-05/06 (bus server + client) gated on V15 shipping the sidecar/always-on server
- When V17-06 lands: remove xfail marks from tests/harness/bus/ + the bus --help test; doc already covers the verbs
- One manual VALIDATION item open from V17-04: `env | grep VOSS_AGENT_ID` in a live pane

---
*Phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot*
*Completed: 2026-06-10*
