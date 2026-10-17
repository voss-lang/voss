# Requirement assessments eval (test)

- commit: `c1a27046aef3096e460b1c24b59d8066e5c2f792`
- rubric: `review.requirements.v2`, threshold 0.8
- model: `jev-1.13.0`, location `Ben's Mac, local`
- false supported: 1/33 = 0.030 (Wilson 95% 0.005 to 0.153)
- contradicted recall: 10/13 = 0.769 (Wilson 95% 0.497 to 0.918)
- abstention: 18/50, coverage 0.640
- failed pairs: 0
- ambiguous pairs (excluded): 0
- calls: 21, answered 21
- cost: $0.0021 total, $0.0001 mean
- latency: p50 304 ms, p95 498 ms
- release bar (false supported <= 0.05, point estimate): **PASS**
- this many locked pairs cannot prove a rate at or below 5%; read the Wilson upper bound

## By kind

| kind | gold | shown | pairs |
| --- | --- | --- | --- |
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
