# Requirement assessments eval (dev)

- commit: `c1a27046aef3096e460b1c24b59d8066e5c2f792`
- rubric: `review.requirements.v2`, threshold 0.8
- model: `jev-1.13.0`, location `Ben's Mac, local`
- false supported: 0/31 = 0.000 (Wilson 95% 0.000 to 0.110)
- contradicted recall: 13/14 = 0.929 (Wilson 95% 0.685 to 0.987)
- abstention: 17/48, coverage 0.646
- failed pairs: 0
- ambiguous pairs (excluded): 2
- calls: 21, answered 21
- cost: $0.0018 total, $0.0001 mean
- latency: p50 316 ms, p95 418 ms

## By kind

| kind | gold | shown | pairs |
| --- | --- | --- | --- |
| ambiguous | insufficient_evidence | abstained | 5 |
| contradicted | contradicted | abstained | 1 |
| contradicted | contradicted | contradicted | 7 |
| contradicted | supported | supported | 4 |
| failed_check | contradicted | contradicted | 2 |
| failed_check | supported | supported | 3 |
| missing_criterion | contradicted | contradicted | 2 |
| missing_criterion | insufficient_evidence | abstained | 5 |
| missing_criterion | insufficient_evidence | contradicted | 1 |
| missing_criterion | supported | supported | 4 |
| no_checks | contradicted | contradicted | 1 |
| no_checks | insufficient_evidence | abstained | 5 |
| skipped_check | contradicted | contradicted | 1 |
| skipped_check | insufficient_evidence | abstained | 1 |
| skipped_check | supported | supported | 2 |
| supported | supported | supported | 4 |
