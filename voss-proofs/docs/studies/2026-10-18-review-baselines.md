# Review baselines on the locked J4 set (2026-10-18)

This study compares four ways of deciding whether a change meets its requirements, on the locked J4 requirement-review set. No model was called. Every label comes from runs that finished before this study, and VossProofs re-scored none of them.

```sh
proofs import-review ../evals/review-locked-2 --split test --out results/review-locked-2
```

## Setup

- **Dataset.** `evals/review-locked-2`, test split. 21 synthetic changes to Voss at commit `c1a27046aef3`, 50 criterion pairs, rubric `review.requirements.v2`. The fixture hashes matched `freeze.json`.
- **Configs.**
  - *author-claim*: accept every change as its author presents it. This is the "agent judges its own work" baseline from H1.
  - *reject-all*: reject every change. It bounds what a false-accept rate alone can show.
  - *jev*: Jev requirement review (`jev-1.13.0`, threshold 0.8), from the locked run in `reports/review-test/`.
  - *reviewer-b*: the board's Reviewer B (`claude-sonnet-5-5`), from `reports/reviewer-b-baseline-test.json`.
- **Ground truth.** A change should be accepted only when every criterion's gold label is *supported*. 19 changes should be rejected and 2 should be accepted.

## Results

Change level. The intervals are Wilson 95%.

| config | false accept | true accept |
|---|---|---|
| author-claim | 19/19 = 100% (83.2–100) | 2/2 = 100% (34.2–100), underpowered |
| reject-all | 0/19 = 0% (0–16.8) | 0/2 = 0% (0–65.8), underpowered |
| jev | 0/19 = 0% (0–16.8) | 2/2 = 100% (34.2–100), underpowered |
| reviewer-b | 0/19 = 0% (0–16.8) | 2/2 = 100% (34.2–100), underpowered |

Criterion level. Reviewer B returns one verdict per change, so it has no row here.

| config | false supported | supported recall | contradicted recall | abstention | Brier |
|---|---|---|---|---|---|
| author-claim | 33/33 | 17/17 | 0/13 | 0/50 | n/a |
| reject-all | 0/33 | 0/17 | 0/13 | 50/50 | n/a |
| jev | 1/33 = 3.0% (0.5–15.3) | 17/17 = 100% (81.6–100) | 10/13 = 76.9% (49.7–91.8) | 18/50 = 36.0% | 0.0601 |

These Jev numbers match the locked report in `reports/review-test.json`. The Reviewer B change-level result matches `reports/review-compare.json`. A test checks both.

## Findings

- **H1, supported on this set.** Trusting the author accepts all 19 defective changes. Both independent reviewers accept none of them. The upper bound on either reviewer's false-accept rate is 16.8%.
- **The change-level comparison can't separate Jev from Reviewer B, or either one from reject-all on false accepts.** The set has only 2 changes where every requirement is met. On that axis, a reviewer that rejects everything looks perfect.
- **The criterion level does show Jev isn't rejecting everything.** It labels all 17 supported criteria as supported, with a lower bound of 81.6%, and it calls 1 of 33 unsupported criteria supported. The one miss sits in a change where other criteria were rejected, so it didn't produce a false accept.
- **H3 is not tested yet.** Jev gives categorical probabilities, so it has a Brier score. Reviewer B gives a self-reported confidence (mean 0.87), which is not a probability and isn't scored as one. A heuristic-confidence baseline on the same pairs doesn't exist yet.

## Limits

- Synthetic changes to one repository at one commit, labeled by the people who wrote them.
- One Jev model and one Reviewer B model. A single run each, so model run-to-run variance is not measured.
- Reviewer B's baseline file records no cost, so its cost is unknown (upstream gap 16).
- Change-level true accept has n=2. It needs at least 10 accept-worthy changes before it can carry a claim (upstream gap 17).

## Not run

The Jev judge on VossBench diffs (`oracle-jev`, `null-jev`, `voss-serve-auto-jev`) was implemented and tested with a stub `voss` binary. It wasn't run live, because no Jev key (`TYPESAFE_API_KEY`) was available. Its `oracle-jev` run adds 8 accept-worthy changes whose ground truth comes from hidden tests.
