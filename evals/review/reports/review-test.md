# Requirement assessments eval (test)

- commit: `c1a27046aef3096e460b1c24b59d8066e5c2f792`
- rubric: `review.requirements.v1`, threshold 0.8
- model: `jev-1.13.0`, location `Ben's Mac, local`
- false supported: 0/33 = 0.000 (Wilson 95% 0.000 to 0.104)
- contradicted recall: 3/15 = 0.200 (Wilson 95% 0.070 to 0.452)
- abstention: 38/50, coverage 0.240
- failed pairs: 0
- ambiguous pairs (excluded): 0
- calls: 21, answered 21
- cost: $0.0016 total, $0.0001 mean
- latency: p50 327 ms, p95 431 ms
- release bar (false supported <= 0.05, point estimate): **PASS**
- this many locked pairs cannot prove a rate at or below 5%; read the Wilson upper bound

## By kind

| kind | gold | shown | pairs |
| --- | --- | --- | --- |
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
