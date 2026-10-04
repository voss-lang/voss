# Retrieval baseline

> Scope: metrics describe ranking of a fixed candidate pool, not complete user tasks.

## Dataset

- split: `dev`
- commit: `c1a27046aef3096e460b1c24b59d8066e5c2f792`
- queries: 120 in 100 groups (120 scored)

## Ranking metrics

| metric | value |
|--------|------:|
| baseline nDCG@5 | 0.4834 |
| baseline recall@5 (files) | 0.8056 |
| groups | 100 |
| queries | 120 |
| excluded (no positive labels) | 0 |

## Adversarial subset

- adversarial queries: 8

| metric | value |
|--------|------:|
| baseline nDCG@5 | 0.3667 |
| baseline recall@5 (files) | 0.5208 |
| groups | 8 |
| queries | 8 |
| excluded (no positive labels) | 0 |

## Ambiguous

- excluded from gate: 0

## Calibration

n/a: retrieval labels carry no probabilities

## Errors and fallbacks

no judgments

## Cost

no judgments

## Latency

no judgments

## Model and rubric

no judgments
