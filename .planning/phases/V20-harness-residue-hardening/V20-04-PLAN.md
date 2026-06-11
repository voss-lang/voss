---
phase: V20-harness-residue-hardening
plan: 04
type: execute
wave: 2
depends_on: ["05"]
files_modified:
  - voss/harness/board/machine.py
  - voss/harness/board/gates.py
  - voss/harness/cli.py
  - tests/harness/board/test_critical_tier.py
autonomous: true
requirements: [VRES-04]
must_haves:
  truths:
    - "A critical-tier card with all-pass A/B reviewers CANNOT reach Done — gate refuses with failing clause 'human' until an explicit human approval record exists"
    - "After the operator approval record is written, the same card passes →Done; an explicit rejection routes it terminal Blocked with reason pending_human_rejected"
    - "low/med/high tiers are behaviorally untouched — full board suite green with zero non-critical test edits"
  artifacts:
    - path: "voss/harness/board/machine.py"
      provides: "RiskTier += 'critical'; thresholds entry; pending-human surfaced in snapshot/deltas"
      contains: "critical"
    - path: "voss/harness/board/gates.py"
      provides: "human_approved Done-predicate sibling, active only for critical tier"
      contains: "human_approved"
    - path: "voss/harness/cli.py"
      provides: "operator approve/reject verb writing the approval record (reuses _write_signoff_ack pattern)"
      contains: "approve"
  key_links:
    - from: "voss/harness/board/gates.py"
      to: "approval record on disk / card attribute"
      via: "human_approved.evaluate — True only for non-critical tiers or explicit approval; NO agent verdict can satisfy it"
      pattern: "human_approved"
---

<objective>
Add the human escape hatch the harness completely lacks. RiskTier is low|med|high
(machine.py:52) and risk routes ONLY the confidence threshold (gates.py conf_meets_p:92-104) —
there is zero human-in-loop anywhere in the gate registry. A card flagged "this could delete
prod data" is cleared by the same machinery as a typo fix, just with conf 0.95 instead of 0.80.

Add a `critical` tier whose Done gate carries a predicate NO agent verdict can clear; the card
parks pending-human and only an explicit operator approve/reject record moves it.

Wave 2: depends on Plan 05, which rewrites the Done predicate call into reviewer_b in
gates.py — this plan adds a sibling predicate to those same tuples.
</objective>

<context>
- RiskTier: machine.py:52; _DEFAULT_RISK_THRESHOLDS machine.py:60-64 (critical needs an entry —
  conf_meets_p indexes the dict at the intermediate gate and must not KeyError; use 0.99).
- Done tuples: gates.py:185-186 (_CODE/_AI), build_default:200-212. Predicate pattern: tiny
  frozen classes with name + evaluate(ctx).
- Terminal routing precedent: B-block→Blocked terminal in Board.move (machine.py:451-466
  _force_terminal). Pending-human must NOT be terminal — it must be resumable, so model it as
  gate-refusal (card stays InReview) + surfaced state, not _force_terminal.
- Retry interaction: retry_under_ceiling / refusal counting in Board.move — a critical card
  waiting for a human must NOT burn retries to retry_ceiling and get force-terminated.
  Inspect the refusal path; if gate refusals increment retry_count, exempt the case where
  'human' is the only failing clause (decide exact mechanism while reading Board.move; this
  is the one open design point — pick minimal, test it).
- Human record precedent: _write_signoff_ack voss/harness/cli.py:4355-4375 (sidecar JSON +
  explicit prompt). Risk tier comes in via ticket risk_tier (handle.py create path) — find
  where cards get risk_tier to allow "critical".
</context>

<tasks>

## Task 1 — RED tests (commit 1: `test(board): RED critical-tier human gate`)
tests/harness/board/test_critical_tier.py:
1. `test_critical_card_blocked_without_human` — critical card, all-pass A/B stubs, attempt
   InReview→Done → BoardGateError with 'human' in failing_clauses; card NOT Done.
2. `test_critical_card_passes_after_approval` — write approval record (via the new API, not
   hand-rolled JSON) → same move succeeds.
3. `test_critical_rejection_routes_blocked` — rejection record → card routes terminal Blocked,
   delta reason pending_human_rejected.
4. `test_noncritical_tiers_unaffected` — low/med/high cards never evaluate human gate
   (spy or clause-name assertion).
5. `test_critical_pending_does_not_burn_retries` — repeated Done attempts while pending do not
   advance the card toward retry_ceiling force-termination.
6. `test_critical_threshold_entry_exists` — conf_meets_p on a critical card at the
   intermediate gate works (0.99) — no KeyError.

## Task 2 — tier + predicate (commit 2: `feat(board): critical risk tier + human_approved gate`)
- machine.py: RiskTier Literal += "critical"; thresholds["critical"]=0.99.
- gates.py: `human_approved` predicate (name="human"): non-critical → True; critical → True
  only when an approval record exists (ctx-accessible: simplest is a card/artifact attribute
  hydrated by Board from a `.voss/sessions/<run>/approvals/<card_id>.json` sidecar — keep the
  read in Board/ctx assembly, predicate stays pure). Append to both Done tuples FIRST
  (cheap→expensive ordering holds: a pending card refuses before paying A/B reviews — this
  also implements gate-before-spend for the critical case).
- Board.move: retry-exemption when failing == ["human"] (per Task 1.5); rejection record →
  _force_terminal(reason="pending_human_rejected").

## Task 3 — operator surface (commit 3: `feat(cli): card approve/reject for critical tier`)
- harness/cli.py: `voss team approve <card_id>` / `--reject` (single command, flag) under
  team_group — writes the approval/rejection sidecar (reuse _write_signoff_ack JSON style:
  ts, card_id, decision, operator note). Echo resulting state.
- Surface pending-human in the existing board snapshot/status output (one marker, e.g.
  `[PENDING HUMAN]` next to the card) so the operator can find what's waiting.

## Task 4 — GREEN + suite
`.venv/bin/python -m pytest tests/harness/board -q` then full tests/harness. Zero edits to
non-critical board tests permitted (truth 3).
</tasks>

<verification>
- Critical card cannot reach Done without explicit human action (headline verify line);
  approval unlocks, rejection terminal-blocks, retries not burned while pending.
</verification>
