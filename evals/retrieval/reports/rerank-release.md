# Code recall rerank release report

Run on 2026-10-04 (UTC 2026-10-05) from Ben's Mac on a home network. Jev model `jev-1.13.0`, rubric `code_recall.rerank.v1`, corpus pinned at `c1a27046`.

## Verdict

**Active allowed.** Every release gate passed on the locked test split and the task suite.

| Gate | Needed | Result | |
|---|---|---|---|
| Ranking quality | mean nDCG@5 gain ≥ 0.03, 95% CI lower bound > 0, no recall@5 drop | +0.237, CI [+0.202, +0.274], recall +0.055 | pass |
| Latency | ≥ 100 answered requests, p95 ≤ 1000 ms | 120 answered, p95 684 ms | pass |
| Task impact | no reproducible regression on the 30-task suite | 0 regressions, 0 unconfirmed | pass |

Activation is still a per-project choice through `voss judge activate code_recall`.

## Ranking

Locked test split: 100 groups, 120 queries, scored once.

| | baseline (= shadow) | active |
|---|---|---|
| nDCG@5 | 0.462 | 0.700 |
| file recall@5 | 0.808 | 0.863 |

- Mean nDCG@5 gain +0.237, 95% paired bootstrap interval [+0.202, +0.274].
- Wins / losses / ties: 106 / 9 / 5.
- Adversarial subset (8 queries): nDCG@5 0.476 to 0.725, file recall 0.750 to 0.938, 7 wins.
- Shadow mode shows the baseline order, so its gain is 0 by definition. It sends the same requests as active.
- The dev split, scored before the locked run, showed a gain of +0.205 (CI [+0.174, +0.236]).

These numbers describe the ranking of a fixed 15-chunk pool, not complete coding tasks.

## Latency

- 120 of 120 requests answered, no fallbacks, no trimmed requests.
- p50 450 ms, p95 684 ms, measured from one machine on one home network.
- Request size median 15,262 bytes, max 17,694 bytes (cap 24,000).
- Observed cost $0.024 for the 120 requests.

## Task impact

30 tasks on the pinned corpus: 15 that ask where something is in the code, and 15 small edits checked by a hidden test. Both sides used `claude-sonnet-5-5` through the Claude subscription, a 30-turn cap, and a code index built before each task.

| | off | active |
|---|---|---|
| pass rate | 29/30 (0.967) | 29/30 (0.967) |
| Jev receipts | 0 | 37 |

- Difference (active − off) +0.000, 95% interval [−0.100, +0.100].
- Passed only with off: `30-split-long-line`. Passed only with active: `05-background-watchdog`. Both tasks passed on both sides when rerun, so neither is a reproducible difference.
- The off side passed 29 of 30 tasks, so this suite had little room to show an improvement. It shows no regression, not a gain.

A 30-task pilot cannot establish general non-regression.

## Surfaces and disable path

- `voss do`, both `voss chat` paths, `voss serve` sessions, and the `code_recall` tool produce the same order and the same injected text for the same pool and Jev answers (`tests/code_recall/test_rerank_parity.py`).
- Swarm builder sessions keep their owned-file recall and make no Jev calls.
- With `VOSS_JUDGMENTS=off`, with `judgments.code_recall: off`, or with no key, every path shows today's output and makes zero Jev calls.
- Release check run on 2026-10-04: `pytest tests/code_recall/test_rerank_parity.py tests/harness/test_code_recall_mode.py tests/harness/server/test_rerank_server.py tests/eval/test_retrieval_dataset.py` gave 36 passed. Both new modules import from the package.

## Limits

- Today's top 5 and the pool's top 5 differ on 56 of 120 dev queries. Off and shadow show today's top 5; only an answered active rerank shows the pool order.
- `voss do` injects nothing on its first turn because the code index is still building. Reranking acts on `code_recall` tool calls and on later chat and server turns.
- The vector search returns slightly different results between runs, so live pools are not exactly reproducible. The ranking eval used the stored pools.
- Shadow mode sends the same task text and code chunks to Jev as active mode.
- A turn that ends with the model asking a clarifying question returns no run record. Its Jev spend is then missing from the `voss do` and server run records; chat still records it in `judgments.json`.
- With the default limits, a turn absorbs three timed-out calls before the $0.01 per-turn cap refuses the next one.
- Tested only with `jev-1.13.0` and rubric `code_recall.rerank.v1`. A model, rubric, candidate-pool, or threshold change needs a fresh locked comparison.
