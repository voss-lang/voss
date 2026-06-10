---
phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot
plan: 02
subsystem: api
tags: [sqlite, wal, begin-immediate, fnmatch, glob, uri, ttl]

# Dependency graph
requires:
  - phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot (plan 01)
    provides: RED test surface (test_overlap.py turned GREEN here; CLI tests stay xfail for V17-03)
provides:
  - voss/harness/claims.py engine — overlap algorithms + SQLite storage + atomic stake (no CLI yet)
  - glob_patterns_overlap / uri_overlap / patterns_overlap (pure static, D-05/D-06)
  - canonicalize_pattern with sandbox.rs-style traversal rejection
  - open_claims_db (.voss-cache/claims.sqlite, WAL, busy_timeout=5000) + atomic_stake (BEGIN IMMEDIATE) + active_claims/all_claims/release_claims/extend_claim/prune_expired/new_claim_id
affects: [V17-03, V17-04]

# Tech tracking
tech-stack:
  added: []
  patterns: [BEGIN IMMEDIATE check-and-stake transaction, base-dir+glob-tail static overlap, expires_at filtering in every read path]

key-files:
  created:
    - voss/harness/claims.py
  modified:
    - tests/harness/claims/test_overlap.py

key-decisions:
  - "Removed xfail scaffolding from test_overlap.py (V17-01 idiom: mark removed when the wave turns GREEN) — 6 SPEC cases now genuinely pass"
  - "canonicalize_pattern rejects any pattern containing '..' substring (blunt, mirrors sandbox.rs validate_scope) plus a normalized cwd-escape check; URIs pass through"
  - "Added new_claim_id() + all_claims() + prune_expired() beyond the interface list — V17-03 verbs need id minting, list --all, and prune hygiene"
  - "patterns_overlap never cross-matches URI vs glob — kinds are disjoint namespaces"

patterns-established:
  - "Claims read paths always carry `expires_at > now` in SQL; expiry is query-time, prune is optional hygiene"
  - "atomic_stake excludes same-agent rows in the conflict scan (D-04 idempotent refresh falls out of the SQL filter)"

requirements-completed: [VBUS-02]

# Metrics
duration: 10min
completed: 2026-06-10
---

# Phase V17 Plan 02: Claims Engine Summary

**Glob/URI overlap engine + WAL SQLite storage at .voss-cache/claims.sqlite with BEGIN IMMEDIATE atomic stake — 8 racing processes grant exactly one winner**

## Performance

- **Duration:** ~10 min
- **Completed:** 2026-06-10
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- All six SPEC overlap cases GREEN in test_overlap.py (xfail scaffold removed); idempotent same-base glob and mixed-set `patterns_overlap` verified
- Exactly-one-winner concurrency proven live: 8 spawned processes racing `atomic_stake` on `src/api/**` → single winner, losers receive conflict rows
- TTL semantics: 0.3s claim blocks then unblocks after expiry; default stake lands `expires_at` 1800s out; extend refreshes own unexpired claims only, refuses foreign agents
- Traversal rejected (`../../etc/passwd` → ValueError) per sandbox.rs validate_scope precedent; sandbox.rs untouched

## Task Commits

1. **Task 1: Overlap engine** - `c4430f2` (feat) — note: full claims.py (both layers) landed here
2. **Task 2: SQLite storage + atomic stake** - `bd48a8e` (feat) — docstring grep-gate fix

## Files Created/Modified
- `voss/harness/claims.py` - overlap engine + storage layer + atomic stake (engine only; CLI verbs in V17-03)
- `tests/harness/claims/test_overlap.py` - xfail scaffolding removed, plain imports, 6 passing

## Decisions Made
See frontmatter. Notably: engine exports a few helpers beyond the planned interface (`new_claim_id`, `all_claims`, `prune_expired`) that V17-03's verbs require.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Wrong assumption] Task 2 verify tests are CLI-driven, cannot pass in this plan**
- **Found during:** Task 2
- **Issue:** Plan's acceptance criteria say test_claims_concurrent.py / test_claims_ttl.py "pass", but both drive the click CLI (`voss claims` subprocess / claims_group) that V17-03 ships — the same plan's objective says "no CLI yet"
- **Fix:** Tests stay xfail (verify command exits 0); engine-level proof run instead: 8-process spawn race (exactly one winner), TTL expiry/default, D-04 idempotency, release/extend semantics — all green (transcript above)
- **Verification:** `/tmp/v17_02_verify.py` output; V17-03 turns the CLI tests GREEN
- **Committed in:** bd48a8e

**2. [Rule 3 - Blocking] Docstring tripped the `:memory:` grep gate**
- **Found during:** Task 2 gate check
- **Issue:** Module docstring warned "never `:memory:`" — `grep -c ':memory:'` returned 1, gate requires 0
- **Fix:** Reworded to "never an in-memory database"
- **Committed in:** bd48a8e

**3. [Minor] click import skipped; both tasks landed in one file write**
- Plan listed click among imports — unused until V17-03 adds verbs; omitted to keep the module lint-clean. Storage layer was written together with the overlap engine, so Task 1's commit contains both layers; Task 2's commit is the gate fix only.

---

**Total deviations:** 3 (1 wrong assumption, 1 blocking, 1 minor)
**Impact on plan:** No scope creep; CLI-test GREEN deferred to V17-03 where it belongs.

## Issues Encountered
- multiprocessing spawn cannot re-import a stdin script — verification script written to a temp file instead.

## User Setup Required
None.

## Next Phase Readiness
- V17-03 (CLI verbs) builds directly on this engine: claims_group + stake/check/release/extend/list, identity from VOSS_AGENT_ID, --json + advice arrays; turning test_claims_verbs/concurrent/ttl/advice GREEN means removing their xfail marks
- Source assertions for the summary gates: overlap functions contain no os.stat/listdir/open calls; active_claims/release_claims/extend_claim all filter or scope by expires_at/agent_id

---
*Phase: V17-external-agent-coordination-surface-claims-bus-verbs-as-prot*
*Completed: 2026-06-10*
