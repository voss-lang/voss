---
phase: V20-edict-residue-hardening
plan: 05
type: execute
wave: 1
depends_on: []
files_modified:
  - voss/harness/board/gates.py
  - voss/harness/board/verdict.py
  - voss/harness/board/reviewer_b.py
  - voss/harness/board/reviewer_a.py
  - voss/harness/board/stub.py
  - tests/harness/board/test_done_gate_tier.py
autonomous: true
requirements: [VEDR-05]
must_haves:
  truths:
    - "Done gate invokes Reviewer-B with tier='strong' (spy-asserted in a board test); ReviewerVerdict.tier persisted in the review sidecar says 'strong' at Done"
    - "Reviewer Protocol widened with keyword-only tier defaulting 'fast'; stub + Reviewer-A accept it; stub-composed boards (team_run) still construct and pass gates"
    - "B's prompt gains a '## Repo Context' section sourced from a card attribute only — the card-attributes-only isolation guarantee (reviewer_b.py:108) is preserved, not bypassed"
  artifacts:
    - path: "tests/harness/board/test_done_gate_tier.py"
      provides: "RED-first: SpyReviewer records tier per call; Done → strong; intermediate conf gate unaffected"
      contains: "test_done_gate_uses_strong_tier"
  key_links:
    - from: "voss/harness/board/gates.py"
      to: "reviewer_b.review(card, tier='strong')"
      via: "b_passes.evaluate — b_passes exists only in _CODE/_AI_DONE_PREDICATES (gates.py:185-186), so strong-at-Done is safe to set here"
      pattern: "tier=\"strong\""
---

<objective>
CORRECTNESS BUG — ship as its own commits, independent of plans 01-04.

The strongest gate uses the weakest reviewer: b_passes calls
`ctx.reviewer_b.review(ctx.card)` with no tier (gates.py:130-133), so ReviewerB defaults
tier="fast" (reviewer_b.py:92-96) — directly contradicting the documented contract
"B.fast at intermediate gates; B.strong at ->Done" (verdict.py:21). Since b_passes appears
ONLY in the Done predicate tuples (gates.py:185-186, build_default :200-212), every →Done
review in production runs the fast model.

Secondary: B sees only original_idea/acceptance/artifact_text/file_diff/a_verification
(reviewer_b.py:108-118) — no repo source — so B cannot catch defects the diff introduces
into pre-existing code it can't see.
</objective>

<context>
- Protocol: verdict.py:49 `def review(self, card: object) -> ReviewerVerdict` — no tier.
  Impls: reviewer_b.py:92 (has tier kwarg), stub.py:24 and reviewer_a.py:137 (do NOT).
  team_run wires DeterministicReviewerStub as reviewer_b (harness/cli.py:4425-4430), so the
  Done gate calling `review(card, tier="strong")` would TypeError on stubs today — Protocol
  + both impls must be widened in the same commit as the gate change.
- Verdict snapshot/sidecar: machine.py:451 region persists verdict via _write_review_sidecar —
  ReviewerVerdict.tier field gives free observability that strong actually ran.
- Isolation guarantee: reviewer_b.py builds user_msg "from card attributes ONLY". Repo context
  must therefore ride ON the card (new defaulted attribute), populated upstream where the
  artifact/file_diff is assembled — B itself never touches the filesystem.
</context>

<tasks>

## Task 1 — RED tests (commit 1: `test(board): RED Done-gate strong tier + repo context`)
tests/harness/board/test_done_gate_tier.py (reuse board lifecycle fixtures):
1. `test_done_gate_uses_strong_tier` — SpyReviewer (records (card, tier) per call, returns
   pass) as reviewer_b; drive a card InReview→Done; assert last B call tier == "strong".
2. `test_intermediate_gate_reviewer_unaffected` — conf gate (InProgress→InReview) reviewer
   spy never receives tier="strong" (conf_meets_p uses ctx.reviewer, default path untouched).
3. `test_stub_reviewer_accepts_tier_kwarg` — DeterministicReviewerStub.review(card,
   tier="strong") does not raise and echoes its configured tier (team_run composition guard).
4. `test_reviewer_b_prompt_includes_repo_context` — card with repo_context set → user_msg
   contains "## Repo Context" + the text; absent/empty attr → section omitted (assert via
   provider fake capturing messages).

## Task 2 — Protocol widen + strong at Done (commit 2: `fix(board): Reviewer-B strong tier at Done gate`)
- verdict.py Protocol: `def review(self, card: object, *, tier: Literal["fast","strong"] =
  "fast") -> ReviewerVerdict: ...` (keyword-only, defaulted — zero-churn for callers).
- stub.py + reviewer_a.py: accept the kwarg. Stub keeps returning its configured verdict
  (decide: echo the passed tier in the returned verdict for observability — yes, do that,
  matches test 3). Reviewer-A ignores tier (A has no tiers).
- gates.py b_passes: `ctx.verdict_b = ctx.reviewer_b.review(ctx.card, tier="strong")` —
  justified by b_passes living only in Done tuples; leave a one-line comment citing
  verdict.py's tier contract.
- Run full board suite — verdict-snapshot sentinels may pin tier="fast"; update only with
  git-log evidence per stale-sentinel discipline.

## Task 3 — repo context field (commit 3: `feat(board): repo_context card field for Reviewer-B`)
- reviewer_b.py: read `getattr(card, "repo_context", "")`; when non-empty append
  `## Repo Context (current source of files touched by the diff)` section to user_msg.
- Locate where the worker artifact/file_diff lands on the card (artifact assembly in the
  dispatch/board flow) and populate repo_context there: for each file in the diff, current
  on-disk content capped (e.g. first ~200 lines/file, total cap ~8k chars — strong tier pays
  for it once per Done). Population is best-effort; missing files → skip.
- Cap constants module-level, named, tested with an oversized fixture.

## Task 4 — GREEN + suite
`.venv/bin/python -m pytest tests/harness/board -q` green; then full
`.venv/bin/python -m pytest tests/harness -q`.
</tasks>

<verification>
- Done gate invokes B with strong tier, asserted in board test (headline verify line).
- Stub-composed team_run path still passes gates (no Protocol TypeError).
- B can now see pre-existing source for touched files via card attribute, isolation intact.
</verification>
