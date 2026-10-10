# Retrieval labels to review

| batch | rows | graded | flagged | ambiguous queries |
|---|---|---|---|---|
| 01 | 983 | 983 | 0 | 0 |
| 02 | 1075 | 1075 | 0 | 0 |
| 03 | 1072 | 1072 | 0 | 0 |
| 04 | 1167 | 1167 | 0 | 0 |

No rows need review.

## Reviewed rows (accepted as graded)

These 16 rows were flagged during labeling. Ben waived the per-row review and accepted each one at its proposed grade. Each row now has `flag=reviewed`; `grade` and `confidence=low` are unchanged.

| batch | query | chunk | grade |
|---|---|---|---|
| 01 | b01-g001-q1 | `code:voss/harness/memory_gateway.py:009` | contextual |
| 01 | b01-g004-q1 | `code:voss/harness/cognition.py:033` | contextual |
| 01 | b01-g021-q1 | `code:tui/toolcard_test.go:010` | contextual |
| 01 | b01-g029-q1 | `code:voss/harness/memory_store.py:024` | contextual |
| 01 | b01-g050-q1 | `code:voss/harness/agent.py:043` | contextual |
| 02 | b02-g004-q1 | `code:voss/harness/cli.py:163` | contextual |
| 02 | b02-g011-q2 | `code:voss/harness/cognition_schemas.py:011` | contextual |
| 02 | b02-g012-q1 | `code:voss/harness/team.py:018` | directly_useful |
| 02 | b02-g013-q1 | `code:voss/harness/tools.py:032` | contextual |
| 02 | b02-g029-q1 | `code:voss/harness/server/app.py:011` | contextual |
| 03 | b03-g024-q1 | `code:voss_runtime/agent.py:001` | directly_useful |
| 03 | b03-g029-q2 | `code:voss_runtime/context.py:007` | directly_useful |
| 03 | b03-g048-q1 | `code:voss/harness/cli.py:026` | directly_useful |
| 04 | b04-g011-q1 | `code:voss/harness/em/loop.py:000` | directly_useful |
| 04 | b04-g027-q1 | `code:voss/harness/cli.py:335` | contextual |
| 04 | b04-g034-q1 | `code:voss/eval/runner.py:009` | directly_useful |

## Metric decisions to confirm

Flagged rows: 16 in total (batch 01: 5, batch 02: 5, batch 03: 3, batch 04: 3). Estimated review time is about 1 minute per flagged row, so about 16 minutes.

All seven defaults were confirmed as written; none were changed. These are frozen by J2-15 together with the locked split.

- [x] 1. nDCG@5 uses gain 2^g-1, discount 1/log2(rank+1), and IDCG over all labeled chunks of the query, including gold extras outside the pool. Consequence: a missed `necessary` chunk costs much more than a missed `contextual` one, and pools that miss gold chunks cannot reach nDCG 1.0.
- [x] 2. Relevant-file recall@5 counts files that own a chunk graded `directly_useful` or `necessary`, macro-averaged over queries. Consequence: `contextual` chunks never count as relevant files, and every query weighs the same regardless of how many relevant files it has.
- [x] 3. Paired percentile bootstrap, B=10,000, seed 20261003, resampling whole groups. Consequence: paraphrase variants move together, so the interval is not narrowed by near-duplicate queries, and reruns give identical bounds.
- [x] 4. J3 gate: mean nDCG@5 gain >= 0.03 AND bootstrap lower bound > 0 AND recall@5 difference >= 0. Consequence: a reranker must improve ranking by a clear margin and must not lose relevant files from the top 5.
- [x] 5. Pinned corpus commit c1a27046aef3096e460b1c24b59d8066e5c2f792; pool = top 15 of the production BM25+vector ranking with the golden test file excluded. Consequence: labels never drift with new code, and a reranker can only reorder these 15 candidates (gold extras outside the pool stay unreachable).
- [x] 6. Adversarial groups count in the gate and are also reported separately; ambiguous queries are excluded from the gate and listed. Consequence: lexical-bait robustness is part of the pass bar, and unclear queries cannot swing the result.
- [x] 7. Split: 200 groups split 100/100 by seeded shuffle within kind (seed 20261003). "Reading the locked split" means parsing test-split labels or computing any metric on test queries. Reading queries.jsonl split metadata and hashing files is allowed, and so is the one-time structural check (ids, vocabulary, coverage; no metric) inside `freeze`. Consequence: dev and test have the same mix of concept, symbol, and adversarial groups, and test labels stay unseen until J3's single locked-final run.

## Approval

- Approved by Ben on 2026-10-03.
- Flagged-row review waived: all 16 flagged rows are accepted as graded.
- All 7 metric defaults are accepted as written, with no edits. J2-15 applies them unchanged.
- No label grades were changed. The only label edit is `flag` moving from `review` to `reviewed` on the 16 accepted rows.
