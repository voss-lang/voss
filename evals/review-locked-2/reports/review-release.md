# Requirement assessments: release report

Run on 2026-10-17 against the second locked set, frozen before the run (commit `9b6202ec`). Pinned source commit `c1a27046`, model `jev-1.13.0`, rubric `review.requirements.v2`, threshold 0.80.

## Verdict

**Pass.** Jev called an unmet requirement met in 1 of 33 locked pairs, 3.0%. That is under the 5% bar in `freeze.json`.

The pass is narrow. The 95% interval reaches 15.3%, so 33 pairs cannot show the true rate is under 5%. Jev labeled 64% of requirements and abstained on the rest. Read the assessments as a second opinion that is often unclear, not as a reviewer.

## Why there is a second locked set

The first locked run gave Jev the pinned source as it was before each change. Live runs send the code after the change, so that run measured the wrong input. Its report is withdrawn (`evals/review/reports/review-release.md`).

Two fixes followed, both tuned on development data only:
- The eval and the Reviewer B baseline now get the code after the change, the same as live runs.
- Rubric v2 says a requirement counts as met only if it is specific enough to check. Under v1, Jev called two vague requirements met.

The first locked half had already been seen, so this set is new: 21 fixtures and 50 pairs with the same kinds and labeling rules. Claude drafted the labels, and Ben reviewed the five flagged pairs before the freeze. All 50 pairs are in the test split, and the set was scored once.

## Locked results

| metric | value | Wilson 95% |
|---|---|---|
| False supported | 1/33 = 0.030 | 0.005 to 0.153 |
| Contradicted recall | 10/13 = 0.769 | 0.497 to 0.918 |
| Abstention | 18/50 = 0.36 (coverage 0.64) | |
| Failed calls | 0 of 21 | |
| Ambiguous pairs | 0 | |
| Brier score of P(supported) | 0.060 | |

The one false supported is rv-057 AC-1, at P(supported)=0.84. The requirement says `voss chat` falls back to plain mode without textual installed. The diff makes the textual check return False on any exception, but nothing was run, and the caller is not in the diff. Ben first labeled this pair supported. It went back to insufficient because the `no_checks` kind requires no supported labels. It is counted as a miss.

All 17 supported pairs were labeled supported. Three contradictions were missed by abstaining, one each in the contradicted, failed-check, and missing-criterion kinds. Four pairs whose gold is insufficient were labeled contradicted. That is stricter than the gold label and does not count toward false supported.

| kind | gold | shown | pairs |
|---|---|---|---|
| ambiguous | insufficient_evidence | abstained | 6 |
| contradicted | contradicted | abstained | 1 |
| contradicted | contradicted | contradicted | 7 |
| contradicted | supported | supported | 4 |
| failed_check | contradicted | abstained | 1 |
| failed_check | contradicted | contradicted | 2 |
| failed_check | supported | supported | 3 |
| missing_criterion | contradicted | abstained | 1 |
| missing_criterion | insufficient_evidence | abstained | 4 |
| missing_criterion | insufficient_evidence | contradicted | 3 |
| missing_criterion | supported | supported | 4 |
| no_checks | contradicted | contradicted | 1 |
| no_checks | insufficient_evidence | abstained | 3 |
| no_checks | insufficient_evidence | contradicted | 1 |
| no_checks | insufficient_evidence | supported | 1 |
| skipped_check | insufficient_evidence | abstained | 2 |
| skipped_check | supported | supported | 2 |
| supported | supported | supported | 4 |

## Development data vs locked

All three runs use the code after the change, rubric v2, and threshold 0.80.

| metric | dev | used first locked half | locked set 2 |
|---|---|---|---|
| False supported | 0/31 | 0/33 | 1/33 = 0.030 |
| Contradicted recall | 13/14 = 0.929 | 13/15 = 0.867 | 10/13 = 0.769 |
| Coverage | 0.646 | 0.60 | 0.64 |
| Brier score | 0.032 | | 0.060 |

The used first locked half is diagnostic only, because its fixtures had been seen. Coverage held steady from development to locked. Recall dropped, and one miss appeared on new fixtures, which is why the locked numbers are the ones to quote.

## Cost and latency

- Locked run: 21 calls, all answered, $0.0021 total, $0.000098 mean per call.
- Latency: p50 304 ms, p95 498 ms.
- Request size: median 7,938 bytes, max 10,435 bytes.
- Model returned: `jev-1.13.0` on every call.

## Reviewer B baseline (informational, not part of the release bar)

The real Reviewer B (`claude-sonnet-5-5`, Claude subscription auth) reviewed all 21 fixtures with no errors.

On the 19 fixtures that have a labeled missing or contradicted requirement:
- Reviewer B passed 0/19 (Wilson 95% 0.000 to 0.168). It failed or blocked every one.
- Jev labeled the bad requirement supported on 1/19 fixtures (0.009 to 0.246), the rv-057 pair above.

Reviewer B passed both fixtures where every requirement is met. On this set, the real reviewer was at least as safe as Jev and gave a verdict on every fixture. Jev adds a per-requirement breakdown tied to an evidence packet, not extra catches.

## Limits

- 33 locked negatives cannot prove a rate of 5% or less. The Wilson upper bound, 15.3%, is the honest ceiling.
- One model, one rubric version, and one threshold were tested. Any change to them or to the evidence packet needs a fresh locked set.
- The board hook does not fire in live runs yet. Once it does, it sends Jev no code, because nothing fills a card's code context. It also sits beside a placeholder Reviewer B that always passes.
- Swarm candidates are judged against their task goal, which is often a single requirement. The locked evaluation used fixtures, not live swarm candidates.
- There is no cumulative spend cap across cards.
