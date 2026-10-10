# Code recall rerank (dev)

> Scope: metrics describe ranking of a fixed candidate pool, not complete user tasks.

## Dataset

- split: `dev`
- commit: `c1a27046aef3096e460b1c24b59d8066e5c2f792`
- queries: 120 in 100 groups (120 scored)

## Ranking metrics

| metric | value |
|--------|------:|
| baseline nDCG@5 | 0.4865 |
| candidate nDCG@5 | 0.6913 |
| mean nDCG@5 gain (per group) | 0.2047 |
| 95% CI lower | 0.1737 |
| 95% CI upper | 0.2363 |
| baseline recall@5 (files) | 0.8056 |
| candidate recall@5 (files) | 0.8847 |
| recall@5 difference | 0.0792 |
| wins | 111 |
| losses | 6 |
| ties | 3 |
| groups | 100 |
| queries | 120 |
| excluded (no positive labels) | 0 |

- gate: **PASS** (mean nDCG@5 gain >= 0.03, 95% CI lower bound > 0, recall@5 drop <= 0.0; B=10000, seed=20261003, alpha=0.05)

## Adversarial subset

- adversarial queries: 8

| metric | value |
|--------|------:|
| baseline nDCG@5 | 0.3667 |
| candidate nDCG@5 | 0.5685 |
| mean nDCG@5 gain (per group) | 0.2018 |
| 95% CI lower | 0.0860 |
| 95% CI upper | 0.3198 |
| baseline recall@5 (files) | 0.5208 |
| candidate recall@5 (files) | 0.7083 |
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

- observed: $0.0234
- held: $0.0000

## Latency

- p50: 447 ms
- p95: 733 ms

## Model and rubric

- model: `jev-1.13.0`
- rubric: `code_recall.rerank.v1`

## Shadow

- shadow serves the baseline order (nDCG@5 gain 0.0 by definition) and sends the same Jev requests as active

## Latency gate

- location: `Ben's Mac, home network`
- answered requests: 120 (need >= 100)
- p50: 447 ms
- p95: 733 ms (max 1000 ms, timeouts included)
- gate: **PASS**
