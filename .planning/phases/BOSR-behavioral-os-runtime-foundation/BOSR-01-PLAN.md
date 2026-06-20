# BOSR-01 Plan: Phase Reset and Contract Reconciliation

**Status:** Executed 2026-06-20
**Wave:** 0
**Type:** docs reconciliation
**Requirements:** BOSR-01

## Objective

Collapse the active BOS0-BOS18/BOSI1-BOSI6 split into one BOSR phase while
preserving all useful source knowledge.

## Scope

Modify:
- `.planning/ROADMAP.md`
- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`
- `.planning/phases/BOSR-behavioral-os-runtime-foundation/*`

Do not modify:
- runtime source code
- old BOS source artifacts
- git history or branches

## Acceptance Criteria

1. ROADMAP has one active BOSR row instead of active BOS0-BOS18/BOSI rows.
2. PROJECT says BOSR is the current milestone.
3. REQUIREMENTS has BOSR execution requirements and keeps old BOS requirements
   as source material.
4. STATE points current position at BOSR.
5. BOSR has discussion, context, research, and plan artifacts.

## Verification

```bash
rg -n "BOSR|BOSI|BOS0-BOS18|docs-first" .planning/PROJECT.md \
  .planning/ROADMAP.md .planning/REQUIREMENTS.md .planning/STATE.md
test -f .planning/phases/BOSR-behavioral-os-runtime-foundation/BOSR-CONTEXT.md
test -f .planning/phases/BOSR-behavioral-os-runtime-foundation/BOSR-RESEARCH.md
```
