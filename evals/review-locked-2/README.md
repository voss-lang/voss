# Requirement assessment locked set 2

A fresh locked set for rubric `review.requirements.v2`, after the first locked split in `evals/review/` was used. It follows the fixture format, kinds, and labeling rules in `evals/review/README.md`, at half the size: 21 fixtures, 50 pairs, 33 that should not be supported.

`corpus.json` sets `locked_only`, so `freeze` puts every fixture in the test split. The set is scored once:

```
python -m voss.eval.review run --root evals/review-locked-2 --split test --locked-final --location "<where>"
```

Development and threshold tuning use `evals/review/` only.
