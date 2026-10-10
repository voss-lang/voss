# Code recall rerank (test)

> Scope: metrics describe ranking of a fixed candidate pool, not complete user tasks.

## Dataset

- split: `test`
- commit: `c1a27046aef3096e460b1c24b59d8066e5c2f792`
- queries: 120 in 100 groups (120 scored)

## Ranking metrics

| metric | value |
|--------|------:|
| baseline nDCG@5 | 0.4623 |
| candidate nDCG@5 | 0.6995 |
| mean nDCG@5 gain (per group) | 0.2372 |
| 95% CI lower | 0.2018 |
| 95% CI upper | 0.2736 |
| baseline recall@5 (files) | 0.8083 |
| candidate recall@5 (files) | 0.8632 |
| recall@5 difference | 0.0549 |
| wins | 106 |
| losses | 9 |
| ties | 5 |
| groups | 100 |
| queries | 120 |
| excluded (no positive labels) | 0 |

- gate: **PASS** (mean nDCG@5 gain >= 0.03, 95% CI lower bound > 0, recall@5 drop <= 0.0; B=10000, seed=20261003, alpha=0.05)

## Adversarial subset

- adversarial queries: 8

| metric | value |
|--------|------:|
| baseline nDCG@5 | 0.4756 |
| candidate nDCG@5 | 0.7250 |
| mean nDCG@5 gain (per group) | 0.2494 |
| 95% CI lower | 0.1358 |
| 95% CI upper | 0.3663 |
| baseline recall@5 (files) | 0.7500 |
| candidate recall@5 (files) | 0.9375 |
| recall@5 difference | 0.1875 |
| wins | 7 |
| losses | 0 |
| ties | 1 |
| groups | 8 |
| queries | 8 |
| excluded (no positive labels) | 0 |

## Ambiguous

- excluded from gate: 0

## Calibration

n/a: retrieval labels carry no probabilities

## Errors and fallbacks

- status answered: 120

## Cost

- observed: $0.0236
- held: $0.0000

## Latency

- p50: 450 ms
- p95: 684 ms

## Model and rubric

- model: `jev-1.13.0`
- rubric: `code_recall.rerank.v1`

## Shadow

- shadow serves the baseline order (nDCG@5 gain 0.0 by definition) and sends the same Jev requests as active

## Latency gate

- location: `Ben's Mac, home network`
- answered requests: 120 (need >= 100)
- p50: 450 ms
- p95: 684 ms (max 1000 ms, timeouts included)
- gate: **PASS**
