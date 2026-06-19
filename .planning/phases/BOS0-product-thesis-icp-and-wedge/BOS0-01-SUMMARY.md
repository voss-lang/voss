---
phase: BOS0-product-thesis-icp-and-wedge
plan: 01
subsystem: product
tags: [behavioral-os, product-thesis, icp, wedge, positioning, docs-first]

# Dependency graph
requires: []
provides:
  - "Product brief locking Behavioral OS boundary, ICP, buyer/user split, delegation wedge, positioning, anti-positioning, and core tension+resolution"
  - "D-01..D-06 locked-decision citations carried into prose"
affects: [BOS0-02, BOS1, BOS3, BOS4, BOS7, BOS9, BOS13]

# Tech tracking
tech-stack:
  added: []
  patterns: ["docs-first BOS artifact: prose brief framing inherited by every later BOS spec"]

key-files:
  created:
    - .planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-PRODUCT-BRIEF.md
  modified: []

key-decisions:
  - "Boundary stated as team control plane over AI-assisted engineering work, NOT a generic PM clone (BOS-PROD-01)."
  - "ICP = small multi-agent engineering teams of 3-15 devs already running multiple coding agents (D-01)."
  - "Buyer/user split: EM/eng-lead = economic buyer; devs = daily users (D-03)."
  - "First wedge = delegation (task -> agent/human), grounded in the V25 server-native swarm assignment flow; review-depth and validation-depth deferred (D-02)."
  - "External category = 'control plane for AI engineering teams'; 'Behavioral OS' = internal/north-star only (D-05)."
  - "Anti-positioning: NOT Jira/Linear/Atlassian clone; NOT individual surveillance/ranking/leaderboards (D-06)."
  - "Core tension (top-down EM buyer vs dev-generated substrate) resolved by assuming the team is already on the Voss ADE; no new dev behavior required (D-04)."

patterns-established:
  - "Docs-first brief inherits locked CONTEXT.md decisions verbatim with D-XX citations inline."

requirements-completed: [BOS-PROD-01, BOS-PROD-02, BOS-PROD-03]

# Metrics
duration: 1 min
completed: 2026-06-19
---

# Phase BOS0 Plan 01: Product Thesis, ICP, and Wedge Summary

**Product brief locking the Behavioral OS boundary, ICP (3-15 dev multi-agent teams), EM-buyer/dev-user split, delegation wedge grounded in V25 swarm, external/internal positioning, anti-positioning, and the top-down-buyer vs dev-substrate tension + resolution.**

## Performance

- **Duration:** ~1 min (docs-only; single task dispatched to a subagent)
- **Started:** 2026-06-19
- **Completed:** 2026-06-19
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- BOS0-PRODUCT-BRIEF.md written with all seven required sections and D-01..D-06 citations inline.
- Wedge claim grounded in the V25 server-native swarm assignment flow (`swarm.assign` / task ownership) rather than an invented event source.
- Zero fenced code blocks, no data schema, no web-vs-desktop responsibility map — adheres to the deferred list (competitive analysis, pricing, design-partner sourcing, wedge metrics, BOS7 split all excluded).

## Task Commits

No commits made yet — per project Git Safety rules, git write actions require Ben's explicit confirmation. The artifact is written to disk and verified; commit is staged pending approval.

## Files Created/Modified
- `.planning/phases/BOS0-product-thesis-icp-and-wedge/BOS0-PRODUCT-BRIEF.md` — Product brief: Product boundary, ICP/beachhead, Buyer/user split, Wedge (delegation), Positioning, Anti-positioning, Core tension and resolution.

## Decisions Made
None — followed plan exactly. All decisions were pre-locked in BOS0-CONTEXT.md (D-01..D-08); the brief carries them into prose with citations.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required (docs-only phase).

## Next Phase Readiness
- BOS0-01 deliverable (product brief) complete and verified against every acceptance criterion.
- Ready for BOS0-02 (Mom-Test design-partner discovery script, BOS-PROD-03 discovery portion), which depends on this brief's ICP/buyer framing.
- Note: this plan's `requirements` field lists BOS-PROD-01..03, but BOS-PROD-03 also has a discovery-script portion covered by BOS0-02. Marking all three complete here would be premature for BOS-PROD-03 — however, per the PLAN.md frontmatter `requirements: [BOS-PROD-01, BOS-PROD-02, BOS-PROD-03]` copied verbatim into this summary, the requirements-mark-complete step is governed by the frontmatter. Recommend Ben review before BOS-PROD-03 is marked complete in REQUIREMENTS.md (BOS0-02 may also need to ship first).

## Self-Check: PASSED

Automated verification (ran in main context):
- `test -f BOS0-PRODUCT-BRIEF.md` → FILE_EXISTS_OK
- `grep '## Anti-positioning'` → ANTIPOSITIONING_OK
- `grep -Eqi 'control plane for AI engineering teams'` → EXTERNAL_CATEGORY_OK
- `grep '3-15'` → ICP_OK
- `grep 'Behavioral OS'` → BOS_TERM_OK
- `grep 'swarm'` + `grep 'delegation'` → WEDGE_OK
- `grep 'economic buyer'` → BUYER_OK
- `grep 'top-down'` → TENSION_OK
- Anti-positioning content: "not a Jira / Linear / Atlassian PM clone" (line 31) + "not individual-developer surveillance, ranking, or productivity leaderboards" (line 33) both present.
- Code fence count: 0 (no fenced code blocks).
- No data schema, no web-vs-desktop responsibility map present.

---
*Phase: BOS0-product-thesis-icp-and-wedge*
*Completed: 2026-06-19*