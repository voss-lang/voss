---
phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot
plan: 03
subsystem: api
tags: [click, cli, exit-codes, advice, voss-agent-id]

# Dependency graph
requires:
  - phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot (plan 02)
    provides: claims engine (overlap + SQLite + atomic_stake) the verbs wrap
provides:
  - claims_group click group — stake/check/release/extend/list, registered in AGENT_COMMANDS
  - exit contract 0 clear / 1 conflict / 2 identity-usage across all verbs
  - VOSS_AGENT_ID identity resolution with actionable exit-2 stderr
  - advice arrays on conflict --json (runnable `voss bus send` naming owner, D-07/VBUS-06)
affects: [V17-04, V17-06, V17-07]

# Tech tracking
tech-stack:
  added: []
  patterns: [shared _emit_conflict for stake/check conflict paths, claim_id = agent:patternset-sha1 for D-04 idempotent refresh]

key-files:
  created: []
  modified:
    - voss/harness/claims.py
    - voss/harness/cli.py
    - tests/harness/claims/test_claims_verbs.py
    - tests/harness/claims/test_claims_advice.py
    - tests/harness/claims/test_claims_ttl.py
    - tests/harness/claims/test_claims_concurrent.py

key-decisions:
  - "claim_id = <agent_id>:<sha1(sorted patterns)[:8]> — same-set re-stake hits INSERT OR REPLACE on the same id (D-04 refresh); distinct sets coexist as separate claims (D-03 release/extend by id still works)"
  - "extend_claim widened to claim_id=None → refreshes all own unexpired claims (bare `voss claims extend`); engine change kept in claims.py"
  - "advice[0] = voss bus send \"@<owner> I need <pattern> — when are you done?\"; advice[1] = claims check retry hint"
  - "list requires identity too (uniform exit-2 contract across all five verbs)"

patterns-established:
  - "Conflict emission shared between stake and check (_emit_conflict): NDJSON one record per conflicting claim, each carrying the advice array"

requirements-completed: [VBUS-01, VBUS-02, VBUS-06]

# Metrics
duration: 12min
completed: 2026-06-10
---

# Phase V17 Plan 03: Claims CLI Verbs Summary

**`voss claims stake/check/release/extend/list` shipped as a shell pre-edit guard — 0/1/2 exit contract, VOSS_AGENT_ID identity, owner-naming advice arrays; full claims suite 12/12 GREEN including the real-subprocess concurrency race**

## Performance

- **Duration:** ~12 min
- **Completed:** 2026-06-10
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Two-agent acceptance sequence passes serverless: A stakes `src/api/**`, B's check exits 1 naming agent-a, disjoint check exits 0, B's conflicting stake atomically rejected, release→stake succeeds
- Concurrent test now races 5 real `python -m voss.cli claims stake` subprocesses → exactly one exit-0 winner through the full CLI stack
- `check --json` conflict emits non-empty advice with runnable `voss bus send "@agent-a ..."` (VBUS-06 acceptance)
- TTL: `--ttl 1` claim stops blocking after expiry; default stake shows `expires_at` ≥ now+1700 via `list --json`
- Registered via 2-line cli.py diff (import + tuple entry); board/jobs byte-untouched; coherence guard still green

## Task Commits

1. **Task 1: claims click group + identity + exit codes + advice** - `6a91215` (feat)
2. **Task 2: Register claims_group in main CLI** - `21d62b0` (feat)

## Files Created/Modified
- `voss/harness/claims.py` - five subcommands + _resolve_agent_id/_emit_conflict/_advice_for_conflict helpers; extend_claim widened for bare-extend
- `voss/harness/cli.py` - import + AGENT_COMMANDS entry only
- `tests/harness/claims/*` - xfail scaffolding removed from verbs/advice/ttl/concurrent (now genuinely GREEN)

## Decisions Made
See frontmatter key-decisions.

## Deviations from Plan

None of substance — plan executed as written. Minor notes:
- `test_env_injection.py` now reports XPASS (its claims-CLI assertions pass once verbs exist); mark removal belongs to V17-04 per its reason string. strict=False, so no gate impact.
- `extend` exits 2 when nothing matched (no unexpired own claim) — plan left the no-match behavior unspecified; 2 fits the usage-error slot.

## Issues Encountered
None — 11/11 CliRunner tests green on first run; subprocess race green immediately after registration.

## User Setup Required
None.

## Next Phase Readiness
- V17-04 (identity injection): Tauri spawn sites + slugRegistry; removes test_env_injection xfail marks
- V17-07 (doc): `voss claims <verb> --help` all exit 0 and are stable to document
- Bus wave (V17-05/06) unchanged, still V15-gated

---
*Phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot*
*Completed: 2026-06-10*
