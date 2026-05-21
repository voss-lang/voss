---
phase: O5-engineering-manager-loop
plan: 00
status: complete
completed_at: 2026-05-20
commits: []
depends_on: []
requirements: []
---

# O5-00 Summary — Substrate Gate (Wave 0)

## Objective

Verify that every interface O5's later waves depend on is either (a) shipped and import-stable in live code (O1/O2) or (b) frozen on paper in O3-SPEC / O4-CONTEXT with the exact shape O5-RESEARCH captured. No code written; this is a blocking acceptance gate.

## Files changed

None. Wave 0 is a checkpoint:human-verify gate producing only this summary artifact.

## What shipped

- Live-import probes confirmed O1 substrate (SessionTreeNode, SessionTreeManager, finalize_node, mutate_envelope, BudgetAllocationError, BudgetCapRaiseError) and O2 substrate (TeamConfig frozen+slots, gate_for_role, filter_toolset_for_role, compile_team, SubagentSpec, SubagentRegistry, run_subagent with node/reserve/gate kwargs).
- Paper-interface audit confirmed O3-SPEC Card shape (8 fields), 6 columns, ReviewerVerdict (6 fields), Reviewer Protocol, DeterministicReviewerStub, node.transitions, SessionTreeManager.get_node, and the Card-Ticket field gap.
- Paper-interface audit confirmed O4-CONTEXT Reviewer-A/B split and the ReviewerVerdict.domain_inferred cross-phase ask.
- Three coordination asks (C-01, C-02, C-03) and five landmines (L-01 through L-05) documented for downstream consumption.

## Test counts

| File | Tests |
|------|-------|
| (none) | 0 |
| **Total** | **0** |

## Key facts

- **EXIT_REASONS at gate time:** `{"done", "max-iter", "budget", "interrupt", "batch-invariant"}` -- "killed" not yet present (confirmed additive extension pending for W1); "timeout" not yet present (O3's responsibility).
- **Card-Ticket gap:** O3 Card lacks original_idea, domain, artifact_path, artifact_text, file_diff, a_verification_summary. O5 resolution: Ticket wrapper carrying EM-authored scaffolding alongside the Card reference.
- **Coordination asks:** C-01 (Reviewer.review signature), C-02 (ReviewerVerdict.domain_inferred), C-03 (EXIT_REASONS additive ordering).
- **Landmines:** L-01 (pydantic LENIENT for LLM output), L-02 (em.* kind namespace), L-03 (no L2 vocab in audit copy), L-04 (append-not-delete on kill/rescope), L-05 (read-from-registry, never construct SubagentSpec).

## Deviations from plan

None. The gate passed cleanly; all citations located.

## Next

W1 lands the EM data model (frozen-slots dataclasses + EXIT_REASONS "killed" extension).

EM_SUBSTRATE_READY
