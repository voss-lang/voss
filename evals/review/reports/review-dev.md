# Requirement assessments eval (dev)

- commit: `c1a27046aef3096e460b1c24b59d8066e5c2f792`
- rubric: `review.requirements.v1`, threshold 0.8
- model: `jev-1.13.0`, location `Ben's Mac, local`
- false supported: 1/31 = 0.032 (Wilson 95% 0.006 to 0.162)
- contradicted recall: 12/14 = 0.857 (Wilson 95% 0.601 to 0.960)
- abstention: 21/48, coverage 0.562
- failed pairs: 0
- ambiguous pairs (excluded): 2
- calls: 21, answered 21
- cost: $0.0017 total, $0.0001 mean
- latency: p50 308 ms, p95 414 ms

## By kind

| kind | gold | shown | pairs |
| --- | --- | --- | --- |
| ambiguous | insufficient_evidence | abstained | 4 |
| ambiguous | insufficient_evidence | supported | 1 |
| contradicted | contradicted | abstained | 1 |
| contradicted | contradicted | contradicted | 7 |
| contradicted | supported | supported | 4 |
| failed_check | contradicted | contradicted | 2 |
| failed_check | supported | supported | 3 |
| missing_criterion | contradicted | abstained | 1 |
| missing_criterion | contradicted | contradicted | 1 |
| missing_criterion | insufficient_evidence | abstained | 5 |
| missing_criterion | insufficient_evidence | contradicted | 1 |
| missing_criterion | supported | abstained | 2 |
| missing_criterion | supported | supported | 2 |
| no_checks | contradicted | contradicted | 1 |
| no_checks | insufficient_evidence | abstained | 5 |
| skipped_check | contradicted | contradicted | 1 |
| skipped_check | insufficient_evidence | abstained | 1 |
| skipped_check | supported | abstained | 1 |
| skipped_check | supported | supported | 1 |
| supported | supported | abstained | 1 |
| supported | supported | supported | 3 |
