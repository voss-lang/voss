# Requirement assessments: release report (withdrawn)

This report has been replaced by `evals/review-locked-2/reports/review-release.md`.

The locked run recorded here, on 2026-10-11 with rubric `review.requirements.v1`, gave Jev the pinned source as it was before each change, not the source after it. Live runs send the code after the change, so this result did not measure what ships. It reported 0/33 false supported, 3/15 contradictions caught, and 24% coverage.

After the code context was fixed, the dev half was rerun under rubric v2, and so was the used locked half. Both now count as development data (see `evals/review/README.md`). The release result comes from a fresh locked set, `evals/review-locked-2`, scored once.

`review-test.json` and `review-test/` keep the withdrawn run's raw output.
