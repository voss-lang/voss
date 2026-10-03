# Retrieval evaluation dataset

This dataset is the J3 retrieval baseline. J3 may only ship a reranker if it beats the stored baseline ranking on this data.

## Corpus scope

The corpus is the Voss repository at the single commit pinned in `corpus.json` (`c1a27046aef3096e460b1c24b59d8066e5c2f792`, on `origin/master`). Labels are keyed to that commit, so they do not drift when the code changes.

The dataset contains no other repositories, no personal session histories, no production data, and no clinical data.

`tests/code_recall/test_golden_queries.py` is excluded from every pool because it contains the seed query strings verbatim and would match itself.

## Files

| File | Written by | Contents |
|---|---|---|
| `corpus.json` | hand | repo, pinned commit, pool size, excluded paths, embedding model, chunker, rubric |
| `queries/batch-NN.jsonl` | Claude | one query per line: `{"id": "bNN-gNNN-qN", "group": "bNN-gNNN", "batch": "NN", "text", "kind": "concept"\|"symbol"\|"adversarial", "synthetic": bool, "seed": bool, "split": ""\|"dev"\|"test", "note"}` |
| `baseline/batch-NN.jsonl` | `baseline` | one row per query: `{"query_id", "embedding_model", "pool": [{"rank", "chunk_id", "path", "line_start", "line_end", "text_sha", "score"}], "bm25": [chunk_id, ...]}`. Do not hand-edit. |
| `labels/batch-NN.csv` | `baseline`, `grade`, Ben | `query_id,chunk_id,path,line_start,line_end,text_sha,source,grade,confidence,flag,note` |
| `REVIEW.md` | `review` | flagged rows for Ben, plus per-batch counts |

Label columns:

- `source`: `pool` for a chunk from the stored baseline pool, `gold` for a chunk added by hand from outside the pool.
- `grade`: empty (not graded yet), or one of the rubric levels below.
- `confidence`: empty, `high`, or `low`.
- `flag`: `none`, `review`, `reviewed`, or `ambiguous`.
- `text_sha`: the first 12 hex characters of the SHA-256 of the chunk text at the pinned commit. `check` rejects any row whose chunk text changed.

A query `group` is the split unit. Paraphrases and same-task variants share a group, and every query in a group has the same split.

## Rubric

| Grade | Digit | Meaning |
|---|---|---|
| `necessary` | 3 | Must be read to answer or implement the query. |
| `directly_useful` | 2 | Implements or directly supports part of the answer: a key helper, caller, or type. |
| `contextual` | 1 | Related background that helps orient, but is not needed. |
| `irrelevant` | 0 | Unrelated, or only overlaps lexically. |

Unlabeled chunks count as `irrelevant`. A file is relevant for recall@5 when it owns at least one chunk graded `directly_useful` or higher.

### Flagging rule

Add a `?` to a grade digit (which records `confidence=low`, `flag=review`) only when, after reading the full chunk, you are undecided across a boundary that matters:

- `contextual` vs `directly_useful`, or
- `directly_useful` vs `necessary` for a top-ranked chunk.

Aim for at most 1.5 flagged rows per group on average.

### Ambiguity rule

A query with more than one reasonable interpretation is marked ambiguous (`grade --ambiguous` sets `flag=ambiguous` on all of its rows). Ambiguous queries are reported separately and excluded from the J3 gate.

## Commands

Run from the repository root with `python -m voss.eval.retrieval <command>`.

| Command | What it does |
|---|---|
| `baseline --batch NN [--force]` | Materializes the pinned commit with `git archive` into a temp cache, ranks each query with the production BM25+vector `CodeIndex` and the local embedding model (no user config, no enrichment), writes `baseline/batch-NN.jsonl`, and appends a `pool` label row for each new (query, chunk) pair. It refuses to overwrite without `--force`, never edits existing label rows, and refuses to run if the vector backend is unavailable. |
| `pool --batch NN --query ID` | Prints the query and each pool row as `<rank>. <chunk_id> <path>:<start>-<end> [<grade or ->]` with an 8-line preview. |
| `pool --full CHUNK_ID` | Prints a whole chunk at the pinned commit. |
| `pool --path FILE` | Lists a file's chunk ids and line ranges at the pinned commit. |
| `grade --batch NN --query ID --grades "3 0 1 2? ..."` | Sets grades in pool rank order, one digit per pool row (0-3, `?` = low confidence). |
| `grade ... --extra CHUNK_ID=G` | Adds a `gold` row (or regrades an existing row) for a chunk at the pinned commit. Repeatable. |
| `grade ... --ambiguous` | Sets `flag=ambiguous` on every row of the query. |
| `review` | Writes `REVIEW.md` with only the `flag=review` rows and a per-batch counts table. |
| `check --batch NN` | Exits 1 and lists every ungraded row, bad value, pool chunk without a label row, or `text_sha` mismatch; exits 0 when the batch is complete. |
| `report [--split dev]` | Renders the metrics report from the stored pools. |

`grade` is idempotent, so labeling can resume from the batch CSV at any time. Run `check` to list what is left.

## Ben's review loop

1. Run `python -m voss.eval.retrieval review` and open `REVIEW.md`.
2. For each listed row, open the labels CSV that the row names, find the row by `query_id` and `chunk_id`, and set `grade`.
3. Then set `flag=reviewed`. If the query itself is unclear, set `flag=ambiguous` instead.
4. Run `check --batch NN` for each batch you edited.

## Locked split

Splits are assigned once, per group, when the dataset is frozen. After the freeze, nobody runs test-split metrics. The only test-split run is J3's comparison run, which uses `report --split test --locked-final`. The report command refuses `--split test` without `--locked-final`.
