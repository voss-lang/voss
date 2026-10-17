# Requirement assessments: release report

Run on 2026-10-11 (UTC) against the frozen dataset (seed 20261010, pinned commit `c1a27046`). Model `jev-1.13.0`, rubric `review.requirements.v1`, threshold 0.80.

## Verdict

**Pass.** On the locked half, the false-supported point estimate is 0/33 = 0%, under the 5% bar frozen in `freeze.json`.

The pass is narrow. Jev never called an unmet requirement met, but it labeled only 12 of 50 locked pairs. It abstained on the other 38, and it caught 3 of 15 contradictions. Read the assessments as a cautious second opinion that is often silent, not as a reviewer.

## Locked results

50 locked pairs cannot prove a false-supported rate of 5% or less. The Wilson upper bound below is the honest ceiling.

| metric | value | Wilson 95% |
|---|---|---|
| False supported | 0/33 = 0.000 | 0.000 to 0.104 |
| Contradicted recall | 3/15 = 0.200 | 0.070 to 0.452 |
| Abstention | 38/50 = 0.76 (coverage 0.24) | |
| Failed calls | 0 of 21 | |
| Ambiguous pairs | 0 in the locked half | |
| Brier score of P(supported) | 0.104 | |

Both pairs marked ambiguous in Ben's label review (rv-020 AC-2 and rv-038 AC-2) fell in the dev half. Every rate excludes them.

All 3 contradictions Jev caught came from fixtures with a failed check, at P(contradicted) of 0.90 to 0.97. When the diff alone contradicted a criterion, Jev abstained. Two of those pairs leaned the wrong way: rv-009 AC-2 had P(supported)=0.72 and rv-030 AC-1 had 0.71. At a 0.70 cutoff both would have been false-supported labels, so the 0.80 cutoff is what kept this half clean.

| kind | gold | shown | pairs |
|---|---|---|---|
| ambiguous | insufficient_evidence | abstained | 6 |
| contradicted | contradicted | abstained | 8 |
| contradicted | supported | abstained | 1 |
| contradicted | supported | supported | 3 |
| failed_check | contradicted | contradicted | 3 |
| failed_check | supported | abstained | 2 |
| failed_check | supported | supported | 1 |
| missing_criterion | contradicted | abstained | 2 |
| missing_criterion | insufficient_evidence | abstained | 6 |
| missing_criterion | supported | abstained | 2 |
| missing_criterion | supported | supported | 2 |
| no_checks | contradicted | abstained | 2 |
| no_checks | insufficient_evidence | abstained | 4 |
| skipped_check | insufficient_evidence | abstained | 2 |
| skipped_check | supported | abstained | 1 |
| skipped_check | supported | supported | 1 |
| supported | supported | abstained | 2 |
| supported | supported | supported | 2 |

## Dev vs locked

| metric | dev | locked |
|---|---|---|
| False supported | 1/31 = 0.032 (0.006 to 0.162) | 0/33 = 0.000 (0.000 to 0.104) |
| Contradicted recall | 12/14 = 0.857 | 3/15 = 0.200 |
| Coverage | 0.562 | 0.240 |
| Brier score | 0.047 | 0.104 |

The dev miss was rv-038 AC-1, a vague criterion ("ambiguous" kind) that Jev labeled supported at 0.96. The drop in recall and coverage from dev to locked is large. With about 21 fixtures per half, much of it may come from which fixtures landed where. The locked numbers are the ones to quote.

## Cost and latency

- Locked run: 21 calls, all answered, $0.0016 total, $0.000076 mean per call.
- Latency: p50 327 ms, p95 431 ms.
- Request size: median 5,759 bytes, max 9,157 bytes.
- Model returned: `jev-1.13.0` on every call. Price checked on docs.typesafe.ai on 2026-10-10: $0.042 per million input tokens.
- Threshold 0.80, rubric `review.requirements.v1`.

## Reviewer B baseline (informational, not part of the release bar)

The real Reviewer B (`claude-sonnet-5-5`, Claude subscription auth) reviewed all 42 fixtures with no errors.

On the 19 locked fixtures that have a labeled missing or contradicted criterion:
- Reviewer B passed 0/19 (Wilson 95% 0.000 to 0.168). It failed or blocked every one.
- Jev labeled the bad criterion supported on 0/19 fixtures (same interval). At the pair level, Jev's false-supported rate was 0/33 (0.000 to 0.104).

Reviewer B passed only the 4 fixtures where every criterion is met, 2 in each half. So on these fixtures the real reviewer was as safe as Jev, and it gave a verdict on every fixture. Jev adds a per-requirement breakdown tied to an evidence packet, not extra catches.

## Where it runs live

- **Swarm candidates.** When a project opts in with `judgments.review: shadow`, each swarm candidate is assessed in the background after it is recorded. Its task goal is the criterion. Read the result with `voss judge review --swarm <id> --task <id> --saved`; that makes no request.
- **On demand.** `voss judge review` checks the working tree or a commit at any time.
- **Board Done hook.** Proven by hermetic tests only. It stays inactive in live runs until the board worker pipeline exists, which is deferred to its own phase.

## Disable path and guards

```
pytest tests/harness/board/test_review_shadow.py tests/harness/test_swarm_review_shadow.py \
  tests/harness/test_decision_review_guards.py tests/harness/test_judgments_review_mode.py \
  tests/harness/test_judge_review_cli.py tests/eval/test_review_dataset.py
147 passed in 19.40s
```

These cover:
- **Zero calls:** no request is made when review is off, judgments are not enabled, the key is missing, or `VOSS_JUDGMENTS=off` is set.
- **Identity:** swarm events, results and git state, and board transitions, match with review off and in shadow, including when Jev fails.
- **No approval path:** the guard that no assessment can build or change a Reviewer B verdict.
- **Frozen dataset:** the hashes are unchanged.

## Limits

- The board hook does not fire in live runs yet, because no worker runs and no card reaches Done. Once it does, live `voss board` runs use a placeholder Reviewer B that always passes. Assessments there will sit beside a placeholder reviewer, not a real one.
- Swarm candidates are judged against their task goal, which is often a single requirement. The locked evaluation used fixtures, not live swarm candidates.
- Reviewer A's note is context only and gives no check status.
- Fixture code context is the pinned pre-change source.
- One model and one rubric version were tested. Any rubric, threshold, or packet change needs a fresh locked split.
- There is no cumulative spend cap across cards.
- Only working-tree candidates can go stale.
- Coverage on the locked half was 24%. Most criteria get no label.
