# V20 — Edict Residue Hardening: Context

**Source:** Audit of sibling project `edict` against the built Voss harness (2026-06-11).
Verdict: Voss already out-built edict on the hard parts (V4 session-tree spine, non-extendable
budget cages, V5 board double-gate, voss_md hash-fences, claims.py TTL ownership). This phase
ships ONLY the confirmed residue — five cheap, in-tree, low-risk items. No re-architecture.

**Requirements:** VEDR-01..05 (V-track phase — requirements live here, not REQUIREMENTS.md).

## Gap confirmations (verified against source 2026-06-11, branch dev @ 3850829)

Every cited gap re-confirmed on disk before planning. Line numbers current as of this commit.

### VEDR-01 — `sync --check` drift gate (Plan 01)
- CONFIRMED: `voss/sync.py:235` reads `recorded_hashes` from `sync-state.json` but uses it
  **only** for the prompt edit-guard at `voss/sync.py:303`. Managed docs loop
  (`voss/sync.py:254-267`) writes via `_diff_write` with **no** edit-guard — a hand-edited
  managed doc is silently clobbered by plain `voss sync`.
- CONFIRMED: `sync_cmd` (`voss/cli.py:491-523`) exposes only `--dry-run`/`--force`; `--dry-run`
  always exits 0. No CI-gate mode exists.

### VEDR-02 — Friction scoring (Plan 02)
- CONFIRMED: `RunRecorder.observe` captures `failures[]={tool,error}`
  (`voss/harness/recorder.py:241-243`) and `validation[]={cmd,exit,summary}`
  (`voss/harness/recorder.py:258-266`). Never scored.
- CONFIRMED: eval row (`voss/eval/runner.py:746-770`) has success/cost/tokens/confidence,
  no wasted-call field; `voss/eval/summary.py` aggregates pass-rate/mean-cost/correlation only.

### VEDR-03 — Worker mission brief (Plan 03)
- CONFIRMED: `agent_task` (`voss/harness/subagents.py:172-173`) injects only
  `role_prompt + task`. Workers blind to siblings.
- CONFIRMED: `claims.py` already knows scope ownership (`open_claims_db:149`,
  `active_claims:204`); `dispatch_card` (`voss/harness/em/handle.py:186`) has the ticket
  table + roster in hand at dispatch time.

### VEDR-04 — Critical-risk human escape hatch (Plan 04)
- CONFIRMED: `RiskTier = Literal["low","med","high"]` (`voss/harness/board/machine.py:52`),
  thresholds map 3 entries (`machine.py:60-64`). Risk routes ONLY the confidence threshold
  (`gates.py:92-104` conf_meets_p). Zero human-in-loop gate anywhere in gates.py.
- CONFIRMED: Blocked-terminal routing exists (`machine.py:451-466` _force_terminal path);
  human ack record pattern exists post-run (`voss/harness/cli.py:4355-4375` _write_signoff_ack).

### VEDR-05 — BUG: Reviewer-B runs fast tier at Done gate (Plan 05)
- CONFIRMED: `b_passes.evaluate` calls `ctx.reviewer_b.review(ctx.card)` with no `tier=`
  (`voss/harness/board/gates.py:130-133`) → `ReviewerB.review` defaults `tier="fast"`
  (`voss/harness/board/reviewer_b.py:92-96`). Contradicts the contract documented at
  `verdict.py:21` ("B.fast at intermediate gates; B.strong at ->Done").
- CONFIRMED: `b_passes` appears ONLY in the Done predicate tuples
  (`gates.py:185-186` _CODE/_AI_DONE_PREDICATES; `build_default` `gates.py:200-212`) —
  so hardcoding strong inside the Done path is safe; no intermediate gate uses B.
- CONFIRMED: B's user_msg is built from card attributes only (`reviewer_b.py:108-118`,
  deliberate isolation guarantee) with no repo-source field — B cannot see pre-existing code.
- WRINKLE found during confirmation: the `Reviewer` Protocol (`verdict.py:49`) and both
  other impls (`stub.py:24`, `reviewer_a.py:137`) define `review(card)` with **no tier
  kwarg**. Plan 05 must widen the Protocol (keyword-only, defaulted) and update both impls,
  or the Done gate's `tier="strong"` call breaks stub-composed boards (`team_run` wires
  DeterministicReviewerStub as reviewer_b, `harness/cli.py:4425-4430`).

## Plan map

| Plan | Item | Wave | Files (primary) |
|------|------|------|-----------------|
| 01 | sync --check drift gate + doc edit-guard | 1 | voss/sync.py, voss/cli.py |
| 02 | friction scoring reducer + eval column | 1 | voss/eval/friction.py (new), runner.py, summary.py |
| 03 | worker mission brief injection | 1 | voss/harness/subagents.py, em/handle.py |
| 04 | critical risk tier + human gate | 2 (after 05) | board/machine.py, board/gates.py, harness/cli.py |
| 05 | B strong-tier at Done + repo context (BUG) | 1 | board/gates.py, verdict.py, reviewer_b.py, stub.py, reviewer_a.py |

Plan 04 waits on 05 because both edit the Done predicate set in `gates.py` — 05 is a
correctness fix and must land as its own atomic commit first.

## Out of scope (deferred — see V20-DEFERRED-SCOPING.md)

Mid-task 429 failover on default path; board/EM crash-recovery rehydrate; coordination bus
verbs; gate-before-spend in EM loop; PTY stuck-detection. Each scoped one paragraph, no plan.
Operator promotes individually.
