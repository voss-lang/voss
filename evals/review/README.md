# Requirement assessment evaluation dataset

This dataset measures how often Jev's requirement assessments are wrong in the way that matters most: calling a requirement supported when the evidence does not show it. J4 publishes that false-supported rate, with its confidence range, from this data.

## Corpus scope

Every fixture is a synthetic change to the Voss repository at the single commit pinned in `corpus.json` (`c1a27046aef3096e460b1c24b59d8066e5c2f792`, the same commit as the retrieval dataset). Each diff must apply cleanly to that tree, so fixtures do not drift when the code changes.

Fixtures may contain only nonsensitive Voss source and made-up edits to it. No other repositories, personal data, session histories, credentials, production data, or clinical data.

## Files

| File | Written by | Contents |
|---|---|---|
| `corpus.json` | hand | repo, pinned commit, rubric version, the fixed shape of each kind, expected pair count, minimum locked negatives |
| `fixtures/batch-NN.jsonl` | Claude, Ben | one fixture per line (format below) |
| `REVIEW.md` | `review` | only the pairs flagged for Ben |
| `freeze.json` | `freeze` | the split, metric definitions, threshold policy, release bar, and file hashes |
| `reports/` | later runs | dev and locked-run reports |

## Fixture format

One JSON object per line:

| Field | Meaning |
|---|---|
| `id` | `rv-NNN`, unique across all batches |
| `kind` | one of the kinds below |
| `title` | a short plain-English summary of the change |
| `criteria` | list of requirement strings; IDs come from the same parser the evaluator uses (`AC-1`, `AC-2`, ... unless a line carries an explicit ID such as `S4.1: ...`) |
| `diff` | a unified diff that applies to the pinned tree with `git apply --check` |
| `checks` | recorded checks as `[{"name", "status"}]` or the eval runner's `[{"type", "pass"}]`; `[]` means no checks recorded |
| `verification_note` | free text, or `""` |
| `labels` | `{criterion_id: {"gold", "confidence", "flag", "note"}}`, one entry per criterion |
| `split` | `dev` or `test`; added by `freeze` only |

A criterion and its fixture together make one pair. All criteria of a fixture share a split.

## Kinds

Each kind has a fixed shape so the set adds up to 100 pairs and splits exactly 50/50:

| Kind | Fixtures | Criteria each | Supported each | What it tests |
|---|---|---|---|---|
| `missing_criterion` | 8 | 3 | 1 | checks pass but one requirement is simply absent from the change |
| `contradicted` | 8 | 3 | 1 | the diff does the opposite of a requirement |
| `failed_check` | 6 | 2 | 1 | a recorded check failed |
| `skipped_check` | 4 | 2 | 1 | a recorded check was skipped |
| `no_checks` | 6 | 2 | 0 | no checks recorded at all |
| `ambiguous` | 6 | 2 | 0 | requirements vague enough that the right answer is to abstain |
| `supported` | 4 | 2 | 2 | every requirement clearly met |

That gives 100 pairs, 66 of them should-not-be-supported, and 33 of those in the locked half. `failed_check` needs at least one failed check, `skipped_check` at least one skipped check, `no_checks` none at all, and the other kinds no failed or skipped checks.

## Labeling rules

- `supported`: the diff, the code, or the checks clearly show the requirement is met.
- `contradicted`: they show the requirement is not met, including a failing check for that behavior.
- `insufficient_evidence`: they show neither, including a requirement that is simply absent from the diff.

### Confidence and flags

- `confidence` is `high` or `low`. A `low` label must carry `flag: review`; `check` rejects a low label with `flag: none`.
- `flag` is `none`, `review` (Ben should look), `reviewed` (Ben looked and kept or fixed the gold label), or `ambiguous` (disputed).
- Ambiguous pairs are excluded from every rate and listed separately in the report.

## Workflow

Run from the repository root with `python -m voss.eval.review <command>`.

1. Claude drafts fixtures in `fixtures/batch-NN.jsonl`, flagging undecided labels.
2. `check [--batch NN]` validates ids, kinds, shapes, labels, checks, and that every diff applies to the pinned tree. It prints one line per problem and exits 1, or prints `ok`.
3. `review` writes `REVIEW.md` with only the flagged pairs: fixture id, criterion id, criterion text, draft gold, and note.
4. Ben resolves each flagged pair by setting `gold` and `flag: reviewed`, or `flag: ambiguous`.
5. `freeze` runs once. It refuses while any pair is still flagged `review`, while `check` fails, when fixture counts per kind differ from `corpus.json`, when dev and test have different pair counts, or when the locked half has fewer than `min_locked_negatives` (30) non-supported, non-ambiguous gold pairs. On refusal no fixture file changes.
6. Dev run, then tune the threshold on dev only.
7. One locked run on the test split.
8. Reviewer B baseline on the same fixtures, then compare.

The locked split cannot be loaded without `locked_final=True`.

## Frozen metric definitions

`freeze` writes these into `freeze.json` before any locked read:

- **False-supported rate:** pairs shown `supported` whose gold is `contradicted` or `insufficient_evidence`, over all non-supported gold pairs, with a Wilson 95% interval.
- **Contradicted recall:** pairs shown `contradicted` over gold `contradicted` pairs, with a Wilson 95% interval.
- **Abstention rate:** pairs shown `abstained` or `no_answer`, or whose call failed, over all scored pairs. **Coverage** is one minus that. Failed calls are also counted separately.
- **Ambiguity:** the number of pairs flagged `ambiguous`, listed by fixture and criterion.
- **Brier score:** mean of (P(supported) minus 1 if gold is supported, else 0) squared, over scored pairs that have probabilities.
- **Latency:** p50 and p95 `latency_ms` over answered receipts.
- **Cost:** total and mean observed `cost_usd`.

Threshold policy: start at 0.80, tune on dev only, and record the value used for the locked run in `reports/review-test.json`.

Release bar: the false-supported point estimate on the locked split is at most 5%. The Wilson 95% interval is reported but does not gate.

A 50-pair locked half cannot prove a false-supported rate of 5% or less. Even with zero errors over 30 negatives, the Wilson upper bound is above 11%. The report says this plainly.
